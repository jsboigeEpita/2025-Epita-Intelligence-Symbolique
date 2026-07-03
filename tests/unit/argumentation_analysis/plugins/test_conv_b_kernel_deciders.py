"""CONV-B #1333 — anti-inerte proof: the TweetyLogicPlugin @kernel_function
*deciding* methods (PL/FOL/Modal consistency) actually produce a verdict when the
JVM is up, and the verdict carries a named solver.

CONTEXT
-------
CONV-A #1332 baseline firsthand (po-2025 R530) showed the conversational
FormalAgent's modal verdict was a *tagheur* (`modalities: deontic/alethic`),
not a solver decision — but that run was a standalone script with **no pytest
conftest → no JVM init**, so the ``@_jvm_required`` kernel_functions
(`check_fol_consistency`, `check_modal_satisfiability`) short-circuited to a
"JVM not available" error and the agent fell back to a manual heuristic.

This test is the DoD CONV-B pre-requisite ("test that calls the REAL consumer";
lesson R319-R321: selector+propagation != wiring). It calls the three deciding
kernel_functions DIRECTLY (the closest testable consumer to the in-conversation
tool-call) and asserts:

1. They do NOT return the ``@_jvm_required`` short-circuit error (the JVM is up
   under pytest) — proving the deciding path is reachable, not dead.
2. They produce a structured verdict (consistency/satisfiability result), not a
   silent empty/degraded placeholder.
3. The modal verdict routes to the capable solver post-#1357 (the
   ``ModalHandler._resolve_active_solver_choice`` hoist, PR #1357) — surfaced
   via the named solver in the result when one is reported.

This does NOT close CONV-B (which requires a verdict produced PAR tool-call in
an AgentGroupChat) but it proves the deciding *plumbing* is alive end-to-end at
the kernel-function layer, isolating the residual gap to the conversational
agent's invocation/scheduling rather than to a dead cable.
"""

import json
from typing import Any, Dict

import pytest

from argumentation_analysis.plugins.tweety_logic_plugin import TweetyLogicPlugin

pytestmark = pytest.mark.tweety


def _parsed(result: str) -> Any:
    """The kernel_functions return JSON strings (SK tool-call contract)."""
    assert isinstance(result, str), "kernel_function must return a JSON string"
    return json.loads(result)


@pytest.fixture(scope="module")
def plugin() -> TweetyLogicPlugin:
    return TweetyLogicPlugin()


# CONV-B #1333 firsthand finding (po-2025 R531): the three *deciding*
# kernel_functions of TweetyLogicPlugin — ``check_propositional_consistency``,
# ``check_fol_consistency``, ``check_modal_satisfiability`` — are REGISTERED on
# the FormalAgent's kernel (factory AGENT_SPECIALITY_MAP["formal_logic"]) and
# named in its instructions (ETAPE 2), BUT each is BROKEN AT CALL TIME:
#
#   * PL  : TweetyBridge.check_consistency returns a ``(bool, str)`` tuple, but
#           the wrapper does ``json.dumps(tuple)`` -> a JSON *array*, not the
#           documented ``{"is_consistent", ...}`` object. Wrong contract.
#   * FOL : passes a ``list`` of formulas to ``FOLHandler.check_consistency``,
#           which expects a belief_set -> ``'list' object has no attribute 'size'``.
#   * Modal: constructs ``ModalHandler()`` with no ``initializer_instance``
#           (required) AND calls ``check_satisfiability`` (no such method; the
#           handler exposes ``is_modal_kb_consistent``) -> ``TypeError``.
#
# This is the lesson R319-R321 firsthand: selector + registration + instructions
# != working cable. These xfail-strict tests document the three broken deciders
# and will flip green the moment each contract is repaired (CONV-B follow-up),
# preventing a silent regression back to "registered but dead".
_PL_BUG = "CONV-B #1333: PL decider returns json.dumps(tuple) -> JSON array, not {is_consistent} dict"
_FOL_BUG = "CONV-B #1333: FOL decider passes list to FOLHandler.check_consistency (expects belief_set) -> 'list' has no attribute 'size'"
_MODAL_BUG = "CONV-B #1333: modal decider constructs ModalHandler() without initializer_instance + calls nonexistent check_satisfiability"


class TestConvBKernelDeciders:
    """CONV-B #1333: the deciding kernel_functions must actually decide (JVM up).

    Currently xfail-strict — three broken deciders identified firsthand. Each
    test calls the REAL consumer (the kernel_function) the way the FormalAgent
    would in AgentGroupChat, surfacing the gap that structural tests
    (registration / instruction-presence) miss.
    """

    @pytest.mark.xfail(strict=True, reason=_PL_BUG)
    def test_propositional_decider_produces_verdict(self, plugin: TweetyLogicPlugin):
        result = _parsed(
            plugin.check_propositional_consistency('{"formulas": ["p => q", "p"]}')
        )
        assert isinstance(
            result, dict
        ), f"PL decider must return a JSON object, got {type(result).__name__}: {result}"
        assert (
            result.get("error") != "JVM not available"
        ), "PL decider unreachable (JVM short-circuit)"
        assert "is_consistent" in result and isinstance(result["is_consistent"], bool)

    @pytest.mark.xfail(strict=True, reason=_FOL_BUG)
    def test_fol_decider_produces_backend_verdict(self, plugin: TweetyLogicPlugin):
        result = _parsed(
            plugin.check_fol_consistency(
                '{"formulas": ["forall X: (P(X))", "exists X: (!P(X))"]}'
            )
        )
        assert isinstance(
            result, dict
        ), f"FOL decider must return a JSON object, got {type(result).__name__}: {result}"
        assert (
            result.get("error") != "JVM not available"
        ), "FOL decider unreachable (JVM short-circuit)"
        backends = result.get("backends")
        assert (
            isinstance(backends, dict) and backends
        ), f"FOL decider produced no backend verdicts: {result}"
        decided = result.get("decided", {})
        assert any(
            bool(v) for v in decided.values()
        ), f"no FOL backend decided: {backends}"

    @pytest.mark.xfail(strict=True, reason=_MODAL_BUG)
    def test_modal_decider_routes_to_capable_solver(self, plugin: TweetyLogicPlugin):
        result = _parsed(
            plugin.check_modal_satisfiability(
                '{"formula": "<>(p)", "logic_type": "S5"}'
            )
        )
        assert isinstance(
            result, dict
        ), f"modal decider must return a JSON object, got {type(result).__name__}: {result}"
        assert (
            result.get("error") != "JVM not available"
        ), "modal decider unreachable (JVM short-circuit)"
        flat_keys = set(result.keys())
        has_verdict = any(
            k in flat_keys for k in ("valid", "is_consistent", "satisfiable", "verdict")
        ) or isinstance(result.get("result"), dict)
        assert (
            has_verdict
        ), f"modal decider produced no satisfiability verdict: {result}"
