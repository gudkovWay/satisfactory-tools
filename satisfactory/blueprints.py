"""Blueprints on disk: the .sbp/.sbpcfg pairs.

A blueprint is two files with the same stem. The .sbp holds the build itself;
the .sbpcfg holds what the menu shows -- description, icon, colour. The game
ignores an .sbp with no .sbpcfg next to it, so they always travel together.

.sbpcfg layout (the part that matters, stable across config versions 0/4/6):

    int32   config version
    int32   description length
    byte[]  description, UTF-8
    int32   icon id
    ...     colour, icon library, and (v4+) trailing fields we do not touch
"""

import os
import shutil
import struct

SBP = ".sbp"
CFG = ".sbpcfg"


class Blueprint:
    """One .sbp/.sbpcfg pair, with whatever the cfg tells us about it."""

    __slots__ = ("name", "sbp", "cfg", "description", "icon")

    def __init__(self, name, sbp, cfg, description="", icon=-1):
        self.name = name
        self.sbp = sbp
        self.cfg = cfg
        self.description = description
        self.icon = icon

    @property
    def text(self):
        """Name and description together -- what the rules match against."""
        return f"{self.name}\n{self.description}"

    def __repr__(self):
        return f"<Blueprint {self.name!r}>"


def read_cfg(path):
    """-> (description, icon id). Anything unreadable degrades to ("", -1)."""
    try:
        data = open(path, "rb").read()
        length = struct.unpack_from("<i", data, 4)[0]
        if not 0 <= length <= len(data) - 8:
            return "", -1
        desc = data[8:8 + length].decode("utf-8", "replace").rstrip("\x00")
        icon = struct.unpack_from("<i", data, 8 + length)[0]
        return desc, icon
    except (OSError, struct.error, IndexError):
        return "", -1


def scan(sources, warn=None):
    """Every complete blueprint under the given files or folders.

    A source is a folder to walk or a single .sbp to take. An .sbp without its
    .sbpcfg is reported through `warn` and skipped -- the game would not see it.
    """
    paths = []
    for src in sources:
        src = os.path.expanduser(src)
        if os.path.isdir(src):
            paths += [os.path.join(src, f) for f in sorted(os.listdir(src))
                      if f.endswith(SBP)]
        elif src.endswith(SBP) and os.path.exists(src):
            paths.append(src)
        else:
            raise SystemExit(f"not a .sbp file or a folder: {src}")

    out, seen = [], set()
    for path in paths:
        cfg = path[:-len(SBP)] + CFG
        name = os.path.basename(path)[:-len(SBP)]
        if not os.path.exists(cfg):
            if warn:
                warn(f"{name}: no {CFG} alongside, skipped")
            continue
        if name in seen:                       # same blueprint from two sources
            continue
        seen.add(name)
        desc, icon = read_cfg(cfg)
        out.append(Blueprint(name, path, cfg, desc, icon))
    return out


def installed(bpdir):
    """The blueprints already sitting in a save's blueprint folder."""
    if not os.path.isdir(bpdir):
        return []
    return scan([bpdir])


def install(items, bpdir, apply_changes):
    """Copy pairs into the save's blueprint folder. -> (added, already there)."""
    added, present = [], []
    for bp in items:
        if os.path.exists(os.path.join(bpdir, bp.name + SBP)):
            present.append(bp)
            continue
        if apply_changes:
            os.makedirs(bpdir, exist_ok=True)
            for src in (bp.sbp, bp.cfg):
                shutil.copy2(src, os.path.join(bpdir, os.path.basename(src)))
        added.append(bp)
    return added, present
