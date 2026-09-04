#!/usr/bin/env python3
"""Разложить паки Swarley и EnderpriseArchitecture по категориям в сейве.

Категории живут в самом сейве (mBlueprintCategoryRecords в BP_GameState),
поэтому файлы просто копируются в папку блюпринтов, а раскладку правит
этот скрипт.

    python3 organize_packs.py                          # dry run
    python3 organize_packs.py --apply --main-menu      # копирует файлы и правит сейв
    python3 organize_packs.py --src ~/Swarley --apply
"""

import os
import shutil
import sys

import satisfactory_bp as S
import organize_blueprints as O            # make_cat / make_sub / props_by_name / icon_of
import organize_sixsense as X              # install_pack / pick_save / game_running

SCRATCH = ("/tmp/claude-1000/-home-q/850e3404-37c0-483e-975f-798a94598606/scratchpad")
SRC_DEFAULT = [os.path.join(SCRATCH, "Swarley"),
               os.path.join(SCRATCH, "EnderpriseArchitecture")]
DOWNLOADS = "/home/q/Downloads"
ICON_DIRS = SRC_DEFAULT + [DOWNLOADS]
BPDIR = O.BPDIR
SAVE_DEFAULT = "cachys.sav"
BACKUP_SUFFIX = ".bak-prepacks"

props_by_name = O.props_by_name


# --------------------------------------------------------------------------
# куда что кладём
# --------------------------------------------------------------------------

def classify(name):
    """-> (категория, подкатегория) по имени файла блюпринта."""
    if "futuristic" in name.lower():
        cat = "DarkStation"
        if "pillar" in name.lower() or "support" in name.lower():
            return cat, "Support"
        return cat, "Station"

    if name.startswith("SwarleyPack"):
        cat = "Swarley"
        if "pillars" in name:                        return cat, "Support"
        if "cross" in name:                          return cat, "Junctions"
        if "turn" in name:                           return cat, "Curves"
        if "updown" in name:                         return cat, "Incline"
        return cat, "Straight"

    cat = "Enderprise"
    if "Rail" in name or "Train Station" in name:    return cat, "Rails"
    if "Wall" in name:                               return cat, "Walls"
    if "Pier" in name or "Pillar" in name:           return cat, "Pillars"
    if "Stairs" in name or "Walkway" in name:        return cat, "Walkways"
    if any(k in name for k in ("Factory", "Manufacturer", "Refinery")):
        return cat, "Factory"
    return cat, "Misc"


CAT_ORDER = ["Swarley", "Enderprise", "DarkStation"]
SUB_ORDER = {
    "Swarley":    ["Straight", "Incline", "Curves", "Junctions", "Support"],
    "Enderprise": ["Walls", "Pillars", "Walkways", "Rails", "Factory", "Misc"],
    "DarkStation": ["Station", "Support"],
}


def pick_icons():
    """Иконки берём из настоящих .sbpcfg — так гарантированно валидные id."""
    def icon(fname):
        for d in ICON_DIRS:
            p = os.path.join(d, fname)
            if os.path.exists(p):
                return O.icon_of(p)
        return -1
    return {
        "Swarley":    icon("SwarleyPack  train rails  road  hypertube straight line.sbpcfg"),
        "Enderprise": icon("Industrial Wall.sbpcfg"),
        "DarkStation": icon("Dark futuristic train station.sbpcfg"),
    }


# --------------------------------------------------------------------------
# сборка записей
# --------------------------------------------------------------------------

def build(prop, icons, names):
    kind, cats = prop.array
    assert kind == "Struct"

    by_name = {X.cat_name(c): c for c in cats}
    # шаблон для клонирования — любая существующая категория
    cat_tpl = next((by_name[n] for n in by_name if n != "Undefined"), None) \
              or by_name.get("Undefined")
    if cat_tpl is None:
        raise SystemExit("в сейве нет ни одной категории — нечего взять за шаблон")
    sub_tpl = props_by_name(cat_tpl)['SubCategoryRecords'].array[1][0]

    known = X.all_known_names(cats)

    placed, dup = {}, []
    for n in names:
        if n in known:
            dup.append(n)                          # уже разложен, второй раз не добавляем
            continue
        placed.setdefault(classify(n), []).append(n)

    new_cats = list(cats)
    prio = float(len(new_cats))

    for cname in CAT_ORDER:
        subs = [(s, placed.get((cname, s), [])) for s in SUB_ORDER[cname]]
        subs = [(s, ns) for s, ns in subs if ns]
        if not subs:
            continue

        existing = by_name.get(cname)
        if existing is None:
            new_cats.append(O.make_cat(cat_tpl, sub_tpl, cname,
                                       icons.get(cname, -1), prio, subs))
            prio += 1.0
            continue

        # категория уже есть — доливаем в неё, чтобы не плодить дубликаты
        arr = props_by_name(existing)['SubCategoryRecords'].array[1]
        have = {X.sub_name(s): s for s in arr}
        for sname, ns in subs:
            if sname in have:
                d = props_by_name(have[sname])
                d['BlueprintNames'].array = ("Str", d['BlueprintNames'].array[1] + ns)
            else:
                arr.append(O.make_sub(sub_tpl, sname, float(len(arr)), ns))
        props_by_name(existing)['SubCategoryRecords'].array = ("Struct", arr)

    prop.array = ("Struct", new_cats)
    return placed, dup


def main():
    apply_changes = "--apply" in sys.argv
    SAVE = X.pick_save(sys.argv)
    srcs = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--src"] or SRC_DEFAULT

    if apply_changes and X.game_running() and "--main-menu" not in sys.argv:
        raise SystemExit("Satisfactory запущен. Выйди в главное меню (мир должен быть "
                         "выгружен) и добавь --main-menu, иначе автосейв затрёт правку.")

    print("== пак ==")
    added, skipped = X.install_pack(srcs, apply_changes)
    print(f"  {len(added)} блюпринтов" + (f", уже на месте: {len(skipped)}" if skipped else ""))

    print(f"\n== {os.path.basename(SAVE)} ==")
    header, body, _ = S.read_save(SAVE)
    loc = S.locate(body)
    prop = S.read_categories(body, loc)
    print(f"  разобран, round-trip точный ({loc.prop_end - loc.prop_off} байт)")

    placed, dup = build(prop, pick_icons(), added + skipped)

    print("\n== раскладка ==")
    O.dump(prop)
    if dup:
        print(f"\n  уже были разложены, пропущены ({len(dup)}): {', '.join(dup)}")

    new_bytes = S.write_props([prop], terminate=True)
    new_body, delta = S.splice(body, loc, new_bytes)
    print(f"\n  тело {len(body)} -> {len(new_body)} ({delta:+d} байт)")

    S.verify(new_body)
    loc2 = S.locate(new_body)
    if S.write_props([S.read_categories(new_body, loc2)], terminate=True) != new_bytes:
        raise SystemExit("re-parse mismatch")
    print("  проверено: секции целы, свойство перечитывается идентично")

    if not apply_changes:
        print("\nDry run. Для записи: python3 organize_packs.py --apply --main-menu")
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
