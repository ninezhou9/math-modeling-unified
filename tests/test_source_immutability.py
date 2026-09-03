import hashlib
import json
from pathlib import Path


BASELINE_PATH = Path(__file__).with_name("source-state-before.json")


class TreeState(dict[str, str]):
    def __init__(self, hashes: dict[str, str], byte_count: int) -> None:
        super().__init__(hashes)
        self.byte_count = byte_count


def tree_state(root: Path) -> TreeState:
    """Map every file below root to its relative path and SHA-256 digest."""
    hashes: dict[str, str] = {}
    byte_count = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if (
            not path.is_file()
            or "__pycache__" in relative.parts
            or path.suffix.casefold() == ".pyc"
        ):
            continue
        content = path.read_bytes()
        hashes[relative.as_posix()] = hashlib.sha256(content).hexdigest()
        byte_count += len(content)
    return TreeState(hashes, byte_count)


def describe_changes(expected: dict[str, str], current: dict[str, str]) -> str:
    added = sorted(current.keys() - expected.keys())
    removed = sorted(expected.keys() - current.keys())
    changed = sorted(
        path
        for path in current.keys() & expected.keys()
        if current[path] != expected[path]
    )
    return "; ".join(
        f"{label} ({len(paths)}): {', '.join(paths) if paths else '-'}"
        for label, paths in (
            ("added", added),
            ("removed", removed),
            ("changed", changed),
        )
    )


def test_tree_state_excludes_python_cache_artifacts(tmp_path: Path) -> None:
    (tmp_path / "kept.py").write_text("kept", encoding="utf-8")
    (tmp_path / "standalone.pyc").write_bytes(b"cache")
    cache_dir = tmp_path / "package" / "__pycache__"
    cache_dir.mkdir(parents=True)
    (cache_dir / "module.cpython-313.pyc").write_bytes(b"cache")

    assert set(tree_state(tmp_path)) == {"kept.py"}


def test_describe_changes_reports_added_removed_and_changed_paths() -> None:
    expected = {"removed.txt": "old", "changed.txt": "old"}
    current = {"added.txt": "new", "changed.txt": "new"}

    assert describe_changes(expected, current) == (
        "added (1): added.txt; removed (1): removed.txt; "
        "changed (1): changed.txt"
    )


def test_installed_source_trees_match_immutable_baseline() -> None:
    assert BASELINE_PATH.is_file(), f"source-state baseline is missing: {BASELINE_PATH}"

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    roots = baseline["roots"]
    expected_hashes = baseline["hashes"]

    assert set(roots) == set(expected_hashes)

    reports: list[str] = []
    differences: list[str] = []
    for name, root_text in roots.items():
        root = Path(root_text)
        assert root.is_dir(), f"source root is missing: {root}"
        current = tree_state(root)
        reports.append(f"{name}: files={len(current)}, bytes={current.byte_count}")
        if current != expected_hashes[name]:
            differences.append(
                f"{name}: {describe_changes(expected_hashes[name], current)}"
            )

    report = "; ".join(reports)
    print(report)
    assert not differences, report + "\n" + "\n".join(differences)
