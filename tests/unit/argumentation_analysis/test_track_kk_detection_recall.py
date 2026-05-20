"""Tests for Track KK (#655): Detection recall — eliminate Type Inconnu + wide-net pass.

Tests cover:
  1. _is_usable_fallacy_type filter
  2. _extract_fallacy_type multi-key extraction
  3. Parent harness skips unusable types
  4. Parent harness wide-net whole-text fusion
  5. One-shot _match_taxonomy_name extraction
"""

import asyncio
import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState


def _get_harness_module():
    from argumentation_analysis.orchestration import conversational_orchestrator as mod

    return mod


class TestIsUsableFallacyType:
    """_is_usable_fallacy_type rejects empty/generic fallacy type names."""

    def test_rejects_empty(self):
        mod = _get_harness_module()
        assert mod._is_usable_fallacy_type("") is False

    def test_rejects_whitespace(self):
        mod = _get_harness_module()
        assert mod._is_usable_fallacy_type("   ") is False

    def test_rejects_type_inconnu_variants(self):
        mod = _get_harness_module()
        for variant in ("Type Inconnu", "Type inconnu", "type inconnu", "TYPE INCONNU"):
            assert mod._is_usable_fallacy_type(variant) is False

    def test_rejects_unknown(self):
        mod = _get_harness_module()
        assert mod._is_usable_fallacy_type("unknown") is False
        assert mod._is_usable_fallacy_type("Unknown") is False

    def test_rejects_sophisme_inconnu(self):
        mod = _get_harness_module()
        assert mod._is_usable_fallacy_type("Sophisme inconnu") is False

    def test_rejects_unknown_class_prefix(self):
        mod = _get_harness_module()
        assert mod._is_usable_fallacy_type("unknown_class_5") is False

    def test_accepts_valid_names(self):
        mod = _get_harness_module()
        assert mod._is_usable_fallacy_type("Ad hominem") is True
        assert mod._is_usable_fallacy_type("slippery slope") is True
        assert mod._is_usable_fallacy_type("Empoisonnement du puits") is True


class TestExtractFallacyType:
    """_extract_fallacy_type tries multiple keys and validates."""

    def test_prefers_fallacy_type(self):
        mod = _get_harness_module()
        d = {"fallacy_type": "Ad hominem", "type": "other", "nom": "third"}
        assert mod._extract_fallacy_type(d) == "Ad hominem"

    def test_falls_back_to_type(self):
        mod = _get_harness_module()
        d = {"type": "slippery slope", "nom": "third"}
        assert mod._extract_fallacy_type(d) == "slippery slope"

    def test_falls_back_to_nom(self):
        mod = _get_harness_module()
        d = {"nom": "Faux dilemme"}
        assert mod._extract_fallacy_type(d) == "Faux dilemme"

    def test_skips_unusable_value(self):
        mod = _get_harness_module()
        d = {"fallacy_type": "unknown", "type": "Ad hominem"}
        assert mod._extract_fallacy_type(d) == "Ad hominem"

    def test_returns_empty_when_all_unusable(self):
        mod = _get_harness_module()
        d = {"fallacy_type": "Type Inconnu", "type": "unknown", "nom": ""}
        assert mod._extract_fallacy_type(d) == ""

    def test_returns_empty_for_empty_dict(self):
        mod = _get_harness_module()
        assert mod._extract_fallacy_type({}) == ""

    def test_ignores_non_string_values(self):
        mod = _get_harness_module()
        d = {"fallacy_type": 42, "type": None, "nom": "Ad hominem"}
        assert mod._extract_fallacy_type(d) == "Ad hominem"


class TestParentHarnessSkipsUnusable:
    """Parent harness _run_parent_harness_fallback skips unusable types."""

    @pytest.fixture()
    def mock_invoke(self, monkeypatch):
        """Mock the invoke_callables module to return controlled data."""
        fake_module = type("FakeInvoke", (), {})()
        fake_results = {
            "per_arg": {
                "fallacies": [
                    {"fallacy_type": "Ad hominem", "explanation": "real"},
                    {"fallacy_type": "Type Inconnu", "explanation": "bad"},
                    {"type": "unknown", "explanation": "also bad"},
                    {"fallacy_type": "slippery slope", "explanation": "good"},
                ],
                "exploration_method": "per_argument_parallel",
            },
            "whole_text": {"fallacies": []},
        }

        async def fake_per_arg(text, context):
            return fake_results["per_arg"]

        async def fake_whole_text(text, context):
            return fake_results["whole_text"]

        fake_module._invoke_hierarchical_fallacy_per_argument = fake_per_arg
        fake_module._invoke_hierarchical_fallacy = fake_whole_text

        import argumentation_analysis.orchestration.conversational_orchestrator as co_mod

        original_import = co_mod.__dict__.get("__original_import__", __import__)

        import importlib
        import sys

        monkeypatch.setitem(
            sys.modules,
            "argumentation_analysis.orchestration.invoke_callables",
            fake_module,
        )

    def test_skips_unusable_types(self, mock_invoke):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_parent_harness_fallback,
        )

        state = UnifiedAnalysisState("test text for harness")
        result = asyncio.get_event_loop().run_until_complete(
            _run_parent_harness_fallback("test text", state)
        )
        assert result is not None
        assert result["fallacies_registered"] == 2
        assert result["fallacies_skipped_unusable"] == 2

    def test_only_valid_types_in_state(self, mock_invoke):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_parent_harness_fallback,
        )

        state = UnifiedAnalysisState("test text for harness")
        asyncio.get_event_loop().run_until_complete(
            _run_parent_harness_fallback("test text", state)
        )
        fallacy_types = {v.get("type", "") for v in state.identified_fallacies.values()}
        assert "Ad hominem" in fallacy_types
        assert "slippery slope" in fallacy_types
        assert "Type Inconnu" not in fallacy_types
        assert "unknown" not in fallacy_types


class TestParentHarnessWideNet:
    """Wide-net whole-text pass adds extra fallacies not in per-argument results."""

    @pytest.fixture()
    def mock_invoke_with_widenet(self, monkeypatch):
        fake_module = type("FakeInvoke", (), {})()

        async def fake_per_arg(text, context):
            return {
                "fallacies": [
                    {
                        "fallacy_type": "Ad hominem",
                        "explanation": "per-arg",
                        "taxonomy_pk": "PK1",
                    },
                ],
                "exploration_method": "per_argument_parallel",
            }

        async def fake_whole_text(text, context):
            return {
                "fallacies": [
                    {
                        "fallacy_type": "Appel à la tradition",
                        "explanation": "whole-text only",
                        "taxonomy_pk": "PK99",
                    },
                ],
            }

        fake_module._invoke_hierarchical_fallacy_per_argument = fake_per_arg
        fake_module._invoke_hierarchical_fallacy = fake_whole_text

        import sys

        monkeypatch.setitem(
            sys.modules,
            "argumentation_analysis.orchestration.invoke_callables",
            fake_module,
        )

    def test_wide_net_extras_counted(self, mock_invoke_with_widenet):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_parent_harness_fallback,
        )

        state = UnifiedAnalysisState("A longer text " * 100)
        result = asyncio.get_event_loop().run_until_complete(
            _run_parent_harness_fallback("A longer text " * 100, state)
        )
        assert result is not None
        assert result["wide_net_extras"] == 1
        assert result["fallacies_registered"] == 2

    def test_wide_net_deduplication(self, monkeypatch):
        """Whole-text finding that duplicates per-arg is not double-counted."""
        fake_module = type("FakeInvoke", (), {})()

        async def fake_per_arg(text, context):
            return {
                "fallacies": [
                    {
                        "fallacy_type": "Ad hominem",
                        "explanation": "per-arg",
                        "taxonomy_pk": "PK1",
                    },
                ],
                "exploration_method": "per_argument_parallel",
            }

        async def fake_whole_text(text, context):
            return {
                "fallacies": [
                    {
                        "fallacy_type": "Ad hominem",
                        "explanation": "duplicate",
                        "taxonomy_pk": "PK1",
                    },
                ],
            }

        fake_module._invoke_hierarchical_fallacy_per_argument = fake_per_arg
        fake_module._invoke_hierarchical_fallacy = fake_whole_text

        import sys

        monkeypatch.setitem(
            sys.modules,
            "argumentation_analysis.orchestration.invoke_callables",
            fake_module,
        )

        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_parent_harness_fallback,
        )

        state = UnifiedAnalysisState("A longer text " * 100)
        result = asyncio.get_event_loop().run_until_complete(
            _run_parent_harness_fallback("A longer text " * 100, state)
        )
        assert result["wide_net_extras"] == 0
        assert result["fallacies_registered"] == 1


class TestParentHarnessEmpty:
    """Parent harness returns None when no fallacies found."""

    def test_returns_none_on_empty(self, monkeypatch):
        fake_module = type("FakeInvoke", (), {})()

        async def fake_per_arg(text, context):
            return {"fallacies": [], "exploration_method": "per_argument_parallel"}

        async def fake_whole_text(text, context):
            return {"fallacies": []}

        fake_module._invoke_hierarchical_fallacy_per_argument = fake_per_arg
        fake_module._invoke_hierarchical_fallacy = fake_whole_text

        import sys

        monkeypatch.setitem(
            sys.modules,
            "argumentation_analysis.orchestration.invoke_callables",
            fake_module,
        )

        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_parent_harness_fallback,
        )

        state = UnifiedAnalysisState("short")
        result = asyncio.get_event_loop().run_until_complete(
            _run_parent_harness_fallback("short", state)
        )
        assert result is None


class TestOneShotMatchTaxonomyName:
    """_match_taxonomy_name extracts fallacy names from raw LLM text."""

    @pytest.fixture()
    def plugin_cls(self):
        from argumentation_analysis.plugins.fallacy_workflow_plugin import (
            FallacyWorkflowPlugin,
        )

        return FallacyWorkflowPlugin

    def test_matches_common_fallacy_in_text(self, plugin_cls):
        plugin = plugin_cls.__new__(plugin_cls)
        plugin.taxonomy_navigator = type("TN", (), {"taxonomy_data": []})()
        result = plugin._match_taxonomy_name(
            "The fallacy here is clearly an Ad hominem attack"
        )
        assert result == "Ad hominem"

    def test_matches_french_name(self, plugin_cls):
        plugin = plugin_cls.__new__(plugin_cls)
        plugin.taxonomy_navigator = type("TN", (), {"taxonomy_data": []})()
        result = plugin._match_taxonomy_name("Il s'agit d'un Faux dilemme classique")
        assert result == "Faux dilemme"

    def test_returns_empty_for_no_match(self, plugin_cls):
        plugin = plugin_cls.__new__(plugin_cls)
        plugin.taxonomy_navigator = type("TN", (), {"taxonomy_data": []})()
        result = plugin._match_taxonomy_name("nothing relevant here")
        assert result == ""

    def test_prefers_longer_match(self, plugin_cls):
        plugin = plugin_cls.__new__(plugin_cls)
        plugin.taxonomy_navigator = type("TN", (), {"taxonomy_data": []})()
        text = "This is a Généralisation hâtive"
        result = plugin._match_taxonomy_name(text)
        assert "Généralisation hâtive" in result

    def test_matches_taxonomy_node_name(self, plugin_cls):
        plugin = plugin_cls.__new__(plugin_cls)
        plugin.taxonomy_navigator = type(
            "TN",
            (),
            {
                "taxonomy_data": [
                    {"text_fr": "Appel à l'autorité", "PK": "1", "depth": 2},
                ]
            },
        )()
        result = plugin._match_taxonomy_name("C'est un appel à l'autorité manifeste")
        assert result == "Appel à l'autorité"
