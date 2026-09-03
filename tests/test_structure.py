from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
OPENAI = ROOT / "agents" / "openai.yaml"
LINK_CHECKER_SPEC = importlib.util.spec_from_file_location(
    "check_internal_links", ROOT / "scripts" / "check_internal_links.py"
)
assert LINK_CHECKER_SPEC is not None and LINK_CHECKER_SPEC.loader is not None
link_checker = importlib.util.module_from_spec(LINK_CHECKER_SPEC)
LINK_CHECKER_SPEC.loader.exec_module(link_checker)

CURRENT_MODULES = (
    "references/workflow/step-review.md",
    "references/workflow/deliverables.md",
    "references/roles/modeler.md",
    "references/roles/programmer.md",
    "references/roles/writer.md",
    "references/competition/cumcm.md",
    "references/competition/c-problem.md",
    "references/modeling/model-selection.md",
    "references/modeling/algorithm-library.md",
    "references/writing/paper-guidance.md",
    "references/writing/evidence-gates.md",
    "references/writing/abstract.md",
    "references/visualization/visualization.md",
    "references/quality/quality-gates.md",
)


def read(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), f"missing unified module: {relative}"
    return path.read_text(encoding="utf-8")


def normalized(text: str) -> str:
    return re.sub(r"[\s`*_]+", "", text).casefold()


def assert_in_order(text: str, needles: tuple[str, ...]) -> None:
    compact = normalized(text)
    positions: list[int] = []
    cursor = 0
    for needle in needles:
        position = compact.find(normalized(needle), cursor)
        positions.append(position)
        if position >= 0:
            cursor = position + len(normalized(needle))
    assert all(position >= 0 for position in positions), (needles, positions)


def test_internal_link_checker_rejects_unrelated_same_basename(tmp_path: Path) -> None:
    document = tmp_path / "docs" / "guide.md"
    document.parent.mkdir()
    document.write_text("[target](missing/note.md)", encoding="utf-8")
    unrelated = tmp_path / "elsewhere" / "note.md"
    unrelated.parent.mkdir()
    unrelated.write_text("not the target", encoding="utf-8")

    errors = link_checker.check_links(tmp_path)

    assert len(errors) == 1
    assert "broken link 'missing/note.md'" in errors[0]


def test_migrated_loaders_restore_unique_module_registrations() -> None:
    migrated = ROOT / "tests" / "migrated" / "math-modeling"
    scripts = sorted(migrated.glob("test_*.py"))
    probe = r'''
import runpy
import sys
from pathlib import Path

prefix = "migrated_math_modeling_"
before = {name for name in sys.modules if name.startswith(prefix)}
namespaces = {}
for script in map(Path, sys.argv[1:]):
    namespaces[script.name] = runpy.run_path(script, run_name=f"probe_{script.stem}")
after_success = {name for name in sys.modules if name.startswith(prefix)}
if after_success != before:
    raise SystemExit(f"successful loads leaked: {sorted(after_success - before)}")

loader = namespaces["test_xlsx_read.py"]["_load_source_module"]
try:
    loader("definitely_missing_module")
except FileNotFoundError:
    pass
else:
    raise SystemExit("failed-load probe unexpectedly succeeded")
after_failure = {name for name in sys.modules if name.startswith(prefix)}
if after_failure != before:
    raise SystemExit(f"failed load leaked: {sorted(after_failure - before)}")
'''

    result = subprocess.run(
        [sys.executable, "-c", probe, *(str(script) for script in scripts)],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=ROOT,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def route_contract() -> dict:
    text = read("references/workflow/step-review.md")
    match = re.search(r"```yaml\s*(.*?)\s*```", text, re.DOTALL)
    assert match is not None, "missing structured route contract"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict)
    return data


def writer_contract() -> dict:
    text = read("references/roles/writer.md")
    match = re.search(r"```yaml\s*(.*?)\s*```", text, re.DOTALL)
    assert match is not None, "missing structured writer contract"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict)
    return data


def test_required_entry_and_modules_exist() -> None:
    assert SKILL.is_file()
    assert OPENAI.is_file()
    for relative in CURRENT_MODULES:
        assert (ROOT / relative).is_file(), relative


def test_frontmatter_has_exact_name_and_concrete_trigger_only() -> None:
    text = read("SKILL.md")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    assert match is not None
    frontmatter = yaml.safe_load(match.group(1))
    assert frontmatter["name"] == "math-modeling-unified"
    description = frontmatter["description"]
    assert description.startswith("当用户") and "时使用" in description
    for trigger in ("数学建模", "竞赛", "分析", "代码", "可视化", "论文"):
        assert trigger in description
    assert "→" not in description and "步骤" not in description


def test_entry_routes_directly_to_internal_modules_and_marks_future_links() -> None:
    text = read("SKILL.md")
    for relative in CURRENT_MODULES:
        assert f"]({relative})" in text

    legacy_rule = re.search(
        r"不得.{0,30}(?:调用|要求|委派).{0,100}math-modeling.{0,100}cumcm-step-review.{0,100}cumcm-c-problem",
        text,
        re.DOTALL,
    )
    assert legacy_rule is not None
    assert "required sub-skill" not in text.casefold()

    assert "计划中" not in text
    assert "Task" not in text


def test_first_update_and_root_contract_are_explicit() -> None:
    text = normalized(read("SKILL.md") + read("references/workflow/deliverables.md"))
    for item in (
        "首次进度更新",
        "math-modeling-unified",
        "SKILL_ROOT",
        "PROJECT_ROOT",
        "任务类型",
        "竞赛",
        "届次",
        "当前阶段",
        "计划读取",
        "待核验",
        "只读",
        "必须不同",
        "先复制",
    ):
        assert normalized(item) in text
    assert normalized("所有新产物") in text
    assert normalized("PROJECT_ROOT") in text


def test_default_full_task_gate_has_ordered_user_approvals() -> None:
    contract = route_contract()
    assert contract["canonical"] is True
    assert contract["routes"]["full_computational"]["sequence"] == [
        "understand_inputs",
        "recommend_2_to_3_candidates",
        "user_approves_candidate",
        "implement_and_run_truthfully",
        "validate_results",
        "user_approves_results",
        "draft_word",
        "user_reviews_and_freezes",
    ]
    assert contract["dependency_policy"] == "block_until_upstream_approved"


def test_full_computational_first_round_requires_immediate_comparative_review() -> None:
    route = route_contract()["routes"]["full_computational"]
    review = route["first_round_review"]
    assert review == {
        "present_now": True,
        "candidate_paths": {"minimum": 2, "maximum": 3},
        "comparison_dimensions": [
            "interpretability",
            "data_fit",
            "validation",
            "implementation_cost",
        ],
        "explicit_recommendation_required": True,
        "pause_for_user_confirmation": True,
        "before_confirmation_forbidden": [
            "promise_or_start_code",
            "promise_or_generate_results",
            "promise_or_generate_figures",
            "promise_or_draft_paper",
        ],
    }

    combined = normalized(
        read("references/workflow/step-review.md")
        + read("references/roles/modeler.md")
        + read("references/modeling/model-selection.md")
    )
    for phrase in (
        "当场列出2–3个候选路径",
        "不能只承诺稍后补充",
        "可解释性",
        "数据适配",
        "验证方案",
        "实现成本",
        "明确推荐一个路径",
        "暂停并等待用户明确确认",
        "不得承诺或开始代码、结果、图表或论文",
    ):
        assert normalized(phrase) in combined


def test_structured_route_decisions_cover_required_scenarios() -> None:
    routes = route_contract()["routes"]
    assert routes["full_noncomputational"]["sequence"] == [
        "prepare_evidence_and_source_outline",
        "user_approves_outline",
        "draft_word",
        "user_reviews_and_freezes",
    ]
    assert routes["full_noncomputational"]["requires_code_or_run"] is False
    assert routes["partial_code_only"]["scope"] == "requested_plus_minimum_prerequisites"
    assert routes["partial_code_only"]["produces_full_paper"] is False
    assert routes["writer_missing_evidence"] == {
        "draft_allowed": False,
        "decision": "backtrack_to_programmer_or_modeler",
    }
    assert routes["legacy_skill_request"] == {
        "invoke_legacy_skill": False,
        "decision": "use_unified_internal_modules",
    }


def test_writer_prerequisites_follow_section_type_routes() -> None:
    prerequisites = writer_contract()["draft_prerequisites"]
    assert prerequisites["computational"] == ["model_approved", "results_approved"]
    assert prerequisites["noncomputational"] == ["evidence_and_source_outline_approved"]
    assert "results_approved" not in prerequisites["noncomputational"]
    assert prerequisites["abstract"] == ["all_evidence_frozen", "use_abstract_route"]


def test_abstract_and_academic_integrity_are_explicit_contracts() -> None:
    contract = route_contract()
    assert contract["routes"]["abstract"]["sequence"] == [
        "check_all_evidence_frozen",
        "draft",
        "second_validation",
        "finalize",
        "user_review",
    ]
    integrity = contract["academic_integrity"]
    assert integrity["artifact_status"] == "reference_material_for_user_review"
    assert integrity["automatically_submit_ready"] is False
    assert integrity["user_responsible_for"] == [
        "competition_rules",
        "ai_disclosure",
        "submission_decision",
    ]


def test_step_review_is_the_shared_canonical_contract() -> None:
    assert "workflow/step-review.md" in read("SKILL.md")
    for role in ("modeler.md", "programmer.md", "writer.md"):
        assert "../workflow/step-review.md" in read(f"references/roles/{role}")


def test_shared_norms_are_not_redefined_by_entry_or_roles() -> None:
    canonical = read("references/workflow/step-review.md")
    satellites = "\n".join(
        read(path)
        for path in (
            "SKILL.md",
            "references/roles/modeler.md",
            "references/roles/programmer.md",
            "references/roles/writer.md",
        )
    )
    for shared_rule in (
        "警告视为未完成",
        "可选独立 Subagent 质检默认关闭",
        "用户审核是独立硬门禁",
    ):
        assert shared_rule in canonical
        assert shared_rule not in satellites
    assert "## 规则优先级" not in satellites


def test_step_review_preserves_working_and_final_orders_and_abstract_gate() -> None:
    text = read("references/workflow/step-review.md")
    compact = normalized(text)
    for heading in ("写作与审核顺序", "最终成稿顺序"):
        assert normalized(heading) in compact
    assert_in_order(
        text,
        (
            "问题重述",
            "数据预处理",
            "逐问建模与求解",
            "模型的分析与检验",
            "模型的评价与推广",
            "参考文献",
            "附录",
            "问题分析",
            "模型假设",
            "符号说明",
            "摘要",
        ),
    )
    for phrase in ("摘要最后", "起草", "二次验证", "定稿", "用户审核"):
        assert normalized(phrase) in compact


def test_role_loop_backtracks_without_repeating_frozen_work() -> None:
    combined = "\n".join(read(path) for path in CURRENT_MODULES)
    compact = normalized(combined)
    for phrase in (
        "题目分析报告.md",
        "术语表格.md",
        "真实运行",
        "复现清单.json",
        "已审核",
        "真实输出",
        "证据",
        "返回建模手",
        "返回编程手",
        "不重复已冻结",
    ):
        assert normalized(phrase) in compact


def test_unique_source_constraints_are_retained() -> None:
    combined = "\n".join(read(path) for path in ("SKILL.md",) + CURRENT_MODULES)
    compact = normalized(combined)
    required = (
        "每个子问题最多两个独立模型体系",
        "同一物理机制",
        "模型族",
        "复杂度本身不构成创新",
        "当届官方规则",
        "历史",
        "警告视为未完成",
        "不得静默降级",
        "引用可追溯",
    )
    for phrase in required:
        assert normalized(phrase) in compact
    contract = route_contract()
    assert contract["independent_qa"] == "optional_default_off_cannot_replace_user_review"
    assert contract["final_report_requires"] == [
        "actual_internal_entries",
        "actual_commands_and_exit_codes",
        "results_and_validation",
        "approval_and_freeze_status",
        "unresolved_blockers",
    ]


def test_deliverables_reconcile_full_and_partial_scope() -> None:
    text = normalized(read("references/workflow/deliverables.md"))
    for phrase in (
        "论文草稿.docx",
        "Word",
        "审核载体",
        "不是Markdown",
        "完整论文.docx",
        "完整论文.pdf",
        "完整论文-LaTeX",
        "可运行代码",
        "真实结果",
        "图",
        "复现清单.json",
        "局部任务",
        "只交付",
    ):
        assert normalized(phrase) in text


def test_openai_interface_is_exact_and_has_no_explicit_only_policy() -> None:
    data = yaml.safe_load(read("agents/openai.yaml"))
    assert data == {
        "interface": {
            "display_name": "数学建模统一工作流",
            "short_description": "逐步完成数学建模、代码求解、验证与论文写作",
            "default_prompt": "使用 $math-modeling-unified 按逐步审核门禁处理当前数学建模任务。",
        }
    }


def test_all_unplanned_internal_markdown_links_exist() -> None:
    for source in (SKILL,) + tuple(ROOT / item for item in CURRENT_MODULES):
        text = source.read_text(encoding="utf-8")
        for label, target in re.findall(r"\[([^]]+)]\(([^)]+\.md)\)", text):
            line = next(line for line in text.splitlines() if f"]({target})" in line)
            if "计划中" in line:
                continue
            assert not target.startswith(("/", "http://", "https://")), (source, target)
            assert (source.parent / target).is_file(), (source, label, target)


def test_validation_record_cannot_claim_completion_while_any_gate_is_pending() -> None:
    validation = read("VALIDATION.md")
    matrix = json.loads(read("references/provenance/coverage-matrix.json"))
    declared_status = re.search(r"\*\*Coverage Matrix Status\*\*:\s*`?([a-z-]+)`?", validation)
    assert declared_status is not None
    assert declared_status.group(1) == matrix["status"]

    pending = re.findall(r"^- .*\bPENDING\b.*$", validation, re.MULTILINE)
    assert pending, "in-progress validation must enumerate the remaining gates"
    assert "**Record Status**: **IN PROGRESS**" in validation
    assert "**Installation Ready**: **NO**" in validation
    forbidden = (
        "all tasks complete",
        "fully verified",
        "installation-ready",
        "ready to proceed",
        "100% green",
    )
    compact = validation.casefold()
    assert not any(phrase in compact for phrase in forbidden)
