#!/usr/bin/env python3
"""Разложить рельсовые паки Hornslet и SeaShark (+ одиночные блюпринты) по категориям.

Категории живут в самом сейве (mBlueprintCategoryRecords в BP_GameState),
а не в .sbpcfg — поэтому файлы просто копируются в папку блюпринтов,
а раскладку правит этот скрипт.

    python3 organize_trains.py                        # dry run, ничего не пишет
    python3 organize_trains.py --apply --main-menu    # копирует файлы и правит сейв
    python3 organize_trains.py --save каша_autosave_0.sav --apply --main-menu

Паки качаются через sc_blueprints.py:
    python3 sc_blueprints.py 26026/Hornslet -o ~/Hornslet
    python3 sc_blueprints.py 99247/SeaShark -o ~/SeaShark

Игра при этом должна быть закрыта (или хотя бы выгружен мир — тогда --main-menu),
иначе автосейв затрёт правку.
"""

import os
import re
import shutil
import sys

import satisfactory_bp as S
import organize_blueprints as O            # make_cat / make_sub / props_by_name / icon_of
import organize_sixsense as X              # install_pack / pick_save / game_running

# каталог -> категория в меню; одиночные .sbp тоже можно прописать сюда
SRC_CATS = [
    ("/home/q/Hornslet", "Hornslet"),
    ("/home/q/SeaShark", "SeaShark"),
    ("/home/q/Downloads/Station Minage.sbp", "Misc"),
]
ICON_DIRS = [d if os.path.isdir(d) else os.path.dirname(d) for d, _ in SRC_CATS] + [O.BPDIR]
BPDIR = O.BPDIR
SAVE_DEFAULT = "cachys.sav"
BACKUP_SUFFIX = ".bak-pretrains"

props_by_name = O.props_by_name

# имя блюпринта -> категория, заполняется в main() по источнику файла
ORIGIN = {}


# --------------------------------------------------------------------------
# куда что кладём
# --------------------------------------------------------------------------

HORN_FAMILIES = ["CTP", "CRS", "CBT", "CCP", "CBR"]
FACTORY_KW = ("Smelter", "Smelting", "Foundry", "Assembler", "Refinery", "Manifold",
              "Generator", "Fuel", "Coal", "Preload", "Pump", "Buffer", "Drone Port",
              "Powercell", "Power Pillar", "Energi Pillar", "Crafting", "Water Ring",
              "Fluid", "Gas Station")


def horn_cat(name):
    """Пак Hornslet огромный (500 шт), поэтому режется на семейства по префиксу."""
    for f in HORN_FAMILIES:
        if name.startswith(f + " "):
            return "Horn " + f
    if name.startswith("2L "):
        return "Horn 2L"
    # завод ловим раньше нумерованной серии: "120 Iron Ore - Ingot Preload"
    if any(k in name for k in FACTORY_KW):
        return "Horn Factory"
    # нумерованная серия автора: "117 Straight 32m" ... "1717 Station Left Extra"
    if re.match(r"^\d{3,4} ", name) or re.match(r"^\d{2} Bonus ", name):
        return "Horn Series"
    if any(k in name for k in ("Bridge", "Viaduct", "Warren", "Arch")):
        return "Horn Bridges"
    if "Station" in name:
        return "Horn Stations"
    if any(k in name for k in ("Rail", "Track", "Train", "Tunnel", "Subway", "Turn",
                               "Curve", "Ramp", "Interchange", "Roundabout", "RoundAbout",
                               "Clover", "Junction", "Overpass", "Underpass", "Lane",
                               "Spiral Elevator", "Monorail", "Y Track")):
        return "Horn Rails"
    return "Horn Decor"


def horn_sub(cat, name):
    """Подкатегория внутри семейства — по типу детали."""
    if cat == "Horn CTP":
        if "Station" in name:                       return "Stations"
        if "Spiral" in name:                        return "Spiral"
        if "Round" in name:                         return "Round"
        if "Switch" in name:                        return "Switches"
        if "T-Section" in name:                     return "T-Section"
        if "X-Section" in name:                     return "X-Section"
        if "Ramp" in name:                          return "Ramps"
        if "Turn" in name:                          return "Turns"
        if "Straight" in name:                      return "Straight"
        return "Misc"

    if cat == "Horn CRS":
        if "Station" in name:                       return "Stations"
        if "Elevator" in name:                      return "Elevators"
        if "Intersection" in name:                  return "Intersections"
        if "Roundabout" in name:                    return "Roundabout"
        if "Split" in name or "Merge" in name or "Merger" in name:
            return "Splits"
        if "Ramp" in name:                          return "Ramps"
        if "Curved" in name or "Curve" in name:     return "Curves"
        if "Straight" in name:                      return "Straight"
        return "Misc"

    if cat == "Horn CBT":
        if "Roundabout" in name:                    return "Roundabout"
        if "Crossing" in name:                      return "Crossings"
        if "Switch" in name:                        return "Switches"
        if "Split" in name:                         return "Splits"
        if "Curve" in name:                         return "Curves"
        return "Misc"

    if cat == "Horn CCP":
        if "Base Plate" in name:                    return "Base Plates"
        if "Tower" in name:                         return "Towers"
        if "Station" in name:                       return "Stations"
        if "Road" in name:                          return "Roads"
        return "Misc"

    if cat == "Horn CBR":
        if "Roundabount" in name or "Roundabout" in name:
            return "Roundabout"
        if "Section" in name:                       return "Sections"
        if "Curve" in name:                         return "Curves"
        if "Straight" in name:                      return "Straight"
        return "Misc"

    if cat == "Horn 2L":
        if "Bridge" in name:                        return "Bridges"
        if "Roundabout" in name:                    return "Roundabout"
        if "Interchange" in name or "Overpass" in name:
            return "Interchanges"
        if "Ramp" in name:                          return "Ramps"
        if "Split" in name or "1into3" in name or "Switch" in name:
            return "Splits"
        if "U-Turn" in name or "Left" in name or "Right" in name or "Curve" in name:
            return "Turns"
        return "Misc"

    if cat == "Horn Series":
        if "Bonus" in name:                         return "Bonus"
        if "Station" in name:                       return "Stations"
        if "Ramp" in name:                          return "Ramps"
        if "Turn" in name:                          return "Turns"
        if "Straight" in name:                      return "Straight"
        return "Misc"

    if cat == "Horn Bridges":
        if "Support" in name or "Legs" in name or "Pillar" in name:
            return "Supports"
        if "Template" in name or "Part" in name:    return "Templates"
        return "Bridges"

    if cat == "Horn Stations":
        if "Truck" in name or "Gas Station" in name:  return "Truck"
        if "Module" in name or "Connector" in name:   return "Modules"
        if "Train" in name or "Station" in name:      return "Train"
        return "Misc"

    if cat == "Horn Rails":
        if "Tunnel" in name or "Subway" in name:    return "Tunnels"
        if "Interchange" in name or "Clover" in name or "Overpass" in name \
                or "Underpass" in name:             return "Interchanges"
        if "Roundabout" in name or "RoundAbout" in name:
            return "Roundabouts"
        if "Elevator" in name:                      return "Elevators"
        if "Ramp" in name:                          return "Ramps"
        if "Turn" in name or "Curve" in name or "Degree" in name:
            return "Turns"
        if "Straight" in name or "Track" in name:   return "Straight"
        return "Misc"

    if cat == "Horn Factory":
        if any(k in name for k in ("Smelter", "Smelting", "Foundry", "Assembler",
                                   "Refinery", "Manifold")):
            return "Production"
        if "Generator" in name or "Fuel" in name or "Coal" in name or "Powercell" in name \
                or "Pillar" in name:                return "Power"
        if "Pump" in name or "Fluid" in name or "Buffer" in name or "Water" in name:
            return "Fluids"
        return "Misc"

    # Horn Decor
    if "Window" in name or "Wall" in name:          return "Walls"
    if "Stair" in name or "Catwalk" in name or "Corridor" in name:
        return "Stairs"
    if "Light" in name or "Tron Gate" in name:      return "Lights"
    return "Art"


def classify(name):
    """-> (категория, подкатегория). Категория — по паку, подкатегория — по имени."""
    origin = ORIGIN.get(name, "Misc")

    if origin == "Hornslet":
        cat = horn_cat(name)
        return cat, horn_sub(cat, name)

    cat = origin
    if "Station" in name:                             return cat, "Stations"
    if "Roundabout" in name:                          return cat, "Roundabout"
    if any(k in name for k in ("Junction", "T-section", "Split", "4-way")):
        return cat, "Junctions"
    if "Ramp" in name or "Incline" in name:           return cat, "Ramps"
    if "Curve" in name or "Degree" in name or "\u00b0" in name:
        return cat, "Curves"
    if "Straight" in name:                            return cat, "Straight"
    if "Diagonal" in name:                            return cat, "Diagonal"
    if "Bridge" in name:                              return cat, "Bridges"
    if "Pillar" in name or "Support" in name:         return cat, "Support"
    return cat, "Misc"


HORN_CATS = ["Horn CTP", "Horn CRS", "Horn CBT", "Horn CCP", "Horn CBR", "Horn 2L",
             "Horn Series", "Horn Rails", "Horn Bridges", "Horn Stations",
             "Horn Factory", "Horn Decor"]
CAT_ORDER = HORN_CATS + ["SeaShark", "Misc"]
SUB_ORDER = {
    "Horn CTP":      ["Straight", "Turns", "Ramps", "T-Section", "X-Section",
                      "Switches", "Round", "Spiral", "Stations", "Misc"],
    "Horn CRS":      ["Straight", "Curves", "Ramps", "Splits", "Intersections",
                      "Roundabout", "Elevators", "Stations", "Misc"],
    "Horn CBT":      ["Curves", "Splits", "Switches", "Crossings", "Roundabout", "Misc"],
    "Horn CCP":      ["Base Plates", "Roads", "Towers", "Stations", "Misc"],
    "Horn CBR":      ["Straight", "Curves", "Sections", "Roundabout", "Misc"],
    "Horn 2L":       ["Turns", "Ramps", "Splits", "Roundabout", "Interchanges",
                      "Bridges", "Misc"],
    "Horn Series":   ["Straight", "Turns", "Ramps", "Stations", "Bonus", "Misc"],
    "Horn Rails":    ["Straight", "Turns", "Ramps", "Tunnels", "Interchanges",
                      "Roundabouts", "Elevators", "Misc"],
    "Horn Bridges":  ["Bridges", "Supports", "Templates"],
    "Horn Stations": ["Train", "Truck", "Modules", "Misc"],
    "Horn Factory":  ["Production", "Power", "Fluids", "Misc"],
    "Horn Decor":    ["Walls", "Stairs", "Lights", "Art"],
    "SeaShark":      ["Straight", "Diagonal", "Curves", "Ramps", "Bridges", "Roundabout",
                      "Junctions", "Stations", "Support", "Misc"],
    "Misc":          ["Stations", "Misc"],
}


def pick_icons(names):
    """Иконки берём из настоящих .sbpcfg — так гарантированно валидные id.

    Многие блюпринты пака делят одну и ту же иконку, поэтому для каждой
    категории берём первый ещё не занятый id среди её же блюпринтов —
    иначе половина категорий в меню выглядит одинаково.
    """
    def cfg_path(name):
        for d in ICON_DIRS:
            p = os.path.join(d, name + ".sbpcfg")
            if os.path.exists(p):
                return p
        return None

    members = {}
    for n in names:
        members.setdefault(classify(n)[0], []).append(n)

    out, used = {}, set()
    for cat in CAT_ORDER:
        ids = []
        for n in members.get(cat, []):
            p = cfg_path(n)
            if p:
                try:
                    ids.append(O.icon_of(p))
                except Exception:
                    pass
        out[cat] = next((i for i in ids if i >= 0 and i not in used),
                        next((i for i in ids if i >= 0), -1))
        used.add(out[cat])
    return out


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


def load_origins():
    """Запоминает, из какого пака пришёл каждый блюпринт, до копирования в сейв."""
    for src, cat in SRC_CATS:
        if not os.path.exists(src):
            print(f"  ! нет источника: {src}")
            continue
        for path in X.iter_sources([src]):
            ORIGIN[os.path.basename(path)[:-4]] = cat


def main():
    apply_changes = "--apply" in sys.argv
    SAVE = X.pick_save(sys.argv) if "--save" in sys.argv \
        else os.path.join(O.SAVEDIR, SAVE_DEFAULT)
    srcs = [s for s, _ in SRC_CATS if os.path.exists(s)]

    if apply_changes and X.game_running() and "--main-menu" not in sys.argv:
        raise SystemExit("Satisfactory запущен. Выйди в главное меню (мир должен быть "
                         "выгружен) и добавь --main-menu, иначе автосейв затрёт правку.")

    load_origins()

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

    names = added + skipped
    placed, dup = build(prop, pick_icons(names), names)

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
        print("\nDry run. Для записи: python3 organize_trains.py --apply --main-menu")
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
