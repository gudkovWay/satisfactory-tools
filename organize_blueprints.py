#!/usr/bin/env python3
"""Reorganise the blueprint categories of the 'каша' save."""

import copy
import os
import shutil
import struct
import sys

import satisfactory_bp as S

SAVEDIR = ("/home/q/games/SteamLibrary/steamapps/compatdata/526870/pfx/drive_c/users/"
           "steamuser/AppData/Local/FactoryGame/Saved/SaveGames/76561198736176585")
BPDIR = ("/home/q/games/SteamLibrary/steamapps/compatdata/526870/pfx/drive_c/users/"
         "steamuser/AppData/Local/FactoryGame/Saved/SaveGames/blueprints/каша")
DOWNLOADS = "/home/q/Downloads"


# --------------------------------------------------------------------------
# where each blueprint should end up
# --------------------------------------------------------------------------

def classify(name):
    """-> (category, subcategory) or None to leave the blueprint where it is."""
    inc = "Incline" in name or "Decline" in name
    curve = "Curve" in name or "°" in name
    junction = "Junction" in name or "Intersection" in name or "Four Way" in name

    if name.startswith("RLRDv1") or name.startswith("RLRD Support"):
        cat = "RLRDv1"
        if "Support" in name:                      return cat, "Support"
        if junction:                               return cat, "Junctions"
        if inc or "2m" in name or "2M" in name:    return cat, "Incline"
        if curve:                                  return cat, "Curves"
        return cat, "Straight"

    if name.startswith("RDv4W"):
        cat = "RDv4W"
        if "Support" in name:                      return cat, "Support"
        if inc or "2m" in name:                    return cat, "Incline"
        if curve:                                  return cat, "Curves"
        return cat, "Straight"

    if name.startswith("RDv4"):
        cat = "RDv4"
        if "Suppport" in name or "Support" in name: return cat, "Support"
        if "Cnnct" in name:                         return cat, "Cnnct"
        if junction:                                return cat, "Junctions"
        if "Ramp" in name or inc:                   return cat, "Ramps"
        if curve:                                   return cat, "Curves"
        return cat, "Straight"

    if name.startswith("RoadRail Seg"):             return "RoadRail", "Segments"
    if name.startswith("T-Junction") or name.startswith("X-Junction"):
        return "RoadRail", "Junctions"
    if name.startswith("Pillar") or name.startswith("Double Pillar"):
        return "RoadRail", "Pillars"

    if name == "Suspension Bridge":                 return "Misc", "Misc"
    return None


# category order and sub-category order in the menu
CAT_ORDER = ["RDv4", "RDv4W", "RLRDv1", "RoadRail", "Misc"]
SUB_ORDER = {
    "RDv4":     ["Straight", "Curves", "Ramps", "Cnnct", "Junctions", "Support"],
    "RDv4W":    ["Straight", "Curves", "Incline", "Support"],
    "RLRDv1":   ["Straight", "Curves", "Incline", "Junctions", "Support"],
    "RoadRail": ["Segments", "Junctions", "Pillars"],
    "Misc":     ["Misc"],
}


# --------------------------------------------------------------------------
# icon ids, harvested from real .sbpcfg files so they are guaranteed valid
# --------------------------------------------------------------------------

def icon_of(cfg_path):
    d = open(cfg_path, 'rb').read()
    desc_len = struct.unpack_from('<i', d, 4)[0]
    return struct.unpack_from('<i', d, 8 + desc_len)[0]


def pick_icons():
    def first(d, prefix):
        for f in sorted(os.listdir(d)):
            if f.startswith(prefix) and f.endswith('.sbpcfg'):
                return icon_of(os.path.join(d, f))
        return -1
    return {
        "RDv4":     first(BPDIR, "RDv4 "),
        "RDv4W":    first(BPDIR, "RDv4W"),
        "RLRDv1":   first(BPDIR, "RLRDv1"),
        "RoadRail": first(DOWNLOADS, "RoadRail Seg"),
        "Misc":     first(BPDIR, "Suspension"),
    }


# --------------------------------------------------------------------------
# record construction (clone an existing record, substitute the fields)
# --------------------------------------------------------------------------

def props_by_name(plist):
    return {p.name: p for p in plist}


def set_str(prop, text):
    prop.value = S.w_fstring(text)


def make_sub(template, name, priority, blueprint_names):
    rec = copy.deepcopy(template)
    d = props_by_name(rec)
    set_str(d['SubCategoryName'], name)
    d['MenuPriority'].value = struct.pack('<f', priority)
    d['IsUndefined'].value = b'\x00'
    d['BlueprintNames'].array = ("Str", list(blueprint_names))
    return rec


def make_cat(template, sub_template, name, icon, priority, subs):
    rec = copy.deepcopy(template)
    d = props_by_name(rec)
    set_str(d['CategoryName'], name)
    d['IconID'].value = struct.pack('<i', icon)
    d['MenuPriority'].value = struct.pack('<f', priority)
    d['IsUndefined'].flag = 0x00
    d['SubCategoryRecords'].array = ("Struct", [
        make_sub(sub_template, sname, float(i), names)
        for i, (sname, names) in enumerate(subs)
    ])
    return rec


# --------------------------------------------------------------------------

def build(prop, icons, extra_names):
    kind, cats = prop.array
    assert kind == "Struct"

    by_name = {}
    order = []
    for c in cats:
        d = props_by_name(c)
        nm = S.Reader(d['CategoryName'].value).fstring()
        by_name[nm] = c
        order.append(nm)

    if "Undefined" not in by_name:
        raise SystemExit("no Undefined category -- nothing to reorganise")

    cat_tpl = by_name.get("ZаVOды") or by_name["Undefined"]
    sub_tpl = props_by_name(cat_tpl)['SubCategoryRecords'].array[1][0]

    # every blueprint name currently known to the save, plus the newly added files
    placed = {}
    leftover = []
    undef = props_by_name(by_name["Undefined"])['SubCategoryRecords'].array[1]
    pool = []
    for s in undef:
        pool += props_by_name(s)['BlueprintNames'].array[1]
    pool += extra_names

    for n in pool:
        target = classify(n)
        if target is None:
            leftover.append(n)
        else:
            placed.setdefault(target, []).append(n)

    # keep Undefined (holding whatever we could not classify) and any pre-existing
    # user categories exactly as they were, then append the new ones
    new_cats = []
    for i, nm in enumerate(order):
        c = by_name[nm]
        if nm == "Undefined":
            subs = props_by_name(c)['SubCategoryRecords'].array[1]
            props_by_name(subs[0])['BlueprintNames'].array = ("Str", leftover)
            for s in subs[1:]:
                props_by_name(s)['BlueprintNames'].array = ("Str", [])
        new_cats.append(c)

    prio = float(len(new_cats))
    for cname in CAT_ORDER:
        subs = [(s, placed.get((cname, s), [])) for s in SUB_ORDER[cname]]
        subs = [(s, names) for s, names in subs if names]
        if not subs:
            continue
        new_cats.append(make_cat(cat_tpl, sub_tpl, cname,
                                 icons.get(cname, -1), prio, subs))
        prio += 1.0

    prop.array = ("Struct", new_cats)
    return placed, leftover


def dump(prop):
    for c in prop.array[1]:
        d = props_by_name(c)
        nm = S.Reader(d['CategoryName'].value).fstring()
        icon = struct.unpack('<i', d['IconID'].value)[0]
        subs = d['SubCategoryRecords'].array[1]
        total = sum(len(props_by_name(s)['BlueprintNames'].array[1]) for s in subs)
        print(f"  {nm}  (icon {icon}, {total} bp)")
        for s in subs:
            sd = props_by_name(s)
            snm = S.Reader(sd['SubCategoryName'].value).fstring()
            names = sd['BlueprintNames'].array[1]
            print(f"      {snm:<12} {len(names):>3}")


def install_pack():
    """Copy the new blueprint pack into the save's blueprint folder."""
    added = []
    for f in sorted(os.listdir(DOWNLOADS)):
        if not f.endswith('.sbp'):
            continue
        cfg = f[:-4] + '.sbpcfg'
        if not os.path.exists(os.path.join(DOWNLOADS, cfg)):
            print(f"  ! {f}: no .sbpcfg alongside, skipped")
            continue
        for src in (f, cfg):
            dst = os.path.join(BPDIR, src)
            if os.path.exists(dst):
                print(f"  ! {src}: already present, skipped")
                break
            shutil.copy2(os.path.join(DOWNLOADS, src), dst)
        else:
            added.append(f[:-4])
    return added


def main():
    apply_changes = "--apply" in sys.argv
    target = os.path.join(SAVEDIR, "cachys.sav")

    print("== blueprint pack ==")
    if apply_changes:
        added = install_pack()
    else:
        added = [f[:-4] for f in sorted(os.listdir(DOWNLOADS)) if f.endswith('.sbp')]
    print(f"  {len(added)} blueprints: {', '.join(added)}")

    print(f"\n== {os.path.basename(target)} ==")
    header, body, _ = S.read_save(target)
    loc = S.locate(body)
    prop = S.read_categories(body, loc)
    print(f"  parsed, round-trip exact ({loc.prop_end - loc.prop_off} bytes)")

    icons = pick_icons()
    placed, leftover = build(prop, icons, added)

    print("\n== new layout ==")
    dump(prop)
    if leftover:
        print(f"\n  left in Undefined ({len(leftover)}): {', '.join(leftover)}")

    new_bytes = S.write_props([prop], terminate=True)
    new_body, delta = S.splice(body, loc, new_bytes)
    print(f"\n  body {len(body)} -> {len(new_body)} ({delta:+d} bytes)")

    S.verify(new_body)
    loc2 = S.locate(new_body)
    prop2 = S.read_categories(new_body, loc2)
    if S.write_props([prop2], terminate=True) != new_bytes:
        raise SystemExit("re-parse mismatch")
    print("  verified: object framing intact, property re-parses identically")

    if not apply_changes:
        print("\nDry run. Re-run with --apply to write.")
        return

    backup = target + ".bak-precat"
    if not os.path.exists(backup):
        shutil.copy2(target, backup)
        print(f"\n  backup -> {os.path.basename(backup)}")
    size = S.write_save(target, header, new_body)
    print(f"  written: {size} bytes")

    h2, b2, _ = S.read_save(target)
    if b2 != new_body:
        raise SystemExit("readback mismatch!")
    S.verify(b2)
    print("  readback OK")


if __name__ == "__main__":
    main()
