from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import types
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_TOOLS = ("docx", "xlsx", "pdf", "latex", "paper-search", "drawio")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_help(script: Path) -> subprocess.CompletedProcess[str]:
    assert script.is_file(), f"missing documented command: {script.relative_to(ROOT)}"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        cwd=ROOT,
    )
    assert result.returncode == 0, (
        f"--help must exit 0 for {script.relative_to(ROOT)}; "
        f"got {result.returncode}: {result.stderr}"
    )
    return result


def test_canonical_tool_entries_exist() -> None:
    for tool in CANONICAL_TOOLS:
        entry = ROOT / "tools" / tool / "SKILL.md"
        assert entry.is_file(), f"missing canonical tool entry: tools/{tool}/SKILL.md"


def test_every_documented_canonical_python_command_exists() -> None:
    for tool in CANONICAL_TOOLS:
        entry = ROOT / "tools" / tool / "SKILL.md"
        assert entry.is_file(), f"missing canonical tool entry: tools/{tool}/SKILL.md"
        text = entry.read_text(encoding="utf-8")
        command_paths = re.findall(
            rf"python(?:3)?\s+(?:\"?<SKILL_ROOT>/tools/{re.escape(tool)}/|"
            r"<this-skill-dir>/)?(scripts/[A-Za-z0-9_./-]+\.py)",
            text,
        )
        for relative in command_paths:
            assert (entry.parent / relative).is_file(), (
                f"stale command in tools/{tool}/SKILL.md: {relative}"
            )


def test_canonical_tool_contracts_do_not_use_stale_paper_search_path() -> None:
    for tool in CANONICAL_TOOLS:
        entry = ROOT / "tools" / tool / "SKILL.md"
        assert entry.is_file(), f"missing canonical tool entry: tools/{tool}/SKILL.md"
        text = entry.read_text(encoding="utf-8")
        assert "paper_search" not in text


def test_consolidated_scripts_exist() -> None:
    expected_scripts = [
        "check_env.py",
        "figure_audit.py",
        "paper_check.py",
        "plot_style.py",
        "profile_data.py",
        "repro_manifest.py",
    ]
    for script in expected_scripts:
        script_path = ROOT / "scripts" / "cumcm-step-review" / script
        assert script_path.is_file(), f"missing consolidated script: {script}"


def test_consolidated_assets_exist() -> None:
    assert (ROOT / "assets").is_dir(), "missing assets directory"


@pytest.mark.parametrize(
    "relative",
    [
        "scripts/cumcm-step-review/check_env.py",
        "scripts/cumcm-step-review/figure_audit.py",
        "scripts/cumcm-step-review/paper_check.py",
        "scripts/cumcm-step-review/profile_data.py",
        "scripts/cumcm-step-review/repro_manifest.py",
        "tools/docx/scripts/equations.py",
        "tools/docx/scripts/paper_format.py",
        "tools/docx/scripts/comment.py",
        "tools/docx/scripts/accept_changes.py",
        "tools/docx/scripts/office/pack.py",
        "tools/docx/scripts/office/unpack.py",
        "tools/docx/scripts/office/validate.py",
        "tools/xlsx/scripts/recalc.py",
        "tools/pdf/scripts/convert_pdf_to_images.py",
        "tools/paper-search/scripts/hybrid_scholar.py",
        "tools/latex/scripts/latex_paper.py",
        "tools/drawio/scripts/validate.py",
    ],
)
def test_python_tools_help_exits_zero(relative: str) -> None:
    run_help(ROOT / relative)


def test_docx_canonical_helpers_create_native_equation_and_three_line_table(
    tmp_path: Path,
) -> None:
    paper_format = load_module(
        ROOT / "tools" / "docx" / "scripts" / "paper_format.py",
        "canonical_docx_paper_format",
    )
    document = paper_format.new_document()
    paper_format.equation(document, r"x_i^2")
    paper_format.three_line_table(
        document, [["符号", "说明", "单位"], ["x", "变量", "-"]]
    )
    output = tmp_path / "minimal.docx"
    document.save(output)

    with zipfile.ZipFile(output) as package:
        xml = package.read("word/document.xml").decode("utf-8")
    assert "<m:oMath" in xml
    assert "<w:tblBorders>" in xml
    assert '<w:insideV w:val="nil"' in xml


def test_docx_canonical_self_check_uses_available_resources() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "docx" / "scripts" / "self_check.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "self_check OK" in result.stdout


@pytest.mark.parametrize("explicit_same_output", [False, True])
def test_docx_replace_refuses_missing_or_same_output(
    tmp_path: Path, explicit_same_output: bool
) -> None:
    docx = pytest.importorskip("docx")
    source = tmp_path / "input.docx"
    document = docx.Document()
    document.add_paragraph("EQ_OBJECTIVE")
    document.save(source)
    before = source.read_bytes()
    command = [
        sys.executable,
        str(ROOT / "tools" / "docx" / "scripts" / "equations.py"),
        "replace",
        str(source),
        "--replace",
        "EQ_OBJECTIVE",
        "x^2",
    ]
    if explicit_same_output:
        command.extend(["--output", str(source), "--overwrite"])

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=ROOT,
    )

    assert result.returncode != 0
    assert "traceback" not in (result.stdout + result.stderr).casefold()
    assert "output" in (result.stdout + result.stderr).casefold()
    assert source.read_bytes() == before


def test_docx_replace_requires_overwrite_for_existing_output(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    source = tmp_path / "input.docx"
    document = docx.Document()
    document.add_paragraph("EQ_OBJECTIVE")
    document.save(source)
    source_before = source.read_bytes()

    output = tmp_path / "output.docx"
    existing = docx.Document()
    existing.add_paragraph("existing output must survive a refused replacement")
    existing.save(output)
    output_before = output.read_bytes()
    command = [
        sys.executable,
        str(ROOT / "tools" / "docx" / "scripts" / "equations.py"),
        "replace",
        str(source),
        "--replace",
        "EQ_OBJECTIVE",
        "x^2",
        "--output",
        str(output),
    ]

    refused = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=ROOT,
    )
    assert refused.returncode == 1
    assert "traceback" not in (refused.stdout + refused.stderr).casefold()
    refusal = json.loads(refused.stdout)
    assert refusal["status"] == "error"
    assert "--overwrite" in refusal["error"]
    assert source.read_bytes() == source_before
    assert output.read_bytes() == output_before

    replaced = subprocess.run(
        [*command, "--overwrite"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=ROOT,
    )
    assert replaced.returncode == 0, replaced.stderr or replaced.stdout
    assert "traceback" not in (replaced.stdout + replaced.stderr).casefold()
    assert source.read_bytes() == source_before
    assert output.read_bytes() != output_before
    with zipfile.ZipFile(output) as package:
        xml = package.read("word/document.xml").decode("utf-8")
    assert "<m:oMath" in xml


def test_xlsx_recalc_safe_errors_do_not_invoke_external_process(tmp_path: Path) -> None:
    script = ROOT / "tools" / "xlsx" / "scripts" / "recalc.py"
    missing = subprocess.run(
        [sys.executable, str(script), str(tmp_path / "missing.xlsx")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=ROOT,
    )
    assert missing.returncode == 1
    assert "文件不存在" in json.loads(missing.stdout)["error"]

    wrong_type = tmp_path / "input.csv"
    wrong_type.write_text("a,b\n1,2\n", encoding="utf-8")
    wrong = subprocess.run(
        [sys.executable, str(script), str(wrong_type)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=ROOT,
    )
    assert wrong.returncode == 1
    assert "只支持 .xlsx" in json.loads(wrong.stdout)["error"]


def test_xlsx_recalc_dry_run_inspects_without_modifying_workbook(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    workbook_path = tmp_path / "formula.xlsx"
    workbook = openpyxl.Workbook()
    workbook.active["A1"] = "=1+1"
    workbook.save(workbook_path)
    before = workbook_path.read_bytes()

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "xlsx" / "scripts" / "recalc.py"),
            "--dry-run",
            str(workbook_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=ROOT,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "dry_run"
    assert payload["total_formulas"] == 1
    assert workbook_path.read_bytes() == before


@pytest.mark.parametrize("timeout", ["not-a-number", "0", "-1"])
def test_xlsx_recalc_invalid_timeout_is_json_error(tmp_path: Path, timeout: str) -> None:
    workbook = tmp_path / "valid.xlsx"
    workbook.write_bytes(b"not opened because timeout is invalid")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "xlsx" / "scripts" / "recalc.py"),
            str(workbook),
            timeout,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=ROOT,
    )
    assert result.returncode == 1
    assert "traceback" not in (result.stdout + result.stderr).casefold()
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert "timeout" in payload["error"].casefold()


def test_xlsx_recalc_corrupt_workbook_is_json_error(tmp_path: Path) -> None:
    workbook = tmp_path / "corrupt.xlsx"
    workbook.write_bytes(b"not an xlsx zip")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "xlsx" / "scripts" / "recalc.py"),
            "--dry-run",
            str(workbook),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=ROOT,
    )
    assert result.returncode == 1
    assert "traceback" not in (result.stdout + result.stderr).casefold()
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert "xlsx" in payload["error"].casefold()


def test_pdf_canonical_script_import_is_safe() -> None:
    module = load_module(
        ROOT / "tools" / "pdf" / "scripts" / "extract_form_structure.py",
        "canonical_pdf_extract_form_structure",
    )
    assert callable(module.extract_form_structure)


def test_pdf_contract_documents_canonical_preview_command() -> None:
    text = (ROOT / "tools" / "pdf" / "SKILL.md").read_text(encoding="utf-8")
    assert "python scripts/convert_pdf_to_images.py" in text


def test_pdf_preview_help_describes_non_mutating_conversion() -> None:
    result = run_help(ROOT / "tools" / "pdf" / "scripts" / "convert_pdf_to_images.py")
    output = (result.stdout + result.stderr).casefold()
    assert "input" in output
    assert "output" in output
    assert "png" in output


def test_pdf_preview_cli_missing_input_is_structured_error(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "pdf" / "scripts" / "convert_pdf_to_images.py"),
            str(tmp_path / "missing.pdf"),
            str(tmp_path / "pages"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=ROOT,
    )
    assert result.returncode == 1
    assert "traceback" not in (result.stdout + result.stderr).casefold()
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert "input" in payload["error"].casefold()
    assert not (tmp_path / "pages").exists()


def test_pdf_preview_cli_rejects_nonpositive_max_dim(tmp_path: Path) -> None:
    source = tmp_path / "input.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "pdf" / "scripts" / "convert_pdf_to_images.py"),
            str(source),
            str(tmp_path / "pages"),
            "--max-dim",
            "0",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=ROOT,
    )
    assert result.returncode == 1
    assert "traceback" not in (result.stdout + result.stderr).casefold()
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert "max-dim" in payload["error"]


def test_pdf_preview_convert_creates_output_directory_with_mock_renderer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "input.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    output = tmp_path / "nested" / "pages"

    class FakeImage:
        size = (1200, 600)

        def resize(self, size):
            self.size = size
            return self

        def save(self, path):
            Path(path).write_bytes(b"PNG")

    monkeypatch.setitem(
        sys.modules,
        "pdf2image",
        types.SimpleNamespace(convert_from_path=lambda *_args, **_kwargs: [FakeImage()]),
    )
    module = load_module(
        ROOT / "tools" / "pdf" / "scripts" / "convert_pdf_to_images.py",
        "canonical_pdf_preview_runtime",
    )
    result = module.convert(source, output, max_dim=1000)

    assert output.is_dir()
    assert (output / "page_1.png").read_bytes() == b"PNG"
    assert result == {"status": "success", "pages": 1, "output_directory": str(output.resolve())}


def test_pdf_preview_formats_dependency_and_poppler_errors() -> None:
    module = load_module(
        ROOT / "tools" / "pdf" / "scripts" / "convert_pdf_to_images.py",
        "canonical_pdf_preview_errors",
    )
    missing_module = module.friendly_error(ModuleNotFoundError("No module named 'pdf2image'"))
    missing_poppler = module.friendly_error(type("PDFInfoNotInstalledError", (Exception,), {})())
    assert "pip install pdf2image" in missing_module
    assert "Poppler" in missing_poppler


def test_paper_search_parser_is_network_free() -> None:
    scripts = ROOT / "tools" / "paper-search" / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        module = load_module(scripts / "hybrid_scholar.py", "canonical_hybrid_scholar")
        arguments = module.build_parser().parse_args(["--query", "robust optimization"])
    finally:
        sys.path.remove(str(scripts))
    assert arguments.query == "robust optimization"


@pytest.mark.parametrize("source_variant", ["math-modeling", "cumcm-step-review"])
def test_docx_comment_variants_resolve_shared_templates(source_variant: str) -> None:
    script = ROOT / "tools" / "docx" / "source-variants" / source_variant / "scripts" / "comment.py"
    expected_templates = ROOT / "tools" / "docx" / "scripts" / "templates"
    probe = (
        "import runpy, sys; "
        "namespace = runpy.run_path(sys.argv[1], run_name='relocation_probe'); "
        "print(namespace['TEMPLATE_DIR'])"
    )

    result = subprocess.run(
        [sys.executable, "-c", probe, str(script)],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()).resolve() == expected_templates.resolve()
    for name in (
        "comments.xml",
        "commentsExtended.xml",
        "commentsExtensible.xml",
        "commentsIds.xml",
        "people.xml",
    ):
        assert (expected_templates / name).is_file(), name


@pytest.mark.parametrize("source_variant", ["math-modeling", "cumcm-step-review"])
def test_xlsx_recalc_variants_resolve_shared_office(source_variant: str) -> None:
    script = ROOT / "tools" / "xlsx" / "source-variants" / source_variant / "scripts" / "recalc.py"
    probe = "import runpy, sys; runpy.run_path(sys.argv[1], run_name='relocation_probe')"

    result = subprocess.run(
        [sys.executable, "-c", probe, str(script)],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=ROOT,
    )

    assert result.returncode == 0, result.stderr
