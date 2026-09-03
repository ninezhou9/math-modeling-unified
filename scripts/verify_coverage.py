#!/usr/bin/env python3
"""Build and verify the source-to-unified coverage plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "references" / "provenance" / "source-inventory.json"
MATRIX_PATH = ROOT / "references" / "provenance" / "coverage-matrix.json"
MARKDOWN_PATH = ROOT / "references" / "provenance" / "coverage-matrix.md"
ALLOWED_ACTIONS = {"merge", "preserve", "deduplicate", "rename", "enhance"}
MAPPING_FIELDS = {
    "source",
    "relative_path",
    "kind",
    "destination",
    "action",
    "integrity_note",
    "verification",
}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "status",
    "inventory_sha256",
    "inventory_file_count",
    "allowed_actions",
    "managed_destinations",
    "summary",
    "mappings",
}
SUMMARY_FIELDS = {"mapping_count", "source_count", "destination_count", "action_counts"}
VERIFICATION_FIELDS = {"source_sha256", "method", "sources", "receipt", "audit"}
VERIFICATION_SOURCE_FIELDS = {"source", "relative_path", "sha256"}
RECEIPT_FIELDS = {
    "schema_version",
    "kind",
    "destination",
    "output_sha256",
    "sources",
    "bindings",
}
RECEIPT_BINDING_FIELDS = {
    "source",
    "relative_path",
    "action",
    "destination",
    "rule_id",
    "evidence_type",
    "test_ids",
}
AUDIT_FIELDS = {"schema_version", "status", "source", "chunks"}
AUDIT_SOURCE_FIELDS = {"source", "relative_path", "sha256", "chunking"}
AUDIT_CHUNK_FIELDS = {
    "id",
    "sha256",
    "heading",
    "disposition",
    "destinations",
    "rationale",
}
AUDIT_DESTINATION_FIELDS = {"path", "anchor", "evidence_terms"}
AUDIT_CHUNKING = "utf8-frontmatter-and-heading-blocks-v1"
MANAGED_DESTINATIONS = [
    "SKILL.md",
    "agents",
    "assets",
    "references",
    "scripts",
    "tests",
    "tools",
]
DIRECT_INTEGRITY_ACTIONS = {"preserve", "rename", "deduplicate"}
RECEIPT_ACTIONS = {"merge", "enhance"}
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
    *(f"COM{number}" for number in "¹²³"),
    *(f"LPT{number}" for number in "¹²³"),
}
CONTROL_FILES = {
    "SKILL.md",
    "VALIDATION.md",
    "references/competition/c-problem.md",
    "references/competition/cumcm.md",
    "references/modeling/algorithm-library.md",
    "references/modeling/evaluation.md",
    "references/modeling/graph-network.md",
    "references/modeling/integrated.md",
    "references/modeling/machine-learning.md",
    "references/modeling/model-selection.md",
    "references/modeling/optimization.md",
    "references/modeling/prediction.md",
    "references/modeling/statistics-data.md",
    "references/provenance/source-inventory.json",
    "references/provenance/coverage-matrix.json",
    "references/provenance/coverage-matrix.md",
    "references/quality/quality-gates.md",
    "references/visualization/visualization.md",
    "references/writing/abstract.md",
    "references/writing/evidence-gates.md",
    "references/writing/paper-guidance.md",
    "scripts/build_source_inventory.py",
    "scripts/check_internal_links.py",
    "scripts/verify_coverage.py",
    "tests/behavior/baseline-results.md",
    "tests/behavior/scenarios.md",
    "tests/behavior/skill-results.md",
    "tests/source-state-before.json",
    "tests/test_behavior_results.py",
    "tests/test_coverage.py",
    "tests/test_inventory.py",
    "tests/test_routing_content.py",
    "tests/test_source_immutability.py",
    "tests/test_structure.py",
    "tests/test_tools_smoke.py",
    "tests/test_writing_gates.py",
    "references/roles/论文手/references/论文模板.docx",
    "tools/docx/SKILL.md",
    "tools/docx/scripts/check_env.py",
    "tools/docx/scripts/comment.py",
    "tools/docx/scripts/equations.py",
    "tools/docx/scripts/office/helpers/merge_runs.py",
    "tools/docx/scripts/office/helpers/simplify_redlines.py",
    "tools/docx/scripts/office/pack.py",
    "tools/docx/scripts/office/unpack.py",
    "tools/docx/scripts/office/validators/base.py",
    "tools/docx/scripts/office/validators/docx.py",
    "tools/docx/scripts/paper_format.py",
    "tools/pdf/SKILL.md",
    "tools/pdf/scripts/convert_pdf_to_images.py",
    "tools/xlsx/scripts/recalc.py",
}

# Task 5 deliberately consolidates these inventoried instruction/reference files
# into a small internal workflow and role surface. Hash keys avoid depending on
# locale-damaged legacy path spellings while remaining bound to the inventory.
TASK5_DESTINATION_BY_SHA256 = {
    "5454df3b295d5dfca8c32851b90049db333eade0571c5fd990c1eaf73a62f99f": "references/roles/modeler.md",
    "ecd6feb44aa110ff762c3d64ba4db4bca13d0e6052b421494fcd2fb1d40e5f18": "references/roles/programmer.md",
    "c39d7a2e2f6574958ef157fcdfb10853f915a86e4d825846bd684ecbe2f94f5c": "references/roles/writer.md",
    "69deb17338dfdc680646cb7deb17500c184d8291a0f8b20114e6226fefa1f8e3": "references/workflow/deliverables.md",
    "ae3d50356bec299aaa66fe4785a75116c440c57775dd4269173d50f76f4c9242": "references/workflow/step-review.md",
}
ROOT_SKILL_AUDIT_DESTINATIONS = {
    source: f"references/provenance/root-audits/{source}-skill.json"
    for source in ("cumcm-c-problem", "cumcm-step-review", "math-modeling")
}
ROOT_AUDIT_ROUTES = {
    "cumcm-c-problem": {
        "frontmatter": ("SKILL.md", "数学建模统一工作流", "CUMCM 本科组 C 题"),
        "preamble": ("SKILL.md", "数学建模统一工作流", "唯一直接入口"),
        "section-001": ("references/competition/c-problem.md", "CUMCM 本科组 C 题专用规则", "transparent_first"),
        "section-002": ("references/competition/c-problem.md", "C 题定位与演化", "真实业务场景"),
        "section-003": ("references/competition/cumcm.md", "赛题分析与建模", "完整阅读赛题"),
        "section-004": ("references/modeling/model-selection.md", "选型三层分离", "验证层（validation）"),
        "section-005": ("references/modeling/algorithm-library.md", "使用规则", "universal_fake_template_forbidden"),
        "section-006": ("references/competition/c-problem.md", "模型选型与创新", "visible_innovations"),
        "section-007": ("references/writing/paper-guidance.md", "优秀论文的微结构模式（Micro-structure）", "段落功能驱动"),
        "section-008": ("references/writing/cumcm-c-problem/paper-structure.md", "C 题论文结构与章节写法", "摘要"),
        "section-009": ("references/writing/abstract.md", "摘要四要素结构", "key_quantitative_results"),
        "section-010": ("references/writing/paper-guidance.md", "标准章节序列与逻辑脉络", "问题重述"),
        "section-011": ("references/visualization/visualization.md", "硬性图表规范", "caption_position"),
        "section-012": ("references/writing/cumcm-c-problem/latex-template-guide.md", "用户模板与 LaTeX 排版规范", "cumcmthesis"),
        "section-013": ("references/quality/quality-gates.md", "质量门禁三层防护体系", "author_self_check"),
        "section-014": ("references/quality/cumcm-c-problem/expert-review-guidance.md", "1. 证据层级", "当前年度 CUMCM 官方文件"),
        "section-015": ("references/competition/cumcm-c-problem/72h-workflow.md", "国赛 C 题 72 小时工作流", "0–3h"),
        "section-016": ("references/modeling/cumcm-c-problem/source-index.md", "官方资料索引（2018–2025 C题）", "重要版权说明"),
        "section-017": ("references/workflow/step-review.md", "共享规则优先级与完成纪律", "用户审核是独立硬门禁"),
    },
    "cumcm-step-review": {
        "frontmatter": ("SKILL.md", "数学建模统一工作流", "逐步审核与冻结工作流"),
        "preamble": ("SKILL.md", "数学建模统一工作流", "唯一直接入口"),
        "section-001": ("SKILL.md", "数学建模统一工作流", "三角色按"),
        "section-002": ("SKILL.md", "根目录与单一入口", "PROJECT_ROOT"),
        "section-003": ("references/workflow/deliverables.md", "根目录合同", "SKILL_ROOT"),
        "section-004": ("references/workflow/step-review.md", "路由合同", "user_approves_candidate"),
        "section-005": ("references/roles/writer.md", "分步 Word 审核", "论文草稿.docx"),
        "section-006": ("references/workflow/step-review.md", "分类型门禁", "局部任务"),
        "section-007": ("SKILL.md", "渐进式加载", "禁止一次性加载全部资料"),
        "section-008": ("references/workflow/step-review.md", "CUMCM 写作与审核顺序", "问题重述"),
        "section-009": ("references/quality/quality-gates.md", "质量门禁三层防护体系", "user_review_hard_gate"),
        "section-010": ("references/modeling/model-selection.md", "选型起点", "约束"),
        "section-011": ("references/visualization/visualization.md", "硬性图表规范", "in_figure_title_forbidden"),
        "section-012": ("references/workflow/step-review.md", "完成纪律", "计算结论必须来自真实运行"),
        "section-013": ("references/quality/quality-gates.md", "质量门禁与验收规范", "final_acceptance_checks"),
    },
    "math-modeling": {
        "frontmatter": ("SKILL.md", "数学建模统一工作流", "逐步审核与冻结工作流"),
        "preamble": ("SKILL.md", "数学建模统一工作流", "唯一直接入口"),
        "section-001": ("SKILL.md", "数学建模统一工作流", "三角色按"),
        "section-002": ("references/workflow/deliverables.md", "根目录合同", "PROJECT_ROOT"),
        "section-003": ("SKILL.md", "渐进式加载", "禁止一次性加载全部资料"),
        "section-004": ("references/workflow/step-review.md", "分类型门禁", "用户批准"),
        "section-005": ("references/roles/modeler.md", "建模手合同", "题目分析报告.md"),
        "section-006": ("references/roles/programmer.md", "实现与真实运行", "退出码"),
        "section-007": ("references/roles/writer.md", "写作前置", "主张—证据映射"),
        "section-008": ("references/workflow/step-review.md", "三角色回退", "不重复已冻结"),
        "section-009": ("references/modeling/model-selection.md", "选型三层分离", "验证层"),
        "section-010": ("references/workflow/step-review.md", "完成纪律", "计算结论必须来自真实运行"),
        "section-011": ("references/quality/quality-gates.md", "质量门禁与验收规范", "final_acceptance_checks"),
    },
}
MIGRATION_ADAPTATIONS = {
    "references/roles/cumcm-step-review/roles/建模手/工作流程.md": "reference",
    "references/roles/cumcm-step-review/roles/编程手/工作流程.md": "reference",
    "references/roles/cumcm-step-review/roles/编程手/可视化规范.md": "reference",
    "references/visualization/cumcm-step-review/绘图参考/drawio_flowchart.md": "reference",
    "references/writing/cumcm-step-review/roles/论文手/工作流程.md": "reference",
    "references/writing/cumcm-step-review/优秀论文写法指南.md": "reference",
    "tests/migrated/math-modeling/test_docx_tools.py": "test",
    "tests/migrated/math-modeling/test_equations.py": "test",
    "tests/migrated/math-modeling/test_paper_format.py": "test",
    "tests/migrated/math-modeling/test_paper_search.py": "test",
    "tests/migrated/math-modeling/test_recalc.py": "test",
    "tests/migrated/math-modeling/test_reproducibility.py": "test",
    "tests/migrated/math-modeling/test_xlsx_read.py": "test",
    "tools/docx/source-variants/cumcm-step-review/scripts/comment.py": "tool",
    "tools/docx/source-variants/math-modeling/scripts/comment.py": "tool",
    "tools/xlsx/source-variants/cumcm-step-review/scripts/recalc.py": "tool",
    "tools/xlsx/source-variants/math-modeling/scripts/recalc.py": "tool",
    "scripts/cumcm-step-review/check_env.py": "tool",
}
MIGRATION_ADAPTATION_BINDINGS = {
    "references/roles/cumcm-step-review/roles/建模手/工作流程.md": ("cumcm-step-review", "references/roles/建模手/工作流程.md"),
    "references/roles/cumcm-step-review/roles/编程手/工作流程.md": ("cumcm-step-review", "references/roles/编程手/工作流程.md"),
    "references/roles/cumcm-step-review/roles/编程手/可视化规范.md": ("cumcm-step-review", "references/roles/编程手/可视化规范.md"),
    "references/visualization/cumcm-step-review/绘图参考/drawio_flowchart.md": ("cumcm-step-review", "references/绘图参考/drawio_flowchart.md"),
    "references/writing/cumcm-step-review/roles/论文手/工作流程.md": ("cumcm-step-review", "references/roles/论文手/工作流程.md"),
    "references/writing/cumcm-step-review/优秀论文写法指南.md": ("cumcm-step-review", "references/优秀论文写法指南.md"),
    **{
        f"tests/migrated/math-modeling/{name}": ("math-modeling", f"tests/{name}")
        for name in (
            "test_docx_tools.py",
            "test_equations.py",
            "test_paper_format.py",
            "test_paper_search.py",
            "test_recalc.py",
            "test_reproducibility.py",
            "test_xlsx_read.py",
        )
    },
    "tools/docx/source-variants/cumcm-step-review/scripts/comment.py": ("cumcm-step-review", "tools/docx/scripts/comment.py"),
    "tools/docx/source-variants/math-modeling/scripts/comment.py": ("math-modeling", "tools/docx/scripts/comment.py"),
    "tools/xlsx/source-variants/cumcm-step-review/scripts/recalc.py": ("cumcm-step-review", "tools/xlsx/scripts/recalc.py"),
    "tools/xlsx/source-variants/math-modeling/scripts/recalc.py": ("math-modeling", "tools/xlsx/scripts/recalc.py"),
    "scripts/cumcm-step-review/check_env.py": ("cumcm-step-review", "scripts/check_env.py"),
}
CONTROLLED_ADAPTATION_OVERRIDES: dict[tuple[str, str, str, str], dict[str, Any]] = {}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def split_markdown_chunks(text: str) -> list[dict[str, str]]:
    """Split UTF-8 Markdown into exact, non-overlapping semantic blocks."""
    lines = text.splitlines(keepends=True)
    raw_chunks: list[tuple[str, str]] = []
    cursor = 0
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                raw_chunks.append(("frontmatter", "".join(lines[: index + 1])))
                cursor = index + 1
                break

    start = cursor
    heading = "preamble"
    in_fence = False
    section_number = 0
    for index in range(cursor, len(lines)):
        line = lines[index]
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
        match = None if in_fence else re.match(r"^(#{1,6})\s+(.+?)\s*$", line.rstrip("\r\n"))
        if match:
            if index > start:
                raw_chunks.append((heading, "".join(lines[start:index])))
            section_number += 1
            heading = match.group(2).strip().rstrip("#").strip()
            start = index
    if start < len(lines):
        raw_chunks.append((heading, "".join(lines[start:])))
    if not raw_chunks and text:
        raw_chunks.append(("preamble", text))

    chunks: list[dict[str, str]] = []
    section_number = 0
    for heading_text, content in raw_chunks:
        if heading_text == "frontmatter":
            chunk_id = "frontmatter"
        elif heading_text == "preamble":
            chunk_id = "preamble"
        else:
            section_number += 1
            chunk_id = f"section-{section_number:03d}"
        chunks.append(
            {
                "id": chunk_id,
                "heading": heading_text,
                "sha256": sha256_bytes(content.encode("utf-8")),
            }
        )
    return chunks


def _authoritative_route(source_name: str, chunk_id: str) -> list[dict[str, Any]] | None:
    route = ROOT_AUDIT_ROUTES.get(source_name, {}).get(chunk_id)
    if route is None:
        return None
    destination, anchor, evidence = route
    return [{"path": destination, "anchor": anchor, "evidence_terms": [evidence]}]


def _generic_evidence(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    compact = re.sub(r"[^0-9A-Za-z\u3400-\u9fff]+", "", value).casefold()
    return len(compact) < 2 or compact in {
        "a",
        "the",
        "data",
        "模型",
        "数据",
        "图表",
        "证据",
        "完成",
    }


def markdown_heading_sections(text: str) -> dict[str, list[str]]:
    """Return exact Markdown heading titles and their same/higher-level-bounded sections."""
    lines = text.splitlines(keepends=True)
    headings: list[tuple[int, int, str]] = []
    in_fence = False
    for index, line in enumerate(lines):
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line.rstrip("\r\n"))
        if match:
            headings.append(
                (index, len(match.group(1)), match.group(2).strip().rstrip("#").strip())
            )
    sections: dict[str, list[str]] = defaultdict(list)
    for position, (start, level, title) in enumerate(headings):
        end = len(lines)
        for candidate_start, candidate_level, _ in headings[position + 1 :]:
            if candidate_level <= level:
                end = candidate_start
                break
        sections[title].append("".join(lines[start:end]))
    return dict(sections)


def key_text(key: tuple[Any, Any]) -> str:
    def component(value: Any) -> str:
        return value if isinstance(value, str) else repr(value)

    return f"{component(key[0])}:{component(key[1])}"


def key_sort(key: tuple[Any, Any]) -> tuple[str, str]:
    return (repr(key[0]), repr(key[1]))


def source_record(item: dict[str, Any], sha256: str | None = None) -> dict[str, str]:
    return {
        "source": item["source"],
        "relative_path": item["relative_path"],
        "sha256": sha256 if sha256 is not None else item["sha256"],
    }


def matrix_summary(mappings: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [item for item in mappings if isinstance(item, dict)]
    action_counts = Counter(item.get("action") for item in valid if isinstance(item.get("action"), str))
    return {
        "mapping_count": len(mappings),
        "source_count": len({item.get("source") for item in valid if isinstance(item.get("source"), str)}),
        "destination_count": len(
            {item.get("destination") for item in valid if isinstance(item.get("destination"), str)}
        ),
        "action_counts": dict(sorted(action_counts.items())),
    }


def normalized_relative_posix(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        return False
    path = PurePosixPath(value)
    if not path.parts or str(path) != value:
        return False
    for part in path.parts:
        if part in {"", ".", ".."} or part.endswith((".", " ")):
            return False
        if any(ord(character) < 32 or character in '<>:"|?*' for character in part):
            return False
        if part.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
            return False
    return True


def _category(relative_path: str) -> str:
    text = relative_path.casefold()
    categories = (
        ("visualization", ("figure", "visual", "plot", "绘图", "图表")),
        ("writing", ("paper", "abstract", "latex", "写作", "论文", "摘要")),
        ("competition", ("competition", "72h", "cumcm", "竞赛", "赛题")),
        ("quality", ("quality", "review", "audit", "gate", "检验", "评价")),
        ("roles", ("roles/", "建模手", "编程手", "论文手")),
        ("workflow", ("workflow", "step", "流程")),
    )
    for category, needles in categories:
        if any(needle in text for needle in needles):
            return category
    return "modeling"


def _safe_name(path: str) -> str:
    return path.replace("README.md", "source-readme.md").replace("SKILL.md", "source-skill.md")


def planned_destination(item: dict[str, Any]) -> str:
    task5_destination = TASK5_DESTINATION_BY_SHA256.get(item.get("sha256"))
    if task5_destination is not None:
        return task5_destination
    source = item["source"]
    relative = item["relative_path"]
    lower = relative.casefold()
    pdf_source_retention = {
        "tools/pdf/skill.md": "tools/pdf/source-variants/shared/SKILL.md",
        "tools/pdf/scripts/convert_pdf_to_images.py": (
            "tools/pdf/source-variants/shared/scripts/convert_pdf_to_images.py"
        ),
    }
    if lower in pdf_source_retention:
        return pdf_source_retention[lower]
    if lower == "skill.md" and source in ROOT_SKILL_AUDIT_DESTINATIONS:
        return ROOT_SKILL_AUDIT_DESTINATIONS[source]
    if lower == "skill.md":
        return "SKILL.md"
    if lower == "agents/openai.yaml":
        return "agents/openai.yaml"
    if source == "workspace-markdown":
        return f"references/{_category(relative)}/workspace/{relative}"
    if lower.startswith("tools/"):
        tool_path = relative[6:]
        if tool_path.casefold() == "readme.md":
            return f"references/provenance/legacy/{source}/tools-readme.md"
        if "/" not in tool_path:
            return f"scripts/{source}/{tool_path}"
        tool, rest = tool_path.split("/", 1)
        tool = "paper-search" if tool.casefold() == "paper_search" else tool
        return f"tools/{tool}/{rest}"
    if lower.startswith("assets/"):
        return f"assets/{source}/{relative[7:]}"
    if lower.startswith("scripts/"):
        return f"scripts/{source}/{relative[8:]}"
    if lower.startswith("tests/"):
        return f"tests/migrated/{source}/{relative[6:]}"
    if lower.startswith("references/"):
        rest = relative[11:]
        return f"references/{_category(relative)}/{source}/{_safe_name(rest)}"
    if lower.startswith("examples/"):
        return f"references/{_category(relative)}/{source}/{relative[9:]}"
    return f"references/provenance/legacy/{source}/{_safe_name(relative)}"


def _duplicate_destination(members: list[dict[str, Any]]) -> str:
    canonical = min(
        members,
        key=lambda item: (item["relative_path"].casefold(), item["relative_path"], item["source"]),
    )
    destination = planned_destination(canonical)
    # Shared exact copies must not retain a source-specific namespace.
    destination = destination.replace(f"/{canonical['source']}/", "/shared/")
    return destination


def _logical_duplicate_key(item: dict[str, Any]) -> str:
    """Identify source copies of one role/path without collapsing package-local files."""
    return item["relative_path"].replace("paper_search/", "paper-search/").casefold()


def _receipt_path(destination: str) -> str:
    token = sha256_bytes(destination.encode("utf-8"))[:24]
    return f"references/provenance/receipts/{token}.json"


def controlled_adaptation_spec(
    item: dict[str, Any], destination: str, action: str
) -> dict[str, Any] | None:
    key = (item["source"], item["relative_path"], destination, action)
    if key in CONTROLLED_ADAPTATION_OVERRIDES:
        return CONTROLLED_ADAPTATION_OVERRIDES[key]
    if item["relative_path"].casefold() == "agents/openai.yaml" and action == "merge":
        return {
            "rule_id": "merge-openai-interface-v1",
            "evidence_type": "interface-schema-regression",
            "test_ids": [
                "tests/test_structure.py::test_openai_interface_is_exact_and_has_no_explicit_only_policy"
            ],
        }
    if item["source"] == "workspace-markdown" and action == "enhance":
        return {
            "rule_id": "route-retained-workspace-markdown-v1",
            "evidence_type": "operational-link-reachability-regression",
            "test_ids": [
                "tests/test_routing_content.py::test_all_workspace_markdown_sources_have_operational_read_when_routes"
            ],
        }
    if item.get("sha256") in TASK5_DESTINATION_BY_SHA256 and action == "enhance":
        return {
            "rule_id": "consolidate-role-workflow-contract-v1",
            "evidence_type": "contract-regression",
            "test_ids": [
                "tests/test_structure.py::test_role_loop_backtracks_without_repeating_frozen_work"
            ],
        }
    adaptation = MIGRATION_ADAPTATIONS.get(destination)
    expected_source = MIGRATION_ADAPTATION_BINDINGS.get(destination)
    if (
        adaptation is None
        or expected_source != (item.get("source"), item.get("relative_path"))
        or action != "enhance"
    ):
        return None
    if adaptation == "reference":
        test_ids = [
            "tests/test_routing_content.py::test_operational_routed_markdown_has_no_stale_legacy_runtime_paths"
        ]
        evidence_type = "link-and-runtime-path-regression"
    elif adaptation == "tool":
        test_ids = ["tests/test_tools_smoke.py::test_python_tools_help_exits_zero"]
        evidence_type = "tool-load-regression"
    else:
        test_ids = [
            "tests/test_coverage.py::test_checked_in_matrix_is_complete_deterministic_and_planning_valid"
        ]
        evidence_type = "relocated-test-regression"
    return {
        "rule_id": f"controlled-{adaptation}-adaptation-v1",
        "evidence_type": evidence_type,
        "test_ids": test_ids,
    }


def adaptation_binding(
    item: dict[str, Any], destination: str, action: str
) -> dict[str, Any] | None:
    spec = controlled_adaptation_spec(item, destination, action)
    if spec is None:
        return None
    return {
        "source": item["source"],
        "relative_path": item["relative_path"],
        "action": action,
        "destination": destination,
        "rule_id": spec["rule_id"],
        "evidence_type": spec["evidence_type"],
        "test_ids": spec["test_ids"],
    }


def test_id_exists(unified_root: Path, test_id: Any) -> bool:
    if not isinstance(test_id, str) or "::" not in test_id:
        return False
    path_text, function_name = test_id.split("::", 1)
    if not normalized_relative_posix(path_text) or not function_name.startswith("test_"):
        return False
    path = unified_root / PurePosixPath(path_text)
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return re.search(rf"^\s*def\s+{re.escape(function_name)}\s*\(", text, re.MULTILINE) is not None


def build_seed_matrix(inventory: dict[str, Any], inventory_bytes: bytes) -> dict[str, Any]:
    duplicate_by_key: dict[tuple[str, str], tuple[str, str, list[dict[str, str]]]] = {}
    for group in inventory.get("exact_duplicate_groups", []):
        logical_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for member in group["members"]:
            logical_groups[_logical_duplicate_key(member)].append(member)
        for members in logical_groups.values():
            if len(members) < 2:
                continue
            destination = _duplicate_destination(members)
            records = [source_record(member, group["sha256"]) for member in members]
            for member in members:
                duplicate_by_key[(member["source"], member["relative_path"])] = (
                    group["sha256"],
                    destination,
                    records,
                )

    conflict_keys = {
        (member["source"], member["relative_path"])
        for group in inventory.get("same_relative_path_conflicts", [])
        for member in group["members"]
    }
    mappings: list[dict[str, Any]] = []
    for item in inventory["files"]:
        key = (item["source"], item["relative_path"])
        destination = planned_destination(item)
        action = "preserve"
        note = "Preserve this source contribution at its functional target without content loss."
        method = "Verify migrated content against the recorded source SHA-256 before acceptance."
        verification_sources = [source_record(item)]
        if key in duplicate_by_key:
            digest, destination, verification_sources = duplicate_by_key[key]
            action = "deduplicate"
            note = f"Deduplicate only this byte-identical cross-source group proven by SHA-256 {digest}."
            method = f"SHA-256 {digest} proves byte identity; verify the canonical destination once."
        elif (
            item["relative_path"].casefold() == "skill.md"
            and item["source"] in ROOT_SKILL_AUDIT_DESTINATIONS
        ):
            action = "enhance"
            note = (
                f"Certify the distributed integration at {destination} with a deterministic chunk audit "
                "covering every source block and its operational evidence."
            )
            method = (
                "Reproduce the source SHA-256 and every frontmatter/heading-block hash, then verify "
                "each declared unified destination, anchor, and evidence term."
            )
        elif item["relative_path"].casefold() == "agents/openai.yaml":
            action = "merge"
            note = f"Merge different-hash source conflict into {destination}; retain unique requirements and resolve contradictions."
            method = (
                "Compare the merged destination against this recorded source hash and audit a traceable "
                "section for every unique requirement."
            )
        elif item["sha256"] in TASK5_DESTINATION_BY_SHA256:
            action = "enhance"
            note = (
                f"Integrate this inventoried source into the Task 5 unified module {destination}; "
                "retain its applicable requirements and record deliberate changes."
            )
            method = (
                "Audit the unified Task 5 module against this recorded source hash and its "
                "behavior-focused structure tests."
            )
        elif key in conflict_keys:
            action = "rename"
            note = "Preserve this different-hash relative-path conflict under a source-qualified destination."
            method = "Verify the renamed destination against this source hash; do not treat it as a duplicate."
            if item["relative_path"].casefold().startswith("tools/"):
                tool, rest = item["relative_path"][6:].split("/", 1)
                tool = "paper-search" if tool.casefold() == "paper_search" else tool
                destination = f"tools/{tool}/source-variants/{item['source']}/{rest}"
        elif item["source"] == "workspace-markdown":
            action = "enhance"
            note = "Integrate this workspace analysis as an explicit enhancement while retaining its evidence."
            method = "Trace every adopted enhancement to this recorded source hash during editorial review."

        adaptation = MIGRATION_ADAPTATIONS.get(destination)
        if adaptation == "test":
            action = "enhance"
            note = "Adapt this migrated test to the unified directory layout while preserving its source behavior."
            method = (
                "Audit the path-only adaptation against the recorded source hash and execute the migrated test."
            )
        elif adaptation == "tool":
            action = "enhance"
            note = (
                "Adapt this source variant to resolve shared resources from the relocated canonical tool directory."
            )
            method = (
                "Audit the relocation adaptation against the recorded source hash and focused standalone-load regressions."
            )
        elif adaptation == "reference":
            action = "enhance"
            note = "Adapt relocated internal links to their explicit unified destinations."
            method = (
                "Audit link-only adaptations against the recorded source hash and the strict internal-link checker."
            )

        mappings.append(
            {
                "source": item["source"],
                "relative_path": item["relative_path"],
                "kind": item["kind"],
                "destination": destination,
                "action": action,
                "integrity_note": note,
                "verification": {
                    "source_sha256": item["sha256"],
                    "method": method,
                    "sources": verification_sources,
                    "receipt": (
                        None
                        if item["relative_path"].casefold() == "skill.md"
                        and item["source"] in ROOT_SKILL_AUDIT_DESTINATIONS
                        else _receipt_path(destination) if action in RECEIPT_ACTIONS else None
                    ),
                    "audit": (
                        destination
                        if item["relative_path"].casefold() == "skill.md"
                        and item["source"] in ROOT_SKILL_AUDIT_DESTINATIONS
                        else None
                    ),
                },
            }
        )

    by_destination: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in mappings:
        by_destination[entry["destination"]].append(entry)
    for destination, entries in by_destination.items():
        if len(entries) > 1 and all(entry["action"] == "merge" for entry in entries):
            item_index = {
                (item["source"], item["relative_path"]): item for item in inventory["files"]
            }
            records = [source_record(item_index[(entry["source"], entry["relative_path"])]) for entry in entries]
            for entry in entries:
                entry["verification"]["sources"] = records

    matrix = {
        "schema_version": 1,
        "status": "migration-planning",
        "inventory_sha256": sha256_bytes(inventory_bytes),
        "inventory_file_count": len(inventory["files"]),
        "allowed_actions": sorted(ALLOWED_ACTIONS),
        "managed_destinations": MANAGED_DESTINATIONS,
        "mappings": mappings,
    }
    matrix["summary"] = matrix_summary(mappings)
    # Keep stable top-level presentation order while validating by exact key set.
    matrix["mappings"] = matrix.pop("mappings")
    return matrix


def validate_root_audit(
    audit_path: Path,
    item: dict[str, Any],
    unified_root: Path,
    planning: bool,
    source_root_overrides: dict[str, Path | str] | None = None,
) -> list[str]:
    label = f"{item['source']}:{item['relative_path']}"
    source_path = Path(item["absolute_path"])
    if source_root_overrides and item["source"] in source_root_overrides:
        source_path = Path(source_root_overrides[item["source"]]) / PurePosixPath(
            item["relative_path"]
        )
    try:
        source_bytes = source_path.read_bytes()
    except OSError as exc:
        return [f"cannot read root audit source for {label}: {exc}"]
    if sha256_bytes(source_bytes) != item["sha256"]:
        return [f"root audit inventory/source hash mismatch for {label}"]
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"invalid root audit JSON for {label}: {exc}"]
    errors: list[str] = []
    if not isinstance(audit, dict) or set(audit) != AUDIT_FIELDS:
        return [f"invalid root audit schema for {label}"]
    if audit.get("schema_version") != 1 or isinstance(audit.get("schema_version"), bool):
        errors.append(f"unsupported root audit schema_version for {label}")
    status = audit.get("status")
    if status not in {"integrated", "pending"}:
        errors.append(f"invalid root audit status for {label}: {status!r}")
    if status == "pending" and not planning:
        errors.append(f"pending root audit status is forbidden in strict mode for {label}")
    source_meta = audit.get("source")
    expected_source = {
        "source": item["source"],
        "relative_path": item["relative_path"],
        "sha256": item["sha256"],
        "chunking": AUDIT_CHUNKING,
    }
    if not isinstance(source_meta, dict) or set(source_meta) != AUDIT_SOURCE_FIELDS:
        errors.append(f"invalid root audit source schema for {label}")
    elif source_meta != expected_source:
        if source_meta.get("sha256") != item["sha256"]:
            errors.append(f"root audit source hash mismatch for {label}")
        else:
            errors.append(f"root audit source identity mismatch for {label}")

    try:
        source_text = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        return errors + [f"root audit source is not UTF-8 for {label}: {exc}"]
    expected_chunks = {chunk["id"]: chunk for chunk in split_markdown_chunks(source_text)}
    chunks = audit.get("chunks")
    if not isinstance(chunks, list):
        return errors + [f"root audit chunks must be a list for {label}"]
    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict) or set(chunk) != AUDIT_CHUNK_FIELDS:
            errors.append(f"invalid root audit chunk schema for {label} at index {index}")
            continue
        chunk_id = chunk.get("id")
        if not isinstance(chunk_id, str):
            errors.append(f"invalid root audit chunk id for {label} at index {index}")
            continue
        by_id[chunk_id].append(chunk)
    duplicates = sorted(chunk_id for chunk_id, values in by_id.items() if len(values) > 1)
    if duplicates:
        errors.append(f"duplicate root audit chunk for {label}: {', '.join(duplicates)}")
    missing = sorted(set(expected_chunks) - set(by_id))
    extra = sorted(set(by_id) - set(expected_chunks))
    if missing:
        errors.append(f"missing root audit chunks for {label}: {', '.join(missing)}")
    if extra:
        errors.append(f"extra root audit chunks for {label}: {', '.join(extra)}")

    destination_cache: dict[str, str] = {}
    for chunk_id in sorted(set(expected_chunks) & set(by_id)):
        chunk = by_id[chunk_id][0]
        expected_chunk = expected_chunks[chunk_id]
        if chunk.get("sha256") != expected_chunk["sha256"]:
            errors.append(f"root audit chunk hash mismatch for {label}:{chunk_id}")
        if chunk.get("heading") != expected_chunk["heading"]:
            errors.append(f"root audit chunk heading mismatch for {label}:{chunk_id}")
        disposition = chunk.get("disposition")
        if disposition not in {"integrated", "retained", "pending"}:
            errors.append(f"invalid root audit disposition for {label}:{chunk_id}")
        if disposition == "pending" and not planning:
            errors.append(f"pending root audit chunk is forbidden in strict mode for {label}:{chunk_id}")
        if not isinstance(chunk.get("rationale"), str) or not chunk.get("rationale", "").strip():
            errors.append(f"empty root audit rationale for {label}:{chunk_id}")
        destinations = chunk.get("destinations")
        if not isinstance(destinations, list) or not destinations:
            errors.append(f"missing root audit destinations for {label}:{chunk_id}")
            continue
        authoritative = _authoritative_route(item["source"], chunk_id)
        if authoritative is None or destinations != authoritative:
            errors.append(f"root audit authoritative route mismatch for {label}:{chunk_id}")
        for routed in destinations:
            if not isinstance(routed, dict) or set(routed) != AUDIT_DESTINATION_FIELDS:
                errors.append(f"invalid root audit destination schema for {label}:{chunk_id}")
                continue
            path_text = routed.get("path")
            anchor = routed.get("anchor")
            evidence_terms = routed.get("evidence_terms")
            if _generic_evidence(anchor):
                errors.append(f"generic root audit anchor for {label}:{chunk_id}: {anchor!r}")
            if isinstance(evidence_terms, list):
                for term in evidence_terms:
                    if _generic_evidence(term):
                        errors.append(f"generic root audit evidence for {label}:{chunk_id}: {term!r}")
            if not normalized_relative_posix(path_text):
                errors.append(f"invalid root audit destination for {label}:{chunk_id}")
                continue
            path = unified_root / PurePosixPath(path_text)
            if not path.is_file():
                errors.append(f"missing root audit destination for {label}:{chunk_id}: {path_text}")
                continue
            if path_text not in destination_cache:
                try:
                    destination_cache[path_text] = path.read_text(encoding="utf-8")
                except (OSError, UnicodeError) as exc:
                    errors.append(f"unreadable root audit destination for {label}:{chunk_id}: {exc}")
                    continue
            routed_text = destination_cache[path_text]
            sections = markdown_heading_sections(routed_text)
            matching_sections = sections.get(anchor, []) if isinstance(anchor, str) else []
            if not matching_sections:
                errors.append(f"missing root audit anchor for {label}:{chunk_id}: {anchor!r}")
            elif len(matching_sections) > 1:
                errors.append(f"ambiguous root audit heading for {label}:{chunk_id}: {anchor!r}")
            if (
                not isinstance(evidence_terms, list)
                or not evidence_terms
                or any(not isinstance(term, str) or not term.strip() for term in evidence_terms)
            ):
                errors.append(f"invalid root audit evidence terms for {label}:{chunk_id}")
            elif len(matching_sections) == 1:
                section_text = matching_sections[0].casefold()
                for term in evidence_terms:
                    if term.casefold() not in section_text:
                        errors.append(
                            f"missing root audit section evidence for {label}:{chunk_id}: {term!r}"
                        )
    return errors


def validate_coverage(
    inventory: dict[str, Any],
    matrix: dict[str, Any],
    unified_root: Path,
    allow_missing_destinations: bool = False,
    inventory_bytes: bytes | None = None,
    source_root_overrides: dict[str, Path | str] | None = None,
    require_integrated_status: bool = True,
) -> list[str]:
    errors: list[str] = []
    source_items = {(item["source"], item["relative_path"]): item for item in inventory["files"]}
    if not isinstance(matrix, dict):
        return ["coverage matrix must be an object"]
    if set(matrix) != TOP_LEVEL_FIELDS:
        errors.append("matrix top-level fields differ from schema")
    if matrix.get("schema_version") != 1 or isinstance(matrix.get("schema_version"), bool):
        errors.append(f"unsupported schema_version: {matrix.get('schema_version', '<missing>')!r}")
    if matrix.get("status") not in {"migration-planning", "integrated"}:
        errors.append(f"unsupported matrix status: {matrix.get('status', '<missing>')!r}")
    elif (
        require_integrated_status
        and not allow_missing_destinations
        and matrix.get("status") != "integrated"
    ):
        errors.append("strict mode requires integrated matrix status")
    if matrix.get("allowed_actions") != sorted(ALLOWED_ACTIONS):
        errors.append("allowed_actions does not match verifier")
    if not isinstance(matrix.get("inventory_sha256"), str) or not re.fullmatch(
        r"[0-9a-f]{64}", matrix.get("inventory_sha256", "")
    ):
        errors.append("invalid inventory_sha256 fingerprint")
    if (
        not isinstance(matrix.get("inventory_file_count"), int)
        or isinstance(matrix.get("inventory_file_count"), bool)
        or matrix.get("inventory_file_count") != len(inventory["files"])
    ):
        errors.append(
            f"inventory_file_count mismatch: expected {len(inventory['files'])}, "
            f"got {matrix.get('inventory_file_count', '<missing>')}"
        )
    managed_destinations = matrix.get("managed_destinations")
    if (
        not isinstance(managed_destinations, list)
        or not managed_destinations
        or any(not isinstance(item, str) for item in managed_destinations)
    ):
        errors.append("managed_destinations must be a nonempty list of strings")
        managed_destinations = []
    mappings = matrix.get("mappings")
    if not isinstance(mappings, list):
        errors.append("matrix mappings must be a list")
        return errors

    summary = matrix.get("summary")
    if (
        not isinstance(summary, dict)
        or set(summary) != SUMMARY_FIELDS
        or summary != matrix_summary(mappings)
    ):
        errors.append("invalid matrix summary")

    if inventory_bytes is not None:
        expected = sha256_bytes(inventory_bytes)
        if matrix.get("inventory_sha256") != expected:
            errors.append(
                f"stale matrix inventory_sha256: expected {expected}, got {matrix.get('inventory_sha256', '<missing>')}"
            )

    by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for index, entry in enumerate(mappings):
        if not isinstance(entry, dict):
            errors.append(f"mapping {index} must be an object")
            continue
        if set(entry) != MAPPING_FIELDS:
            errors.append(f"mapping {index} fields differ from schema")
        key = (entry.get("source"), entry.get("relative_path"))
        label = key_text(key)
        for field in ("source", "relative_path", "kind", "destination", "action", "integrity_note"):
            if not isinstance(entry.get(field), str):
                errors.append(f"mapping {index} field {field} must be a string")
        valid_key = all(isinstance(component, str) for component in key)
        item = source_items.get(key) if valid_key else None
        if valid_key:
            by_key[key].append(entry)
        if entry.get("action") not in ALLOWED_ACTIONS:
            errors.append(f"invalid action for {label}: {entry.get('action')!r}")
        if not normalized_relative_posix(entry.get("destination")):
            errors.append(f"invalid destination for {label}: {entry.get('destination')!r}")
        if not isinstance(entry.get("integrity_note"), str) or not entry.get("integrity_note", "").strip():
            errors.append(f"empty integrity_note for {label}")
        verification = entry.get("verification")
        if not isinstance(verification, dict):
            errors.append(f"invalid verification for {label}")
        else:
            if set(verification) != VERIFICATION_FIELDS:
                errors.append(f"verification fields differ from schema for {label}")
            if not isinstance(verification.get("source_sha256"), str):
                errors.append(f"verification source_sha256 must be a string for {label}")
            if not isinstance(verification.get("method"), str) or not verification.get("method", "").strip():
                errors.append(f"empty verification method for {label}")
            verification_sources = verification.get("sources")
            if not isinstance(verification_sources, list) or not verification_sources:
                errors.append(f"invalid verification sources for {label}")
            else:
                seen_records: set[tuple[str, str, str]] = set()
                for record in verification_sources:
                    if not isinstance(record, dict):
                        errors.append(f"invalid verification source record for {label}")
                        continue
                    if set(record) != VERIFICATION_SOURCE_FIELDS:
                        errors.append(f"verification source fields differ from schema for {label}")
                    if not all(isinstance(record.get(field), str) for field in VERIFICATION_SOURCE_FIELDS):
                        errors.append(f"verification source fields must be strings for {label}")
                        continue
                    record_key = (record["source"], record["relative_path"])
                    expected_item = source_items.get(record_key)
                    if expected_item is None or record["sha256"] != expected_item["sha256"]:
                        errors.append(f"invalid verification source assumption for {label}: {key_text(record_key)}")
                    tuple_record = (record["source"], record["relative_path"], record["sha256"])
                    if tuple_record in seen_records:
                        errors.append(f"duplicate verification source for {label}: {key_text(record_key)}")
                    seen_records.add(tuple_record)
            receipt = verification.get("receipt")
            audit = verification.get("audit")
            is_root_audit = (
                isinstance(key[0], str)
                and key[0] in ROOT_SKILL_AUDIT_DESTINATIONS
                and isinstance(key[1], str)
                and key[1].casefold() == "skill.md"
            )
            if is_root_audit:
                if audit != entry.get("destination") or not normalized_relative_posix(audit):
                    errors.append(f"invalid root audit assignment for {label}")
                if receipt is not None:
                    errors.append(f"root audit must not use a byte-integrity receipt for {label}")
            elif audit is not None:
                errors.append(f"unexpected root audit for {label}")
            elif entry.get("action") in RECEIPT_ACTIONS:
                if item is not None and adaptation_binding(
                    item, entry.get("destination"), entry.get("action")
                ) is None:
                    errors.append(f"missing controller-owned adaptation rule for {label}")
                if not normalized_relative_posix(receipt):
                    errors.append(f"invalid byte-integrity receipt path for {label}: {receipt!r}")
            elif receipt is not None:
                errors.append(f"unexpected byte-integrity receipt for {label}")
            if item and verification.get("source_sha256") != item["sha256"]:
                errors.append(
                    f"source hash mismatch for {label}: expected {item['sha256']}, "
                    f"got {verification.get('source_sha256', '<missing>')}"
                )
        item = source_items.get(key) if valid_key else None
        if item and entry.get("kind") != item["kind"]:
            errors.append(f"kind mismatch for {label}: expected {item['kind']}, got {entry.get('kind')}")

    source_keys = set(source_items)
    mapped_keys = set(by_key)
    missing = sorted(source_keys - mapped_keys, key=key_sort)
    extra = sorted(mapped_keys - source_keys, key=key_sort)
    duplicates = sorted(
        (key for key, values in by_key.items() if len(values) > 1), key=key_sort
    )
    if missing:
        errors.append(f"missing mapping keys ({len(missing)}): {', '.join(map(key_text, missing))}")
    if extra:
        errors.append(f"extra mapping keys ({len(extra)}): {', '.join(map(key_text, extra))}")
    if duplicates:
        errors.append(f"duplicate mapping keys ({len(duplicates)}): {', '.join(map(key_text, duplicates))}")

    for group in inventory.get("exact_duplicate_groups", []):
        logical_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for member in group["members"]:
            logical_groups[_logical_duplicate_key(member)].append(member)
        logical_destinations: dict[str, set[Any]] = {}
        for logical_key, members in logical_groups.items():
            keys = [(item["source"], item["relative_path"]) for item in members]
            entries = [by_key[key][0] for key in keys if len(by_key.get(key, [])) == 1]
            logical_destinations[logical_key] = {entry.get("destination") for entry in entries}
            if len(members) < 2:
                continue
            expected_records = {
                tuple(source_record(member, group["sha256"]).values()) for member in members
            }
            structured = all(
                {
                    (record.get("source"), record.get("relative_path"), record.get("sha256"))
                    for record in entry.get("verification", {}).get("sources", [])
                    if isinstance(record, dict)
                }
                == expected_records
                for entry in entries
            )
            if (
                len(entries) != len(keys)
                or any(entry.get("action") != "deduplicate" for entry in entries)
                or len(logical_destinations[logical_key]) != 1
                or not structured
            ):
                errors.append(
                    f"duplicate group must share one canonical destination with action deduplicate "
                    f"and complete hash traceability: {group['sha256']}"
                )
        seen_logical_destinations: dict[Any, str] = {}
        for logical_key, destinations_for_role in logical_destinations.items():
            for destination in destinations_for_role:
                previous = seen_logical_destinations.get(destination)
                if previous is not None and previous != logical_key:
                    errors.append(
                        "exact-hash members with different logical paths must retain separate "
                        f"destinations: {destination}"
                    )
                seen_logical_destinations[destination] = logical_key

    by_destination: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for key, entries in by_key.items():
        if key in source_items and len(entries) == 1 and normalized_relative_posix(entries[0].get("destination")):
            by_destination[entries[0]["destination"]].append((entries[0], source_items[key]))
    casefold_destinations: dict[str, set[str]] = defaultdict(set)
    for destination in by_destination:
        casefold_destinations[destination.casefold()].add(destination)
    for spellings in casefold_destinations.values():
        if len(spellings) > 1:
            errors.append(
                "case-insensitive destination collision: " + ", ".join(sorted(spellings))
            )
    for destination, pairs in sorted(by_destination.items()):
        if len({item["sha256"] for _, item in pairs}) <= 1:
            continue
        expected_records = {
            (item["source"], item["relative_path"], item["sha256"])
            for _, item in pairs
        }
        valid_merge = all(
            entry.get("action") == "merge"
            and f"Merge different-hash source conflict into {destination};" in entry.get("integrity_note", "")
            and {
                (record.get("source"), record.get("relative_path"), record.get("sha256"))
                for record in entry.get("verification", {}).get("sources", [])
                if isinstance(record, dict)
            }
            == expected_records
            for entry, _ in pairs
        )
        if not valid_merge:
            labels = ", ".join(key_text((entry["source"], entry["relative_path"])) for entry, _ in pairs)
            errors.append(
                f"different source hashes share destination {destination} without structured merge traceability: {labels}"
            )

    destinations = sorted(by_destination)
    file_hashes: dict[Path, str] = {}

    def destination_hash(path: Path) -> str:
        if path not in file_hashes:
            file_hashes[path] = sha256_bytes(path.read_bytes())
        return file_hashes[path]

    if not allow_missing_destinations:
        missing_destinations = [
            path for path in destinations if not (unified_root / PurePosixPath(path)).is_file()
        ]
        if missing_destinations:
            errors.append(
                f"missing destination files ({len(missing_destinations)}): {', '.join(missing_destinations)}"
            )

        for destination, pairs in sorted(by_destination.items()):
            output_path = unified_root / PurePosixPath(destination)
            if not output_path.is_file():
                continue
            output_sha256 = destination_hash(output_path)
            actions = {entry.get("action") for entry, _ in pairs}
            if any(entry.get("verification", {}).get("audit") for entry, _ in pairs):
                continue
            if actions <= DIRECT_INTEGRITY_ACTIONS:
                expected_hashes = {item["sha256"] for _, item in pairs}
                if len(expected_hashes) != 1 or output_sha256 not in expected_hashes:
                    errors.append(
                        f"destination hash mismatch for {destination}: got {output_sha256}, "
                        f"expected {', '.join(sorted(expected_hashes))}"
                    )
                continue
            if not actions <= RECEIPT_ACTIONS:
                continue
            if output_path.stat().st_size == 0:
                errors.append(f"empty merged destination for {destination}")
            receipt_paths = {
                entry.get("verification", {}).get("receipt")
                for entry, _ in pairs
                if isinstance(entry.get("verification"), dict)
            }
            if len(receipt_paths) != 1 or not all(
                isinstance(path, str) and normalized_relative_posix(path)
                for path in receipt_paths
            ):
                errors.append(f"invalid byte-integrity receipt assignment for {destination}")
                continue
            receipt_relative = next(iter(receipt_paths))
            receipt_path = unified_root / PurePosixPath(receipt_relative)
            if not receipt_path.is_file():
                errors.append(f"missing byte-integrity receipt for {destination}: {receipt_relative}")
                continue
            try:
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"invalid byte-integrity receipt for {destination}: {exc}")
                continue
            if not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS:
                errors.append(f"invalid byte-integrity receipt schema for {destination}")
                if not isinstance(receipt, dict) or "bindings" not in receipt:
                    errors.append(f"missing controlled adaptation binding for {destination}")
                continue
            if receipt.get("schema_version") != 1 or receipt.get("kind") != (
                "byte-integrity-controlled-adaptation"
            ):
                errors.append(f"invalid byte-integrity receipt identity for {destination}")
            expected_records = {
                (item["source"], item["relative_path"], item["sha256"]) for _, item in pairs
            }
            receipt_sources = receipt.get("sources")
            actual_records: set[tuple[str, str, str]] = set()
            valid_receipt_sources = isinstance(receipt_sources, list)
            if valid_receipt_sources:
                for record in receipt_sources:
                    if (
                        not isinstance(record, dict)
                        or set(record) != VERIFICATION_SOURCE_FIELDS
                        or not all(
                            isinstance(record.get(field), str)
                            for field in VERIFICATION_SOURCE_FIELDS
                        )
                    ):
                        valid_receipt_sources = False
                        continue
                    record_tuple = (
                        record["source"],
                        record["relative_path"],
                        record["sha256"],
                    )
                    if record_tuple in actual_records:
                        valid_receipt_sources = False
                    actual_records.add(record_tuple)
            if not valid_receipt_sources:
                errors.append(f"invalid byte-integrity receipt sources for {destination}")
            elif receipt.get("destination") != destination or actual_records != expected_records:
                errors.append(f"byte-integrity receipt source set mismatch for {destination}")
            if receipt.get("output_sha256") != output_sha256:
                errors.append(
                    f"byte-integrity receipt output hash mismatch for {destination}: "
                    f"expected {output_sha256}, got {receipt.get('output_sha256', '<missing>')}"
                )
            expected_bindings = []
            for entry, item in pairs:
                binding = adaptation_binding(item, destination, entry.get("action"))
                if binding is not None:
                    expected_bindings.append(binding)
            expected_bindings.sort(
                key=lambda value: (value["source"], value["relative_path"], value["action"])
            )
            bindings = receipt.get("bindings")
            valid_bindings = isinstance(bindings, list) and all(
                isinstance(binding, dict)
                and set(binding) == RECEIPT_BINDING_FIELDS
                and isinstance(binding.get("test_ids"), list)
                and binding.get("test_ids")
                for binding in bindings or []
            )
            if not valid_bindings or bindings != expected_bindings:
                errors.append(f"controlled adaptation binding mismatch for {destination}")
            else:
                for binding in bindings:
                    for test_id in binding["test_ids"]:
                        if not test_id_exists(unified_root, test_id):
                            errors.append(
                                f"missing controlled adaptation regression test for {destination}: {test_id!r}"
                            )

    for key, entries in by_key.items():
        if (
            key[0] not in ROOT_SKILL_AUDIT_DESTINATIONS
            or not isinstance(key[1], str)
            or key[1].casefold() != "skill.md"
            or len(entries) != 1
            or key not in source_items
        ):
            continue
        audit_relative = entries[0].get("verification", {}).get("audit")
        if not isinstance(audit_relative, str) or not normalized_relative_posix(audit_relative):
            continue
        audit_path = unified_root / PurePosixPath(audit_relative)
        if not audit_path.is_file():
            if not allow_missing_destinations:
                errors.append(f"missing root audit for {key_text(key)}: {audit_relative}")
            continue
        errors.extend(
            validate_root_audit(
                audit_path,
                source_items[key],
                unified_root,
                planning=allow_missing_destinations and matrix.get("status") == "migration-planning",
                source_root_overrides=source_root_overrides,
            )
        )

    receipt_destinations = {
        entry.get("verification", {}).get("receipt")
        for entry in mappings
        if isinstance(entry, dict)
        and isinstance(entry.get("verification"), dict)
        and entry.get("action") in RECEIPT_ACTIONS
        and isinstance(entry["verification"].get("receipt"), str)
    }
    registered = set(destinations) | CONTROL_FILES | receipt_destinations
    discovered_files: set[str] = set()
    for root_text in managed_destinations:
        if not normalized_relative_posix(root_text):
            errors.append(f"invalid managed destination: {root_text!r}")
            continue
        managed_root = unified_root / PurePosixPath(root_text)
        if managed_root.is_file():
            discovered_files.add(managed_root.relative_to(unified_root).as_posix())
        if managed_root.is_dir():
            for path in managed_root.rglob("*"):
                if path.is_file():
                    relative = path.relative_to(unified_root).as_posix()
                    if "__pycache__" not in path.parts and path.suffix != ".pyc":
                        discovered_files.add(relative)
    unregistered = sorted(discovered_files - registered)
    if unregistered:
        errors.append(
            f"unregistered managed files ({len(unregistered)}): {', '.join(unregistered)}"
        )
    return errors


def render_markdown(matrix: dict[str, Any], inventory: dict[str, Any]) -> str:
    mappings = matrix["mappings"]
    action_counts = Counter(item["action"] for item in mappings)
    source_counts = Counter(item["source"] for item in mappings)
    destinations = {item["destination"] for item in mappings}
    lines = [
        "# Coverage Matrix",
        "",
        f"> Status: **{matrix['status']}**. Every inventoried source is mapped; root Skill coverage "
        "is checked by controller-bound section audits rather than copied entrypoints. "
        "Receipts prove output byte integrity and controlled relocation only; they do not establish "
        "semantic integration.",
        "",
        "## Summary",
        "",
        f"- Inventory mappings: {len(mappings)}",
        f"- Unique destinations: {len(destinations)}",
        f"- Sources: {len(source_counts)}",
        "- Actions: " + ", ".join(f"{name}={action_counts[name]}" for name in sorted(action_counts)),
        "",
        "## Source counts",
        "",
        "| Source | Mappings |",
        "|---|---:|",
    ]
    lines.extend(f"| `{name}` | {source_counts[name]} |" for name in sorted(source_counts))
    lines.extend(["", "## Per-source mappings", ""])
    for source_name in sorted(source_counts):
        lines.extend(
            [
                f"### {source_name}",
                "",
                "| Source path | Kind | Action | Destination | Integrity / verification |",
                "|---|---|---|---|---|",
            ]
        )
        for item in (entry for entry in mappings if entry["source"] == source_name):
            note = item["integrity_note"].replace("|", "\\|")
            method = item["verification"]["method"].replace("|", "\\|")
            lines.append(
                f"| `{item['relative_path']}` | {item['kind']} | {item['action']} | "
                f"`{item['destination']}` | {note} {method} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def check_markdown_freshness(
    actual: str, matrix: dict[str, Any], inventory: dict[str, Any]
) -> list[str]:
    return [] if actual == render_markdown(matrix, inventory) else ["stale coverage-matrix.md"]


def atomic_write_text(path: Path, text: str) -> None:
    """Replace one generated text artifact only after its complete bytes are durable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        stream.write(text)
        stream.flush()
    try:
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_existing_integrity_receipts(matrix: dict[str, Any]) -> None:
    """Write byte-integrity and controlled-adaptation receipts for built outputs."""
    by_destination: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in matrix["mappings"]:
        if entry["action"] in RECEIPT_ACTIONS and not entry["verification"].get("audit"):
            by_destination[entry["destination"]].append(entry)

    for destination, entries in sorted(by_destination.items()):
        output_path = ROOT / PurePosixPath(destination)
        if not output_path.is_file():
            continue
        receipt_relative = entries[0]["verification"]["receipt"]
        receipt_path = ROOT / PurePosixPath(receipt_relative)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        sources = {
            (record["source"], record["relative_path"], record["sha256"])
            for entry in entries
            for record in entry["verification"]["sources"]
        }
        receipt = {
            "schema_version": 1,
            "kind": "byte-integrity-controlled-adaptation",
            "destination": destination,
            "output_sha256": sha256_bytes(output_path.read_bytes()),
            "sources": [
                {"source": source, "relative_path": relative_path, "sha256": digest}
                for source, relative_path, digest in sorted(sources)
            ],
            "bindings": sorted(
                (
                    binding
                    for entry in entries
                    if (
                        binding := adaptation_binding(
                            {
                                "source": entry["source"],
                                "relative_path": entry["relative_path"],
                                "sha256": entry["verification"]["source_sha256"],
                            },
                            destination,
                            entry["action"],
                        )
                    )
                    is not None
                ),
                key=lambda value: (
                    value["source"],
                    value["relative_path"],
                    value["action"],
                ),
            ),
        }
        receipt_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def write_root_audits(inventory: dict[str, Any]) -> None:
    root_items = {
        item["source"]: item
        for item in inventory["files"]
        if item["relative_path"].casefold() == "skill.md"
        and item["source"] in ROOT_SKILL_AUDIT_DESTINATIONS
    }
    for source_name, item in sorted(root_items.items()):
        source_bytes = Path(item["absolute_path"]).read_bytes()
        if sha256_bytes(source_bytes) != item["sha256"]:
            raise ValueError(f"source changed since inventory: {source_name}:SKILL.md")
        chunks = split_markdown_chunks(source_bytes.decode("utf-8"))
        routes = ROOT_AUDIT_ROUTES[source_name]
        chunk_ids = {chunk["id"] for chunk in chunks}
        if chunk_ids != set(routes):
            raise ValueError(f"root audit route table is stale for {source_name}")
        audit = {
            "schema_version": 1,
            "status": "integrated",
            "source": {
                "source": source_name,
                "relative_path": "SKILL.md",
                "sha256": item["sha256"],
                "chunking": AUDIT_CHUNKING,
            },
            "chunks": [],
        }
        for chunk in chunks:
            destination, anchor, evidence = routes[chunk["id"]]
            audit["chunks"].append(
                {
                    "id": chunk["id"],
                    "sha256": chunk["sha256"],
                    "heading": chunk["heading"],
                    "disposition": "integrated",
                    "destinations": [
                        {
                            "path": destination,
                            "anchor": anchor,
                            "evidence_terms": [evidence],
                        }
                    ],
                    "rationale": (
                        "This exact source block is operationalized by the declared unified module; "
                        "the anchor and evidence term are verifier-checked."
                    ),
                }
            )
        audit_path = ROOT / PurePosixPath(ROOT_SKILL_AUDIT_DESTINATIONS[source_name])
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(
            json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def write_seed() -> None:
    inventory_bytes = INVENTORY_PATH.read_bytes()
    inventory = json.loads(inventory_bytes)
    matrix = build_seed_matrix(inventory, inventory_bytes)
    with tempfile.TemporaryDirectory(prefix="coverage-seed-") as temp_directory:
        seed_errors = validate_coverage(
            inventory,
            matrix,
            Path(temp_directory),
            allow_missing_destinations=True,
            inventory_bytes=inventory_bytes,
        )
    if seed_errors:
        raise ValueError(
            "refusing to write invalid seed matrix: " + "; ".join(seed_errors)
        )
    markdown = render_markdown(matrix, inventory)
    write_root_audits(inventory)
    atomic_write_text(MATRIX_PATH, json.dumps(matrix, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(MARKDOWN_PATH, markdown)
    write_existing_integrity_receipts(matrix)


def finalize_matrix() -> None:
    inventory_bytes = INVENTORY_PATH.read_bytes()
    inventory = json.loads(inventory_bytes)
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    if matrix.get("status") != "migration-planning":
        raise ValueError("finalization requires a migration-planning matrix")
    preflight_errors = validate_coverage(
        inventory,
        matrix,
        ROOT,
        allow_missing_destinations=False,
        inventory_bytes=inventory_bytes,
        require_integrated_status=False,
    )
    if preflight_errors:
        raise ValueError("strict finalization failed: " + "; ".join(preflight_errors))
    candidate = json.loads(json.dumps(matrix))
    candidate["status"] = "integrated"
    errors = validate_coverage(
        inventory,
        candidate,
        ROOT,
        allow_missing_destinations=False,
        inventory_bytes=inventory_bytes,
        require_integrated_status=True,
    )
    if errors:
        raise ValueError("strict finalization failed: " + "; ".join(errors))
    markdown = render_markdown(candidate, inventory)
    atomic_write_text(MATRIX_PATH, json.dumps(candidate, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(MARKDOWN_PATH, markdown)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-missing-destinations",
        action="store_true",
        help="planning-only: validate schema/provenance before migration destinations exist",
    )
    parser.add_argument("--write-seed", action="store_true", help="regenerate deterministic JSON and Markdown")
    parser.add_argument(
        "--finalize",
        action="store_true",
        help="switch a validated planning matrix to integrated only after strict verification",
    )
    parser.add_argument(
        "--source-root",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="portable installed-source root override used by root audit verification",
    )
    args = parser.parse_args(argv)
    source_root_overrides: dict[str, Path] = {}
    for value in args.source_root:
        if "=" not in value:
            parser.error("--source-root must use NAME=PATH")
        name, path = value.split("=", 1)
        if not name or not path or name in source_root_overrides:
            parser.error("--source-root names and paths must be nonempty and unique")
        source_root_overrides[name] = Path(path)
    if args.write_seed:
        write_seed()
        print(f"wrote {MATRIX_PATH} and {MARKDOWN_PATH}")
        return 0
    if args.finalize:
        finalize_matrix()
        print(f"finalized {MATRIX_PATH} after strict verification")
        return 0

    inventory_bytes = INVENTORY_PATH.read_bytes()
    inventory = json.loads(inventory_bytes)
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    errors = validate_coverage(
        inventory,
        matrix,
        ROOT,
        allow_missing_destinations=args.allow_missing_destinations,
        inventory_bytes=inventory_bytes,
        source_root_overrides=source_root_overrides,
    )
    if MARKDOWN_PATH.is_file():
        errors.extend(check_markdown_freshness(MARKDOWN_PATH.read_text(encoding="utf-8"), matrix, inventory))
    else:
        errors.append("missing coverage-matrix.md")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    mode = (
        f"planning mode ({matrix['status']} matrix)"
        if args.allow_missing_destinations
        else "strict mode"
    )
    print(
        f"coverage valid in {mode}: mappings={len(matrix['mappings'])}, "
        f"destinations={len({item['destination'] for item in matrix['mappings']})}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
