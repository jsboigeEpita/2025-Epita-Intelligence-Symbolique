# -*- coding: utf-8 -*-
"""
Unit tests for bootstrap module.

Tests cover:
- ProjectContext: initialization, lazy fallacy detector, services dict
- _load_tweety_classes(): JVM class loading with mocked jpype
- initialize_project_environment(): project root detection, JVM init,
  service creation, kernel setup, settings loading
"""

import sys
import threading
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from argumentation_analysis.core.bootstrap import (
    ProjectContext,
    _load_tweety_classes,
    _pre_init_safety_checks,
)

# ===========================================================================
# ProjectContext Tests
# ===========================================================================


class TestProjectContext:
    """Tests for ProjectContext class."""

    def test_init_defaults(self):
        ctx = ProjectContext()
        assert ctx.kernel is None
        assert ctx.jvm_initialized is False
        assert ctx.crypto_service is None
        assert ctx.definition_service is None
        assert ctx.llm_service is None
        assert ctx.tweety_classes == {}
        assert ctx.config == {}
        assert ctx.settings is None
        assert ctx.project_root_path is None
        assert ctx.services == {}

    def test_fallacy_detector_starts_none(self):
        ctx = ProjectContext()
        assert ctx._fallacy_detector_instance is None

    def test_get_fallacy_detector_returns_none_when_class_missing(self):
        """When ContextualFallacyDetector_class is None, returns None."""
        ctx = ProjectContext()
        with patch(
            "argumentation_analysis.core.bootstrap.ContextualFallacyDetector_class",
            None,
        ):
            result = ctx.get_fallacy_detector()
            assert result is None

    def test_get_fallacy_detector_lazy_init(self):
        """Detector is created on first call, cached on subsequent calls."""
        ctx = ProjectContext()
        mock_detector_class = MagicMock()
        mock_detector_instance = MagicMock()
        mock_detector_class.return_value = mock_detector_instance

        with patch(
            "argumentation_analysis.core.bootstrap.ContextualFallacyDetector_class",
            mock_detector_class,
        ):
            first_call = ctx.get_fallacy_detector()
            second_call = ctx.get_fallacy_detector()

        # Class is instantiated exactly once (lazy + cached)
        mock_detector_class.assert_called_once()
        assert first_call is second_call

    def test_get_fallacy_detector_handles_init_error(self):
        """If detector init raises, returns None gracefully."""
        ctx = ProjectContext()
        mock_detector_class = MagicMock(side_effect=RuntimeError("init failed"))

        with patch(
            "argumentation_analysis.core.bootstrap.ContextualFallacyDetector_class",
            mock_detector_class,
        ):
            result = ctx.get_fallacy_detector()
            assert result is None


# ===========================================================================
# _load_tweety_classes Tests
# ===========================================================================


class TestLoadTweetyClasses:
    """Tests for _load_tweety_classes()."""

    def test_skips_when_jvm_not_initialized(self):
        """Does nothing if context.jvm_initialized is False."""
        ctx = ProjectContext()
        ctx.jvm_initialized = False
        _load_tweety_classes(ctx)
        assert ctx.tweety_classes == {}

    def test_loads_aspic_parser_when_jvm_available(self):
        """Loads AspicParser into context.tweety_classes when JVM is up."""
        ctx = ProjectContext()
        ctx.jvm_initialized = True

        mock_jclass = MagicMock()
        mock_pl_parser = MagicMock()
        mock_formula_gen = MagicMock()
        mock_aspic_parser = MagicMock()

        # JClass returns different mocks for different class names
        def jclass_side_effect(class_name):
            if "PlParser" in class_name:
                return mock_pl_parser
            elif "PlFormulaGenerator" in class_name:
                return mock_formula_gen
            elif "AspicParser" in class_name:
                return mock_aspic_parser
            return MagicMock()

        mock_jclass.side_effect = jclass_side_effect

        mock_jpype = MagicMock()
        mock_jpype.JClass = mock_jclass

        with patch.dict(
            sys.modules,
            {"jpype": mock_jpype, "jpype.imports": MagicMock()},
        ):
            _load_tweety_classes(ctx)

        assert "AspicParser" in ctx.tweety_classes

    def test_handles_import_error(self):
        """Gracefully handles ImportError when jpype is not available."""
        ctx = ProjectContext()
        ctx.jvm_initialized = True

        # Simulate jpype import failing
        with patch.dict(sys.modules, {"jpype": None}):
            # This should not raise — errors are caught and logged
            _load_tweety_classes(ctx)

        assert ctx.tweety_classes == {}


# ===========================================================================
# initialize_project_environment Tests
# ===========================================================================


class TestInitializeProjectEnvironment:
    """Tests for initialize_project_environment()."""

    @pytest.fixture(autouse=True)
    def _reset_jvm_flag(self):
        """Reset sys._jvm_initialized before each test."""
        original = getattr(sys, "_jvm_initialized", None)
        if hasattr(sys, "_jvm_initialized"):
            delattr(sys, "_jvm_initialized")
        yield
        # Restore
        if original is not None:
            sys._jvm_initialized = original
        elif hasattr(sys, "_jvm_initialized"):
            delattr(sys, "_jvm_initialized")

    @pytest.fixture(autouse=True)
    def _bypass_safety_checks(self):
        """Bypass _pre_init_safety_checks which validates real filesystem paths.

        These tests focus on initialization logic, not path validation.
        Path validation is tested separately in TestPreInitSafetyChecks.
        """
        with patch(
            "argumentation_analysis.core.bootstrap._pre_init_safety_checks",
            return_value=True,
        ):
            yield

    def test_returns_project_context(self):
        """initialize_project_environment returns a ProjectContext."""
        with patch(
            "argumentation_analysis.core.bootstrap.initialize_jvm_func", None
        ), patch(
            "argumentation_analysis.core.bootstrap.CryptoService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.DefinitionService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.create_llm_service_func", None
        ), patch(
            "argumentation_analysis.core.bootstrap.sk_module", None
        ), patch(
            "argumentation_analysis.core.bootstrap.settings", None
        ), patch(
            "argumentation_analysis.core.bootstrap.ContextualFallacyDetector_class",
            None,
        ):
            from argumentation_analysis.core.bootstrap import (
                initialize_project_environment,
            )

            ctx = initialize_project_environment(root_path_str="/tmp/test")
            assert isinstance(ctx, ProjectContext)
            assert ctx.project_root_path == Path("/tmp/test")

    def test_uses_provided_root_path(self):
        """root_path_str argument sets project_root_path."""
        with patch(
            "argumentation_analysis.core.bootstrap.initialize_jvm_func", None
        ), patch(
            "argumentation_analysis.core.bootstrap.CryptoService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.DefinitionService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.create_llm_service_func", None
        ), patch(
            "argumentation_analysis.core.bootstrap.sk_module", None
        ), patch(
            "argumentation_analysis.core.bootstrap.settings", None
        ), patch(
            "argumentation_analysis.core.bootstrap.ContextualFallacyDetector_class",
            None,
        ):
            from argumentation_analysis.core.bootstrap import (
                initialize_project_environment,
            )

            ctx = initialize_project_environment(root_path_str="/my/project")
            assert ctx.project_root_path == Path("/my/project")

    def test_jvm_init_called_when_available(self):
        """When initialize_jvm_func is available, it gets called."""
        mock_init_jvm = MagicMock(return_value=True)

        with patch(
            "argumentation_analysis.core.bootstrap.initialize_jvm_func",
            mock_init_jvm,
        ), patch(
            "argumentation_analysis.core.bootstrap._load_tweety_classes"
        ) as mock_load, patch(
            "argumentation_analysis.core.bootstrap.CryptoService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.DefinitionService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.create_llm_service_func", None
        ), patch(
            "argumentation_analysis.core.bootstrap.sk_module", None
        ), patch(
            "argumentation_analysis.core.bootstrap.settings", None
        ), patch(
            "argumentation_analysis.core.bootstrap.ContextualFallacyDetector_class",
            None,
        ):
            from argumentation_analysis.core.bootstrap import (
                initialize_project_environment,
            )

            ctx = initialize_project_environment(root_path_str="/tmp/test")
            mock_init_jvm.assert_called_once()
            assert ctx.jvm_initialized is True
            mock_load.assert_called_once_with(ctx)

    def test_jvm_init_false_means_not_initialized(self):
        """When initialize_jvm returns False, jvm_initialized is False."""
        mock_init_jvm = MagicMock(return_value=False)

        with patch(
            "argumentation_analysis.core.bootstrap.initialize_jvm_func",
            mock_init_jvm,
        ), patch(
            "argumentation_analysis.core.bootstrap.CryptoService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.DefinitionService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.create_llm_service_func", None
        ), patch(
            "argumentation_analysis.core.bootstrap.sk_module", None
        ), patch(
            "argumentation_analysis.core.bootstrap.settings", None
        ), patch(
            "argumentation_analysis.core.bootstrap.ContextualFallacyDetector_class",
            None,
        ):
            from argumentation_analysis.core.bootstrap import (
                initialize_project_environment,
            )

            ctx = initialize_project_environment(root_path_str="/tmp/test")
            assert ctx.jvm_initialized is False

    def test_skips_jvm_if_already_initialized(self):
        """If sys._jvm_initialized is True, skips JVM initialization."""
        sys._jvm_initialized = True
        mock_init_jvm = MagicMock(return_value=True)

        with patch(
            "argumentation_analysis.core.bootstrap.initialize_jvm_func",
            mock_init_jvm,
        ), patch("argumentation_analysis.core.bootstrap._load_tweety_classes"), patch(
            "argumentation_analysis.core.bootstrap.CryptoService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.DefinitionService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.create_llm_service_func", None
        ), patch(
            "argumentation_analysis.core.bootstrap.sk_module", None
        ), patch(
            "argumentation_analysis.core.bootstrap.settings", None
        ), patch(
            "argumentation_analysis.core.bootstrap.ContextualFallacyDetector_class",
            None,
        ):
            from argumentation_analysis.core.bootstrap import (
                initialize_project_environment,
            )

            ctx = initialize_project_environment(root_path_str="/tmp/test")
            # JVM init function should NOT be called since already initialized
            mock_init_jvm.assert_not_called()
            assert ctx.jvm_initialized is True

    def test_kernel_created_when_sk_available(self):
        """When semantic_kernel and create_llm_service are available, kernel is created."""
        mock_sk = MagicMock()
        mock_kernel = MagicMock()
        mock_sk.Kernel.return_value = mock_kernel
        mock_llm_service = MagicMock()
        mock_create_llm = MagicMock(return_value=mock_llm_service)

        mock_settings = MagicMock()
        mock_settings.openai.chat_model_id = "test-model"
        mock_settings.openai.api_key = None
        mock_settings.passphrase = None
        mock_settings.encryption_key = None

        with patch(
            "argumentation_analysis.core.bootstrap.initialize_jvm_func", None
        ), patch(
            "argumentation_analysis.core.bootstrap.CryptoService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.DefinitionService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.create_llm_service_func",
            mock_create_llm,
        ), patch(
            "argumentation_analysis.core.bootstrap.sk_module", mock_sk
        ), patch(
            "argumentation_analysis.core.bootstrap.settings", mock_settings
        ), patch(
            "argumentation_analysis.core.bootstrap.ContextualFallacyDetector_class",
            None,
        ):
            from argumentation_analysis.core.bootstrap import (
                initialize_project_environment,
            )

            ctx = initialize_project_environment(root_path_str="/tmp/test")
            assert ctx.kernel is mock_kernel
            assert ctx.llm_service is mock_llm_service
            mock_kernel.add_service.assert_called_once_with(mock_llm_service)

    def test_services_dict_populated(self):
        """The services dict is populated at the end of initialization."""
        with patch(
            "argumentation_analysis.core.bootstrap.initialize_jvm_func", None
        ), patch(
            "argumentation_analysis.core.bootstrap.CryptoService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.DefinitionService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.create_llm_service_func", None
        ), patch(
            "argumentation_analysis.core.bootstrap.sk_module", None
        ), patch(
            "argumentation_analysis.core.bootstrap.settings", None
        ), patch(
            "argumentation_analysis.core.bootstrap.ContextualFallacyDetector_class",
            None,
        ):
            from argumentation_analysis.core.bootstrap import (
                initialize_project_environment,
            )

            ctx = initialize_project_environment(root_path_str="/tmp/test")
            assert "kernel" in ctx.services
            assert "crypto_service" in ctx.services
            assert "definition_service" in ctx.services
            assert "llm_service" in ctx.services
            assert "fallacy_detector" in ctx.services


# ===========================================================================
# _pre_init_safety_checks Tests (#253)
# ===========================================================================


class TestPreInitSafetyChecks:
    """Tests for _pre_init_safety_checks() pre-initialization validation."""

    def test_checks_python_version(self):
        """Fails when Python version is below 3.10."""
        from argumentation_analysis.core.bootstrap import _pre_init_safety_checks

        with patch("sys.version_info", (3, 9)), patch(
            "sys.executable", "/usr/bin/python3.9"
        ):
            result = _pre_init_safety_checks(Path.cwd(), Path.cwd() / ".env")
            assert result is False

    def test_accepts_python_3_10(self):
        """Passes when Python version is 3.10 or higher."""
        from argumentation_analysis.core.bootstrap import _pre_init_safety_checks

        with patch("sys.version_info", (3, 10)), patch(
            "sys.executable", "/usr/bin/python3.10"
        ):
            result = _pre_init_safety_checks(Path.cwd(), Path.cwd() / ".env")
            assert result is True

    def test_warns_for_python_3_13(self):
        """Warns but passes when Python version is 3.13+ (not fully tested)."""
        from argumentation_analysis.core.bootstrap import _pre_init_safety_checks

        with patch("sys.version_info", (3, 13)), patch(
            "sys.executable", "/usr/bin/python3.13"
        ):
            result = _pre_init_safety_checks(Path.cwd(), Path.cwd() / ".env")
            assert result is True  # Should pass with warning

    def test_fails_when_jpype_not_available(self):
        """Fails when jpype module is not available."""
        from argumentation_analysis.core.bootstrap import _pre_init_safety_checks

        with patch.dict("sys.modules", {"jpype": None}):
            result = _pre_init_safety_checks(Path.cwd(), Path.cwd() / ".env")
            assert result is False

    def test_checks_project_root_exists(self):
        """Fails when project root directory does not exist."""
        from argumentation_analysis.core.bootstrap import _pre_init_safety_checks

        with patch("pathlib.Path.exists", return_value=False):
            result = _pre_init_safety_checks(
                Path("C:/nonexistent"), Path("C:/nonexistent/.env")
            )
            assert result is False

    def test_checks_project_root_is_directory(self):
        """Fails when project root path is not a directory."""
        from argumentation_analysis.core.bootstrap import _pre_init_safety_checks

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.is_dir", return_value=False
        ):
            result = _pre_init_safety_checks(
                Path("C:/test/file.txt"), Path("C:/test/.env")
            )
            assert result is False

    def test_warns_for_pycharm_environment(self):
        """Warns when running from PyCharm IDE."""
        from argumentation_analysis.core.bootstrap import _pre_init_safety_checks

        with patch("sys.version_info", (3, 11)), patch(
            "sys.executable", "/opt/pycharm/bin/python3"
        ):
            result = _pre_init_safety_checks(Path.cwd(), Path.cwd() / ".env")
            assert result is True  # Should pass with warning

    def test_passes_all_checks(self):
        """Passes when all critical checks are satisfied."""
        from argumentation_analysis.core.bootstrap import _pre_init_safety_checks

        with patch("sys.version_info", (3, 11)), patch(
            "sys.executable", "/usr/bin/python3"
        ):
            result = _pre_init_safety_checks(Path.cwd(), Path.cwd() / ".env")
            assert result is True

    def test_skips_memory_check_when_psutil_unavailable(self):
        """Gracefully skips memory check when psutil is not installed."""
        from argumentation_analysis.core.bootstrap import _pre_init_safety_checks

        with patch.dict("sys.modules", {"psutil": None}), patch(
            "sys.version_info", (3, 11)
        ):
            result = _pre_init_safety_checks(Path.cwd(), Path.cwd() / ".env")
            # Should not fail, just skip the check
            assert result is True
