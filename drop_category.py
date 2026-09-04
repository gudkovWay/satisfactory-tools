#!/usr/bin/env python3
"""Удалить категорию блюпринтов из сейва (по умолчанию — пустую Undefined).

    python3 drop_category.py                                # dry run
    python3 drop_category.py --apply --main-menu
    python3 drop_category.py --cat Misc --save каша_autosave_0.sav --apply

Непустую категорию удалить не даст без --force (её блюпринты просто исчезнут
из меню; сами .sbp останутся на диске).
"""

import os
import shutil
import struct
import sys

import satisfactory_bp as S
import organize_blueprints as O
import organize_sixsense as X

SAVE_DEFAULT = "cachys.sav"
BACKUP_SUFFIX = ".bak-predrop"

props_by_name = O.props_by_name


def bp_count(cat):
    return sum(len(props_by_name(s)['BlueprintNames'].array[1])
               for s in props_by_name(cat)['SubCategoryRecords'].array[1])


def drop(prop, target, force):
    kind, cats = prop.array
    assert kind == "Struct"

    if target not in [X.cat_name(c) for c in cats]:
        raise SystemExit(f"в сейве нет категории {target!r}")

    keep, dropped = [], []
    for c in cats:
        if X.cat_name(c) == target:
            n = bp_count(c)
            if n and not force:
                raise SystemExit(f"в категории {target!r} лежит {n} блюпринтов — "
                                 f"добавь --force, если правда надо удалить")
            dropped.append((target, n))
            continue
        keep.append(c)

    # приоритеты меню пересчитываем подряд, чтобы не осталось дырки
    for i, c in enumerate(keep):
        props_by_name(c)['MenuPriority'].value = struct.pack('<f', float(i))

    prop.array = ("Struct", keep)
    return dropped


def main():
    apply_changes = "--apply" in sys.argv
    force = "--force" in sys.argv
    target = sys.argv[sys.argv.index("--cat") + 1] if "--cat" in sys.argv else "Undefined"
    SAVE = X.pick_save(sys.argv) if "--save" in sys.argv \
        else os.path.join(O.SAVEDIR, SAVE_DEFAULT)

    if apply_changes and X.game_running() and "--main-menu" not in sys.argv:
        raise SystemExit("Satisfactory запущен. Выйди в главное меню (мир должен быть "
                         "выгружен) и добавь --main-menu, иначе автосейв затрёт правку.")

    print(f"== {os.path.basename(SAVE)} ==")
    header, body, _ = S.read_save(SAVE)
    loc = S.locate(body)
    prop = S.read_categories(body, loc)
    print(f"  разобран, round-trip точный ({loc.prop_end - loc.prop_off} байт)")

    dropped = drop(prop, target, force)
    for name, n in dropped:
        print(f"  удаляю категорию {name!r} ({n} блюпринтов)")

    print("\n== раскладка ==")
    O.dump(prop)

    new_bytes = S.write_props([prop], terminate=True)
    new_body, delta = S.splice(body, loc, new_bytes)
    print(f"\n  тело {len(body)} -> {len(new_body)} ({delta:+d} байт)")

    S.verify(new_body)
    loc2 = S.locate(new_body)
    if S.write_props([S.read_categories(new_body, loc2)], terminate=True) != new_bytes:
        raise SystemExit("re-parse mismatch")
    print("  проверено: секции целы, свойство перечитывается идентично")

    if not apply_changes:
        print("\nDry run. Для записи: python3 drop_category.py --apply --main-menu")
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
