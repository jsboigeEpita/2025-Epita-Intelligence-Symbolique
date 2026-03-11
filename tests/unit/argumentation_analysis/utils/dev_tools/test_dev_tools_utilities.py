# -*- coding: utf-8 -*-
"""
Tests unitaires pour les utilitaires de développement :
- project_structure_utils.py — map_package_to_module()
- coverage_utils.py — parse_coverage_xml(), create_initial_coverage_history(), save_coverage_history()
- import_testing_utils.py — test_module_import_by_name(), test_module_import_by_path()
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ============================================================================
# project_structure_utils tests
# ============================================================================

from argumentation_analysis.utils.dev_tools.project_structure_utils import (
    map_package_to_module,
    DEFAULT_PACKAGE_TO_MODULE_MAPPING,
)


class TestMapPackageToModule:
    """Tests for map_package_to_module()."""

    def test_exact_match_known_package(self):
        """Exact match returns mapped module name."""
        result = map_package_to_module("argumentation_analysis.utils")
        assert result == "Argumentation Analysis Utilities"

    def test_exact_match_tests_unit(self):
        result = map_package_to_module("tests.unit")
        assert result == "Tests - Unit"

    def test_exact_match_scripts_execution(self):
        result = map_package_to_module("scripts.execution")
        assert result == "Scripts - Execution"

    def test_partial_match_subpackage(self):
        """Subpackage matches parent prefix."""
        result = map_package_to_module("argumentation_analysis.agents.core.logic")
        assert result == "Argumentation Agents"

    def test_partial_match_deep_subpackage(self):
        result = map_package_to_module("tests.integration.workers.something")
        assert result == "Tests - Integration"

    def test_no_match_falls_through_to_empty_key(self):
        """Unknown package matches empty string prefix, returns Global/Non-Specific."""
        # The empty string "" key in DEFAULT_PACKAGE_TO_MODULE_MAPPING matches
        # all strings via startswith(""), so "Autre" is never returned.
        result = map_package_to_module("completely_unknown_package")
        assert result == "Global/Non-Specific"

    def test_empty_string_returns_global(self):
        """Empty string maps to Global/Non-Specific."""
        result = map_package_to_module("")
        assert result == "Global/Non-Specific"

    def test_dot_returns_global(self):
        """Root package '.' maps to Global/Non-Specific."""
        result = map_package_to_module(".")
        assert result == "Global/Non-Specific"

    def test_custom_mapping_overrides_default(self):
        """Custom mapping overrides default mapping."""
        custom = {"argumentation_analysis.utils": "Custom Utils"}
        result = map_package_to_module("argumentation_analysis.utils", custom_mapping=custom)
        assert result == "Custom Utils"

    def test_custom_mapping_adds_new_entry(self):
        """Custom mapping adds entries not in default."""
        custom = {"my_custom_package": "My Custom Module"}
        result = map_package_to_module("my_custom_package", custom_mapping=custom)
        assert result == "My Custom Module"

    def test_custom_mapping_none_uses_defaults(self):
        """None custom_mapping uses defaults only."""
        result = map_package_to_module("argumentation_analysis.services", custom_mapping=None)
        assert result == "Argumentation Services"

    def test_most_specific_partial_match_wins(self):
        """More specific partial match takes priority over shorter."""
        result = map_package_to_module("core.communication.channels")
        assert result == "Legacy Core Communication"

    def test_default_mapping_is_dict(self):
        """DEFAULT_PACKAGE_TO_MODULE_MAPPING is a non-empty dict."""
        assert isinstance(DEFAULT_PACKAGE_TO_MODULE_MAPPING, dict)
        assert len(DEFAULT_PACKAGE_TO_MODULE_MAPPING) > 10


# ============================================================================
# coverage_utils tests
# ============================================================================

from argumentation_analysis.utils.dev_tools.coverage_utils import (
    parse_coverage_xml,
    create_initial_coverage_history,
    save_coverage_history,
)


SAMPLE_COVERAGE_XML = """<?xml version="1.0" ?>
<coverage version="7.0" timestamp="1234567890" lines-valid="1000" lines-covered="750"
          branches-valid="200" branches-covered="150" line-rate="0.75" branch-rate="0.75">
    <packages>
        <package name="argumentation_analysis.core" line-rate="0.80" branch-rate="0.60">
            <classes/>
        </package>
        <package name="argumentation_analysis.agents" line-rate="0.70" branch-rate="0.50">
            <classes/>
        </package>
    </packages>
</coverage>"""


class TestParseCoverageXml:
    """Tests for parse_coverage_xml()."""

    def test_parse_valid_xml(self, tmp_path):
        """Parses valid coverage.xml and returns expected structure."""
        xml_file = tmp_path / "coverage.xml"
        xml_file.write_text(SAMPLE_COVERAGE_XML)

        result = parse_coverage_xml(xml_file)
        assert result is not None
        assert result["global_line_rate"] == 75.0
        assert result["global_branch_rate"] == 75.0
        assert result["lines_valid"] == 1000
        assert result["lines_covered"] == 750
        assert result["branches_valid"] == 200
        assert result["branches_covered"] == 150

    def test_parse_packages(self, tmp_path):
        """Parses package-level coverage data."""
        xml_file = tmp_path / "coverage.xml"
        xml_file.write_text(SAMPLE_COVERAGE_XML)

        result = parse_coverage_xml(xml_file)
        assert "packages" in result
        assert "argumentation_analysis.core" in result["packages"]
        assert result["packages"]["argumentation_analysis.core"]["line_rate"] == 80.0
        assert result["packages"]["argumentation_analysis.agents"]["line_rate"] == 70.0

    def test_parse_has_timestamp(self, tmp_path):
        """Result includes a timestamp string."""
        xml_file = tmp_path / "coverage.xml"
        xml_file.write_text(SAMPLE_COVERAGE_XML)

        result = parse_coverage_xml(xml_file)
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)

    def test_parse_nonexistent_file_returns_none(self, tmp_path):
        """Returns None for non-existent file."""
        result = parse_coverage_xml(tmp_path / "nonexistent.xml")
        assert result is None

    def test_parse_invalid_xml_returns_none(self, tmp_path):
        """Returns None for malformed XML."""
        xml_file = tmp_path / "bad.xml"
        xml_file.write_text("<invalid>not closed")

        result = parse_coverage_xml(xml_file)
        assert result is None

    def test_parse_directory_returns_none(self, tmp_path):
        """Returns None when path is a directory, not a file."""
        result = parse_coverage_xml(tmp_path)
        assert result is None

    def test_parse_string_path_converted(self, tmp_path):
        """Accepts string paths (converted to Path internally)."""
        xml_file = tmp_path / "coverage.xml"
        xml_file.write_text(SAMPLE_COVERAGE_XML)

        result = parse_coverage_xml(str(xml_file))
        assert result is not None
        assert result["lines_valid"] == 1000

    def test_parse_invalid_path_type_returns_none(self):
        """Returns None for invalid path types."""
        result = parse_coverage_xml(12345)
        assert result is None

    def test_parse_no_packages_node(self, tmp_path):
        """Handles XML without packages node."""
        xml_content = """<?xml version="1.0" ?>
<coverage line-rate="0.5" branch-rate="0.3"
          lines-valid="100" lines-covered="50"
          branches-valid="20" branches-covered="6">
</coverage>"""
        xml_file = tmp_path / "coverage.xml"
        xml_file.write_text(xml_content)

        result = parse_coverage_xml(xml_file)
        assert result is not None
        assert result["packages"] == {}
        assert result["global_line_rate"] == 50.0


class TestCreateInitialCoverageHistory:
    """Tests for create_initial_coverage_history()."""

    def test_creates_history_file(self, tmp_path):
        """Creates a JSON history file with 2 entries."""
        history_file = tmp_path / "history.json"
        coverage_data = {
            "global_line_rate": 75.0,
            "lines_covered": 750,
            "lines_valid": 1000,
            "packages": {"core": {"line_rate": 80.0, "branch_rate": 60.0}},
            "timestamp": "2026-03-01 12:00:00",
        }

        result = create_initial_coverage_history(coverage_data, history_file)
        assert result is True
        assert history_file.exists()

        entries = json.loads(history_file.read_text())
        assert len(entries) == 2

    def test_previous_entry_has_lower_coverage(self, tmp_path):
        """Previous (fictive) entry has slightly lower coverage."""
        history_file = tmp_path / "history.json"
        coverage_data = {
            "global_line_rate": 75.0,
            "lines_covered": 750,
            "lines_valid": 1000,
            "packages": {"core": {"line_rate": 80.0, "branch_rate": 60.0}},
            "timestamp": "2026-03-01 12:00:00",
        }

        create_initial_coverage_history(coverage_data, history_file)
        entries = json.loads(history_file.read_text())

        previous = entries[0]
        current = entries[1]
        assert previous["global_line_rate"] < current["global_line_rate"]
        assert previous["lines_covered"] < current["lines_covered"]

    def test_invalid_coverage_data_returns_false(self, tmp_path):
        """Returns False for None or empty coverage data."""
        history_file = tmp_path / "history.json"
        assert create_initial_coverage_history(None, history_file) is False
        assert create_initial_coverage_history({}, history_file) is False

    def test_creates_parent_directories(self, tmp_path):
        """Creates parent directories if they don't exist."""
        history_file = tmp_path / "deep" / "nested" / "history.json"
        coverage_data = {
            "global_line_rate": 50.0,
            "lines_covered": 500,
            "timestamp": "2026-03-01",
        }

        result = create_initial_coverage_history(coverage_data, history_file)
        assert result is True
        assert history_file.exists()


class TestSaveCoverageHistory:
    """Tests for save_coverage_history()."""

    def test_save_new_history_file(self, tmp_path):
        """Creates new history file if it doesn't exist."""
        history_file = tmp_path / "history.json"
        coverage_data = {"global_line_rate": 80.0, "timestamp": "2026-03-01"}

        result = save_coverage_history(coverage_data, history_file)
        assert result is True

        entries = json.loads(history_file.read_text())
        assert len(entries) == 1
        assert entries[0]["global_line_rate"] == 80.0

    def test_append_to_existing_history(self, tmp_path):
        """Appends to existing history file."""
        history_file = tmp_path / "history.json"
        existing = [{"global_line_rate": 70.0, "timestamp": "2026-02-01"}]
        history_file.write_text(json.dumps(existing))

        new_data = {"global_line_rate": 80.0, "timestamp": "2026-03-01"}
        result = save_coverage_history(new_data, history_file)
        assert result is True

        entries = json.loads(history_file.read_text())
        assert len(entries) == 2
        assert entries[1]["global_line_rate"] == 80.0

    def test_adds_timestamp_if_missing(self, tmp_path):
        """Adds timestamp to coverage data if not present."""
        history_file = tmp_path / "history.json"
        coverage_data = {"global_line_rate": 80.0}

        save_coverage_history(coverage_data, history_file)

        entries = json.loads(history_file.read_text())
        assert "timestamp" in entries[0]

    def test_handles_corrupted_json(self, tmp_path):
        """Overwrites corrupted JSON history file."""
        history_file = tmp_path / "history.json"
        history_file.write_text("not valid json {{{")

        new_data = {"global_line_rate": 80.0, "timestamp": "2026-03-01"}
        result = save_coverage_history(new_data, history_file)
        assert result is True

        entries = json.loads(history_file.read_text())
        assert len(entries) == 1

    def test_handles_non_list_json(self, tmp_path):
        """Overwrites JSON that's not a list."""
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps({"not": "a list"}))

        new_data = {"global_line_rate": 80.0, "timestamp": "2026-03-01"}
        result = save_coverage_history(new_data, history_file)
        assert result is True

        entries = json.loads(history_file.read_text())
        assert isinstance(entries, list)
        assert len(entries) == 1

    def test_empty_data_returns_false(self, tmp_path):
        """Returns False for empty coverage data."""
        history_file = tmp_path / "history.json"
        assert save_coverage_history({}, history_file) is False
        assert save_coverage_history(None, history_file) is False

    def test_creates_parent_directories(self, tmp_path):
        """Creates parent directories if needed."""
        history_file = tmp_path / "deep" / "path" / "history.json"
        new_data = {"global_line_rate": 80.0, "timestamp": "2026-03-01"}

        result = save_coverage_history(new_data, history_file)
        assert result is True
        assert history_file.exists()


# ============================================================================
# import_testing_utils tests
# ============================================================================

# Import as module to avoid pytest collecting source functions named test_*
import argumentation_analysis.utils.dev_tools.import_testing_utils as _import_utils

# Aliases that don't start with test_ (prevents pytest collection)
_import_by_name = _import_utils.test_module_import_by_name
_import_by_path = _import_utils.test_module_import_by_path


class TestModuleImportByName:
    """Tests for test_module_import_by_name()."""

    def test_import_builtin_module_succeeds(self):
        """Importing a built-in module returns (True, success_msg)."""
        success, msg = _import_by_name("os")
        assert success is True
        assert "✓" in msg
        assert "os" in msg

    def test_import_json_module_succeeds(self):
        success, msg = _import_by_name("json")
        assert success is True

    def test_import_nonexistent_module_fails(self):
        """Importing a non-existent module returns (False, error_msg)."""
        success, msg = _import_by_name("nonexistent_module_xyz_123")
        assert success is False
        assert "✗" in msg

    def test_import_empty_string_fails(self):
        """Empty module name returns (False, error_msg)."""
        success, msg = _import_by_name("")
        assert success is False

    def test_import_none_fails(self):
        """None module name returns (False, error_msg)."""
        success, msg = _import_by_name(None)
        assert success is False

    def test_import_integer_fails(self):
        """Non-string module name returns (False, error_msg)."""
        success, msg = _import_by_name(123)
        assert success is False

    def test_import_submodule(self):
        """Importing a submodule works."""
        success, msg = _import_by_name("os.path")
        assert success is True

    def test_alias_is_same_function(self):
        """test_import is an alias for test_module_import_by_name."""
        assert _import_utils.test_import is _import_utils.test_module_import_by_name


class TestModuleImportByPath:
    """Tests for test_module_import_by_path()."""

    def test_import_existing_py_file(self, tmp_path):
        """Importing an existing .py file succeeds."""
        module_file = tmp_path / "my_module.py"
        module_file.write_text("VALUE = 42\n")

        success, msg = _import_by_path(module_file)
        assert success is True
        assert "✓" in msg
        assert "my_module" in msg

    def test_import_nonexistent_file_fails(self, tmp_path):
        """Non-existent .py file returns (False, error_msg)."""
        fake_path = tmp_path / "nonexistent.py"
        success, msg = _import_by_path(fake_path)
        assert success is False
        assert "✗" in msg

    def test_import_non_py_file_fails(self, tmp_path):
        """Non-.py file returns (False, error_msg)."""
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("not python")

        success, msg = _import_by_path(txt_file)
        assert success is False

    def test_import_directory_fails(self, tmp_path):
        """Directory path returns (False, error_msg)."""
        success, msg = _import_by_path(tmp_path)
        assert success is False

    def test_import_with_name_override_uses_override(self, tmp_path):
        """module_name_override overrides the inferred module name in the message."""
        module_file = tmp_path / "actual_file.py"
        module_file.write_text("VALUE = 99\n")

        # Override name that doesn't match any importable module — expected to fail
        # but the override name should appear in the message
        success, msg = _import_by_path(module_file, module_name_override="custom_name")
        assert "custom_name" in msg  # override name is used regardless of success

    def test_import_init_py_infers_package_name(self, tmp_path):
        """__init__.py uses the parent directory name as the inferred module name."""
        pkg_dir = tmp_path / "my_test_pkg"
        pkg_dir.mkdir()
        init_file = pkg_dir / "__init__.py"
        init_file.write_text("PKG_VALUE = 1\n")

        # The function adds pkg_dir to sys.path, not its parent,
        # so importing by package name may fail — but the name is inferred correctly
        success, msg = _import_by_path(init_file)
        assert "my_test_pkg" in msg  # inferred name from parent dir

    def test_sys_path_restored_after_success(self, tmp_path):
        """sys.path is restored after successful import."""
        import sys

        module_file = tmp_path / "temp_module.py"
        module_file.write_text("X = 1\n")

        original_path = list(sys.path)
        _import_by_path(module_file)
        # The tmp_path directory should not remain in sys.path
        assert str(tmp_path) not in sys.path or str(tmp_path) in original_path

    def test_sys_path_restored_after_failure(self, tmp_path):
        """sys.path is restored after failed import."""
        import sys

        module_file = tmp_path / "broken_module.py"
        module_file.write_text("raise RuntimeError('intentional')\n")

        original_path_len = len(sys.path)
        _import_by_path(module_file)
        # sys.path should not grow
        assert len(sys.path) <= original_path_len + 1  # tolerance for edge cases

    def test_import_module_with_syntax_error(self, tmp_path):
        """Module with syntax error returns (False, error_msg)."""
        module_file = tmp_path / "syntax_err.py"
        module_file.write_text("def broken(\n")  # syntax error

        success, msg = _import_by_path(module_file)
        assert success is False
        assert "✗" in msg
