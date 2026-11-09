# 分析 JSON

图片路径相对 JSON 所在目录。构建器将图片嵌入 HTML，无需在旁边留原图。ID 保持稳定；组件 ID 在页面内唯一。

```json
{
  "product": "Example App",
  "surface": "IDE",
  "conclusion": "编辑区和会话栏并排显示。",
  "pages": [{
    "id": "home", "title": "首页",
    "sources": {
      "dark": {"id": "s-dark", "path": "dark.png", "width": 1440, "height": 900,
        "state": "空输入；账户受限", "colorSpace": "sRGB"},
      "light": {"id": "s-light", "path": "light.png", "width": 1440, "height": 900,
        "state": "空输入；账户受限", "colorSpace": "sRGB"}
    },
    "components": [{
      "id": "composer", "name": "输入框",
      "bounds": {"dark": [400, 300, 640, 200], "light": [400, 300, 640, 200]},
      "facts": ["空输入状态，额度提示可见。"],
      "estimates": [{"property": "容器圆角", "value": 16, "unit": "image-px", "tolerance": "±3"}],
      "inferences": ["建议作为复合输入组件。"],
      "notes": ["未验证输入和发送行为。"]
    }]
  }],
  "variables": [{
    "id": "composer-fill", "category": "colors",
    "name": "surface/composer", "label": "输入框表面", "kind": "color",
    "values": {"light": "#FFFFFF", "dark": "#242424"},
    "evidence": {"type": "sample", "note": "内部 9×9 众数", "sourceIds": ["s-dark", "s-light"]},
    "applications": [{"page": "home", "component": "composer", "property": "填充", "relation": "截图对应"}],
    "note": "用途名称为建议，源码绑定未验证。"
  }, {
    "id": "composer-radius", "category": "radius",
    "name": "radius/composer", "label": "输入框圆角", "kind": "number",
    "value": 16, "unit": "image-px",
    "evidence": {"type": "estimate", "note": "±3 图像像素；倍率未标定", "sourceIds": ["s-dark"]},
    "applications": [{"page": "home", "component": "composer", "property": "圆角", "relation": "几何估算"}]
  }]
}
```

示例只说明格式，不是任何产品的取样结果，不能把值复制到实际分析。

默认采用紧凑总览：标题、短简介后直接显示变量分类表；页面、组件和变量保留各自证据，不额外生成“设计线索”或“主题与状态覆盖”汇总。校验器检查最终 HTML，包括后处理插入的内容。仅当用户明确要求自定义总览汇总时，才可在根对象设置 `"reportLayout": {"allowOverviewSummary": true}`；默认省略，不能为绕过校验自动开启。

## 截图工作区标定

`surface` 与 `conclusion` 是可选顶层字段。按用户的分析范围填写 `工作台` 或 `IDE` 和对应短结论。无分类的既有清单可省略。

用户确认使用 2560×1440 标准时，记录在根对象：

```json
{
  "captureStandard": {
    "width": 2560, "height": 1440, "confirmed": true,
    "unit": "standard-px", "allowFullWidthPartialHeight": false
  }
}
```

原图 `width/height`、裁切 `bounds`、取样 `box` 和几何 `value` 继续保存原图像素。执行 `calibrate_analysis.py` 后生成派生信息：

- 源图 `displayMapping`：一致的 `scaleX/scaleY`、标准尺寸与映射依据。5120×2880 → 2560×1440，倍率 2；2560×1440 倍率 1。
- 几何估算和数值变量的 `standard`：标准值、标准单位、倍率、换算后的误差。例如原值 30、容差 ±5，标准值 15、容差 ±2.5；二维尺寸的每一维都换算。
- 组件的 `standardBounds`：截图内标准坐标；原坐标不变。不能据此推断裁切偏移或显示器绝对坐标。
- 原说明保存在 `originalNote/originalNotes`；可见说明更新为当前标定依据。重复执行从原值重新派生，不会重复缩小。

纵横倍率不一致的截图默认 `unresolved`，不使用 5120/2560 与 2820/1440 两种不同倍率拉伸。已确认“全宽、局部高度”的旧图，显式使用 `--allow-full-width-partial-height`；例如 5120×2820 按同一个 2× 换为 2560×1410。不要给未知裁切图自动套此例外。

设置中显示的 13 px、CSS/代码中的原生配置、颜色、字重、字体家族不参与像素倍率除法。图像测量换成标准 px 后依然是估算，不代表获得产品 computed style。

```bash
python3 scripts/calibrate_analysis.py analysis.json --width 2560 --height 1440 --output analysis.json
python3 scripts/build_report.py analysis.json --output report.html
```

更新现有自包含报告可增加 `--report report.html --report-output report.html`，图片数据原样保留。生成器检测已确认的 `captureStandard` 后会自动刷新派生值和换算显示；静态校验检查这些值与原值/倍率是否一致。

## 产品 Logo（可选）

在根对象增加 `brand.logo`，素材路径相对于 JSON。没有 Logo 时省略整个字段，模板会只显示产品名，不保留空图片框。标志资产放在当前报告项目内，不将具体产品的 Logo 固化到 Skill 安装目录。

```json
{
  "brand": {
    "logo": {
      "path": "assets/product-logo.png",
      "sourceId": "s-light",
      "box": [100, 80, 46, 49],
      "blendMode": "darken",
      "description": "从 Light 截图直接裁切的产品标志，未重绘。"
    }
  }
}
```

`path` 必需，支持 PNG/JPEG/WebP；构建器会嵌入图片并记录哈希。`sourceId`、`box` 是截图裁切的来源记录，坐标为原图像素，必须对应实际来源；用户单独提供的标志可省略这两个字段，用 `description` 说明来源。Logo 图形优先，避免把包含名称的整段字标缩成难以辨认的小图。

透明素材默认 `blendMode: normal`。浅色截图底、深色标志可用 `darken` 融合浅灰侧栏；已有反白版本可按真实素材选择 `lighten`。这些只用于图片显示，保留原素材，不强制重着色或改变品牌形状。显示框约 22×22 CSS px，等比适应，与产品名有 9 px 间距。

报告校验会检查文件、格式、可选哈希、来源和裁切边界，并确认 HTML 内嵌标志。交付前再检查实际显示、导航后的加载及没有 Logo 的文字回退。

- `sources` 按可用主题 / 模式记录，不必同时有 Light / Dark，缺失模式不做反色补齐。源 ID、尺寸必需；可选 `sha256` 提供则校验文件。不同业务状态建议独立页面 / 状态组。
- `bounds` 使用指定源图的原图像素 `[x,y,width,height]`。边界未知可省略裁切，保留原图，不伪造坐标。
- `facts`、`inferences`、`notes` 是字符串数组；`estimates` 每项有 `property`、`value`、`unit`，建议有 `tolerance`。这些字段刻意分开。
- 分类：`colors/radius/spacing/borders/text/weight/size`，没有依据的分类不必制造记录。
- `kind` 为 `color/number/string`。主题化值用 `values`，共用值用 `value`，两者不同时提供。数字必须有单位。未知用 `value: null` 和 `evidence.type: unknown`。
- `evidence.type` 使用证据规则中的六类；`sourceIds` 指向至少一个实际源记录；`note` 保留方法 / 容差。采样可附 `samples`，每项有 `sourceId`、`box`、`hex`、`agreement`、`colorSpace`。
- `applications` 指向现有页面 / 组件，包含具体参数和关系。`note` 在语义表行直接显示，不再创建重复详情卡片。
- 页面内“对应设计变量”直接反查 `applications`：必须同时匹配页面与组件 ID，展示实际 `property` 和所属变量。按当前模式读取 `values[mode]`；有 `standard` 时使用派生几何值，未知值不补齐。只显示有对应关系的分类，没有对应关系则写“暂无对应变量记录”。变量链接使用 `#view=variables&target=variable-ID`，沿用自动打开语义层的定位。共享模板内置该展示；旧报告可用 `scripts/component_variables.py` 更新，不重新取样或改写 JSON。

```bash
python3 scripts/validate_analysis.py analysis.json
python3 scripts/build_report.py analysis.json --output report.html
python3 scripts/validate_analysis.py analysis.json --report report.html
```

构建器可嵌入 PNG/JPEG/WebP，自动裁切只支持 8 位非交错 PNG，其他格式先生成有来源记录的分析副本。静态校验不代替渲染和交互检查。扩展至 TRAE / Qoder 时复用结构，重新建立样本和值。
