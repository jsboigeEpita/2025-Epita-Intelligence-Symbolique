# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.utils.dev_tools.env_checks
Covers _run_command, _parse_requirement, _parse_version,
check_java_environment, check_jpype_config, check_python_dependencies.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from argumentation_analysis.utils.dev_tools.env_checks import (
    _run_command,
    _parse_requirement,
    _parse_version,
    check_java_environment,
    check_python_dependencies,
)

# ============================================================
# _parse_requirement / _parse_version
# ============================================================


class TestParseHelpers:
    def test_parse_requirement_simple(self):
        req = _parse_requirement("requests")
        assert req.name == "requests"

    def test_parse_requirement_with_version(self):
        req = _parse_requirement("requests>=2.20")
        assert req.name == "requests"
        assert str(req.specifier) == ">=2.20"

    def test_parse_requirement_invalid_raises(self):
        with pytest.raises(Exception):
            _parse_requirement("!!!invalid!!!")

    def test_parse_version_simple(self):
        v = _parse_version("1.2.3")
        assert str(v) == "1.2.3"

    def test_parse_version_with_pre(self):
        v = _parse_version("1.0.0rc1")
        assert v is not None

    def test_parse_version_invalid_raises(self):
        with pytest.raises(Exception):
            _parse_version("not-a-version")


# ============================================================
# _run_command
# ============================================================


class TestRunCommand:
    @patch("argumentation_analysis.utils.dev_tools.env_checks.subprocess.Popen")
    def test_success(self, mock_popen):
        proc = MagicMock()
        proc.communicate.return_value = ("stdout_data", "stderr_data")
        proc.returncode = 0
        mock_popen.return_value = proc
        rc, out, err = _run_command(["echo", "hello"])
        assert rc == 0
        assert out == "stdout_data"

    @patch("argumentation_analysis.utils.dev_tools.env_checks.subprocess.Popen")
    def test_timeout(self, mock_popen):
        import subprocess

        proc = MagicMock()
        proc.communicate.side_effect = subprocess.TimeoutExpired(cmd="cmd", timeout=30)
        mock_popen.return_value = proc
        rc, out, err = _run_command(["slow_cmd"])
        assert rc == -1
        assert "TimeoutExpired" in err

    @patch("argumentation_analysis.utils.dev_tools.env_checks.subprocess.Popen")
    def test_file_not_found(self, mock_popen):
        mock_popen.side_effect = FileNotFoundError("not found")
        rc, out, err = _run_command(["nonexistent"])
        assert rc == -1
        assert "FileNotFoundError" in err

    @patch("argumentation_analysis.utils.dev_tools.env_checks.subprocess.Popen")
    def test_general_exception(self, mock_popen):
        mock_popen.side_effect = OSError("disk error")
        rc, out, err = _run_command(["bad_cmd"])
        assert rc == -1


# ============================================================
# check_java_environment
# ============================================================


class TestCheckJavaEnvironment:
    @patch("argumentation_analysis.utils.dev_tools.env_checks._run_command")
    @patch(
        "argumentation_analysis.utils.dev_tools.env_checks.os.environ",
        {"JAVA_HOME": "/fake/java"},
    )
    @patch("argumentation_analysis.utils.dev_tools.env_checks._PathInternal")
    def test_java_home_valid_and_java_works(self, mock_path_cls, mock_run):
        # Setup JAVA_HOME path mock
        mock_home_path = MagicMock()
        mock_home_path.is_dir.return_value = True
        mock_java_exe = MagicMock()
        mock_java_exe.exists.return_value = True
        mock_java_exe.is_file.return_value = True
        mock_home_path.__truediv__ = MagicMock(
            side_effect=lambda x: mock_java_exe if "java" in str(x) else MagicMock()
        )
        # Return the home path when _PathInternal is called with JAVA_HOME
        mock_path_cls.return_value = mock_home_path
        # java -version succeeds
        mock_run.return_value = (0, "", 'openjdk version "11.0.1"')
        result = check_java_environment()
        assert result is True

    @patch("argumentation_analysis.utils.dev_tools.env_checks._run_command")
    @patch("argumentation_analysis.utils.dev_tools.env_checks.os.environ", {})
    def test_no_java_home_java_works(self, mock_run):
        # No JAVA_HOME but java -version works
        mock_run.return_value = (0, "", "java version 11")
        result = check_java_environment()
        # Should return False because java_home_valid is False
        assert result is False

    @patch("argumentation_analysis.utils.dev_tools.env_checks._run_command")
    @patch("argumentation_analysis.utils.dev_tools.env_checks.os.environ", {})
    def test_no_java_at_all(self, mock_run):
        mock_run.return_value = (-1, "", "FileNotFoundError: java")
        result = check_java_environment()
        assert result is False

    @patch("argumentation_analysis.utils.dev_tools.env_checks._run_command")
    @patch(
        "argumentation_analysis.utils.dev_tools.env_checks.os.environ",
        {"JAVA_HOME": "/fake"},
    )
    @patch("argumentation_analysis.utils.dev_tools.env_checks._PathInternal")
    def test_java_home_not_a_dir(self, mock_path_cls, mock_run):
        mock_home_path = MagicMock()
        mock_home_path.is_dir.return_value = False
        mock_path_cls.return_value = mock_home_path
        mock_run.return_value = (0, "", "java version 11")
        result = check_java_environment()
        assert result is False

    @patch("argumentation_analysis.utils.dev_tools.env_checks._run_command")
    @patch(
        "argumentation_analysis.utils.dev_tools.env_checks.os.environ",
        {"JAVA_HOME": "/fake/java"},
    )
    @patch("argumentation_analysis.utils.dev_tools.env_checks._PathInternal")
    def test_java_version_returns_no_output(self, mock_path_cls, mock_run):
        mock_home_path = MagicMock()
        mock_home_path.is_dir.return_value = True
        mock_java_exe = MagicMock()
        mock_java_exe.exists.return_value = True
        mock_java_exe.is_file.return_value = True
        mock_home_path.__truediv__ = MagicMock(return_value=mock_java_exe)
        mock_path_cls.return_value = mock_home_path
        # java -version returns 0 but empty output
        mock_run.return_value = (0, "", "")
        result = check_java_environment()
        assert result is False


# ============================================================
# check_python_dependencies
# ============================================================


class TestCheckPythonDependencies:
    def test_file_not_found(self, tmp_path):
        result = check_python_dependencies(tmp_path / "nonexistent.txt")
        assert result is False

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("# just a comment\n", encoding="utf-8")
        result = check_python_dependencies(f)
        assert result is True

    @patch(
        "argumentation_analysis.utils.dev_tools.env_checks.importlib.metadata.version"
    )
    def test_satisfied_dependency(self, mock_version, tmp_path):
        mock_version.return_value = "2.28.0"
        f = tmp_path / "reqs.txt"
        f.write_text("requests>=2.20\n", encoding="utf-8")
        result = check_python_dependencies(f)
        assert result is True

    @patch(
        "argumentation_analysis.utils.dev_tools.env_checks.importlib.metadata.version"
    )
    def test_unsatisfied_dependency(self, mock_version, tmp_path):
        mock_version.return_value = "1.0.0"
        f = tmp_path / "reqs.txt"
        f.write_text("requests>=2.20\n", encoding="utf-8")
        result = check_python_dependencies(f)
        assert result is False

    @patch(
        "argumentation_analysis.utils.dev_tools.env_checks.importlib.metadata.version"
    )
    def test_missing_package(self, mock_version, tmp_path):
        import importlib.metadata

        mock_version.side_effect = importlib.metadata.PackageNotFoundError("nope")
        f = tmp_path / "reqs.txt"
        f.write_text("nonexistent_package_xyz\n", encoding="utf-8")
        result = check_python_dependencies(f)
        assert result is False

    def test_editable_install_skipped(self, tmp_path):
        f = tmp_path / "reqs.txt"
        f.write_text("-e git+https://example.com/repo.git\n", encoding="utf-8")
        result = check_python_dependencies(f)
        assert result is True

    def test_recursive_include_skipped(self, tmp_path):
        f = tmp_path / "reqs.txt"
        f.write_text("-r other_requirements.txt\n", encoding="utf-8")
        result = check_python_dependencies(f)
        assert result is True

    @patch(
        "argumentation_analysis.utils.dev_tools.env_checks.importlib.metadata.version"
    )
    def test_no_version_specifier(self, mock_version, tmp_path):
        mock_version.return_value = "1.0.0"
        f = tmp_path / "reqs.txt"
        f.write_text("requests\n", encoding="utf-8")
        result = check_python_dependencies(f)
        assert result is True

    def test_string_path_accepted(self, tmp_path):
        f = tmp_path / "reqs.txt"
        f.write_text("# empty\n", encoding="utf-8")
        result = check_python_dependencies(str(f))
        assert result is True

    @patch(
        "argumentation_analysis.utils.dev_tools.env_checks.importlib.metadata.version"
    )
    def test_multiple_deps_mixed(self, mock_version, tmp_path):
        import importlib.metadata

        def side_effect(name):
            if name == "requests":
                return "2.28.0"
            raise importlib.metadata.PackageNotFoundError(name)

        mock_version.side_effect = side_effect
        f = tmp_path / "reqs.txt"
        f.write_text("requests>=2.20\nmissing_pkg\n", encoding="utf-8")
        result = check_python_dependencies(f)
        assert result is False

    def test_git_vcs_line_skipped(self, tmp_path):
        f = tmp_path / "reqs.txt"
        f.write_text("git+https://github.com/user/repo.git@main\n", encoding="utf-8")
        result = check_python_dependencies(f)
        assert result is True
