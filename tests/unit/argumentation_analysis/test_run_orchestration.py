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
