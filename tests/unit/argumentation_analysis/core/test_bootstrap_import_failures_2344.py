# -*- coding: utf-8 -*-
"""#2344 family (b) — the bootstrap's ImportError degradations live in the state.

Every dependency import used to leave a ``None`` that call sites skipped
silently — the only trace was an ERROR log line at import time, and the
caller of ``initialize_project_environment`` could not know WHAT had been
skipped. The named state (``BOOTSTRAP_IMPORT_FAILURES``, mirrored on the
ProjectContext as ``import_failures``) is the repair: doctrine #1019, the
degradation lives in the state, not only in the log.
"""

import sys
from unittest.mock import patch

import pytest

from argumentation_analysis.core.bootstrap import (
    BOOTSTRAP_IMPORT_FAILURES,
    ProjectContext,
    initialize_project_environment,
)


class TestProjectContextFailures:
    def test_context_defaults_to_empty_failures(self):
        assert ProjectContext().import_failures == {}


class TestFailuresFlowToTheContext:
    """A degraded import registry is mirrored, named, on the context."""

    @pytest.fixture(autouse=True)
    def _reset_jvm_flag(self):
        original = getattr(sys, "_jvm_initialized", None)
        if hasattr(sys, "_jvm_initialized"):
            delattr(sys, "_jvm_initialized")
        yield
        if original is not None:
            sys._jvm_initialized = original
        elif hasattr(sys, "_jvm_initialized"):
            delattr(sys, "_jvm_initialized")

    def test_registry_entries_reach_the_context(self):
        with patch(
            "argumentation_analysis.core.bootstrap._pre_init_safety_checks",
            return_value=True,
        ), patch(
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
        ), patch.dict(
            BOOTSTRAP_IMPORT_FAILURES,
            {"initialize_jvm_func": "simulated missing module"},
        ):
            ctx = initialize_project_environment(root_path_str="/tmp/test")
        assert ctx.import_failures == {
            "initialize_jvm_func": "simulated missing module"
        }, "the caller must see exactly which imports were skipped"

    def test_clean_registry_means_empty_failures(self):
        with patch(
            "argumentation_analysis.core.bootstrap._pre_init_safety_checks",
            return_value=True,
        ), patch(
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
        ), patch.dict(
            BOOTSTRAP_IMPORT_FAILURES, clear=True
        ):
            ctx = initialize_project_environment(root_path_str="/tmp/test")
        assert ctx.import_failures == {}
