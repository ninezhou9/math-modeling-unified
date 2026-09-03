# 逐步审核与冻结工作流

本文件是所有角色与统一入口共享的门禁、依赖、规则优先级和完成纪律的唯一规范来源。角色文件只补充职责，不重定义这些规则。

只有在需要追溯旧工作流的完整说明或核对迁移语义时，才读取保留的[CUMCM 分步审核总结](../competition/workspace/CUMCM-Step-Review-Skill总结.md)与[通用数学建模 Skill 详细总结](../modeling/workspace/math-modeling-skill-详细总结.md)；执行时始终以本页合同为准。

## 路由合同

```yaml
version: 1
canonical: true
dependency_policy: block_until_upstream_approved
independent_qa: optional_default_off_cannot_replace_user_review
final_report_requires:
  - actual_internal_entries
  - actual_commands_and_exit_codes
  - results_and_validation
  - approval_and_freeze_status
  - unresolved_blockers
routes:
  full_computational:
    applies_to: modeling_data_processing_solution_validation_and_computational_evaluation
    sequence:
      - understand_inputs
      - recommend_2_to_3_candidates
      - user_approves_candidate
      - implement_and_run_truthfully
      - validate_results
      - user_approves_results
      - draft_word
      - user_reviews_and_freezes
    first_round_review:
      present_now: true
      candidate_paths:
        minimum: 2
        maximum: 3
      comparison_dimensions:
        - interpretability
        - data_fit
        - validation
        - implementation_cost
      explicit_recommendation_required: true
      pause_for_user_confirmation: true
      before_confirmation_forbidden:
        - promise_or_start_code
        - promise_or_generate_results
        - promise_or_generate_figures
        - promise_or_draft_paper
  full_noncomputational:
    applies_to: references_appendix_narrative_problem_analysis_assumptions_symbols_and_nonrun_evaluation
    requires_code_or_run: false
    sequence:
      - prepare_evidence_and_source_outline
      - user_approves_outline
      - draft_word
      - user_reviews_and_freezes
  partial_code_only:
    scope: requested_plus_minimum_prerequisites
    produces_full_paper: false
    sequence:
      - check_executable_model_contract
      - implement_run_and_validate
      - deliver_code_results_and_reproduction_record
  writer_missing_evidence:
    draft_allowed: false
    decision: backtrack_to_programmer_or_modeler
  legacy_skill_request:
    invoke_legacy_skill: false
    decision: use_unified_internal_modules
  abstract:
    sequence:
      - check_all_evidence_frozen
      - draft
      - second_validation
      - finalize
      - user_review
academic_integrity:
  artifact_status: reference_material_for_user_review
  automatically_submit_ready: false
  user_responsible_for:
    - competition_rules
    - ai_disclosure
    - submission_decision
```

## 共享规则优先级与完成纪律

1. 用户当前明确要求、赛题原文、附件、当届官方规则和官方模板；
2. 本 Skill 的范围、安全、真实性、根目录与用户审核约束；
3. 适用的竞赛通用规则和题型专用规则；
4. 通用角色、算法、写法与历史经验。

当届官方规则覆盖历史指导；未知规则标为“待核验”。同级来源冲突时列出来源、影响和建议并请用户决定。警告视为未完成。工具、引擎、搜索源、渲染器或依赖缺失时报告阻塞，不得静默降级或用较差产物冒充完成。引用必须追溯到 DOI、原始出版页或权威原始来源。

用户审核是独立硬门禁。可选独立 Subagent 质检默认关闭，仅能附加，不能替代用户审核。最终回复必须列出实际读取入口、实际运行命令与退出码、结果与验证、审核/冻结状态和未解决阻塞；未运行的命令不得列作通过。

生成的竞赛论文或草稿仅是供用户审阅的参考材料，不代表已自动满足提交条件。用户负责核对竞赛规则、履行 AI 使用披露并自行决定是否提交，Skill 不得把产物表述为可自动直接参赛提交。

## 分类型门禁

完整计算型请求的首轮方案审核输出必须当场列出 2–3 个候选路径，不能只承诺稍后补充，也不能把单一主路径后的“可选方法”算作独立候选。逐项比较可解释性、数据适配、验证方案和实现成本，明确推荐一个路径及理由，然后暂停并等待用户明确确认。确认前不得承诺或开始代码、结果、图表或论文；即使用户要求“一次性完成”或“不要中途询问”，也不能越过这一审核门。

用户批准候选路径后才实现并真实运行。编程手记录命令、退出码、环境、参数、种子和真实输出，提交结果与边界、约束、误差或稳定性验证；结果经用户批准后，论文手才写入 `论文草稿.docx`，再由用户审核并冻结。

非计算章节包括参考文献、附录叙述与材料清单、问题分析、模型假设、符号说明，以及不需要新增运行的评价内容。它们提交证据/来源大纲供用户批准后直接起草 Word 正文，再审核冻结；不得为了套流程伪造代码、运行或计算结果。若评价依赖新增计算，则改走计算章节门禁。

用户未批准上游，不得进入依赖它的后续阶段。冻结内容实质变化时仅使受影响审核失效。局部任务只执行用户指定范围和最小必要前置检查：代码任务不扩成论文，写作缺真实证据时返回相应上游，不擅自补造。

## 三角色回退

- 编程手发现公式不完整、约束冲突、参数未定义或模型不可实现：停止猜测，提交实际命令、退出码、最小复现、预期与实际，返回建模手修订。
- 论文手发现结论无真实结果、图表、公式或文献支撑：禁止补写或美化，按缺口返回编程手或建模手。
- 修订后从被阻断阶段继续，只重做受影响的验证和审核，不重复已冻结且不受影响的工作。

## CUMCM 写作与审核顺序

在 CUMCM 完整论文任务中，工作顺序保留为：

1. 问题重述；
2. 数据预处理；
3. 逐问建模与求解（q1 → qN，每问独立走完整门禁）；
4. 模型的分析与检验；
5. 模型的评价与推广；
6. 参考文献；
7. 附录；
8. 问题分析（全部子问题确定后写）；
9. 模型假设（问题与模型确定后写）；
10. 符号说明（全文符号确定后写）；
11. 摘要（前 10 部分全部冻结后最后写）。

摘要最后执行“起草 → 二次验证 → 定稿”：起草按子问题逐段给出方法、量化结果与结论；二次验证逐值回查真实结果、逐项核对正文术语和证据；定稿提交用户审核，通过后冻结。无出处的数值标为待确认，禁止臆造。

## 最终成稿顺序

写作与审核顺序不等于最终排版顺序。最终成稿以当届官方模板为准；未另有规定时组织为：摘要独立首页 → 问题重述 → 问题分析 → 模型假设与符号说明 → 数据预处理 → 各问模型建立、求解与结果 → 模型分析与检验 → 模型评价与推广 → 参考文献 → 附录。问题分析、假设和符号说明虽后写，成稿时移到建模正文之前。

## 完成纪律

- 当前当届官方规则优先于历史指导；未核验规则保持“待核验”。
- 警告视为未完成；只有权威规则或用户明确允许的偏离才能附依据继续。
- 来源引用可追溯；计算结论必须来自真实运行，不手写结果。
- 最终回复列出实际读取的入口、实际运行的命令与退出码、结果和验证摘要、用户审核与冻结状态、任何阻塞。
