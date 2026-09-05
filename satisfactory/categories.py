"""The mBlueprintCategoryRecords property: read it, add to it, write it back.

This is the thing the game reads to build the blueprint menu, and the reason
installing a downloaded pack takes a tool at all -- the .sbpcfg next to a
blueprint says nothing about which category it belongs to. The record tree is:

    category record
        CategoryName        StrProperty
        IconID              IntProperty
        MenuPriority        FloatProperty
        IsUndefined         BoolProperty
        SubCategoryRecords  ArrayProperty<StructProperty>
            SubCategoryName StrProperty
            MenuPriority    FloatProperty
            IsUndefined     BoolProperty
            BlueprintNames  ArrayProperty<StrProperty>

New records are never built from nothing: one that the game itself wrote is
deep-copied and its fields substituted, so anything in the struct we do not
know about keeps whatever value the game put there.
"""

import copy
import struct

from . import save as S

UNDEFINED = "Undefined"


# --------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------

def props_by_name(plist):
    return {p.name: p for p in plist}


def cat_name(rec):
    return S.Reader(props_by_name(rec)['CategoryName'].value).fstring()


def sub_name(rec):
    return S.Reader(props_by_name(rec)['SubCategoryName'].value).fstring()


def subs_of(rec):
    return props_by_name(rec)['SubCategoryRecords'].array[1]


def names_of(sub):
    return props_by_name(sub)['BlueprintNames'].array[1]


def categories(prop):
    kind, cats = prop.array
    if kind != "Struct":
        raise ValueError("mBlueprintCategoryRecords is not a struct array")
    return cats


def all_names(cats):
    """Every blueprint name the save has already filed somewhere."""
    out = set()
    for c in cats:
        for s in subs_of(c):
            out.update(names_of(s))
    return out


def layout(prop):
    """-> [(category, icon, [(sub, [names])])], for printing."""
    out = []
    for c in categories(prop):
        d = props_by_name(c)
        icon = struct.unpack('<i', d['IconID'].value)[0]
        out.append((cat_name(c), icon,
                    [(sub_name(s), list(names_of(s))) for s in subs_of(c)]))
    return out


# --------------------------------------------------------------------------
# building
# --------------------------------------------------------------------------

def templates(cats):
    """A category record and a sub-category record to clone from."""
    named = {cat_name(c): c for c in cats}
    tpl = next((c for n, c in named.items() if n != UNDEFINED), None) \
        or named.get(UNDEFINED)
    if tpl is None:
        raise SystemExit("the save has no categories at all -- nothing to clone")
    subs = subs_of(tpl)
    if not subs:
        raise SystemExit(f"category {cat_name(tpl)!r} has no sub-categories to clone")
    return tpl, subs[0]


def _set_str(prop, text):
    prop.value = S.w_fstring(text)


def make_sub(template, name, priority, blueprint_names):
    rec = copy.deepcopy(template)
    d = props_by_name(rec)
    _set_str(d['SubCategoryName'], name)
    d['MenuPriority'].value = struct.pack('<f', priority)
    d['IsUndefined'].value = b'\x00'
    d['BlueprintNames'].array = ("Str", list(blueprint_names))
    return rec


def make_cat(template, sub_template, name, icon, priority, subs):
    rec = copy.deepcopy(template)
    d = props_by_name(rec)
    _set_str(d['CategoryName'], name)
    d['IconID'].value = struct.pack('<i', icon)
    d['MenuPriority'].value = struct.pack('<f', priority)
    d['IsUndefined'].flag = 0x00
    d['SubCategoryRecords'].array = ("Struct", [
        make_sub(sub_template, sname, float(i), names)
        for i, (sname, names) in enumerate(subs)
    ])
    return rec


# --------------------------------------------------------------------------
# editing
# --------------------------------------------------------------------------

def take_from_undefined(prop):
    """Empty the Undefined category and return what was in it.

    Undefined is where the game files anything it has no record for, so its
    contents are exactly the blueprints that want sorting.
    """
    taken = []
    for c in categories(prop):
        if cat_name(c) != UNDEFINED:
            continue
        for s in subs_of(c):
            taken += names_of(s)
            props_by_name(s)['BlueprintNames'].array = ("Str", [])
    return taken


def clear(prop, keep=()):
    """Empty every category except the named ones, and return what was emptied."""
    taken = []
    for c in categories(prop):
        if cat_name(c) in keep:
            continue
        for s in subs_of(c):
            taken += names_of(s)
            props_by_name(s)['BlueprintNames'].array = ("Str", [])
    return taken


def prune(prop, keep_empty=(UNDEFINED,)):
    """Drop categories and sub-categories that ended up with nothing in them."""
    kept = []
    for c in categories(prop):
        name = cat_name(c)
        subs = [s for s in subs_of(c) if names_of(s) or name in keep_empty]
        if not subs and name not in keep_empty:
            continue
        for i, s in enumerate(subs):
            props_by_name(s)['MenuPriority'].value = struct.pack('<f', float(i))
        props_by_name(c)['SubCategoryRecords'].array = ("Struct", subs)
        kept.append(c)
    _renumber(kept)
    prop.array = ("Struct", kept)


def merge(prop, placed, icons, order, sub_order):
    """Add `placed` -- {(category, sub): [names]} -- to what the save has.

    An existing category is topped up rather than duplicated, and a name that
    the save already files somewhere is left alone: the point is to add the
    new pack, not to rearrange what the player has arranged by hand.
    """
    cats = categories(prop)
    cat_tpl, sub_tpl = templates(cats)
    known = all_names(cats)
    by_name = {cat_name(c): c for c in cats}

    skipped = []
    fresh = {}
    for (cat, sub), names in placed.items():
        new = [n for n in names if n not in known]
        skipped += [n for n in names if n in known]
        if new:
            fresh[(cat, sub)] = new

    new_cats = list(cats)
    priority = float(len(new_cats))

    for cat in order:
        subs = [(s, fresh.get((cat, s), [])) for s in sub_order.get(cat, [])]
        subs = [(s, names) for s, names in subs if names]
        if not subs:
            continue

        existing = by_name.get(cat)
        if existing is None:
            new_cats.append(make_cat(cat_tpl, sub_tpl, cat,
                                     icons.get(cat, -1), priority, subs))
            priority += 1.0
            continue

        arr = subs_of(existing)
        have = {sub_name(s): s for s in arr}
        for sname, names in subs:
            if sname in have:
                d = props_by_name(have[sname])
                d['BlueprintNames'].array = ("Str", names_of(have[sname]) + names)
            else:
                arr.append(make_sub(sub_tpl, sname, float(len(arr)), names))
        props_by_name(existing)['SubCategoryRecords'].array = ("Struct", arr)

    prop.array = ("Struct", new_cats)
    return skipped


def drop(prop, target, force):
    """Remove a category. Its .sbp files stay on disk; only the menu forgets them."""
    cats = categories(prop)
    if target not in [cat_name(c) for c in cats]:
        raise SystemExit(f"the save has no category {target!r}")

    keep, dropped = [], []
    for c in cats:
        if cat_name(c) != target:
            keep.append(c)
            continue
        count = sum(len(names_of(s)) for s in subs_of(c))
        if count and not force:
            raise SystemExit(f"category {target!r} holds {count} blueprints -- "
                             f"pass --force if you really mean it")
        dropped.append((target, count))

    _renumber(keep)
    prop.array = ("Struct", keep)
    return dropped


def _renumber(cats):
    """Menu priorities run 0..n-1 with no gaps."""
    for i, c in enumerate(cats):
        props_by_name(c)['MenuPriority'].value = struct.pack('<f', float(i))
