# -*- coding: utf-8 -*-
"""
Unit tests for Demo EPITA modules.

Tests the 6 demo category modules by mocking `executer_tests` (the subprocess
test runner) and verifying each module's `run_demo_rapide` function returns
correct results.
"""

import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure demo modules are importable
project_root = Path(__file__).resolve().parent.parent.parent
demo_modules_dir = (
    project_root
    / "examples"
    / "02_core_system_demos"
    / "scripts_demonstration"
    / "modules"
)
demo_scripts_dir = demo_modules_dir.parent

# Add paths needed for demo module imports
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(demo_modules_dir) not in sys.path:
    sys.path.insert(0, str(demo_modules_dir))
if str(demo_scripts_dir) not in sys.path:
    sys.path.insert(0, str(demo_scripts_dir))


def _mock_executer_tests_success(pattern_tests, logger=None, timeout=300):
    """Mock executer_tests that always returns success."""
    return True, {
        "passed": 3,
        "failed": 0,
        "total": 3,
        "duration": 1.5,
        "details": ["test_a PASSED", "test_b PASSED", "test_c PASSED"],
    }


def _mock_executer_tests_partial(pattern_tests, logger=None, timeout=300):
    """Mock executer_tests that returns partial failure."""
    return False, {
        "passed": 2,
        "failed": 1,
        "total": 3,
        "duration": 2.0,
        "details": ["test_a PASSED", "test_b FAILED", "test_c PASSED"],
    }


# ============================================================
# Tests for demo_tests_validation
# ============================================================


class TestDemoTestsValidation:
    """Tests for the Tests & Validation demo module."""

    @patch(
        "demo_tests_validation.executer_tests", side_effect=_mock_executer_tests_success
    )
    def test_run_demo_rapide_success(self, mock_exec):
        from demo_tests_validation import run_demo_rapide

        result = run_demo_rapide()
        assert result is True
        assert mock_exec.call_count >= 1

    @patch(
        "demo_tests_validation.executer_tests", side_effect=_mock_executer_tests_partial
    )
    def test_run_demo_rapide_with_failures(self, mock_exec):
        from demo_tests_validation import run_demo_rapide

        result = run_demo_rapide()
        # Should still return a bool (may be True or False depending on module logic)
        assert isinstance(result, bool)


# ============================================================
# Tests for demo_services_core
# ============================================================


class TestDemoServicesCore:
    """Tests for the Services Core demo module."""

    @patch(
        "demo_services_core.executer_tests", side_effect=_mock_executer_tests_success
    )
    def test_run_demo_rapide_success(self, mock_exec):
        from demo_services_core import run_demo_rapide

        result = run_demo_rapide()
        assert result is True

    @patch(
        "demo_services_core.executer_tests", side_effect=_mock_executer_tests_partial
    )
    def test_run_demo_rapide_partial_failure(self, mock_exec):
        from demo_services_core import run_demo_rapide

        result = run_demo_rapide()
        assert isinstance(result, bool)


# ============================================================
# Tests for demo_cas_usage
# ============================================================


class TestDemoCasUsage:
    """Tests for the Cas d'Usage demo module."""

    @patch("demo_cas_usage.executer_tests", side_effect=_mock_executer_tests_success)
    def test_run_demo_rapide_success(self, mock_exec):
        from demo_cas_usage import run_demo_rapide

        result = run_demo_rapide()
        assert result is True

    @patch("demo_cas_usage.executer_tests", side_effect=_mock_executer_tests_partial)
    def test_run_demo_rapide_partial(self, mock_exec):
        from demo_cas_usage import run_demo_rapide

        result = run_demo_rapide()
        assert isinstance(result, bool)


# ============================================================
# Tests for demo_outils_utils
# ============================================================


class TestDemoOutilsUtils:
    """Tests for the Outils & Utilitaires demo module."""

    @patch("demo_utils.executer_tests", side_effect=_mock_executer_tests_success)
    def test_run_demo_rapide_default(self, mock_exec):
        from demo_outils_utils import run_demo_rapide

        result = run_demo_rapide()
        assert result is True

    @patch("demo_utils.executer_tests", side_effect=_mock_executer_tests_success)
    def test_run_demo_rapide_with_custom_data(self, mock_exec):
        from demo_outils_utils import run_demo_rapide

        result = run_demo_rapide(custom_data="Test data for hashing")
        assert result is True


# ============================================================
# Tests for demo_integrations
# ============================================================


class TestDemoIntegrations:
    """Tests for the Integrations demo module."""

    @patch("demo_utils.executer_tests", side_effect=_mock_executer_tests_success)
    def test_run_demo_rapide_default(self, mock_exec):
        from demo_integrations import run_demo_rapide

        result = run_demo_rapide()
        assert result is True

    @patch("demo_utils.executer_tests", side_effect=_mock_executer_tests_success)
    def test_run_demo_rapide_with_custom_data(self, mock_exec):
        from demo_integrations import run_demo_rapide

        result = run_demo_rapide(custom_data="Integration test payload")
        assert result is True


# ============================================================
# Tests for demo_utils itself
# ============================================================


class TestDemoUtils:
    """Tests for the demo utility functions."""

    def test_colors_defined(self):
        from demo_utils import Colors

        assert hasattr(Colors, "CYAN")
        assert hasattr(Colors, "GREEN")
        assert hasattr(Colors, "FAIL")
        assert hasattr(Colors, "ENDC")

    def test_symbols_defined(self):
        from demo_utils import Symbols

        assert hasattr(Symbols, "CHECK")
        assert hasattr(Symbols, "CROSS")
        assert hasattr(Symbols, "ROCKET")

    def test_demo_logger_creation(self):
        from demo_utils import DemoLogger

        logger = DemoLogger("test_module")
        assert logger is not None

    def test_charger_config_categories(self):
        # Must run from project root for the config path to resolve
        original_cwd = os.getcwd()
        try:
            os.chdir(str(project_root))
            from demo_utils import charger_config_categories

            config = charger_config_categories()
            assert config is not None
            assert "categories" in config
            assert len(config["categories"]) == 6
        finally:
            os.chdir(original_cwd)


# ============================================================
# Tests for EpitaValidator (from demonstration_epita.py)
# ============================================================


class TestEpitaValidator:
    """Tests for the EpitaValidator class in the main demo script."""

    def test_create_custom_datasets(self):
        # Add the demo scripts dir to path for import
        sys.path.insert(0, str(demo_scripts_dir))
        try:
            from demonstration_epita import EpitaValidator

            validator = EpitaValidator()
            datasets = validator.create_custom_datasets()
            assert len(datasets) == 3
            for ds in datasets:
                assert ds.name
                assert ds.content
                assert ds.marker
                assert ds.content_hash
        finally:
            sys.path.remove(str(demo_scripts_dir))

    def test_validator_indicators(self):
        sys.path.insert(0, str(demo_scripts_dir))
        try:
            from demonstration_epita import EpitaValidator

            validator = EpitaValidator()
            assert len(validator.real_indicators) > 0
            assert len(validator.mock_indicators) > 0
            assert "mock" in validator.mock_indicators
        finally:
            sys.path.remove(str(demo_scripts_dir))
