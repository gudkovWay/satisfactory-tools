#!/usr/bin/env python3
"""Read-only planning context and validated publication for the factory atlas."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from satisfactory import paths, save
from satisfactory.projects import ROOT, asset_path, publish_project, read_json, validate_project


class RequestError(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise RequestError(message)


def digest(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def emit(value, *, error=False):
    print(json.dumps(value, ensure_ascii=False, indent=2), file=sys.stderr if error else sys.stdout)


def parse_request(words, kind):
    words = list(words)
    if words and words[0] in {'road', 'depot', 'warehouse'} and kind == 'factory':
        kind = words.pop(0)
    text = ' '.join(words).strip()
    if kind != 'factory':
        return {'kind': kind, 'title': text or kind, 'target': None, 'rate': None, 'unit': None}
    match = re.fullmatch(r'(.+?)\s+(\d+(?:[.,]\d+)?)(?:\s*(?:per\s+min(?:ute)?|/min|/мин|в\s+минуту))?', text, re.IGNORECASE)
    if not match:
        raise RequestError('Use: modular engine 100 per min [--save cachys], or road|depot|warehouse <description>.')
    rate = float(match[2].replace(',', '.'))
    if not 0 < rate < float('inf'):
        raise RequestError('Factory rate must be positive and finite.')
    return {'kind': kind, 'title': match[1], 'target': match[1], 'rate': rate, 'unit': 'per min'}


def select_save(save_id, explicit_file=None):
    records = read_json(ROOT / 'saves.json')['saves']
    if save_id is None:
        if len(records) != 1:
            raise RequestError('Select --save from the registered save IDs: ' + ', '.join(record['id'] for record in records))
        record = records[0]
    else:
        record = next((record for record in records if save_id in {record['id'], record['name']}), None)
        if record is None:
            raise RequestError(f'Unregistered save {save_id!r}; register its source snapshot before planning.')
    candidates, failures = [], []
    if explicit_file:
        files = [str(Path(explicit_file).expanduser())]
    else:
        directories = paths.save_dirs()
        files = [path for directory in directories for path in paths.saves(directory)]
    for filename in files:
        path = Path(filename)
        try:
            header = save.read_header(path)
            matches = header.get('sessionName') == record['sessionName'] or path.stem == record['id']
            if matches:
                candidates.append((path.stat().st_mtime_ns, path, header))
        except (OSError, ValueError, IndexError, UnicodeError) as exc:
            if explicit_file or path.stem.startswith((record['id'], record['sessionName'])):
                failures.append(f'{path.name}: {exc}')
    if not candidates:
        raise RequestError('No readable matching source save was found. ' + '; '.join(failures))
    _, selected, header = max(candidates, key=lambda candidate: (candidate[0], str(candidate[1])))
    return record, selected, header


def find_game_root():
    for library in paths.steam_libraries():
        candidate = Path(library) / 'steamapps' / 'common' / 'Satisfactory'
        if (candidate / 'FactoryGame').is_dir():
            return candidate
    return None


def planning_context(args):
    request = parse_request(args.request, args.kind)
    record, selected, header = select_save(args.save, args.save_file)
    selected_hash = digest(selected)
    snapshot_file = ROOT / record['id'] / 'source-evidence.json'
    blocking, fingerprint = [], []
    snapshot = read_json(snapshot_file) if snapshot_file.is_file() else None
    if snapshot is None:
        blocking.append('The save has no source-evidence.json containing installed mod/settings fingerprints and unlock provenance.')
    else:
        game = Path(args.game_dir).expanduser().resolve() if args.game_dir else find_game_root()
        saved_root = selected.parents[2]
        for item in snapshot.get('fingerprints', []):
            base = game if item['root'] == 'game' else saved_root if item['root'] == 'saved' else None
            relative = Path(item['path'])
            if relative.is_absolute() or '..' in relative.parts:
                raise RequestError('Unsafe source fingerprint path in registered evidence.')
            candidate = base / relative if base else None
            state = 'missing' if candidate is None or not candidate.is_file() else 'match' if digest(candidate) == item['sha256'] else 'changed'
            fingerprint.append({'root': item['root'], 'path': item['path'], 'status': state})
        if not fingerprint or any(item['status'] != 'match' for item in fingerprint):
            blocking.append('Installed game/mod/settings inputs differ from the frozen recipe snapshot or cannot be read; re-extract affected evidence before calculating.')
        if game:
            expected_manifests = {item['path'] for item in snapshot.get('fingerprints', []) if item['root'] == 'game' and item['path'].endswith('.uplugin')}
            actual_manifests = {path.relative_to(game).as_posix() for path in (game / 'FactoryGame/Mods').rglob('*.uplugin')}
            if expected_manifests != actual_manifests:
                blocking.append('Installed mod manifest inventory changed; refresh the mod and recipe extraction.')
    index = read_json(ROOT / 'projects.json')['projects']
    recipe_candidates = []
    for project in index:
        if project['saveId'] != record['id']:
            continue
        document = read_json(ROOT / project['saveId'] / project['id'] / 'project.json')
        production = document.get('production')
        if production:
            candidate, _ = asset_path(production['recipesFile'], document, ROOT / project['saveId'] / project['id'])
            data = read_json(candidate)
            recipe_candidates.append((candidate, data, data.get('provenance', {}).get('save_sha256') == selected_hash))
    chosen = next((candidate for candidate in recipe_candidates if candidate[2]), recipe_candidates[0] if recipe_candidates else None)
    if chosen is None:
        blocking.append('No normalized unlocked recipe inventory exists for this save.')
    elif not chosen[2]:
        blocking.append('Recipe/unlock snapshot does not match the latest source save hash; refresh it rather than substituting vanilla recipes.')
    return {
        'ok': True, 'request': {**request, 'save': record['id']},
        'save': {'id': record['id'], 'sessionName': header.get('sessionName'), 'path': str(selected), 'sha256': selected_hash, 'header': {key: value for key, value in header.items() if key != 'mapOptions'}},
        'snapshot': {'path': str(snapshot_file) if snapshot else None, 'fresh': not blocking, 'fingerprints': fingerprint,
                     'mods': snapshot.get('mods', []) if snapshot else [], 'settings': snapshot.get('settings', {}) if snapshot else {}},
        'recipes': {'path': str(chosen[0]), 'sha256': digest(chosen[0]), 'unlockedCount': len(chosen[1]['recipes']), 'saveMatches': chosen[2]} if chosen else None,
        'existingProjects': [{'id': project['id'], 'kind': project['kind'], 'path': str(ROOT / project['saveId'] / project['id'] / 'project.json')} for project in index if project['saveId'] == record['id']],
        'blocking': blocking,
        'next': 'Compare supported full recipe chains, audit existing allocations, produce a complete ProjectDocument and assets, validate and publish. Never mutate saves or label a schematic as an exact game render.'
    }


def load_document(filename):
    path = Path(filename).expanduser().resolve()
    return path, read_json(path)


def main(argv=None):
    parser = Parser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare', help='Read actual save identity, pinned recipes and installed-source freshness.')
    prepare.add_argument('request', nargs='*')
    prepare.add_argument('--save')
    prepare.add_argument('--save-file')
    prepare.add_argument('--game-dir')
    prepare.add_argument('--kind', choices=['factory', 'road', 'depot', 'warehouse'], default='factory')
    validate = commands.add_parser('validate', help='Check full project/assets/recipe arithmetic without publishing.')
    validate.add_argument('project')
    validate.add_argument('--assets')
    publish = commands.add_parser('publish', help='Publish validated project and immutable asset revision.')
    publish.add_argument('project')
    publish.add_argument('--assets', required=True)
    publish.add_argument('--replace', action='store_true')
    try:
        args = parser.parse_args(argv)
        if args.command == 'prepare':
            emit(planning_context(args))
            return 0
        source, document = load_document(args.project)
        assets_root = Path(args.assets).expanduser().absolute() if args.assets else source.parent
        errors, warnings = validate_project(document, assets_root=assets_root)
        if errors:
            emit({'ok': False, 'errors': errors, 'warnings': warnings}, error=True)
            return 2
        if args.command == 'validate':
            emit({'ok': True, 'project': f"{document['saveId']}/{document['id']}", 'revision': document['revision'], 'warnings': warnings})
        else:
            destination = publish_project(document, assets_root, replace=args.replace)
            emit({'ok': True, 'published': str(destination), 'url': f"/projects/{document['saveId']}/{document['id']}", 'warnings': warnings})
        return 0
    except (RequestError, OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
        emit({'ok': False, 'error': str(exc)}, error=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
