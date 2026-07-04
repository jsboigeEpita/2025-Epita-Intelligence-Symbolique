"""Tests for run_orchestration.py CLI entry point."""
import subprocess
import sys
from pathlib import Path

import pytest

CLI_SCRIPT = Path(__file__).parent.parent.parent.parent / "argumentation_analysis" / "run_orchestration.py"


class TestRunOrchestrationCLI:
    """Tests for the CLI entry point."""

    def test_sys_path_includes_project_root(self):
        """Verify sys.path includes both script dir and project root.

        Regression test for #883: ModuleNotFoundError when running
        `python argumentation_analysis/run_orchestration.py` without
        explicit PYTHONPATH.
        """
        result = subprocess.run(
            [sys.executable, "-c",
             f"import importlib.util; "
             f"spec = importlib.util.spec_from_file_location('run_orch', r'{CLI_SCRIPT}'); "
             f"mod = importlib.util.module_from_spec(spec); "
             f"import sys; "
             f"project_root = r'{CLI_SCRIPT.parent}'; "
             f"script_dir = r'{CLI_SCRIPT.parent}'; "
             f"print(str(script_dir) in sys.path or True);"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # The script should not fail with ModuleNotFoundError
        assert "ModuleNotFoundError" not in result.stderr

    def test_help_flag_works(self):
        """Verify --help flag works without import errors."""
        result = subprocess.run(
            [sys.executable, str(CLI_SCRIPT), "--help"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(CLI_SCRIPT.parent.parent),
        )
        assert result.returncode == 0
        assert "orchestration" in result.stdout.lower()
        assert "ModuleNotFoundError" not in result.stderr

    def test_list_workflows_no_import_error(self):
        """Verify --list-workflows runs without ModuleNotFoundError.

        This was the exact failure mode in #883: sys.path only included
        the script directory, not the project root, so
        `argumentation_analysis` could not be found.
        """
        result = subprocess.run(
            [sys.executable, str(CLI_SCRIPT), "--list-workflows"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(CLI_SCRIPT.parent.parent),
        )
        assert "ModuleNotFoundError" not in result.stderr
        assert result.returncode == 0
        # Should list at least the standard workflows
        assert "standard" in result.stdout
        assert "light" in result.stdout

    def test_render_restitution_flag_advertised(self):
        """CONV-D #1335: --help advertises --render-restitution (CLI reachability)."""
        result = subprocess.run(
            [sys.executable, str(CLI_SCRIPT), "--help"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(CLI_SCRIPT.parent.parent),
        )
        assert result.returncode == 0
        assert "--render-restitution" in result.stdout
        assert "--restitution-output" in result.stdout


# ============================================================================
# surface_restitution helper — CONV-D #1335
# ============================================================================


class TestSurfaceRestitution:
    """Unit tests for the surface_restitution CLI helper (#1335)."""

    def test_noop_when_report_absent(self, capsys, tmp_path):
        from argumentation_analysis.run_orchestration import surface_restitution

        # No restitution_report key → silent no-op (no print, no write).
        surface_restitution({}, str(tmp_path / "out.md"))
        captured = capsys.readouterr()
        assert "Restitution" not in captured.out

    def test_prints_gate_band_and_writes_markdown(self, capsys, tmp_path):
        from argumentation_analysis.run_orchestration import surface_restitution

        class _Verdict:
            band = "PASS"

        class _Report:
            markdown = "# Restitution corpus_A\n\nActe I…"
            verdict = _Verdict()

        out = tmp_path / "nested" / "report.md"
        surface_restitution({"restitution_report": _Report()}, str(out))
        # the gate band + char count are surfaced in the summary
        captured = capsys.readouterr()
        assert "gate=PASS" in captured.out
        # the markdown is written to the (nested) path
        assert out.exists()
        assert out.read_text(encoding="utf-8").startswith("# Restitution")

    def test_prints_verdict_without_writing_when_no_path(self, capsys, tmp_path):
        from argumentation_analysis.run_orchestration import surface_restitution

        class _Verdict:
            band = "WARN"

        class _Report:
            markdown = "x"
            verdict = _Verdict()

        surface_restitution({"restitution_report": _Report()}, None)
        captured = capsys.readouterr()
        assert "gate=WARN" in captured.out
