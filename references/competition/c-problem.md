# CUMCM 本科组 C 题专用规则

本文件仅适用于 CUMCM 本科组 C 题（大数据与决策类）。非 C 题任务不得加载此文件。加载前必须先加载 CUMCM 通用规则。

```yaml
scope: cumcm_undergraduate_c_only
explicit_exclusions:
  - generic_math_modeling
  - cumcm_undergraduate_a
  - cumcm_undergraduate_b
  - cumcm_undergraduate_d
  - cumcm_undergraduate_e
selection_policy: transparent_first
visible_innovations:
  minimum: 1
  maximum: 3
complexity_questions:
  - what_simple_method_fails
  - why_it_fails_for_this_data_or_mechanism
  - what_verifiable_gain_the_added_complexity_provides
```

## C 题定位与演化

C 题是 CUMCM 本科组专设的大数据与决策分析类赛题，通常围绕真实业务场景（供应商评价、商品定价、信贷风险、医学检测等），要求从数据出发建立模型并给出可执行的决策方案。

### 历年 C 题演化脉络

- **2020 年 C 题**：中小微企业信贷决策（信用评估 + 风险定价）。
- **2021 年 C 题**：生产企业原材料订购与运输（供应商评价 + 多目标优化）。
- **2022 年 C 题**：古代玻璃制品成分分析（成分数据 CLR 变换 + 分类聚类）。
- **2023 年 C 题**：蔬菜商品定价与补货（需求预测 + 优化联动）。
- **2024 年 C 题**（具体赛题以官方发布为准；当届规则待核验）。
- **2025 年 C 题**：NIPT 检测时点与胎儿异常判定（线性混合效应模型 LMM + 纵向数据决策）。

## 72 小时工作流

C 题的 72 小时时间约束要求高效的任务分解与执行：

1. **任务分解**：将赛题拆解为子问题，明确每个子问题的输入、输出和依赖关系。
2. **依赖分析**：识别子问题间的数据依赖与逻辑依赖，确定执行顺序。
3. **并行与串行**：无依赖的子问题可并行推进；有依赖的必须按序执行。
4. **时间分配**：为每个子问题预留建模、编码、验证和写作时间；留出最终整合与检查时间。

## 数据驱动建模原则

### 数据质量与缺口分析

- 首先进行数据探索（profiling）：维度、缺失率、异常值、分布特征。
- 显式识别数据缺口：哪些建模所需的信息在数据中不直接可得，需要通过特征工程或外部知识弥补。
- 数据预处理步骤必须可追溯：每个变换（清洗、编码、标准化、降维）的理由和影响需记录。

### 决策误差传播

- 上游模型（预测/分类）的误差会传播到下游决策（优化/规划）。
- 必须分析误差传播路径：预测偏差如何影响最终决策质量。
- 建议进行情景分析或鲁棒优化来量化决策对上游误差的敏感性。

## 模型选型与创新

### 选型策略：透明优先（transparent_first）

C 题优先选择可解释性强的模型，复杂模型需要证明简单方法不足：

1. **首先尝试简单基线**：线性回归、逻辑回归、决策树等可解释模型。
2. **证明简单方法不足**（`what_simple_method_fails`）：用实验数据和指标说明基线模型在哪些方面表现不足。
3. **解释失败原因**（`why_it_fails_for_this_data_or_mechanism`）：分析是数据特性（非线性、高维交互、时序依赖）还是问题机制导致的。
4. **量化复杂方法的收益**（`what_verifiable_gain_the_added_complexity_provides`）：用实验指标证明复杂方法带来了可验证的提升。

### 验证成熟度

模型验证的深度应与模型复杂度匹配：

- 简单模型：残差分析、交叉验证即可。
- 复杂模型：需要消融实验、特征重要性分析、鲁棒性测试。
- 集成模型：需要基模型对比、集成增益分析。

### 可见创新控制

- 每道子问题的创新点控制在 1–3 个（`visible_innovations`）。
- 创新必须可见、可验证、可解释：读者能在论文中看到创新点及其效果。
- 避免为创新而创新：每个创新点必须回答"解决了什么具体问题"。

## C 题工具箱

### 常用建模工具链

- **数据处理**：pandas profiling、缺失值插补（KNN / 多重插补）、异常检测。
- **特征工程**：成分数据 CLR/ILR 变换（source-index 变换）、时间序列特征提取、交互特征。
- **预测模型**：ARIMA、灰色预测、随机森林回归、XGBoost、线性混合效应模型（LMM）。
- **分类与聚类**：逻辑回归、SVM、K-means、DBSCAN、层次聚类。
- **优化求解**：线性规划、整数规划、多目标优化、启发式算法。
- **评价方法**：AHP、熵权法、TOPSIS、模糊综合评价。

### 论文结构（C 题特化）

C 题论文在通用结构基础上，通常需要：

- **数据预处理**章节占较大篇幅，展示数据质量分析与处理过程。
- **模型联动**：多个子问题的模型之间有明确的数据流和逻辑链。
- **决策方案**：最终输出可执行的决策建议，而非纯学术分析。
- **灵敏度分析**：对关键参数的扰动分析，验证决策的鲁棒性。

## 专家评审视角

评审关注的 C 题核心要素：

1. 数据处理是否充分、合理、可追溯。
2. 模型选择是否有据可循、是否与数据特性匹配。
3. 创新点是否解决了实际问题。
4. 结果是否可解释、决策是否可执行。
5. 误差分析与灵敏度分析是否覆盖关键路径。

## 保留细节的渐进式路由

下列文件是可验证的详细参考，只在对应触发条件出现时读取，不得一次性全部加载：

| 读取条件 | 详细参考 |
|---|---|
| 制定 72 小时排程、检查关键冻结点 | [72 小时详细工作流](cumcm-c-problem/72h-workflow.md) |
| 判断历史题型变化与方法迁移边界 | [C 题演化](../modeling/cumcm-c-problem/c-problem-evolution.md) |
| 核对竞赛合规、AI 与支撑材料要求 | [竞赛合规](cumcm-c-problem/competition-compliance.md) |
| 需要 C 题专用数据处理、预测、优化工具 | [建模工具箱](../modeling/cumcm-c-problem/modeling-toolbox.md) |
| 按评委视角做终检 | [专家评审指南](../quality/cumcm-c-problem/expert-review-guidance.md) |
| 寻找可迁移的题型结构而非照搬结论 | [优秀范式](../modeling/cumcm-c-problem/exemplar-patterns.md) |
| 追溯 2018–2025 题目、论文和讲评来源 | [来源索引](../modeling/cumcm-c-problem/source-index.md) |
| 组织 C 题章节与模型联动叙事 | [论文结构](../writing/cumcm-c-problem/paper-structure.md) |
| 使用官方模板与 LaTeX 排版 | [LaTeX 模板指南](../writing/cumcm-c-problem/latex-template-guide.md) |
| 设计 C 题数据图、机制图与决策图 | [可视化手册](../visualization/cumcm-c-problem/visualization-playbook.md) |
| 执行 C 题专项质量检查 | [C 题质量门禁](../quality/cumcm-c-problem/quality-gates.md) |
