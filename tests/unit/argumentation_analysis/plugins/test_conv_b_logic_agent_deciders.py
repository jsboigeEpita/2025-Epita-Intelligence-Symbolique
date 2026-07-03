"""CONV-B #1333 DoD #1 — the REAL conversational deciders (LogicAgentPlugin) must
produce a verdict, not short-circuit / fabricate.

CONTEXT
-------
The corpus_A conversational smoke run (po-2025 R534, with the FCB bump #1378)
showed the FormalAgent invokes ``LogicAgentPlugin.check_{pl,fol,modal}_consistency``
(NOT ``TweetyLogicPlugin`` -- that plugin's deciders had 0 trace hits). Each
``LogicAgentPlugin`` decider gated on ``_jvm_available()``, which called
``TweetyBridge.get_instance().is_jvm_ready()`` -- a method that does NOT exist on
TweetyBridge (it lives on ``bridge.initializer``). The bare ``except`` swallowed
the AttributeError, so ``_jvm_available()`` ALWAYS returned False and every
decider short-circuited to ``{"error": "JVM/Tweety non disponible"}`` even with a
ready bridge. This was the DoD #1 root cause (the R530 "tagheur": the FormalAgent
called its deciders, always got the JVM error, and answered from parametric
knowledge).

Behind that guard, two latent string mismatches: FOL passed ``logic_type="fol"``
and modal passed ``"modal_s5"`` -- but ``TweetyBridge.check_consistency`` routes
only ``"first_order"`` and the bare codes ``["K","T","S4","S5"]``. Both fell to
the else-branch -> fabricated ``(False, "Unknown logic type")``.

This test calls the REAL consumer (the plugin method) the way the FormalAgent
would, via ``tweety_bridge_fixture`` so the bridge singleton is ready.
"""

import json

import pytest

from argumentation_analysis.plugins.logic_agent_plugin import LogicAgentPlugin

pytestmark = pytest.mark.tweety


def _parsed(result: str):
    assert isinstance(result, str), "kernel_function must return a JSON string"
    return json.loads(result)


class TestConvBLogicAgentDeciders:
    """CONV-B #1333: the conversational deciders (LogicAgentPlugin) must decide."""

    def test_pl_decider_produces_verdict(self, tweety_bridge_fixture):
        result = _parsed(LogicAgentPlugin().check_pl_consistency("p => q\np"))
        assert (
            result.get("error") != "JVM/Tweety non disponible"
        ), "PL decider short-circuited (is_jvm_ready bug)"
        assert "is_consistent" in result, f"PL decider produced no verdict: {result}"

    def test_fol_decider_produces_verdict(self, tweety_bridge_fixture):
        result = _parsed(
            LogicAgentPlugin().check_fol_consistency(
                "forall X: (P(X))\nexists X: (!P(X))"
            )
        )
        assert (
            result.get("error") != "JVM/Tweety non disponible"
        ), "FOL decider short-circuited (is_jvm_ready bug)"
        assert "Unknown logic type" not in str(
            result.get("message", "")
        ), f"FOL decider -> else-branch (fabricated False, logic_type mismatch): {result}"
        assert "is_consistent" in result, f"FOL decider produced no verdict: {result}"

    def test_modal_decider_routes_to_capable_solver(self, tweety_bridge_fixture):
        result = _parsed(
            LogicAgentPlugin().check_modal_consistency(
                json.dumps({"belief_set": "<>(p)", "logic_type": "S5"})
            )
        )
        assert (
            result.get("error") != "JVM/Tweety non disponible"
        ), "modal decider short-circuited (is_jvm_ready bug)"
        assert "Unknown logic type" not in str(
            result.get("message", "")
        ), f"modal decider -> else-branch (fabricated False, logic_type mismatch): {result}"
        assert "is_consistent" in result, f"modal decider produced no verdict: {result}"
        solver = result.get("solver")
        assert (
            isinstance(solver, str) and solver
        ), f"modal verdict must name its solver (genuine-solver #1019): {result}"
