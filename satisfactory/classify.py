"""Name/description -> (category, sub-category).

Every per-pack script this repository used to carry was the same shape: a
chain of `if "Pillar" in name: return cat, "Support"` tests, differing only in
which keywords came first. That chain is data, not code, so it lives in JSON
now (see rules/default.json) and this module is the engine that runs it.

A ruleset is:

    {"categories": [rule, ...], "subcategories": [rule, ...]}

and a rule is:

    {"name": "Support",           the category/sub-category it assigns
     "any":  ["Pillar", "Pier"],  matches if any pattern hits   (optional)
     "all":  ["THG", "2F"],       matches only if all hit       (optional)
     "none": ["Pixelart"],        never matches if one hits     (optional)
     "in":   "name",              name | description | text     (default name)
     "cat":  "THG Highway"}       sub-category rules: only inside this category

Patterns are case-insensitive substrings, or regexes when written `re:...`.
Order decides ties, so the list reads top-down like the old if-chains did:
"Support" sits above "Ends" because "Pillar End" is a pillar, and "Ends" sits
above "Straight" because "Straight End T" is an end.
"""

import collections
import json
import os
import re

RULES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rules")
DEFAULT_RULES = os.path.join(RULES_DIR, "default.json")

FALLBACK_SUB = "Misc"
FALLBACK_CAT = "Misc"


# --------------------------------------------------------------------------
# patterns
# --------------------------------------------------------------------------

def _compile(pattern):
    if pattern.startswith("re:"):
        return re.compile(pattern[3:], re.IGNORECASE)
    return re.compile(re.escape(pattern), re.IGNORECASE)


class Rule:
    __slots__ = ("name", "any", "all", "none", "field", "cat")

    def __init__(self, spec):
        if "name" not in spec:
            raise ValueError(f"rule without a name: {spec}")
        self.name = spec["name"]
        self.any = [_compile(p) for p in spec.get("any", [])]
        self.all = [_compile(p) for p in spec.get("all", [])]
        self.none = [_compile(p) for p in spec.get("none", [])]
        self.field = spec.get("in", "name")
        self.cat = spec.get("cat")
        if self.field not in ("name", "description", "text"):
            raise ValueError(f"rule {self.name!r}: bad 'in' value {self.field!r}")

    def matches(self, bp):
        text = getattr(bp, self.field)
        if any(p.search(text) for p in self.none):
            return False
        if self.all and not all(p.search(text) for p in self.all):
            return False
        if self.any:
            return any(p.search(text) for p in self.any)
        return bool(self.all)          # an 'any'-less rule needs 'all' to fire


class Ruleset:
    def __init__(self, spec):
        self.categories = [Rule(r) for r in spec.get("categories", [])]
        self.subcategories = [Rule(r) for r in spec.get("subcategories", [])]
        self.order = spec.get("order", [])            # category display order
        self.sub_order = spec.get("sub_order", {})    # per-category sub order

    def category(self, bp):
        for rule in self.categories:
            if rule.matches(bp):
                return rule.name
        return None

    def subcategory(self, bp, cat):
        for rule in self.subcategories:
            if rule.cat and rule.cat != cat:
                continue
            if rule.matches(bp):
                return rule.name
        return FALLBACK_SUB


def load(paths=None):
    """Load the default ruleset, then layer extra rule files on top.

    Layering prepends, so a user's rules win over the built-in ones without
    having to restate them.
    """
    spec = json.load(open(DEFAULT_RULES, encoding="utf-8"))
    for path in paths or []:
        path = os.path.expanduser(path)
        if not os.path.exists(path) and os.path.exists(os.path.join(RULES_DIR, path)):
            path = os.path.join(RULES_DIR, path)
        extra = json.load(open(path, encoding="utf-8"))
        spec["categories"] = extra.get("categories", []) + spec.get("categories", [])
        spec["subcategories"] = extra.get("subcategories", []) + spec.get("subcategories", [])
        spec["order"] = extra.get("order", []) + spec.get("order", [])
        merged = dict(spec.get("sub_order", {}))
        merged.update(extra.get("sub_order", {}))
        spec["sub_order"] = merged
    return Ruleset(spec)


# --------------------------------------------------------------------------
# working out a category when no rule names one
# --------------------------------------------------------------------------

WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
COLLECTION = re.compile(
    r"(?:part of|from)\s+(?:the\s+)?(.{3,40}?)\s+(?:collection|pack|series|set)\b",
    re.IGNORECASE)

# words that carry no identity -- a category named after one of these tells
# you nothing, so they never become the shared prefix
GENERIC = {"the", "a", "an", "and", "of", "for", "with", "my", "new", "old",
           "small", "big", "large", "left", "right", "up", "down", "top",
           "basic", "extended", "simple", "custom", "modern", "actually",
           "straight", "curve", "curved", "bend", "turn", "ramp", "slope",
           "wall", "floor", "roof", "station", "stations", "train", "rail",
           "rails", "road", "roads", "lane", "lanes", "way", "bridge",
           "roundabout", "junction", "tunnel", "pillar", "support", "block",
           "part", "piece", "set", "mk", "degree", "double", "single", "truck",
           "1", "2", "3", "4"}


def common_prefix(names, min_words=1):
    """The leading words every name shares, if that is a real name.

    A pack downloaded as a batch usually prefixes everything: "THG Highway
    Straight L", "THG Highway Ramp R"... -> "THG Highway".
    """
    if len(names) < 2:
        return None
    split = [WORD.findall(n)[:4] for n in names]
    if not all(split):
        return None
    shared = []
    for column in zip(*split):
        first = column[0]
        if any(w.lower() != first.lower() for w in column):
            break
        shared.append(first)
    while shared and shared[-1].lower() in GENERIC:
        shared.pop()
    if len(shared) < min_words:
        return None
    return " ".join(shared)


def collection_of(bp):
    """The collection a blueprint says it belongs to, if it says so.

    Authors write "This is Part of the Retrofuturistic Railway Collection" into
    every blueprint of a set. That is the author's own name for the group, and
    it is there even when the file names share nothing -- which makes it a
    better category than anything guessed from the file name.
    """
    found = COLLECTION.search(bp.description or "")
    return " ".join(found.group(1).split()) if found else None


def collection_name(items):
    """The one collection a batch agrees on, if a quarter of it agrees."""
    counts, titles = collections.Counter(), {}
    for bp in items:
        title = collection_of(bp)
        if title:
            counts[title.lower()] += 1
            titles.setdefault(title.lower(), title)
    if not counts:
        return None
    key, count = counts.most_common(1)[0]
    # one stray mention is not a collection; a quarter of the batch is
    return titles[key] if count >= max(2, len(items) // 4) else None


def auto_category(items, hint=None):
    """Name a category for a batch that no rule claimed."""
    for candidate in (hint,
                      collection_name(items),
                      common_prefix([bp.name for bp in items])):
        if candidate:
            return candidate.strip()
    return FALLBACK_CAT


# --------------------------------------------------------------------------

def _families(items):
    """Group by leading word, for splitting one folder into several shelves.

    A word that says nothing about which family a blueprint belongs to -- a
    part name like "Bridge", a direction, a number -- is not a family, and its
    group goes back into the pile under None.
    """
    out = {}
    for bp in items:
        words = WORD.findall(bp.name)
        first = words[0].title() if words else ""
        if len(first) < 3 or first.lower() in GENERIC:
            first = None
        out.setdefault(first, []).append(bp)
    return out


def place(items, rules, hint=None, category=None, split=False, min_group=3):
    """Sort blueprints into {(category, sub-category): [names]}.

    Each blueprint is asked, in order, until something names a category:

      1. `category`, if the caller forced one;
      2. the category rules;
      3. the collection the blueprint's own description names, when enough
         other blueprints name the same one;
      4. the batch as a whole -- `hint`, a collection its descriptions agree
         on, or the leading words its file names share;
      5. failing all that, its own leading word (with `split`) or "Misc".

    Steps 3 and 4 are why a downloaded pack needs no rules written for it: a
    pack is a set of blueprints that already say what they are.
    """
    ruled, loose = {}, []
    for bp in items:
        cat = category or rules.category(bp)
        if cat:
            ruled.setdefault(cat, []).append(bp)
        else:
            loose.append(bp)

    # 3. collections named by the blueprints themselves
    rest = []
    groups = {}
    for bp in loose:
        title = collection_of(bp)
        groups.setdefault(title.lower() if title else None, []).append(bp)
    for key, group in groups.items():
        if key is not None and len(group) >= min_group:
            ruled.setdefault(collection_of(group[0]), []).extend(group)
        else:
            rest += group

    # 4/5. whatever is left, named after the batch or split into families
    if rest:
        base = auto_category(rest, hint)
        if split:
            for family, group in sorted(_families(rest).items(),
                                        key=lambda kv: kv[0] or ""):
                if family is None or len(group) < min_group:
                    shelf = base                     # too small to be a family
                elif base == FALLBACK_CAT:
                    shelf = family                   # the batch has no name of its own
                else:
                    shelf = f"{base} {family}"
                ruled.setdefault(shelf, []).extend(group)
        else:
            ruled.setdefault(base, []).extend(rest)

    placed = {}
    for cat, group in ruled.items():
        for bp in group:
            placed.setdefault((cat, rules.subcategory(bp, cat)), []).append(bp.name)
    return placed


def order_of(placed, rules):
    """Category order and per-category sub-category order for the menu."""
    cats = sorted({c for c, _ in placed})
    ranked = sorted(cats, key=lambda c: (rules.order.index(c)
                                         if c in rules.order else len(rules.order), c))
    subs = {}
    for cat in ranked:
        want = rules.sub_order.get(cat) or rules.sub_order.get("*", [])
        here = sorted({s for c, s in placed if c == cat})
        subs[cat] = sorted(here, key=lambda s: (want.index(s) if s in want else len(want), s))
    return ranked, subs
