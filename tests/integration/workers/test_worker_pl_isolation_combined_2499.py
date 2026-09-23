# -*- coding: utf-8 -*-
"""#2499 on the real JVM: the PL phase's isolation net checks its survivors
together.

Measured on ``main``: when the batch check raised, the net kept every formula
Tweety parsed alone and published ``satisfiable: True`` with an all-True model
built from the argument texts. No check ran on the survivors together, so
``{p, !p}`` next to one unparsable formula came out satisfiable. Synthetic
atoms only.
"""

import asyncio
import sys
from unittest.mock import MagicMock, patch

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2499 isolation tests require the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]

# The sanitizer lets this one through and Tweety refuses it, so the batch check
# raises and the isolation net runs.
UNPARSABLE = "p &&"


@pytest.fixture(scope="module", autouse=True)
def _jvm():
    from argumentation_analysis.core.jvm_setup import initialize_jvm

    initialize_jvm()


def _run_pl_phase(formulas):
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_propositional_logic,
    )

    # A short input: the phase's LLM formula generator stays off.
    context = {
        "phase_extract_output": {"arguments": [{"text": "an argument"}]},
        "formulas": list(formulas),
        "_state_object": None,
    }
    return asyncio.run(_invoke_propositional_logic("text", context))


@pytest.mark.parametrize("poisoned", [False, True], ids=["control", "poisoned"])
def test_an_unsat_set_is_never_published_satisfiable(poisoned):
    """Born red on ``poisoned``. The control never enters isolation."""
    formulas = ["p", "!p"] + ([UNPARSABLE] if poisoned else [])

    out = _run_pl_phase(formulas)

    assert out.get("isolation_retry") is (True if poisoned else None), out
    assert out["satisfiable"] is False, out
    assert out["model"] == {}, out
    if poisoned:
        assert out["rejected_count"] == 1


def test_a_survivor_contradictory_on_its_own_is_decided_unsat():
    """``main`` read no single verdict: only an exception dropped a formula."""
    out = _run_pl_phase(["p && !p", "q", UNPARSABLE])

    assert out["isolation_retry"] is True, out
    assert out["satisfiable"] is False, out


def test_a_satisfiable_set_publishes_the_solver_model():
    """Control for the verdict. Born red on the model: ``main`` published
    ``{"p_an_argument_<hash>": True}``, an atom of the argument text, not of
    the formulas."""
    out = _run_pl_phase(["p", "q", UNPARSABLE])

    assert out["isolation_retry"] is True, out
    assert out["satisfiable"] is True, out
    assert out["model"] == {"p": True, "q": True}, out


def test_a_failed_combined_check_is_unverified():
    """The survivors parse one by one but the combined check fails: the verdict
    is None, the sibling FOL net's motif, never True."""
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    with patch.object(
        TweetyBridge,
        "check_consistency_detailed",
        side_effect=RuntimeError("simulated combined-check failure"),
    ):
        out = _run_pl_phase(["p", "q"])

    assert out["isolation_retry"] is True, out
    assert out["satisfiable"] is None, out
    assert out["model"] == {}, out
    assert "simulated combined-check failure" in out["message"], out
