# satisfactory-tools

One tool for Satisfactory blueprints: download a pack, drop it into your save's
blueprint folder, and file it into real categories instead of leaving 500
blueprints in `Undefined`. Plus a couple of unrelated mod fixes.

No dependencies outside the standard library. Runs on Linux, Windows and macOS.

Everything here was written against **save version 60 (U1.1)**. Save formats
change; check before pointing it at something you care about. Save-writing
commands are a dry run until `--apply`, take a backup the first time they
write, and re-read the file afterwards to check themselves — but
**back up your save anyway**.

## Why a tool is needed at all

Blueprint categories do **not** live in the `.sbpcfg` files next to the
blueprints. They live inside the save, in the `mBlueprintCategoryRecords`
property of the `BP_GameState` object. So installing a downloaded pack is two
steps — copy the files into the blueprint folder, then rewrite the category
records — and only the second one needs a tool.

## Use

```sh
python3 sfbp.py paths                  # what it found on this machine
python3 sfbp.py list                   # the save's current layout

python3 sfbp.py sync 51246/sixsense    # download, install and file, in one go
python3 sfbp.py sync 51246/sixsense --apply

python3 sfbp.py fetch 51246/sixsense -o ~/sixsense    # just download
python3 sfbp.py organize --src ~/sixsense --apply     # just install and file
python3 sfbp.py organize --apply                      # just file what is there

python3 sfbp.py drop --cat Misc --apply               # remove a category
```

The three stages are independent, so any subset works: `fetch` only touches the
network, `organize --src` only reads the folder you point it at, and `organize`
with no `--src` files what is already installed.

Quit to the main menu before `--apply`, or the next autosave will overwrite the
edit. If the game is running the tool refuses unless you add `--main-menu` to
say the world is unloaded.

## Where your folders are

`sfbp.py paths` looks for them: `%LOCALAPPDATA%` on Windows, every Steam
library's Proton prefix on Linux, CrossOver and Whisky bottles on macOS. It
also reads the save's header to find the blueprint folder, which the game names
after the session.

Anything it gets wrong can be given directly:

```sh
python3 sfbp.py organize --save-dir "D:\...\SaveGames" --save mysave.sav \
                         --bp-dir "D:\...\SaveGames\blueprints\MySession"
```

To stop typing that, copy `config.example.json` to `config.json` (next to
`sfbp.py`, git-ignored) or to `~/.config/satisfactory-tools/config.json`. The
example holds a real Linux/Proton setup. Flags beat the config file; the config
file beats autodetection.

## How blueprints get sorted

`rules/default.json` holds the sub-category keywords — `Pillar` → Support,
`Roundabout` → Roundabout, `Curve`/`45°`/`Left 30` → Curves, and so on. Order
matters and reads top-down: `Support` sits above `Ends` because "Pillar End" is
a pillar, and `Ends` sits above `Straight` because "Straight End T" is an end.

The **category** is worked out per blueprint, in this order:

1. `--category NAME`, if you force one;
2. a category rule from `rules/*.json`;
3. the collection the blueprint's own description names — authors write
   "This is Part of the Retrofuturistic Railway Collection" into every piece of
   a set, and that is a better name than anything guessable from a filename;
4. the batch as a whole: `--category-hint`, a collection its descriptions agree
   on, or the leading words its filenames share;
5. failing all that, `Misc` — or one category per name prefix with `--split`,
   which is what a 500-blueprint folder holding a dozen families wants.

Steps 3 and 4 are why a freshly downloaded pack usually needs no rules written
for it. Category icons are not invented either: each one is the icon of the
first blueprint filed under it, read out of a real `.sbpcfg`.

Useful flags:

| flag | |
| --- | --- |
| `--scope new` | file `Undefined` plus anything on disk the save has not filed (default) |
| `--scope src` | file only what `--src` brought in |
| `--scope all` | re-file everything, discarding the current layout |
| `--split` | split an unruled batch into one category per name prefix |
| `--prune` | drop categories left empty afterwards |
| `-v` | print every blueprint and where it lands |

### Your own rules

```sh
python3 sfbp.py organize --rules myrules.json
```

Your file is checked before the built-ins, so you only write what you want to
change:

```json
{
  "categories":    [ {"name": "Big Rails", "any": ["re:^BR ", "Bigrail"]} ],
  "subcategories": [ {"name": "Turntables", "cat": "Big Rails", "any": ["Turntable"]} ],
  "order":         ["Big Rails"],
  "sub_order":     {"Big Rails": ["Straight", "Turntables", "Misc"]}
}
```

A rule matches on `any` / `all` / `none` patterns — case-insensitive
substrings, or regexes written `re:...` — against the blueprint's `name`,
`description`, or `text` (both). A sub-category rule with `cat` only applies
inside that category.

`rules/packs.json` is a worked example: the layouts for TheHighwayGuy,
sixsense, Swarley, EnderpriseArchitecture, Hornslet, SeaShark, Svosh and the
road/rail sets, which this repository used to carry as one `organize_<pack>.py`
script each.

## Layout

| path | |
| --- | --- |
| `sfbp.py` | the CLI: `paths`, `list`, `fetch`, `organize`, `sync`, `drop` |
| `satisfactory/save.py` | the save container: read, splice, write, verify |
| `satisfactory/categories.py` | the `mBlueprintCategoryRecords` property |
| `satisfactory/blueprints.py` | `.sbp`/`.sbpcfg` pairs on disk |
| `satisfactory/classify.py` | name/description → category, sub-category |
| `satisfactory/paths.py` | finding the game's folders, per platform |
| `satisfactory/fetch.py` | downloading from satisfactory-calculator.com |
| `rules/` | the keyword rules |
| `mods/` | the mod fixes below |

## Mod fixes

Two unrelated mod problems that turned out to be fixable from the outside.

**`mods/hf-setting.py` / `mods/hf-unhalve.py` — HeavyFluids 1.4.5.** SML session
settings live in the save, and `hf-setting.py` edits them there:

```sh
python3 mods/hf-setting.py cachys.sav                              # show all
python3 mods/hf-setting.py cachys.sav HeavyFluids.Pipeline.Limit off
python3 mods/hf-setting.py cachys.sav HeavyFluids.Divider.Main 3
```

"Half Pipeline Flow Capacity" is the exception: SML does not apply that one from
the save and reverts it to the mod's own default of `true`. It has to be fixed
in the mod instead — `hf-unhalve.py` patches the helper that reads the setting
so it always returns `false`, which kills the halving at every call site.

**`mods/pmk3-fiximport.py` — PipelineMk3Plus 1.0.0.** Built against Satisfactory
CL 383729, will not load on CL 502094. Exactly one unresolved import from Core:

```
old  ?GetBlocks@FNameDebugVisualizer@@SAPEAPEAEXZ    (static)
new  ?GetBlocks@FNameDebugVisualizer@@QEAAPEAPEAEXZ  (non-static method)
```

The script rewrites that import name in the binary. A mangled-name swap is only
safe because the two differ in calling convention but not in what the code does
with the result.

## License

MIT
