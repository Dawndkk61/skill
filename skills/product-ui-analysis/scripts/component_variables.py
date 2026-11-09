#!/usr/bin/env python3
"""Add the shared component-variable panel to an existing self-contained report."""
import argparse
import re
from pathlib import Path

MARKER = '/* PRODUCT_UI_COMPONENT_VARIABLES v1 */'
OLD_MARKER = '/* TRAE_COMPONENT_VARIABLES v1 */'
CSS_START = '/* PRODUCT_UI_COMPONENT_VARIABLES_STYLE v1 */'
CSS_END = '/* END_PRODUCT_UI_COMPONENT_VARIABLES_STYLE */'
JS_END = '/* END_PRODUCT_UI_COMPONENT_VARIABLES */'


def block(template, start, end):
    match = re.search(re.escape(start)+r'[\s\S]*?'+re.escape(end), template)
    if not match:
        raise ValueError('Shared template missing component variable block: '+start)
    return match.group(0)


def enhance_html(html):
    scripts = list(re.finditer(r'(<script>)([\s\S]*?)(</script>)', html))
    match = next((m for m in scripts if 'function pageView(p){' in m.group(2)), None)
    if not match:
        raise ValueError('No supported page renderer; adapt explicitly instead of guessing.')
    runtime = match.group(2)
    if MARKER in runtime:
        return html
    if OLD_MARKER in runtime:
        # Adopt the already-approved TRAE trial without changing its layout.
        runtime = runtime.replace(OLD_MARKER, MARKER, 1)
    else:
        ending = "+list(c.notes)+'</div></div></article>'"
        if ending not in runtime:
            raise ValueError('Unsupported component ending; cannot mount variable panel safely.')
        template = (Path(__file__).resolve().parent.parent/'assets/report.html').read_text(encoding='utf-8')
        runtime = runtime.replace('function pageView(p){', block(template, MARKER, JS_END)+'\nfunction pageView(p){', 1)
        runtime = runtime.replace('<article class="component" id="component-', '<article class="component component-with-variables" id="component-', 1)
        runtime = runtime.replace(ending, "+list(c.notes)+'</div>'+componentVariables(p,c,mode)+'</div></article>'", 1)
        css = block(template, CSS_START, CSS_END)
        if '</style>' not in html:
            raise ValueError('Report has no stylesheet')
        html = html[:match.start(2)]+runtime+html[match.end(2):]
        return html.replace('</style>', '\n'+css+'\n</style>', 1)
    return html[:match.start(2)]+runtime+html[match.end(2):]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    source = Path(args.report).read_text(encoding='utf-8')
    result = enhance_html(source)
    Path(args.output).write_text(result, encoding='utf-8')
    print('Component variable display ready; embedded analysis and images preserved.')


if __name__ == '__main__':
    main()
