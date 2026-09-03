---
name: math-modeling-unified
description: 当用户要求数学建模、建模竞赛、建模分析、代码求解、结果可视化或生成数学建模论文时使用。
---

# 数学建模统一工作流

## 启动回显

首次进度更新必须回显：已激活 `$math-modeling-unified`；解析后的 `SKILL_ROOT` 与 `PROJECT_ROOT`；任务类型、竞赛名称、届次/年份、当前阶段；本轮计划读取的内部入口。尚未从当届官方来源确认的规则统一标为“待核验”，不得把历史经验写成现行要求。

## 根目录与单一入口

- `SKILL_ROOT` 是本文件所在目录，只读；内部说明、工具、模板和资产只从这里读取。
- `PROJECT_ROOT` 是用户项目目录；所有新产物只写入这里。两根目录必须不同。
- 题目、附件、数据和用户模板均按只读输入处理；确需修改时先复制到 `PROJECT_ROOT`，再改复制件。
- 本文件是唯一直接入口。不得调用、要求或委派给旧入口 `math-modeling`、`cumcm-step-review` 或 `cumcm-c-problem`；直接读取下表中的统一内部模块。

## 范围与共享合同

完整计算章节、完整非计算章节、摘要和局部任务分别按[逐步审核与冻结工作流](references/workflow/step-review.md)中的结构化路由合同执行；该文件是门禁、依赖、规则优先级、学术诚信与完成纪律的唯一共享规范。局部任务不得扩张为完整论文，缺少前置输入时只回补最小必要范围。

三角色按 [建模手](references/roles/modeler.md) → [编程手](references/roles/programmer.md) → [论文手](references/roles/writer.md) 闭环协作；具体文件范围见 [交付物与项目合同](references/workflow/deliverables.md)。下游发现缺陷时携证据返回对应上游，从阻断处继续，不重复已冻结且未受影响的工作。

## 渐进式加载

| 何时读取 | 内部入口 |
|---|---|
| 启动完整任务或推进任一部分 | [逐步审核工作流](references/workflow/step-review.md)、[交付物与项目合同](references/workflow/deliverables.md) |
| 形成题意、模型合同、候选方案 | [建模手](references/roles/modeler.md) |
| 写代码、真实运行、验证、出图与复现 | [编程手](references/roles/programmer.md) |
| 写入 Word 草稿、论文正文或检查证据 | [论文手](references/roles/writer.md) |
| 确认为 CUMCM 任务后读取 | [CUMCM 通用规则](references/competition/cumcm.md) |
| 确认为 CUMCM 本科组 C 题后，在通用规则之上读取 | [C 题专用规则](references/competition/c-problem.md)（仅限 C 题） |
| 选择模型或查算法时读取 | [模型选型](references/modeling/model-selection.md)、[算法库](references/modeling/algorithm-library.md)（只读相关条目） |
| 生成或审核图表时读取 | [可视化规范](references/visualization/visualization.md) |
| 把内容写入论文草稿前读取 | [论文写作指南](references/writing/paper-guidance.md)、[证据门禁](references/writing/evidence-gates.md) |
| 写、改或评摘要时读取 | [摘要闭环](references/writing/abstract.md) |
| 阶段冻结或最终交付前读取 | [质量门禁](references/quality/quality-gates.md) |
| 需要统一工具、脚本或资产时读取 | `tools/`、`scripts/`、`assets/`（按需使用） |

禁止一次性加载全部资料；不得回退调用旧 Skill。

## 完成判定

完成声明按[逐步审核与冻结工作流](references/workflow/step-review.md)的共享完成纪律判定；入口只负责报告实际采用的路由和产物位置。
