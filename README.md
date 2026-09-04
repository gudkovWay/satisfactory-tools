# satisfactory-tools

Python tools for Satisfactory save files and mods, written while sorting out a
save that had accumulated a few hundred blueprints. No dependencies outside the
standard library.

Everything here was written against **save version 60 (U1.1)**. Save formats
change; check before pointing these at something you care about.

**Back up your save first.** These rewrite it in place.

## Blueprint categories

The interesting fact that makes all of this possible: blueprint categories do
**not** live in the `.sbpcfg` files next to the blueprints. They live inside the
save, in the `mBlueprintCategoryRecords` property of the `BP_GameState` object.
So installing a downloaded blueprint pack is two steps — copy the files into the
blueprints folder, then rewrite the category records — and only the second step
needs a tool.

| file | what it does |
| --- | --- |
| `satisfactory_bp.py` | the parser/writer: reads the save, rewrites `mBlueprintCategoryRecords`, writes it back. Everything else builds on this. |
| `organize_blueprints.py` | category/sub-category helpers (`make_cat`, `make_sub`, `props_by_name`, `icon_of`) on top of it |
| `organize_sixsense.py` | pack installation (`install_pack`, `pick_save`, `game_running`) plus its own pack layout |
| `drop_category.py` | delete a category (default: the empty `Undefined`). Dry run unless `--apply`. |

```sh
python3 drop_category.py                                   # dry run
python3 drop_category.py --apply --main-menu
python3 drop_category.py --cat Misc --save my_autosave_0.sav --apply
```

## Pack organisers

`organize_highway.py`, `organize_packs.py`, `organize_rails.py`,
`organize_svosh.py`, `organize_trains.py` — one per downloaded blueprint pack
(TheHighwayGuy, Swarley, EnderpriseArchitecture, Hornslet, SeaShark, Svosh…),
each laying its pack out into the categories it deserves.

These are **worked examples, not a library**. They carry the specific category
layout of specific packs and a specific save name. Read one and adapt it; that
is faster than a configuration format would be.

The modules import each other flat (`import satisfactory_bp as S`,
`import organize_blueprints as O`, `import organize_sixsense as X`), so they all
have to sit in one directory. That is why this repository has no `src/`.

## Downloading blueprints

`sc_blueprints.py` fetches every blueprint a user has published on
satisfactory-calculator.com.

```sh
python3 sc_blueprints.py "https://satisfactory-calculator.com/en/blueprints/index/index/idU/51246/user/sixsense"
python3 sc_blueprints.py 51246/sixsense -o ./blueprints
```

## Mod fixes

Two unrelated mod problems that turned out to be fixable from the outside.

**`hf-setting.py` / `hf-unhalve.py` — HeavyFluids 1.4.5.** SML session settings
live in the save, and `hf-setting.py` edits them there:

```sh
python3 hf-setting.py cachys.sav                              # show all settings
python3 hf-setting.py cachys.sav HeavyFluids.Pipeline.Limit off
python3 hf-setting.py cachys.sav HeavyFluids.Divider.Main 3
```

"Half Pipeline Flow Capacity" is the exception: SML does not apply that one from
the save and reverts it to the mod's own default of `true`. It has to be fixed
in the mod instead — `hf-unhalve.py` patches the helper that reads the setting
so it always returns `false`, which kills the halving at every call site.

**`pmk3-fiximport.py` — PipelineMk3Plus 1.0.0.** Built against Satisfactory
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
