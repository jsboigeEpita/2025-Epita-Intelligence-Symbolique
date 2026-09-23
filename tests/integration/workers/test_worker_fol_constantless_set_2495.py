# -*- coding: utf-8 -*-
"""#2495 on the real JVM and the bundled solvers: a FOL set without any
constant is decided.

Measured on ``main``: ``FOLLogicAgent.extract_fol_metadata`` declared the sort
of such a set as ``thing = {}``, which Tweety's parser refuses. Every solver
receives the set through that parser, so every solver answered ``None``, and
the FOL phase published the set ``unverified`` with each of its formulas
listed as rejected. The builder now declares one witness constant, which no
formula names: a FOL domain is never empty, so the witness adds no
constraint. It relies on #2494 (the in-JVM domain) and #2514 (EProver's sort
membership). Synthetic predicates only.
"""

import asyncio
import sys
from unittest.mock import MagicMock

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2495 tests require the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]

# Each set names no constant; its classical verdict (FOL domains are
# non-empty).
_SETS = [
    ("an existential", ["exists X: (Man(X))"], True),
    (
        "two universals that contradict",
        ["forall X: (Man(X))", "forall X: (!Man(X))"],
        False,
    ),
    ("two existentials", ["exists X: (Man(X))", "exists X: (!Man(X))"], True),
    (
        "an existential and its universal negation",
        ["exists X: (Man(X))", "forall X: (!Man(X))"],
        False,
    ),
    ("a rule alone", ["forall X: (Man(X) => Mortal(X))"], True),
    (
        "a rule and a counterexample",
        ["forall X: (Man(X) => Mortal(X))", "exists X: (Man(X) && !Mortal(X))"],
        False,
    ),
]
_SOLVERS = ["tweety", "eprover", "prover9", "mace4"]


@pytest.fixture
def fol():
    """The handler module, with the JVM up and the solver pin restored."""
    from argumentation_analysis.core.jvm_setup import initialize_jvm

    initialize_jvm()
    from argumentation_analysis.agents.core.logic import fol_handler

    previous = fol_handler.settings.solver
    try:
        yield fol_handler
    finally:
        fol_handler.settings.solver = previous


def _available(fol, solver):
    from argumentation_analysis.core.mace4_runner import MACE4_EXECUTABLE
    from argumentation_analysis.core.prover9_runner import PROVER9_EXECUTABLE

    if solver == "eprover" and fol._get_eprover_path() is None:
        pytest.skip("the EProver binary is not wired on this seat")
    if solver == "prover9" and not PROVER9_EXECUTABLE.is_file():
        pytest.skip("the bundled Prover9 binary is absent on this seat")
    if solver == "mace4" and not MACE4_EXECUTABLE.is_file():
        pytest.skip("the bundled Mace4 binary is absent on this seat")


def _belief_set_text(formulas):
    """The belief set the FOL phase builds: its signature, then its formulas."""
    from argumentation_analysis.agents.core.logic.fol_logic_agent import (
        FOLLogicAgent,
    )

    meta = FOLLogicAgent.extract_fol_metadata(formulas)
    return "\n".join(meta["signature_lines"] + [""] + meta["formulas"])


@pytest.mark.parametrize("solver", _SOLVERS)
@pytest.mark.parametrize(
    "formulas, expected", [s[1:] for s in _SETS], ids=[s[0] for s in _SETS]
)
def test_a_set_without_constants_is_decided(fol, solver, formulas, expected):
    """DoD: each solver gives the classical verdict. ``main``: ``None``
    everywhere ("Erreur de parsing Tweety")."""
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    _available(fol, solver)
    handler = fol.FOLHandler(TweetyBridge().initializer)

    verdict, message, decided_by = handler.check_consistency_by(
        _belief_set_text(formulas), solver=solver
    )

    assert (verdict, decided_by) == (expected, solver), message


@pytest.mark.parametrize("solver", _SOLVERS)
def test_the_witness_does_not_clash_with_a_predicate(fol, solver):
    """A predicate named ``witness``: EProver refuses a constant that shares
    a predicate's name, and that refusal reads as ``consistent``. The
    witness takes another name, so the contradiction is decided."""
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    _available(fol, solver)
    handler = fol.FOLHandler(TweetyBridge().initializer)
    formulas = ["forall X: (witness(X))", "forall X: (!witness(X))"]

    verdict, message, decided_by = handler.check_consistency_by(
        _belief_set_text(formulas), solver=solver
    )

    assert (verdict, decided_by) == (False, solver), message


@pytest.mark.parametrize("solver", ["tweety", "eprover"])
def test_the_fol_phase_decides_a_set_without_constants(fol, solver):
    """The phase publishes a decided verdict and rejects no formula.
    ``main``: ``fol_status: unverified``, every formula in
    ``rejected_formulas``."""
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_fol_reasoning,
    )

    _available(fol, solver)
    formulas = ["forall X: (Man(X))", "forall X: (!Man(X))"]
    context = {
        "phase_extract_output": {"arguments": [{"text": "an argument"}]},
        "formulas": list(formulas),
        "fol_solver": solver,
        "_state_object": None,
    }

    result = asyncio.run(_invoke_fol_reasoning("text", context))

    assert (result["fol_status"], result["consistent"]) == ("decided", False), result
    assert not result["fol_metrics"].get("rejected_formulas"), result["fol_metrics"]
