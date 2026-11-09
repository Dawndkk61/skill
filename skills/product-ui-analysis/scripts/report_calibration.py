"""Add calibrated display to the shared report, preserving product-specific content."""
import re

RUNTIME = r'''
/* PRODUCT_UI_CALIBRATION v1 */
function measurementUnit(v){return v.standard?.unit||v.unit||''}
function measurementNumber(v){return v.standard?.value??v.value}
function measurementLabel(unit){return unit==='standard-px'?'标准 px':unit||''}
function originalValueText(v){const raw='values' in v?v.values:{Default:v.value};return Object.entries(raw).map(([mode,x])=>(mode==='Default'?'':mode+' ')+String(x)+(v.unit?' '+v.unit:'')).join(' / ')}
function value(v){const unit=measurementLabel(measurementUnit(v));return '<div class="value">'+Object.entries(vals(v)).map(([mode,x])=>'<div><small>'+esc(mode)+'</small>'+(x===null?'<span>未核实</span>':v.kind==='color'?'<span class="swatch"><i style="background:'+esc(x)+'"></i><code>'+esc(x.toUpperCase())+'</code></span>':'<span>'+esc(x)+(unit?' '+esc(unit):'')+(v.standard?.tolerance?'（'+esc(v.standard.tolerance)+'）':'')+'</span>')+'</div>').join('')+'</div>'+(v.standard?'<small class="original-measurement">原图：'+esc(originalValueText(v))+'</small>':'')}
function estimateText(x){const m=x.standard||x;return x.property+'：'+m.value+' '+measurementLabel(m.unit)+(m.tolerance?'（'+m.tolerance+'）':'')+(x.standard?'；原图 '+x.value+' '+x.unit:'')}
function calibrationBanner(){const standard=data.captureStandard;if(!standard?.confirmed)return '';const sources=data.pages.flatMap(p=>Object.values(p.sources)),mapped=sources.filter(s=>s.displayMapping?.status==='mapped'),scales=[...new Set(mapped.map(s=>s.displayMapping.scale))],partial=mapped.some(s=>s.displayMapping.frame==='full-width-partial-height');return '<div class="measurement-standard"><b>截图标准 '+standard.width+' × '+standard.height+'</b> · '+(scales.length===1?'原图倍率 '+scales[0]+'×；几何主值与误差同步换算为标准 px。':'按各源图的可靠映射换算几何与误差。')+(partial?' 高度不足完整工作区的截图保留实际高度，不拉伸。':'')+(mapped.length!==sources.length?' '+(sources.length-mapped.length)+' 张截图映射未确认，相关参数保留 image-px。':'')+' 原图坐标、取样区域及原始值保留；标准 px 为分析单位，不等同已验证源码 CSS px。</div>'}
'''


def enhance_html(html):
    html = html.replace('Value / 原始值', 'Value / 数值与单位')
    html = html.replace('倍率未标定，几何量使用 image-px', '几何量已按截图标准换算，原图值保留')
    html = html.replace('几何使用原图像素，倍率未标定', '几何已按截图标准换算，原图数值保留')
    html = html.replace('几何为原图像素，2× 仅为假设', '几何已按截图标准换算，原图数值保留')
    if '/* PRODUCT_UI_CALIBRATION v1 */' in html:
        return html
    original = "const vals=v=>'values' in v?v.values:{Default:v.value};"
    replacement = "const vals=v=>{const m=v.standard||v;return 'values' in m?m.values:{Default:m.value}};"
    if original not in html:
        raise ValueError('Unsupported report value renderer; adapt the report explicitly instead of guessing.')
    html = html.replace(original, replacement, 1)
    # Last function declaration wins; helpers are hoisted before the initial render().
    anchor = "document.getElementById('close-original').onclick="
    if anchor not in html: raise ValueError('Missing shared report runtime anchor')
    html = html.replace(anchor, RUNTIME+'\n'+anchor, 1)
    html = html.replace("String(a.unit).localeCompare(String(b.unit))||(a.value??0)-(b.value??0)", "measurementUnit(a).localeCompare(measurementUnit(b))||(measurementNumber(a)??0)-(measurementNumber(b)??0)")
    html = html.replace("[v.kind,v.unit||'',vals(v),v.evidence.type]", "[v.kind,measurementUnit(v),vals(v),v.evidence.type]")
    html = html.replace("vs.filter(x=>x.unit===v.unit&&typeof x.value==='number').map(x=>x.value)", "vs.filter(x=>measurementUnit(x)===measurementUnit(v)&&typeof measurementNumber(x)==='number').map(x=>measurementNumber(x))")
    html = html.replace("v.kind==='number'&&typeof v.value==='number'", "v.kind==='number'&&typeof measurementNumber(v)==='number'")
    html = html.replace('v.value/max*100', 'measurementNumber(v)/max*100')
    html = html.replace("x=>x.property+'：'+x.value+' '+x.unit+(x.tolerance?'（'+x.tolerance+'）':'')", 'estimateText')
    html = html.replace("s.width+'×'+s.height", "s.width+'×'+s.height+(s.displayMapping?.status==='mapped'?' · 标准尺寸 '+s.displayMapping.standardSize.join('×')+' px（'+s.displayMapping.scale+'× 原图）':'')")
    html = html.replace("document.getElementById('main').innerHTML=(p?", "document.getElementById('main').innerHTML=calibrationBanner()+(p?")
    html = html.replace("document.getElementById('main').innerHTML=pageView(currentPage.p);", "document.getElementById('main').innerHTML=calibrationBanner()+pageView(currentPage.p);")
    html = html.replace('</style>', '.measurement-standard{font-size:11px;line-height:1.8;color:#666;background:#f3f3f3;border:1px solid #ddd;border-radius:6px;padding:12px 16px;margin:0 0 24px}.measurement-standard b{color:#333}.original-measurement{color:#888;font-size:10px}</style>', 1)
    return html
