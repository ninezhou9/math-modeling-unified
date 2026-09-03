from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "verify_coverage.py"
INVENTORY_PATH = PROJECT_ROOT / "references" / "provenance" / "source-inventory.json"
MATRIX_PATH = PROJECT_ROOT / "references" / "provenance" / "coverage-matrix.json"
MARKDOWN_PATH = PROJECT_ROOT / "references" / "provenance" / "coverage-matrix.md"

SPEC = importlib.util.spec_from_file_location("verify_coverage", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
coverage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(coverage)


@pytest.fixture(autouse=True)
def restore_controller_owned_tables():
    """Keep tests that install synthetic controller routes/rules isolated."""
    routes = copy.deepcopy(coverage.ROOT_AUDIT_ROUTES)
    adaptations = copy.deepcopy(coverage.CONTROLLED_ADAPTATION_OVERRIDES)
    yield
    coverage.ROOT_AUDIT_ROUTES.clear()
    coverage.ROOT_AUDIT_ROUTES.update(routes)
    coverage.CONTROLLED_ADAPTATION_OVERRIDES.clear()
    coverage.CONTROLLED_ADAPTATION_OVERRIDES.update(adaptations)


def source(source: str, path: str, digest: str, kind: str = "reference") -> dict:
    return {
        "source": source,
        "relative_path": path,
        "absolute_path": f"C:/sources/{source}/{path}",
        "size": 1,
        "sha256": digest,
        "kind": kind,
    }


def mapping(item: dict, destination: str, action: str = "preserve") -> dict:
    return {
        "source": item["source"],
        "relative_path": item["relative_path"],
        "kind": item["kind"],
        "destination": destination,
        "action": action,
        "integrity_note": "Preserve this source contribution without content loss.",
        "verification": {
            "source_sha256": item["sha256"],
            "method": "Verify the migrated content against this recorded source hash.",
            "sources": [
                {
                    "source": item["source"],
                    "relative_path": item["relative_path"],
                    "sha256": item["sha256"],
                }
            ],
            "receipt": (
                "references/provenance/receipts/test-merge.json"
                if action in {"merge", "enhance"}
                else None
            ),
            "audit": None,
        },
    }


def fixture_inventory(*items: dict) -> dict:
    return {"files": list(items), "exact_duplicate_groups": [], "same_relative_path_conflicts": []}


def fixture_matrix(*mappings: dict) -> dict:
    action_counts: dict[str, int] = {}
    for item in mappings:
        action_counts[item["action"]] = action_counts.get(item["action"], 0) + 1
    return {
        "schema_version": 1,
        "status": "integrated",
        "inventory_sha256": "0" * 64,
        "inventory_file_count": len(mappings),
        "allowed_actions": sorted(coverage.ALLOWED_ACTIONS),
        "managed_destinations": [
            "SKILL.md",
            "agents",
            "assets",
            "references",
            "scripts",
            "tests",
            "tools",
        ],
        "summary": {
            "mapping_count": len(mappings),
            "source_count": len({item["source"] for item in mappings}),
            "destination_count": len({item["destination"] for item in mappings}),
            "action_counts": dict(sorted(action_counts.items())),
        },
        "mappings": list(mappings),
    }


def messages(errors: list) -> str:
    return "\n".join(str(error) for error in errors)


def write_root_audit(tmp_path: Path, item: dict, *, status: str = "integrated") -> tuple[dict, Path]:
    source_path = Path(item["absolute_path"])
    chunks = coverage.split_markdown_chunks(source_path.read_bytes().decode("utf-8"))
    destination = "evidence/target.md"
    target = tmp_path / destination
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Routed target\n\nshared evidence term\n", encoding="utf-8")
    coverage.ROOT_AUDIT_ROUTES[item["source"]] = {
        chunk["id"]: (destination, "Routed target", "shared evidence term")
        for chunk in chunks
    }
    audit_path = tmp_path / coverage.ROOT_SKILL_AUDIT_DESTINATIONS[item["source"]]
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit = {
        "schema_version": 1,
        "status": status,
        "source": {
            "source": item["source"],
            "relative_path": "SKILL.md",
            "sha256": item["sha256"],
            "chunking": "utf8-frontmatter-and-heading-blocks-v1",
        },
        "chunks": [
            {
                "id": chunk["id"],
                "sha256": chunk["sha256"],
                "heading": chunk["heading"],
                "disposition": "integrated",
                "destinations": [
                    {
                        "path": destination,
                        "anchor": "Routed target",
                        "evidence_terms": ["shared evidence term"],
                    }
                ],
                "rationale": "The unified target operationalizes this source block.",
            }
            for chunk in chunks
        ],
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
    entry = mapping(item, audit_path.relative_to(tmp_path).as_posix(), "enhance")
    entry["verification"]["receipt"] = None
    entry["verification"]["audit"] = entry["destination"]
    return {"audit": audit, "entry": entry}, audit_path


def install_test_adaptation(
    tmp_path: Path, item: dict, destination: str, action: str
) -> dict:
    test_id = "controller_regression.py::test_controller_rule"
    test_file = tmp_path / "controller_regression.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_controller_rule():\n    pass\n", encoding="utf-8")
    coverage.CONTROLLED_ADAPTATION_OVERRIDES[
        (item["source"], item["relative_path"], destination, action)
    ] = {
        "rule_id": "test-controller-rule-v1",
        "evidence_type": "test-regression",
        "test_ids": [test_id],
    }
    binding = coverage.adaptation_binding(item, destination, action)
    assert binding is not None
    return binding


def copied_checked_in_root_audit(tmp_path: Path, source_name: str = "math-modeling") -> tuple[dict, dict, Path]:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    item = next(
        item
        for item in inventory["files"]
        if item["source"] == source_name and item["relative_path"].casefold() == "skill.md"
    )
    relative = coverage.ROOT_SKILL_AUDIT_DESTINATIONS[source_name]
    audit = json.loads((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
    for chunk in audit["chunks"]:
        chunk["destinations"] = copy.deepcopy(
            coverage._authoritative_route(source_name, chunk["id"])
        )
    audit_path = tmp_path / relative
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    for chunk in audit["chunks"]:
        for routed in chunk["destinations"]:
            destination = tmp_path / routed["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PROJECT_ROOT / routed["path"], destination)
    audit_path.write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
    return item, audit, audit_path


def test_rejects_missing_extra_and_duplicate_mapping_keys(tmp_path: Path) -> None:
    a = source("alpha", "a.md", "a" * 64)
    b = source("beta", "b.md", "b" * 64)
    inventory = fixture_inventory(a, b)

    missing = fixture_matrix(mapping(a, "references/a.md"))
    assert "missing mapping keys (1): beta:b.md" in messages(
        coverage.validate_coverage(inventory, missing, tmp_path, allow_missing_destinations=True)
    )

    extra_item = source("extra", "c.md", "c" * 64)
    extra = fixture_matrix(
        mapping(a, "references/a.md"),
        mapping(b, "references/b.md"),
        mapping(extra_item, "references/c.md"),
    )
    assert "extra mapping keys (1): extra:c.md" in messages(
        coverage.validate_coverage(inventory, extra, tmp_path, allow_missing_destinations=True)
    )

    duplicate = fixture_matrix(
        mapping(a, "references/a.md"),
        mapping(a, "references/a-copy.md"),
        mapping(b, "references/b.md"),
    )
    assert "duplicate mapping keys (1): alpha:a.md" in messages(
        coverage.validate_coverage(inventory, duplicate, tmp_path, allow_missing_destinations=True)
    )


@pytest.mark.parametrize("action", ["delete", "ignore", "copy", ""])
def test_rejects_invalid_actions(action: str, tmp_path: Path) -> None:
    item = source("alpha", "a.md", "a" * 64)
    candidate = mapping(item, "references/a.md")
    candidate["action"] = action
    errors = coverage.validate_coverage(
        fixture_inventory(item), fixture_matrix(candidate), tmp_path, True
    )
    assert "invalid action" in messages(errors)


@pytest.mark.parametrize(
    "destination", ["", ".", "/absolute.md", "C:/drive.md", "../escape.md", "a/../b.md", "a\\b.md", "./a.md"]
)
def test_rejects_empty_absolute_traversing_or_non_normalized_destinations(
    destination: str, tmp_path: Path
) -> None:
    item = source("alpha", "a.md", "a" * 64)
    errors = coverage.validate_coverage(
        fixture_inventory(item), fixture_matrix(mapping(item, destination)), tmp_path, True
    )
    assert "invalid destination" in messages(errors)


def test_rejects_empty_notes_and_invalid_source_hash_assumptions(tmp_path: Path) -> None:
    item = source("alpha", "a.md", "a" * 64)
    candidate = mapping(item, "references/a.md")
    candidate["integrity_note"] = " "
    candidate["verification"]["method"] = ""
    candidate["verification"]["source_sha256"] = "b" * 64
    text = messages(
        coverage.validate_coverage(
            fixture_inventory(item), fixture_matrix(candidate), tmp_path, True
        )
    )
    assert "empty integrity_note" in text
    assert "empty verification method" in text
    assert "source hash mismatch" in text


def test_exact_hash_duplicates_require_complete_canonical_deduplication(tmp_path: Path) -> None:
    digest = "d" * 64
    a = source("alpha", "shared.md", digest)
    b = source("beta", "shared.md", digest)
    inventory = fixture_inventory(a, b)
    inventory["exact_duplicate_groups"] = [
        {"sha256": digest, "member_count": 2, "members": [a, b]}
    ]
    bad = fixture_matrix(
        mapping(a, "references/a.md", "deduplicate"),
        mapping(b, "references/b.md", "deduplicate"),
    )
    assert "duplicate group must share one canonical destination" in messages(
        coverage.validate_coverage(inventory, bad, tmp_path, True)
    )

    good_a = mapping(a, "references/canonical.md", "deduplicate")
    good_b = mapping(b, "references/canonical.md", "deduplicate")
    duplicate_sources = [
        {"source": item["source"], "relative_path": item["relative_path"], "sha256": item["sha256"]}
        for item in (a, b)
    ]
    good_a["verification"]["sources"] = duplicate_sources
    good_b["verification"]["sources"] = duplicate_sources
    good_a["verification"]["method"] = f"SHA-256 {digest} proves byte identity; use one canonical copy."
    good_b["verification"]["method"] = f"SHA-256 {digest} proves byte identity; use one canonical copy."
    assert coverage.validate_coverage(
        inventory, fixture_matrix(good_a, good_b), tmp_path, True
    ) == []


def test_different_hashes_sharing_destination_require_specific_merge_records(tmp_path: Path) -> None:
    a = source("alpha", "same.md", "a" * 64)
    b = source("beta", "same.md", "b" * 64)
    inventory = fixture_inventory(a, b)
    inventory["same_relative_path_conflicts"] = [
        {"relative_path": "same.md", "hash_count": 2, "members": [a, b]}
    ]
    bad = fixture_matrix(
        mapping(a, "references/shared.md", "deduplicate"),
        mapping(b, "references/shared.md", "deduplicate"),
    )
    assert "different source hashes share destination" in messages(
        coverage.validate_coverage(inventory, bad, tmp_path, True)
    )

    good = fixture_matrix(
        mapping(a, "references/alpha-same.md", "rename"),
        mapping(b, "references/beta-same.md", "rename"),
    )
    assert coverage.validate_coverage(inventory, good, tmp_path, True) == []

    merged = [mapping(a, "references/shared.md", "merge"), mapping(b, "references/shared.md", "merge")]
    merge_sources = [
        {"source": item["source"], "relative_path": item["relative_path"], "sha256": item["sha256"]}
        for item in (a, b)
    ]
    for entry in merged:
        entry["integrity_note"] = "Merge different-hash source conflict into references/shared.md; retain unique rules and resolve contradictions."
        entry["verification"]["method"] = "Compare both recorded hashes and audit the merged sections against both source files."
        entry["verification"]["sources"] = merge_sources
    install_test_adaptation(tmp_path, a, "references/shared.md", "merge")
    install_test_adaptation(tmp_path, b, "references/shared.md", "merge")
    assert coverage.validate_coverage(inventory, fixture_matrix(*merged), tmp_path, True) == []


def test_exact_duplicate_group_cannot_bypass_canonicalization_with_all_preserve(
    tmp_path: Path,
) -> None:
    digest = "d" * 64
    a = source("alpha", "shared.md", digest)
    b = source("beta", "shared.md", digest)
    inventory = fixture_inventory(a, b)
    inventory["exact_duplicate_groups"] = [
        {"sha256": digest, "member_count": 2, "members": [a, b]}
    ]
    matrix = fixture_matrix(
        mapping(a, "references/a.md", "preserve"),
        mapping(b, "references/b.md", "preserve"),
    )

    assert "duplicate group must share one canonical destination" in messages(
        coverage.validate_coverage(inventory, matrix, tmp_path, True)
    )


def test_strict_reports_exact_missing_destinations_but_planning_mode_passes(tmp_path: Path) -> None:
    a = source("alpha", "a.md", "a" * 64)
    b = source("beta", "b.md", "b" * 64)
    matrix = fixture_matrix(mapping(a, "references/a.md"), mapping(b, "scripts/b.py"))
    assert coverage.validate_coverage(
        fixture_inventory(a, b), matrix, tmp_path, allow_missing_destinations=True
    ) == []
    assert messages(coverage.validate_coverage(fixture_inventory(a, b), matrix, tmp_path)) == (
        "missing destination files (2): references/a.md, scripts/b.py"
    )


def test_rejects_unregistered_files_under_managed_destinations(tmp_path: Path) -> None:
    item = source("alpha", "a.md", "a" * 64)
    matrix = fixture_matrix(mapping(item, "references/workflow/a.md"))
    matrix["managed_destinations"] = ["references/workflow"]
    destination = tmp_path / "references" / "workflow" / "a.md"
    destination.parent.mkdir(parents=True)
    destination.write_text("planned", encoding="utf-8")
    (destination.parent / "orphan.md").write_text("orphan", encoding="utf-8")
    assert "unregistered managed files (1): references/workflow/orphan.md" in messages(
        coverage.validate_coverage(fixture_inventory(item), matrix, tmp_path)
    )


def test_planning_mode_still_rejects_unregistered_managed_files(tmp_path: Path) -> None:
    item = source("alpha", "a.md", "a" * 64)
    matrix = fixture_matrix(mapping(item, "references/workflow/a.md"))
    matrix["managed_destinations"] = ["references/workflow"]
    managed = tmp_path / "references" / "workflow"
    managed.mkdir(parents=True)
    (managed / "orphan.md").write_text("orphan", encoding="utf-8")

    text = messages(
        coverage.validate_coverage(
            fixture_inventory(item), matrix, tmp_path, allow_missing_destinations=True
        )
    )
    assert "unregistered managed files (1): references/workflow/orphan.md" in text
    assert "missing destination files" not in text


def test_identical_hashes_in_different_tool_packages_remain_package_local(
    tmp_path: Path,
) -> None:
    digest = "d" * 64
    docx = source("alpha", "tools/docx/LICENSE.txt", digest, "metadata")
    pdf = source("beta", "tools/pdf/LICENSE.txt", digest, "metadata")
    xlsx = source("gamma", "tools/xlsx/LICENSE.txt", digest, "metadata")
    inventory = fixture_inventory(docx, pdf, xlsx)
    inventory["exact_duplicate_groups"] = [
        {"sha256": digest, "member_count": 3, "members": [docx, pdf, xlsx]}
    ]

    matrix = coverage.build_seed_matrix(inventory, b"inventory")
    by_key = {(item["source"], item["relative_path"]): item for item in matrix["mappings"]}
    assert by_key[("alpha", "tools/docx/LICENSE.txt")]["destination"] == "tools/docx/LICENSE.txt"
    assert by_key[("beta", "tools/pdf/LICENSE.txt")]["destination"] == "tools/pdf/LICENSE.txt"
    assert by_key[("gamma", "tools/xlsx/LICENSE.txt")]["destination"] == "tools/xlsx/LICENSE.txt"
    assert {item["action"] for item in matrix["mappings"]} == {"preserve"}
    assert coverage.validate_coverage(inventory, matrix, tmp_path, True, b"inventory") == []


@pytest.mark.parametrize(
    ("relative_path", "destination"),
    [
        (
            "tools/pdf/scripts/convert_pdf_to_images.py",
            "tools/pdf/source-variants/shared/scripts/convert_pdf_to_images.py",
        ),
        ("tools/pdf/SKILL.md", "tools/pdf/source-variants/shared/SKILL.md"),
    ],
)
def test_pdf_sources_are_preserved_away_from_unified_cli(
    relative_path: str, destination: str
) -> None:
    digest = "d" * 64
    first = source("alpha", relative_path, digest, "script")
    second = source("beta", relative_path, digest, "script")
    inventory = fixture_inventory(first, second)
    inventory["exact_duplicate_groups"] = [
        {"sha256": digest, "member_count": 2, "members": [first, second]}
    ]

    matrix = coverage.build_seed_matrix(inventory, b"inventory")
    entries = matrix["mappings"]
    assert {entry["action"] for entry in entries} == {"deduplicate"}
    assert {entry["destination"] for entry in entries} == {destination}


def test_strict_direct_integrity_accepts_matching_bytes_and_rejects_corruption(tmp_path: Path) -> None:
    content = b"preserved bytes"
    item = source("alpha", "a.md", hashlib.sha256(content).hexdigest())
    matrix = fixture_matrix(mapping(item, "references/a.md"))
    destination = tmp_path / "references" / "a.md"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(content)
    assert coverage.validate_coverage(fixture_inventory(item), matrix, tmp_path) == []

    destination.write_bytes(b"corrupt")
    assert "destination hash mismatch" in messages(
        coverage.validate_coverage(fixture_inventory(item), matrix, tmp_path)
    )


def test_strict_merge_integrity_requires_valid_receipt_and_output_hash(tmp_path: Path) -> None:
    a = source("alpha", "same.md", "a" * 64)
    b = source("beta", "same.md", "b" * 64)
    entries = [mapping(a, "references/shared.md", "merge"), mapping(b, "references/shared.md", "merge")]
    records = [source_record for source_record in (entries[0]["verification"]["sources"][0], entries[1]["verification"]["sources"][0])]
    for entry in entries:
        entry["integrity_note"] = "Merge different-hash source conflict into references/shared.md; retain unique rules."
        entry["verification"]["sources"] = records
    matrix = fixture_matrix(*entries)
    destination = tmp_path / "references" / "shared.md"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"merged output")
    receipt_path = tmp_path / entries[0]["verification"]["receipt"]
    receipt_path.parent.mkdir(parents=True)
    bindings = [
        install_test_adaptation(tmp_path, item, "references/shared.md", "merge")
        for item in (a, b)
    ]

    assert "missing byte-integrity receipt" in messages(
        coverage.validate_coverage(fixture_inventory(a, b), matrix, tmp_path)
    )
    receipt = {
        "schema_version": 1,
        "kind": "byte-integrity-controlled-adaptation",
        "destination": "references/shared.md",
        "output_sha256": hashlib.sha256(b"merged output").hexdigest(),
        "sources": records,
        "bindings": bindings,
    }
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert coverage.validate_coverage(fixture_inventory(a, b), matrix, tmp_path) == []

    destination.write_bytes(b"")
    receipt["output_sha256"] = hashlib.sha256(b"").hexdigest()
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert "empty merged destination" in messages(
        coverage.validate_coverage(fixture_inventory(a, b), matrix, tmp_path)
    )

    destination.write_bytes(b"merged output")
    receipt["output_sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert "byte-integrity receipt output hash mismatch" in messages(
        coverage.validate_coverage(fixture_inventory(a, b), matrix, tmp_path)
    )


def test_malformed_mapping_key_types_report_errors_without_crashing(tmp_path: Path) -> None:
    item = source("alpha", "a.md", "a" * 64)
    bad = mapping(item, "references/a.md")
    bad["source"] = None
    bad["relative_path"] = 7
    also_bad = mapping(item, "references/b.md")
    also_bad["source"] = "mixed"
    also_bad["relative_path"] = None
    text = messages(
        coverage.validate_coverage(
            fixture_inventory(item), fixture_matrix(bad, also_bad), tmp_path, True
        )
    )
    assert "field source must be a string" in text
    assert "field relative_path must be a string" in text
    assert "missing mapping keys (1): alpha:a.md" in text


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", ["unhashable"]),
        ("source", {"unhashable": True}),
        ("relative_path", ["unhashable"]),
        ("relative_path", {"unhashable": True}),
    ],
)
def test_unhashable_mapping_key_types_report_errors_without_crashing(
    field: str, value, tmp_path: Path
) -> None:
    item = source("alpha", "a.md", "a" * 64)
    entry = mapping(item, "references/a.md")
    matrix = fixture_matrix(entry)
    entry[field] = value

    text = messages(
        coverage.validate_coverage(fixture_inventory(item), matrix, tmp_path, True)
    )
    assert f"field {field} must be a string" in text
    assert "missing mapping keys (1): alpha:a.md" in text


@pytest.mark.parametrize(
    "destination",
    [
        "references/a:b.md",
        "references/CON",
        "references/con.txt",
        "references/PRN.md",
        "references/AUX",
        "references/NUL.txt",
        "references/COM1.log",
        "references/LPT9.md",
        "references/COM¹.log",
        "references/com².txt",
        "references/Com³",
        "references/LPT¹.log",
        "references/lpt².txt",
        "references/Lpt³",
        "references/bad<name>.md",
        'references/bad"name.md',
        "references/bad|name.md",
        "references/bad?name.md",
        "references/bad*name.md",
        "references/bad\tname.md",
        "references/trailing.",
        "references/trailing ",
    ],
)
def test_rejects_windows_unsafe_destination_components(destination: str, tmp_path: Path) -> None:
    item = source("alpha", "a.md", "a" * 64)
    assert "invalid destination" in messages(
        coverage.validate_coverage(
            fixture_inventory(item), fixture_matrix(mapping(item, destination)), tmp_path, True
        )
    )


def test_rejects_case_insensitive_destination_collisions(tmp_path: Path) -> None:
    a = source("alpha", "a.md", "a" * 64)
    b = source("beta", "b.md", "b" * 64)
    matrix = fixture_matrix(
        mapping(a, "references/Result.md"), mapping(b, "references/result.md")
    )
    assert "case-insensitive destination collision" in messages(
        coverage.validate_coverage(fixture_inventory(a, b), matrix, tmp_path, True)
    )


@pytest.mark.parametrize(
    "receipt_sources",
    [
        None,
        {},
        [{"source": "alpha", "relative_path": "same.md", "sha256": "a" * 64, "extra": True}],
        [
            {"source": "alpha", "relative_path": "same.md", "sha256": "a" * 64},
            {"source": "beta", "relative_path": "same.md", "sha256": "b" * 64},
            {"source": "alpha", "relative_path": "same.md", "sha256": "a" * 64},
        ],
        [
            {"source": None, "relative_path": "same.md", "sha256": "a" * 64},
            {"source": "beta", "relative_path": "same.md", "sha256": "b" * 64},
        ],
    ],
)
def test_strict_receipt_rejects_malformed_source_records_without_crashing(
    receipt_sources, tmp_path: Path
) -> None:
    a = source("alpha", "same.md", "a" * 64)
    b = source("beta", "same.md", "b" * 64)
    entries = [
        mapping(a, "references/shared.md", "merge"),
        mapping(b, "references/shared.md", "merge"),
    ]
    records = [entry["verification"]["sources"][0] for entry in entries]
    for entry in entries:
        entry["integrity_note"] = (
            "Merge different-hash source conflict into references/shared.md; retain unique rules."
        )
        entry["verification"]["sources"] = records
    destination = tmp_path / "references" / "shared.md"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"merged output")
    receipt_path = tmp_path / entries[0]["verification"]["receipt"]
    receipt_path.parent.mkdir(parents=True)
    bindings = [
        install_test_adaptation(tmp_path, item, "references/shared.md", "merge")
        for item in (a, b)
    ]
    receipt_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "byte-integrity-controlled-adaptation",
                "destination": "references/shared.md",
                "output_sha256": hashlib.sha256(b"merged output").hexdigest(),
                "sources": receipt_sources,
                "bindings": bindings,
            }
        ),
        encoding="utf-8",
    )

    assert "invalid byte-integrity receipt sources" in messages(
        coverage.validate_coverage(
            fixture_inventory(a, b), fixture_matrix(*entries), tmp_path
        )
    )


def test_controlled_adaptation_receipt_requires_authoritative_rule_and_test_binding(tmp_path: Path) -> None:
    item = source("alpha", "same.md", "a" * 64)
    entry = mapping(item, "references/shared.md", "enhance")
    destination = tmp_path / "references/shared.md"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"unrelated output")
    receipt_path = tmp_path / entry["verification"]["receipt"]
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(
        json.dumps(
            {
                "destination": "references/shared.md",
                "output_sha256": hashlib.sha256(b"unrelated output").hexdigest(),
                "sources": entry["verification"]["sources"],
            }
        ),
        encoding="utf-8",
    )
    text = messages(
        coverage.validate_coverage(fixture_inventory(item), fixture_matrix(entry), tmp_path)
    )
    assert "missing controller-owned adaptation rule" in text
    assert "controlled adaptation binding" in text


def test_self_issued_receipt_cannot_forge_controller_binding(tmp_path: Path) -> None:
    item = source("alpha", "same.md", "a" * 64)
    entry = mapping(item, "references/shared.md", "enhance")
    destination = tmp_path / "references/shared.md"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"unrelated output")
    receipt_path = tmp_path / entry["verification"]["receipt"]
    receipt_path.parent.mkdir(parents=True)
    forged = {
        "source": "alpha",
        "relative_path": "same.md",
        "action": "enhance",
        "destination": "references/shared.md",
        "rule_id": "self-issued",
        "evidence_type": "asserted-by-receipt",
        "test_ids": ["tests/test_rule.py::test_fake"],
    }
    receipt_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "byte-integrity-controlled-adaptation",
                "destination": "references/shared.md",
                "output_sha256": hashlib.sha256(b"unrelated output").hexdigest(),
                "sources": entry["verification"]["sources"],
                "bindings": [forged],
            }
        ),
        encoding="utf-8",
    )
    text = messages(coverage.validate_coverage(fixture_inventory(item), fixture_matrix(entry), tmp_path))
    assert "missing controller-owned adaptation rule" in text
    assert "controlled adaptation binding mismatch" in text


def test_unrelated_source_cannot_claim_known_migration_adaptation(tmp_path: Path) -> None:
    item = source("attacker", "unrelated.md", "a" * 64)
    known_destination = "tests/migrated/math-modeling/test_recalc.py"
    entry = mapping(item, known_destination, "enhance")
    text = messages(
        coverage.validate_coverage(
            fixture_inventory(item), fixture_matrix(entry), tmp_path, True
        )
    )
    assert "missing controller-owned adaptation rule" in text


def test_receipts_and_generated_docs_never_claim_semantic_inclusion_proof() -> None:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    rendered = coverage.render_markdown(matrix, inventory).casefold()
    validation = (PROJECT_ROOT / "VALIDATION.md").read_text(encoding="utf-8").casefold()
    for text in (rendered, validation):
        assert not re.search(
            r"receipts?\s+(prove|establish|certify|verify)\s+"
            r"(semantic|语义|integration|inclusion)",
            text,
        )
        assert re.search(r"receipts?[^\n.]{0,120}(byte integrity|字节完整性)", text)
        assert re.search(r"(not|不)[^\n.]{0,80}(semantic|语义)", text)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda matrix: matrix.pop("status"), "matrix top-level fields differ from schema"),
        (lambda matrix: matrix.__setitem__("unexpected", True), "matrix top-level fields differ from schema"),
        (lambda matrix: matrix.__setitem__("schema_version", 2), "unsupported schema_version"),
        (lambda matrix: matrix.__setitem__("status", "complete"), "unsupported matrix status"),
        (lambda matrix: matrix.__setitem__("allowed_actions", ["preserve"]), "allowed_actions does not match verifier"),
        (lambda matrix: matrix.__setitem__("summary", []), "invalid matrix summary"),
    ],
)
def test_rejects_malformed_top_level_schema(mutation, expected: str, tmp_path: Path) -> None:
    item = source("alpha", "a.md", "a" * 64)
    matrix = fixture_matrix(mapping(item, "references/a.md"))
    mutation(matrix)
    assert expected in messages(
        coverage.validate_coverage(fixture_inventory(item), matrix, tmp_path, True)
    )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda entry: entry["verification"].__setitem__("extra", "bypass"), "verification fields differ from schema"),
        (lambda entry: entry["verification"].pop("sources"), "verification fields differ from schema"),
        (lambda entry: entry["verification"].__setitem__("sources", "not-a-list"), "invalid verification sources"),
        (lambda entry: entry["verification"]["sources"][0].__setitem__("extra", True), "verification source fields differ from schema"),
    ],
)
def test_rejects_malformed_nested_verification_schema(mutation, expected: str, tmp_path: Path) -> None:
    item = source("alpha", "a.md", "a" * 64)
    entry = mapping(item, "references/a.md")
    mutation(entry)
    assert expected in messages(
        coverage.validate_coverage(fixture_inventory(item), fixture_matrix(entry), tmp_path, True)
    )


def test_fake_long_merge_prose_cannot_bypass_structured_traceability(tmp_path: Path) -> None:
    a = source("alpha", "same.md", "a" * 64)
    b = source("beta", "same.md", "b" * 64)
    entries = [mapping(a, "references/shared.md", "merge"), mapping(b, "references/shared.md", "merge")]
    for entry in entries:
        entry["integrity_note"] = "x" * 100
        entry["verification"]["method"] = "y" * 100
        entry["verification"]["sources"] = [entry["verification"]["sources"][0]]
    text = messages(
        coverage.validate_coverage(fixture_inventory(a, b), fixture_matrix(*entries), tmp_path, True)
    )
    assert "different source hashes share destination" in text
    assert "structured merge traceability" in text


def test_rejects_stale_inventory_fingerprint_and_stale_generated_markdown(tmp_path: Path) -> None:
    item = source("alpha", "a.md", "a" * 64)
    inventory = fixture_inventory(item)
    matrix = fixture_matrix(mapping(item, "references/a.md"))
    matrix["inventory_sha256"] = "stale"
    assert "stale matrix inventory_sha256" in messages(
        coverage.validate_coverage(inventory, matrix, tmp_path, True, inventory_bytes=b"current")
    )

    matrix["inventory_sha256"] = coverage.sha256_bytes(b"current")
    markdown = coverage.render_markdown(matrix, inventory)
    assert markdown == coverage.render_markdown(matrix, inventory)
    assert coverage.check_markdown_freshness(markdown, matrix, inventory) == []
    assert "stale coverage-matrix.md" in messages(
        coverage.check_markdown_freshness(markdown + "changed", matrix, inventory)
    )


def test_seed_routes_tool_sources_to_only_the_designed_tool_families() -> None:
    digest = "a" * 64
    paper = source("alpha", "tools/paper_search/SKILL.md", digest, "instruction")
    readme = source("alpha", "tools/README.md", digest)
    updater = source("alpha", "tools/update_star_history.py", digest, "script")

    assert coverage.planned_destination(paper) == "tools/paper-search/SKILL.md"
    assert coverage.planned_destination(readme) == "references/provenance/legacy/alpha/tools-readme.md"
    assert coverage.planned_destination(updater) == "scripts/alpha/update_star_history.py"


def test_checked_in_matrix_is_complete_deterministic_and_planning_valid() -> None:
    inventory_bytes = INVENTORY_PATH.read_bytes()
    inventory = json.loads(inventory_bytes)
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    assert len(matrix["mappings"]) == len(inventory["files"]) == 416
    generated = coverage.build_seed_matrix(inventory, inventory_bytes)
    assert generated["status"] == "migration-planning"
    generated["status"] = matrix["status"]
    assert matrix == generated
    assert matrix["managed_destinations"] == [
        "SKILL.md",
        "agents",
        "assets",
        "references",
        "scripts",
        "tests",
        "tools",
    ]
    assert {
        "references/roles/modeler.md",
        "references/roles/programmer.md",
        "references/roles/writer.md",
        "references/workflow/deliverables.md",
        "references/workflow/step-review.md",
    } <= {item["destination"] for item in matrix["mappings"]}
    assert coverage.validate_coverage(
        inventory,
        matrix,
        PROJECT_ROOT,
        allow_missing_destinations=True,
        inventory_bytes=inventory_bytes,
    ) == []
    assert MARKDOWN_PATH.read_text(encoding="utf-8") == coverage.render_markdown(matrix, inventory)


def test_seed_generation_defaults_to_planning_and_never_auto_integrates() -> None:
    inventory_bytes = INVENTORY_PATH.read_bytes()
    inventory = json.loads(inventory_bytes)
    assert coverage.build_seed_matrix(inventory, inventory_bytes)["status"] == "migration-planning"


def test_write_seed_failure_does_not_replace_existing_matrix(tmp_path: Path, monkeypatch) -> None:
    inventory_path = tmp_path / "inventory.json"
    matrix_path = tmp_path / "matrix.json"
    markdown_path = tmp_path / "matrix.md"
    inventory_path.write_text(json.dumps(fixture_inventory()), encoding="utf-8")
    matrix_path.write_text('{"status":"sentinel"}', encoding="utf-8")
    markdown_path.write_text("sentinel markdown", encoding="utf-8")
    monkeypatch.setattr(coverage, "INVENTORY_PATH", inventory_path)
    monkeypatch.setattr(coverage, "MATRIX_PATH", matrix_path)
    monkeypatch.setattr(coverage, "MARKDOWN_PATH", markdown_path)
    monkeypatch.setattr(coverage, "build_seed_matrix", lambda *_: {"invalid": True})
    monkeypatch.setattr(coverage, "write_root_audits", lambda *_: None)
    with pytest.raises(ValueError, match="refusing to write invalid seed matrix"):
        coverage.write_seed()
    assert matrix_path.read_text(encoding="utf-8") == '{"status":"sentinel"}'
    assert markdown_path.read_text(encoding="utf-8") == "sentinel markdown"


def test_write_seed_replaces_integrated_status_with_planning(tmp_path: Path, monkeypatch) -> None:
    inventory_path = tmp_path / "inventory.json"
    matrix_path = tmp_path / "matrix.json"
    markdown_path = tmp_path / "matrix.md"
    inventory_path.write_text(json.dumps(fixture_inventory()), encoding="utf-8")
    matrix_path.write_text(json.dumps(fixture_matrix()), encoding="utf-8")
    monkeypatch.setattr(coverage, "INVENTORY_PATH", inventory_path)
    monkeypatch.setattr(coverage, "MATRIX_PATH", matrix_path)
    monkeypatch.setattr(coverage, "MARKDOWN_PATH", markdown_path)
    monkeypatch.setattr(coverage, "write_root_audits", lambda *_: None)
    monkeypatch.setattr(coverage, "write_existing_integrity_receipts", lambda *_: None)
    coverage.write_seed()
    assert json.loads(matrix_path.read_text(encoding="utf-8"))["status"] == "migration-planning"
    assert "migration-planning" in markdown_path.read_text(encoding="utf-8")


def test_finalize_refuses_status_switch_when_strict_validation_fails(tmp_path: Path, monkeypatch) -> None:
    inventory_path = tmp_path / "inventory.json"
    matrix_path = tmp_path / "matrix.json"
    markdown_path = tmp_path / "matrix.md"
    inventory_path.write_text(json.dumps(fixture_inventory()), encoding="utf-8")
    planning_matrix = fixture_matrix()
    planning_matrix["status"] = "migration-planning"
    matrix_path.write_text(json.dumps(planning_matrix), encoding="utf-8")
    markdown_path.write_text("sentinel markdown", encoding="utf-8")
    monkeypatch.setattr(coverage, "INVENTORY_PATH", inventory_path)
    monkeypatch.setattr(coverage, "MATRIX_PATH", matrix_path)
    monkeypatch.setattr(coverage, "MARKDOWN_PATH", markdown_path)
    monkeypatch.setattr(coverage, "validate_coverage", lambda *args, **kwargs: ["blocked"])
    with pytest.raises(ValueError, match="strict finalization failed"):
        coverage.finalize_matrix()
    assert json.loads(matrix_path.read_text(encoding="utf-8"))["status"] == "migration-planning"
    assert markdown_path.read_text(encoding="utf-8") == "sentinel markdown"


def test_finalize_runs_nonstatus_and_final_strict_checks_before_write(tmp_path: Path, monkeypatch) -> None:
    inventory_path = tmp_path / "inventory.json"
    matrix_path = tmp_path / "matrix.json"
    markdown_path = tmp_path / "matrix.md"
    inventory_path.write_text(json.dumps(fixture_inventory()), encoding="utf-8")
    planning = fixture_matrix()
    planning["status"] = "migration-planning"
    matrix_path.write_text(json.dumps(planning), encoding="utf-8")
    markdown_path.write_text("planning", encoding="utf-8")
    monkeypatch.setattr(coverage, "INVENTORY_PATH", inventory_path)
    monkeypatch.setattr(coverage, "MATRIX_PATH", matrix_path)
    monkeypatch.setattr(coverage, "MARKDOWN_PATH", markdown_path)
    calls = []

    def validate(_inventory, candidate, _root, **options):
        calls.append((candidate["status"], options.get("require_integrated_status")))
        return []

    monkeypatch.setattr(coverage, "validate_coverage", validate)
    coverage.finalize_matrix()
    assert calls == [("migration-planning", False), ("integrated", True)]
    assert json.loads(matrix_path.read_text(encoding="utf-8"))["status"] == "integrated"


def test_root_skill_sources_require_distributed_audits_not_entry_receipt() -> None:
    inventory_bytes = INVENTORY_PATH.read_bytes()
    inventory = json.loads(inventory_bytes)
    matrix = coverage.build_seed_matrix(inventory, inventory_bytes)
    root_skills = {
        entry["source"]: entry
        for entry in matrix["mappings"]
        if entry["relative_path"].casefold() == "skill.md"
    }
    expected = {
        source: f"references/provenance/root-audits/{source}-skill.json"
        for source in ("cumcm-c-problem", "cumcm-step-review", "math-modeling")
    }
    assert set(root_skills) == set(expected)
    for source, destination in expected.items():
        entry = root_skills[source]
        assert entry["destination"] == destination
        assert entry["action"] == "enhance"
        assert entry["verification"]["audit"] == destination
        assert entry["verification"]["receipt"] is None
        assert "deterministic chunk audit" in entry["integrity_note"]
    assert not any(
        entry["destination"] == "SKILL.md"
        for entry in root_skills.values()
    )


def test_cli_planning_and_strict_both_succeed_after_full_migration() -> None:
    planning = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--allow-missing-destinations"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert planning.returncode == 0, planning.stdout + planning.stderr
    assert "coverage valid in planning mode (integrated matrix)" in planning.stdout

    strict = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert strict.returncode == 0, strict.stdout + strict.stderr
    assert "coverage valid in strict mode" in strict.stdout


def test_strict_requires_integrated_matrix_but_planning_accepts_both_states(tmp_path: Path) -> None:
    item = source("alpha", "a.md", "a" * 64)
    matrix = fixture_matrix(mapping(item, "references/a.md"))
    matrix["status"] = "migration-planning"
    assert "strict mode requires integrated matrix status" in messages(
        coverage.validate_coverage(fixture_inventory(item), matrix, tmp_path)
    )
    assert coverage.validate_coverage(
        fixture_inventory(item), matrix, tmp_path, allow_missing_destinations=True
    ) == []
    matrix["status"] = "integrated"
    assert coverage.validate_coverage(
        fixture_inventory(item), matrix, tmp_path, allow_missing_destinations=True
    ) == []


def test_root_audit_rejects_invalid_json_and_wrong_source_hash(tmp_path: Path) -> None:
    source_path = tmp_path / "legacy.md"
    source_path.write_text("---\nname: legacy\n---\n# First\nbody\n", encoding="utf-8")
    item = source("math-modeling", "SKILL.md", hashlib.sha256(source_path.read_bytes()).hexdigest(), "instruction")
    item["absolute_path"] = str(source_path)
    prepared, audit_path = write_root_audit(tmp_path, item)
    matrix = fixture_matrix(prepared["entry"])
    audit_path.write_text("not json", encoding="utf-8")
    assert "invalid root audit JSON" in messages(coverage.validate_coverage(fixture_inventory(item), matrix, tmp_path))
    audit_path.write_text(json.dumps(prepared["audit"]), encoding="utf-8")
    prepared["audit"]["source"]["sha256"] = "0" * 64
    audit_path.write_text(json.dumps(prepared["audit"]), encoding="utf-8")
    assert "root audit source hash mismatch" in messages(coverage.validate_coverage(fixture_inventory(item), matrix, tmp_path))


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda audit: audit["chunks"].pop(), "missing root audit chunks"),
        (lambda audit: audit["chunks"][0].__setitem__("sha256", "0" * 64), "root audit chunk hash mismatch"),
        (lambda audit: audit["chunks"].append(copy.deepcopy(audit["chunks"][0])), "duplicate root audit chunk"),
        (lambda audit: audit["chunks"].append({**copy.deepcopy(audit["chunks"][0]), "id": "extra"}), "extra root audit chunks"),
        (lambda audit: audit["chunks"][0]["destinations"][0].__setitem__("path", "references/missing.md"), "missing root audit destination"),
        (lambda audit: audit["chunks"][0]["destinations"][0].__setitem__("anchor", "absent anchor"), "missing root audit anchor"),
        (lambda audit: audit["chunks"][0]["destinations"][0].__setitem__("evidence_terms", ["absent evidence"]), "missing root audit section evidence"),
    ],
)
def test_root_audit_rejects_incomplete_or_unverifiable_chunks(tmp_path: Path, mutate, expected: str) -> None:
    source_path = tmp_path / "legacy.md"
    source_path.write_text("---\nname: legacy\n---\n# First\nbody\n## Second\nmore\n", encoding="utf-8")
    item = source("math-modeling", "SKILL.md", hashlib.sha256(source_path.read_bytes()).hexdigest(), "instruction")
    item["absolute_path"] = str(source_path)
    prepared, audit_path = write_root_audit(tmp_path, item)
    mutate(prepared["audit"])
    audit_path.write_text(json.dumps(prepared["audit"]), encoding="utf-8")
    assert expected in messages(coverage.validate_coverage(fixture_inventory(item), fixture_matrix(prepared["entry"]), tmp_path))


def test_pending_root_audit_is_allowed_only_in_planning_mode(tmp_path: Path) -> None:
    source_path = tmp_path / "legacy.md"
    source_path.write_text("# First\nbody\n", encoding="utf-8")
    item = source("math-modeling", "SKILL.md", hashlib.sha256(source_path.read_bytes()).hexdigest(), "instruction")
    item["absolute_path"] = str(source_path)
    prepared, audit_path = write_root_audit(tmp_path, item, status="pending")
    for chunk in prepared["audit"]["chunks"]:
        chunk["disposition"] = "pending"
    audit_path.write_text(json.dumps(prepared["audit"]), encoding="utf-8")
    matrix = fixture_matrix(prepared["entry"])
    assert "pending root audit status is forbidden in strict mode" in messages(
        coverage.validate_coverage(fixture_inventory(item), matrix, tmp_path)
    )
    matrix["status"] = "migration-planning"
    assert coverage.validate_coverage(
        fixture_inventory(item), matrix, tmp_path, allow_missing_destinations=True
    ) == []


def test_root_audit_cannot_forge_all_chunks_to_unrelated_tiny_heading(tmp_path: Path) -> None:
    item, audit, audit_path = copied_checked_in_root_audit(tmp_path)
    unrelated = tmp_path / "unrelated.md"
    unrelated.write_text("# a\n\na\n", encoding="utf-8")
    forged = {"path": "unrelated.md", "anchor": "a", "evidence_terms": ["a"]}
    for chunk in audit["chunks"]:
        chunk["destinations"] = [copy.deepcopy(forged)]
    audit_path.write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
    text = messages(coverage.validate_root_audit(audit_path, item, tmp_path, planning=False))
    assert "root audit authoritative route mismatch" in text
    assert "generic root audit anchor" in text
    assert "generic root audit evidence" in text


def test_root_audit_rejects_route_table_mismatch(tmp_path: Path) -> None:
    item, audit, audit_path = copied_checked_in_root_audit(tmp_path)
    audit["chunks"][0]["destinations"][0]["path"] = "references/modeling/model-selection.md"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
    assert "root audit authoritative route mismatch" in messages(
        coverage.validate_root_audit(audit_path, item, tmp_path, planning=False)
    )


def test_root_audit_evidence_must_be_inside_the_anchored_heading_section(tmp_path: Path) -> None:
    item, audit, audit_path = copied_checked_in_root_audit(tmp_path)
    routed = audit["chunks"][0]["destinations"][0]
    destination = tmp_path / routed["path"]
    evidence = routed["evidence_terms"][0]
    content = destination.read_text(encoding="utf-8")
    content = content.replace(evidence, "removed-from-section")
    destination.write_text(content + f"\n# Unrelated later section\n\n{evidence}\n", encoding="utf-8")
    assert "missing root audit section evidence" in messages(
        coverage.validate_root_audit(audit_path, item, tmp_path, planning=False)
    )


def test_root_audit_rejects_generic_anchor_and_evidence_even_when_route_is_mutated(tmp_path: Path) -> None:
    item, audit, audit_path = copied_checked_in_root_audit(tmp_path)
    audit["chunks"][0]["destinations"] = [
        {"path": "SKILL.md", "anchor": "#", "evidence_terms": ["a"]}
    ]
    audit_path.write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
    text = messages(coverage.validate_root_audit(audit_path, item, tmp_path, planning=False))
    assert "generic root audit anchor" in text
    assert "generic root audit evidence" in text


def test_root_audit_rejects_duplicate_heading_ambiguity(tmp_path: Path) -> None:
    item, audit, audit_path = copied_checked_in_root_audit(tmp_path)
    routed = audit["chunks"][0]["destinations"][0]
    destination = tmp_path / routed["path"]
    content = destination.read_text(encoding="utf-8")
    destination.write_text(f"# {routed['anchor']}\n\nshadow\n\n" + content, encoding="utf-8")
    assert "ambiguous root audit heading" in messages(
        coverage.validate_root_audit(audit_path, item, tmp_path, planning=False)
    )


def test_root_audit_source_location_can_be_portably_overridden(tmp_path: Path) -> None:
    item, audit, audit_path = copied_checked_in_root_audit(tmp_path)
    portable_root = tmp_path / "portable-math-modeling"
    portable_root.mkdir()
    shutil.copyfile(Path(item["absolute_path"]), portable_root / "SKILL.md")
    item["absolute_path"] = str(tmp_path / "missing-machine-path" / "SKILL.md")
    assert coverage.validate_root_audit(
        audit_path,
        item,
        tmp_path,
        planning=False,
        source_root_overrides={"math-modeling": portable_root},
    ) == []
