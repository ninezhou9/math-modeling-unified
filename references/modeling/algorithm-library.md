# 算法库索引

本文件是算法库的路由入口。按需加载相关集合中的条目，禁止一次性加载全部算法资料。

当现有分类索引无法定位跨类算法、需要核对迁移前的算法比较维度或补查长尾方法时，再读取保留的[算法库整合详表](workspace/数学建模算法库_整合版.md)；日常选型仍以本页和相关集合条目为准。

```yaml
collections:
  optimization: optimization.md
  prediction: prediction.md
  evaluation: evaluation.md
  graph_network: graph-network.md
  statistics_data: statistics-data.md
  integrated: integrated.md
  machine_learning: machine-learning.md
entry_fields:
  - applicability
  - structure_or_formula
  - algorithm_specific_steps
  - constraint_handling
  - parameters
  - validation
  - risks
  - scenarios
  - comparisons
universal_fake_template_forbidden: true
```

## 使用规则

1. **按需加载**：根据模型选型决策树确定的决策族，只读取对应集合文件中的相关条目。
2. **专属步骤**：每个算法的步骤必须按该算法的特征单独设计（`universal_fake_template_forbidden: true`），禁止用千篇一律的通用模板套用所有算法。
3. **条目字段**：每个算法条目包含以下 9 个标准字段（`entry_fields`），确保信息完整且可比较。

## 条目字段说明

### applicability（适用性）
描述该算法适用的问题类型、数据特征和场景限制。

### structure_or_formula（结构或公式）
给出算法的核心数学表达、模型结构或关键公式。

### algorithm_specific_steps（算法专属步骤）
该算法独有的执行步骤，不可用通用模板替代。包括初始化、迭代/训练、终止条件等。

### constraint_handling（约束处理）
该算法如何处理等式约束、不等式约束、逻辑约束等。包括可行编码、修复算子、罚函数、可行优先等方法。

### parameters（参数）
关键超参数、推荐取值范围和调参建议。

### validation（验证）
该算法的标准验证方法：指标选择、交叉验证、收敛性检验、结果可信度评估。

### risks（风险）
常见陷阱、失败模式和误用场景。

### scenarios（场景）
具体的竞赛应用案例和适用场景描述。

### comparisons（比较）
与同族其他算法的对比维度和典型优劣势。

## 集合概览

| 集合 | 文件 | 涵盖内容 |
|---|---|---|
| 优化决策与运筹求解 | [optimization.md](optimization.md) | LP、IP/MILP、0-1 规划、NLP、多目标、组合优化、DP、最短路、网络流、GA、PSO、SA、NSGA-II、ACO、TS、DE、VNS、LNS/ALNS 等 |
| 预测与时序分析 | [prediction.md](prediction.md) | 回归分析、GM(1,1)、ARIMA、LMM、组合预测等 |
| 综合评价与排序 | [evaluation.md](evaluation.md) | AHP、熵权法、TOPSIS、模糊综合评价、DEA、组合赋权等 |
| 图论与网络分析 | [graph-network.md](graph-network.md) | 最短路、最小生成树、网络流、图着色、社区发现等 |
| 统计分析与数据处理 | [statistics-data.md](statistics-data.md) | 假设检验、方差分析、主成分分析、因子分析、成分数据变换等 |
| 综合类方法 | [integrated.md](integrated.md) | 灵敏度分析、蒙特卡洛模拟、系统动力学、微分方程数值解等 |
| 机器学习 | [machine-learning.md](machine-learning.md) | 逻辑回归、SVM、随机森林、BPNN、K-means、DBSCAN、XGBoost 等 |
