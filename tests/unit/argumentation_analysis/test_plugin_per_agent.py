"""Tests for plugin-per-agent speciality mapping (#221, Epic #208-E).

Validates:
- AGENT_PLUGIN_MAP has entries for all known agent specialities
- _PLUGIN_REGISTRY maps plugin names to importable modules
- load_plugins_for_agent loads correct plugins per speciality
- StateManagerPlugin always loaded when state is provided
- Unknown agent speciality returns empty (+ StateManager if state)
- Plugin load failures are handled gracefully
"""

import pytest
from unittest.mock import MagicMock, patch

from argumentation_analysis.agents.factory import (
    AGENT_PLUGIN_MAP,
    _PLUGIN_REGISTRY,
    load_plugins_for_agent,
)


# --- Plugin map structure ---


class TestAgentPluginMap:
    def test_all_specialities_defined(self):
        expected = {
            "project_manager",
            "informal_fallacy",
            "extract",
            "formal_logic",
            "quality",
            "debate",
            "counter_argument",
            "governance",
            "sherlock",
            "watson",
        }
        assert set(AGENT_PLUGIN_MAP.keys()) == expected

    def test_all_values_are_lists(self):
        for key, plugins in AGENT_PLUGIN_MAP.items():
            assert isinstance(plugins, list), f"{key} should map to a list"

    def test_informal_has_fallacy_plugin(self):
        assert "french_fallacy" in AGENT_PLUGIN_MAP["informal_fallacy"]

    def test_formal_has_tweety(self):
        assert "tweety_logic" in AGENT_PLUGIN_MAP["formal_logic"]

    def test_quality_has_scoring(self):
        assert "quality_scoring" in AGENT_PLUGIN_MAP["quality"]

    def test_governance_has_governance_plugin(self):
        assert "governance" in AGENT_PLUGIN_MAP["governance"]

    def test_pm_has_no_speciality_plugins(self):
        assert AGENT_PLUGIN_MAP["project_manager"] == []


# --- Plugin registry ---


class TestPluginRegistry:
    def test_all_mapped_plugins_in_registry(self):
        """Every plugin name referenced in AGENT_PLUGIN_MAP should exist in _PLUGIN_REGISTRY."""
        all_plugin_names = set()
        for plugins in AGENT_PLUGIN_MAP.values():
            all_plugin_names.update(plugins)
        for name in all_plugin_names:
            assert name in _PLUGIN_REGISTRY, f"Plugin '{name}' missing from registry"

    def test_registry_entries_are_tuples(self):
        for name, entry in _PLUGIN_REGISTRY.items():
            assert isinstance(entry, tuple), f"{name} should be a (module, class) tuple"
            assert len(entry) == 2, f"{name} should have exactly 2 elements"

    def test_state_manager_in_registry(self):
        assert "state_manager" in _PLUGIN_REGISTRY


# --- load_plugins_for_agent ---


class TestLoadPluginsForAgent:
    def test_loads_state_manager_when_state_provided(self):
        mock_kernel = MagicMock()
        mock_state = MagicMock()
        loaded = load_plugins_for_agent(
            mock_kernel, "project_manager", state=mock_state
        )
        assert "state_manager" in loaded
        # PM has no speciality plugins, so only StateManager
        mock_kernel.add_plugin.assert_called_once()

    def test_no_state_manager_without_state(self):
        mock_kernel = MagicMock()
        loaded = load_plugins_for_agent(mock_kernel, "project_manager", state=None)
        assert "state_manager" not in loaded

    def test_informal_loads_french_fallacy(self):
        mock_kernel = MagicMock()
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            loaded = load_plugins_for_agent(mock_kernel, "informal_fallacy")
        assert "french_fallacy" in loaded

    def test_quality_loads_quality_scoring(self):
        mock_kernel = MagicMock()
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            loaded = load_plugins_for_agent(mock_kernel, "quality")
        assert "quality_scoring" in loaded

    def test_unknown_speciality_loads_nothing(self):
        mock_kernel = MagicMock()
        loaded = load_plugins_for_agent(mock_kernel, "nonexistent")
        assert loaded == []

    def test_unknown_speciality_with_state_loads_state_manager_only(self):
        mock_kernel = MagicMock()
        mock_state = MagicMock()
        loaded = load_plugins_for_agent(mock_kernel, "nonexistent", state=mock_state)
        assert loaded == ["state_manager"]

    def test_plugin_import_failure_handled_gracefully(self):
        mock_kernel = MagicMock()
        with patch("importlib.import_module", side_effect=ImportError("not found")):
            loaded = load_plugins_for_agent(mock_kernel, "informal_fallacy")
        # Should not raise, just skip the failed plugin
        assert "french_fallacy" not in loaded

    def test_formal_loads_tweety(self):
        mock_kernel = MagicMock()
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            loaded = load_plugins_for_agent(mock_kernel, "formal_logic")
        assert "tweety_logic" in loaded

    def test_governance_loads_governance_plugin(self):
        mock_kernel = MagicMock()
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            loaded = load_plugins_for_agent(mock_kernel, "governance")
        assert "governance" in loaded

    def test_watson_loads_tweety(self):
        mock_kernel = MagicMock()
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            loaded = load_plugins_for_agent(mock_kernel, "watson")
        assert "tweety_logic" in loaded

    def test_debate_has_no_external_plugins(self):
        mock_kernel = MagicMock()
        loaded = load_plugins_for_agent(mock_kernel, "debate")
        assert loaded == []


# --- Integration: plugin count per agent ---


class TestPluginCounts:
    def test_no_agent_has_more_than_3_plugins(self):
        """No agent should be loaded with too many plugins — focused speciality."""
        for speciality, plugins in AGENT_PLUGIN_MAP.items():
            assert (
                len(plugins) <= 3
            ), f"Agent '{speciality}' has {len(plugins)} plugins — too many"
