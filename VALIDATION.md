# Validation Record: `math-modeling-unified`

- **Validation Date**: 2026-09-03
- **Record Status**: **COMPLETE**
- **Installation Ready**: **YES**
- **Coverage Matrix Status**: `integrated`

This record describes the final pre-install workspace state. Provenance, canonical tools, behavioral acceptance, source immutability, links, metadata, and both full test modes passed fresh validation. The user explicitly authorized installation and GitHub publication.

## Completed provenance checks

The following checks were rerun from the `math-modeling-unified` workspace on 2026-09-03. They establish provenance integrity only; they do not establish final tool or behavioral acceptance.

| Check | Fresh command | Recorded result |
|---|---|---|
| Strict provenance coverage | `python scripts/verify_coverage.py` | Exit `0`; 416 mappings and 333 destinations passed byte, controller-binding, regression-ID, and root heading-section checks. Receipts alone prove byte integrity and controlled relocation, not semantic integration. |
| Planning-mode schema coverage | `python scripts/verify_coverage.py --allow-missing-destinations` | Exit `0`; planning mode accepted the final `integrated` matrix. |
| Provenance/routing/inventory regressions | `python -m pytest -q tests/test_coverage.py tests/test_inventory.py tests/test_routing_content.py` | Exit `0`; 121 passed. |
| Full regression suite | `python -m pytest -q -p no:cacheprovider` | Exit `0`; 251 passed. |
| Full regression suite without conftest | `python -m pytest -q --noconftest -p no:cacheprovider` | Exit `0`; 251 passed. |
| Installed-source immutability | `python -m pytest -q tests/test_source_immutability.py` | Exit `0`; 3 passed and the installed source trees matched the recorded baseline. |
| Internal Markdown links/runtime closure | `python scripts/check_internal_links.py` | Exit `0`; all local links resolved and reachable operational Markdown contained no stale runtime path. |
| Skill metadata and UTF-8 | `python -X utf8 C:\Users\qwerq\.codex\skills\.system\skill-creator\scripts\quick_validate.py .` | Exit `0`; `Skill is valid!`. The UTF-8 mode is required on GBK-default Windows shells. |

The root Skill mappings use valid JSON audits under `references/provenance/root-audits/`. Each audit is bound to the exact inventoried source SHA-256, deterministic frontmatter/heading chunks, controller-owned routes, exact unambiguous Markdown headings, and evidence located inside each bounded heading section. Root Skill coverage is not established by a copied source file or an output-hash receipt.

## Completed tool canonicalization

The six operational tool entries are now `tools/docx/`, `tools/xlsx/`, `tools/pdf/`, `tools/latex/`, `tools/paper-search/`, and `tools/drawio/`. Source variants remain provenance/difference records rather than user-facing commands.

| Check | Fresh command | Recorded result |
|---|---|---|
| Canonical tool smoke and safe functional probes | `python -m pytest -q tests/test_tools_smoke.py` | Exit `0`; 45 passed. Every canonical entry exists; documented local Python commands resolve; help exits exactly `0`; DOCX generated native OMML and a three-line table, rejected missing or same-path output even with overwrite requested, preserved an existing different output by default, and replaced it only with explicit `--overwrite`; XLSX error and dry-run paths returned structured JSON without tracebacks; the PDF PNG-preview CLI validated inputs, created output directories under a mocked renderer, and formatted dependency/Poppler failures without tracebacks; paper-search parsing, LaTeX help, and draw.io validation help passed. |
| Focused tool/provenance/immutability regression | `python -m pytest -q tests/test_tools_smoke.py tests/test_coverage.py tests/test_source_immutability.py` | Exit `0`; 147 passed. |
| Strict provenance after canonicalization | `python scripts/verify_coverage.py` | Exit `0`; 416 mappings and 333 destinations. |
| Planning-mode provenance after canonicalization | `python scripts/verify_coverage.py --allow-missing-destinations` | Exit `0`; the matrix remained `integrated`. |
| Internal links and runtime closure | `python scripts/check_internal_links.py` | Exit `0`; all internal Markdown links were valid. |
| UTF-8 Skill validation | `python -X utf8 C:\Users\qwerq\.codex\skills\.system\skill-creator\scripts\quick_validate.py .` | Exit `0`; `Skill is valid!`. |

The XLSX source implementations were fully compared: their recalculation and atomic replacement logic is identical, while the step-review variant alone adds successful `--help`; the canonical union keeps that behavior, corrects the relocated shared-office path, enforces UTF-8 output, and adds a read-only `--dry-run`. The DOCX source contracts and scripts were fully compared: the step-review variant is the capability superset for complete LaTeX conversion manifests, warning gates, structured paper validation, and safe XML-parser fallback, so those capabilities form the canonical baseline together with the shared template, comment, revision, OOXML, self-check, and rendering workflow. No installed source file was modified.

The canonical PDF command is `python scripts/convert_pdf_to_images.py input.pdf output_pages --max-dim 1000`. Its argparse help is non-mutating and exits `0` before the optional `pdf2image` import. The two byte-identical installed-source versions of the original script and PDF contract remain deduplicated at `tools/pdf/source-variants/shared/`; the operational PDF CLI and contract are registered controller-owned files, so provenance does not treat modified bytes as an unchanged source copy.

Canonical runtime hardening now also enforces three safety contracts: DOCX formula replacement requires an explicit output path different from the input, refuses an existing output unless `--overwrite` is explicit, and still has no in-place mode; PDF preview validates the input, positive size bound, dependencies, Poppler availability, and output directory with structured failures; XLSX recalculation and dry-run convert corrupt workbooks and invalid timeouts into JSON `status: error` results with nonzero exit codes. These are unified-only controller changes; all retained source-variant bytes remain unchanged.

## Closed gates

- **PASS — Behavioral validation**: six isolated final evaluator runs passed all 18 checks. S1's initial failure, corrective change, and fresh rerun are retained verbatim in `tests/behavior/skill-results.md`; fixed controller-owned hashes protect prompts, transcripts, check evidence, and run identifiers. This is a single-run qualitative validation, not a reliability estimate. Evaluator self-reports about internal tool execution are explicitly unverified and are not used as acceptance evidence.
- **PASS — Final acceptance**: the final shared tree passed both full test modes (251 tests each), strict provenance (416 mappings / 333 destinations), internal-link closure, UTF-8 Skill validation, and installed-source immutability (3 tests).
- **AUTHORIZED — Installation/handoff**: the user explicitly requested immediate installation and GitHub publication.

## Current boundaries

- The three installed source Skill trees remain read-only inputs.
- Installation must preserve the prior installed version as a recoverable backup before replacement.
- An `integrated` coverage matrix means the inventoried source mappings, controller-bound adaptations, and section audits pass their limited provenance checks; it does not prove semantic equivalence and does not close the pending tool or behavioral gates.
- Warnings, skipped required checks, stale scenario evidence, or a matrix/status mismatch keep this record in progress.

## Final regeneration rule

After the remaining gates are resolved, regenerate this file from fresh commands and their actual exit codes. Only that later run may change `IN PROGRESS` or `Installation Ready: NO`, or record final behavioral acceptance and installation readiness.

## Portable reproduction

- Inventory: pass a complete source map with `--source-root-map roots.json`, a complete repeated map with `--source-root NAME=PATH`, or merge individual entries with `--source-root-override NAME=PATH`. Workspace notes accept `--workspace-root` and repeated `--workspace-markdown` values. Equivalent JSON environment variables remain supported.
- Audit verification: pass repeated `--source-root NAME=PATH` values to `scripts/verify_coverage.py`; each override replaces the inventory's machine-specific source location for that named root while preserving its recorded relative path and SHA-256 requirement.
- Regeneration: `--write-seed` always writes `migration-planning`. Only `--finalize` may switch the matrix to `integrated`, after a non-status strict preflight and a second strict validation.
