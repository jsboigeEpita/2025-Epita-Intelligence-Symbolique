# -*- coding: utf-8 -*-
"""#2506 on the real JVM and the bundled Prover9: a query it proves reads
entailed, and a search it did not finish decides nothing.

Measured on ``main``: with the goal's denial and a negative clause of two
literals, ``auto_denials`` asks Prover9 for two proofs. It finds the one while it reads
the input, the search for a second runs out, and the output ends on ``SEARCH
FAILED``, which ``main`` read as "not entailed". The same marker ends a run
stopped by a resource limit, which ``main`` read as a decided verdict too.
Synthetic predicates and constants only.
"""

import sys
from unittest.mock import MagicMock

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2506 tests require the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]


@pytest.fixture
def fol():
    """The handler module, with the JVM up and the solver pin restored."""
    from argumentation_analysis.core.jvm_setup import initialize_jvm
    from argumentation_analysis.core.prover9_runner import PROVER9_EXECUTABLE

    initialize_jvm()
    if not PROVER9_EXECUTABLE.is_file():
        pytest.skip("the bundled Prover9 binary is absent on this seat")
    from argumentation_analysis.agents.core.logic import fol_handler

    previous = fol_handler.settings.solver
    try:
        yield fol_handler
    finally:
        fol_handler.settings.solver = previous


def _kb(*formulas):
    return "\n".join(["thing = {a, b}", "type(Man(thing))"] + list(formulas))


QUERIES = {
    "a query proved while Prover9 reads its input": (
        _kb("Man(a)", "!Man(a) || !Man(b)"),
        "Man(a)",
        True,
    ),
    "control: entailed, the other negative clause is a unit": (
        _kb("Man(a)", "!Man(b)"),
        "Man(a)",
        True,
    ),
    "control: entailed through the disjunction": (
        _kb("Man(a)", "!Man(a) || !Man(b)"),
        "!Man(b)",
        True,
    ),
    "control: not entailed": (_kb("Man(a)", "!Man(a) || !Man(b)"), "Man(b)", False),
}


@pytest.mark.parametrize("label", list(QUERIES))
def test_prover9_answers_with_the_proof_it_found(fol, label):
    """``solver_fallback`` is ``False``: Prover9 answered."""
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    text, goal, expected = QUERIES[label]
    fol.settings.solver = fol.SolverChoice.PROVER9
    handler = fol.FOLHandler(TweetyBridge().initializer)
    belief_set = handler.create_belief_set_from_string(text)

    assert handler.fol_query(belief_set, goal) == (expected, False)


# A query that needs more than one given clause, under a limit of one.
_STOPPED_EARLY = """assign(max_given, 1).
set(prolog_style_variables).
formulas(assumptions).
all X (R(X, s(X))).
all X all Y all Z ((R(X, Y) & R(Y, Z)) -> R(X, Z)).
end_of_list.
formulas(goals).
R(a, a).
end_of_list.
"""


def test_a_search_stopped_by_a_limit_decides_nothing(fol):
    from argumentation_analysis.core.prover9_runner import run_prover9

    output = run_prover9(_STOPPED_EARLY)

    assert "exit (max_given)" in output, output[-400:]
    assert fol._prover9_proved(output) is None
