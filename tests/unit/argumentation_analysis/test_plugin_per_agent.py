"""Tests for plugin-per-agent speciality mapping (#221, Epic #208-E).

Validates:
- AGENT_SPECIALITY_MAP has entries for all known agent specialities
- _PLUGIN_REGISTRY maps plugin names to importable modules
- load_plugins_for_agent loads correct plugins per speciality
- get_plugin_instances returns correct plugin objects per speciality
- StateManagerPlugin always loaded when state is provided
- Unknown agent speciality returns empty (+ StateManager if state)
- Plugin load failures are handled gracefully
- conversational_orchestrator.AGENT_CONFIG uses factory speciality keys
"""

import pytest
from unittest.mock import MagicMock, patch

from argumentation_analysis.agents.factory import (
    AGENT_SPECIALITY_MAP,
    _PLUGIN_REGISTRY,
    get_plugin_instances,
    load_plugins_for_agent,
)

# --- Plugin map structure ---


class TestAgentSpecialityMap:
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
        assert set(AGENT_SPECIALITY_MAP.keys()) == expected

    def test_all_values_are_lists(self):
        for key, plugins in AGENT_SPECIALITY_MAP.items():
            assert isinstance(plugins, list), f"{key} should map to a list"

    def test_informal_has_fallacy_plugin(self):
        assert "french_fallacy" in AGENT_SPECIALITY_MAP["informal_fallacy"]

    def test_formal_has_tweety(self):
        assert "tweety_logic" in AGENT_SPECIALITY_MAP["formal_logic"]

    def test_quality_has_scoring(self):
        assert "quality_scoring" in AGENT_SPECIALITY_MAP["quality"]

    def test_governance_has_governance_plugin(self):
        assert "governance" in AGENT_SPECIALITY_MAP["governance"]

    def test_debate_has_debate_plugin(self):
        assert "debate" in AGENT_SPECIALITY_MAP["debate"]

    def test_counter_argument_has_counter_plugin(self):
        assert "counter_argument" in AGENT_SPECIALITY_MAP["counter_argument"]

    def test_pm_carries_only_narrative_synthesis(self):
        """ProjectManager orchestrates + synthesizes; it carries the
        narrative_synthesis plugin (its own role) and no operational
        analysis plugins (extraction / fallacy / formal-logic).

        Legacy contract asserted ``== []`` (#1336): obsolete since PM gained
        the ``narrative_synthesis`` plugin. Converted to a fail-loud pin on the
        exact plugin set + a negative isolation check against operational
        domains — adding an operational plugin to PM must break this test.
        """
        plugins = set(AGENT_SPECIALITY_MAP["project_manager"])
        assert plugins == {"narrative_synthesis"}
        assert not (
            plugins
            & {"toulmin", "text_to_kb", "french_fallacy", "fallacy_workflow",
               "tweety_logic"}
        )


# --- Plugin registry ---


class TestPluginRegistry:
    def test_all_mapped_plugins_in_registry(self):
        """Every plugin name referenced in AGENT_SPECIALITY_MAP should exist in _PLUGIN_REGISTRY."""
        all_plugin_names = set()
        for plugins in AGENT_SPECIALITY_MAP.values():
            all_plugin_names.update(plugins)
        for name in all_plugin_names:
            assert name in _PLUGIN_REGISTRY, f"Plugin '{name}' missing from registry"

    def test_registry_entries_are_tuples(self):
        for name, entry in _PLUGIN_REGISTRY.items():
            assert isinstance(entry, tuple), f"{name} should be a (module, class) tuple"
            assert len(entry) == 2, f"{name} should have exactly 2 elements"

    def test_state_manager_in_registry(self):
        assert "state_manager" in _PLUGIN_REGISTRY

    def test_debate_plugin_in_registry(self):
        assert "debate" in _PLUGIN_REGISTRY

    def test_counter_argument_plugin_in_registry(self):
        assert "counter_argument" in _PLUGIN_REGISTRY


# --- load_plugins_for_agent ---


class TestLoadPluginsForAgent:
    def test_loads_state_manager_when_state_provided(self):
        mock_kernel = MagicMock()
        mock_state = MagicMock()
        loaded = load_plugins_for_agent(
            mock_kernel, "project_manager", state=mock_state
        )
        assert "state_manager" in loaded
        # PM carries state_manager (state provided) + narrative_synthesis
        # (its own speciality plugin) -> exactly 2 plugins registered.
        assert mock_kernel.add_plugin.call_count == 2

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

    def test_debate_loads_debate_plugin(self):
        mock_kernel = MagicMock()
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            loaded = load_plugins_for_agent(mock_kernel, "debate")
        assert "debate" in loaded


# --- get_plugin_instances ---


class TestGetPluginInstances:
    def test_returns_state_manager_when_state_provided(self):
        mock_state = MagicMock()
        instances = get_plugin_instances("project_manager", state=mock_state)
        # PM carries state_manager (state provided) + narrative_synthesis
        # (its own speciality plugin) -> exactly 2 instances.
        instance_types = {type(i).__name__ for i in instances}
        assert len(instances) == 2
        assert "StateManagerPlugin" in instance_types
        assert "NarrativeSynthesisPlugin" in instance_types

    def test_returns_narrative_synthesis_without_state_for_pm(self):
        # PM carries its own narrative_synthesis plugin even without a state.
        instances = get_plugin_instances("project_manager", state=None)
        instance_types = {type(i).__name__ for i in instances}
        assert instance_types == {"NarrativeSynthesisPlugin"}

    def test_returns_speciality_plugins(self):
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            instances = get_plugin_instances("informal_fallacy")
        assert len(instances) >= 1  # at least french_fallacy

    def test_import_failure_returns_partial(self):
        with patch("importlib.import_module", side_effect=ImportError("not found")):
            instances = get_plugin_instances("informal_fallacy")
        assert instances == []  # all failed gracefully

    def test_unknown_speciality_returns_empty(self):
        instances = get_plugin_instances("nonexistent")
        assert instances == []


# --- Conversational orchestrator integration ---


class TestConvOrchestratorIntegration:
    def test_agent_config_specialities_exist_in_factory(self):
        """All speciality keys in AGENT_CONFIG must exist in AGENT_SPECIALITY_MAP."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        for agent_name, config in AGENT_CONFIG.items():
            speciality = config["speciality"]
            assert speciality in AGENT_SPECIALITY_MAP, (
                f"Agent '{agent_name}' references speciality '{speciality}' "
                f"not found in AGENT_SPECIALITY_MAP"
            )

    def test_agent_config_has_instructions(self):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        for agent_name, config in AGENT_CONFIG.items():
            assert (
                "instructions" in config
            ), f"Agent '{agent_name}' missing instructions"
            assert (
                len(config["instructions"]) > 20
            ), f"Agent '{agent_name}' has suspiciously short instructions"


# --- Integration: plugin count per agent ---


class TestPluginCounts:
    def test_cross_domain_plugin_isolation(self):
        """No agent may carry plugins from mutually-exclusive domains at once.

        Legacy contract asserted ``len(plugins) <= 3`` (#1336): obsolete —
        formal_logic legitimately carries the full formal-logic stack (11
        plugins). A plugin COUNT is not the right invariant; the real one is
        cross-DOMAIN isolation: an agent scoped to informal fallacies must not
        also carry formal-logic plugins, and vice-versa. Converted to a
        fail-loud check on that invariant.
        """
        fallacy_domain = {"french_fallacy", "fallacy_workflow"}
        logic_domain = {
            "tweety_logic", "nl_to_logic", "coordinated_logic", "atms",
            "ranking", "aspic", "belief_revision", "logic_agents",
            "tweety_interpretation", "kb_to_tweety",
        }
        for speciality, plugins in AGENT_SPECIALITY_MAP.items():
            plugin_set = set(plugins)
            if plugin_set & fallacy_domain:
                assert not (plugin_set & logic_domain), (
                    f"Agent '{speciality}' mixes fallacy-detection + "
                    f"formal-logic plugins (cross-domain isolation violated): "
                    f"{plugin_set}"
                )
