"""Validate registered worlds without embedding one save's engineering profile."""
from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path

from satisfactory.projects import ROOT, ID_RE, close, read_json, validate_project


def local_document(base, relative):
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        raise ValueError('Missing or escaping world document: ' + str(relative))
    return read_json(path)


def project_world_url(project, worlds_root=None):
    worlds_root = Path(worlds_root) if worlds_root else ROOT.parent / 'worlds'
    for record in read_json(worlds_root / 'index.json')['worlds']:
        if record['saveId'] != project['saveId']:
            continue
        manifest = local_document(worlds_root / record['id'], 'manifest.json')
        summary = next((item for item in manifest['projects'] if item['id'] == project['id']), None)
        if summary:
            return f"/worlds/{record['id']}/tiers/{summary['tier']}/{summary['category']}/{summary['id']}"
    return None


def expected_extraction(profile, miner, clock, purity):
    return profile['normalRates'][str(miner)] * profile['purityFactors'][purity] * clock


def validate_world(root=ROOT, worlds_root=None):
    root = Path(root)
    worlds_root = Path(worlds_root) if worlds_root else root.parent / 'worlds'
    registry = read_json(worlds_root / 'index.json')
    records = registry['worlds']
    errors, warnings, results = [], [], []
    if registry.get('schemaVersion') != 1 or not isinstance(records, list):
        return {'ok': False, 'errors': ['world registry: unsupported schema'], 'warnings': []}
    for field in ('id', 'saveId'):
        values = [record[field] for record in records]
        if len(values) != len(set(values)) or any(not ID_RE.fullmatch(value) for value in values):
            errors.append(f'world registry: duplicate or unsafe {field}')
    saves = {record['id']: record for record in read_json(root / 'saves.json')['saves']}
    catalogue = read_json(root / 'projects.json')['projects']
    registered_pairs = {(item['saveId'], item['id']) for item in catalogue}
    all_pairs = set()
    for record in records:
        ident, save_id = record['id'], record['saveId']
        if not ID_RE.fullmatch(ident) or not ID_RE.fullmatch(save_id):
            continue
        base = worlds_root / ident
        manifest = local_document(base, 'manifest.json')
        prefix = f'{ident}: '
        if manifest.get('schemaVersion') != 1 or manifest.get('id') != ident or manifest.get('saveId') != save_id:
            errors.append(prefix + 'manifest world/save identity differs from registry')
        if save_id not in saves or saves[save_id]['sourceSha256'] != manifest['saveSha256']:
            errors.append(prefix + 'save source differs from registered snapshot')
        analyses = {}
        for entry in manifest['analyses']:
            if not ID_RE.fullmatch(entry['id']) or entry['path'] != f"analysis/{entry['id']}.json":
                errors.append(prefix + 'unsafe analysis path')
                continue
            document = local_document(base, entry['path'])
            if hashlib.sha256((base / entry['path']).read_bytes()).hexdigest() != entry.get('sha256'):
                errors.append(prefix + entry['id'] + ': analysis content hash mismatch')
            if any(document.get(key) != value for key, value in [('worldId', ident), ('saveId', save_id), ('saveSha256', manifest['saveSha256'])]):
                errors.append(prefix + entry['id'] + ': analysis world/save/source identity mismatch')
            if document['id'] != entry['id'] or entry['id'] in analyses:
                errors.append(prefix + 'duplicate/mismatched analysis identity')
            analyses[entry['id']] = document
        source = analyses.get(manifest['sourceAnalysisId'])
        if not source or source.get('saveSha256') != manifest['saveSha256']:
            errors.append(prefix + 'source analysis belongs to another snapshot')
        source_entry = next((entry for entry in manifest['analyses'] if entry['id'] == manifest['sourceAnalysisId']), {})
        for analysis_id, document in analyses.items():
            if analysis_id != manifest['sourceAnalysisId'] and document.get('sourceSha256') != source_entry.get('sha256'):
                errors.append(prefix + analysis_id + ': stale source analysis digest')
            if any(dependency not in analyses for dependency in document.get('dependsOn', [])):
                errors.append(prefix + analysis_id + ': unknown analysis dependency')
        nodes = {node['id']: node for analysis in analyses.values() for node in analysis.get('nodes', [])}
        node_ids = set(nodes)
        summaries = manifest['projects']
        project_ids = {summary['id'] for summary in summaries}
        if len(project_ids) != len(summaries):
            errors.append(prefix + 'duplicate project IDs')
        known = {(save_id, project_id) for project_id in project_ids}
        all_pairs.update(known)
        if not known <= registered_pairs:
            errors.append(prefix + 'world projects missing from atlas catalogue')
        documents = {}
        for summary in summaries:
            project_id = summary['id']
            if not ID_RE.fullmatch(project_id):
                errors.append(prefix + 'unsafe project ID')
                continue
            project = read_json(root / save_id / project_id / 'project.json')
            documents[project_id] = project
            found, notes = validate_project(project, registry_root=root, known_projects=known)
            errors.extend(prefix + project_id + ': ' + message for message in found)
            warnings.extend(prefix + project_id + ': ' + message for message in notes)
            if project['saveId'] != save_id or project['id'] != project_id or project['source']['saveSha256'] != manifest['saveSha256']:
                errors.append(prefix + project_id + ': cross-world save/source association')
            if project['revision'] != summary['revision'] or len(project['build']['steps']) != summary['stages']:
                errors.append(prefix + project_id + ': manifest revision/stage count mismatch')
            if summary['category'] != ('factories' if project['kind'] == 'factory' else 'global'):
                errors.append(prefix + project_id + ': wrong project category')
            site = project.get('sitePlan')
            placements = project['placements']
            if site:
                for placement in placements:
                    for axis, extent in [('x', 'width'), ('y', 'depth')]:
                        if placement[axis] - placement[extent] / 2 < 0 or placement[axis] + placement[extent] / 2 > site[extent]:
                            errors.append(prefix + project_id + ': placement outside floor')
            for index, left in enumerate(placements):
                for right in placements[index + 1:]:
                    if left['levelId'] == right['levelId'] and abs(left['x'] - right['x']) < (left['width'] + right['width']) / 2 and abs(left['y'] - right['y']) < (left['depth'] + right['depth']) / 2:
                        errors.append(prefix + project_id + ': overlapping machine footprints')
            minimum_clock = manifest.get('engineering', {}).get('extraction', {}).get('minimumClock', 0)
            for extractor in project.get('extraction', []):
                if extractor['nodeId'] not in node_ids or extractor['clock'] < minimum_clock:
                    errors.append(prefix + project_id + ': unknown node or disallowed extractor clock')
                if extractor['lanes'] > extractor['ports'] or extractor['perLane'] > extractor['belt'] or not close(extractor['perLane'] * extractor['lanes'], extractor['raw']):
                    errors.append(prefix + project_id + ': extractor line/port mismatch')
                extraction_profile = manifest.get('engineering', {}).get('extraction')
                if extraction_profile and extractor['nodeId'] in nodes:
                    try:
                        expected = expected_extraction(extraction_profile, extractor['miner'], extractor['clock'], nodes[extractor['nodeId']]['purity'])
                        if not close(extractor['raw'], expected):
                            errors.append(prefix + project_id + ': extractor output differs from node/clock/profile')
                    except KeyError:
                        errors.append(prefix + project_id + ': unsupported extractor or purity')
            stage_ids = {step['id'] for step in project['build']['steps']}
            for step in project['build']['steps']:
                if any(item not in stage_ids for item in step['prerequisites']):
                    errors.append(prefix + project_id + ': missing predecessor stage')
        tier_ids = {tier['id'] for tier in manifest['tiers']}
        if len(tier_ids) != len(manifest['tiers']):
            errors.append(prefix + 'duplicate tier IDs')
        for tier in manifest['tiers']:
            for project_id in tier['globals'] + tier['factories'] + [step['project'] for step in tier['sequence']]:
                if project_id not in project_ids:
                    errors.append(prefix + f"tier{tier['id']}: unknown project {project_id}")
        for summary in summaries:
            if summary['tier'] not in tier_ids:
                errors.append(prefix + 'project points to an unknown tier')
        world_map = manifest.get('map')
        if world_map:
            bounds = world_map['bounds']
            if len(bounds) != 4 or bounds[0] >= bounds[1] or bounds[2] >= bounds[3] or world_map['gridMeters'] <= 0:
                errors.append(prefix + 'invalid map bounds/grid')
            if any(key not in analyses for key in [world_map['nodeAnalysisId'], world_map['siteAnalysisId']]):
                errors.append(prefix + 'unknown map analysis')
            for site in analyses.get(world_map['siteAnalysisId'], {}).get('sites', []):
                if site.get('projectId') and site['projectId'] not in project_ids:
                    errors.append(prefix + 'site links to a foreign/unknown project')
        profile = manifest.get('engineering', {})
        extraction = profile.get('extraction')
        states = analyses.get(extraction['analysisId'], {}).get('states', []) if extraction else []
        for state in states:
            try:
                expected = expected_extraction(extraction, state['miner'], state['clock'], state['purity'])
                if not close(state['raw'], expected) or state['lanes'] > state['ports'] or state['perLane'] > state['belt'] or not close(state['lanes'] * state['perLane'], state['raw']):
                    errors.append(prefix + 'invalid extraction state for this world profile')
            except KeyError:
                errors.append(prefix + 'unsupported extraction state for this world profile')
        if profile.get('powerFile'):
            for state in local_document(base, profile['powerFile'])['states']:
                if not close(state['totalMW'], state['processMW'] + state['extractorsMW'] + state['waterMW']) or state['generationMW'] < state['requiredWithReserveMW']:
                    errors.append(prefix + state['id'] + ': invalid power balance/headroom')
        phase = profile.get('phaseWindows')
        if phase:
            for window in analyses[phase['analysisId']]['phaseWindows']:
                for resource, coefficients in phase['coefficients'].items():
                    if not close(window[resource], sum(window[product] * value for product, value in coefficients.items())):
                        errors.append(prefix + 'phase window differs from world recipe coefficients')
        results.append({'id': ident, 'saveId': save_id, 'projects': len(documents), 'stages': sum(len(project['build']['steps']) for project in documents.values()), 'drawings': sum(len(project['drawings']) for project in documents.values()), 'extractorStates': len(states), 'manifestSha256': hashlib.sha256((base / 'manifest.json').read_bytes()).hexdigest()})
    if all_pairs != registered_pairs:
        errors.append('world registry/catalogue project ownership differs')
    return {'ok': not errors, 'worlds': results, 'errors': errors, 'warnings': warnings, 'gameplay': 'unverified; data validation does not certify terrain or runtime mod interactions'}
