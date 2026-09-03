# 用户模板与 LaTeX 排版规范

## 1. 模板地位

`assets/template/example-source.tex` 是用户指定的排版基准。生成新 C 题论文时，优先复制其 `cumcmthesis` 文档类、标题字段、abstract/keywords、三线表、figure/subfigure、公式与交叉引用习惯。

不要另起一套页面设计。字体、字号、标题层级、页边距和正文排版尽量由 `cumcmthesis` 类控制。

## 2. 电子版

使用模板提供的电子版方式，例如：

```latex
\documentclass[withoutpreface]{cumcmthesis}
```

需要黑白打印时再考虑 `bwprint`，但论文中图表应首先按屏幕评阅设计低饱和颜色，同时保证转灰度后仍能区分线型/标记。

## 3. 第一页

第一页必须是：
- 论文标题；
- 摘要；
- 关键词（≤5）。

摘要结束后显式 `\newpage`，确保“问题重述”从第2页开始。若摘要溢出，先删冗余，不通过缩小字号破坏模板。

## 4. 固定章节骨架

优先：

```latex
\section{问题重述}
\section{问题分析}
\section{模型假设}
\section{符号说明}
\section{模型的建立与求解}
  \subsection{问题一的模型建立与求解}
  ...
\section{模型评价与推广}
\begin{thebibliography}{99}
...
\end{thebibliography}
\begin{appendices}
...
\end{appendices}
```

若优秀范文和当前题目更适合把每问设为一级章节，可以微调，但全文层级必须一致。

## 5. 公式

普通推导使用 `equation/align`。完整优化模型在解释完每个组件后集中展示：

```latex
\begin{equation}
\boxed{
\left\{
\begin{aligned}
\max_{x_{ijt}}\quad & Z=\sum_{i,j,t} r_{ijt}x_{ijt},\\
\text{s.t.}\quad
& \sum_i x_{ijt}\le A_j,\\
& x_{ijt}\ge 0,\\
& x_{ijt}\in\mathbb{Z}\quad \text{(when needed)}.
\end{aligned}
\right.
}
\label{eq:main-model}
\end{equation}
```

不要用大段文字取代约束，也不要堆几十行方程组看不清。可把约束分组并在式后逐条解释。

## 6. 表格

严格使用 `booktabs` 三线表；避免竖线。表头简洁，单位优先写到列名。小数位按实际精度统一。

## 7. 图片

图片文件使用英文/数字有意义命名：
- `overview_model.pdf`
- `sales_week_pattern.png`
- `strategy_phase_map.pdf`

不要使用 `1.png`, `图3.png`。

矢量图优先 PDF；位图 200–300 dpi。Overview 图、网络图优先 TikZ 或矢量工具，避免截图。

## 8. 页数

主论文 25–28 页目标以最终 PDF 为准。不要在 TeX 源里通过 `\vspace` 大量拉页。

附录从新页开始，代码只放核心片段或文件说明；完整代码放支撑材料 `code/`。
