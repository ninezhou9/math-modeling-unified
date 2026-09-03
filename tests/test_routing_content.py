from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
LINK_SCRIPT = ROOT / "scripts" / "check_internal_links.py"
LINK_SPEC = importlib.util.spec_from_file_location("check_internal_links", LINK_SCRIPT)
assert LINK_SPEC is not None and LINK_SPEC.loader is not None
link_checker = importlib.util.module_from_spec(LINK_SPEC)
LINK_SPEC.loader.exec_module(link_checker)


def read(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), f"missing Task 6 module: {relative}"
    return path.read_text(encoding="utf-8")


def contract(relative: str) -> dict:
    text = read(relative)
    match = re.search(r"```yaml\s*(.*?)\s*```", text, re.DOTALL)
    assert match is not None, f"missing structured contract: {relative}"
    value = yaml.safe_load(match.group(1))
    assert isinstance(value, dict)
    return value


def normalized(text: str) -> str:
    return re.sub(r"[\s`*_]+", "", text).casefold()


def linked_paths(relative: str) -> set[str]:
    source = ROOT / relative
    return {
        (source.parent / target.split("#", 1)[0]).resolve().relative_to(ROOT.resolve()).as_posix()
        for target in re.findall(r"\[[^]]+\]\(([^)]+\.md(?:#[^)]+)?)\)", read(relative))
        if not re.match(r"^[a-z]+://", target)
    }


def reachable_operational_markdown() -> set[str]:
    return link_checker.markdown_link_closure(ROOT)


def test_competition_routes_compose_general_and_c_overlay_without_leakage() -> None:
    routing = contract("references/competition/cumcm.md")["routing"]
    assert routing["generic_math_modeling"] == []
    assert routing["cumcm_undergraduate_a"] == ["cumcm"]
    assert routing["cumcm_undergraduate_b"] == ["cumcm"]
    assert routing["cumcm_undergraduate_c"] == ["cumcm", "c_problem"]
    assert routing["cumcm_undergraduate_d"] == ["cumcm"]
    assert routing["cumcm_undergraduate_e"] == ["cumcm"]

    overlay = contract("references/competition/c-problem.md")
    assert overlay["scope"] == "cumcm_undergraduate_c_only"
    assert set(overlay["explicit_exclusions"]) >= {
        "generic_math_modeling",
        "cumcm_undergraduate_a",
        "cumcm_undergraduate_b",
        "cumcm_undergraduate_d",
        "cumcm_undergraduate_e",
    }


def test_current_official_rules_override_history_and_unknowns_remain_pending() -> None:
    data = contract("references/competition/cumcm.md")
    assert data["authority_order"][0] == "current_official_problem_rules_templates"
    assert data["unknown_current_requirements"] == "pending_verification"
    assert data["historical_guidance"] == "non_binding"
    text = normalized(read("references/competition/cumcm.md"))
    for phrase in ("AI", "支撑材料", "章节", "模型", "创新", "图", "交付物"):
        assert normalized(phrase) in text


def test_c_problem_overlay_preserves_specialized_decision_logic() -> None:
    data = contract("references/competition/c-problem.md")
    assert data["selection_policy"] == "transparent_first"
    assert data["visible_innovations"] == {"minimum": 1, "maximum": 3}
    assert data["complexity_questions"] == [
        "what_simple_method_fails",
        "why_it_fails_for_this_data_or_mechanism",
        "what_verifiable_gain_the_added_complexity_provides",
    ]
    text = normalized(read("references/competition/c-problem.md"))
    for phrase in (
        "任务分解",
        "依赖",
        "数据驱动",
        "72",
        "验证成熟度",
        "决策误差传播",
        "2024",
        "数据缺口",
        "source-index",
    ):
        assert normalized(phrase) in text


def test_model_selection_separates_model_solver_and_validation() -> None:
    data = contract("references/modeling/model-selection.md")
    assert data["layers"] == ["model", "solver", "validation"]
    assert data["selection_starts_from"] == [
        "requested_output",
        "variables",
        "objective",
        "constraints",
        "data_mechanism",
    ]
    assert data["exact_methods_before_metaheuristics"] is True
    assert data["independent_model_system_limit"] == 2
    assert data["same_mechanism_variants_are_one_family"] is True
    assert data["advanced_method_requires_complexity_justification"] is True
    assert set(data["decision_families"]) == {
        "optimization",
        "evaluation",
        "prediction",
        "classification",
        "clustering",
        "mechanism",
        "attribution",
        "uncertainty",
    }


def test_algorithm_library_is_routed_and_algorithm_specific() -> None:
    data = contract("references/modeling/algorithm-library.md")
    required = {
        "optimization",
        "prediction",
        "evaluation",
        "graph_network",
        "statistics_data",
        "integrated",
        "machine_learning",
    }
    assert required <= set(data["collections"])
    assert data["entry_fields"] == [
        "applicability",
        "structure_or_formula",
        "algorithm_specific_steps",
        "constraint_handling",
        "parameters",
        "validation",
        "risks",
        "scenarios",
        "comparisons",
    ]
    assert data["universal_fake_template_forbidden"] is True
    for target in data["collections"].values():
        assert (ROOT / "references/modeling" / target).is_file(), target


def test_partial_requests_do_not_expand_to_competition_or_full_library() -> None:
    data = contract("references/modeling/model-selection.md")
    assert data["loading"]["generic_without_selection_need"] == []
    assert data["loading"]["selection_needed"] == ["model_selection"]
    assert data["loading"]["algorithm_lookup_needed"] == [
        "model_selection",
        "relevant_algorithm_entries_only",
    ]
    assert data["loading"]["partial_fixed_model_code_request"] == []


def test_task6_skill_routes_are_materialized_while_later_tasks_remain_planned() -> None:
    text = read("SKILL.md")
    for path in (
        "references/competition/cumcm.md",
        "references/competition/c-problem.md",
        "references/modeling/model-selection.md",
        "references/modeling/algorithm-library.md",
    ):
        line = next(line for line in text.splitlines() if path in line)
        assert "计划中" not in line and "Task" not in line


def test_all_workspace_markdown_sources_have_operational_read_when_routes() -> None:
    expected = {
        "references/modeling/workspace/数学建模算法库_整合版.md": {
            "references/modeling/algorithm-library.md",
            "references/modeling/model-selection.md",
        },
        "references/writing/workspace/优秀论文特点与Skill补充建议.md": {
            "references/writing/paper-guidance.md",
            "references/quality/quality-gates.md",
        },
        "references/modeling/workspace/math-modeling-skill-详细总结.md": {
            "references/workflow/step-review.md",
        },
        "references/writing/workspace/CUMCM写作证据门禁补充.md": {
            "references/writing/evidence-gates.md",
            "references/roles/writer.md",
        },
        "references/competition/workspace/CUMCM-Step-Review-Skill总结.md": {
            "references/workflow/step-review.md",
        },
    }
    for destination, route_sources in expected.items():
        assert any(destination in linked_paths(source) for source in route_sources), destination


def test_c_problem_routes_every_retained_specialist_reference() -> None:
    required = {
        "references/competition/cumcm-c-problem/72h-workflow.md",
        "references/modeling/cumcm-c-problem/c-problem-evolution.md",
        "references/competition/cumcm-c-problem/competition-compliance.md",
        "references/modeling/cumcm-c-problem/modeling-toolbox.md",
        "references/quality/cumcm-c-problem/expert-review-guidance.md",
        "references/modeling/cumcm-c-problem/exemplar-patterns.md",
        "references/modeling/cumcm-c-problem/source-index.md",
        "references/writing/cumcm-c-problem/paper-structure.md",
        "references/writing/cumcm-c-problem/latex-template-guide.md",
        "references/visualization/cumcm-c-problem/visualization-playbook.md",
        "references/quality/cumcm-c-problem/quality-gates.md",
    }
    assert required <= linked_paths("references/competition/c-problem.md")


def test_general_modules_route_retained_writing_visualization_and_role_details() -> None:
    assert "references/writing/cumcm-step-review/优秀论文写法指南.md" in linked_paths(
        "references/writing/paper-guidance.md"
    )
    assert "references/visualization/cumcm-step-review/绘图参考/chart_selection.md" in linked_paths(
        "references/visualization/visualization.md"
    )
    assert "references/roles/cumcm-step-review/roles/建模手/工作流程.md" in linked_paths(
        "references/roles/modeler.md"
    )
    assert "references/roles/cumcm-step-review/roles/编程手/工作流程.md" in linked_paths(
        "references/roles/programmer.md"
    )
    assert "references/writing/cumcm-step-review/roles/论文手/工作流程.md" in linked_paths(
        "references/roles/writer.md"
    )


def test_operational_routed_markdown_has_no_stale_legacy_runtime_paths() -> None:
    operational = reachable_operational_markdown()
    stale_patterns = (
        r"[A-Za-z]:\\Users\\[^\n`]+\\\.codex\\skills",
        r"~[/\\]\.codex[/\\]skills",
        r"<SKILL_ROOT>[/\\]references[/\\]Subagent调度\.md",
        r"<SKILL_ROOT>[/\\]tools[/\\]paper_search",
        r"references[/\\]绘图参考[/\\]",
    )
    for relative in operational:
        for line_number, line in enumerate(read(relative).splitlines(), start=1):
            source_history = (
                "/workspace/" in f"/{relative}"
                and any(label in line for label in ("来源：", "原 Skill 路径："))
            )
            if source_history:
                continue
            assert not any(
                re.search(pattern, line, re.IGNORECASE) for pattern in stale_patterns
            ), (relative, line_number)
    assert link_checker.check_reachable_runtime_paths(ROOT) == []


def test_transitive_skill_route_reaches_all_declared_operational_sources() -> None:
    reached = reachable_operational_markdown()
    required = {
        "references/competition/cumcm.md",
        "references/competition/c-problem.md",
        "references/modeling/workspace/数学建模算法库_整合版.md",
        "references/writing/workspace/优秀论文特点与Skill补充建议.md",
        "references/modeling/workspace/math-modeling-skill-详细总结.md",
        "references/writing/workspace/CUMCM写作证据门禁补充.md",
        "references/competition/workspace/CUMCM-Step-Review-Skill总结.md",
        "references/competition/cumcm-c-problem/72h-workflow.md",
        "references/modeling/cumcm-c-problem/c-problem-evolution.md",
        "references/competition/cumcm-c-problem/competition-compliance.md",
        "references/modeling/cumcm-c-problem/modeling-toolbox.md",
        "references/quality/cumcm-c-problem/expert-review-guidance.md",
        "references/modeling/cumcm-c-problem/exemplar-patterns.md",
        "references/modeling/cumcm-c-problem/source-index.md",
        "references/writing/cumcm-c-problem/paper-structure.md",
        "references/writing/cumcm-c-problem/latex-template-guide.md",
        "references/visualization/cumcm-c-problem/visualization-playbook.md",
        "references/quality/cumcm-c-problem/quality-gates.md",
    }
    assert required <= reached
