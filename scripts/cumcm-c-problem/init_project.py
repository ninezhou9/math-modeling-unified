#!/usr/bin/env python3
from __future__ import annotations
import argparse
import shutil
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description="Initialize a CUMCM C-problem LaTeX project.")
    p.add_argument("output", help="Output project directory")
    p.add_argument("--class-file", help="Optional path to cumcmthesis.cls")
    args = p.parse_args()

    root = Path(__file__).resolve().parents[1]
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)

    for d in ["figures", "code", "data", "support", "notes"]:
        (out / d).mkdir(exist_ok=True)

    shutil.copy2(root / "assets" / "template" / "paper_skeleton.tex", out / "example.tex")
    shutil.copy2(root / "assets" / "template" / "example-source.tex", out / "notes" / "template_reference.tex")

    if args.class_file:
        cls = Path(args.class_file).resolve()
        if not cls.exists():
            raise SystemExit(f"class file not found: {cls}")
        shutil.copy2(cls, out / "cumcmthesis.cls")

    (out / ".gitignore").write_text(
        "*.aux\n*.log\n*.out\n*.synctex.gz\n*.fls\n*.fdb_latexmk\n*.xdv\n.DS_Store\n__pycache__/\n",
        encoding="utf-8",
    )
    (out / "README.md").write_text(
        "# CUMCM C Project\n\n"
        "- `example.tex`: main paper\n"
        "- `figures/`: final figures used in the paper\n"
        "- `code/`: complete runnable source code\n"
        "- `data/`: self-collected/processed data when allowed\n"
        "- `support/`: large intermediate outputs and required supporting material\n\n"
        "Use XeLaTeX. Keep title+abstract+keywords on page 1; start problem restatement on page 2.\n",
        encoding="utf-8",
    )
    print(f"Initialized: {out}")
    if not (out / "cumcmthesis.cls").exists():
        print("NOTE: cumcmthesis.cls was not bundled. Supply it with --class-file or place it beside example.tex.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
