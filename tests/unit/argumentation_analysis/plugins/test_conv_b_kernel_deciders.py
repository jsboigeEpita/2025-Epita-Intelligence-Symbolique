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


# CONV-B #1333 fix (po-2025 R532): the three *deciding* kernel_functions of
# TweetyLogicPlugin — ``check_propositional_consistency``,
# ``check_fol_consistency``, ``check_modal_satisfiability`` — were REGISTERED on
# the FormalAgent's kernel and named in its instructions, BUT each crashed at
# call time (the xfail-strict baseline of #1368 documented the break). Each
# contract is now repaired:
#
#   * PL  : unpacks the ``(bool, str)`` tuple from ``TweetyBridge`` into a
#           ``{"is_consistent": ...}`` object (was ``json.dumps(tuple)`` array).
#   * FOL : joins the formula list into a Tweety-syntax STRING before handing
#           it to ``FOLHandler.check_consistency`` (was a raw ``list`` ->
#           ``'list' object has no attribute 'size'``).
#   * Modal: constructs ``ModalHandler`` with the required ``initializer_instance``
#           and calls ``is_modal_kb_consistent`` (was ``ModalHandler()`` +
#           nonexistent ``check_satisfiability``), AND names the resolved solver.
#
# The lesson R319-R321 (selector + registration + instructions != working
# cable) is now verified firsthand: each test calls the REAL consumer (the
# kernel_function) the way the FormalAgent would in AgentGroupChat, and asserts
# a structured verdict is produced — not a crash, not a degraded placeholder.
# The JVM is up under pytest, so the ``@_jvm_required`` short-circuit is NOT
# the path exercised.


class TestConvBKernelDeciders:
    """CONV-B #1333: the deciding kernel_functions must actually decide (JVM up).

    Post-fix (#1368 baseline -> this PR): each decider produces a structured
    verdict, proving the deciding plumbing is alive end-to-end at the
    kernel-function layer. Each test calls the REAL consumer (the
    kernel_function) the way the FormalAgent would in AgentGroupChat — the gap
    that structural tests (registration / instruction-presence) miss.
    """

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
        # The repaired contract exposes ``is_consistent`` (bool from the
        # TweetyBridge tuple), not a bare JSON array.
        assert "is_consistent" in result and isinstance(
            result["is_consistent"], bool
        ), f"PL decider produced no consistency verdict: {result}"

    def test_fol_decider_produces_verdict(self, plugin: TweetyLogicPlugin):
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
        # The repaired contract joins the formulas into a string and exposes
        # ``is_consistent`` (the FOLHandler tuple verdict) — not the previous
        # ``'list' has no attribute 'size'`` crash.
        assert "is_consistent" in result, f"FOL decider produced no verdict: {result}"

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
        # The repaired contract constructs the handler correctly and exposes a
        # named solver (genuine-solver invariant #1019), not the previous
        # ``ModalHandler()`` TypeError.
        assert "is_consistent" in result, f"modal decider produced no verdict: {result}"
        solver = result.get("solver")
        assert (
            isinstance(solver, str) and solver
        ), f"modal verdict must name its solver (genuine-solver #1019): {result}"

    def test_dung_decider_produces_extensions(self, plugin: TweetyLogicPlugin):
        """CONV-B #1333 (po-2025): the Dung decider (FormalAgent ETAPE 3) must
        produce extensions, not crash. Same dead-cable bug class as the modal
        decider (#1371): ``AFHandler()`` missing ``initializer_instance`` +
        nonexistent ``compute_extensions`` method. The repaired contract
        constructs ``AFHandler(TweetyInitializer())`` and calls
        ``analyze_dung_framework``.
        """
        # A trivially grounded framework: one argument, no attacks -> the
        # argument is in every extension under preferred semantics.
        result = _parsed(
            plugin.analyze_dung_framework(
                '{"arguments": ["a"], "attacks": [], "semantics": "preferred"}'
            )
        )
        assert isinstance(
            result, dict
        ), f"Dung decider must return a JSON object, got {type(result).__name__}: {result}"
        assert (
            result.get("error") != "JVM not available"
        ), "Dung decider unreachable (JVM short-circuit)"
        # The repaired contract returns {semantics, extensions, statistics}.
        assert "extensions" in result, f"Dung decider produced no extensions: {result}"
