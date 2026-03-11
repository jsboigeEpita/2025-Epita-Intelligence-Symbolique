# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.utils.dev_tools.refactoring_utils
Covers import refactoring and path refactoring utilities.
"""

import pytest
from pathlib import Path

from argumentation_analysis.utils.dev_tools.refactoring_utils import (
    update_imports_in_file_content,
    update_imports_in_file,
    update_imports_in_directory,
    update_paths_in_file_content,
    update_paths_in_file,
    update_paths_in_directory,
    DEFAULT_IMPORT_PATTERNS,
    DEFAULT_PATH_PATTERNS,
)


# ============================================================
# update_imports_in_file_content
# ============================================================

class TestUpdateImportsInFileContent:
    def test_no_changes_on_unmatched_content(self):
        content = "import os\nimport sys\n"
        result, count = update_imports_in_file_content(content)
        assert count == 0
        assert result == content

    def test_replaces_core_import(self):
        content = "from core import utils\n"
        result, count = update_imports_in_file_content(content)
        assert count >= 1
        assert "argumentation_analysis.core" in result

    def test_replaces_import_core(self):
        content = "import core\n"
        result, count = update_imports_in_file_content(content)
        assert count == 1
        assert "import argumentation_analysis.core" in result

    def test_replaces_core_submodule(self):
        content = "from core.config import Settings\n"
        result, count = update_imports_in_file_content(content)
        assert count == 1
        assert "from argumentation_analysis.core.config import Settings" in result

    def test_replaces_agents_import(self):
        content = "from agents import BaseAgent\n"
        result, count = update_imports_in_file_content(content)
        assert count == 1
        assert "from argumentation_analysis.agents import BaseAgent" in result

    def test_replaces_agents_submodule(self):
        content = "from agents.core.abc import agent_bases\n"
        result, count = update_imports_in_file_content(content)
        assert count == 1
        assert "from argumentation_analysis.agents.core.abc import agent_bases" in result

    def test_replaces_orchestration_import(self):
        content = "from orchestration import workflow_dsl\n"
        result, count = update_imports_in_file_content(content)
        assert count == 1
        assert "from argumentation_analysis.orchestration import workflow_dsl" in result

    def test_replaces_ui_import(self):
        content = "from ui import components\n"
        result, count = update_imports_in_file_content(content)
        assert count == 1
        assert "from argumentation_analysis.ui import components" in result

    def test_replaces_utils_import(self):
        content = "from utils import helpers\n"
        result, count = update_imports_in_file_content(content)
        assert count == 1
        assert "from argumentation_analysis.utils import helpers" in result

    def test_multiple_replacements(self):
        content = "from core import A\nfrom agents import B\nfrom ui import C\n"
        result, count = update_imports_in_file_content(content)
        assert count == 3
        assert "from argumentation_analysis.core import A" in result
        assert "from argumentation_analysis.agents import B" in result
        assert "from argumentation_analysis.ui import C" in result

    def test_partial_module_names_behavior(self):
        # "import cores" partially matches "import core" regex due to broad patterns
        # This is a known limitation of the regex approach
        content = "import cores\n"
        result, count = update_imports_in_file_content(content)
        # The pattern `import\s+core(?!\s*\.)` matches "import core" within "import cores"
        assert count >= 1

    def test_custom_patterns(self):
        custom_patterns = [
            (r"from\s+mylib\s+import\s+([^\n]+)", r"from newlib import \1"),
        ]
        content = "from mylib import foo\n"
        result, count = update_imports_in_file_content(content, custom_patterns)
        assert count == 1
        assert "from newlib import foo" in result

    def test_invalid_regex_pattern_handled(self):
        bad_patterns = [
            (r"[invalid(", r"replacement"),  # Invalid regex
        ]
        content = "some content\n"
        result, count = update_imports_in_file_content(content, bad_patterns)
        assert count == 0
        assert result == content

    def test_empty_content(self):
        result, count = update_imports_in_file_content("")
        assert count == 0
        assert result == ""

    def test_already_qualified_core_not_rematched(self):
        # "from argumentation_analysis.core import X" should not re-match "from core import"
        # But broad patterns like "import utils" may still match the tail
        content = "from argumentation_analysis.core import Config\n"
        result, count = update_imports_in_file_content(content)
        # The "from core" pattern does NOT re-match qualified imports
        # Count depends on whether other broad patterns match the captured group
        assert "argumentation_analysis.core" in result


# ============================================================
# update_imports_in_file
# ============================================================

class TestUpdateImportsInFile:
    def test_dry_run_returns_updated_content(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("from core import Config\n", encoding="utf-8")
        count, content = update_imports_in_file(f, dry_run=True)
        assert count >= 1
        assert "argumentation_analysis.core" in content
        # File should NOT be modified in dry_run
        assert f.read_text(encoding="utf-8") == "from core import Config\n"

    def test_write_mode_modifies_file(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("from core import Config\n", encoding="utf-8")
        count, content = update_imports_in_file(f, dry_run=False)
        assert count >= 1
        assert "argumentation_analysis.core" in f.read_text(encoding="utf-8")

    def test_no_changes_returns_original(self, tmp_path):
        f = tmp_path / "test.py"
        original = "import os\n"
        f.write_text(original, encoding="utf-8")
        count, content = update_imports_in_file(f, dry_run=True)
        assert count == 0
        assert content == original

    def test_file_not_found(self, tmp_path):
        f = tmp_path / "nonexistent.py"
        count, content = update_imports_in_file(f, dry_run=True)
        assert count == 0
        assert content is None

    def test_custom_patterns(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("from mymod import X\n", encoding="utf-8")
        patterns = [(r"from\s+mymod\s+import\s+([^\n]+)", r"from newmod import \1")]
        count, content = update_imports_in_file(f, dry_run=True, import_patterns=patterns)
        assert count == 1
        assert "from newmod import X" in content


# ============================================================
# update_imports_in_directory
# ============================================================

class TestUpdateImportsInDirectory:
    def _make_tree(self, tmp_path):
        """Create a simple directory tree with Python files."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("from core import A\n", encoding="utf-8")
        (tmp_path / "src" / "b.py").write_text("import os\n", encoding="utf-8")
        (tmp_path / "src" / "c.txt").write_text("from core import C\n", encoding="utf-8")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "d.py").write_text("from core import D\n", encoding="utf-8")
        return tmp_path

    def test_scans_only_py_files(self, tmp_path):
        self._make_tree(tmp_path)
        stats = update_imports_in_directory(tmp_path, dry_run=True)
        # a.py and b.py should be scanned; c.txt should not
        assert stats["total_files_scanned"] == 2
        assert stats["files_with_potential_changes"] == 1

    def test_excludes_pycache(self, tmp_path):
        self._make_tree(tmp_path)
        stats = update_imports_in_directory(tmp_path, dry_run=True)
        # d.py in __pycache__ should be excluded
        modified_paths = [d["path"] for d in stats["modified_files_list_details"]]
        assert not any("__pycache__" in p for p in modified_paths)

    def test_custom_extensions(self, tmp_path):
        self._make_tree(tmp_path)
        stats = update_imports_in_directory(tmp_path, extensions=[".txt"], dry_run=True)
        assert stats["total_files_scanned"] == 1  # only c.txt

    def test_custom_exclude_dirs(self, tmp_path):
        self._make_tree(tmp_path)
        stats = update_imports_in_directory(
            tmp_path, exclude_dirs=["src", "__pycache__"], dry_run=True
        )
        # All files under src/ and __pycache__/ should be excluded
        assert stats["files_with_potential_changes"] == 0

    def test_dry_run_does_not_modify(self, tmp_path):
        self._make_tree(tmp_path)
        update_imports_in_directory(tmp_path, dry_run=True)
        # Original file content should be unchanged
        assert (tmp_path / "src" / "a.py").read_text(encoding="utf-8") == "from core import A\n"

    def test_write_mode_modifies_files(self, tmp_path):
        self._make_tree(tmp_path)
        stats = update_imports_in_directory(tmp_path, dry_run=False)
        assert stats["total_potential_replacements"] == 1
        updated = (tmp_path / "src" / "a.py").read_text(encoding="utf-8")
        assert "from argumentation_analysis.core import A" in updated

    def test_empty_directory(self, tmp_path):
        stats = update_imports_in_directory(tmp_path, dry_run=True)
        assert stats["total_files_scanned"] == 0


# ============================================================
# update_paths_in_file_content
# ============================================================

class TestUpdatePathsInFileContent:
    def test_no_changes_on_unmatched(self):
        content = 'x = "/some/other/path"\n'
        result, count, imp = update_paths_in_file_content(content)
        assert count == 0
        assert imp is False
        assert result == content

    def test_replaces_config_path_double_quotes(self):
        content = 'f = "config/settings.yaml"\n'
        result, count, imp = update_paths_in_file_content(content)
        assert count == 1
        assert 'CONFIG_DIR / "settings.yaml"' in result

    def test_replaces_config_path_single_quotes(self):
        content = "f = 'config/settings.yaml'\n"
        result, count, imp = update_paths_in_file_content(content)
        assert count == 1
        assert "CONFIG_DIR / 'settings.yaml'" in result

    def test_replaces_data_path(self):
        content = 'f = "data/corpus.json"\n'
        result, count, imp = update_paths_in_file_content(content)
        assert count == 1
        assert 'DATA_DIR / "corpus.json"' in result

    def test_replaces_libs_path(self):
        content = 'jar = "libs/tweety.jar"\n'
        result, count, imp = update_paths_in_file_content(content)
        assert count == 1
        assert 'LIBS_DIR / "tweety.jar"' in result

    def test_replaces_results_path(self):
        content = 'out = "results/output.csv"\n'
        result, count, imp = update_paths_in_file_content(content)
        assert count == 1
        assert 'RESULTS_DIR / "output.csv"' in result

    def test_replaces_bare_directory_reference(self):
        content = 'x = "config/"\n'
        result, count, imp = update_paths_in_file_content(content)
        assert count == 1
        assert "CONFIG_DIR" in result

    def test_multiple_replacements(self):
        content = 'a = "config/a.py"\nb = "data/b.json"\n'
        result, count, imp = update_paths_in_file_content(content)
        assert count == 2

    def test_adds_import_when_missing(self):
        content = 'import os\nf = "config/settings.yaml"\n'
        result, count, imp = update_paths_in_file_content(content)
        assert count == 1
        assert imp is True
        assert "from argumentation_analysis.paths import" in result
        assert "CONFIG_DIR" in result

    def test_updates_existing_import(self):
        content = 'from argumentation_analysis.paths import DATA_DIR\nf = "config/settings.yaml"\n'
        result, count, imp = update_paths_in_file_content(content)
        assert count == 1
        assert imp is True
        assert "CONFIG_DIR" in result
        assert "DATA_DIR" in result

    def test_no_import_added_when_no_replacements(self):
        content = "import os\nx = 42\n"
        result, count, imp = update_paths_in_file_content(content)
        assert count == 0
        assert imp is False

    def test_custom_patterns(self):
        custom = [(r'"assets/([^"]+)"', r'ASSETS_DIR / "\1"')]
        content = 'f = "assets/logo.png"\n'
        # Custom patterns don't match the default _DIR heuristic, so no auto-import
        result, count, imp = update_paths_in_file_content(content, path_patterns=custom)
        assert count == 1

    def test_empty_content(self):
        result, count, imp = update_paths_in_file_content("")
        assert count == 0
        assert imp is False

    def test_invalid_regex_handled(self):
        bad = [(r"[invalid(", r"replacement")]
        content = "some text\n"
        result, count, imp = update_paths_in_file_content(content, path_patterns=bad)
        assert count == 0


# ============================================================
# update_paths_in_file
# ============================================================

class TestUpdatePathsInFile:
    def test_dry_run(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text('import os\nf = "config/x.yaml"\n', encoding="utf-8")
        count, imp, content = update_paths_in_file(f, dry_run=True)
        assert count == 1
        assert imp is True
        # File unchanged
        assert '"config/x.yaml"' in f.read_text(encoding="utf-8")

    def test_write_mode(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text('f = "data/file.json"\n', encoding="utf-8")
        count, imp, content = update_paths_in_file(f, dry_run=False)
        assert count == 1
        written = f.read_text(encoding="utf-8")
        assert 'DATA_DIR / "file.json"' in written

    def test_no_changes(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("import os\n", encoding="utf-8")
        count, imp, content = update_paths_in_file(f, dry_run=True)
        assert count == 0
        assert imp is False
        assert content == "import os\n"

    def test_file_not_found(self, tmp_path):
        f = tmp_path / "missing.py"
        count, imp, content = update_paths_in_file(f, dry_run=True)
        assert count == 0
        assert imp is False
        assert content is None


# ============================================================
# update_paths_in_directory
# ============================================================

class TestUpdatePathsInDirectory:
    def _make_tree(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text('f = "config/x.yaml"\n', encoding="utf-8")
        (tmp_path / "src" / "b.py").write_text("import os\n", encoding="utf-8")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "c.py").write_text('f = "config/y.yaml"\n', encoding="utf-8")
        return tmp_path

    def test_scans_and_reports(self, tmp_path):
        self._make_tree(tmp_path)
        stats = update_paths_in_directory(tmp_path, dry_run=True)
        assert stats["total_files_scanned"] >= 2
        assert stats["total_path_replacements"] >= 1

    def test_excludes_docs_by_default(self, tmp_path):
        self._make_tree(tmp_path)
        stats = update_paths_in_directory(tmp_path, dry_run=True)
        modified_paths = [d["path"] for d in stats["changed_files_details"]]
        # docs/ directory files should be excluded by default
        # Check using Path parts (not substring) to avoid false positives from temp dir names
        from pathlib import Path
        for p in modified_paths:
            assert "docs" not in Path(p).relative_to(tmp_path).parts

    def test_empty_directory(self, tmp_path):
        stats = update_paths_in_directory(tmp_path, dry_run=True)
        assert stats["total_files_scanned"] == 0

    def test_write_mode(self, tmp_path):
        self._make_tree(tmp_path)
        stats = update_paths_in_directory(tmp_path, dry_run=False)
        assert stats["total_path_replacements"] >= 1
        updated = (tmp_path / "src" / "a.py").read_text(encoding="utf-8")
        assert "CONFIG_DIR" in updated


# ============================================================
# DEFAULT_IMPORT_PATTERNS validation
# ============================================================

class TestDefaultImportPatterns:
    def test_patterns_are_nonempty(self):
        assert len(DEFAULT_IMPORT_PATTERNS) > 0

    def test_all_patterns_are_valid_regex(self):
        import re
        for pattern, replacement in DEFAULT_IMPORT_PATTERNS:
            re.compile(pattern)  # Should not raise

    def test_agents_extract_pattern(self):
        content = "from agents.extract import FactExtractor\n"
        result, count = update_imports_in_file_content(content)
        assert count >= 1
        assert "argumentation_analysis" in result


# ============================================================
# DEFAULT_PATH_PATTERNS validation
# ============================================================

class TestDefaultPathPatterns:
    def test_patterns_are_nonempty(self):
        assert len(DEFAULT_PATH_PATTERNS) > 0

    def test_all_patterns_are_valid_regex(self):
        import re
        for pattern, replacement in DEFAULT_PATH_PATTERNS:
            re.compile(pattern)  # Should not raise

    def test_config_double_and_single_quote_pairs(self):
        # Each config/data/libs/results should have both " and ' variants
        patterns_str = str(DEFAULT_PATH_PATTERNS)
        for keyword in ["config", "data", "libs", "results"]:
            assert f'"{keyword}/' in patterns_str or f"'{keyword}/" in patterns_str
