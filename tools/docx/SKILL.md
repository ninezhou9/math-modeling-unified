---
name: DOCX工具
description: 创建、编辑、校验和转换 Word DOCX，支持数学建模模板、原生 OMML 公式、三线表、修订、批注和完整 LaTeX 论文转换。
---

# DOCX 工具

本目录是统一的 DOCX 操作入口。只从 `tools/docx/scripts/` 调用脚本；`source-variants/` 仅保留来源差异和完整性证据，不是运行入口。输入和模板保持只读，产物写入用户 `PROJECT_ROOT`，默认不覆盖已有文件。

## 数学建模论文

优先使用当届官方 DOCX 模板。仓库内可复现基线为 `<SKILL_ROOT>/assets/cumcm-step-review/templates/论文模板.docx`。`paper_format.py` 保留模板的页面与样式，并提供标题、摘要、正文、原生 OMML 公式、图表题注和三线表构建器：

```python
from pathlib import Path
import sys

scripts = Path("<SKILL_ROOT>") / "tools" / "docx" / "scripts"
sys.path.insert(0, str(scripts))
import paper_format as pf

doc = pf.new_document(
    contest="cumcm",
    template_path=Path("<PROJECT_ROOT>") / "当届官方模板.docx",
    preserve_template_content=False,
)
pf.title(doc, "论文题目")
pf.abstract_title(doc)
pf.body(doc, "摘要正文。")
pf.keywords(doc, "优化；预测")
pf.equation(doc, r"\min f(x)=\sum_{i=1}^{n}x_i^2")
pf.three_line_table(doc, [["符号", "说明"], ["x", "决策变量"]])
pf.save_document(doc, Path("<PROJECT_ROOT>"), contest="cumcm")
```

## 公式与文档转换

常用 LaTeX 子集直接转换为可编辑 OMML；未知命令、未闭合分组和不支持环境会失败：

```powershell
python scripts/equations.py replace "输入.docx" --replace "EQ_OBJECTIVE" "\min f(x)" --output "<PROJECT_ROOT>/输出.docx"
python scripts/equations.py generate "论文.md" --output "<PROJECT_ROOT>/论文.docx" --template "官方模板.docx"
```

`replace` 必须显式提供 `--output`，且输出路径必须与输入 DOCX 不同。若输出文件已经存在，默认拒绝写入；只有明确传入 `--overwrite` 才会覆盖这个不同路径的输出文件。输入与输出为同一路径时，即使传入 `--overwrite` 也始终拒绝，工具不提供原地覆盖模式。

完整 LaTeX 项目通过 Pandoc 转换。工具递归展开项目内 `\input`/`\include`，拒绝越界与循环包含，处理 BibTeX/citeproc 和相对图片，并生成同名 `.conversion.json` 哈希清单。警告默认阻断发布，DOCX 与清单成对原子替换：

```powershell
python scripts/equations.py convert-latex "<PROJECT_ROOT>/论文/main.tex" --output "<PROJECT_ROOT>/论文.docx" --template "<PROJECT_ROOT>/官方模板.docx" --timeout 120
python scripts/equations.py verify-conversion "<PROJECT_ROOT>/论文.docx"
```

仅在逐项核对后，才可为具体警告传入 `--allow-warning <精确正则>` 和 `--override-reason <证据>`。自定义宏、浮动体、交叉引用和引文样式仍须在渲染结果中核对。

## OOXML、修订与批注

```powershell
python scripts/office/unpack.py "输入.docx" "<PROJECT_ROOT>/unpacked"
python scripts/comment.py "<PROJECT_ROOT>/unpacked" 0 "批注意见"
python scripts/comment.py "<PROJECT_ROOT>/unpacked" 1 "回复意见" --parent 0
python scripts/office/pack.py "<PROJECT_ROOT>/unpacked" "<PROJECT_ROOT>/输出.docx" --original "输入.docx"
python scripts/accept_changes.py "输入.docx" "<PROJECT_ROOT>/已接受修订.docx"
```

不要绕过关系、内容类型和 schema 校验直接改压缩包。批注父 ID 不存在或 ID 重复时必须在写入前失败；接受修订只有在隔离 LibreOffice 成功且无残留修订标记时才发布输出。

## 完成门禁与渲染

```powershell
python scripts/check_env.py
python scripts/self_check.py
python scripts/office/validate.py "<PROJECT_ROOT>/完整论文.docx"
python scripts/paper_format.py validate "<PROJECT_ROOT>/完整论文.docx" --contest cumcm --rendered-pages <实际页数>
python scripts/equations.py verify-conversion "<PROJECT_ROOT>/完整论文.docx"
```

`verify-conversion` 仅用于带 `.conversion.json` 的 Pandoc 产物。`paper_format.py validate` 检查官方前置结构、正文规模、公式/图/表数量、编号与正文引用、参考文献对应和实际页数；非零退出表示不能交付。结构检查后用 LibreOffice 将 DOCX 渲染为 PDF，再逐页抽检分页、公式、三线表、图片、页眉页脚和字体替换。CUMCM 的内容规模和约 20 页是质量目标；当届官方页数限制才是硬约束。
