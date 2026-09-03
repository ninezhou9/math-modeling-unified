#!/usr/bin/env python3
"""Check internal Markdown links in the unified skill."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_MARKDOWN_ENTRIES = ("SKILL.md",)
STALE_RUNTIME_PATTERNS = (
    r"[A-Za-z]:\\Users\\[^\n`]+\\\.codex\\skills",
    r"~[/\\]\.codex[/\\]skills",
    r"<SKILL_ROOT>[/\\]references[/\\]Subagent调度\.md",
    r"<SKILL_ROOT>[/\\]tools[/\\]paper_search",
    r"references[/\\]绘图参考[/\\]",
)


def strip_code_and_math(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]*`", "", text)
    text = re.sub(r"\$\$[\s\S]*?\$\$", "", text)
    text = re.sub(r"\$[^$\n]*?\$", "", text)
    return text


def extract_links(markdown_text: str) -> list[str]:
    cleaned = strip_code_and_math(markdown_text)
    links = re.findall(r"\[(?:[^\]]*)\]\(([^)]+)\)", cleaned)
    filtered = []
    for link in links:
        link = link.strip()
        if (
            link.startswith("http://")
            or link.startswith("https://")
            or link.startswith("mailto:")
            or link.startswith("#")
        ):
            continue
        target = link.split("#", 1)[0].strip()
        if target:
            filtered.append(unquote(target))
    return filtered


def markdown_link_closure(
    skill_root: Path, entries: tuple[str, ...] = CANONICAL_MARKDOWN_ENTRIES
) -> set[str]:
    """Return the transitive local-Markdown closure from controller entrypoints."""
    root = skill_root.resolve()
    pending = list(entries)
    reached: set[str] = set()
    while pending:
        relative = pending.pop()
        if relative in reached:
            continue
        path = root / relative
        if not path.is_file():
            continue
        reached.add(relative)
        try:
            links = extract_links(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            continue
        for link in links:
            target = (path.parent / link).resolve()
            try:
                target_relative = target.relative_to(root).as_posix()
            except ValueError:
                continue
            if target_relative.endswith(".md") and target_relative not in reached:
                pending.append(target_relative)
    return reached


def check_reachable_runtime_paths(skill_root: Path) -> list[str]:
    """Reject legacy runtime paths in every operationally reachable Markdown file."""
    errors: list[str] = []
    for relative in sorted(markdown_link_closure(skill_root)):
        path = skill_root / Path(relative)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            errors.append(f"failed to read reachable Markdown {relative}: {exc}")
            continue
        for line_number, line in enumerate(lines, start=1):
            source_history = (
                "/workspace/" in f"/{relative}"
                and any(label in line for label in ("来源：", "原 Skill 路径："))
            )
            if source_history:
                continue
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in STALE_RUNTIME_PATTERNS):
                errors.append(f"stale runtime path in {relative}:{line_number}")
    return errors


def check_links(skill_root: Path) -> list[str]:
    errors = []
    for md_path in sorted(skill_root.rglob("*.md")):
        if "__pycache__" in md_path.parts:
            continue
        if "provenance" in md_path.parts and "legacy" in md_path.parts:
            continue

        rel_md = md_path.relative_to(skill_root).as_posix()
        try:
            content = md_path.read_text(encoding="utf-8")
        except Exception as exc:
            errors.append(f"failed to read {rel_md}: {exc}")
            continue

        links = extract_links(content)
        for link in links:
            try:
                target_path = (md_path.parent / link).resolve()
            except Exception as exc:
                errors.append(f"invalid link {link!r} in {rel_md}: {exc}")
                continue

            # Check if target escapes skill_root
            try:
                target_path.relative_to(skill_root)
            except ValueError:
                errors.append(f"link {link!r} in {rel_md} escapes skill root: {target_path}")
                continue

            if not target_path.exists():
                errors.append(f"broken link {link!r} in {rel_md} -> {target_path.as_posix()} (missing)")
    return errors


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    errors = check_links(ROOT)
    errors.extend(check_reachable_runtime_paths(ROOT))
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1
    print("all internal Markdown links are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
