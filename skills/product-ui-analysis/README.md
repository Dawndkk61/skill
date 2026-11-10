# 产品界面分析 Skill 使用说明

从全屏产品截图整理页面、主题和设计变量候选，生成可在浏览器离线打开的 HTML 报告。报告把可见事实、像素取样、几何估算和设计推断分别标注。

## 安装

1. 解压 `product-ui-analysis.zip`。
2. 把完整的 `product-ui-analysis` 文件夹放入 `~/.codex/skills/`。如果环境设置了 `CODEX_HOME`，使用该目录下的 `skills/`。
3. 新开一个 Codex 对话，在请求中输入 `$product-ui-analysis`。已有同名 Skill 时，可先备份旧目录，再用新目录替换。

安装后的入口路径应为 `~/.codex/skills/product-ui-analysis/SKILL.md`。构建和校验脚本使用 Python 3.9 或更新版本及其标准库。

## 第一次使用

准备单个显示器的全屏截图原图，保留截图的完整画面和原始像素。多产品可按产品名放入各自的子目录。窗口图、局部裁切、拼接图和单独的组件截图请换为全屏原图。报告可以从全屏原图裁取组件作为证据，独立组件级分析留待后续迭代。

首次使用请填写截图所用屏幕的**系统显示尺寸（逻辑工作区）**。macOS 有「看起来像」时填该尺寸。截图文件的实际像素尺寸由 Skill 读取。缺少系统显示尺寸时会询问一次，填「不确定」则用原图像素继续。同一显示条件可沿用，换屏或调整系统显示比例后分别填写。

### 可直接复制的提示词

```text
使用 $product-ui-analysis 分析这批未裁剪、未缩放的全屏截图原图。

素材路径：[截图目录或附件]
系统显示尺寸（逻辑工作区）：[宽 × 高，或填不确定]

输出含页面、主题、设计变量和截图证据的 HTML 报告及 analysis.json。
```

**换算示例**　系统显示尺寸为 2560 × 1440，同一显示器的全屏原图为 5120 × 2880，横纵倍率均为 2。原图测得的 24 图像像素可记为约 12 标准像素。报告保留原值和证据坐标。标准像素用于报告内对照。

## 查看产物

- 用浏览器打开报告 HTML。侧栏可选择页面，变量表可切换原始层、语义层和组件层。证据链接可以跳到对应组件。
- `analysis.json` 保存来源、截图坐标、取样和估算。
- 只有深色截图时，报告只呈现已采集的深色数据。

## 已有清单时手动生成

在 Skill 目录中运行以下命令。清单内的截图路径相对于 `analysis.json` 所在目录。

```sh
python3 scripts/build_report.py /path/to/analysis.json --output /path/to/report.html
python3 scripts/validate_analysis.py /path/to/analysis.json --report /path/to/report.html
```
