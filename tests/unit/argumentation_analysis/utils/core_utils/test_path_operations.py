# tests/unit/argumentation_analysis/utils/core_utils/test_path_operations.py
"""Tests for path operations utilities — sanitize_filename, check_path_exists, archive_file."""

import pytest
from pathlib import Path

from argumentation_analysis.core.utils.path_operations import (
    sanitize_filename,
    check_path_exists,
    create_archive_path,
    archive_file,
    PATH_TYPE_FILE,
    PATH_TYPE_DIRECTORY,
)

# ── sanitize_filename ──


class TestSanitizeFilename:
    def test_simple_name(self):
        result = sanitize_filename("test.txt")
        assert result == "test.txt"

    def test_spaces_to_underscores(self):
        result = sanitize_filename("my file name.txt")
        assert "_" in result
        assert " " not in result
        assert result.endswith(".txt")

    def test_empty_string(self):
        assert sanitize_filename("") == "empty_filename"

    def test_dot_only(self):
        assert sanitize_filename(".") == "_hidden_default"

    def test_dotdot(self):
        assert sanitize_filename("..") == "_hidden_default"

    def test_accented_chars(self):
        result = sanitize_filename("café résumé.txt")
        assert result.endswith(".txt")
        # unidecode converts accents to ASCII
        assert "e" in result

    def test_special_chars_removed(self):
        result = sanitize_filename("file@#$%.txt")
        assert "@" not in result
        assert "#" not in result
        assert result.endswith(".txt")

    def test_hidden_file(self):
        result = sanitize_filename(".gitkeep")
        assert result.startswith(".")

    def test_hidden_file_with_extension(self):
        result = sanitize_filename(".config.json")
        assert result.startswith(".")
        assert result.endswith(".json")

    def test_max_len_truncation(self):
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name, max_len=50)
        assert len(result) <= 50
        assert result.endswith(".txt")

    def test_no_extension(self):
        result = sanitize_filename("Makefile")
        assert "." not in result or result.startswith(".")

    def test_multiple_dots(self):
        result = sanitize_filename("file.name.backup.txt")
        assert result.endswith(".txt")

    def test_all_special_chars(self):
        result = sanitize_filename("!@#$%^&*()")
        assert result == "default_filename"

    def test_preserves_lowercase(self):
        result = sanitize_filename("MyFile.TXT")
        assert result == result.lower()

    def test_dashes_to_underscores(self):
        result = sanitize_filename("my-file-name.txt")
        assert "-" not in result


# ── check_path_exists ──


class TestCheckPathExists:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        assert check_path_exists(f, PATH_TYPE_FILE) is True

    def test_existing_directory(self, tmp_path):
        assert check_path_exists(tmp_path, PATH_TYPE_DIRECTORY) is True

    def test_missing_path_exits(self, tmp_path):
        f = tmp_path / "missing.txt"
        with pytest.raises(SystemExit):
            check_path_exists(f, PATH_TYPE_FILE)

    def test_file_expected_but_is_dir(self, tmp_path):
        with pytest.raises(SystemExit):
            check_path_exists(tmp_path, PATH_TYPE_FILE)

    def test_dir_expected_but_is_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        with pytest.raises(SystemExit):
            check_path_exists(f, PATH_TYPE_DIRECTORY)

    def test_unsupported_type_exits(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        with pytest.raises(SystemExit):
            check_path_exists(f, "unsupported_type")


# ── create_archive_path ──


class TestCreateArchivePath:
    def test_basic(self, tmp_path):
        archive_dir = tmp_path / "archives"
        source = Path("src/file.txt")
        result = create_archive_path(archive_dir, source)
        assert result.name == "file.txt"
        assert str(archive_dir) in str(result)

    def test_preserve_levels_zero(self, tmp_path):
        archive_dir = tmp_path / "archives"
        source = Path("a/b/c/file.txt")
        result = create_archive_path(archive_dir, source, preserve_levels=0)
        assert result == archive_dir / "file.txt"

    def test_preserve_levels_one(self, tmp_path):
        archive_dir = tmp_path / "archives"
        source = Path("a/b/c/file.txt")
        result = create_archive_path(archive_dir, source, preserve_levels=1)
        assert "c" in str(result)
        assert result.name == "file.txt"

    def test_preserve_levels_two(self, tmp_path):
        archive_dir = tmp_path / "archives"
        source = Path("a/b/c/file.txt")
        result = create_archive_path(archive_dir, source, preserve_levels=2)
        assert result.name == "file.txt"

    def test_negative_levels_treated_as_zero(self, tmp_path):
        archive_dir = tmp_path / "archives"
        source = Path("a/b/file.txt")
        result = create_archive_path(archive_dir, source, preserve_levels=-1)
        assert result == archive_dir / "file.txt"

    def test_creates_parent_dirs(self, tmp_path):
        archive_dir = tmp_path / "deep" / "archive"
        source = Path("src/file.txt")
        result = create_archive_path(archive_dir, source)
        assert result.parent.exists()


# ── archive_file ──


class TestArchiveFile:
    def test_archive_moves_file(self, tmp_path):
        source = tmp_path / "source.txt"
        source.write_text("content")
        dest = tmp_path / "archive" / "source.txt"
        result = archive_file(source, dest)
        assert result is True
        assert dest.exists()
        assert not source.exists()

    def test_archive_missing_source(self, tmp_path):
        source = tmp_path / "missing.txt"
        dest = tmp_path / "archive" / "missing.txt"
        assert archive_file(source, dest) is False

    def test_archive_source_is_directory(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        dest = tmp_path / "archive" / "subdir"
        assert archive_file(subdir, dest) is False

    def test_archive_creates_parent_dirs(self, tmp_path):
        source = tmp_path / "source.txt"
        source.write_text("content")
        dest = tmp_path / "deep" / "nested" / "archive" / "source.txt"
        result = archive_file(source, dest)
        assert result is True
        assert dest.exists()

    def test_archive_preserves_content(self, tmp_path):
        source = tmp_path / "source.txt"
        source.write_text("important data")
        dest = tmp_path / "archive" / "source.txt"
        archive_file(source, dest)
        assert dest.read_text() == "important data"
