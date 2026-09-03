import importlib.util
import subprocess
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook


UNIFIED_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = (
    UNIFIED_ROOT / "tools" / "xlsx" / "source-variants" / "math-modeling" / "scripts"
)


def _load_source_module(name):
    unique_name = f"migrated_math_modeling_{Path(__file__).stem}_{name}"
    spec = importlib.util.spec_from_file_location(unique_name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    original_path = sys.path.copy()
    sys.modules[unique_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original_path
        sys.modules.pop(unique_name, None)
    return module


recalc = _load_source_module("recalc")


class RecalcTests(unittest.TestCase):
    def test_timeout_is_reported_as_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "book.xlsx"
            Workbook().save(path)
            with patch.object(recalc, "get_soffice_env", return_value={}), patch.object(
                recalc.subprocess, "run", side_effect=subprocess.TimeoutExpired(["soffice"], 1)
            ):
                result = recalc.recalc(path, timeout=1)

        self.assertIn("error", result)
        self.assertIn("超时", result["error"])

    def test_success_uses_temporary_output_and_counts_formulas(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "book.xlsx"
            workbook = Workbook()
            workbook.active["A1"] = "=1+1"
            workbook.save(path)

            def fake_run(command, **_kwargs):
                output_dir = Path(command[command.index("--outdir") + 1])
                shutil.copy2(path, output_dir / path.name)
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch.object(recalc, "get_soffice_env", return_value={}), patch.object(
                recalc.subprocess, "run", side_effect=fake_run
            ):
                result = recalc.recalc(path)

        self.assertIn("status", result, result)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total_formulas"], 1)


if __name__ == "__main__":
    unittest.main()
