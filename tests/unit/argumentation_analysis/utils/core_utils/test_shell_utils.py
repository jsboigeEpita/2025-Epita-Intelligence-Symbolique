# tests/unit/argumentation_analysis/utils/core_utils/test_shell_utils.py
"""Tests for shell command execution utilities."""

import pytest
import sys
from unittest.mock import patch, MagicMock

from argumentation_analysis.core.utils.shell_utils import run_shell_command


class TestRunShellCommand:
    def test_successful_command_list(self):
        code, stdout, stderr = run_shell_command(
            [sys.executable, "-c", "print('hello')"]
        )
        assert code == 0
        assert "hello" in stdout

    def test_successful_command_with_description(self):
        code, stdout, stderr = run_shell_command(
            [sys.executable, "-c", "print('test')"],
            description="Test command",
        )
        assert code == 0

    def test_failed_command(self):
        code, stdout, stderr = run_shell_command(
            [sys.executable, "-c", "import sys; sys.exit(1)"]
        )
        assert code == 1

    def test_stderr_captured(self):
        code, stdout, stderr = run_shell_command(
            [sys.executable, "-c", "import sys; sys.stderr.write('error msg')"]
        )
        assert "error msg" in stderr

    def test_command_not_found(self):
        code, stdout, stderr = run_shell_command(["nonexistent_command_12345"])
        assert code == -1

    def test_capture_output_false(self):
        code, stdout, stderr = run_shell_command(
            [sys.executable, "-c", "print('ignored')"],
            capture_output=False,
        )
        assert code == 0
        assert stdout == ""
        assert stderr == ""

    def test_custom_cwd(self, tmp_path):
        code, stdout, stderr = run_shell_command(
            [sys.executable, "-c", "import os; print(os.getcwd())"],
            cwd=tmp_path,
        )
        assert code == 0
        # Output should contain the tmp_path
        assert (
            str(tmp_path).replace("\\", "/") in stdout.replace("\\", "/")
            or tmp_path.name in stdout
        )

    def test_custom_env(self):
        import os

        env = os.environ.copy()
        env["TEST_VAR_SHELL_UTILS"] = "custom_value"
        code, stdout, stderr = run_shell_command(
            [
                sys.executable,
                "-c",
                "import os; print(os.environ.get('TEST_VAR_SHELL_UTILS', ''))",
            ],
            env=env,
        )
        assert code == 0
        assert "custom_value" in stdout

    def test_string_command_shell_mode(self):
        code, stdout, stderr = run_shell_command(
            f"{sys.executable} -c \"print('shell_mode')\"",
            shell_mode=True,
        )
        assert code == 0
        assert "shell_mode" in stdout

    def test_default_description_string(self):
        # Verify it doesn't crash with auto-generated description
        code, stdout, stderr = run_shell_command([sys.executable, "-c", "pass"])
        assert code == 0

    def test_default_description_long_command(self):
        long_arg = "x" * 200
        code, stdout, stderr = run_shell_command(
            [sys.executable, "-c", f"print('{long_arg}')"]
        )
        assert code == 0

    def test_return_types(self):
        code, stdout, stderr = run_shell_command([sys.executable, "-c", "pass"])
        assert isinstance(code, int)
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)
