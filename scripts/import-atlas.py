#!/usr/bin/env python3
"""Deterministic import of the frozen factory atlas into the portal contract.

The frozen atlas is an input only. This script never edits it, never copies raw
save binaries or journals, and never publishes private absolute source paths.

Usage:
    python3 scripts/import-atlas.py --source /absolute/path/to/factory_atlas
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "public" / "atlas"

SAVE_ID = "cachys"
PROJECT_ID = "modular-engine-100"
MOD_COUNT = 86
BASE_COMMIT = "7056eb01bda5801babde77970765ab81e0965130"
SOURCE_LABEL = "Сессия 01a15ec1: полный атлас зон"
SNAPSHOT_LABEL = "Последний атлас: 52 вида зон и 49 размерных чертежей"
SOURCE_CUTOFF = "2026-10-21T22:55:36.810Z"
SOURCE_SESSION = "01a15ec1-ca39-7011-9809-de1d3190eccd"
NEWER_SAVE_WARNING = (
    "После этого расчёта появился новый сейв с меткой CALCULATOR. "
    "В исходной сессии 22 октября изменены настройки стоимости и энергии, "
    "а ранние Mk.3/Mk.5 вынесены в отдельную работу. Этот атлас ещё не пересчитан "
    "под новый сейв: числа относятся к зафиксированному исходному срезу."
)

# Hashes of the frozen inputs this importer understands. A different atlas is
# not silently substituted: it is an explicit source failure.
EXPECTED_INPUTS = {
    "data/plan.json": "7f9a8a6f6fea3956d22fb63a4faf10c1a3f7cfa12500add4a0fcd08517ca239b",
    "data/construction.json": "3b7fa99ef933ecdd23784be1fdc2f9ccfaa8b2e910a9b3d52e6b087cee9672e7",
    "data/ownership.json": "0d33a2ab67cd1b23d4ca66b105f5268df0fe28ce51a3bc56851f094968255562",
    "data/parts.json": "179c02c3f62d6a4e92c40272ce05abd9c3042e4aef4ee9c6d895f779892a79cc",
    "data/analysis.json": "1e4d6771b75a9e4935c0031b09dbcd9928f5a4488c255eeece2b302bd7f77f5b",
    "data/recipes.json": "5c9f9e9ff9166f59fa872b78fe8f450cdea6461fb529628f5841f710252c9ffb",
    "data/world.json": "36eb9fbdab58e9a7ba761b4ae3ec5d72df7a2598191b13ff683520520f5c5bb0",
    "site/atlas.js": "3bbafb7962702747a1c3f79b6d2e218e0804e2b61056824ca9491fe1b6ca18d9",
    "site/build-manifest.json": "cf7871abf082a09c9b096b1e0b99862d1a5e82fbd2f3665756c453976a9ec1c0",
    "site/verification.json": "3bda7b621123ea0029b1a0d8a10a846fdaa4f541979b8406378a072399067d40",
    "site/downloads/marker.json": "9e40a3930f02c05bb619c25bf7c8cc8d6caa1dd76da7125fa6d6111d0fa81b51",
    "site/maps/world-terrain.jpg": "8c8b653c7b2bcebf950e027b26cce87f566a56a281e4a9720e2f7b4df2ab4979",
    "site/visuals/F1-built-concept.webp": "61687d0dca90869ab0cfe2f03d719457a732909aefc325bbf027b939f2a8e4dc",
    "site/visuals/provenance.json": "7a918939f91721838cb70a16a983d3a7d0b36c37ac4fc61b45d94d359c74164b",
    "data/zones.json": "d0f1ccee31fc0702a07b6ae3fc3a94a64fb8bc52a8e2534fe1a56e715a17dd2a",
    "site/visuals/zone-provenance.json": "5e7fc846bfea40ee766a9a91547010613429c944da2547a4f1daad0e99ab3600",
    "site/visuals/references/sources.json": "fd0519e4130d6e190999edb10817e44521f2e322510533714523a05feb966039",
    "zones.py": "94f529c007d3926340daaba6b8141b1fcc62640126b343b3aa6208912c7c7df9",
}

REQUIRED_DIRS = ("site/drawings", "site/renders")

WORLD_BOUNDS = [-3246.98832031, 4253.01832031, -3750.0, 3750.0]
REGION_BOUNDS = [1100.0, 3700.0, -2050.0, 250.0]
SITE_BOUNDS = [1100.0, 3100.0, -1600.0, -200.0]

PRIVATE_MARKERS = (
    "/home/",
    "SteamLibrary",
    "drive_c",
    "AppData",
    "Saved/SaveGames",
    "/Users/",
    "C:\\",
    ".sav",
)

VOLUME_LEVELS = ("F1", "F2", "F3", "RF")
ANGLE_FILES = (("", "ЮВ", "юго-востока"),
               ("-90", "СВ", "северо-востока"),
               ("-180", "СЗ", "северо-запада"),
               ("-270", "ЮЗ", "юго-запада"))

STAGE_LEVEL_MAP = (
    [],
    ["T0", "F1", "RF"],
    [],
    ["RF"],
    ["T0", "F1"],
    ["T1", "F2"],
    ["T2", "F3"],
    [],
    ["ROOF"],
    [],
)

STAGE_DRAWING_MAP = (
    ["site"],
    ["floor-T0", "floor-F1", "floor-RF"],
    [],
    ["floor-RF"],
    ["floor-T0", "floor-F1"],
    ["floor-T1", "floor-F2"],
    ["floor-T2", "floor-F3"],
    ["site"],
    ["floor-ROOF"],
    [],
)

STAGE_MATERIALS = {
    1: ["FND", "BASE"],
    3: ["PIPE", "SPLIT"],
    7: ["BUF"],
    8: ["GLS", "WALL", "BEAM", "GATE", "DOOR", "ARCH", "RGL", "STAIR", "LIGHT", "REAL_LIGHT", "SIGN"],
}

PROCESS_NOTE_RE = re.compile(r"^\s*(P\d{2}):'(.*)'\s*,?\s*$")


class ImportSourceError(RuntimeError):
    """Explicit, user-facing source or contract failure."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def pretty_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def cell(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(cell(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def note(title: str, body: str) -> dict[str, str]:
    return {"title": title, "body": body}


def table(caption: str, columns: list[str], rows: list[list[Any]]) -> dict[str, Any]:
    return {
        "caption": caption,
        "columns": columns,
        "rows": [[cell(value) for value in row] for row in rows],
    }


def load_json_input(root: Path, rel: str) -> Any:
    path = root / rel
    if not path.is_file():
        raise ImportSourceError(f"missing required source file: {rel}")
    expected = EXPECTED_INPUTS[rel]
    actual = sha256_file(path)
    if actual != expected:
        raise ImportSourceError(
            f"source hash mismatch for {rel}: expected {expected}, got {actual}"
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ImportSourceError(f"{rel} is not valid UTF-8: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ImportSourceError(f"{rel} is not valid JSON: {exc}") from exc


def validate_source_root(root: Path) -> None:
    if not root.is_dir():
        raise ImportSourceError(f"source root does not exist or is not a directory: {root}")
    missing = [rel for rel in EXPECTED_INPUTS if not (root / rel).is_file()]
    missing += [rel for rel in REQUIRED_DIRS if not (root / rel).is_dir()]
    if missing:
        raise ImportSourceError("missing required source paths: " + ", ".join(missing))


def read_process_notes(atlas_js: Path) -> dict[str, str]:
    notes: dict[str, str] = {}
    for line in atlas_js.read_text(encoding="utf-8").splitlines():
        match = PROCESS_NOTE_RE.match(line)
        if not match:
            continue
        notes[match.group(1)] = match.group(2).replace("\\'", "'").replace("\\\\", "\\")
    if sorted(notes) != [f"P{index:02d}" for index in range(1, 21)]:
        raise ImportSourceError("legacy atlas process notes are incomplete; refused to invent notes")
    return notes


def _numbers_equal(left: float, right: float) -> bool:
    return abs(left - right) <= max(1e-6, abs(right) * 1e-8)


def validate_domain(plan: dict[str, Any], recipes: dict[str, Any], ownership: dict[str, Any],
                    construction: dict[str, Any], parts: dict[str, Any]) -> None:
    recipes_by_id = {item["id"]: item for item in recipes["recipes"]}
    allowed = {"smelter", "constructor", "foundry", "assembler", "manufacturer", "refinery", "packager"}

    if plan.get("target") != 100:
        raise ImportSourceError("plan target is not 100; the frozen source no longer matches this importer")
    if len(plan["levels"]) != 8:
        raise ImportSourceError("expected 8 level records in the frozen plan")
    if len(plan["construction"]["construction_steps"]) != 10:
        raise ImportSourceError("expected 10 construction stages in the frozen plan")
    if len(plan["processes"]) != 20:
        raise ImportSourceError("expected 20 production groups in the frozen plan")
    if len(plan["placements"]) != 48:
        raise ImportSourceError("expected 48 placements in the frozen plan")
    if len(plan["streams"]) != 40:
        raise ImportSourceError("expected 40 infrastructure streams in the frozen plan")
    if len(plan["comparisons"]) != 23:
        raise ImportSourceError("expected 23 recipe comparison groups in the frozen plan")
    if len(parts["parts"]) != 20:
        raise ImportSourceError("expected 20 parts in the frozen parts bill")

    for process in plan["processes"]:
        recipe = recipes_by_id.get(process["recipe_path"])
        if recipe is None:
            raise ImportSourceError(
                f"{process['id']}: recipe path is absent from recipes.json: {process['recipe_path']}"
            )
        if recipe.get("class_name") != process["recipe_key"]:
            raise ImportSourceError(
                f"{process['id']}: recipe class does not match path "
                f"({recipe.get('class_name')} != {process['recipe_key']})"
            )
        if recipe.get("machine") not in allowed:
            raise ImportSourceError(f"{process['id']}: unknown machine class {recipe.get('machine')}")
        if not _numbers_equal(recipe["duration"], process["duration_s"]):
            raise ImportSourceError(f"{process['id']}: recipe duration disagrees with plan")
        for kind in ("inputs", "outputs"):
            for item_id, rate in process[kind].items():
                coefficient = recipe[kind].get(item_id)
                if coefficient is None:
                    raise ImportSourceError(f"{process['id']}: {kind} item {item_id} absent in recipe")
                expected = coefficient * process["cycles_min"]
                if not _numbers_equal(rate, expected):
                    raise ImportSourceError(
                        f"{process['id']}: {kind} {item_id} rate {rate} != coefficient {expected}"
                    )
        clock = process["cycles_min"] * process["duration_s"] / (
            60.0 * process["machines"] * 10.0
        )
        if not _numbers_equal(process["clock"], clock):
            raise ImportSourceError(f"{process['id']}: clock does not match cycles/duration formula")
        if not (0.0 < process["clock"] <= 1.0):
            raise ImportSourceError(f"{process['id']}: clock outside (0, 1]")
        if sum(1 for placement in plan["placements"] if placement["process"] == process["id"]) != process["machines"]:
            raise ImportSourceError(f"{process['id']}: placement count does not match machine count")

    level_ids = {level["id"] for level in plan["levels"]}
    for placement in plan["placements"]:
        if placement["floor"] not in level_ids:
            raise ImportSourceError(f"{placement['id']}: unknown floor {placement['floor']}")
        if not (0.0 < placement["clock"] <= 1.0):
            raise ImportSourceError(f"{placement['id']}: placement clock outside (0, 1]")

    for stream in plan["streams"]:
        if stream["lanes"] < 1:
            raise ImportSourceError(f"{stream['id']}: stream has no lanes")
        if stream["rate"] / stream["lanes"] > stream["capacity"] + max(1e-6, stream["capacity"] * 1e-8):
            raise ImportSourceError(f"{stream['id']}: rate exceeds lane capacity")

    for comparison in plan["comparisons"]:
        if not comparison["variants"]:
            raise ImportSourceError(f"{comparison['item']}: comparison has no variants")
        for variant in comparison["variants"]:
            if variant["path"] not in recipes_by_id:
                raise ImportSourceError(
                    f"{comparison['item']}: comparison recipe absent from recipes.json: {variant['path']}"
                )
            if recipes_by_id[variant["path"]].get("class_name") != variant["key"]:
                raise ImportSourceError(f"{comparison['item']}: comparison class/path mismatch")

    produced: dict[str, float] = {}
    consumed: dict[str, float] = {}
    for item_id, rate in plan["raw_inputs"].items():
        produced[item_id] = produced.get(item_id, 0.0) + rate
    for process in plan["processes"]:
        for item_id, rate in process["outputs"].items():
            produced[item_id] = produced.get(item_id, 0.0) + rate
        for item_id, rate in process["inputs"].items():
            consumed[item_id] = consumed.get(item_id, 0.0) + rate
    consumed["Desc_SpaceElevatorPart_4_C"] = consumed.get("Desc_SpaceElevatorPart_4_C", 0.0) + plan["target"]
    consumed["Desc_PetroleumCoke_C"] = consumed.get("Desc_PetroleumCoke_C", 0.0) + plan["surplus_coke"]
    for item_id in set(produced) | set(consumed):
        left = produced.get(item_id, 0.0)
        right = consumed.get(item_id, 0.0)
        if not _numbers_equal(left, right):
            raise ImportSourceError(
                f"material conservation failed for {item_id}: produced {left} != consumed {right}"
            )

    protected_box = ownership["siting"]["protected_box_xy"]
    if len(protected_box) != 4 or not (protected_box[0] < protected_box[2] and protected_box[1] < protected_box[3]):
        raise ImportSourceError("protected box is not [minX, minY, maxX, maxY]")
    bounds = ownership["protected_factory"]["bounds_xy"]
    if len(bounds) != 2 or len(bounds[0]) != 2 or len(bounds[1]) != 2:
        raise ImportSourceError("protected factory bounds are not a nested native pair")
    if construction.get("site_selection", {}).get("choice") is None:
        raise ImportSourceError("source has no site selection rationale")
    if not ownership.get("extractors"):
        raise ImportSourceError("source has no protected extractors")


def build_drawings(root: Path, manifest: dict[str, Any], levels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries = manifest.get("source_to_render", [])
    by_stem: dict[str, dict[str, Any]] = {}
    for entry in entries:
        stem = Path(entry["svg"]).stem
        if stem in by_stem:
            raise ImportSourceError(f"build manifest repeats drawing {stem}")
        by_stem[stem] = entry
    if len(by_stem) != 49:
        raise ImportSourceError(f"expected 49 registered drawings, got {len(by_stem)}")

    asset_base = f"/atlas/{SAVE_ID}/{PROJECT_ID}"
    drawings: list[dict[str, Any]] = []
    claimed: set[str] = set()

    def add(stem: str, family: str, label: str, caption: str,
            level_id: str | None = None) -> None:
        entry = by_stem.get(stem)
        if entry is None:
            raise ImportSourceError(f"drawing {stem} is not in the frozen build manifest")
        if stem in claimed:
            raise ImportSourceError(f"drawing {stem} registered twice")
        claimed.add(stem)
        svg_path = root / "site" / entry["svg"]
        if not svg_path.is_file():
            raise ImportSourceError(f"missing drawing SVG: {entry['svg']}")
        if sha256_file(svg_path) != entry["svg_sha256"]:
            raise ImportSourceError(f"drawing SVG hash mismatch: {entry['svg']}")
        png_rel = entry.get("png")
        png_path = root / "site" / png_rel if png_rel else None
        if png_path is None or not png_path.is_file():
            raise ImportSourceError(f"missing drawing PNG: {png_rel or stem}")
        if sha256_file(png_path) != entry.get("png_sha256"):
            raise ImportSourceError(f"drawing PNG hash mismatch: {png_rel}")
        drawing: dict[str, Any] = {
            "id": stem,
            "family": family,
            "label": label,
            "caption": f"{caption} · Историческая инженерная схема, не игровой рендер.",
            "svg": f"{asset_base}/drawings/{stem}.svg",
            "png": f"{asset_base}/drawings/{stem}.png",
        }
        if level_id:
            drawing["levelId"] = level_id
        drawings.append(drawing)

    for level in levels:
        add(f"floor-{level['id']}", "floors", level["id"], level["name"], level["id"])

    add("overview", "volumes", "Общий вид", "Общий вид комплекса")
    add("view-northwest", "volumes", "Северо-восточный угол", "Общий вид с северо-запада")
    add("view-northeast", "volumes", "Северо-западный угол", "Общий вид с северо-востока")
    add("view-southeast", "volumes", "Юго-западный угол", "Общий вид с юго-востока")
    add("exploded", "volumes", "Разборный вид", "Разборный вид комплекса")
    add("volume-ROOF", "volumes", "Крыша", "Крыша / объёмная раскладка", "ROOF")
    for level in VOLUME_LEVELS:
        for suffix, short, direction in ANGLE_FILES:
            add(
                f"volume-{level}{suffix}",
                "volumes",
                f"{level} /{short}",
                f"{level} / объёмная раскладка / вид с {direction}",
                level,
            )

    for level in ("T0", "T1", "T2"):
        for suffix, short, direction in ANGLE_FILES:
            add(
                f"volume-{level}{suffix}",
                "technical",
                f"{level} /{short}",
                f"{level} / шины на +1 м, ответвления на +2 м / вид с {direction}",
                level,
            )

    add("facade-south", "facades", "Юг / вход", "Южный фасад / вход")
    add("facade-north", "facades", "Север / ворота", "Северный фасад / ворота")
    add("facade-east", "facades", "Восток / НПЗ", "Восточный фасад / НПЗ")
    add("facade-west", "facades", "Запад", "Западный фасад")
    add("site", "assembly", "Генплан", "Генеральный план участка")
    add("section", "assembly", "Разрез", "Разрез основного корпуса")
    add("facade-module", "assembly", "Фасадный модуль", "Фасадный модуль 16 м")

    if claimed != set(by_stem):
        missing = ", ".join(sorted(set(by_stem) - claimed))
        raise ImportSourceError(f"drawing registry does not cover the frozen manifest: {missing}")
    actual_stems = {path.stem for path in (root / "site" / "drawings").glob("*.svg")}
    if actual_stems != claimed:
        extra = ", ".join(sorted(actual_stems - claimed))
        lost = ", ".join(sorted(claimed - actual_stems))
        raise ImportSourceError(f"frozen drawing directory mismatch; extra: {extra}; missing: {lost}")
    return drawings


def item_label(plan: dict[str, Any], recipes: dict[str, Any], item_id: str) -> str:
    if item_id in plan.get("names", {}):
        return plan["names"][item_id]
    item = recipes.get("items", {}).get(item_id)
    if isinstance(item, dict) and item.get("name"):
        return item["name"]
    return item_id


def item_unit(recipes: dict[str, Any], item_id: str) -> str:
    item = recipes.get("items", {}).get(item_id)
    if isinstance(item, dict) and item.get("form") in ("RF_LIQUID", "RF_GAS"):
        return "м³/мин"
    return "шт/мин"


def coefficient_unit(recipes: dict[str, Any], item_id: str) -> str:
    item = recipes.get("items", {}).get(item_id)
    if isinstance(item, dict) and item.get("form") in ("RF_LIQUID", "RF_GAS"):
        return "м³/ед."
    return "шт/ед."


def minute_flow(plan: dict[str, Any], recipes: dict[str, Any], item_id: str,
                rate: float, exact: str | None = None) -> dict[str, Any]:
    flow: dict[str, Any] = {
        "itemId": item_id,
        "label": item_label(plan, recipes, item_id),
        "rate": rate,
        "unit": item_unit(recipes, item_id),
    }
    if exact is not None:
        flow["exact"] = exact
    return flow


def coefficient_flow(plan: dict[str, Any], recipes: dict[str, Any], item_id: str,
                     rate: float) -> dict[str, Any]:
    return {
        "itemId": item_id,
        "label": item_label(plan, recipes, item_id),
        "rate": rate,
        "unit": coefficient_unit(recipes, item_id),
    }


def split_sentences(body: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", body.strip()) if part.strip()]
    return parts or [body.strip()]


def build_production(plan: dict[str, Any], analysis: dict[str, Any], recipes: dict[str, Any],
                     process_notes: dict[str, str]) -> dict[str, Any]:
    processes: list[dict[str, Any]] = []
    for process in plan["processes"]:
        processes.append({
            "id": process["id"],
            "recipeKey": process["recipe_key"],
            "recipePath": process["recipe_path"],
            "recipeName": process["name"],
            "machineKind": process["machine"],
            "machineName": process["machine_name"],
            "machines": process["machines"],
            "clock": process["clock"],
            "clockFraction": process["clock_fraction"],
            "speedMultiplier": 10,
            "durationSeconds": process["duration_s"],
            "cyclesPerMinute": process["cycles_min"],
            "cyclesFraction": process["cycles_fraction"],
            "inputs": [
                minute_flow(plan, recipes, item_id, rate)
                for item_id, rate in process["inputs"].items()
            ],
            "outputs": [
                minute_flow(plan, recipes, item_id, rate)
                for item_id, rate in process["outputs"].items()
            ],
            "note": process_notes[process["id"]],
        })

    comparisons: list[dict[str, Any]] = []
    for comparison in plan["comparisons"]:
        variants: list[dict[str, Any]] = []
        for variant in comparison["variants"]:
            variants.append({
                "key": variant["key"],
                "path": variant["path"],
                "name": variant["recipe"],
                "inputs": [
                    coefficient_flow(plan, recipes, item_id, rate)
                    for item_id, rate in variant["inputs_per_unit"].items()
                ],
                "byproducts": [
                    coefficient_flow(plan, recipes, item_id, rate)
                    for item_id, rate in variant["byproducts_per_unit"].items()
                ],
                "outputAtFullClock": variant["output_per_mk3_100"],
                "machineKind": variant["machine"],
                "selected": variant["selected"],
            })
        comparisons.append({
            "itemId": comparison["item"],
            "label": item_label(plan, recipes, comparison["item"]),
            "variants": variants,
        })

    selected_names = {
        alternative["name"]
        for alternative in plan["alternatives"]
        if alternative.get("selected")
    }
    scenario_rows = []
    for scenario in plan["alternatives"]:
        scenario_rows.append([
            scenario["name"],
            scenario["processes"],
            scenario["machines"],
            scenario["raw_types"],
            scenario["linear_cost"],
            scenario["build_score"],
            "да" if scenario["name"] in selected_names else "нет",
        ])

    notes = [
        "Производительность указана в минуту; clock: доля 0…1; speedMultiplier MkPlus Mk.3 ×10 уже учтён в cyclesPerMinute.",
        "HeavyFluids делит объёмы ингредиентов и продуктов на 5; добыча не делится. Все жидкостные числа: эффективные м³/мин.",
        "Сравнения рецептов хранят коэффициенты на 1 единицу основного выхода; outputAtFullClock: в минуту.",
        "Кокс: 539,475/мин потребляется сталью и медью, 5139,691/мин уходит в 5 SINK. Общую ленту 5679,167 не собирать.",
        "Выбран сценарий «Прямая EasyAlt с утилизацией кокса»; остальные 7 сценариев сохранены для сравнения.",
        "Точные доли частоты и циклов сохранены отдельными полями; дробные значения не округлены до целых процентов.",
        "Статический баланс не является проверкой игры: напор, лимит труб, модовые коллизии и устойчивый выпуск не проверены.",
    ]

    return {
        "targetItemId": "Desc_SpaceElevatorPart_4_C",
        "targetRate": plan["target"],
        "recipesFile": f"/atlas/{SAVE_ID}/{PROJECT_ID}/recipes.json",
        "recipesSha256": "",  # filled after the published recipes bytes are known
        "rawInputs": [
            minute_flow(plan, recipes, item_id, rate, plan["raw_fractions"].get(item_id))
            for item_id, rate in plan["raw_inputs"].items()
        ],
        "disposal": [
            minute_flow(plan, recipes, "Desc_PetroleumCoke_C", plan["surplus_coke"],
                        plan["surplus_coke_fraction"]),
        ],
        "processes": processes,
        "comparisons": comparisons,
        "scenarios": table(
            "Источники альтернативных сценариев",
            ["Сценарий", "Групп", "Машин", "Сырьевых видов", "Линейный критерий", "Сложность сборки", "Выбран"],
            scenario_rows,
        ),
        "notes": notes,
        "normalizedRecipeCount": plan["recipe_inventory"]["normalized_unlocked"],
        "candidateRecipeCount": plan["recipe_inventory"]["dependency_candidates"],
    }


def build_build(plan: dict[str, Any], construction: dict[str, Any], parts: dict[str, Any],
                readiness_blockers: list[str]) -> dict[str, Any]:
    parts_by_code = {part["code"]: part for part in parts["parts"]}
    commissioning = list(construction["commissioning"])
    if len(commissioning) != 8:
        raise ImportSourceError("expected 8 commissioning items in the frozen construction data")

    checks_by_stage = {
        0: [commissioning[0], commissioning[7]],
        1: [],
        2: [commissioning[4]],
        3: [commissioning[1], commissioning[2]],
        4: ["Выход 633,333 стали, 351,759 меди, 16,667 железа и 422,222 труб/мин."],
        5: [],
        6: [commissioning[3]],
        7: [commissioning[6]],
        8: [commissioning[5]],
        9: [commissioning[5], commissioning[6]],
    }

    steps: list[dict[str, Any]] = []
    for index, source_step in enumerate(construction["construction_steps"]):
        materials = []
        for code in STAGE_MATERIALS.get(index, []):
            part = parts_by_code.get(code)
            if part is None:
                raise ImportSourceError(f"stage {index + 1}: missing parts bill entry {code}")
            materials.append(f"{code}: {part['quantity']}")
        steps.append({
            "id": f"stage-{index + 1:02d}",
            "title": source_step["title"],
            "body": source_step["body"],
            "prerequisites": [],
            "actions": split_sentences(source_step["body"]),
            "materials": materials,
            "checks": checks_by_stage.get(index, []),
            "levelIds": list(STAGE_LEVEL_MAP[index]),
            "drawingIds": list(STAGE_DRAWING_MAP[index]),
        })

    steps[0]["prerequisites"] = list(readiness_blockers)
    for index in range(1, len(steps)):
        steps[index]["prerequisites"] = [
            "Сначала разрешить привязку площадки (этап 1).",
            f"Предыдущий этап: {steps[index - 1]['title']}.",
        ]

    notes = list(plan["assumptions"])
    notes.extend([
        "10 этапов соответствуют исходным construction_steps; частичное выполнение не означает разрешение площадки.",
        "Игровой runtime не проверен; construction_ready=false.",
    ])
    notes.extend(f"{key}: {cell(value)}" for key, value in plan["checks"].items())
    return {"steps": steps, "commissioning": commissioning, "notes": notes}


def build_map(plan: dict[str, Any], ownership: dict[str, Any], marker: dict[str, Any],
              recipes: dict[str, Any]) -> dict[str, Any]:
    asset_base = f"/atlas/{SAVE_ID}/{PROJECT_ID}"
    site = plan["site"]
    protected_factory = ownership["protected_factory"]
    bounds_pair = protected_factory["bounds_xy"]
    protected_factory_bounds = [bounds_pair[0][0], bounds_pair[1][0], bounds_pair[0][1], bounds_pair[1][1]]

    marker_cm = marker["location_cm"]
    withdrawn = {
        "x": marker_cm[0] / 100.0,
        "y": marker_cm[1] / 100.0,
        "z": marker_cm[2] / 100.0,
        "label": "ME-100: старая метка отозвана",
    }

    extractors = []
    for index, extractor in enumerate(ownership["extractors"], start=1):
        node_short = extractor["node"].rsplit(".", 1)[-1]
        actor_short = extractor["path"].rsplit(".", 1)[-1]
        extractors.append({
            "id": actor_short,
            "label": f"{item_label(plan, recipes, extractor['resource']) if 'resource' in extractor else 'Геотермальный генератор'} · {node_short}",
            "node": node_short,
            "x": extractor["xyz"][0],
            "y": extractor["xyz"][1],
            "z": extractor["xyz"][2],
            **({"nominal": extractor["nominal_per_min"]} if "nominal_per_min" in extractor else {}),
            **({"clock": extractor["clock_pct"] / 100.0} if "clock_pct" in extractor else {}),
        })

    feeds = []
    for index, feed in enumerate(site["feeds"], start=1):
        is_water = feed["resource"] == "Desc_Water_C"
        clock_pct = feed.get("extractor_clock_pct", feed.get("clock_pct"))
        clock = clock_pct / 100.0 if clock_pct is not None else 0.0
        if is_water:
            feed_note = (
                "Водоём-ориентир, НЕ точка насоса; отдельный насос и его труба не проверены. "
                "Существующий насос и трубопровод не переиспользуются. "
                f"Ориентир X{feed['x']:.3f}/Y{feed['y']:.3f}/Z{feed['z']:.3f}; "
                f"расстояние {feed.get('distance')} м."
            )
            purity = "водоём-ориентир"
            capacity = 0.0
        else:
            purity = feed.get("purity", "")
            capacity = feed.get("capacity", 0.0)
            feed_note = (
                f"{feed.get('miner', 'новый экстрактор')}; {feed.get('allocation', '')}; "
                f"настроенная частота {clock_pct}%; ёмкость {capacity}; "
                f"расстояние {feed.get('distance')} м."
            )
        feeds.append({
            "id": f"feed-{index:02d}",
            "nodeId": (feed.get("public_id") or feed["path"].rsplit(".", 1)[-1]),
            **({"locationRole": "waterbody-reference"} if is_water else {}),
            "itemId": feed["resource"],
            "label": item_label(plan, recipes, feed["resource"]),
            "x": feed["x"],
            "y": feed["y"],
            "z": feed["z"],
            "required": feed["required"],
            "capacity": capacity,
            "clock": clock,
            "purity": purity,
            "note": feed_note,
        })

    site_alt_rows = []
    for candidate in plan["site_alternatives"]:
        site_alt_rows.append([
            candidate["name"],
            candidate["x"],
            candidate["y"],
            candidate.get("base_z"),
            candidate.get("haul_lane_m"),
            candidate.get("distance_hub"),
            candidate.get("distance_rail"),
            candidate.get("score"),
            candidate.get("approval", "кандидат"),
        ])

    extractor_rows = []
    for extractor in ownership["extractors"]:
        extractor_rows.append([
            item_label(plan, recipes, extractor["resource"]) if "resource" in extractor else "Геотермальный генератор",
            extractor["node"].rsplit(".", 1)[-1],
            extractor["xyz"][0],
            extractor["xyz"][1],
            extractor["xyz"][2],
            extractor.get("nominal_per_min", "не применимо"),
            extractor.get("clock_pct", "не применимо"),
            extractor.get("nominal_basis", "Геотермальная генерация, не поставка сырья."),
        ])

    feed_rows = []
    for feed in site["feeds"]:
        feed_rows.append([
            item_label(plan, recipes, feed["resource"]),
            feed.get("public_id") or feed.get("path", "").rsplit(".", 1)[-1],
            feed.get("purity") or "водоём-ориентир",
            feed["x"],
            feed["y"],
            feed["z"],
            feed["required"],
            feed.get("capacity", "не заявлена"),
            feed.get("extractor_clock_pct", feed.get("clock_pct", "")),
            feed.get("location_role") or feed.get("allocation", ""),
        ])

    protected_product_rows = [
        [
            item_label(plan, recipes, item_id),
            product["machines"],
            product["configured_per_min"],
            len(product["machine_paths"]),
            ", ".join(product["recipes"]),
        ]
        for item_id, product in ownership["products"].items()
    ]

    nearby_rows = []
    for node in plan["nearby_nodes"]:
        nearby_rows.append([
            node.get("public_id") or node["path"].rsplit(".", 1)[-1],
            item_label(plan, recipes, node["resource"]),
            node.get("purity", ""),
            node["x"],
            node["y"],
            node["z"],
            "да" if node.get("occupied") else "нет",
        ])

    notes = [
        note("Статус площадки", f"{ownership['site_approval']}. construction_ready=false. Площадка не утверждена."),
        note("Отозванная метка", f"{marker['recommendation_status']}. {marker['withdrawal_reason']} Новая метка для кандидата не создавалась."),
        note("Критерий выбора", construction_site_text(plan, "formula")),
        note("Что измеряет критерий", construction_site_text(plan, "definitions")),
        note("Решение по площадке", construction_site_text(plan, "choice")),
        note("Чего оценка не доказывает", construction_site_text(plan, "limits")),
        note("Ограничения аудита владения", " ".join(ownership["limits"])),
        note(
            "Защищённый завод",
            f"Сохранённый западный завод: {ownership['products']['Desc_Computer_C']['configured_per_min']} компьютеров/мин "
            f"({ownership['products']['Desc_Computer_C']['machines']} производителей Mk.2) и "
            f"{ownership['products']['Desc_ModularFrameHeavy_C']['configured_per_min']} тяжёлых модульных каркасов/мин "
            f"({ownership['products']['Desc_ModularFrameHeavy_C']['machines']} производителей Mk.2). "
            f"Защищено {protected_factory['physical_network_actors']} связанных объектов и {len(ownership['extractors'])} добывающих установок. "
            "Это настроенный номинал, не замер выпуска и не свободная мощность.",
        ),
        note(
            "Защищённый контур",
            "protectedBox и protectedFactoryBounds: границы сохранённых центров акторов, не полные меши. "
            "Запас 250 м и 32 м: консервативное инженерное решение, не игровые collision-box.",
        ),
        note(
            "Вода",
            "Координата воды показывает существующий водоём/насос как ориентир, НЕ новую точку постройки. "
            "Отдельный насос, независимая труба и напор не проверены.",
        ),
        note(
            "Проекция карты",
            f"worldBounds [{WORLD_BOUNDS[0]}, {WORLD_BOUNDS[1]}, {WORLD_BOUNDS[2]}, {WORLD_BOUNDS[3]}] в метрах; "
            "мировые координаты игры: эти числа ×100. Карта перестроена из текущих кандидатов и защищённых данных; "
            "исторические location-*.png не используются. Проекция выполняется интерфейсом.",
        ),
        note(
            "Линии карты",
            "hub и railPoints используют первые две координаты исходных точек. "
            "Коридоры и маршрут поезда на схеме: проект, а не обследованный spline.",
        ),
        note(
            "Ноды",
            f"{plan['provenance']['node_matches']} совпадений координат; {plan['provenance']['known_miner_types_agree']} известных типов добычи согласованы. "
            "Первичный источник занятости: текущий сейв; внешняя база нод указана в источниках.",
        ),
    ]

    tables = [
        table(
            "Предварительные кандидаты площадки",
            ["Кандидат", "X", "Y", "Базовая Z", "Линия, м", "HUB, м", "Рельс, м", "Оценка", "Статус"],
            site_alt_rows,
        ),
        table(
            "Защищённые добывающие установки",
            ["Ресурс", "Нода", "X", "Y", "Z", "Номинал /мин", "Частота, %", "Основание"],
            extractor_rows,
        ),
        table(
            "Защищённые производства",
            ["Продукт", "Машин", "Настроено /мин", "Акторов", "Рецепты"],
            protected_product_rows,
        ),
        table(
            "Сырьевые вводы кандидата",
            ["Ресурс", "Нода", "Чистота", "X", "Y", "Z", "Требуется", "Ёмкость", "Частота, %", "Роль / распределение"],
            feed_rows,
        ),
        table(
            "Ближайшие ноды",
            ["Нода", "Ресурс", "Чистота", "X", "Y", "Z", "Занята"],
            nearby_rows,
        ),
    ]

    return {
        "terrain": {
            "src": f"{asset_base}/maps/world-terrain.jpg",
            "alt": "Карта мира Satisfactory с каньоном и защищённым заводом",
            "caption": "Реальная карта мира из атласа; координаты в метрах, север вверх. Проекция и наложение выполняются интерфейсом.",
            "kind": "map",
        },
        "worldBounds": WORLD_BOUNDS,
        "scales": [
            {"id": "world", "label": "Весь мир", "bounds": WORLD_BOUNDS},
            {"id": "region", "label": "От HUB до участка", "bounds": REGION_BOUNDS},
            {"id": "site", "label": "Площадка и защищённый завод", "bounds": SITE_BOUNDS},
        ],
        "site": {
            "x": site["x"],
            "y": site["y"],
            "baseZ": site["base_z"],
            "origin": [site["origin"][0], site["origin"][1]],
            "width": site["footprint"][0],
            "depth": site["footprint"][1],
            "label": site["name"],
        },
        "hub": [plan["hub"][0], plan["hub"][1]],
        "railPoints": [[point[0], point[1]] for point in plan["rail_points"]],
        "protectedBox": ownership["siting"]["protected_box_xy"],
        "protectedFactoryBounds": protected_factory_bounds,
        "protectedExtractors": extractors,
        "withdrawnMarker": withdrawn,
        "feeds": feeds,
        "notes": notes,
        "tables": tables,
    }


def construction_site_text(plan: dict[str, Any], key: str) -> str:
    return plan["construction"]["site_selection"][key]


def build_infrastructure(plan: dict[str, Any], construction: dict[str, Any], ownership: dict[str, Any],
                         recipes: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    asset_base = f"/atlas/{SAVE_ID}/{PROJECT_ID}"
    notes = [
        note("Координаты", construction["coordinates"]["convention"]),
        note("Разбивка участка", construction["coordinates"]["setting_out"]),
        note("Модуль", construction["coordinates"]["grid"]),
        note("Ядро", construction["technical"]["core"]),
        note("Правило трассировки", construction["technical"]["bus_rule"]),
        note("Правило портов", construction["technical"]["port_rule"]),
        note("T0", construction["technical"]["T0"]),
        note("T1", construction["technical"]["T1"]),
        note("T2", construction["technical"]["T2"]),
        note("Крыша", construction["technical"]["roof"]),
        note("Ёмкость жидкостей", construction["fluids"]["capacity"]),
        note("Напор", construction["fluids"]["headlift"]),
        note("Пуск жидкостей", construction["fluids"]["start"]),
        note("База мощности", construction["power"]["basis"]),
        note("Бюджет мощности", construction["power"]["budget"]),
        note("Проводка", construction["power"]["wiring"]),
        note("Свет", construction["power"]["lights"]),
        note("Отправляющее депо", construction["rail"]["source"]),
        note("Состав", construction["rail"]["rolling_stock"]),
        note("Буферы", construction["rail"]["buffers"]),
        note("Ответвление", construction["rail"]["route"]),
        note("Приём у склада", construction["rail"]["receiver"]),
        note("Сигналы", construction["rail"]["signals"]),
    ]

    fluid_rows = [
        [header["id"], header["rate"], header["consumers"], header["route"]]
        for header in construction["fluids"]["headers"]
    ]
    split_rows = [
        [split["name"], split["text"]]
        for split in construction["critical_splits"]
    ]
    machine_rows = [
        [kind, machine["name"], machine["width"], machine["depth"], machine["height"],
         "×".join(str(value) for value in machine["cell"]), machine["power"]]
        for kind, machine in plan["machines"].items()
    ]
    architecture_rows = [[key, value] for key, value in plan["architecture"].items()]
    placement_rows = [
        [
            placement["id"],
            placement["process"],
            placement["floor"],
            placement["number"],
            placement["x"],
            placement["y"],
            placement["z"],
            "×".join(str(value) for value in placement["cell"]),
            f"{placement['width']}×{placement['depth']}×{placement['height']}",
        ]
        for placement in plan["placements"]
    ]
    check_rows = [[key, value] for key, value in plan["checks"].items()]
    weight_rows = [[key, value] for key, value in analysis["raw_weights"].items()]
    machine_weight_rows = [[key, value] for key, value in analysis["machine_weights"].items()]

    streams = []
    for stream in plan["streams"]:
        streams.append({
            "id": stream["id"],
            "itemId": stream["item"],
            "label": item_label(plan, recipes, stream["item"]),
            "from": list(stream["from"]),
            "to": stream["to"],
            "rate": stream["rate"],
            "fluid": stream["fluid"],
            "capacity": stream["capacity"],
            "lanes": stream["lanes"],
        })

    tables = [
        table("Коллекторы жидкостей", ["Коллектор", "Поток, м³/мин", "Потребители", "Трасса"], fluid_rows),
        table("Критические развязки", ["Узел", "Описание"], split_rows),
        table("Машинные классы", ["Класс", "Название", "Ширина", "Глубина", "Высота", "Клетка", "Мощность, МВт"], machine_rows),
        table("Архитектурные габариты", ["Параметр", "Значение"], architecture_rows),
        table("Сетка размещений", ["ID", "Группа", "Этаж", "Номер", "X", "Y", "Z", "Клетка", "Габарит"], placement_rows),
        table("Проверки проекта", ["Проверка", "Значение"], check_rows),
        table("Веса сырья", ["Ресурс", "Вес"], weight_rows),
        table("Веса машин", ["Класс", "Вес"], machine_weight_rows),
        table("Ограничения аудита владения", ["Ограничение"], [[value] for value in ownership["limits"]]),
    ]

    diagrams = [
        {
            "src": f"{asset_base}/drawings/site.svg",
            "alt": "Генеральный план участка",
            "caption": "Генплан из исторической инженерной схемы; не игровой рендер.",
            "kind": "schematic",
        },
        {
            "src": f"{asset_base}/drawings/section.svg",
            "alt": "Разрез основного корпуса",
            "caption": "Разрез из исторической инженерной схемы; не игровой рендер.",
            "kind": "schematic",
        },
    ]

    return {"notes": notes, "tables": tables, "diagrams": diagrams, "streams": streams}


def build_parts(parts: dict[str, Any], construction: dict[str, Any]) -> dict[str, Any]:
    asset_base = f"/atlas/{SAVE_ID}/{PROJECT_ID}"
    items = []
    for part in parts["parts"]:
        items.append({
            "code": part["code"],
            "name": part["name"],
            "recipeKey": part["key"],
            "recipePath": part["path"],
            "mod": part["mod"],
            "role": part["role"],
            "quantity": part["quantity"],
            "availability": part["availability"],
        })

    notes = []
    for key in ("module", "quantities", "openings", "structure", "stairs", "roof"):
        notes.append(note(f"Фасад: {key}", construction["facade"][key]))
    style = construction["style"]
    notes.append(note("Стиль", f"{style['name']}. {style['language']}"))
    notes.append(note("Свет", style["light_rule"]))
    notes.append(note(
        "Палитра",
        "; ".join(f"{entry['name']} {entry['hex']}: {entry['role']}" for entry in style["palette"]),
    ))
    notes.append(note(
        "Смета",
        "Количества взяты из исходного parts.json. Это проектные объёмы, не закупка: "
        "фасадный запас 5–10% добавляется отдельно; точные метражи труб, кабеля, перил и лестниц "
        "определяются после монтажа и проверки образцов.",
    ))
    notes.append(note(
        "Проверка деталей",
        "Все позиции отмечены как unlocked in current save; game geometry unverified. "
        "Геометрия модовых деталей, сокеты и коллизии не проверены в игре.",
    ))

    return {
        "items": items,
        "notes": notes,
        "facade": {
            "src": f"{asset_base}/drawings/facade-module.svg",
            "alt": "Фасадный модуль 16 м",
            "caption": "Фасадный модуль из исторической инженерной схемы; не игровой рендер.",
            "kind": "schematic",
        },
    }


def zone_asset_paths(zones: dict[str, Any], references: list[dict[str, Any]]) -> list[str]:
    paths = {reference["file"] for reference in references}
    paths.update(zone[key] for zone in zones["zones"]
                 for key in ("image", "sheet_image", "position_image") if zone.get(key))
    for path in paths:
        if not path.startswith("visuals/") or Path(path).is_absolute() or ".." in Path(path).parts:
            raise ImportSourceError(f"unsafe zone asset path: {path}")
    return sorted(paths)


def build_zone_atlas(zones: dict[str, Any], references: list[dict[str, Any]],
                     plan: dict[str, Any], recipes: dict[str, Any]) -> dict[str, Any]:
    if zones["engineering_sha256"] != EXPECTED_INPUTS["data/plan.json"]:
        raise ImportSourceError("zone illustrations refer to another engineering revision")
    owned = [placement for zone in zones["zones"] if zone["production_owner"]
             for placement in zone["placement_ids"]]
    expected = {placement["id"] for placement in plan["placements"]}
    if len(zones["zones"]) != 52 or len(owned) != len(set(owned)) or set(owned) != expected:
        raise ImportSourceError("latest zones must cover all 48 machines exactly once across 52 views")
    asset_base = f"/atlas/{SAVE_ID}/{PROJECT_ID}/"
    def asset(path: str, title: str, kind: str = "concept") -> dict[str, str]:
        return {"src": asset_base + path, "alt": title, "caption": (
            "Приближённая AI-иллюстрация по игровым референсам, не игровой скриншот."
            if kind == "concept" else "Размерная привязка из того же инженерного плана."
        ), "kind": kind}
    reference_ids = {reference["file"]: Path(reference["file"]).stem for reference in references}
    result = {
        "title": zones["title"],
        "engineeringSha256": zones["engineering_sha256"],
        "fidelity": "Приближённые AI-иллюстрации по реальным игровым референсам. Геометрия, порты и видимое количество машин не заменяют размерный план и не доказывают игровые коллизии.",
        "levels": zones["levels"],
        "references": [{
            "id": reference_ids[reference["file"]],
            "name": reference["name"],
            "image": {"src": asset_base + reference["file"], "alt": reference["name"],
                      "caption": reference["kind"], "kind": "reference"},
            "sourceUrl": reference["url"],
            "sha256": reference["sha256"],
        } for reference in references],
        "views": [],
    }
    for zone in zones["zones"]:
        result["views"].append({
            "id": zone["id"], "levelId": zone["level"], "title": zone["title"],
            "scope": zone["scope"], "variance": zone["variance"],
            "image": asset(zone["image"], zone["title"]),
            "sheet": asset(zone["sheet_image"], f"Исходный лист: {zone['sheet']}"),
            **({"position": asset(zone["position_image"], f"Точные позиции: {zone['id']}", "schematic")}
               if zone.get("position_image") else {}),
            "width": zone["width"], "height": zone["height"],
            "actions": zone["steps"], "network": zone["network"],
            "partCodes": zone["parts"],
            "referenceIds": [reference_ids[path] for path in zone["references"]],
            "placementIds": zone["placement_ids"], "ownsProduction": zone["production_owner"],
            "groups": [{
                "processId": group["id"], "machines": group["zone_machines"],
                "inputs": [minute_flow(plan, recipes, item, rate) for item, rate in group["zone_inputs"].items()],
                "outputs": [minute_flow(plan, recipes, item, rate) for item, rate in group["zone_outputs"].items()],
            } for group in zone["groups"]],
        })
    return result


def build_evidence(verification: dict[str, Any], readiness_blockers: list[str],
                   drawing_count: int, site_approval: str) -> dict[str, Any]:
    items = [
        {
            "id": "source-hashes",
            "label": "Исходные данные и ревизия",
            "status": "verified",
            "detail": "Импорт сверяет SHA-256 всех используемых исходников с замороженным снимком; ревизия: детерминированный хеш входных байтов.",
            "source": "source-snapshot / build-manifest",
        },
        {
            "id": "recipe-coefficients",
            "label": "Рецепты и коэффициенты",
            "status": "verified",
            "detail": "20 групп проверены по published recipes.json: путь, класс, длительность и коэффициенты на цикл совпадают; 23 группы сравнения ссылаются на существующие рецепты.",
            "source": "recipes.json",
        },
        {
            "id": "material-conservation",
            "label": "Материальный баланс",
            "status": "verified",
            "detail": "Сумма сырья и выходов равна потреблению, включая 100 ME/мин и 5139,691 кокса/мин в утилизацию; clock ≤ 1 и формула частоты совпадают.",
            "source": "plan.json",
        },
        {
            "id": "protected-factory",
            "label": "Защищённый завод",
            "status": "verified",
            "detail": "Нативный аудит: 100 компьютеров/мин и около 100 тяжёлых модульных каркасов/мин, 2599 связанных объектов, 10 добывающих установок. Номиналы: настроенные ожидания, не свободная мощность.",
            "source": "ownership.json",
        },
        {
            "id": "assets",
            "label": "Чертежи и карта",
            "status": "verified",
            "detail": f"{drawing_count} SVG и {drawing_count} PNG скопированы с проверкой хешей; это инженерные схемы, не игровые рендеры. Реальная карта мира и AI-концепт F1 сохранены отдельно.",
            "source": "build-manifest / visuals provenance",
        },
        {
            "id": "finished-mesh-views",
            "label": "Точные игровые виды готового завода",
            "status": "unverified",
            "detail": "52 приближённых вида зон закрывают обновлённый иллюстрированный объём. Точные извлечённые меши, порты и игровые коллизии не проверены; AI-кадр не является их доказательством.",
            "source": "zones.json / zone-provenance.json",
        },
        {
            "id": "site-approval",
            "label": "Утверждение площадки",
            "status": "blocked",
            "detail": f"site_approval={site_approval}; construction_ready=false. Террейн, полная геометрия, отдельный водозабор и коридоры не проверены.",
            "source": "ownership.json / construction.json",
        },
        {
            "id": "save-marker",
            "label": "Метка в сохранении",
            "status": "blocked",
            "detail": "Историческая копия сейва с меткой существует, но её рекомендация отозвана: метка относится к отклонённому адресу. Новая метка для кандидата не создавалась; эта миграция не изменяет игровые файлы.",
            "source": "marker.json",
        },
        {
            "id": "terrain-projection",
            "label": "Проекция карты",
            "status": "unverified",
            "detail": "Исходная карта скопирована, но проекция, клиппинг и наложение проверяются интерфейсом; импортёр их не упражняет.",
            "source": "atlas.js projection constants",
        },
        {
            "id": "game-runtime",
            "label": "Игровой runtime",
            "status": "unverified",
            "detail": "Игра не запускалась в этой миграции; эта миграция не изменяет игровые файлы. Напор, Pipeline Mk.3 на 326,2 м³/мин, сочетание MkPlus/VU, устойчивый выпуск, коллизии, поезд, FPS и рельеф не проверены.",
            "source": verification.get("current_milestone", {}).get("game_runtime", "unverified"),
        },
        {
            "id": "construction-readiness",
            "label": "Готовность к строительству",
            "status": "blocked",
            "detail": "Блокеры: " + "; ".join(readiness_blockers),
            "source": "readiness",
        },
    ]
    items.append({
        "id": "zone-illustrations", "label": "Полный визуальный справочник зон",
        "status": "verified",
        "detail": "52 вида всех 8 уровней, ядра и депо; 14 игровых референсов. Все 20 групп и 48 машин связаны с инженерным планом без пропусков и повторного счёта. Изображения приблизительны.",
        "source": "zones.json / zone-provenance.json / references/sources.json",
    })
    items.append({
        "id": "newer-world-settings", "label": "Новый сейв и настройки после расчёта",
        "status": "unverified", "detail": NEWER_SAVE_WARNING,
        "source": "Исходная OMP-сессия: сообщение владельца 2026-10-22T00:01:04.586Z; отдельная early-infrastructure работа.",
    })

    notes = [
        NEWER_SAVE_WARNING,
        "construction_ready=false: успешный статический аудит не является разрешением на строительство.",
        "Игровой runtime не проверен; эта миграция не изменяет игровые файлы. Историческая копия сейва с меткой существует, но её рекомендация отозвана.",
        "Номиналы защищённых экстракторов: configured expectation, не spare capacity и не измеренная подача.",
        "Координата воды: водоём-ориентир, не проверенная точка насоса.",
        "Полный иллюстрированный справочник: 52 AI-вида зон по игровым референсам. Точная игровая геометрия не подтверждена; 49 размерных схем сохранены отдельно.",
        "Исторические location-*.png не используются; карта перестроена из текущих данных.",
        "updatedAt: время генерации импорта, не время игровой проверки.",
        "Все downloads очищены от приватных абсолютных путей; raw save binary и журналы не публикуются.",
        "Ревизия детерминирована по байтам источников; повторный импорт того же снимка даёт ту же ревизию.",
    ]

    sources = [
        {
            "label": "Hirashi3630 / satisfactory_node_heatmap: nodes_vanilla.json",
            "url": "https://raw.githubusercontent.com/Hirashi3630/satisfactory_node_heatmap/master/resources/nodes_vanilla.json",
        },
        {
            "label": "Hirashi3630 / satisfactory_node_heatmap",
            "url": "https://github.com/Hirashi3630/satisfactory_node_heatmap",
        },
    ]

    asset_base = f"/atlas/{SAVE_ID}/{PROJECT_ID}"
    downloads = [
        {"label": "Нормализованный project.json", "path": f"{asset_base}/project.json"},
        {"label": "Опубликованные рецепты recipes.json", "path": f"{asset_base}/recipes.json"},
        {"label": "Очищенный plan.json", "path": f"{asset_base}/downloads/plan.json"},
        {"label": "Очищенный ownership.json", "path": f"{asset_base}/downloads/ownership.json"},
        {"label": "Очищенный analysis.json", "path": f"{asset_base}/downloads/analysis.json"},
        {"label": "Очищенный construction.json", "path": f"{asset_base}/downloads/construction.json"},
        {"label": "Очищенный parts.json", "path": f"{asset_base}/downloads/parts.json"},
        {"label": "Очищенный world.json", "path": f"{asset_base}/downloads/world.json"},
        {"label": "Очищенный marker.json", "path": f"{asset_base}/downloads/marker.json"},
        {"label": "Очищенный verification.json", "path": f"{asset_base}/downloads/verification.json"},
        {"label": "Очищенный build-manifest.json: происхождение изображений", "path": f"{asset_base}/downloads/build-manifest.json"},
        {"label": "Полные инструкции зон zones.json", "path": f"{asset_base}/downloads/zones.json"},
        {"label": "Происхождение иллюстраций зон", "path": f"{asset_base}/downloads/zone-provenance.json"},
        {"label": "Источники игровых референсов", "path": f"{asset_base}/downloads/reference-sources.json"},
    ]

    return {"items": items, "notes": notes, "sources": sources, "downloads": downloads}


def readiness_blockers(ownership: dict[str, Any], construction: dict[str, Any]) -> list[str]:
    return [
        NEWER_SAVE_WARNING,
        f"Площадка не утверждена: {ownership['site_approval']}; construction_ready=false.",
        "Не проверены рельеф, полная геометрия и коллизии выбранных модовых деталей.",
        "Отдельный водозабор и независимая труба не проверены; координата воды: только ориентир.",
        "Коридоры сырья и труб, маршрут поезда и приёмный терминал не обследованы.",
        "Свободная генерация 10–11 ГВт не подтверждена; PowerDuplicator и NoPower не считаются бюджетом.",
        "Игровой runtime не проверен: MkPlus/VU, напор, лимит Pipeline Mk.3, устойчивый выпуск и FPS.",
        "Старая метка в сохранении отозвана; новой метки для кандидата нет.",
    ]


def revision_for(root: Path, manifest: dict[str, Any]) -> str:
    inputs: dict[str, str] = {}
    for rel in sorted(EXPECTED_INPUTS):
        inputs[rel] = sha256_file(root / rel)
    for entry in manifest["source_to_render"]:
        inputs[entry["svg"]] = entry["svg_sha256"]
        inputs[entry["png"]] = entry["png_sha256"]
    for capture in manifest.get("terrain_map_captures", []):
        source_hash = capture.get("source_hashes", {}).get("maps/world-terrain.jpg")
        if source_hash:
            inputs["site/maps/world-terrain.jpg"] = source_hash
            break
    concept_hash = None
    provenance = json.loads((root / "site/visuals/provenance.json").read_text(encoding="utf-8"))
    for name, entry in provenance.items():
        if name == "F1-built-concept.webp":
            concept_hash = entry.get("sha256")
    if concept_hash:
        inputs["site/visuals/F1-built-concept.webp"] = concept_hash
    return sha256_bytes(canonical_bytes({
        "base_commit": BASE_COMMIT,
        "importer_sha256": sha256_file(Path(__file__)),
        "inputs": inputs,
    }))


def normalize_dashes(value: Any) -> Any:
    """Normalize authored/imported typographic dashes in generated data only.

    SVG source assets are copied byte-for-byte and are never rewritten.
    """
    if isinstance(value, dict):
        return {key: normalize_dashes(child) for key, child in value.items()}
    if isinstance(value, list):
        return [normalize_dashes(item) for item in value]
    if isinstance(value, str):
        return value.replace(" — ", ": ").replace("—", "-")
    return value


def sanitize_source(value: Any, save_sha: str, key: str | None = None) -> Any:
    if isinstance(value, dict):
        if key == "input_hashes":
            return [
                {"label": Path(path).name, "sha256": digest}
                for path, digest in sorted(value.items())
            ]
        cleaned: dict[str, Any] = {}
        for child_key, child_value in value.items():
            if child_key == "save" and isinstance(child_value, str):
                cleaned[child_key] = f"source save (sha256 {save_sha})"
            elif child_key == "source_docs" and isinstance(child_value, str):
                cleaned[child_key] = "Satisfactory Docs/en-US.json"
            elif child_key in ("preview_session", "source_worktree", "snapshot_root"):
                cleaned[child_key] = "[private workspace path removed]"
            else:
                cleaned[child_key] = sanitize_source(child_value, save_sha, child_key)
        return cleaned
    if isinstance(value, list):
        return [sanitize_source(item, save_sha, key) for item in value]
    if isinstance(value, str):
        if value.endswith(".sav"):
            return "save file"
        if any(marker in value for marker in PRIVATE_MARKERS):
            return "[private source path removed]"
    return value


def assert_no_private_paths(value: Any, location: str = "document") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str):
                for marker in PRIVATE_MARKERS:
                    if marker in key:
                        raise ImportSourceError(
                            f"refused to publish private source marker {marker!r} in key at {location}"
                        )
            assert_no_private_paths(child, f"{location}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_private_paths(child, f"{location}[{index}]")
        return
    if isinstance(value, str):
        for marker in PRIVATE_MARKERS:
            if marker in value:
                raise ImportSourceError(
                    f"refused to publish private source marker {marker!r} at {location}"
                )


def write_json(path: Path, value: Any) -> bytes:
    data = pretty_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def copy_verified(source: Path, destination: Path, expected_hash: str) -> None:
    data = source.read_bytes()
    actual = sha256_bytes(data)
    if actual != expected_hash:
        raise ImportSourceError(
            f"asset hash mismatch for {source}: expected {expected_hash}, got {actual}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)


def build_document(plan: dict[str, Any], construction: dict[str, Any],
                   ownership: dict[str, Any], parts: dict[str, Any], analysis: dict[str, Any],
                   recipes: dict[str, Any], marker: dict[str, Any],
                   verification: dict[str, Any], manifest: dict[str, Any],
                   process_notes: dict[str, str], drawing_list: list[dict[str, Any]],
                   published_recipes_sha: str, revision: str, updated_at: str) -> dict[str, Any]:
    blockers = readiness_blockers(ownership, construction)
    production = build_production(plan, analysis, recipes, process_notes)
    production["recipesSha256"] = published_recipes_sha
    build_section = build_build(plan, construction, parts, blockers)
    map_section = build_map(plan, ownership, marker, recipes)
    infrastructure = build_infrastructure(plan, construction, ownership, recipes, analysis)
    parts_section = build_parts(parts, construction)
    evidence = build_evidence(verification, blockers, len(drawing_list), ownership["site_approval"])

    preview = {
        "src": f"/atlas/{SAVE_ID}/{PROJECT_ID}/drawings/overview.svg",
        "alt": "Обзорная инженерная схема комбината",
        "caption": "Историческая обзорная инженерная схема, не игровой рендер.",
        "kind": "schematic",
    }
    concept = {
        "src": f"/atlas/{SAVE_ID}/{PROJECT_ID}/visuals/f1-built-concept.webp",
        "alt": "AI-концепт первого этажа; не точная сборка",
        "caption": "AI-визуальный концепт F1 по габаритному плану. Не точная сборка, не игровые ассеты; размеры, меши, порты и идентичность машин не подтверждены.",
        "kind": "concept",
    }

    overview_paragraphs = [
        NEWER_SAVE_WARNING,
        plan["title"],
        construction["style"]["language"],
        (
            f"Производственная цепь: {len(plan['processes'])} групп, "
            f"{sum(process['machines'] for process in plan['processes'])} машин Mk.3, "
            f"{len(plan['levels'])} уровней и {len(drawing_list)} инженерных чертежей. "
            "Целевой выпуск: 100 модульных двигателей в минуту."
        ),
        (
            f"Площадка: кандидат X{plan['site']['x']} / Y{plan['site']['y']}, "
            f"начало X{plan['site']['origin'][0]} / Y{plan['site']['origin'][1]}, "
            f"габарит {plan['site']['footprint'][0]}×{plan['site']['footprint'][1]} м. "
            "Старая точка X1980 / Y−960 отозвана; construction_ready=false."
        ),
        (
            "Защищённый завод на 100 компьютеров/мин и около 100 тяжёлых модульных каркасов/мин "
            "сохраняется полностью: 2599 связанных объектов и 10 добывающих установок не получают "
            "ни одного нового потребителя из этого проекта."
        ),
        (
            "Проект статический: рельеф, отдельный водозабор, коридоры, коллизии и игровой runtime "
            "не проверены. Номиналы защищённых экстракторов: настроенные ожидания, не свободная мощность. "
            "52 приближённых AI-вида зон по игровым референсам дополняют 49 размерных чертежей, но не доказывают точность игровых мешей."
        ),
    ]

    decisions = []
    for decision in construction["design_decisions"]:
        decisions.append({
            "choice": decision["choice"],
            "instead": decision["instead"],
            "reason": decision["reason"],
            "tradeoff": decision["tradeoff"],
        })

    levels = [
        {
            "id": level["id"],
            "name": level["name"],
            "z": level["z"],
            "type": level["type"],
            "purpose": level["purpose"],
        }
        for level in plan["levels"]
    ]

    placements = [
        {
            "id": placement["id"],
            "processId": placement["process"],
            "levelId": placement["floor"],
            "x": placement["x"],
            "y": placement["y"],
            "z": placement["z"],
            "kind": placement["kind"],
            "clock": placement["clock"],
            "width": placement["width"],
            "depth": placement["depth"],
            "height": placement["height"],
        }
        for placement in plan["placements"]
    ]

    summary = {
        "id": PROJECT_ID,
        "saveId": SAVE_ID,
        "kind": "factory",
        "title": "Модульные двигатели",
        "subtitle": "Каньонный моторный комбинат",
        "revision": revision,
        "updatedAt": updated_at,
        "status": "blocked",
        "target": {
            "itemId": "Desc_SpaceElevatorPart_4_C",
            "label": "Modular Engine",
            "rate": 100,
            "unit": "шт/мин",
        },
        "preview": preview,
        "drawingCount": len(drawing_list),
    }

    document = {
        **summary,
        "schemaVersion": 1,
        "source": {
            "saveSha256": plan["provenance"]["save_sha256"],
            "snapshotLabel": SNAPSHOT_LABEL,
            "recipeSha256": published_recipes_sha,
            "sourceSession": SOURCE_SESSION,
        },
        "dependencies": [],
        "readiness": {
            "constructionReady": False,
            "blockers": blockers,
        },
        "overview": {
            "paragraphs": overview_paragraphs,
            "decisions": decisions,
            "concept": concept,
        },
        "build": build_section,
        "drawings": drawing_list,
        "levels": levels,
        "placements": placements,
        "production": production,
        "map": map_section,
        "infrastructure": infrastructure,
        "parts": parts_section,
        "evidence": evidence,
    }
    return document


def publish(root: Path, output: Path, document: dict[str, Any], summary: dict[str, Any],
            recipes_bytes: bytes, manifest: dict[str, Any], downloads: dict[str, Any],
            marker: dict[str, Any], verification: dict[str, Any],
            save_record: dict[str, Any]) -> None:
    # Bootstrap-only publication. A nonempty atlas root is someone else's data:
    # refuse before any staging or mutation so it can never be wiped.
    if output.is_symlink():
        raise ImportSourceError(f"refusing symlink output root: {output}")
    if output.exists():
        if not output.is_dir():
            raise ImportSourceError(f"output root is not a directory: {output}")
        for reserved in ("saves.json", "projects.json"):
            if (output / reserved).exists():
                raise ImportSourceError(
                    f"refusing to replace existing atlas registry {reserved}; "
                    "bootstrap the importer into an empty output root"
                )
        if (output / SAVE_ID / PROJECT_ID).exists():
            raise ImportSourceError(
                f"refusing to replace existing project {SAVE_ID}/{PROJECT_ID}; "
                "bootstrap the importer into an empty output root"
            )
        if any(output.iterdir()):
            raise ImportSourceError(
                f"refusing to replace nonempty output root {output}; "
                "existing atlas content is preserved"
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{PROJECT_ID}-import-", dir=str(output.parent)))
    staged_root = staging / "atlas"
    project_stage = staged_root / SAVE_ID / PROJECT_ID

    try:
        project_stage.mkdir(parents=True, exist_ok=True)
        # Drawings and renders.
        for entry in manifest["source_to_render"]:
            stem = Path(entry["svg"]).stem
            copy_verified(root / "site" / entry["svg"], project_stage / "drawings" / f"{stem}.svg", entry["svg_sha256"])
            copy_verified(root / "site" / entry["png"], project_stage / "drawings" / f"{stem}.png", entry["png_sha256"])

        # Terrain and the disclosed concept.
        terrain_hash = EXPECTED_INPUTS["site/maps/world-terrain.jpg"]
        copy_verified(root / "site/maps/world-terrain.jpg", project_stage / "maps" / "world-terrain.jpg", terrain_hash)
        provenance = json.loads((root / "site/visuals/provenance.json").read_text(encoding="utf-8"))
        concept_hash = provenance["F1-built-concept.webp"]["sha256"]
        copy_verified(root / "site/visuals/F1-built-concept.webp", project_stage / "visuals" / "f1-built-concept.webp", concept_hash)
        zones = load_json_input(root, "data/zones.json")
        references = load_json_input(root, "site/visuals/references/sources.json")
        for relative in zone_asset_paths(zones, references):
            copy_verified(root / "site" / relative, project_stage / relative, manifest["outputs"][relative])
        for entry in zones["source_to_output"]:
            if sha256_file(root / "site" / entry["source"]) != entry["source_sha256"] or sha256_file(root / "site" / entry["output"]) != entry["output_sha256"]:
                raise ImportSourceError(f"zone crop provenance mismatch: {entry['zone']}")

        # Sanitized evidence downloads and the exact published recipe bytes.
        save_sha = document["source"]["saveSha256"]
        download_objects = {
            "plan.json": downloads["plan"],
            "ownership.json": downloads["ownership"],
            "analysis.json": downloads["analysis"],
            "construction.json": downloads["construction"],
            "parts.json": downloads["parts"],
            "world.json": downloads["world"],
            "marker.json": marker,
            "verification.json": verification,
            "build-manifest.json": manifest,
            "zones.json": zones,
            "zone-provenance.json": load_json_input(root, "site/visuals/zone-provenance.json"),
            "reference-sources.json": references,
        }
        for name, value in download_objects.items():
            cleaned = normalize_dashes(sanitize_source(value, save_sha))
            assert_no_private_paths(cleaned, f"downloads/{name}")
            write_json(project_stage / "downloads" / name, cleaned)
        (project_stage / "recipes.json").write_bytes(recipes_bytes)

        write_json(project_stage / "project.json", document)
        assert_no_private_paths(document, "project.json")
        write_json(staged_root / "saves.json", normalize_dashes({"schemaVersion": 1, "saves": [save_record]}))
        write_json(staged_root / "projects.json", normalize_dashes({"schemaVersion": 1, "projects": [summary]}))

        # Re-check immediately before the atomic promotion. Any concurrent work
        # in the root makes this a refusal, not an overwrite.
        removed_empty_output = False
        if output.exists():
            if not output.is_dir() or any(output.iterdir()):
                raise ImportSourceError(
                    f"output root {output} became nonempty during import; refusing to overwrite it"
                )
            output.rmdir()
            removed_empty_output = True
        try:
            os.replace(staged_root, output)
        except OSError as exc:
            if removed_empty_output and not output.exists():
                try:
                    output.mkdir(parents=True, exist_ok=True)
                except OSError:
                    pass
            raise ImportSourceError(f"could not atomically promote empty output: {exc}") from exc
    finally:
        # Only the unique staging directory created above is removed. No stale
        # staging directory, backup, registry, or existing project is touched.
        shutil.rmtree(staging, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import the frozen factory atlas into public/atlas.")
    parser.add_argument("--source", required=True, help="absolute path to the frozen factory_atlas root")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="empty public root or owned ignored staging root")
    args = parser.parse_args(argv)

    source = Path(args.source)
    output = Path(args.output)
    if not source.is_absolute():
        print(json.dumps({"ok": False, "error": "--source must be an absolute path"}, ensure_ascii=False), file=sys.stderr)
        return 2
    atlas_root = (REPO_ROOT / "public" / "atlas").resolve()
    if output.resolve() != atlas_root and not output.resolve().is_relative_to((REPO_ROOT / ".superpowers").resolve()):
        print(json.dumps({"ok": False, "error": "output must be public/atlas or owned ignored staging"}, ensure_ascii=False), file=sys.stderr)
        return 2

    try:
        validate_source_root(source)
        plan = load_json_input(source, "data/plan.json")
        construction = load_json_input(source, "data/construction.json")
        ownership = load_json_input(source, "data/ownership.json")
        parts = load_json_input(source, "data/parts.json")
        analysis = load_json_input(source, "data/analysis.json")
        recipes = load_json_input(source, "data/recipes.json")
        world = load_json_input(source, "data/world.json")
        marker = load_json_input(source, "site/downloads/marker.json")
        manifest = load_json_input(source, "site/build-manifest.json")
        verification = load_json_input(source, "site/verification.json")
        load_json_input(source, "site/visuals/provenance.json")

        validate_domain(plan, recipes, ownership, construction, parts)
        process_notes = read_process_notes(source / "site/atlas.js")
        drawing_list = build_drawings(source, manifest, plan["levels"])

        save_sha = plan["provenance"]["save_sha256"]
        cleaned_recipes = normalize_dashes(sanitize_source(recipes, save_sha))
        assert_no_private_paths(cleaned_recipes, "recipes.json")
        recipes_bytes = pretty_bytes(cleaned_recipes)
        published_recipes_sha = sha256_bytes(recipes_bytes)

        revision = revision_for(source, manifest)
        updated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        document = normalize_dashes(build_document(
            plan, construction, ownership, parts, analysis, recipes,
            marker, verification, manifest, process_notes, drawing_list,
            published_recipes_sha, revision, updated_at,
        ))
        zones = load_json_input(source, "data/zones.json")
        references = load_json_input(source, "site/visuals/references/sources.json")
        document["zoneAtlas"] = normalize_dashes(build_zone_atlas(zones, references, plan, recipes))
        document["zoneCount"] = len(document["zoneAtlas"]["views"])
        document["source"].update(planSha256=EXPECTED_INPUTS["data/plan.json"], snapshotAt=SOURCE_CUTOFF)
        document["preview"] = next(view["image"] for view in document["zoneAtlas"]["views"] if view["id"] == "F1-00")
        document["overview"]["paragraphs"].insert(3, "Последнее дополнение исходной сессии: 52 вида зон с порядком сборки, потоками, точными размещениями и игровыми референсами.")
        for index, step in enumerate(document["build"]["steps"]):
            zone_levels = set(step["levelIds"])
            if index == 2: zone_levels.update(("T0", "RF"))
            if index == 7: zone_levels.add("DEPOT")
            if index == 8: zone_levels.add("CORE")
            step["zoneIds"] = [view["id"] for view in document["zoneAtlas"]["views"] if view["levelId"] in zone_levels]
        summary = {
            key: document[key]
            for key in ("id", "saveId", "kind", "title", "subtitle", "revision", "updatedAt",
                        "status", "target", "preview", "drawingCount", "zoneCount")
        }
        save_record = {
            "id": SAVE_ID,
            "name": "cachys",
            "sessionName": "каша",
            "sourceLabel": SOURCE_LABEL,
            "sourceSha256": save_sha,
            "snapshotAt": verification.get("checked_at", updated_at),
            "modCount": MOD_COUNT,
        }
        downloads = {"plan": plan, "ownership": ownership, "analysis": analysis,
                     "construction": construction, "parts": parts, "world": world}

        publish(source, output, document, summary, recipes_bytes,
                manifest, downloads, marker, verification, save_record)

        result = {
            "ok": True,
            "output": str(output),
            "project": f"{SAVE_ID}/{PROJECT_ID}",
            "revision": revision,
            "updatedAt": updated_at,
            "recipesSha256": published_recipes_sha,
            "counts": {
                "drawings": len(drawing_list),
                "zones": len(document["zoneAtlas"]["views"]),
                "references": len(document["zoneAtlas"]["references"]),
                "levels": len(document["levels"]),
                "placements": len(document["placements"]),
                "processes": len(document["production"]["processes"]),
                "comparisons": len(document["production"]["comparisons"]),
                "scenarios": len(document["production"]["scenarios"]["rows"]),
                "streams": len(document["infrastructure"]["streams"]),
                "parts": len(document["parts"]["items"]),
                "stages": len(document["build"]["steps"]),
            },
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ImportSourceError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except (KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": f"source data shape failure: {exc!r}"}, ensure_ascii=False), file=sys.stderr)
        return 2
    except OSError as exc:
        print(json.dumps({"ok": False, "error": f"I/O failure: {exc}"}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
