#!/usr/bin/env python3
"""Derive standard-viewport geometry while retaining original image pixels and bounds."""
import argparse
import copy
import json
import math
import re
from pathlib import Path


def fmt(value):
    return format(round(value, 6), '.6f').rstrip('0').rstrip('.')


def convert_value(value, scale):
    if type(value) in (int, float):
        return round(value/scale, 6)
    if isinstance(value, str) and re.fullmatch(r'\s*\d+(?:\.\d+)?(?:\s*[×x]\s*\d+(?:\.\d+)?)*\s*', value):
        return ' × '.join(fmt(float(x)/scale) for x in re.split(r'\s*[×x]\s*', value.strip()))
    return None


def convert_tolerance(text, scale):
    match = re.search(r'±\s*(\d+(?:\.\d+)?)(?:\s*[–—-]\s*(\d+(?:\.\d+)?))?', str(text or ''))
    if not match:
        return '原记录未量化该参数误差' if text else ''
    first = fmt(float(match.group(1))/scale)
    second = '–'+fmt(float(match.group(2))/scale) if match.group(2) else ''
    return '±'+first+second+' 标准 px'


def source_mapping(source, width, height, allow_partial):
    sx, sy = source['width']/width, source['height']/height
    full = math.isclose(sx, sy, rel_tol=1e-7, abs_tol=1e-7)
    partial = allow_partial and source['height'] < height*sx and math.isclose(sx, round(sx), abs_tol=1e-7) and sx >= 1
    if not full and not partial:
        return {'status': 'unresolved', 'reason': '截图纵横倍率不一致；未给出可靠的裁切/缩放映射，保留原图单位。'}
    return {'status': 'mapped', 'scale': sx, 'scaleX': sx, 'scaleY': sx,
            'standardSize': [round(source['width']/sx, 6), round(source['height']/sx, 6)],
            'basis': '用户确认的截图工作区标准；按完整帧等比换算' if full else '按已确认的全宽等比换算；高度覆盖不足完整工作区，不单独拉伸高度',
            'frame': 'full' if full else 'full-width-partial-height',
            'coordinateOrigin': '截图自身左上角；不推断显示器绝对原点或裁切偏移'}


def calibrated_note(note, width=2560, height=1440, scale=2):
    text = str(note)
    standard = str(width)+'×'+str(height)
    factor = fmt(scale)+'×'
    replacements = [
        ('截图倍率未标定，未换算为确定 CSS px。', '按用户确认的 '+standard+' 标准等比换算；标准 px 是分析单位，不等于已验证源码 CSS px。'),
        ('截图倍率未校准', '现已按用户确认的截图工作区标准换算'),
        ('截图倍率未标定', '现已按用户确认的截图工作区标准换算'),
        ('倍率未标定', '现已按用户确认的截图工作区标准换算'),
        ('2× 换算仅为假设', '当前 '+factor+' 换算依据用户确认的 '+standard+' 标准'),
        ('2× 参考值未标定', '当前 '+factor+' 换算依据用户确认的截图工作区标准'),
        ('换算非校准值', '换算依据用户确认的截图工作区标准'),
        ('假定 2×', '按已确认 '+factor),
        ('2× 仅为假设', factor+' 已按用户标准换算')]
    for a, b in replacements: text = text.replace(a, b)
    return text


def calibrate(data, width=2560, height=1440, allow_partial=False):
    if width <= 0 or height <= 0:
        raise ValueError('Standard viewport dimensions must be positive')
    result = copy.deepcopy(data)
    result['captureStandard'] = {'width': width, 'height': height, 'confirmed': True,
        'unit': 'standard-px', 'basis': '用户指定的固定截图工作区；不推断应用缩放或源码 CSS px',
        'allowFullWidthPartialHeight': allow_partial}
    mappings = {}
    for page in result['pages']:
        for source in page['sources'].values():
            source['displayMapping'] = source_mapping(source, width, height, allow_partial)
            mappings[source['id']] = source['displayMapping']
        page_maps = [s['displayMapping'] for s in page['sources'].values()]
        scales = {s['scale'] for s in page_maps if s['status'] == 'mapped'}
        ready = len(scales) == 1 and all(s['status'] == 'mapped' for s in page_maps)
        for component in page.get('components', []):
            component['standardBounds'] = {mode: [round(x/page['sources'][mode]['displayMapping']['scale'], 6) for x in box]
                for mode, box in component.get('bounds', {}).items() if page['sources'][mode]['displayMapping']['status'] == 'mapped'}
            for estimate in component.get('estimates', []):
                estimate.pop('standard', None)
                if estimate.get('unit') != 'image-px' or estimate.get('evidence', {}).get('type') == 'config' or not ready: continue
                scale = next(iter(scales)); value = convert_value(estimate.get('value'), scale)
                if value is not None:
                    estimate['standard'] = {'value': value, 'unit': 'standard-px', 'scale': scale,
                        'tolerance': convert_tolerance(estimate.get('tolerance'), scale)}
            if ready:
                component.setdefault('originalNotes', copy.deepcopy(component.get('notes', [])))
                component['notes'] = [calibrated_note(s, width, height, next(iter(scales))) for s in component['originalNotes']]
    for variable in result.get('variables', []):
        variable.pop('standard', None)
        refs = [mappings[sid] for sid in variable.get('evidence', {}).get('sourceIds', []) if sid in mappings]
        scales = {s['scale'] for s in refs if s['status'] == 'mapped'}
        ready = refs and len(scales) == 1 and all(s['status'] == 'mapped' for s in refs)
        if variable.get('unit') != 'image-px' or variable.get('evidence', {}).get('type') == 'config' or not ready: continue
        scale = next(iter(scales))
        if 'values' in variable:
            values = {mode: convert_value(x, scale) for mode, x in variable['values'].items()}
            if any(v is None for v in values.values()): continue
            standard = {'values': values}
        else:
            value = convert_value(variable.get('value'), scale)
            if value is None: continue
            standard = {'value': value}
        variable['standard'] = {**standard, 'unit': 'standard-px', 'scale': scale,
            'tolerance': convert_tolerance(variable.get('evidence', {}).get('note'), scale)}
        variable.setdefault('originalNote', variable.get('note', ''))
        variable['note'] = calibrated_note(variable['originalNote'], width, height, scale)
        evidence = variable.get('evidence', {})
        evidence.setdefault('originalNote', evidence.get('note', ''))
        evidence['note'] = calibrated_note(evidence['originalNote'], width, height, scale)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest'); p.add_argument('--output', required=True)
    p.add_argument('--width', type=int, default=2560); p.add_argument('--height', type=int, default=1440)
    p.add_argument('--allow-full-width-partial-height', action='store_true', help='Use confirmed full-width scaling for shorter captures; do not stretch height.')
    p.add_argument('--report', help='Existing self-contained report to update without recropping images')
    p.add_argument('--report-output', help='Destination for the updated report; required with --report')
    args = p.parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    calibrated = calibrate(data, args.width, args.height, args.allow_full_width_partial_height)
    Path(args.output).write_text(json.dumps(calibrated, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.report:
        if not args.report_output: p.error('--report-output is required with --report')
        from report_calibration import enhance_html
        html = Path(args.report).read_text(encoding='utf-8')
        pattern = r'(<script id="analysis-data" type="application/json">)([\s\S]*?)(</script>)'
        match = re.search(pattern, html)
        if not match: raise ValueError('Report has no embedded analysis data')
        embedded = calibrate(json.loads(match.group(2)), args.width, args.height, args.allow_full_width_partial_height)
        payload = json.dumps(embedded, ensure_ascii=False).replace('<', '\\u003c')
        html = html[:match.start(2)]+payload+html[match.end(2):]
        Path(args.report_output).write_text(enhance_html(html), encoding='utf-8')
    print(json.dumps({'status': 'derived', 'standard': [args.width, args.height],
        'sourcesMapped': sum(s['displayMapping']['status'] == 'mapped' for page in calibrated['pages'] for s in page['sources'].values()),
        'variablesConverted': sum('standard' in v for v in calibrated.get('variables', []))}, ensure_ascii=False))


if __name__ == '__main__': main()
