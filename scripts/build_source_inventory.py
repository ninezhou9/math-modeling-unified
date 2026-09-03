#!/usr/bin/env python3
"""Create a deterministic inventory of the three source skills and five notes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping, Sequence


DEFAULT_SOURCE_ROOTS = {
    "cumcm-step-review": Path(r"C:\Users\qwerq\.codex\skills\cumcm-step-review"),
    "cumcm-c-problem": Path(r"C:\Users\qwerq\.codex\skills\cumcm-c-problem-lfs"),
    "math-modeling": Path(r"C:\Users\qwerq\.codex\skills\math-modeling"),
}
DEFAULT_WORKSPACE_ROOT = Path(r"C:\Users\qwerq\Desktop\skill")
DEFAULT_WORKSPACE_MARKDOWN = (
    "数学建模算法库_整合版.md",
    "优秀论文特点与Skill补充建议.md",
    "math-modeling-skill-详细总结.md",
    "CUMCM写作证据门禁补充.md",
    "CUMCM-Step-Review-Skill总结.md",
)
KINDS = ("asset", "instruction", "metadata", "reference", "script", "test")

INSTRUCTION_NAMES = {"agents.md", "claude.md", "gemini.md", "skill.md"}
SCRIPT_SUFFIXES = {".bat", ".cmd", ".js", ".jl", ".m", ".ps1", ".py", ".r", ".sh", ".ts"}
ASSET_SUFFIXES = {
    ".bmp", ".csv", ".doc", ".docx", ".gif", ".ico", ".jpeg", ".jpg",
    ".mp3", ".mp4", ".pdf", ".png", ".svg", ".tsv", ".wav", ".webp",
    ".xls", ".xlsx", ".zip",
}
METADATA_SUFFIXES = {
    ".ini", ".json", ".lock", ".toml", ".xml", ".xsd", ".yaml", ".yml"
}
METADATA_NAMES = {
    ".gitignore", "license", "license.md", "manifest", "manifest.json",
    "package.json", "pyproject.toml", "requirements.txt",
}


def _sort_key(*values: str) -> tuple[str, ...]:
    return tuple(value.casefold() for value in values) + values


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_file(relative_path: str) -> str:
    path = PurePosixPath(relative_path)
    name = path.name.casefold()
    directories = {part.casefold() for part in path.parts[:-1]}
    suffix = path.suffix.casefold()

    if name in INSTRUCTION_NAMES:
        return "instruction"
    if directories & {"test", "tests"} or name.startswith("test_"):
        return "test"
    if suffix in SCRIPT_SUFFIXES:
        return "script"
    if directories & {"asset", "assets", "imgs", "images"} or suffix in ASSET_SUFFIXES:
        return "asset"
    if name in METADATA_NAMES or suffix in METADATA_SUFFIXES:
        return "metadata"
    return "reference"


def _is_generated(relative_path: str) -> bool:
    path = PurePosixPath(relative_path)
    return (
        any(part.casefold() == "__pycache__" for part in path.parts)
        or path.suffix.casefold() in {".pyc", ".pyo"}
    )


def _file_record(source: str, root: Path, path: Path) -> dict[str, object]:
    relative_path = path.relative_to(root).as_posix()
    return {
        "source": source,
        "relative_path": relative_path,
        "absolute_path": str(path.resolve()),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
        "kind": classify_file(relative_path),
    }


def _scan_root(
    source: str, root: Path
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    files: list[dict[str, object]] = []
    excluded: list[dict[str, str]] = []
    paths = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: _sort_key(path.relative_to(root).as_posix()),
    )
    for path in paths:
        relative_path = path.relative_to(root).as_posix()
        if _is_generated(relative_path):
            excluded.append(
                {
                    "source": source,
                    "relative_path": relative_path,
                    "absolute_path": str(path.resolve()),
                    "reason": "generated Python bytecode",
                }
            )
        else:
            files.append(_file_record(source, root, path))
    return files, excluded


def _duplicate_groups(files: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    hashes: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in files:
        hashes[str(item["sha256"])].append(
            {
                "source": str(item["source"]),
                "relative_path": str(item["relative_path"]),
                "absolute_path": str(item["absolute_path"]),
            }
        )

    groups: list[dict[str, object]] = []
    for digest, members in hashes.items():
        if len({member["source"] for member in members}) < 2:
            continue
        members.sort(
            key=lambda item: _sort_key(
                item["source"], item["relative_path"], item["absolute_path"]
            )
        )
        groups.append({"sha256": digest, "member_count": len(members), "members": members})
    groups.sort(key=lambda group: str(group["sha256"]))
    return groups


def _relative_path_conflicts(
    files: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    relative_paths: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in files:
        relative_path = str(item["relative_path"])
        relative_paths[relative_path.casefold()].append(
            {
                "source": str(item["source"]),
                "relative_path": relative_path,
                "absolute_path": str(item["absolute_path"]),
                "sha256": str(item["sha256"]),
            }
        )

    conflicts: list[dict[str, object]] = []
    for collision_key, members in relative_paths.items():
        distinct_hashes = {member["sha256"] for member in members}
        if len(distinct_hashes) < 2:
            continue
        members.sort(
            key=lambda item: _sort_key(item["source"], item["absolute_path"], item["sha256"])
        )
        conflicts.append(
            {
                "relative_path": collision_key,
                "hash_count": len(distinct_hashes),
                "members": members,
            }
        )
    conflicts.sort(key=lambda group: _sort_key(str(group["relative_path"])))
    return conflicts


def build_inventory(
    source_roots: Mapping[str, Path | str] | None = None,
    source_root_overrides: Mapping[str, Path | str] | None = None,
    workspace_root: Path | str | None = None,
    workspace_markdown: Sequence[str] | None = None,
) -> dict[str, object]:
    """Return the complete inventory without writing any output file."""
    configured_roots = dict(DEFAULT_SOURCE_ROOTS if source_roots is None else source_roots)
    if source_root_overrides:
        unknown = set(source_root_overrides) - set(configured_roots)
        if unknown:
            raise KeyError(f"Cannot override unknown source roots: {', '.join(sorted(unknown))}")
        configured_roots.update(source_root_overrides)
    roots = {name: Path(path).resolve() for name, path in configured_roots.items()}
    workspace = Path(DEFAULT_WORKSPACE_ROOT if workspace_root is None else workspace_root).resolve()
    markdown_names = (
        DEFAULT_WORKSPACE_MARKDOWN if workspace_markdown is None else tuple(workspace_markdown)
    )

    files: list[dict[str, object]] = []
    excluded: list[dict[str, str]] = []
    for source in sorted(roots, key=lambda value: (value.casefold(), value)):
        root = roots[source]
        if not root.is_dir():
            raise FileNotFoundError(f"Source root does not exist: {root}")
        source_files, source_excluded = _scan_root(source, root)
        files.extend(source_files)
        excluded.extend(source_excluded)

    for name in markdown_names:
        path = workspace / name
        if not path.is_file():
            raise FileNotFoundError(f"Workspace Markdown input does not exist: {path}")
        files.append(_file_record("workspace-markdown", workspace, path))

    files.sort(key=lambda item: _sort_key(str(item["source"]), str(item["relative_path"])))
    excluded.sort(key=lambda item: _sort_key(item["source"], item["relative_path"]))
    category_counts = Counter(str(item["kind"]) for item in files)

    return {
        "source_roots": {name: str(roots[name]) for name in sorted(roots)},
        "workspace_root": str(workspace),
        "workspace_markdown_inputs": list(markdown_names),
        "files": files,
        "excluded_generated": excluded,
        "exact_duplicate_groups": _duplicate_groups(files),
        "same_relative_path_conflicts": _relative_path_conflicts(files),
        "category_counts": {kind: category_counts[kind] for kind in KINDS},
    }


def write_inventory(inventory: Mapping[str, object], output: Path | str) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(inventory, ensure_ascii=False, indent=2) + "\n"
    output_path.write_bytes(serialized.encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="inventory JSON output path")
    parser.add_argument(
        "--source-root",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="portable source root override; repeat once per source",
    )
    parser.add_argument(
        "--source-root-map",
        type=Path,
        help="JSON file containing the complete portable NAME-to-PATH source root map",
    )
    parser.add_argument(
        "--source-root-override",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="override one entry in the selected/default source root map; repeat as needed",
    )
    parser.add_argument("--workspace-root", type=Path, help="portable workspace-note root")
    parser.add_argument(
        "--workspace-markdown",
        action="append",
        default=[],
        metavar="FILE.md",
        help="workspace Markdown input relative to --workspace-root; repeat as needed",
    )
    arguments = parser.parse_args()
    environment_roots = os.environ.get("MATH_MODELING_SOURCE_ROOTS_JSON")
    configured_roots: Mapping[str, Path | str] | None = None
    if arguments.source_root_map:
        value = json.loads(arguments.source_root_map.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not all(
            isinstance(name, str) and isinstance(path, str) for name, path in value.items()
        ):
            parser.error("--source-root-map must contain a JSON object of string paths")
        configured_roots = value
    if environment_roots:
        value = json.loads(environment_roots)
        if not isinstance(value, dict) or not all(
            isinstance(name, str) and isinstance(path, str) for name, path in value.items()
        ):
            parser.error("MATH_MODELING_SOURCE_ROOTS_JSON must be a JSON object of string paths")
        configured_roots = value
    if arguments.source_root:
        parsed_roots: dict[str, str] = {}
        for value in arguments.source_root:
            if "=" not in value:
                parser.error("--source-root must use NAME=PATH")
            name, path = value.split("=", 1)
            if not name or not path or name in parsed_roots:
                parser.error("--source-root names and paths must be nonempty and unique")
            parsed_roots[name] = path
        configured_roots = parsed_roots

    parsed_overrides: dict[str, str] = {}
    for value in arguments.source_root_override:
        if "=" not in value:
            parser.error("--source-root-override must use NAME=PATH")
        name, path = value.split("=", 1)
        if not name or not path or name in parsed_overrides:
            parser.error("--source-root-override names and paths must be nonempty and unique")
        parsed_overrides[name] = path

    workspace_root = arguments.workspace_root or os.environ.get("MATH_MODELING_WORKSPACE_ROOT")
    markdown_inputs: Sequence[str] | None = None
    environment_markdown = os.environ.get("MATH_MODELING_WORKSPACE_MARKDOWN_JSON")
    if environment_markdown:
        value = json.loads(environment_markdown)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            parser.error("MATH_MODELING_WORKSPACE_MARKDOWN_JSON must be a JSON string list")
        markdown_inputs = value
    if arguments.workspace_markdown:
        markdown_inputs = arguments.workspace_markdown

    inventory = build_inventory(
        source_roots=configured_roots,
        source_root_overrides=parsed_overrides,
        workspace_root=workspace_root,
        workspace_markdown=markdown_inputs,
    )
    write_inventory(inventory, arguments.output)
    print(f"Wrote {len(inventory['files'])} files to {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
