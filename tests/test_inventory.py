from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "build_source_inventory.py"
INVENTORY_PATH = PROJECT_ROOT / "references" / "provenance" / "source-inventory.json"

SPEC = importlib.util.spec_from_file_location("build_source_inventory", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
inventory_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory_module)


EXPECTED_ROOTS = {
    "cumcm-step-review": r"C:\Users\qwerq\.codex\skills\cumcm-step-review",
    "cumcm-c-problem": r"C:\Users\qwerq\.codex\skills\cumcm-c-problem-lfs",
    "math-modeling": r"C:\Users\qwerq\.codex\skills\math-modeling",
}
EXPECTED_MARKDOWN = [
    "数学建模算法库_整合版.md",
    "优秀论文特点与Skill补充建议.md",
    "math-modeling-skill-详细总结.md",
    "CUMCM写作证据门禁补充.md",
    "CUMCM-Step-Review-Skill总结.md",
]
KINDS = {"instruction", "reference", "script", "test", "asset", "metadata"}
FILE_FIELDS = {
    "source",
    "relative_path",
    "absolute_path",
    "size",
    "sha256",
    "kind",
}


def test_default_inventory_has_exact_inputs_and_valid_records() -> None:
    inventory = inventory_module.build_inventory()

    assert inventory["source_roots"] == EXPECTED_ROOTS
    assert inventory["workspace_markdown_inputs"] == EXPECTED_MARKDOWN
    workspace_files = [
        item for item in inventory["files"] if item["source"] == "workspace-markdown"
    ]
    assert [item["relative_path"] for item in workspace_files] == sorted(
        EXPECTED_MARKDOWN, key=lambda value: (value.casefold(), value)
    )
    assert len(workspace_files) == 5

    for item in inventory["files"]:
        assert set(item) == FILE_FIELDS
        assert "\\" not in item["relative_path"]
        assert Path(item["absolute_path"]).is_absolute()
        assert item["size"] >= 0
        assert len(item["sha256"]) == 64
        assert item["sha256"] == item["sha256"].lower()
        assert set(item["sha256"]) <= set("0123456789abcdef")
        assert item["kind"] in KINDS


def test_classification_exclusions_duplicates_and_conflicts(tmp_path: Path) -> None:
    roots = {name: tmp_path / name for name in ("alpha", "beta")}
    for root in roots.values():
        (root / "references").mkdir(parents=True)
        (root / "scripts").mkdir()
        (root / "tests").mkdir()
        (root / "assets").mkdir()

    (roots["alpha"] / "SKILL.md").write_text("instruction", encoding="utf-8")
    (roots["alpha"] / "references" / "note.md").write_text("same", encoding="utf-8")
    (roots["alpha"] / "scripts" / "tool.py").write_text("print(1)", encoding="utf-8")
    (roots["alpha"] / "tests" / "test_tool.py").write_text("pass", encoding="utf-8")
    (roots["alpha"] / "assets" / "icon.png").write_bytes(b"png")
    (roots["alpha"] / "manifest.json").write_text("{}", encoding="utf-8")
    (roots["beta"] / "references" / "copy.md").write_text("same", encoding="utf-8")
    (roots["beta"] / "references" / "note.md").write_text("different", encoding="utf-8")
    cache = roots["beta"] / "__pycache__" / "tool.pyc"
    cache.parent.mkdir()
    cache.write_bytes(b"generated")
    optimized = roots["beta"] / "orphan.pyo"
    optimized.write_bytes(b"generated")

    inventory = inventory_module.build_inventory(
        source_roots=roots,
        workspace_root=tmp_path,
        workspace_markdown=(),
    )
    kinds = {
        (item["source"], item["relative_path"]): item["kind"]
        for item in inventory["files"]
    }
    assert kinds[("alpha", "SKILL.md")] == "instruction"
    assert kinds[("alpha", "references/note.md")] == "reference"
    assert kinds[("alpha", "scripts/tool.py")] == "script"
    assert kinds[("alpha", "tests/test_tool.py")] == "test"
    assert kinds[("alpha", "assets/icon.png")] == "asset"
    assert kinds[("alpha", "manifest.json")] == "metadata"

    assert [(item["relative_path"], item["reason"]) for item in inventory["excluded_generated"]] == [
        ("__pycache__/tool.pyc", "generated Python bytecode"),
        ("orphan.pyo", "generated Python bytecode"),
    ]
    included = {item["absolute_path"] for item in inventory["files"]}
    assert all(item["absolute_path"] not in included for item in inventory["excluded_generated"])

    assert len(inventory["exact_duplicate_groups"]) == 1
    duplicate = inventory["exact_duplicate_groups"][0]
    assert duplicate["member_count"] == 2
    assert [(item["source"], item["relative_path"]) for item in duplicate["members"]] == [
        ("alpha", "references/note.md"),
        ("beta", "references/copy.md"),
    ]
    assert inventory["same_relative_path_conflicts"][0]["relative_path"] == "references/note.md"
    assert inventory["same_relative_path_conflicts"][0]["hash_count"] == 2


def test_mixed_content_under_scripts_is_classified_by_semantic_file_type(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    scripts = root / "scripts" / "runtime"
    scripts.mkdir(parents=True)
    (scripts / "driver.py").write_text("print('run')", encoding="utf-8")
    (scripts / "schema.xsd").write_text("<schema/>", encoding="utf-8")
    (scripts / "config.xml").write_text("<config/>", encoding="utf-8")
    (scripts / "records.csv").write_text("value\n1\n", encoding="utf-8")
    (scripts / "README.md").write_text("runtime notes", encoding="utf-8")

    inventory = inventory_module.build_inventory(
        source_roots={"source": root},
        workspace_root=tmp_path,
        workspace_markdown=(),
    )
    kinds = {item["relative_path"]: item["kind"] for item in inventory["files"]}

    assert kinds == {
        "scripts/runtime/README.md": "reference",
        "scripts/runtime/config.xml": "metadata",
        "scripts/runtime/driver.py": "script",
        "scripts/runtime/records.csv": "asset",
        "scripts/runtime/schema.xsd": "metadata",
    }


def test_same_source_copies_are_not_cross_source_duplicate_groups(tmp_path: Path) -> None:
    root = tmp_path / "only-source"
    root.mkdir()
    (root / "first.md").write_text("copy", encoding="utf-8")
    (root / "second.md").write_text("copy", encoding="utf-8")

    inventory = inventory_module.build_inventory(
        source_roots={"only": root},
        workspace_root=tmp_path,
        workspace_markdown=(),
    )

    assert inventory["exact_duplicate_groups"] == []


def test_relative_path_conflicts_use_casefolded_windows_collision_keys(
    tmp_path: Path,
) -> None:
    alpha = tmp_path / "alpha"
    beta = tmp_path / "beta"
    (alpha / "Path").mkdir(parents=True)
    (beta / "path").mkdir(parents=True)
    (alpha / "Path" / "Note.md").write_text("alpha", encoding="utf-8")
    (beta / "path" / "note.md").write_text("beta", encoding="utf-8")

    inventory = inventory_module.build_inventory(
        source_roots={"alpha": alpha, "beta": beta},
        workspace_root=tmp_path,
        workspace_markdown=(),
    )

    assert len(inventory["same_relative_path_conflicts"]) == 1
    conflict = inventory["same_relative_path_conflicts"][0]
    assert conflict["relative_path"] == "path/note.md"
    assert conflict["hash_count"] == 2
    assert [item["relative_path"] for item in conflict["members"]] == [
        "Path/Note.md",
        "path/note.md",
    ]


def test_output_order_and_serialization_are_deterministic(tmp_path: Path) -> None:
    first = inventory_module.build_inventory()
    second = inventory_module.build_inventory()
    assert first == second

    file_keys = [(item["source"], item["relative_path"]) for item in first["files"]]
    excluded_keys = [
        (item["source"], item["relative_path"])
        for item in first["excluded_generated"]
    ]
    order = lambda item: (item[0].casefold(), item[1].casefold(), item)
    assert file_keys == sorted(file_keys, key=order)
    assert excluded_keys == sorted(excluded_keys, key=order)
    assert list(first["category_counts"]) == sorted(first["category_counts"])

    output_a = tmp_path / "a.json"
    output_b = tmp_path / "b.json"
    inventory_module.write_inventory(first, output_a)
    inventory_module.write_inventory(second, output_b)
    assert output_a.read_bytes() == output_b.read_bytes()
    assert output_a.read_bytes().endswith(b"\n")
    assert "数学建模" in output_a.read_text(encoding="utf-8")


def test_cli_output_option_writes_requested_file(tmp_path: Path) -> None:
    output = tmp_path / "inventory.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output", str(output)],
        cwd=PROJECT_ROOT.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output.is_file()
    assert json.loads(output.read_text(encoding="utf-8")) == inventory_module.build_inventory()


def test_cli_accepts_portable_source_root_and_workspace_overrides(tmp_path: Path) -> None:
    source_root = tmp_path / "portable-source"
    source_root.mkdir()
    (source_root / "SKILL.md").write_text("portable", encoding="utf-8")
    workspace = tmp_path / "portable-workspace"
    workspace.mkdir()
    (workspace / "note.md").write_text("note", encoding="utf-8")
    output = tmp_path / "portable.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--output",
            str(output),
            "--source-root",
            f"portable={source_root}",
            "--workspace-root",
            str(workspace),
            "--workspace-markdown",
            "note.md",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    inventory = json.loads(output.read_text(encoding="utf-8"))
    assert inventory["source_roots"] == {"portable": str(source_root.resolve())}
    assert inventory["workspace_root"] == str(workspace.resolve())


def test_cli_accepts_portable_inventory_roots_from_environment(tmp_path: Path) -> None:
    source_root = tmp_path / "environment-source"
    source_root.mkdir()
    (source_root / "SKILL.md").write_text("portable", encoding="utf-8")
    workspace = tmp_path / "environment-workspace"
    workspace.mkdir()
    (workspace / "note.md").write_text("note", encoding="utf-8")
    output = tmp_path / "environment.json"
    environment = os.environ.copy()
    environment.update(
        {
            "MATH_MODELING_SOURCE_ROOTS_JSON": json.dumps({"portable": str(source_root)}),
            "MATH_MODELING_WORKSPACE_ROOT": str(workspace),
            "MATH_MODELING_WORKSPACE_MARKDOWN_JSON": json.dumps(["note.md"]),
        }
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output", str(output)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    inventory = json.loads(output.read_text(encoding="utf-8"))
    assert inventory["source_roots"] == {"portable": str(source_root.resolve())}
    assert inventory["workspace_markdown_inputs"] == ["note.md"]


def test_builder_accepts_individual_source_root_overrides(tmp_path: Path) -> None:
    alpha = tmp_path / "alpha"
    replacement = tmp_path / "replacement"
    alpha.mkdir()
    replacement.mkdir()
    (alpha / "old.md").write_text("old", encoding="utf-8")
    (replacement / "new.md").write_text("new", encoding="utf-8")
    inventory = inventory_module.build_inventory(
        source_roots={"alpha": alpha},
        source_root_overrides={"alpha": replacement},
        workspace_root=tmp_path,
        workspace_markdown=(),
    )
    assert inventory["source_roots"] == {"alpha": str(replacement.resolve())}
    assert [item["relative_path"] for item in inventory["files"]] == ["new.md"]


def test_cli_accepts_complete_root_map_plus_individual_override(tmp_path: Path) -> None:
    original = tmp_path / "original"
    replacement = tmp_path / "replacement"
    workspace = tmp_path / "workspace"
    for directory in (original, replacement, workspace):
        directory.mkdir()
    (original / "old.md").write_text("old", encoding="utf-8")
    (replacement / "new.md").write_text("new", encoding="utf-8")
    (workspace / "note.md").write_text("note", encoding="utf-8")
    root_map = tmp_path / "roots.json"
    root_map.write_text(json.dumps({"alpha": str(original)}), encoding="utf-8")
    output = tmp_path / "inventory.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--output",
            str(output),
            "--source-root-map",
            str(root_map),
            "--source-root-override",
            f"alpha={replacement}",
            "--workspace-root",
            str(workspace),
            "--workspace-markdown",
            "note.md",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    inventory = json.loads(output.read_text(encoding="utf-8"))
    assert inventory["source_roots"] == {"alpha": str(replacement.resolve())}
    assert any(item["relative_path"] == "new.md" for item in inventory["files"])


def test_checked_in_inventory_exactly_matches_current_build() -> None:
    assert json.loads(INVENTORY_PATH.read_text(encoding="utf-8")) == inventory_module.build_inventory()
