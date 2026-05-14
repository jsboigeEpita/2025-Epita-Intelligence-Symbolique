"""Tests for LogicAgentPlugin — PL/FOL/Modal @kernel_function methods (#477).

Validates:
- All 8 @kernel_function methods are registered and callable
- JVM-unavailable path returns proper error JSON
- Each method delegates to TweetyBridge correctly
- Input parsing (JSON strings) works for multi-param methods
- Registry registration in setup_registry
- AGENT_SPECIALITY_MAP includes logic_agents
"""

import json
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bridge(**kwargs):
    """Create a mock TweetyBridge instance with default returns."""
    bridge = MagicMock()
    bridge.validate_pl_formula.return_value = kwargs.get("validate_pl", True)
    bridge.execute_pl_query.return_value = (
        kwargs.get("pl_accepted", True),
        kwargs.get("pl_message", "Query accepted"),
    )
    bridge.execute_fol_query.return_value = (
        kwargs.get("fol_accepted", True),
        kwargs.get("fol_message", "FOL query accepted"),
    )
    bridge.execute_modal_query.return_value = (
        kwargs.get("modal_accepted", True),
        kwargs.get("modal_message", "Modal query accepted"),
    )
    bridge.check_consistency.return_value = (
        kwargs.get("consistent", True),
        kwargs.get("consistency_msg", "Consistent"),
    )
    return bridge


def _patch_jvm_available(value: bool):
    """Return a patch context for _jvm_available."""
    return patch(
        "argumentation_analysis.plugins.logic_agent_plugin._jvm_available",
        return_value=value,
    )


def _patch_tweety_bridge(bridge_mock):
    """Return a patch that makes TweetyBridge.get_instance() return bridge_mock.

    TweetyBridge is imported locally inside each method body
    (``from ... import TweetyBridge``), so we must patch the source module's
    attribute rather than the plugin module.
    """
    mock_cls = MagicMock()
    mock_cls.get_instance.return_value = bridge_mock
    return patch(
        "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
        mock_cls,
    )


# ---------------------------------------------------------------------------
# Test: kernel_function registration
# ---------------------------------------------------------------------------


class TestKernelFunctionRegistration:
    """Verify all methods are decorated and discoverable."""

    def test_plugin_has_8_kernel_functions(self):
        from argumentation_analysis.plugins.logic_agent_plugin import LogicAgentPlugin

        plugin = LogicAgentPlugin()
        methods = [
            m for m in dir(plugin)
            if not m.startswith("_") and callable(getattr(plugin, m))
        ]
        expected = {
            "parse_pl_formula",
            "execute_pl_query",
            "check_pl_consistency",
            "execute_fol_query",
            "check_fol_consistency",
            "execute_modal_query",
            "check_modal_consistency",
            "validate_formula",
        }
        assert expected.issubset(set(methods))

    def test_methods_have_kernel_function_decorator(self):
        from argumentation_analysis.plugins.logic_agent_plugin import LogicAgentPlugin

        plugin = LogicAgentPlugin()
        # SK stores metadata on the function object
        for method_name in [
            "parse_pl_formula",
            "execute_pl_query",
            "check_pl_consistency",
            "execute_fol_query",
            "check_fol_consistency",
            "execute_modal_query",
            "check_modal_consistency",
            "validate_formula",
        ]:
            func = getattr(plugin, method_name)
            # @kernel_function adds __kernel_function__ metadata
            assert hasattr(func, "__kernel_function__"), (
                f"{method_name} missing @kernel_function decorator"
            )


# ---------------------------------------------------------------------------
# Test: JVM-unavailable path
# ---------------------------------------------------------------------------


class TestJVMUnavailable:
    """All methods should return error JSON when JVM is down."""

    @pytest.fixture()
    def plugin(self):
        from argumentation_analysis.plugins.logic_agent_plugin import LogicAgentPlugin
        return LogicAgentPlugin()

    def test_parse_pl_formula_no_jvm(self, plugin):
        with _patch_jvm_available(False):
            result = json.loads(plugin.parse_pl_formula("a => b"))
        assert "error" in result
        assert "JVM" in result["error"]

    def test_execute_pl_query_no_jvm(self, plugin):
        with _patch_jvm_available(False):
            result = json.loads(
                plugin.execute_pl_query('{"belief_set":"a","query":"a"}')
            )
        assert "error" in result

    def test_check_pl_consistency_no_jvm(self, plugin):
        with _patch_jvm_available(False):
            result = json.loads(plugin.check_pl_consistency("a"))
        assert "error" in result

    def test_execute_fol_query_no_jvm(self, plugin):
        with _patch_jvm_available(False):
            result = json.loads(
                plugin.execute_fol_query('{"belief_set":"p(X)","query":"p(X)"}')
            )
        assert "error" in result

    def test_check_fol_consistency_no_jvm(self, plugin):
        with _patch_jvm_available(False):
            result = json.loads(plugin.check_fol_consistency("p(X)"))
        assert "error" in result

    def test_execute_modal_query_no_jvm(self, plugin):
        with _patch_jvm_available(False):
            result = json.loads(
                plugin.execute_modal_query('{"belief_set":"[]a","query":"a"}')
            )
        assert "error" in result

    def test_check_modal_consistency_no_jvm(self, plugin):
        with _patch_jvm_available(False):
            result = json.loads(
                plugin.check_modal_consistency('{"belief_set":"[]a"}')
            )
        assert "error" in result

    def test_validate_formula_no_jvm(self, plugin):
        with _patch_jvm_available(False):
            result = json.loads(
                plugin.validate_formula('{"formula":"a","logic_type":"propositional"}')
            )
        assert "error" in result


# ---------------------------------------------------------------------------
# Test: PL methods
# ---------------------------------------------------------------------------


class TestPLMethods:
    """Propositional logic methods delegate to TweetyBridge."""

    @pytest.fixture()
    def plugin_and_bridge(self):
        from argumentation_analysis.plugins.logic_agent_plugin import LogicAgentPlugin
        bridge = _make_bridge(validate_pl=True)
        return LogicAgentPlugin(), bridge

    def test_parse_pl_formula_valid(self, plugin_and_bridge):
        plugin, bridge = plugin_and_bridge
        with _patch_jvm_available(True), _patch_tweety_bridge(bridge):
            result = json.loads(plugin.parse_pl_formula("a => b"))

        assert result["is_valid"] is True
        assert result["formula"] == "a => b"
        bridge.validate_pl_formula.assert_called_once_with("a => b")

    def test_parse_pl_formula_invalid(self, plugin_and_bridge):
        plugin, bridge = plugin_and_bridge
        bridge.validate_pl_formula.return_value = False
        with _patch_jvm_available(True), _patch_tweety_bridge(bridge):
            result = json.loads(plugin.parse_pl_formula("invalid!!"))

        assert result["is_valid"] is False

    def test_execute_pl_query(self, plugin_and_bridge):
        plugin, bridge = plugin_and_bridge
        with _patch_jvm_available(True), _patch_tweety_bridge(bridge):
            result = json.loads(
                plugin.execute_pl_query(
                    '{"belief_set": "a => b\\nb", "query": "b"}'
                )
            )

        assert result["accepted"] is True
        assert result["query"] == "b"
        bridge.execute_pl_query.assert_called_once()

    def test_check_pl_consistency(self, plugin_and_bridge):
        plugin, bridge = plugin_and_bridge
        with _patch_jvm_available(True), _patch_tweety_bridge(bridge):
            result = json.loads(plugin.check_pl_consistency("a => b\nb"))

        assert result["is_consistent"] is True
        bridge.check_consistency.assert_called_once_with(
            "a => b\nb", logic_type="propositional"
        )


# ---------------------------------------------------------------------------
# Test: FOL methods
# ---------------------------------------------------------------------------


class TestFOLMethods:
    """First-order logic methods delegate correctly."""

    @pytest.fixture()
    def plugin_and_bridge(self):
        from argumentation_analysis.plugins.logic_agent_plugin import LogicAgentPlugin
        bridge = _make_bridge()
        return LogicAgentPlugin(), bridge

    def test_execute_fol_query(self, plugin_and_bridge):
        plugin, bridge = plugin_and_bridge
        with _patch_jvm_available(True), _patch_tweety_bridge(bridge):
            result = json.loads(
                plugin.execute_fol_query(
                    '{"belief_set": "forall X: p(X)", "query": "exists Y: p(Y)"}'
                )
            )

        assert result["accepted"] is True
        assert result["query"] == "exists Y: p(Y)"
        bridge.execute_fol_query.assert_called_once()

    def test_check_fol_consistency(self, plugin_and_bridge):
        plugin, bridge = plugin_and_bridge
        with _patch_jvm_available(True), _patch_tweety_bridge(bridge):
            result = json.loads(plugin.check_fol_consistency("forall X: p(X)"))

        assert result["is_consistent"] is True
        bridge.check_consistency.assert_called_once_with(
            "forall X: p(X)", logic_type="fol"
        )


# ---------------------------------------------------------------------------
# Test: Modal methods
# ---------------------------------------------------------------------------


class TestModalMethods:
    """Modal logic methods handle logic_type correctly."""

    @pytest.fixture()
    def plugin_and_bridge(self):
        from argumentation_analysis.plugins.logic_agent_plugin import LogicAgentPlugin
        bridge = _make_bridge()
        return LogicAgentPlugin(), bridge

    def test_execute_modal_query_default_logic(self, plugin_and_bridge):
        plugin, bridge = plugin_and_bridge
        with _patch_jvm_available(True), _patch_tweety_bridge(bridge):
            result = json.loads(
                plugin.execute_modal_query(
                    '{"belief_set": "[](a => b)", "query": "[]b"}'
                )
            )

        assert result["accepted"] is True
        assert result["logic_type"] == "K"

    def test_execute_modal_query_s5(self, plugin_and_bridge):
        plugin, bridge = plugin_and_bridge
        with _patch_jvm_available(True), _patch_tweety_bridge(bridge):
            result = json.loads(
                plugin.execute_modal_query(
                    '{"belief_set": "[]a", "query": "a", "logic_type": "S5"}'
                )
            )

        assert result["logic_type"] == "S5"

    def test_check_modal_consistency(self, plugin_and_bridge):
        plugin, bridge = plugin_and_bridge
        with _patch_jvm_available(True), _patch_tweety_bridge(bridge):
            result = json.loads(
                plugin.check_modal_consistency(
                    '{"belief_set": "[]a", "logic_type": "T"}'
                )
            )

        assert result["is_consistent"] is True
        assert result["logic_type"] == "T"
        bridge.check_consistency.assert_called_once()
        call_kwargs = bridge.check_consistency.call_args
        assert "modal_t" in call_kwargs[1]["logic_type"]


# ---------------------------------------------------------------------------
# Test: Cross-logic validate_formula
# ---------------------------------------------------------------------------


class TestValidateFormula:
    """validate_formula dispatches to correct logic type."""

    @pytest.fixture()
    def plugin_and_bridge(self):
        from argumentation_analysis.plugins.logic_agent_plugin import LogicAgentPlugin
        bridge = _make_bridge()
        return LogicAgentPlugin(), bridge

    def test_validate_propositional(self, plugin_and_bridge):
        plugin, bridge = plugin_and_bridge
        with _patch_jvm_available(True), _patch_tweety_bridge(bridge):
            result = json.loads(
                plugin.validate_formula(
                    '{"formula": "a => b", "logic_type": "propositional"}'
                )
            )

        assert result["is_valid"] is True
        assert result["logic_type"] == "propositional"
        bridge.validate_pl_formula.assert_called_once_with("a => b")

    def test_validate_fol(self, plugin_and_bridge):
        plugin, bridge = plugin_and_bridge
        with _patch_jvm_available(True), _patch_tweety_bridge(bridge):
            result = json.loads(
                plugin.validate_formula(
                    '{"formula": "forall X: p(X)", "logic_type": "fol"}'
                )
            )

        assert result["logic_type"] == "fol"

    def test_validate_default_logic_type(self, plugin_and_bridge):
        plugin, bridge = plugin_and_bridge
        with _patch_jvm_available(True), _patch_tweety_bridge(bridge):
            result = json.loads(
                plugin.validate_formula('{"formula": "a"}')
            )

        assert result["logic_type"] == "propositional"


# ---------------------------------------------------------------------------
# Test: Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Exceptions from TweetyBridge are caught and returned as JSON."""

    @pytest.fixture()
    def plugin(self):
        from argumentation_analysis.plugins.logic_agent_plugin import LogicAgentPlugin
        return LogicAgentPlugin()

    def test_parse_pl_formula_exception(self, plugin):
        bridge = MagicMock()
        bridge.validate_pl_formula.side_effect = RuntimeError("Parse failed")
        with _patch_jvm_available(True), _patch_tweety_bridge(bridge):
            result = json.loads(plugin.parse_pl_formula("bad"))

        assert "error" in result
        assert "Parse failed" in result["error"]

    def test_execute_pl_query_bad_json(self, plugin):
        with _patch_jvm_available(True):
            result = json.loads(plugin.execute_pl_query("not json"))

        assert "error" in result


# ---------------------------------------------------------------------------
# Test: Registry and factory integration
# ---------------------------------------------------------------------------


class TestRegistryIntegration:
    """LogicAgentPlugin is registered in CapabilityRegistry."""

    def test_plugin_registered_in_setup_registry(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry(include_optional=False)
        reg = registry._registrations.get("logic_agent_plugin")
        assert reg is not None
        caps = reg.capabilities
        assert "propositional_reasoning" in caps
        assert "first_order_reasoning" in caps
        assert "modal_reasoning" in caps


class TestFactoryIntegration:
    """AGENT_SPECIALITY_MAP includes logic_agents."""

    def test_formal_logic_has_logic_agents(self):
        from argumentation_analysis.agents.factory import AGENT_SPECIALITY_MAP

        assert "logic_agents" in AGENT_SPECIALITY_MAP["formal_logic"]

    def test_watson_has_logic_agents(self):
        from argumentation_analysis.agents.factory import AGENT_SPECIALITY_MAP

        assert "logic_agents" in AGENT_SPECIALITY_MAP["watson"]

    def test_plugin_registry_has_logic_agents(self):
        from argumentation_analysis.agents.factory import _PLUGIN_REGISTRY

        assert "logic_agents" in _PLUGIN_REGISTRY
        module_path, class_name = _PLUGIN_REGISTRY["logic_agents"]
        assert "logic_agent_plugin" in module_path
        assert class_name == "LogicAgentPlugin"
