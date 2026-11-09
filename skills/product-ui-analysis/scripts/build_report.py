#!/usr/bin/env python3
"""Build a self-contained, evidence-led report from an analysis manifest."""
import argparse
import base64
import copy
import hashlib
import json
import mimetypes
from pathlib import Path
from sample_png import read_png, crop_png
from validate_analysis import validate, validate_report_html
from calibrate_analysis import calibrate
from report_calibration import enhance_html


def uri(blob, mime):
    return 'data:'+mime+';base64,'+base64.b64encode(blob).decode('ascii')


def build(manifest, output):
    manifest, output = Path(manifest).resolve(), Path(output).resolve()
    data = json.loads(manifest.read_text(encoding='utf-8'))
    errors = validate(data, manifest.parent)
    if errors: raise ValueError('\n'.join(errors))
    standard = data.get('captureStandard') or {}
    if standard.get('confirmed'):
        data = calibrate(data, standard['width'], standard['height'], standard.get('allowFullWidthPartialHeight', False))
    rendered = copy.deepcopy(data)
    logo = (rendered.get('brand') or {}).get('logo')
    if logo:
        path = (manifest.parent/logo['path']).resolve()
        mime = mimetypes.guess_type(str(path))[0]
        if mime not in ('image/png', 'image/jpeg', 'image/webp'):
            raise ValueError('Logo must be PNG, JPEG or WebP: '+str(path))
        blob = path.read_bytes()
        logo['image'] = uri(blob, mime)
        logo['sha256'] = hashlib.sha256(blob).hexdigest()
    for page in rendered['pages']:
        for mode, source in page['sources'].items():
            path = (manifest.parent/source['path']).resolve()
            blob = path.read_bytes()
            mime = mimetypes.guess_type(str(path))[0]
            if mime not in ('image/png', 'image/jpeg', 'image/webp'): raise ValueError('Use PNG, JPEG or WebP: '+str(path))
            source['image'] = uri(blob, mime); source['path'] = path.name
            source['sha256'] = hashlib.sha256(blob).hexdigest()
            decoded = None
            for component in page.get('components', []):
                box = component.get('bounds', {}).get(mode)
                if box:
                    if mime != 'image/png': raise ValueError('For auto-crops, supply a PNG analysis copy: '+str(path))
                    if decoded is None: decoded = read_png(path)
                    component.setdefault('images', {})[mode] = uri(crop_png(path, box, decoded), 'image/png')
    template = Path(__file__).resolve().parent.parent/'assets'/'report.html'
    payload = json.dumps(rendered, ensure_ascii=False).replace('<', '\\u003c')
    output.parent.mkdir(parents=True, exist_ok=True)
    html = template.read_text(encoding='utf-8').replace('__PAYLOAD__', payload)
    if standard.get('confirmed'): html = enhance_html(html)
    errors = validate_report_html(html, data)
    if errors: raise ValueError('\n'.join(errors))
    output.write_text(html, encoding='utf-8')
    return {'report': str(output), 'pages': len(data['pages']), 'variables': len(data.get('variables', [])), 'bytes': output.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest'); parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.manifest, args.output), ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
