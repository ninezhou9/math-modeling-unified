#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit figure/table usage in a CUMCM C paper TeX file.")
    ap.add_argument("tex")
    args = ap.parse_args()
    path = Path(args.tex)
    text = path.read_text(encoding="utf-8", errors="ignore")

    figs = re.findall(r"\\begin\{figure\}.*?\\end\{figure\}", text, re.S)
    tabs = re.findall(r"\\begin\{table\}.*?\\end\{table\}", text, re.S)
    print(f"figures: {len(figs)}")
    print(f"tables:  {len(tabs)}")

    bad = 0
    for i, block in enumerate(figs, 1):
        cap = re.search(r"\\caption(?:\[[^]]*\])?\{([^}]*)\}", block, re.S)
        lab = re.search(r"\\label\{([^}]*)\}", block)
        if not cap:
            print(f"WARN figure {i}: missing caption"); bad += 1
        if not lab:
            print(f"WARN figure {i}: missing label"); bad += 1
        names = re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", block)
        for name in names:
            if re.fullmatch(r"\d+", Path(name).stem):
                print(f"WARN figure {i}: non-semantic filename {name}")

    for i, block in enumerate(tabs, 1):
        if "\\toprule" not in block or "\\midrule" not in block or "\\bottomrule" not in block:
            print(f"WARN table {i}: not a standard booktabs three-line table")
            bad += 1

    # crude anti-pattern checks
    if "rainbow" in text.lower() or "jet" in text.lower():
        print("WARN: rainbow/jet colormap keyword found; prefer restrained perceptual palettes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
