# 模型选型决策树

当候选方法跨越多个决策族、需要从原始整合资料反查算法适用条件时，按需读取[算法库整合详表](workspace/数学建模算法库_整合版.md)，再回到本页完成模型、求解器与验证三层决策。

本文件在需要选择模型或评估候选方案时加载。局部代码请求或已指定模型的任务不需要加载本文件。

```yaml
layers:
  - model
  - solver
  - validation
selection_starts_from:
  - requested_output
  - variables
  - objective
  - constraints
  - data_mechanism
exact_methods_before_metaheuristics: true
independent_model_system_limit: 2
same_mechanism_variants_are_one_family: true
advanced_method_requires_complexity_justification: true
decision_families:
  - optimization
  - evaluation
  - prediction
  - classification
  - clustering
  - mechanism
  - attribution
  - uncertainty
loading:
  generic_without_selection_need: []
  selection_needed:
    - model_selection
  algorithm_lookup_needed:
    - model_selection
    - relevant_algorithm_entries_only
  partial_fixed_model_code_request: []
```

## 选型三层分离

模型选型将决策过程分为三个独立但有序的层次：

1. **模型层（model）**：确定问题属于哪个决策族，选择数学模型框架。
2. **求解层（solver）**：为所选模型选择合适的求解算法或数值方法。
3. **验证层（validation）**：为模型和求解结果设计验证方案。

每一层的决策应独立记录理由，不因求解层的偏好反向修改模型层的选择。

## 选型起点

选型不从"我会什么算法"出发，而是从问题本身出发：

1. **requested_output**：题目要求什么输出（预测值、排序、分类标签、最优方案、机理解释）？
2. **variables**：涉及哪些变量，变量间是什么关系（线性/非线性、连续/离散、时序/截面）？
3. **objective**：优化什么目标（最小化成本、最大化收益、最优拟合、最佳分类）？
4. **constraints**：有哪些约束条件（等式/不等式、逻辑、资源、时间）？
5. **data_mechanism**：数据特征和问题机制是什么（样本量、维度、分布、因果关系）？

## 完整计算型请求的首轮比较

首轮方案审核须当场列出 2–3 个候选路径，不能只承诺稍后补充。候选路径应分别形成可执行的“模型层—求解层—验证层”闭环，而不是在单一主路径后罗列若干可选算法。对各路径至少逐项比较可解释性、数据适配、验证方案与实现成本，明确推荐一个路径并说明取舍，然后暂停等待用户确认；确认前不得进入或承诺代码、结果、图表和论文阶段。

该要求只适用于需要模型选型的完整计算型请求。用户已指定模型的局部代码、出图或写作请求继续按局部范围执行，不重新开启完整选型。

## 八大决策族

### 1. 优化（optimization）

- **适用**：有明确目标函数和约束的决策问题。
- **模型框架**：线性规划、整数规划、非线性规划、多目标规划、组合优化。
- **求解**：精确方法（单纯形法、分支定界）优先于元启发式（GA、PSO、SA）。
- **验证**：可行性检验、对偶分析、灵敏度分析。

### 2. 评价（evaluation）

- **适用**：需要对多个对象进行综合排序或评分。
- **模型框架**：AHP、熵权法、TOPSIS、模糊综合评价、DEA。
- **求解**：权重确定方法（主观/客观/组合）。
- **验证**：权重灵敏度分析、排序稳定性检验。

### 3. 预测（prediction）

- **适用**：基于历史数据预测未来趋势或数值。
- **模型框架**：回归分析、时间序列（ARIMA）、灰色预测、机器学习回归。
- **求解**：参数估计、模型训练。
- **验证**：交叉验证、残差分析、预测区间。

### 4. 分类（classification）

- **适用**：将样本分配到预定义类别。
- **模型框架**：逻辑回归、SVM、决策树/随机森林、神经网络。
- **求解**：训练与超参数调优。
- **验证**：混淆矩阵、ROC/AUC、精确率/召回率。

### 5. 聚类（clustering）

- **适用**：发现数据中的自然分组结构。
- **模型框架**：K-means、层次聚类、DBSCAN、GMM。
- **求解**：聚类数选择（轮廓系数、肘部法则）。
- **验证**：内部评价指标、外部评价指标（如有标签）、聚类稳定性。

### 6. 机理（mechanism）

- **适用**：需要建立物理/化学/生物等过程的数学描述。
- **模型框架**：微分方程（ODE/PDE）、SIR/SEIR、系统动力学、有限元。
- **求解**：数值积分、有限差分、有限元方法。
- **验证**：参数灵敏度、守恒量检验、与实测数据对比。

### 7. 归因（attribution）

- **适用**：识别影响因素的贡献度或因果关系。
- **模型框架**：回归分析（标准化系数）、方差分析、因果推断、Shapley 值。
- **求解**：假设检验、特征重要性排序。
- **验证**：交叉验证、多重共线性检查、因果稳健性。

### 8. 不确定性（uncertainty）

- **适用**：需要量化和管理不确定性。
- **模型框架**：蒙特卡洛模拟、贝叶斯推断、区间分析、鲁棒优化。
- **求解**：采样方法、后验分布估计。
- **验证**：收敛性检验、覆盖率检验、情景分析。

## 选型硬约束

### 精确方法优先

`exact_methods_before_metaheuristics: true`

- 能用精确方法（LP、MILP、凸优化）求解的问题，不优先使用启发式。
- 使用启发式必须说明精确方法不可行的原因（规模、非凸、NP-hard）。

### 模型数量限制

`independent_model_system_limit: 2`

- 每道子问题最多两个独立模型体系。
- 同一机制的变体计为一个族（`same_mechanism_variants_are_one_family: true`）。

### 复杂方法需论证

`advanced_method_requires_complexity_justification: true`

- 使用深度学习、集成学习、复杂元启发式等高级方法，必须论证简单方法不足。
- 论证格式：简单基线指标 → 不足分析 → 高级方法指标 → 提升量化。

## 渐进式加载规则

- 不需要选型的通用任务（`generic_without_selection_need`）：不加载本文件。
- 需要选型（`selection_needed`）：加载本文件。
- 需要查算法细节（`algorithm_lookup_needed`）：加载本文件 + 算法库中的相关条目（不全量加载）。
- 局部代码请求且模型已确定（`partial_fixed_model_code_request`）：不加载本文件。
