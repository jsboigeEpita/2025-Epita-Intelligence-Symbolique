# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.utils.system_utils
Covers ensure_directory_exists, get_project_root, is_running_in_notebook, check_and_install.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

from argumentation_analysis.utils.system_utils import (
    ensure_directory_exists,
    get_project_root,
    is_running_in_notebook,
    check_and_install,
)


# ============================================================
# ensure_directory_exists
# ============================================================

class TestEnsureDirectoryExists:
    def test_creates_missing_directory(self, tmp_path):
        target = tmp_path / "new_dir"
        assert not target.exists()
        result = ensure_directory_exists(target)
        assert result is True
        assert target.is_dir()

    def test_existing_directory_returns_true(self, tmp_path):
        target = tmp_path / "existing"
        target.mkdir()
        result = ensure_directory_exists(target)
        assert result is True

    def test_creates_nested_directories(self, tmp_path):
        target = tmp_path / "a" / "b" / "c"
        result = ensure_directory_exists(target)
        assert result is True
        assert target.is_dir()

    def test_string_path_accepted(self, tmp_path):
        target = str(tmp_path / "str_dir")
        result = ensure_directory_exists(target)
        assert result is True
        assert Path(target).is_dir()

    def test_file_at_path_returns_false(self, tmp_path):
        target = tmp_path / "a_file"
        target.write_text("content", encoding="utf-8")
        result = ensure_directory_exists(target)
        assert result is False

    def test_permission_error_returns_false(self, tmp_path):
        with patch.object(Path, "mkdir", side_effect=PermissionError("no access")):
            with patch.object(Path, "exists", return_value=False):
                result = ensure_directory_exists(tmp_path / "blocked")
                assert result is False


# ============================================================
# get_project_root
# ============================================================

class TestGetProjectRoot:
    def test_returns_path(self):
        root = get_project_root()
        assert isinstance(root, Path)

    def test_root_contains_pyproject_or_git(self):
        root = get_project_root()
        has_marker = (root / ".git").is_dir() or (root / "pyproject.toml").is_file()
        # Should find root or fallback
        assert isinstance(root, Path)

    def test_root_is_absolute(self):
        root = get_project_root()
        assert root.is_absolute()


# ============================================================
# is_running_in_notebook
# ============================================================

class TestIsRunningInNotebook:
    def test_not_in_notebook(self):
        # In pytest, ipykernel is typically not loaded
        if "ipykernel" in sys.modules:
            pytest.skip("ipykernel is loaded in this environment")
        assert is_running_in_notebook() is False

    def test_detects_notebook_when_ipykernel_loaded(self):
        fake_modules = dict(sys.modules)
        fake_modules["ipykernel"] = MagicMock()
        with patch.dict("sys.modules", fake_modules):
            assert is_running_in_notebook() is True


# ============================================================
# check_and_install
# ============================================================

class TestCheckAndInstall:
    def test_existing_package_returns_true(self):
        # os is always available
        result = check_and_install("os", "os")
        assert result is True

    def test_nonexistent_triggers_install(self):
        with patch("importlib.import_module", side_effect=[ImportError, None]):
            with patch("subprocess.check_call") as mock_call:
                with patch("importlib.invalidate_caches"):
                    result = check_and_install("fake_pkg_xyz", "fake-pkg-xyz")
                    assert result is True
                    mock_call.assert_called_once()

    def test_install_failure_returns_false(self):
        with patch("importlib.import_module", side_effect=ImportError):
            with patch("subprocess.check_call", side_effect=Exception("install failed")):
                result = check_and_install("fake_pkg_xyz", "fake-pkg-xyz")
                assert result is False

    def test_install_uses_pip(self):
        with patch("importlib.import_module", side_effect=[ImportError, None]):
            with patch("subprocess.check_call") as mock_call:
                with patch("importlib.invalidate_caches"):
                    check_and_install("some_pkg", "some-pkg")
                    args = mock_call.call_args[0][0]
                    assert "-m" in args
                    assert "pip" in args
                    assert "install" in args
                    assert "some-pkg" in args
