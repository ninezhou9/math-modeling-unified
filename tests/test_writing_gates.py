from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), f"missing Task 7 module: {relative}"
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


def test_evidence_gates_require_strict_claim_traceability_and_reject_unsupported_words() -> None:
    data = contract("references/writing/evidence-gates.md")
    assert data["forbidden_unsupported_words"] == [
        "显著",
        "最优",
        "稳健",
        "大幅提高",
        "高度吻合",
        "完美",
    ]
    assert data["traceability_chain"] == [
        "code",
        "raw_output",
        "figure_or_table",
        "paper_claim",
    ]
    assert data["model_switch_condition"] == "actual_failure_evidence_required"
    text = normalized(read("references/writing/evidence-gates.md"))
    for phrase in ("事实包", "公式叙述闭环", "结果分析五要素", "误差定位", "强判断词", "退回条件"):
        assert normalized(phrase) in text


def test_paper_guidance_integrates_structure_and_excellent_patterns() -> None:
    data = contract("references/writing/paper-guidance.md")
    assert data["chapter_sequence"] == [
        "abstract",
        "problem_restatement",
        "problem_analysis",
        "assumptions",
        "symbols",
        "modeling_and_solution",
        "analysis_and_verification",
        "evaluation_and_extension",
        "references",
        "appendix",
    ]
    assert data["evidence_density"] == "high"
    text = normalized(read("references/writing/paper-guidance.md"))
    for phrase in ("段落功能", "图表环绕", "客观主语", "逻辑连接", "微结构"):
        assert normalized(phrase) in text


def test_abstract_guidance_distinguishes_from_conclusion_and_has_two_phase_loop() -> None:
    data = contract("references/writing/abstract.md")
    assert data["phases"] == ["drafting", "secondary_verification", "finalization"]
    assert data["abstract_vs_conclusion"]["abstract_focus"] == "high_density_and_core_metrics"
    assert data["abstract_vs_conclusion"]["conclusion_focus"] == "direct_answers_and_boundaries"
    assert data["required_elements"] == [
        "background_and_objective",
        "model_and_methods",
        "key_quantitative_results",
        "innovation_and_value",
    ]
    text = normalized(read("references/writing/abstract.md"))
    for phrase in ("起草", "二次验证", "定稿", "数值绑定", "字数控制"):
        assert normalized(phrase) in text


def test_visualization_guidance_enforces_clean_figures_and_journal_palettes() -> None:
    data = contract("references/visualization/visualization.md")
    assert data["in_figure_title_forbidden"] is True
    assert data["caption_position"] == "bottom"
    assert data["same_chart_type_max_per_paper"] == 3
    assert data["consecutive_same_chart_type_max"] == 2
    assert "nature" in data["journal_palettes"]
    assert "okabe-ito" in data["journal_palettes"]
    text = normalized(read("references/visualization/visualization.md"))
    for phrase in ("无图内标题", "图题在下", "字号比例", "期刊配色", "draw.io", "图表面板"):
        assert normalized(phrase) in text


def test_quality_gates_define_stage_and_final_acceptance() -> None:
    data = contract("references/quality/quality-gates.md")
    assert data["author_self_check"] is True
    assert data["user_review_hard_gate"] is True
    assert data["final_acceptance_checks"] == [
        "reproduction_manifest",
        "paper_check_script",
        "visual_pdf_check",
        "formula_native_check",
    ]
    text = normalized(read("references/quality/quality-gates.md"))
    for phrase in ("阶段自检", "用户审核", "终稿核验", "硬错误阻断", "复现清单"):
        assert normalized(phrase) in text


def test_task7_skill_routes_are_materialized_while_task8_remains_planned() -> None:
    text = read("SKILL.md")
    for path in (
        "references/writing/paper-guidance.md",
        "references/writing/evidence-gates.md",
        "references/writing/abstract.md",
        "references/visualization/visualization.md",
        "references/quality/quality-gates.md",
    ):
        line = next(line for line in text.splitlines() if path in line)
        assert "计划中" not in line and "Task" not in line
