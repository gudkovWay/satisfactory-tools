"""Validate source-backed atlas documents and publish immutable asset revisions."""
from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'public' / 'atlas'
ID_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
KEY_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]*$')
HASH_RE = re.compile(r'^[0-9a-f]{64}$')
KINDS = {'factory', 'road', 'depot', 'warehouse'}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def close(actual, expected):
    return abs(actual - expected) <= max(1e-6, abs(expected) * 1e-8)


def number(value, *, positive=False, integer=False):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and (not positive or value > 0)
            and (not integer or int(value) == value))


def asset_references(project):
    for name, asset in [('preview', project.get('preview')),
                        ('overview.concept', project.get('overview', {}).get('concept')),
                        ('map.terrain', project.get('map', {}).get('terrain')),
                        ('parts.facade', project.get('parts', {}).get('facade'))]:
        if asset:
            yield name, asset.get('src')
    for index, drawing in enumerate(project['drawings']):
        yield f'drawings[{index}].svg', drawing.get('svg')
        if drawing.get('png'):
            yield f'drawings[{index}].png', drawing['png']
    for index, asset in enumerate(project['infrastructure']['diagrams']):
        yield f'infrastructure.diagrams[{index}]', asset.get('src')
    for index, download in enumerate(project['evidence']['downloads']):
        yield f'evidence.downloads[{index}]', download.get('path')
    if project.get('production'):
        yield 'production.recipesFile', project['production'].get('recipesFile')
    atlas = project.get('zoneAtlas')
    if atlas:
        for index, zone in enumerate(atlas['views']):
            for key in ('image', 'sheet', 'position'):
                if zone.get(key):
                    yield f'zoneAtlas.views[{index}].{key}', zone[key].get('src')
        for index, reference in enumerate(atlas['references']):
            yield f'zoneAtlas.references[{index}]', reference['image'].get('src')


def asset_path(url, project, assets_root):
    prefix = f"/atlas/{project['saveId']}/{project['id']}/"
    if not isinstance(url, str) or not url.startswith(prefix):
        raise ValueError('asset must use this project local /atlas URL prefix')
    suffix = url[len(prefix):]
    parts = PurePosixPath(suffix).parts
    if not suffix or any(part in {'.', '..'} for part in suffix.split('/')) or any(c in suffix for c in '\\?#\0'):
        raise ValueError('unsafe asset URL')
    root = Path(assets_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('asset root must be an existing non-symlink directory')
    root = root.resolve()
    candidate = root
    for part in parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError('symlink assets are not supported')
    if not candidate.is_file() or not candidate.resolve().is_relative_to(root):
        raise ValueError(f'missing or escaping asset: {suffix}')
    return candidate, suffix


def construction_signature(project, assets_root):
    fields = ('build', 'placements', 'levels', 'production', 'parts', 'drawings', 'zoneAtlas', 'infrastructure', 'sitePlan', 'extraction')
    semantic = {key: project.get(key) for key in fields}
    encoded = re.sub(r'/revisions/[0-9a-f]{64}/', '/revisions/', json.dumps(semantic, sort_keys=True, ensure_ascii=False))
    assets = {}
    for name, url in asset_references(project):
        if name.startswith(('drawings[', 'zoneAtlas.', 'infrastructure.diagrams', 'parts.facade', 'production.recipesFile')):
            assets[name] = digest(asset_path(url, project, assets_root)[0])
    return hashlib.sha256(json.dumps({'semantic': encoded, 'assets': assets}, sort_keys=True).encode()).hexdigest()


def validate_zones(project, assets):
    atlas = project.get('zoneAtlas')
    if atlas is None:
        return ['zoneCount requires a zone atlas'] if project.get('zoneCount', 0) else []
    errors = []
    def fail(message):
        errors.append('zoneAtlas: ' + message)
    if not isinstance(atlas, dict) or any(not isinstance(atlas.get(key), list) for key in ('views', 'levels', 'references')):
        return ['zoneAtlas: views, levels and references must be arrays']
    views, levels, references = atlas['views'], atlas['levels'], atlas['references']
    if any(not isinstance(item, dict) or not isinstance(item.get('id'), str) for item in views + levels + references):
        return ['zoneAtlas: each view, level and reference requires an ID']
    view_ids = {view['id'] for view in views}
    level_ids = {level['id'] for level in levels}
    reference_ids = {reference['id'] for reference in references}
    if not views or len(view_ids) != len(views) or len(level_ids) != len(levels) or len(reference_ids) != len(references):
        fail('empty views or duplicate IDs')
    if project.get('zoneCount') != len(views):
        fail('zoneCount differs from actual views')
    plan_hash = atlas.get('engineeringSha256')
    if not HASH_RE.fullmatch(str(plan_hash)) or plan_hash != project['source'].get('planSha256'):
        fail('zone engineering revision differs from the project source')
    processes = {process['id']: process for process in project.get('production', {}).get('processes', [])}
    placements = {placement['id']: placement for placement in project['placements']}
    part_codes = {part['code'] for part in project['parts']['items']}
    owned = Counter()
    for view in views:
        ident = view['id']
        if view.get('levelId') not in level_ids:
            fail(f'{ident}: unknown level')
        for key in ('actions', 'partCodes', 'referenceIds', 'placementIds', 'groups'):
            if not isinstance(view.get(key), list):
                fail(f'{ident}: {key} must be an array')
        if errors:
            continue
        if not view['actions'] or not all(isinstance(action, str) and action.strip() for action in view['actions']):
            fail(f'{ident}: missing construction actions')
        if any(not number(view.get(key), positive=True) for key in ('width', 'height')):
            fail(f'{ident}: invalid image dimensions')
        for key in ('image', 'sheet'):
            if not isinstance(view.get(key), dict) or not view[key].get('src'):
                fail(f'{ident}: missing {key}')
        if not isinstance(view.get('ownsProduction'), bool):
            fail(f'{ident}: ownsProduction must be explicit')
        if any(code not in part_codes for code in view['partCodes']) or any(ref not in reference_ids for ref in view['referenceIds']):
            fail(f'{ident}: unknown part or reference')
        counts = Counter()
        for placement_id in view['placementIds']:
            placement = placements.get(placement_id)
            if not placement or placement['levelId'] != view['levelId']:
                fail(f'{ident}: unknown placement or wrong level')
                continue
            counts[placement['processId']] += 1
            if view['ownsProduction']:
                owned[placement_id] += 1
        group_ids = set()
        for group in view['groups']:
            process = processes.get(group.get('processId')) if isinstance(group, dict) else None
            if not process or not number(process.get('machines'), positive=True):
                fail(f'{ident}: unknown or invalid production group')
                continue
            pid, machines = process['id'], group.get('machines')
            if pid in group_ids or not number(machines, positive=True, integer=True) or counts[pid] != machines:
                fail(f'{ident}/{pid}: duplicate group or machine/placement count mismatch')
                continue
            group_ids.add(pid)
            for side in ('inputs', 'outputs'):
                actual = group.get(side)
                if not isinstance(actual, list) or any(not isinstance(flow, dict) or not number(flow.get('rate')) for flow in actual):
                    fail(f'{ident}/{pid}: invalid {side}')
                    continue
                rates = {flow.get('itemId'): flow['rate'] for flow in actual}
                expected = {flow['itemId']: flow['rate'] * machines / process['machines'] for flow in process[side]}
                if len(rates) != len(actual) or set(rates) != set(expected) or any(not close(rates[item], rate) for item, rate in expected.items() if item in rates):
                    fail(f'{ident}/{pid}: scoped {side} differ from the engineering plan')
        if set(counts) != group_ids:
            fail(f'{ident}: placements and groups differ')
    if set(owned) != set(placements) or any(count != 1 for count in owned.values()):
        fail('owned zones must cover every production placement exactly once')
    for stage in project['build']['steps']:
        if any(ident not in view_ids for ident in stage.get('zoneIds', [])):
            fail(f"{stage['id']}: unknown zone link")
    for reference in references:
        path = assets.get(reference.get('image', {}).get('src'))
        if not path or reference.get('sha256') != digest(path):
            fail(f"{reference['id']}: reference bytes differ from provenance")
    return errors


def validate_project(project, *, recipes_file=None, save_ids=None, known_projects=None, assets_root=None, registry_root=ROOT):
    errors, warnings = [], []

    def error(path, message):
        errors.append(f'{path}: {message}')

    def string(obj, key, path, *, empty=False):
        value = obj.get(key)
        if not isinstance(value, str) or (not empty and not value.strip()):
            error(f'{path}.{key}', 'expected nonempty text')

    def array(obj, key, path, *, nonempty=False):
        value = obj.get(key)
        if not isinstance(value, list) or (nonempty and not value):
            error(f'{path}.{key}', 'expected ' + ('nonempty ' if nonempty else '') + 'array')
            return []
        return value

    def strings(obj, key, path, *, nonempty=False):
        values = array(obj, key, path, nonempty=nonempty)
        if any(not isinstance(value, str) or not value.strip() for value in values):
            error(f'{path}.{key}', 'entries must be nonempty text')
        return values

    def objects(obj, key, path, *, nonempty=False):
        values = array(obj, key, path, nonempty=nonempty)
        if any(not isinstance(value, dict) for value in values):
            error(f'{path}.{key}', 'entries must be objects')
        return [value for value in values if isinstance(value, dict)]

    def unique(values, path, key='id'):
        seen = set()
        for value in values:
            ident = value.get(key)
            if not isinstance(ident, str) or not KEY_RE.fullmatch(ident):
                error(path, f'unsafe or missing {key}')
            elif ident in seen:
                error(path, f'duplicate {key}: {ident}')
            seen.add(ident if isinstance(ident, str) else None)

    def flow_map(flows, path):
        result = {}
        if not isinstance(flows, list):
            error(path, 'expected flow array')
            return result
        for index, flow in enumerate(flows):
            if not isinstance(flow, dict):
                error(f'{path}[{index}]', 'expected flow object')
                continue
            item = flow.get('itemId')
            if not isinstance(item, str) or not item or item in result:
                error(path, 'missing or duplicate itemId')
                continue
            if not number(flow.get('rate')) or flow['rate'] < 0:
                error(path, f'invalid flow rate for {item}')
                continue
            string(flow, 'label', path)
            string(flow, 'unit', path)
            result[item] = flow['rate']
        return result

    if not isinstance(project, dict):
        return ['project: expected object'], warnings
    for key in ('id', 'saveId', 'kind', 'title', 'subtitle', 'revision', 'updatedAt', 'status'):
        string(project, key, 'project')
    if project.get('schemaVersion') != 1:
        error('schemaVersion', 'must be 1')
    for key in ('id', 'saveId'):
        if not isinstance(project.get(key), str) or not ID_RE.fullmatch(project[key]):
            error(key, 'must be lowercase kebab-case')
    if project.get('kind') not in KINDS:
        error('kind', 'unknown project kind')
    if project.get('status') not in {'draft', 'blocked', 'ready'}:
        error('status', 'unknown readiness status')
    if not HASH_RE.fullmatch(str(project.get('revision', ''))):
        error('revision', 'expected SHA-256 source revision')
    if 'progressRevision' in project and not HASH_RE.fullmatch(str(project['progressRevision'])):
        error('progressRevision', 'expected SHA-256 construction revision')
    if 'progressSignature' in project and not HASH_RE.fullmatch(str(project['progressSignature'])):
        error('progressSignature', 'expected SHA-256 construction signature')
    try:
        datetime.fromisoformat(project.get('updatedAt', '').replace('Z', '+00:00'))
    except (ValueError, TypeError, AttributeError):
        error('updatedAt', 'expected ISO date/time')
    for key in ('source', 'readiness', 'overview', 'build', 'infrastructure', 'parts', 'evidence'):
        if not isinstance(project.get(key), dict):
            error(key, 'expected object')
    if errors:
        return errors, warnings
    source, ready = project['source'], project['readiness']
    if not HASH_RE.fullmatch(str(source.get('saveSha256', ''))):
        error('source.saveSha256', 'expected SHA-256')
    string(source, 'snapshotLabel', 'source')
    blockers = strings(ready, 'blockers', 'readiness')
    if not isinstance(ready.get('constructionReady'), bool):
        error('readiness.constructionReady', 'expected boolean')
    if ready.get('constructionReady') != (project['status'] == 'ready'):
        error('readiness', 'constructionReady and status must agree')
    if ready.get('constructionReady') and blockers:
        error('readiness', 'ready project retains blockers')
    planning = source.get('planning')
    forecast = planning is not None
    forecast_profile = {}
    if forecast:
        if not isinstance(planning, dict):
            error('source.planning', 'expected explicit forecast scope')
            planning = {}
        tier, density = planning.get('tier'), planning.get('density')
        if planning.get('mode') != 'forecast' or not number(tier, positive=True, integer=True) or not number(density, positive=True):
            error('source.planning', 'forecast requires a positive tier and density')
        try:
            authority = read_json(registry_root / project['saveId'] / 'source-evidence.json')
            profiles = [profile for profile in authority.get('forecastProfiles', []) if profile.get('density') == density]
            if len(profiles) != 1 or not number(tier) or not profiles[0]['minTier'] <= tier <= profiles[0]['maxTier']:
                error('source.planning', 'density is unavailable in this save/tier profile')
            else:
                forecast_profile = profiles[0]
        except (OSError, ValueError, TypeError, KeyError) as exc:
            error('source.planning', f'cannot read save forecast profile: {exc}')
        strings(planning, 'prerequisites', 'source.planning', nonempty=True)
        if ready.get('constructionReady'):
            error('readiness', 'a source forecast cannot certify current gameplay readiness')
    strings(project['overview'], 'paragraphs', 'overview', nonempty=True)
    objects(project['overview'], 'decisions', 'overview')
    stages = objects(project['build'], 'steps', 'build', nonempty=True)
    strings(project['build'], 'commissioning', 'build', nonempty=True)
    strings(project['build'], 'notes', 'build')
    drawings = objects(project, 'drawings', 'project', nonempty=True)
    levels = objects(project, 'levels', 'project')
    placements = objects(project, 'placements', 'project')
    dependencies = objects(project, 'dependencies', 'project')
    streams = objects(project['infrastructure'], 'streams', 'infrastructure')
    for key in ('notes', 'tables', 'diagrams'):
        objects(project['infrastructure'], key, 'infrastructure')
    objects(project['parts'], 'items', 'parts', nonempty=True)
    objects(project['parts'], 'notes', 'parts')
    evidence = objects(project['evidence'], 'items', 'evidence', nonempty=True)
    strings(project['evidence'], 'notes', 'evidence')
    objects(project['evidence'], 'sources', 'evidence')
    objects(project['evidence'], 'downloads', 'evidence')
    for values, label in [(stages, 'build.steps'), (drawings, 'drawings'), (levels, 'levels'), (placements, 'placements'), (streams, 'streams'), (evidence, 'evidence.items')]:
        unique(values, label)
    if project.get('drawingCount') != len(drawings):
        error('drawingCount', 'does not match drawing inventory')
    drawing_ids = {drawing.get('id') for drawing in drawings}
    level_ids = {level.get('id') for level in levels}
    for index, stage in enumerate(stages):
        label = f'build.steps[{index}]'
        string(stage, 'title', label)
        string(stage, 'body', label)
        strings(stage, 'actions', label, nonempty=True)
        for key in ('prerequisites', 'materials', 'checks', 'drawingIds', 'levelIds'):
            strings(stage, key, label)
        if any(ident not in drawing_ids for ident in stage.get('drawingIds', [])):
            error(label, 'unknown drawing reference')
        if any(ident not in level_ids for ident in stage.get('levelIds', [])):
            error(label, 'unknown level reference')
    for item in evidence:
        for key in ('label', 'detail'):
            string(item, key, 'evidence.items')
        if item.get('status') not in {'verified', 'unverified', 'blocked', 'not-applicable'}:
            error('evidence.items', 'unknown evidence status')
    if ready.get('constructionReady') and any(item.get('status') in {'blocked', 'unverified'} for item in evidence):
        error('readiness', 'unresolved evidence cannot be construction-ready')
    if errors:
        return errors, warnings

    registry_root = Path(registry_root)
    try:
        saves = read_json(registry_root / 'saves.json')['saves']
        registered = {item['id'] for item in saves}
        index = read_json(registry_root / 'projects.json') if (registry_root / 'projects.json').exists() else {'projects': []}
        known = {(item['saveId'], item['id']) for item in index['projects']}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        error('registry', f'cannot read save/project registry: {exc}')
        registered, known = set(), set()
    if project['saveId'] not in (set(save_ids) if save_ids is not None else registered):
        error('saveId', 'unknown registered save')
    known = set(known_projects) if known_projects is not None else known
    seen_dependencies = set()
    for dep in dependencies:
        pair = (dep.get('saveId'), dep.get('projectId'))
        if pair in seen_dependencies or pair not in known or pair == (project['saveId'], project['id']):
            error('dependencies', 'unknown, duplicate or self dependency')
        if pair[0] != project['saveId']:
            error('dependencies', 'cross-save dependency')
        seen_dependencies.add(pair)
        string(dep, 'role', 'dependencies')

    root = Path(assets_root) if assets_root is not None else registry_root / project['saveId'] / project['id']
    asset_files = {}
    for label, url in asset_references(project):
        try:
            asset_files[url] = asset_path(url, project, root)[0]
        except (ValueError, OSError) as exc:
            error(label, str(exc))
    errors.extend(validate_zones(project, asset_files))
    production = project.get('production')
    if project['kind'] == 'factory' and not isinstance(production, dict):
        error('production', 'factory requires full production evidence')
    if project['kind'] != 'factory' and project.get('target') is not None:
        error('target', 'shared infrastructure must not invent a production target')
    if isinstance(production, dict):
        target = project.get('target', {})
        target_rate = target.get('rate')
        if not number(target_rate, positive=True) or not isinstance(target.get('itemId'), str):
            error('target', 'expected item and positive finite rate')
        if production.get('targetItemId') != target.get('itemId') or production.get('targetRate') != target_rate:
            error('production', 'target differs from project target')
        targets = production.get('targets', [target])
        if 'targets' in production:
            targets = objects(production, 'targets', 'production', nonempty=True)
        target_flows = flow_map(targets, 'production.targets')
        for item, rate in target_flows.items():
            if rate <= 0:
                error('production.targets', f'{item} must have a positive target rate')
        if target_flows.get(target.get('itemId')) != target_rate:
            error('production.targets', 'must include the primary project target at the same rate')
        processes = objects(production, 'processes', 'production', nonempty=True)
        unique(processes, 'production.processes')
        recipe_path = asset_files.get(production.get('recipesFile'))
        if recipes_file is not None and recipe_path and Path(recipes_file).resolve() != recipe_path.resolve():
            error('production.recipesFile', 'validator input differs from referenced recipe file')
        try:
            source_registry = read_json(registry_root / project['saveId'] / 'source-evidence.json')
            if source_registry.get('saveSha256') != source['saveSha256']:
                error('source.saveSha256', 'does not match the registered save snapshot')
            recipe_authority = 'forecastRecipesSha256' if forecast else 'normalizedRecipesSha256'
            if source_registry.get(recipe_authority) != production.get('recipesSha256'):
                error('production.recipesSha256', 'does not match the registered recipe authority')
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            error('source', f'cannot read registered recipe authority: {exc}')
        recipe_data = None
        if recipe_path:
            try:
                recipe_data = read_json(recipe_path)
                if production.get('recipesSha256') != digest(recipe_path):
                    error('production.recipesSha256', 'does not match exact recipe bytes')
                if recipe_data.get('provenance', {}).get('save_sha256') != source['saveSha256']:
                    error('production', 'recipe unlock snapshot belongs to a different save revision')
            except (OSError, ValueError, TypeError) as exc:
                error('production', f'cannot read normalized recipes: {exc}')
        if forecast and isinstance(recipe_data, dict) and recipe_data.get('provenance', {}).get('scope') != 'forecast-standard-recipes':
            error('production', 'forecast must not masquerade as a current unlock inventory')
        recipes = {recipe.get('class_name'): recipe for recipe in recipe_data.get('recipes', []) if isinstance(recipe, dict)} if isinstance(recipe_data, dict) else {}
        if not recipes:
            error('production', 'normalized unlocked recipe inventory is missing')
        raw = flow_map(production.get('rawInputs'), 'production.rawInputs')
        disposal = flow_map(production.get('disposal'), 'production.disposal')
        net = defaultdict(float, raw)
        inputs_by_process, outputs_by_process = {}, {}
        process_by_id = {}
        for index, process in enumerate(processes):
            label = f'production.processes[{index}]'
            process_by_id[process['id']] = process
            for key in ('machines', 'clock', 'speedMultiplier', 'durationSeconds', 'cyclesPerMinute'):
                if not number(process.get(key), positive=True, integer=key == 'machines'):
                    error(label, f'{key} must be positive and finite')
            ins = flow_map(process.get('inputs'), label + '.inputs')
            outs = flow_map(process.get('outputs'), label + '.outputs')
            inputs_by_process[process['id']], outputs_by_process[process['id']] = ins, outs
            for item, value in outs.items(): net[item] += value
            for item, value in ins.items(): net[item] -= value
            if any(not number(process.get(key), positive=True) for key in ('machines', 'clock', 'speedMultiplier', 'durationSeconds', 'cyclesPerMinute')):
                continue
            clock_limit = forecast_profile.get('manufacturingClockLimit', 1) if forecast else recipe_data.get('provenance', {}).get('manufacturing_clock_limit', 1)
            if process['clock'] > clock_limit + 1e-10:
                error(label, 'manufacturing clock exceeds the source profile')
            expected_clock = process['cyclesPerMinute'] * process['durationSeconds'] / (60 * process['machines'] * process['speedMultiplier'])
            if not close(process['clock'], expected_clock):
                error(label, 'clock/cycle/machine formula mismatch')
            recipe = recipes.get(process.get('recipeKey'))
            if not recipe or recipe.get('id') != process.get('recipePath'):
                error(label, 'recipe class/path is absent from pinned unlocked inventory')
                continue
            if forecast and (not number(recipe.get('availableFromTier'), positive=True, integer=True) or recipe['availableFromTier'] > planning['tier']):
                error(label, 'recipe is unavailable at the forecast tier')
            if recipe.get('machine') != process.get('machineKind') or not close(process['durationSeconds'], recipe.get('duration', 0)):
                error(label, 'machine kind or recipe duration differs from source')
            provenance = recipe_data.get('provenance', {})
            expected_speed = forecast_profile.get('machineMultipliers', {}).get(process['machineKind']) if forecast else provenance.get('machine_multipliers', {}).get(process['machineKind'], provenance.get('MkPlus_machine_multiplier', 1))
            if not number(expected_speed, positive=True) or not close(process['speedMultiplier'], expected_speed):
                error(label, 'machine speed differs from source modifiers')
            for side, actual in [('inputs', ins), ('outputs', outs)]:
                coefficients = recipe.get(side, {})
                if set(actual) != set(coefficients):
                    error(label, f'{side} item set differs from source recipe')
                for item, coefficient in coefficients.items():
                    if not number(coefficient) or not close(actual.get(item, -1), coefficient * process['cyclesPerMinute']):
                        error(label, f'{side} coefficient mismatch for {item}')
        for item, value in disposal.items(): net[item] -= value
        for item, rate in target_flows.items(): net[item] -= rate
        for item, value in net.items():
            scale = max(raw.get(item, 0), sum(out.get(item, 0) for out in outputs_by_process.values()), 1)
            if not close(value, 0) and abs(value) > scale * 1e-8:
                error('production.conservation', f'{item} has unbalanced flow {value:.9g}/min')
        placement_counts = Counter()
        for index, placement in enumerate(placements):
            process = process_by_id.get(placement.get('processId'))
            if not process:
                error(f'placements[{index}]', 'unknown process')
                continue
            placement_counts[process['id']] += 1
            if placement.get('levelId') not in level_ids or not number(placement.get('clock')) or not close(placement['clock'], process['clock']):
                error(f'placements[{index}]', 'unknown level or inconsistent machine clock')
            for key in ('x', 'y', 'z', 'width', 'depth', 'height'):
                if not number(placement.get(key), positive=key in {'width', 'depth', 'height'}):
                    error(f'placements[{index}]', f'invalid {key}')
        for process in processes:
            if placement_counts[process['id']] != process.get('machines'):
                error('placements', f"count differs from machines for {process['id']}")
        routed = defaultdict(float)
        for stream in streams:
            label = 'infrastructure.streams.' + stream['id']
            item, to = stream.get('itemId'), stream.get('to')
            rate, capacity, lanes = stream.get('rate'), stream.get('capacity'), stream.get('lanes')
            if not all(number(value, positive=True) for value in (rate, capacity, lanes)) or not number(lanes, positive=True, integer=True):
                error(label, 'invalid stream rate, lane count or capacity')
                continue
            if rate > capacity * lanes + 1e-6:
                error(label, 'stream exceeds lane capacity')
            if item not in inputs_by_process.get(to, {}):
                error(label, 'stream consumer/input does not exist')
            sources = stream.get('from')
            if not isinstance(sources, list) or not sources:
                error(label, 'missing source group')
                continue
            for origin in sources:
                available = raw if origin == 'RAW' else outputs_by_process.get(origin, {})
                if item not in available:
                    error(label, f'source {origin} does not supply item')
            routed[(to, item)] += rate
        for process_id, inputs in inputs_by_process.items():
            for item, rate in inputs.items():
                if not close(routed[(process_id, item)], rate):
                    error('infrastructure.streams', f'consumer flow differs for {process_id}/{item}')
    world = project.get('map')
    if isinstance(world, dict):
        extractors = world.get('protectedExtractors', [])
        protected_coords = {(round(extractor['x'], 3), round(extractor['y'], 3)) for extractor in extractors if isinstance(extractor, dict) and number(extractor.get('x')) and number(extractor.get('y'))}
        protected_nodes = {extractor.get('node') for extractor in extractors if isinstance(extractor, dict)}
        for feed in world.get('feeds', []):
            if not isinstance(feed, dict):
                error('map.feeds', 'invalid feed')
                continue
            if feed.get('locationRole') == 'waterbody-reference':
                if feed.get('itemId') != 'Desc_Water_C' or feed.get('capacity') != 0 or ready['constructionReady']:
                    error('map.feeds', 'unverified water reference requires zero allocated capacity and blocked readiness')
                continue
            if feed.get('nodeId', feed.get('id')) in protected_nodes or (number(feed.get('x')) and number(feed.get('y')) and (round(feed['x'], 3), round(feed['y'], 3)) in protected_coords):
                error('map.feeds', 'new feed reuses protected extraction')
    if not ready['constructionReady']:
        warnings.append('Construction remains blocked/draft; validation does not clear gameplay or exact-visual acceptance.')
    return errors, warnings


@contextmanager
def writer_lock():
    lock_path = REPO / '.cache' / 'factory-publish.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield
        fcntl.flock(handle, fcntl.LOCK_UN)


def atomic_json(path, value):
    path = Path(path)
    data = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def publish_project(project, assets_root, *, replace=False, root=ROOT):
    root = Path(root)
    with writer_lock():
        errors, _ = validate_project(project, assets_root=assets_root, registry_root=root)
        if errors:
            raise ValueError('; '.join(errors))
        dest = root / project['saveId'] / project['id']
        if dest.is_symlink() or dest.parent.is_symlink():
            raise ValueError('publication target must not be a symlink')
        current = dest / 'project.json'
        if dest.exists() and not replace:
            raise FileExistsError('project already exists; replacement requires --replace')
        index = read_json(root / 'projects.json') if (root / 'projects.json').exists() else {'schemaVersion': 1, 'projects': []}
        old_bytes = current.read_bytes() if current.exists() else None
        old_index = (root / 'projects.json').read_bytes() if (root / 'projects.json').exists() else None
        signature = construction_signature(project, assets_root)
        if old_bytes is not None:
            previous = json.loads(old_bytes)
            previous_progress = previous.get('progressRevision', previous['revision'])
            current_progress = project.get('progressRevision', project['revision'])
            previous_signature = previous.get('progressSignature') or construction_signature(previous, dest)
            if previous_progress == current_progress and previous_signature != signature:
                raise ValueError('construction changed without a new progressRevision')
        root.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.factory-stage-', dir=root))
        created_dest = False
        promoted_revision = None
        try:
            published = json.loads(json.dumps(project))
            published['progressSignature'] = signature
            asset_prefix = f"/atlas/{project['saveId']}/{project['id']}/"
            version_prefix = asset_prefix + 'revisions/' + project['revision'] + '/'
            assets = stage / 'revision'
            assets.mkdir()
            replacements = {}
            for _, url in asset_references(project):
                source_file, suffix = asset_path(url, project, assets_root)
                suffix_parts = PurePosixPath(suffix).parts
                if len(suffix_parts) > 2 and suffix_parts[0] == 'revisions' and HASH_RE.fullmatch(suffix_parts[1]):
                    suffix = PurePosixPath(*suffix_parts[2:]).as_posix()
                target = assets / suffix
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source_file, target)
                replacements[url] = version_prefix + suffix
            def rewrite(value):
                if isinstance(value, str): return replacements.get(value, value)
                if isinstance(value, list): return [rewrite(item) for item in value]
                if isinstance(value, dict): return {key: rewrite(item) for key, item in value.items()}
                return value
            published = rewrite(published)
            if (assets / 'project.json').is_file():
                (assets / 'project.json').write_text(json.dumps(published, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                (stage / 'project' / 'revisions').mkdir(parents=True)
                os.replace(assets, stage / 'project' / 'revisions' / project['revision'])
                (stage / 'project' / 'project.json').write_text(json.dumps(published, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                os.replace(stage / 'project', dest)
                created_dest = True
            else:
                versions = dest / 'revisions'
                versions.mkdir(exist_ok=True)
                version = versions / project['revision']
                if version.exists():
                    for candidate in assets.rglob('*'):
                        if candidate.is_file() and (not (version / candidate.relative_to(assets)).is_file() or digest(candidate) != digest(version / candidate.relative_to(assets))):
                            raise ValueError('revision already exists with different asset bytes')
                else:
                    os.replace(assets, version)
                    promoted_revision = version
                atomic_json(current, published)
            keys = ('id', 'saveId', 'kind', 'title', 'subtitle', 'revision', 'updatedAt', 'status', 'target', 'preview', 'drawingCount', 'zoneCount')
            summary = {key: published[key] for key in keys if key in published}
            index['projects'] = [item for item in index['projects'] if (item['saveId'], item['id']) != (project['saveId'], project['id'])] + [summary]
            atomic_json(root / 'projects.json', index)
        except Exception:
            if created_dest:
                shutil.rmtree(dest)
            elif old_bytes is not None:
                fd, temp = tempfile.mkstemp(prefix='.project-rollback-', dir=dest)
                with os.fdopen(fd, 'wb') as handle: handle.write(old_bytes)
                os.replace(temp, current)
            if promoted_revision is not None and promoted_revision.exists():
                shutil.rmtree(promoted_revision)
            if old_index is not None and (root / 'projects.json').read_bytes() != old_index:
                fd, temp = tempfile.mkstemp(prefix='.index-rollback-', dir=root)
                with os.fdopen(fd, 'wb') as handle: handle.write(old_index)
                os.replace(temp, root / 'projects.json')
            raise
        finally:
            shutil.rmtree(stage)
    return dest
