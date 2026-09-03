#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
import shutil
import subprocess
from pathlib import Path

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"


def emit(level: str, msg: str) -> None:
    print(f"[{level}] {msg}")


def run(cmd, cwd: Path):
    return subprocess.run(cmd, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def keyword_count(tex: str):
    m = re.search(r"\\keywords\s*\{([^}]*)\}", tex, re.S)
    if not m:
        return None
    s = m.group(1).strip()
    parts = re.split(r"\\quad|[，,；;]+", s)
    return len([x for x in parts if x.strip()])


def page_text(pdf: Path, page: int):
    if not shutil.which("pdftotext"):
        return None
    r = subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(pdf), "-"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return r.stdout if r.returncode == 0 else None


def pdf_pages(pdf: Path):
    if not shutil.which("pdfinfo"):
        return None
    r = subprocess.run(["pdfinfo", str(pdf)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    m = re.search(r"^Pages:\s+(\d+)", r.stdout, re.M)
    return int(m.group(1)) if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit CUMCM C-problem project structure and PDF presentation.")
    ap.add_argument("project")
    ap.add_argument("--compile", action="store_true", help="Compile with XeLaTeX before PDF checks")
    ap.add_argument("--min-pages", type=int, default=25)
    ap.add_argument("--max-pages", type=int, default=28)
    args = ap.parse_args()

    root = Path(args.project).resolve()
    texfile = root / "example.tex"
    failures = 0

    for name in ["figures", "code"]:
        p = root / name
        if p.is_dir(): emit(PASS, f"{name}/ exists")
        else: emit(FAIL, f"missing {name}/"); failures += 1

    if not texfile.exists():
        emit(FAIL, "missing example.tex")
        return 2
    tex = texfile.read_text(encoding="utf-8", errors="ignore")

    checks = [
        (r"\\documentclass(?:\[[^]]*\])?\{cumcmthesis\}", "uses cumcmthesis class"),
        (r"\\tihao\{C\}", "problem type is C"),
        (r"\\begin\{abstract\}", "abstract exists"),
        (r"\\keywords\{", "keywords exist"),
        (r"\\section\{问题重述\}", "problem restatement section exists"),
        (r"\\section\{问题分析\}", "problem analysis section exists"),
        (r"\\section\{模型假设\}", "assumptions section exists"),
        (r"\\section\{符号说明\}", "symbol section exists"),
        (r"\\begin\{thebibliography\}", "references exist"),
    ]
    for pat, msg in checks:
        if re.search(pat, tex, re.S): emit(PASS, msg)
        else: emit(FAIL, msg); failures += 1

    if "\\tableofcontents" in re.sub(r"(?m)^\s*%.*$", "", tex):
        emit(FAIL, "table of contents is enabled")
        failures += 1
    else:
        emit(PASS, "no table of contents")

    nkw = keyword_count(tex)
    if nkw is None:
        pass
    elif nkw <= 5:
        emit(PASS, f"keyword count = {nkw} (<=5)")
    else:
        emit(FAIL, f"keyword count = {nkw} (>5)")
        failures += 1

    abs_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.S)
    if abs_match:
        if "\\textbf{" in abs_match.group(1):
            emit(PASS, "abstract highlights at least one key model/result with bold")
        else:
            emit(WARN, "abstract has no \\textbf{} highlight")

    if re.search(r"\\end\{abstract\}\s*\\newpage", tex, re.S):
        emit(PASS, "explicit new page after abstract")
    else:
        emit(WARN, "consider \\newpage after abstract to lock problem restatement to page 2")

    has_optimization = bool(re.search(r"\\(?:min|max)|\\text\{s\.t\.\}|\\mathrm\{s\.t\.\}", tex))
    has_summary_model = "\\boxed{" in tex and "\\left\\{" in tex
    if has_optimization and not has_summary_model:
        emit(WARN, "optimization detected but no boxed brace model summary found")
    elif has_summary_model:
        emit(PASS, "boxed model-summary form detected")

    includegraphics = re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", tex)
    emit(PASS, f"figure references in TeX: {len(includegraphics)}")
    captions = len(re.findall(r"\\caption(?:\[[^]]*\])?\{", tex))
    emit(PASS, f"captions in TeX: {captions}")

    if args.compile:
        if not shutil.which("xelatex"):
            emit(WARN, "xelatex not installed; skipped compile")
        elif not (root / "cumcmthesis.cls").exists() and not shutil.which("kpsewhich"):
            emit(WARN, "cumcmthesis.cls not found locally; skipped compile")
        else:
            ok = True
            for _ in range(2):
                r = run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "example.tex"], root)
                if r.returncode != 0:
                    emit(FAIL, "XeLaTeX compile failed")
                    print(r.stdout[-3000:])
                    failures += 1
                    ok = False
                    break
            if ok: emit(PASS, "XeLaTeX compiled twice")

    pdf = root / "example.pdf"
    if pdf.exists():
        p1 = page_text(pdf, 1)
        p2 = page_text(pdf, 2)
        if p1 is not None:
            if "关键词" in p1 or "关键字" in p1:
                emit(PASS, "keywords appear on page 1")
            else:
                emit(WARN, "could not confirm keywords on page 1")
            if "问题重述" in p1:
                emit(FAIL, "problem restatement appears on page 1; abstract page is not isolated")
                failures += 1
            else:
                emit(PASS, "problem restatement does not spill onto page 1")
        if p2 is not None:
            if "问题重述" in p2: emit(PASS, "problem restatement starts by page 2")
            else: emit(WARN, "problem restatement not found on page 2")

        total = pdf_pages(pdf)
        if total:
            appendix_page = None
            if shutil.which("pdftotext"):
                for i in range(1, total + 1):
                    txt = page_text(pdf, i) or ""
                    if re.search(r"(^|\n)\s*附\s*录|附录", txt):
                        appendix_page = i
                        break
            main_pages = appendix_page - 1 if appendix_page else total
            if args.min_pages <= main_pages <= args.max_pages:
                emit(PASS, f"main paper pages = {main_pages} (target {args.min_pages}-{args.max_pages})")
            else:
                emit(WARN, f"main paper pages = {main_pages}; target is {args.min_pages}-{args.max_pages} when official rules allow")

    log = root / "example.log"
    if log.exists():
        s = log.read_text(encoding="utf-8", errors="ignore")
        if "Overfull \\hbox" in s: emit(WARN, "Overfull \\hbox found")
        else: emit(PASS, "no Overfull \\hbox found")
        if re.search(r"undefined references|Reference .* undefined", s, re.I): emit(FAIL, "undefined references found"); failures += 1
        else: emit(PASS, "no undefined-reference warning found")

    if (root / "code").is_dir():
        files = [p for p in (root / "code").rglob("*") if p.is_file()]
        if files: emit(PASS, f"code/ contains {len(files)} file(s)")
        else: emit(WARN, "code/ is empty; final delivery should include complete runnable code")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
