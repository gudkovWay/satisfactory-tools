#!/usr/bin/env python3
"""Разложить пак блюпринтов sixsense по категориям в сейве cachys.sav.

Категории живут в самом сейве (mBlueprintCategoryRecords в BP_GameState),
а не в .sbpcfg — поэтому файлы просто копируются в папку блюпринтов,
а раскладку правит этот скрипт.

    python3 organize_sixsense.py                     # dry run, ничего не пишет
    python3 organize_sixsense.py --apply             # копирует файлы и правит сейв
    python3 organize_sixsense.py --save каша_autosave_0.sav --apply
    python3 organize_sixsense.py --src ~/sixsense --src "~/Downloads/Foo.sbp" --apply

Игра при этом должна быть закрыта, иначе автосейв затрёт правку.
"""

import copy
import os
import shutil
import struct
import sys

import satisfactory_bp as S
import organize_blueprints as O            # make_cat / make_sub / props_by_name / icon_of

SRC_DEFAULT = ["/home/q/sixsense"]
BPDIR = O.BPDIR
SAVE_DEFAULT = "cachys.sav"
BACKUP_SUFFIX = ".bak-presixsense"

props_by_name = O.props_by_name


# --------------------------------------------------------------------------
# куда что кладём
# --------------------------------------------------------------------------

def classify(name):
    """-> (категория, подкатегория). Система берётся из суффикса имени."""
    if "(ML_" in name:
        cat = "ML"
    elif "(TL_" in name or name.endswith("(TL)"):
        cat = "TL"
    else:
        return "Misc", "Misc"                      # Hyperloop, Main Bus, и т.п.

    if "Roundabout" in name:                       return cat, "Roundabout"
    if "Crossing" in name or "Junction" in name:   return cat, "Junctions"
    if "Adapter" in name:                          return cat, "Adapters"
    if "Curve" in name or "°" in name:             return cat, "Curves"
    if any(k in name for k in ("Ascend", "Descend", "Slope", "Incline", "Decline")):
        return cat, "Incline"
    if "Straight" in name:                         return cat, "Straight"
    return cat, "Misc"


CAT_ORDER = ["ML", "TL", "Misc"]
SUB_ORDER = {
    "ML":   ["Straight", "Curves", "Incline", "Adapters", "Roundabout", "Junctions", "Misc"],
    "TL":   ["Straight", "Curves", "Incline", "Adapters", "Roundabout", "Junctions", "Misc"],
    "Misc": ["Misc"],
}


def pick_icons():
    """Иконки берём из настоящих .sbpcfg — так гарантированно валидные id."""
    def icon(fname):
        for d in SRC_DEFAULT:
            p = os.path.join(d, fname)
            if os.path.exists(p):
                return O.icon_of(p)
        return -1
    return {
        "ML":   icon("Straight (ML_basic).sbpcfg"),
        "TL":   icon("Straight (TL_basic).sbpcfg"),
        "Misc": icon("Hyperloop Single.sbpcfg"),
    }


# --------------------------------------------------------------------------
# сборка записей
# --------------------------------------------------------------------------

def cat_name(rec):
    return S.Reader(props_by_name(rec)['CategoryName'].value).fstring()


def sub_name(rec):
    return S.Reader(props_by_name(rec)['SubCategoryName'].value).fstring()


def all_known_names(cats):
    """Все имена блюпринтов, уже разложенные по категориям сейва."""
    out = set()
    for c in cats:
        for s in props_by_name(c)['SubCategoryRecords'].array[1]:
            out.update(props_by_name(s)['BlueprintNames'].array[1])
    return out


def build(prop, icons, names):
    kind, cats = prop.array
    assert kind == "Struct"

    by_name = {cat_name(c): c for c in cats}
    # шаблон для клонирования — любая существующая категория
    cat_tpl = next((by_name[n] for n in by_name if n != "Undefined"), None) \
              or by_name.get("Undefined")
    if cat_tpl is None:
        raise SystemExit("в сейве нет ни одной категории — нечего взять за шаблон")
    sub_tpl = props_by_name(cat_tpl)['SubCategoryRecords'].array[1][0]

    known = all_known_names(cats)

    placed, leftover, dup = {}, [], []
    for n in names:
        if n in known:
            dup.append(n)                          # уже разложен, второй раз не добавляем
            continue
        c, s = classify(n)
        placed.setdefault((c, s), []).append(n)

    new_cats = list(cats)
    prio = float(len(new_cats))

    for cname in CAT_ORDER:
        subs = [(s, placed.get((cname, s), [])) for s in SUB_ORDER[cname]]
        subs = [(s, ns) for s, ns in subs if ns]
        if not subs:
            continue

        existing = by_name.get(cname)
        if existing is None:
            # новой категории ещё нет — создаём целиком
            new_cats.append(O.make_cat(cat_tpl, sub_tpl, cname,
                                       icons.get(cname, -1), prio, subs))
            prio += 1.0
            continue

        # категория уже есть — доливаем в неё, чтобы не плодить дубликаты
        arr = props_by_name(existing)['SubCategoryRecords'].array[1]
        have = {sub_name(s): s for s in arr}
        for sname, ns in subs:
            if sname in have:
                d = props_by_name(have[sname])
                d['BlueprintNames'].array = ("Str", d['BlueprintNames'].array[1] + ns)
            else:
                arr.append(O.make_sub(sub_tpl, sname, float(len(arr)), ns))
        props_by_name(existing)['SubCategoryRecords'].array = ("Struct", arr)

    prop.array = ("Struct", new_cats)
    return placed, leftover, dup


def iter_sources(srcs):
    """Каждый источник — каталог с .sbp или путь к конкретному .sbp."""
    for src in srcs:
        if os.path.isdir(src):
            for f in sorted(os.listdir(src)):
                if f.endswith('.sbp'):
                    yield os.path.join(src, f)
        elif src.endswith('.sbp'):
            yield src
        else:
            raise SystemExit(f"не .sbp и не каталог: {src}")


def install_pack(srcs, apply_changes):
    """Копирует .sbp + .sbpcfg в папку блюпринтов сейва."""
    added, skipped = [], []
    for path in iter_sources(srcs):
        d, f = os.path.split(path)
        cfg = f[:-4] + '.sbpcfg'
        if not os.path.exists(os.path.join(d, cfg)):
            print(f"  ! {f}: нет парного .sbpcfg, пропуск")
            continue
        if os.path.exists(os.path.join(BPDIR, f)):
            skipped.append(f[:-4])
            continue
        if apply_changes:
            for name in (f, cfg):
                shutil.copy2(os.path.join(d, name), os.path.join(BPDIR, name))
        added.append(f[:-4])
    return added, skipped


def pick_save(argv):
    if "--save" in argv:
        name = argv[argv.index("--save") + 1]
    else:
        name = SAVE_DEFAULT
    path = name if os.path.isabs(name) else os.path.join(O.SAVEDIR, name)
    if not os.path.exists(path):
        raise SystemExit(f"нет такого сейва: {path}")
    return path


def game_running():
    """Ищет процесс игры в /proc.

    `pgrep -f` тут не годится: паттерн лежит в командной строке того шелла,
    который этот же pgrep и запускает, поэтому он матчит сам себя и всегда
    говорит «игра запущена». Свой процесс и всех своих родителей исключаем.
    """
    mine, pid = set(), os.getpid()
    while pid > 1:
        mine.add(pid)
        try:
            stat = open(f"/proc/{pid}/stat", "rb").read()
            pid = int(stat[stat.rindex(b")") + 2:].split()[1])   # ppid
        except (OSError, ValueError, IndexError):
            break

    for entry in os.listdir("/proc"):
        if not entry.isdigit() or int(entry) in mine:
            continue
        try:
            with open(f"/proc/{entry}/cmdline", "rb") as f:
                if b"FactoryGameSteam.exe" in f.read():
                    return True
        except OSError:                                          # процесс успел умереть
            continue
    return False


def pick_srcs(argv):
    out = [argv[i + 1] for i, a in enumerate(argv) if a == "--src"]
    return out or SRC_DEFAULT


def main():
    apply_changes = "--apply" in sys.argv
    SAVE = pick_save(sys.argv)
    srcs = pick_srcs(sys.argv)

    if apply_changes and game_running() and "--main-menu" not in sys.argv:
        raise SystemExit("Satisfactory запущен. Выйди в главное меню (мир должен быть "
                         "выгружен) и добавь --main-menu, иначе автосейв затрёт правку.")

    print("== пак ==")
    added, skipped = install_pack(srcs, apply_changes)
    print(f"  {len(added)} блюпринтов" + (f", уже на месте: {len(skipped)}" if skipped else ""))
    if not added:
        print("  нечего добавлять")

    print(f"\n== {os.path.basename(SAVE)} ==")
    header, body, _ = S.read_save(SAVE)
    loc = S.locate(body)
    prop = S.read_categories(body, loc)
    print(f"  разобран, round-trip точный ({loc.prop_end - loc.prop_off} байт)")

    placed, leftover, dup = build(prop, pick_icons(), added + skipped)

    print("\n== раскладка ==")
    O.dump(prop)
    if dup:
        print(f"\n  уже были разложены, пропущены ({len(dup)}): {', '.join(dup)}")
    if leftover:
        print(f"\n  осталось в Undefined ({len(leftover)}): {', '.join(leftover)}")

    new_bytes = S.write_props([prop], terminate=True)
    new_body, delta = S.splice(body, loc, new_bytes)
    print(f"\n  тело {len(body)} -> {len(new_body)} ({delta:+d} байт)")

    S.verify(new_body)
    loc2 = S.locate(new_body)
    if S.write_props([S.read_categories(new_body, loc2)], terminate=True) != new_bytes:
        raise SystemExit("re-parse mismatch")
    print("  проверено: секции целы, свойство перечитывается идентично")

    if not apply_changes:
        print("\nDry run. Для записи: python3 organize_sixsense.py --apply")
        return

    backup = SAVE + BACKUP_SUFFIX
    if not os.path.exists(backup):
        shutil.copy2(SAVE, backup)
        print(f"\n  бэкап -> {os.path.basename(backup)}")
    size = S.write_save(SAVE, header, new_body)
    print(f"  записано: {size} байт")

    _, b2, _ = S.read_save(SAVE)
    if b2 != new_body:
        raise SystemExit("readback mismatch!")
    S.verify(b2)
    print("  readback OK")


if __name__ == "__main__":
    main()
