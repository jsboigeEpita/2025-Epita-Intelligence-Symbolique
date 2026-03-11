# tests/unit/argumentation_analysis/utils/core_utils/test_filesystem_utils.py
"""Tests for filesystem utility functions."""

import pytest
from pathlib import Path

from argumentation_analysis.core.utils.filesystem_utils import (
    ensure_directory_exists,
    create_gitkeep_in_directory,
    check_files_existence,
    get_all_files_in_directory,
)


# ── ensure_directory_exists ──

class TestEnsureDirectoryExists:
    def test_creates_new_directory(self, tmp_path):
        new_dir = tmp_path / "new_dir"
        assert not new_dir.exists()
        result = ensure_directory_exists(new_dir)
        assert result is True
        assert new_dir.exists()

    def test_existing_directory(self, tmp_path):
        result = ensure_directory_exists(tmp_path)
        assert result is True

    def test_creates_nested_dirs(self, tmp_path):
        deep_dir = tmp_path / "a" / "b" / "c"
        result = ensure_directory_exists(deep_dir)
        assert result is True
        assert deep_dir.exists()


# ── create_gitkeep_in_directory ──

class TestCreateGitkeepInDirectory:
    def test_creates_gitkeep(self, tmp_path):
        result = create_gitkeep_in_directory(tmp_path)
        assert result is True
        assert (tmp_path / ".gitkeep").exists()

    def test_creates_directory_and_gitkeep(self, tmp_path):
        new_dir = tmp_path / "new_dir"
        result = create_gitkeep_in_directory(new_dir)
        assert result is True
        assert new_dir.exists()
        assert (new_dir / ".gitkeep").exists()

    def test_no_overwrite_existing(self, tmp_path):
        gitkeep = tmp_path / ".gitkeep"
        gitkeep.write_text("existing")
        result = create_gitkeep_in_directory(tmp_path, overwrite=False)
        assert result is True
        # File should still exist
        assert gitkeep.exists()

    def test_overwrite_existing(self, tmp_path):
        gitkeep = tmp_path / ".gitkeep"
        gitkeep.write_text("old content")
        result = create_gitkeep_in_directory(tmp_path, overwrite=True)
        assert result is True
        assert gitkeep.exists()


# ── check_files_existence ──

class TestCheckFilesExistence:
    def test_all_exist(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("a")
        f2.write_text("b")
        existing, missing = check_files_existence([f1, f2])
        assert len(existing) == 2
        assert len(missing) == 0

    def test_all_missing(self, tmp_path):
        f1 = tmp_path / "missing1.txt"
        f2 = tmp_path / "missing2.txt"
        existing, missing = check_files_existence([f1, f2])
        assert len(existing) == 0
        assert len(missing) == 2

    def test_mixed(self, tmp_path):
        f1 = tmp_path / "exists.txt"
        f1.write_text("yes")
        f2 = tmp_path / "missing.txt"
        existing, missing = check_files_existence([f1, f2])
        assert len(existing) == 1
        assert len(missing) == 1

    def test_empty_input(self):
        existing, missing = check_files_existence([])
        assert existing == []
        assert missing == []

    def test_string_paths(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("content")
        existing, missing = check_files_existence([str(f)])
        assert len(existing) == 1

    def test_directory_treated_as_missing(self, tmp_path):
        existing, missing = check_files_existence([tmp_path])
        assert len(existing) == 0
        assert len(missing) == 1


# ── get_all_files_in_directory ──

class TestGetAllFilesInDirectory:
    def test_all_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.py").write_text("b")
        files = get_all_files_in_directory(tmp_path)
        assert len(files) == 2

    def test_pattern_filter(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.py").write_text("b")
        files = get_all_files_in_directory(tmp_path, patterns=["*.txt"])
        assert len(files) == 1
        assert files[0].suffix == ".txt"

    def test_recursive(self, tmp_path):
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (tmp_path / "root.txt").write_text("r")
        (subdir / "nested.txt").write_text("n")
        files = get_all_files_in_directory(tmp_path, patterns=["*.txt"], recursive=True)
        assert len(files) == 2

    def test_non_recursive(self, tmp_path):
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (tmp_path / "root.txt").write_text("r")
        (subdir / "nested.txt").write_text("n")
        files = get_all_files_in_directory(tmp_path, patterns=["*.txt"], recursive=False)
        assert len(files) == 1

    def test_exclusions(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.log").write_text("b")
        files = get_all_files_in_directory(tmp_path, exclusions=["*.log"])
        assert len(files) == 1
        assert files[0].name == "a.txt"

    def test_invalid_directory(self, tmp_path):
        bad = tmp_path / "nonexistent"
        files = get_all_files_in_directory(bad)
        assert files == []

    def test_empty_directory(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        files = get_all_files_in_directory(empty_dir)
        assert files == []

    def test_string_path(self, tmp_path):
        (tmp_path / "file.txt").write_text("content")
        files = get_all_files_in_directory(str(tmp_path))
        assert len(files) == 1

    def test_multiple_patterns(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.py").write_text("b")
        (tmp_path / "c.md").write_text("c")
        files = get_all_files_in_directory(tmp_path, patterns=["*.txt", "*.py"])
        assert len(files) == 2

    def test_returns_sorted(self, tmp_path):
        (tmp_path / "c.txt").write_text("c")
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        files = get_all_files_in_directory(tmp_path)
        names = [f.name for f in files]
        assert names == sorted(names)
