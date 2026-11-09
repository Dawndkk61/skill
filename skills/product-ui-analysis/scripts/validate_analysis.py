#!/usr/bin/env python3
"""Validate analysis evidence, bounds, references and embedded report data."""
import argparse
import hashlib
import json
import mimetypes
import re
from pathlib import Path
from sample_png import inspect, bounds

CATEGORIES = ['colors', 'radius', 'spacing', 'borders', 'text', 'weight', 'size']
EVIDENCE = ['observation', 'sample', 'estimate', 'config', 'inference', 'unknown']


def validate(data, base):
    errors, source_ids, components, page_ids, variable_ids = [], {}, set(), set(), set()
    def check(condition, message):
        if not condition: errors.append(message)
    def identifier(value, label):
        check(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]+', value) is not None, 'Invalid '+label)
    check(bool(data.get('product')), 'Missing product')
    check(bool(data.get('pages')), 'No pages')
    for page in data.get('pages', []):
        pid = page.get('id'); identifier(pid, 'page ID')
        check(pid not in page_ids, 'Duplicate page '+str(pid)); page_ids.add(pid)
        check(bool(page.get('title')), 'Missing page title '+str(pid))
        check(bool(page.get('sources')), 'No sources '+str(pid))
        for mode, source in page.get('sources', {}).items():
            sid = source.get('id'); identifier(sid, 'source ID')
            check(sid not in source_ids, 'Duplicate source '+str(sid)); source_ids[sid] = source
            w, h = source.get('width'), source.get('height')
            check(isinstance(w, int) and isinstance(h, int) and min(w, h) > 0, 'Invalid source dimensions '+str(sid))
            path = (base/source.get('path', '')).resolve()
            check(path.is_file(), 'Missing image '+str(path))
            if path.is_file():
                if source.get('sha256'): check(hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256'], 'Image hash changed '+str(sid))
                if path.suffix.lower() == '.png':
                    try:
                        meta = inspect(path)
                        check((w, h) == (meta['width'], meta['height']), 'Source dimensions differ '+str(sid))
                    except (ValueError, IndexError) as e: errors.append(str(e))
        for component in page.get('components', []):
            cid = component.get('id'); identifier(cid, 'component ID')
            check((pid, cid) not in components, 'Duplicate component '+str(cid)); components.add((pid, cid))
            for field in ('facts', 'inferences', 'notes'):
                check(all(isinstance(s, str) for s in component.get(field, [])), 'Invalid '+field+' '+str(cid))
            for mode, box in component.get('bounds', {}).items():
                check(mode in page.get('sources', {}), 'Bounds reference unavailable mode '+mode)
                if mode in page.get('sources', {}):
                    source = page['sources'][mode]
                    try: bounds(box, source['width'], source['height'])
                    except (ValueError, TypeError) as e: errors.append(str(cid)+': '+str(e))
    brand = data.get('brand') or {}
    check(isinstance(brand, dict), 'Brand must be an object')
    logo = brand.get('logo') if isinstance(brand, dict) else None
    if logo is not None:
        check(isinstance(logo, dict), 'Logo must be an object')
        if isinstance(logo, dict):
            check(isinstance(logo.get('path'), str) and bool(logo.get('path')), 'Logo path missing')
            logo_path = (base/(logo.get('path') if isinstance(logo.get('path'), str) else '')).resolve()
            check(logo_path.is_file(), 'Missing logo '+str(logo_path))
            check(mimetypes.guess_type(str(logo_path))[0] in ('image/png', 'image/jpeg', 'image/webp'), 'Unsupported logo format')
            check(logo.get('blendMode', 'normal') in ('normal', 'darken', 'lighten'), 'Invalid logo blendMode')
            if logo_path.is_file() and logo.get('sha256'):
                check(hashlib.sha256(logo_path.read_bytes()).hexdigest() == logo['sha256'], 'Logo hash changed')
            if logo.get('sourceId') is not None:
                check(logo['sourceId'] in source_ids, 'Logo has unknown source')
            if 'box' in logo:
                source = source_ids.get(logo.get('sourceId'))
                check(source is not None, 'Logo crop needs a sourceId')
                if source:
                    try: bounds(logo['box'], source['width'], source['height'])
                    except (ValueError, TypeError) as e: errors.append('Logo: '+str(e))
    for variable in data.get('variables', []):
        vid = variable.get('id'); identifier(vid, 'variable ID')
        check(vid not in variable_ids, 'Duplicate variable '+str(vid)); variable_ids.add(vid)
        check(variable.get('category') in CATEGORIES, 'Unknown category '+str(vid))
        check(variable.get('kind') in ('color', 'number', 'string'), 'Unknown value kind '+str(vid))
        check(('value' in variable) != ('values' in variable), 'Provide value OR values '+str(vid))
        values = list(variable.get('values', {}).values()) if 'values' in variable else [variable.get('value')]
        check(bool(values), 'Empty values '+str(vid))
        if variable.get('kind') == 'color':
            check(all(v is None or isinstance(v, str) and re.fullmatch(r'#[a-fA-F0-9]{6}', v) for v in values), 'Invalid color '+str(vid))
        if variable.get('kind') == 'number':
            check(bool(variable.get('unit')), 'Numeric unit missing '+str(vid))
            check(all(v is None or type(v) in (int, float) for v in values), 'Invalid number '+str(vid))
        evidence = variable.get('evidence', {})
        check(evidence.get('type') in EVIDENCE, 'Invalid evidence type '+str(vid))
        if any(v is None for v in values): check(evidence.get('type') == 'unknown', 'Unknown value must be labeled unknown '+str(vid))
        check(bool(evidence.get('sourceIds')), 'Evidence has no source '+str(vid))
        for sid in evidence.get('sourceIds', []): check(sid in source_ids, 'Unknown source '+str(sid))
        for sample in evidence.get('samples', []):
            source = source_ids.get(sample.get('sourceId'))
            check(source is not None, 'Sample has unknown source '+str(vid))
            if source:
                try: bounds(sample.get('box', []), source['width'], source['height'])
                except (ValueError, TypeError) as e: errors.append(str(vid)+': '+str(e))
        check(bool(variable.get('applications')), 'Variable has no application '+str(vid))
        for ref in variable.get('applications', []):
            check((ref.get('page'), ref.get('component')) in components, 'Unknown component application '+str(vid))
            check(bool(ref.get('property')), 'Application property missing '+str(vid))
    if data.get('captureStandard'):
        standard = data['captureStandard']
        check(isinstance(standard, dict), 'captureStandard must be an object')
        if isinstance(standard, dict):
            check(type(standard.get('width')) in (int, float) and standard['width'] > 0, 'Invalid standard width')
            check(type(standard.get('height')) in (int, float) and standard['height'] > 0, 'Invalid standard height')
            if not errors and standard.get('confirmed'):
                from calibrate_analysis import calibrate
                expected = calibrate(data, standard['width'], standard['height'], standard.get('allowFullWidthPartialHeight', False))
                for page, actual_page in zip(expected['pages'], data['pages']):
                    for mode, source in actual_page['sources'].items():
                        if 'displayMapping' in source:
                            check(source['displayMapping'] == page['sources'][mode]['displayMapping'], 'Invalid source mapping '+source['id'])
                    for c, actual in zip(page['components'], actual_page.get('components', [])):
                        if 'standardBounds' in actual: check(actual['standardBounds'] == c['standardBounds'], 'Incorrect standardized bounds '+actual['id'])
                        for e, a in zip(c.get('estimates', []), actual.get('estimates', [])):
                            if 'standard' in a: check(a['standard'] == e.get('standard'), 'Incorrect standardized estimate '+str(actual['id']))
                for expected_v, actual_v in zip(expected.get('variables', []), data.get('variables', [])):
                    if 'standard' in actual_v: check(actual_v['standard'] == expected_v.get('standard'), 'Incorrect standardized variable '+actual_v['id'])
    return errors


def validate_report(report, data):
    return validate_report_html(Path(report).read_text(encoding='utf-8'), data)


def validate_report_html(html, data):
    standard = data.get('captureStandard') or {}
    if standard.get('confirmed'):
        from calibrate_analysis import calibrate
        data = calibrate(data, standard['width'], standard['height'], standard.get('allowFullWidthPartialHeight', False))
    errors = []
    match = re.search(r'<script id="analysis-data" type="application/json">([\s\S]*?)</script>', html)
    if not match: return ['Report missing embedded analysis data']
    embedded = json.loads(match.group(1))
    for key in ('product', 'surface', 'conclusion', 'variables'):
        if embedded.get(key) != data.get(key): errors.append('Report differs from manifest: '+key)
    ids = re.findall(r'\bid="([^"\s]+)"', html.split('<script')[0])
    if len(ids) != len(set(ids)): errors.append('Duplicate static HTML IDs')
    if re.search(r'<(?:script|link)[^>]+(?:src|href)=["\'](?:https?:|file:)', html): errors.append('External runtime dependency')
    if '__PAYLOAD__' in html: errors.append('Unfilled template payload')
    runtime = html[:match.start()]+html[match.end():]
    if any(page.get('components') for page in data.get('pages', [])):
        page_view = re.search(r'function pageView\(p\)\{([\s\S]*?)(?=\nfunction |</script>)', runtime)
        if not page_view or 'componentVariables(p,c,mode)' not in page_view.group(1):
            errors.append('Page components must mount their related design-variable display')
        component_view = re.search(r'function componentVariables\(p,c,mode\)\{([\s\S]*?)(?=\nfunction |/\* END_PRODUCT_UI_COMPONENT_VARIABLES|</script>)', runtime)
        if not component_view:
            errors.append('Missing component variable renderer')
        elif re.search(r'\bdata-mode=', component_view.group(1)):
            errors.append('Component variable panels must not share the theme-button data-mode event selector')
    # Check the final runtime too: product-specific postprocessors previously
    # inserted large summary sections despite the compact shared template.
    if not (data.get('reportLayout') or {}).get('allowOverviewSummary', False):
        overview = re.search(r'function variableView\(\)\{([\s\S]*?)(?=\nfunction |</script>)', runtime)
        if overview and re.search(r'<section\b', overview.group(1)):
            errors.append('Compact overview must go directly from introduction to variable tables; remove extra summary sections')
        if re.search(r'<section\s+class=(?:["\']|\\["\'])findings|EVIDENCE COVERAGE', runtime):
            errors.append('Legacy design-findings / theme-coverage summary is not allowed in compact reports')
    logo = (data.get('brand') or {}).get('logo')
    if logo:
        embedded_logo = embedded.get('brand', {}).get('logo', {})
        if not embedded_logo.get('image', '').startswith(('data:image/png;', 'data:image/jpeg;', 'data:image/webp;')):
            errors.append('Logo not embedded')
        for key in ('path', 'sourceId', 'box', 'blendMode', 'description'):
            if embedded_logo.get(key) != logo.get(key): errors.append('Logo metadata differs: '+key)
    for page in embedded.get('pages', []):
        for source in page.get('sources', {}).values():
            if not source.get('image', '').startswith('data:image/'): errors.append('Image not embedded')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest'); parser.add_argument('--report'); parser.add_argument('--output')
    args = parser.parse_args(); path = Path(args.manifest).resolve()
    data = json.loads(path.read_text(encoding='utf-8'))
    errors = validate(data, path.parent)
    if args.report: errors += validate_report(args.report, data)
    result = {'status': 'failed' if errors else 'passed', 'scope': 'data, image metadata, bounds, evidence references and embedded payload; rendered interaction still requires UI verification', 'errors': errors}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output: Path(args.output).write_text(text, encoding='utf-8')
    print(text)
    raise SystemExit(bool(errors))


if __name__ == '__main__': main()
