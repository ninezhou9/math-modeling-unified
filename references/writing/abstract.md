# 摘要写作与验证闭环

本文件是论文摘要撰写、验证与打磨的执行规范。摘要是决定评奖层级的核心页面，必须全篇正文冻结后独立完成。

```yaml
phases:
  - drafting
  - secondary_verification
  - finalization
abstract_vs_conclusion:
  abstract_focus: high_density_and_core_metrics
  conclusion_focus: direct_answers_and_boundaries
required_elements:
  - background_and_objective
  - model_and_methods
  - key_quantitative_results
  - innovation_and_value
```

## 摘要与结论的差异化定位

- **摘要（Abstract）**：面向评审专家的"第一眼看板"，信息密度极高，必须包含背景简述、核心建模思想、关键求解方法、各子问题的具体定量数值结果（`high_density_and_core_metrics`）以及主要创新点。
- **结论（Conclusion）**：面向应用实践者的"决策执行指南"，直接回答题目所提问题，强调决策适用边界与现实推广价值（`direct_answers_and_boundaries`）。

## 摘要四要素结构

1. **背景与目标（background_and_objective）**：1–2 句提炼实际背景与核心研究目标。
2. **模型与方法（model_and_methods）**：针对每个子问题分别说明所建数学模型体系与求解算法。
3. **关键定量结果（key_quantitative_results）**：逐问列出最关键的数值结果、误差指标或最优决策指标，数值必须与正文完全一致。
4. **创新与特色（innovation_and_value）**：1–2 句总结模型特色、算法改进或理论/实际价值。

## 写作三阶段闭环

### 第一阶段：起草（drafting）
- 在正文全部内容冻结后启动。
- 从各子问题的冻结章节中抽取核心模型名称、算法名称与关键定量结果。
- 组织为逻辑紧凑的结构化段落，做好严格字数控制（800–1200 字，一页以内）。

### 第二阶段：二次验证（secondary_verification）
- **数值绑定与一致性核验**：逐字比对摘要中出现的每一个数字、百分比、误差值是否完成数值绑定，与正文表格和代码输出 100% 一致。
- **术语一致性核验**：确保模型名称与正文完全统一。
- **信息完整性核验**：确认覆盖了题目的每一个子问题，无遗漏。

### 第三阶段：定稿（finalization）
- 润色语言，消除语病与套话。
- 提炼 3–5 个精准的关键词（涵盖领域背景、核心模型、优化算法）。
- 提交用户审核通过后最终冻结。
