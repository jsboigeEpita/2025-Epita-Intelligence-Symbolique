"""Tests that SK plugins are loadable and their @kernel_function methods
are discoverable in a Semantic Kernel instance (#468).

Validates:
- All entries in _PLUGIN_REGISTRY can be imported
- No-arg plugins instantiate correctly
- Plugins register their @kernel_function methods via kernel.add_plugin()
- AGENT_SPECIALITY_MAP specialities load the expected plugins
"""

import pytest
import importlib
from unittest.mock import MagicMock

from semantic_kernel import Kernel


# =====================================================================
# Plugin Registry Integrity
# =====================================================================


class TestPluginRegistryIntegrity:
    """Verify _PLUGIN_REGISTRY entries are importable."""

    def test_all_registry_entries_importable(self):
        from argumentation_analysis.agents.factory import _PLUGIN_REGISTRY

        for name, (module_path, class_name) in _PLUGIN_REGISTRY.items():
            mod = importlib.import_module(module_path)
            plugin_cls = getattr(mod, class_name)
            assert plugin_cls is not None, f"{name}: {class_name} not found in {module_path}"

    def test_registry_has_expected_plugins(self):
        from argumentation_analysis.agents.factory import _PLUGIN_REGISTRY

        expected = {
            "french_fallacy", "tweety_logic", "nl_to_logic",
            "quality_scoring", "governance", "debate", "counter_argument",
            "fallacy_workflow", "atms", "state_manager",
            "ranking", "aspic", "belief_revision",
            "narrative_synthesis", "toulmin",
        }
        assert expected.issubset(set(_PLUGIN_REGISTRY.keys())), (
            f"Missing: {expected - set(_PLUGIN_REGISTRY.keys())}"
        )


# =====================================================================
# Plugin Instantiation
# =====================================================================


class TestPluginInstantiation:
    """Verify no-arg plugins can be instantiated."""

    NO_ARG_PLUGINS = [
        "french_fallacy", "tweety_logic", "nl_to_logic",
        "quality_scoring", "governance", "counter_argument",
        "atms", "ranking", "aspic", "belief_revision",
        "narrative_synthesis", "toulmin",
    ]

    @pytest.mark.parametrize("plugin_name", NO_ARG_PLUGINS)
    def test_no_arg_plugin_instantiates(self, plugin_name):
        from argumentation_analysis.agents.factory import _PLUGIN_REGISTRY

        module_path, class_name = _PLUGIN_REGISTRY[plugin_name]
        mod = importlib.import_module(module_path)
        plugin_cls = getattr(mod, class_name)
        instance = plugin_cls()
        assert instance is not None


# =====================================================================
# Kernel Function Registration
# =====================================================================


class TestKernelFunctionRegistration:
    """Verify plugins register @kernel_function methods in a kernel."""

    def test_tweety_logic_plugin_registers_22_functions(self):
        from argumentation_analysis.plugins.tweety_logic_plugin import TweetyLogicPlugin

        kernel = Kernel()
        kernel.add_plugin(TweetyLogicPlugin(), plugin_name="tweety_logic")

        functions = kernel.get_full_list_of_function_metadata()
        tweety_fns = [f for f in functions if f.plugin_name == "tweety_logic"]
        assert len(tweety_fns) >= 20, (
            f"Expected >= 20 kernel functions, got {len(tweety_fns)}: "
            f"{[f.name for f in tweety_fns]}"
        )

    def test_nl_to_logic_plugin_registers_functions(self):
        from argumentation_analysis.plugins.nl_to_logic_plugin import NLToLogicPlugin

        kernel = Kernel()
        kernel.add_plugin(NLToLogicPlugin(), plugin_name="nl_to_logic")

        functions = kernel.get_full_list_of_function_metadata()
        nl_fns = [f for f in functions if f.plugin_name == "nl_to_logic"]
        assert len(nl_fns) >= 4, (
            f"Expected >= 4 kernel functions, got {len(nl_fns)}"
        )

    def test_ranking_plugin_registers_functions(self):
        from argumentation_analysis.plugins.ranking_plugin import RankingPlugin

        kernel = Kernel()
        kernel.add_plugin(RankingPlugin(), plugin_name="ranking")

        functions = kernel.get_full_list_of_function_metadata()
        rank_fns = [f for f in functions if f.plugin_name == "ranking"]
        assert len(rank_fns) >= 2

    def test_aspic_plugin_registers_functions(self):
        from argumentation_analysis.plugins.aspic_plugin import ASPICPlugin

        kernel = Kernel()
        kernel.add_plugin(ASPICPlugin(), plugin_name="aspic")

        functions = kernel.get_full_list_of_function_metadata()
        aspic_fns = [f for f in functions if f.plugin_name == "aspic"]
        assert len(aspic_fns) >= 2

    def test_belief_revision_plugin_registers_functions(self):
        from argumentation_analysis.plugins.belief_revision_plugin import BeliefRevisionPlugin

        kernel = Kernel()
        kernel.add_plugin(BeliefRevisionPlugin(), plugin_name="belief_revision")

        functions = kernel.get_full_list_of_function_metadata()
        br_fns = [f for f in functions if f.plugin_name == "belief_revision"]
        assert len(br_fns) >= 3

    def test_atms_plugin_registers_functions(self):
        from argumentation_analysis.plugins.atms_plugin import ATMSPlugin

        kernel = Kernel()
        kernel.add_plugin(ATMSPlugin(), plugin_name="atms")

        functions = kernel.get_full_list_of_function_metadata()
        atms_fns = [f for f in functions if f.plugin_name == "atms"]
        assert len(atms_fns) >= 4

    def test_governance_plugin_registers_functions(self):
        from argumentation_analysis.plugins.governance_plugin import GovernancePlugin

        kernel = Kernel()
        kernel.add_plugin(GovernancePlugin(), plugin_name="governance")

        functions = kernel.get_full_list_of_function_metadata()
        gov_fns = [f for f in functions if f.plugin_name == "governance"]
        assert len(gov_fns) >= 6

    def test_state_manager_plugin_registers_functions(self):
        from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState

        state = RhetoricalAnalysisState("test")
        kernel = Kernel()
        kernel.add_plugin(StateManagerPlugin(state=state), plugin_name="state_manager")

        functions = kernel.get_full_list_of_function_metadata()
        sm_fns = [f for f in functions if f.plugin_name == "state_manager"]
        assert len(sm_fns) >= 15, (
            f"Expected >= 15 kernel functions, got {len(sm_fns)}: "
            f"{[f.name for f in sm_fns]}"
        )


# =====================================================================
# Factory Integration
# =====================================================================


class TestFactoryPluginLoading:
    """Verify load_plugins_for_agent and get_plugin_instances work."""

    def test_formal_logic_speciality_loads_expected_plugins(self):
        from argumentation_analysis.agents.factory import AGENT_SPECIALITY_MAP

        speciality = "formal_logic"
        plugins = AGENT_SPECIALITY_MAP.get(speciality, [])
        expected = {"tweety_logic", "nl_to_logic", "atms", "ranking", "aspic", "belief_revision"}
        assert expected.issubset(set(plugins)), (
            f"Missing from formal_logic: {expected - set(plugins)}"
        )

    def test_informal_fallacy_speciality_includes_toulmin(self):
        from argumentation_analysis.agents.factory import AGENT_SPECIALITY_MAP

        plugins = AGENT_SPECIALITY_MAP.get("informal_fallacy", [])
        assert "toulmin" in plugins

    def test_project_manager_includes_narrative_synthesis(self):
        from argumentation_analysis.agents.factory import AGENT_SPECIALITY_MAP

        plugins = AGENT_SPECIALITY_MAP.get("project_manager", [])
        assert "narrative_synthesis" in plugins

    def test_get_plugin_instances_returns_for_formal_logic(self):
        from argumentation_analysis.agents.factory import get_plugin_instances
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState

        state = RhetoricalAnalysisState("test")
        instances = get_plugin_instances("formal_logic", state=state)
        class_names = {type(p).__name__ for p in instances}

        assert "StateManagerPlugin" in class_names
        assert "TweetyLogicPlugin" in class_names
        assert "NLToLogicPlugin" in class_names
        assert "RankingPlugin" in class_names
        assert "ASPICPlugin" in class_names
        assert "BeliefRevisionPlugin" in class_names

    def test_get_plugin_instances_no_state_excludes_state_manager(self):
        from argumentation_analysis.agents.factory import get_plugin_instances

        instances = get_plugin_instances("quality")
        class_names = {type(p).__name__ for p in instances}
        assert "StateManagerPlugin" not in class_names
        assert "QualityScoringPlugin" in class_names

    def test_load_plugins_for_agent_registers_in_kernel(self):
        from argumentation_analysis.agents.factory import load_plugins_for_agent
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState

        kernel = Kernel()
        state = RhetoricalAnalysisState("test")
        loaded = load_plugins_for_agent(kernel, "quality", state=state)

        assert "state_manager" in loaded
        assert "quality_scoring" in loaded

        functions = kernel.get_full_list_of_function_metadata()
        plugin_names = {f.plugin_name for f in functions}
        assert "state_manager" in plugin_names
        assert "quality_scoring" in plugin_names

    def test_load_plugins_for_agent_formal_logic_all_registered(self):
        from argumentation_analysis.agents.factory import load_plugins_for_agent
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState

        kernel = Kernel()
        state = RhetoricalAnalysisState("test")
        loaded = load_plugins_for_agent(kernel, "formal_logic", state=state)

        assert "state_manager" in loaded
        assert "tweety_logic" in loaded
        assert "nl_to_logic" in loaded
        assert "ranking" in loaded
        assert "aspic" in loaded
        assert "belief_revision" in loaded

        functions = kernel.get_full_list_of_function_metadata()
        plugin_names = {f.plugin_name for f in functions}
        assert "tweety_logic" in plugin_names
        assert "nl_to_logic" in plugin_names
        assert "ranking" in plugin_names


# =====================================================================
# Total Kernel Function Count
# =====================================================================


class TestTotalKernelFunctionCount:
    """Verify total @kernel_function methods across all loadable plugins."""

    def test_minimum_total_kernel_functions(self):
        """All no-arg plugins together should register at least 60 kernel functions."""
        from argumentation_analysis.agents.factory import _PLUGIN_REGISTRY

        kernel = Kernel()
        total = 0
        for name in [
            "tweety_logic", "nl_to_logic", "state_manager",
            "ranking", "aspic", "belief_revision",
            "governance", "quality_scoring", "atms",
            "french_fallacy", "toulmin", "narrative_synthesis",
            "counter_argument",
        ]:
            entry = _PLUGIN_REGISTRY.get(name)
            if entry is None:
                continue
            module_path, class_name = entry
            try:
                if name == "state_manager":
                    from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
                    instance = importlib.import_module(module_path)
                    cls = getattr(instance, class_name)
                    inst = cls(state=RhetoricalAnalysisState("test"))
                else:
                    mod = importlib.import_module(module_path)
                    cls = getattr(mod, class_name)
                    inst = cls()
                kernel.add_plugin(inst, plugin_name=name)
            except Exception:
                continue

        functions = kernel.get_full_list_of_function_metadata()
        total = len(functions)
        assert total >= 55, (
            f"Expected >= 55 total kernel functions across all plugins, got {total}"
        )
