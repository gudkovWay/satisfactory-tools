#!/usr/bin/env python3
"""sfbp -- fetch, install and file Satisfactory blueprints.

Blueprint categories do not live next to the blueprints. They live inside the
save, in `mBlueprintCategoryRecords` on BP_GameState, which is why installing
a downloaded pack is two steps: copy the files into the blueprint folder, then
rewrite the category records. This does both.

    sfbp.py paths                                  what it found on this machine
    sfbp.py list                                   the save's current layout
    sfbp.py fetch 51246/sixsense -o ~/sixsense     download a pack
    sfbp.py organize --src ~/sixsense              install it and file it
    sfbp.py organize                               file what is already there
    sfbp.py sync 51246/sixsense                    fetch, install and file, in one
    sfbp.py drop --cat Misc --apply                remove a category

Every save-writing command is a dry run until `--apply`, takes a backup the
first time it writes, and re-reads the file afterwards to check itself.

Nothing outside the standard library. Written against save version 60 (U1.1);
save formats change, so check before pointing it at something you care about.
"""

import argparse
import json
import os
import shutil
import sys

from satisfactory import blueprints as B
from satisfactory import categories as C
from satisfactory import classify
from satisfactory import fetch
from satisfactory import paths
from satisfactory import save as S

CONFIG_NAMES = ["config.json",
                os.path.join("~", ".config", "satisfactory-tools", "config.json")]
BACKUP_SUFFIX = ".bak-sfbp"


# --------------------------------------------------------------------------
# configuration: flags beat the config file, the config file beats autodetection
# --------------------------------------------------------------------------

def load_config(explicit=None):
    candidates = [explicit] if explicit else CONFIG_NAMES
    for name in candidates:
        path = os.path.expanduser(name)
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return {k: v for k, v in json.load(f).items()
                        if not k.startswith("_")}
    if explicit:
        raise SystemExit(f"no such config file: {explicit}")
    return {}


class Target:
    """The save being worked on, and the folders around it."""

    def __init__(self, args):
        cfg = load_config(getattr(args, "config", None))
        self.save_dir = paths.save_dir(
            getattr(args, "save_dir", None) or cfg.get("save_dir"))

        name = getattr(args, "save", None) or cfg.get("save")
        if name:
            self.save = paths.find_save(self.save_dir, name)
        else:
            found = paths.saves(self.save_dir)
            if not found:
                raise SystemExit(f"no saves under {self.save_dir}")
            self.save = max(found, key=os.path.getmtime)   # the one last played

        self.header = S.read_header(self.save)
        self.session = self.header.get("sessionName") or self.header.get("saveName")
        self.bp_dir = paths.blueprint_dir(
            self.save_dir, self.session,
            getattr(args, "bp_dir", None) or cfg.get("bp_dir"))
        self.rules = classify.load(
            list(getattr(args, "rules", None) or cfg.get("rules", [])))

    def describe(self):
        return (f"  save     {self.save}\n"
                f"  session  {self.session}  (save v{self.header['saveVersion']}, "
                f"build {self.header['buildVersion']})\n"
                f"  blueprints {self.bp_dir}")


# --------------------------------------------------------------------------
# the read/edit/verify/write cycle every save-touching command shares
# --------------------------------------------------------------------------

def edit_save(target, args, mutate):
    """Parse the save, let `mutate(prop, cats)` change it, verify, maybe write.

    The property is re-serialised and compared byte-for-byte against the
    original before anything is changed, and the rewritten body is re-parsed
    from scratch afterwards. A save that does not survive both checks is left
    alone.
    """
    apply_changes = args.apply
    if apply_changes and paths.game_running() and not args.main_menu:
        raise SystemExit(
            "Satisfactory is running. Go back to the main menu so the world is "
            "unloaded and add --main-menu, or the next autosave overwrites this.")

    print(f"== {os.path.basename(target.save)} ==")
    header, body, _ = S.read_save(target.save)
    loc = S.locate(body)
    prop = S.read_categories(body, loc)
    print(f"  parsed, round-trip exact ({loc.prop_end - loc.prop_off} bytes)")

    mutate(prop)

    print("\n== layout ==")
    dump(prop)

    new_bytes = S.write_props([prop], terminate=True)
    new_body, delta = S.splice(body, loc, new_bytes)
    print(f"\n  body {len(body)} -> {len(new_body)} ({delta:+d} bytes)")

    S.verify(new_body)
    loc2 = S.locate(new_body)
    if S.write_props([S.read_categories(new_body, loc2)], terminate=True) != new_bytes:
        raise SystemExit("re-parse mismatch -- refusing to write")
    print("  verified: object framing intact, property re-parses identically")

    if not apply_changes:
        print("\nDry run. Add --apply to write.")
        return

    backup = target.save + BACKUP_SUFFIX
    if not os.path.exists(backup):
        shutil.copy2(target.save, backup)
        print(f"\n  backup -> {os.path.basename(backup)}")
    size = S.write_save(target.save, header, new_body)
    print(f"  written: {size} bytes")

    _, check, _ = S.read_save(target.save)
    if check != new_body:
        raise SystemExit("readback mismatch!")
    S.verify(check)
    print("  readback OK")


def dump(prop):
    for name, icon, subs in C.layout(prop):
        total = sum(len(names) for _, names in subs)
        print(f"  {name}  (icon {icon}, {total} bp)")
        for sub, names in subs:
            print(f"      {sub:<14} {len(names):>4}")


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_paths(args):
    found = paths.save_dirs()
    print("SaveGames folders:")
    for d in found or ["  (none found -- pass --save-dir)"]:
        print(f"  {d}")
    for d in found:
        for bp in paths.blueprint_dirs(d):
            count = len([f for f in os.listdir(bp) if f.endswith(B.SBP)])
            print(f"  blueprints: {bp}  ({count})")
        for sav in paths.saves(d):
            print(f"  save:       {sav}")
    print(f"\ngame running: {paths.game_running()}")


def cmd_list(args):
    target = Target(args)
    print(target.describe())
    _, body, _ = S.read_save(target.save)
    prop = S.read_categories(body, S.locate(body))
    print("\n== layout ==")
    dump(prop)

    on_disk = {bp.name for bp in B.installed(target.bp_dir)}
    filed = C.all_names(C.categories(prop))
    missing = sorted(filed - on_disk)
    unfiled = sorted(on_disk - filed)
    if missing:
        print(f"\n  filed but not on disk ({len(missing)}): {', '.join(missing[:12])}"
              + (" ..." if len(missing) > 12 else ""))
    if unfiled:
        print(f"\n  on disk but not filed ({len(unfiled)}): {', '.join(unfiled[:12])}"
              + (" ..." if len(unfiled) > 12 else ""))


def cmd_fetch(args):
    if args.list_only:
        id_user, user = fetch.parse_target(args.target)
        for bp_id, slug in fetch.collect(id_user, user, args.delay):
            print(f"  {bp_id}  {fetch.safe_name(slug)}")
        return None

    outdir, ok, skipped, failed = fetch.download_user(
        args.target, args.outdir, args.delay, args.force, not args.no_cfg)
    print(f"\ndownloaded {ok}, already had {skipped}, failed {failed} "
          f"-> {os.path.abspath(outdir)}")
    return outdir


def collect_sources(target, args, extra_dirs=()):
    """The blueprints to file: the sources given, plus what is already installed."""
    srcs = [os.path.expanduser(s) for s in (args.src or [])] + list(extra_dirs)
    incoming = B.scan(srcs, warn=lambda m: print(f"  ! {m}")) if srcs else []

    added, present = B.install(incoming, target.bp_dir, args.apply)
    if incoming:
        verb = "installed" if args.apply else "would install"
        print(f"  {verb} {len(added)}"
              + (f", already there {len(present)}" if present else ""))
    return incoming, added


def cmd_organize(args, extra_dirs=()):
    target = Target(args)
    print(target.describe())

    print("\n== blueprints ==")
    incoming, added = collect_sources(target, args, extra_dirs)

    def mutate(prop):
        if args.scope == "all":
            C.clear(prop, keep=())
        elif args.scope != "src":                    # "new": Undefined and unfiled
            C.take_from_undefined(prop)

        pool = list(incoming)
        seen = {bp.name for bp in pool}
        if args.scope != "src":
            # whatever the save no longer accounts for, plus anything sitting
            # in the blueprint folder that it never knew about
            filed = C.all_names(C.categories(prop))
            for bp in B.installed(target.bp_dir):
                if bp.name not in seen and bp.name not in filed:
                    pool.append(bp)
                    seen.add(bp.name)

        if not pool:
            print("\n  nothing to file")
            return

        placed = classify.place(pool, target.rules, hint=args.category_hint,
                                category=args.category, split=args.split)
        order, sub_order = classify.order_of(placed, target.rules)
        icons = pick_icons(placed, {bp.name: bp for bp in pool})

        print(f"\n  filing {sum(len(v) for v in placed.values())} blueprints "
              f"into {len(order)} categories")
        for cat in order:
            for sub in sub_order[cat]:
                names = placed.get((cat, sub), [])
                if names and args.verbose:
                    print(f"    {cat}/{sub}: {', '.join(names)}")

        skipped = C.merge(prop, placed, icons, order, sub_order)
        if skipped:
            print(f"\n  already filed, left alone ({len(skipped)})")
        if args.prune:
            C.prune(prop)

    edit_save(target, args, mutate)


def pick_icons(placed, by_name):
    """A category's icon is the icon of the first blueprint in it.

    Icon ids are taken from real .sbpcfg files rather than invented, so they
    are always ones the game knows how to draw.
    """
    icons = {}
    for (cat, _), names in sorted(placed.items()):
        if cat in icons:
            continue
        for name in names:
            bp = by_name.get(name)
            if bp and bp.icon >= 0:
                icons[cat] = bp.icon
                break
    return icons


def cmd_sync(args):
    outdir = args.outdir
    if not outdir:
        _, user = fetch.parse_target(args.target)
        outdir = os.path.join(os.path.expanduser("~"), fetch.safe_name(user))
    print("== download ==")
    fetch.download_user(args.target, outdir, args.delay, args.force,
                        log=lambda m: print(m))
    if args.category_hint is None:
        args.category_hint = os.path.basename(os.path.normpath(outdir))
    print()
    cmd_organize(args, extra_dirs=[outdir])


def cmd_drop(args):
    target = Target(args)
    print(target.describe())
    print()

    def mutate(prop):
        for name, count in C.drop(prop, args.cat, args.force):
            print(f"  dropping {name!r} ({count} blueprints)")

    edit_save(target, args, mutate)


# --------------------------------------------------------------------------

def add_save_args(p):
    p.add_argument("--config", help="config file (default: ./config.json)")
    p.add_argument("--save-dir", help="the SaveGames folder")
    p.add_argument("--save", help="save name, file name, or path "
                                  "(default: the most recently played)")
    p.add_argument("--bp-dir", help="blueprint folder "
                                    "(default: the one named after the session)")


def add_write_args(p):
    p.add_argument("--apply", action="store_true", help="actually write; "
                                                        "without it, dry run")
    p.add_argument("--main-menu", action="store_true",
                   help="the game is open but the world is unloaded")


def add_organize_args(p):
    p.add_argument("--src", action="append", metavar="PATH",
                   help="folder of .sbp files, or one .sbp; repeatable")
    p.add_argument("--rules", action="append", metavar="FILE",
                   help="extra rule file, checked before the built-ins; repeatable")
    p.add_argument("--category", help="put everything in this category, "
                                      "bypassing the category rules")
    p.add_argument("--category-hint", metavar="NAME",
                   help="name to fall back on when nothing else names a category")
    p.add_argument("--split", action="store_true",
                   help="split a big unruled batch into one category per name "
                        "prefix instead of one big one")
    p.add_argument("--scope", choices=["new", "src", "all"], default="new",
                   help="what to file: new = Undefined and anything unfiled "
                        "(default), src = only what --src brought, "
                        "all = re-file everything, discarding the current layout")
    p.add_argument("--prune", action="store_true",
                   help="drop categories left empty afterwards")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="list every blueprint and where it lands")


def main():
    ap = argparse.ArgumentParser(
        prog="sfbp.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("paths", help="show the folders found on this machine")
    p.set_defaults(func=cmd_paths)

    p = sub.add_parser("list", help="show a save's current blueprint layout")
    add_save_args(p)
    p.add_argument("--rules", action="append", help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("fetch", help="download a user's blueprints")
    p.add_argument("target", help="listing URL, or 'userId/username'")
    p.add_argument("-o", "--outdir", help="where to put them (default ./<username>)")
    p.add_argument("-d", "--delay", type=float, default=1.0,
                   help="seconds between requests (default 1.0)")
    p.add_argument("-f", "--force", action="store_true", help="re-download")
    p.add_argument("--no-cfg", action="store_true",
                   help="skip the .sbpcfg files (the game will not show them)")
    p.add_argument("--list-only", action="store_true",
                   help="print what is published, download nothing")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("organize", help="install blueprints and file them in a save")
    add_save_args(p)
    add_organize_args(p)
    add_write_args(p)
    p.set_defaults(func=cmd_organize)

    p = sub.add_parser("sync", help="fetch, install and file, in one go")
    p.add_argument("target", help="listing URL, or 'userId/username'")
    p.add_argument("-o", "--outdir", help="where to download to (default ~/<username>)")
    p.add_argument("-d", "--delay", type=float, default=1.0)
    p.add_argument("-f", "--force", action="store_true")
    add_save_args(p)
    add_organize_args(p)
    add_write_args(p)
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("drop", help="remove a category from a save")
    add_save_args(p)
    p.add_argument("--cat", default=C.UNDEFINED, help="category to remove "
                                                      "(default: Undefined)")
    p.add_argument("--force", action="store_true",
                   help="remove it even if blueprints are filed under it")
    p.add_argument("--rules", action="append", help=argparse.SUPPRESS)
    add_write_args(p)
    p.set_defaults(func=cmd_drop)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\ninterrupted")
