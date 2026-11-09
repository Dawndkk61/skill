# 产品界面分析 Skill 使用说明

从产品截图整理页面、主题、组件和设计变量候选，生成可在浏览器离线打开的 HTML 报告。报告把可见事实、像素取样、几何估算和设计推断分别标注。

## 安装

1. 解压 `product-ui-analysis.zip`。
2. 把完整的 `product-ui-analysis` 文件夹放入 `~/.codex/skills/`。如果环境设置了 `CODEX_HOME`，使用该目录下的 `skills/`。
3. 新开一个 Codex 对话，在请求中输入 `$product-ui-analysis`。已有同名 Skill 时，可先备份旧目录，再用新目录替换。

安装后的入口路径应为 `~/.codex/skills/product-ui-analysis/SKILL.md`。构建和校验脚本使用 Python 3.9 或更新版本及其标准库。

## 第一次使用

把截图按产品放在子文件夹中。如果同一产品有多个分类或主题，可以再分子目录，例如：

```text
产品截图/
  产品 A/
    工作台/
    IDE/
  产品 B/
    IDE/
```

在 Codex 中提交：

> 使用 $product-ui-analysis 分析「产品截图」目录。按产品与分类分别输出包含页面、主题、设计变量、组件和截图证据的 HTML。已有工作台报告的同名产品保留原报告，并增加 IDE 入口。仅有 IDE 截图的产品只记录 IDE。

也可以提供一张截图、一个目录或已有报告。若需要把截图几何换算成标准像素，请在请求里说明工作区标准尺寸与截图范围。

## 查看产物

- 用浏览器打开报告 HTML。侧栏可选择页面，变量表可切换原始层、语义层和组件层。证据链接可以跳到对应组件。
- `analysis.json` 保存来源、截图坐标、取样和估算，供后续增量更新。同一产品的工作台和 IDE 各有独立清单与短结论。
- 新增截图时提供原报告目录和新增素材，说明新增的页面、主题或分类。只有深色截图时，报告只呈现已采集的深色数据。

## 已有清单时手动生成

在 Skill 目录中运行以下命令。清单内的截图路径相对于 `analysis.json` 所在目录。

```sh
python3 scripts/build_report.py /path/to/analysis.json --output /path/to/report.html
python3 scripts/validate_analysis.py /path/to/analysis.json --report /path/to/report.html
```
