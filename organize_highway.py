#!/usr/bin/env python3
"""Разложить пак хайвеев TheHighwayGuy по категориям в сейве cachys.sav.

Категории живут в самом сейве (mBlueprintCategoryRecords в BP_GameState),
а не в .sbpcfg — поэтому файлы просто копируются в папку блюпринтов,
а раскладку правит этот скрипт.

    python3 organize_highway.py                        # dry run, ничего не пишет
    python3 organize_highway.py --apply --main-menu    # копирует файлы и правит сейв
    python3 organize_highway.py --save каша_autosave_0.sav --apply
    python3 organize_highway.py --src ~/TheHighwayGuy --apply

Пак качается через sc_blueprints.py:
    python3 sc_blueprints.py 54766/TheHighwayGuy -o ~/TheHighwayGuy

Игра при этом должна быть закрыта, иначе автосейв затрёт правку.
"""

import os
import re
import shutil
import sys

import satisfactory_bp as S
import organize_blueprints as O            # make_cat / make_sub / props_by_name / icon_of
import organize_sixsense as X              # install_pack / pick_save / game_running

SRC_DEFAULT = ["/home/q/TheHighwayGuy"]
ICON_DIRS = SRC_DEFAULT + [O.BPDIR]
BPDIR = O.BPDIR
SAVE_DEFAULT = "cachys.sav"
BACKUP_SUFFIX = ".bak-prehighway"

props_by_name = O.props_by_name


# --------------------------------------------------------------------------
# куда что кладём
# --------------------------------------------------------------------------

def classify(name):
    """-> (категория, подкатегория). Этаж берётся из '2F' в имени."""
    if "Pixelart" in name:
        if "Targaryen" in name:   return "THG Pixelart", "Targaryen"
        if "Ficsit" in name:      return "THG Pixelart", "Ficsit"
        return "THG Pixelart", "Misc"

    cat = "THG Highway 2F" if "2F" in name else "THG Highway"

    # обвязка идёт первой: "Pillar End" — это опора, а не торец дороги
    if any(k in name for k in ("Pillar", "PowerTower", "Streetsign")):
        return cat, "Support"
    if "Station" in name:                             return cat, "Stations"
    if "Intersection" in name:                        return cat, "Junctions"
    if "Ramp" in name:                                return cat, "Ramps"
    # Ends раньше Straight: "Straight End T" — это торец, а не прямая
    if "End" in name:                                 return cat, "Ends"
    # градусы в именах файлов теряются ("Left 30°" -> "Left 30"), ловим и то и то
    if re.search(r"(Left|Right)\s*\d", name) or "°" in name \
            or "S Left" in name or "S Right" in name:
        return cat, "Curves"
    if "Straight" in name:                            return cat, "Straight"
    return cat, "Misc"


CAT_ORDER = ["THG Highway", "THG Highway 2F", "THG Pixelart"]
SUB_ORDER = {
    "THG Highway":    ["Straight", "Curves", "Ramps", "Ends", "Junctions",
                       "Stations", "Support", "Misc"],
    "THG Highway 2F": ["Straight", "Curves", "Ramps", "Ends", "Junctions",
                       "Stations", "Support", "Misc"],
    "THG Pixelart":   ["Ficsit", "Targaryen", "Misc"],
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
        "THG Highway":    icon("THG Highway Straight L.sbpcfg"),
        # у 2F иконка рампы, иначе оба хайвея в меню выглядят одинаково
        "THG Highway 2F": icon("THG Highway 2F Ramp L Lighted.sbpcfg"),
        "THG Pixelart":   icon("THG Pixelart Canvas.sbpcfg"),
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
    SAVE = X.pick_save(sys.argv) if "--save" in sys.argv \
        else os.path.join(O.SAVEDIR, SAVE_DEFAULT)
    srcs = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--src"] or SRC_DEFAULT

    if apply_changes and X.game_running() and "--main-menu" not in sys.argv:
        raise SystemExit("Satisfactory запущен. Выйди в главное меню (мир должен быть "
                         "выгружен) и добавь --main-menu, иначе автосейв затрёт правку.")

    print("== пак ==")
    added, skipped = X.install_pack(srcs, apply_changes)
    print(f"  {len(added)} блюпринтов" + (f", уже на месте: {len(skipped)}" if skipped else ""))
    for n in added:
        c, s = classify(n)
        print(f"    {n}  ->  {c}/{s}")

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
        print("\nDry run. Для записи: python3 organize_highway.py --apply --main-menu")
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
