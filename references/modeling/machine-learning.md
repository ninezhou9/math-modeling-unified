# 机器学习

## 逻辑回归（Logistic Regression）
### 适用性
二分类与多分类概率估计基准模型。要求特征与对数几率（Log-odds）呈线性关系，具极高计算效率与原生几率比（OR）可解释性。
### 结构或公式
- Sigmoid 映射：$P(Y=1|\mathbf{x}) = \sigma(\mathbf{w}^T \mathbf{x} + b) = \frac{1}{1 + e^{-(\mathbf{w}^T \mathbf{x} + b)}}$
- 正则化对数损失：$L(\mathbf{w}) = -\frac{1}{N}\sum [y_i \ln \hat{y}_i + (1-y_i)\ln(1-\hat{y}_i)] + \frac{\lambda}{2}\|\mathbf{w}\|_2^2$
### 算法专属步骤
1. 特征工程：连续变量标准化、类别变量 One-Hot 编码、VIF 过滤高共线性特征。
2. 权重初始化（$\mathbf{w}_0 = \mathbf{0}, b_0 = 0$），计算梯度 $\nabla_{\mathbf{w}} L = \frac{1}{N} X^T (\hat{\mathbf{y}} - \mathbf{y}) + \lambda \mathbf{w}$。
3. 选用 L-BFGS 或 Newton-CG 迭代更新权重直至收敛；基于 ROC 曲线确定最优分类阈值输出类别与概率。
### 约束处理
- 样本不平衡设置 `class_weight='balanced'`；共线性施加 $L_1$（Lasso）或 $L_2$（Ridge）正则化。
### 参数
- 正则化倒数 $C = 1/\lambda$（$0.01 \sim 100$）；惩罚项 `penalty`（'l1', 'l2', 'elasticnet'）；求解器 `solver`（'lbfgs', 'liblinear'）。
### 验证
- 5折交叉验证评估 AUC-ROC、Log-Loss、F1-Score；Hosmer-Lemeshow 拟合优度检验。
### 风险
- 无法直接捕捉特征非线性交互；对极端离群杠杆点敏感。
### 场景
- 金融个人信用评分卡；疾病患病概率影响因素归因与筛查。
### 比较
- 计算开销极低、几率比解释直观；拟合复杂非线性能力弱于树模型与神经网络。

## 支持向量机（SVM）
### 适用性
中小样本、高维特征空间下的非线性分类与回归（SVR）。基于最大间隔与结构风险最小化，具备强泛化能力。
### 结构或公式
- 对偶优化问题：$\max_{\boldsymbol{\alpha}} \sum \alpha_i - \frac{1}{2}\sum \alpha_i \alpha_j y_i y_j K(\mathbf{x}_i, \mathbf{x}_j)$，s.t. $0 \le \alpha_i \le C, \sum \alpha_i y_i = 0$
- RBF 高斯核：$K(\mathbf{x}_i, \mathbf{x}_j) = \exp(-\gamma \|\mathbf{x}_i - \mathbf{x}_j\|^2)$；判决函数：$f(\mathbf{x}) = \text{sign}(\sum_{i \in \text{SV}} \alpha_i y_i K(\mathbf{x}_i, \mathbf{x}) + b)$
### 算法专属步骤
1. 严格标准化所有输入特征；核函数选型（线性可分选 Linear，非线性选高斯 RBF 核）。
2. 序列最小最优化（SMO）迭代求解对偶乘子 $\alpha_i$；筛选支持向量（$\alpha_i > 0$）并计算截距 $b$。
3. 构造决策超平面并对测试样本进行符号判别。
### 约束处理
- 线性不可分引入软间隔松弛变量 $\xi_i \ge 0$ 与惩罚 $C$；类别不平衡设置非对称权重 $C_+ \neq C_-$。
### 参数
- 惩罚系数 $C$（控制间隔与误分类容忍度，$0.1 \sim 100$）；核参数 $\gamma$（默认 $1/(p \cdot \text{Var}(X))$）。
### 验证
- K折分层交叉验证；支持向量占比检查（若 SV 占比 $> 50\%$ 提示过拟合）；ROC-AUC 与 PR-AUC。
### 风险
- 样本量 $N > 50000$ 时核矩阵计算与内存复杂度达 $O(N^2 \sim N^3)$；黑盒模型不可直观解释。
### 场景
- 基因高维小样本癌症亚型分类；文本小样本特征分类；材料微观结构性能回归。
### 比较
- 在高维小样本场景下泛化性与抗噪能力超越逻辑回归与浅层神经网络；大规模数据训练效率不及 XGBoost。

## 决策树（Decision Tree）
### 适用性
处理混合类型特征（连续+类别）的分类与回归。具备天然的白盒规则可视化与特征非线性交互捕捉能力。
### 结构或公式
- 信息增益（ID3）：$IG(D, A) = H(D) - \sum \frac{|D^v|}{|D|} H(D^v)$
- 基尼指数（CART）：$Gini(D) = 1 - \sum p_k^2$；分裂增益：$\Delta Gini = Gini(D) - (\frac{|D_L|}{|D|}Gini(D_L) + \frac{|D_R|}{|D|}Gini(D_R))$
### 算法专属步骤
1. 遍历所有候选特征及其切分阈值，计算分裂前后的不纯度下降量。
2. 贪心选取增益最大的特征与阈值作为节点分裂条件，递归构建左右子树。
3. 触发终止条件后，利用代价复杂度剪枝（CCP，极小化 $R(T) + \alpha |T|$）生成最优子树并提取 `IF-THEN` 规则。
### 约束处理
- 连续特征通过排序与中点离散化；缺失值通过替代分裂（Surrogate Splits）路由。
### 参数
- 最大树深 `max_depth`（推荐 $3 \sim 8$）；分裂最小样本数 `min_samples_split`；剪枝参数 `ccp_alpha`。
### 验证
- 交叉验证确定最优剪枝树深；特征重要性（Gini 减少量加权）排序；测试集混淆矩阵。
### 风险
- 单棵树方差极大，数据微小扰动会导致树结构彻底重构；极易过拟合深层叶节点。
### 场景
- 医疗辅助诊断路径推导；企业信贷准入规则树构建；工业设备故障根因定位。
### 比较
- 可解释性最强，直观展现决策流；但单模型预测精度与稳定性普遍弱于集成森林算法。

## 随机森林（Random Forest）
### 适用性
大规模结构化表格数据的分类、回归与特征重要性评估。基于 Bagging 集成思想，具备极高准确率与抗噪鲁棒性。
### 结构或公式
- 集成决策规则（分类）：$\hat{y} = \arg\max_{c} \sum_{b=1}^B I(T_b(\mathbf{x}) = c)$；回归：$\hat{y} = \frac{1}{B}\sum_{b=1}^B T_b(\mathbf{x})$
- 泛化误差界：$PE^* \le \frac{\bar{\rho}(1-s^2)}{s^2}$（$\bar{\rho}$ 为树间平均相关度，$s$ 为单树平均强度）
### 算法专属步骤
1. Bootstrap 抽样：从容量为 $N$ 的训练集中有放回随机抽取 $B$ 个自助样本子集。
2. 随机特征分裂：构建每棵树时，节点分裂仅随机抽取 $m \ll p$ 个特征候选最优切分；单树充分生长不剪枝。
3. 并行集成预测：聚合所有 $B$ 棵树的投票结果或均值输出；利用袋外样本（OOB）评估泛化误差与特征重要性。
### 约束处理
- 类别不平衡采用平衡随机森林（Balanced RF，Bootstrap 阶段分层平衡采样）或类别加权。
### 参数
- 决策树棵数 `n_estimators`（$100 \sim 500$）；分裂特征数 `max_features`（分类取 $\sqrt{p}$，回归取 $p/3$）；`max_depth`。
### 验证
- OOB 误差评估（无需独立验证集）；K折交叉验证；Permutation Feature Importance 排序。
### 风险
- 无法外推超出训练集目标值取值范围的回归趋势；对高基数类别特征重要性存在偏好。
### 场景
- 遥感多光谱地物覆盖分类；金融风控反欺诈检测；高维生物信息特征筛选。
### 比较
- 相比单决策树方差大幅降低；相比 Boosting 调参更简单稳健，支持多进程完全并行化训练。

## XGBoost
### 适用性
结构化表格数据的高精度分类、回归与排序任务。基于 Gradient Boosting 框架的高效工程实现，为竞赛主流主力模型。
### 结构或公式
- 目标函数二阶展开：$\tilde{\mathcal{L}}^{(t)} \approx \sum [g_i f_t(\mathbf{x}_i) + \frac{1}{2} h_i f_t^2(\mathbf{x}_i)] + \gamma T + \frac{1}{2}\lambda \sum w_j^2$
- 最优叶权重与分裂增益：$w_j^* = -\frac{G_j}{H_j + \lambda}$，$\text{Gain} = \frac{1}{2}\left[ \frac{G_L^2}{H_L+\lambda} + \frac{G_R^2}{H_R+\lambda} - \frac{(G_L+G_R)^2}{H_L+H_R+\lambda} \right] - \gamma$
### 算法专属步骤
1. 初始化模型常数预测值；迭代计算各样本一阶梯度 $g_i$ 与二阶 Hessian 梯度 $h_i$。
2. 采用加权分位数略图搜索使 $\text{Gain}$ 最大的特征与切分点；计算叶节点最优权重 $w_j^*$。
3. 按学习率 $\eta$ 累加更新预测值：$\hat{y}^{(t)} = \hat{y}^{(t-1)} + \eta f_t(\mathbf{x})$；结合 Early Stopping 终止迭代。
### 约束处理
- 自动学习缺失值默认分裂方向；行采样 `subsample` 与列采样 `colsample_bytree` 正则约束；$L_1/L_2$ 惩罚约束叶权重。
### 参数
- 学习率 `learning_rate`（$0.01 \sim 0.1$）；树深 `max_depth`（$3 \sim 8$）；正则参数 `reg_lambda`（$\lambda$）、`gamma`（$\gamma$）。
### 验证
- 5折分层交叉验证；早停监控曲线；SHAP 值归因解释特征贡献。
### 风险
- 超参数较多，网格搜索耗时且易局部过拟合；对离群异常标签噪声敏感。
### 场景
- 数模竞赛表格数据预测冲高分主力模型；电商转化率 CTR 预估；量化多因子评分。
### 比较
- 引入二阶导数与显式树复杂度正则项，精度与收敛速度优于传统 GBDT；小样本上比 LightGBM 更不易过拟合。

## BP神经网络（BPNN）
### 适用性
多层前馈神经网络，通过反向传播误差梯度拟合复杂多维非线性连续映射、多输入多输出函数逼近与复杂模式分类。
### 结构或公式
- 前向传播：$\mathbf{z}^{[l]} = W^{[l]} \mathbf{a}^{[l-1]} + \mathbf{b}^{[l]}, \quad \mathbf{a}^{[l]} = \sigma(\mathbf{z}^{[l]})$
- 反向误差传播：$\boldsymbol{\delta}^{[l]} = ((W^{[l+1]})^T \boldsymbol{\delta}^{[l+1]}) \odot \sigma'(\mathbf{z}^{[l]})$；权重更新：$W^{[l]} \leftarrow W^{[l]} - \eta \boldsymbol{\delta}^{[l]} (\mathbf{a}^{[l-1]})^T$
### 算法专属步骤
1. 数据归一化至 $[0, 1]$；设计网络拓扑（输入层、隐藏层节点数及输出层激活函数）与权重初始化（He/Xavier）。
2. 前向传播计算各层激活值与损失函数（MSE/交叉熵）。
3. 反向传播基于链式法则逐层传递误差梯度；优化器（Adam/SGD）结合 Mini-batch 更新权值直至收敛。
### 约束处理
- 防过拟合引入 Dropout、权重衰减（$L_2$ 正则）及 Early Stopping；梯度消失采用 ReLU 与 BatchNorm。
### 参数
- 隐藏层神经元数（经验公式 $n_h = \sqrt{n_{in} + n_{out}} + \alpha$）；学习率 $\eta$（$10^{-3} \sim 10^{-4}$）；`batch_size`（32/64）。
### 验证
- 训练集与验证集 Loss 学习曲线；测试集 RMSE/MAE 与残差正态性检验。
### 风险
- 极易陷入局部极小与鞍点；样本量小时易发生过拟合；黑盒不可解释。
### 场景
- 复杂非线性物理系统黑盒代理建模；短期多变量时间序列滑动窗口预测；传感器模式识别。
### 比较
- 拟合任意复杂连续非线性函数能力强；但在结构化表格数据上调参难度与训练成本高于树模型。

## K近邻（KNN）
### 适用性
基于实例的非参数惰性学习（Lazy Learning）分类与回归方法。适用于特征维度较低、局部结构明显的空间近邻决策。
### 结构或公式
- Minkowski 距离：$D(\mathbf{x}, \mathbf{z}) = (\sum |x_j - z_j|^q)^{1/q}$（$q=2$ 欧氏距离，$q=1$ 曼哈顿距离）
- 分类多数表决：$\hat{y} = \arg\max_{c} \sum_{\mathbf{x}_i \in N_k(\mathbf{x})} I(y_i = c)$；距离反比加权：$w_i = \frac{1}{D(\mathbf{x}, \mathbf{x}_i) + \epsilon}$
### 算法专属步骤
1. 数据严格标准化；构建 KD-Tree 或 Ball-Tree 空间索引树以加速近邻搜索。
2. 输入待测样本 $\mathbf{x}$，检索空间距离最近的 $K$ 个训练样本集合 $N_k(\mathbf{x})$。
3. 分类执行多数/加权表决，回归计算近邻目标值均值，输出预测结果。
### 约束处理
- 高维数据距离失效（维度灾难），须先通过 PCA 降维或特征筛选；样本不平衡采用距离倒数加权。
### 参数
- 近邻数 $K$（通常选奇数 $3 \sim 15$）；距离度量类型 `metric`（'euclidean', 'manhattan'）。
### 验证
- K折交叉验证或留一法（LOOCV）寻找最优 $K$ 值与距离范数；测试集准确率与分类边界可视化。
### 风险
- 预测阶段须遍历样本库计算距离，大样本下推理开销巨大；对噪声特征极度敏感。
### 场景
- 推荐系统相似用户/物品检索；空间地理近邻属性插值；低维数据分类 Baseline。
### 比较
- 无显式训练过程（$O(1)$ 训练），概念最直观；但高维大规模数据下性能远逊于 SVM 和树模型。

## K-means聚类
### 适用性
无监督数值型数据样本硬划分聚类。适用于簇分布为凸集、各向同性（球状分布）且各簇方差相近的大规模数据集。
### 结构或公式
- 簇内误差平方和（WCSS / Inertia）：$J = \sum_{k=1}^K \sum_{\mathbf{x}_i \in C_k} \|\mathbf{x}_i - \boldsymbol{\mu}_k\|_2^2$
- 质心更新公式：$\boldsymbol{\mu}_k = \frac{1}{|C_k|}\sum_{\mathbf{x}_i \in C_k} \mathbf{x}_i$
### 算法专属步骤
1. 数据标准化消除量纲差异；采用 K-means++ 初始化 $K$ 个互不重叠的初始质心。
2. 样本分配：计算每个样本到各质心的欧氏距离，指派给最近质心所属簇 $C_k$。
3. 质心重算：计算各簇样本均值更新质心 $\boldsymbol{\mu}_k$；重复分配与重算直至质心漂移小于容差 $\epsilon$。
### 约束处理
- 离群异常值拉偏质心时改用 K-Medoids（PAM）；簇大小均衡约束采用 Same-size K-means。
### 参数
- 聚类数 $K$；初始化方案 `init='k-means++'`；重复初始化次数 `n_init=10`；最大迭代轮数 `max_iter=300`。
### 验证
- 肘部法则（Elbow Method 观察 WCSS 拐点）；轮廓系数（Silhouette Score $\in [-1, 1]$）；CH 指数。
### 风险
- 必须预先人为指定 $K$ 值；无法识别非凸形状簇；极易受孤立异常点干扰。
### 场景
- 客户价值 RFM 分群画像；城市物流网点选址聚类；遥感图像像素颜色量化。
### 比较
- 时间复杂度 $O(N \cdot K \cdot I)$，大规模数据求解极快；但对非球状簇与噪声的鲁棒性不如 DBSCAN。

## DBSCAN
### 适用性
基于密度的空间无监督聚类。能够自动发现任意复杂几何形状的簇，且天然具备离群噪声点识别与过滤能力。
### 结构或公式
- $\varepsilon$-邻域：$N_\varepsilon(\mathbf{x}) = \{ \mathbf{x}' \in D \mid \text{dist}(\mathbf{x}, \mathbf{x}') \le \varepsilon \}$
- 核心点判定条件：$|N_\varepsilon(\mathbf{x})| \ge \text{MinPts}$；边界点与噪声点（标记为 $-1$）。
### 算法专属步骤
1. 计算全量样本在半径 $\varepsilon$ 内的邻域样本计数，标记核心点与边界点。
2. 从未访问核心点出发，利用 BFS/DFS 搜索所有密度可达样本点，扩展为极大密度连通簇。
3. 递归遍历所有核心点，直到所有样本归入特定簇或标定为噪声点；输出各独立簇与噪声点集。
### 约束处理
- 经纬度地理坐标选用 Haversine 距离；高维特征先使用 PCA 降维防止密度失效。
### 参数
- 邻域半径 $\varepsilon$（通过 K-距离图拐点确定）；最小样本数 $\text{MinPts}$（通常取 $2 \times \text{dim}$ 或 $\ge 4$）。
### 验证
- 轮廓系数（排除噪声点后计算）；DBCV 指数；噪声点比例合理性检验（通常 $< 10\% \sim 15\%$）。
### 风险
- 数据集存在多尺度不同密度簇时，全局单一 $(\varepsilon, \text{MinPts})$ 无法兼顾疏密不同簇。
### 场景
- GPS 轨迹停留点挖掘与热点出行区域提取；网络异常流量离群点检测；天文学星团识别。
### 比较
- 无需指定簇数 $K$，能发现任意非凸流形簇并过滤噪声；但在密度极不均匀数据上不如 HDBSCAN。

## 层次聚类（Hierarchical Clustering）
### 适用性
构建样本间层次嵌套树状聚类体系（Dendrogram）。适用于小样本探索性分析、生物分类学谱系构建与多尺度分层决策。
### 结构或公式
- Ward 最小方差准则：$\Delta ESS_{AB} = \frac{n_A n_B}{n_A + n_B} \|\boldsymbol{\mu}_A - \boldsymbol{\mu}_B\|_2^2$
- 最长距离法（Complete）：$D(A, B) = \max_{\mathbf{x} \in A, \mathbf{y} \in B} d(\mathbf{x}, \mathbf{y})$；平均距离（Average）：$D(A, B) = \frac{1}{|A||B|} \sum \sum d(\mathbf{x}, \mathbf{y})$
### 算法专属步骤
1. 自底向上聚合初始化：将每个样本点视为单独的单元素初始簇，计算初始两两距离矩阵。
2. 聚类合并：在矩阵中寻找距离最小的两个簇 $A$ 和 $B$，合并为新簇 $A \cup B$。
3. 距离更新：依据指定链接准则（Ward/Complete/Average）更新距离矩阵；重复合并直至汇聚为单一根簇。
4. 绘制谱系聚类树状图（Dendrogram），选取合适高度截断线输出指定 $K$ 个聚类。
### 约束处理
- 大样本内存超限可采用 BIRCH 算法先做微簇预聚类；支持任意非欧几何自定义距离矩阵。
### 参数
- 目标簇数 $K$ 或截断距离阈值 `distance_threshold`；链接方法 `linkage`（推荐 'ward' 或 'complete'）；距离范数 `affinity`。
### 验证
- 共性相关系数（Cophenetic Correlation Coefficient，要求 $> 0.75$）；轮廓系数。
### 风险
- 合并过程贪心不可逆，早期错误合并无法撤销；时间复杂度 $O(N^3)$，不适合大规模数据。
### 场景
- 生物基因序列相似性谱系进化树构建；多层级产品品类谱系划分；区域经济梯队分层。
### 比较
- 输出完整的层次结构树状图，信息丰富且无需预先固定 $K$；但计算开销大，不适合大规模数据集。
