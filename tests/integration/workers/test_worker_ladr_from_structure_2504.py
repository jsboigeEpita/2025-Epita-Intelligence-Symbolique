# -*- coding: utf-8 -*-
"""#2504 on the real JVM and the bundled binaries: Prover9 and Mace4 decide
the formulas of the belief set, not another problem.

Measured on ``main``: their input was Tweety's ``toString()`` with operators
replaced. It prints ``!(Man(a) && Man(b))`` as ``!Man(a)&&Man(b)``, so both
solvers decided a consistent set inconsistent and Prover9 said it entailed
``Man(b)``. LADR also reads a predicate with no argument that starts
uppercase (``Bad``) as a variable, and Tweety's exclusive disjunction was sent
as ``^^``, which LADR does not have: both inputs were refused. Synthetic
predicates and constants only.
"""

import asyncio
import sys
from unittest.mock import MagicMock

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2504 tests require the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]


@pytest.fixture
def fol():
    """The handler module, with the JVM up and the solver pin restored."""
    from argumentation_analysis.core.jvm_setup import initialize_jvm
    from argumentation_analysis.core.mace4_runner import MACE4_EXECUTABLE
    from argumentation_analysis.core.prover9_runner import PROVER9_EXECUTABLE

    initialize_jvm()
    if not (PROVER9_EXECUTABLE.is_file() and MACE4_EXECUTABLE.is_file()):
        pytest.skip("the bundled Prover9/Mace4 binaries are absent on this seat")
    from argumentation_analysis.agents.core.logic import fol_handler

    previous = fol_handler.settings.solver
    try:
        yield fol_handler
    finally:
        fol_handler.settings.solver = previous


def _handler(fol, solver=None):
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    if solver is not None:
        fol.settings.solver = fol.SolverChoice(solver)
    return fol.FOLHandler(TweetyBridge().initializer)


def _kb(sort, predicates, *formulas):
    return "\n".join([sort] + [f"type({p})" for p in predicates] + list(formulas))


DECIDED = {
    "negated conjunction": (
        _kb("thing = {a, b}", ["Man(thing)"], "Man(a)", "!(Man(a) && Man(b))"),
        True,
    ),
    "negated disjunction, contradicted": (
        _kb("thing = {a, b}", ["Man(thing)"], "Man(b)", "!(Man(a) || Man(b))"),
        False,
    ),
    "propositions": (
        _kb("thing = {a}", ["Man(thing)", "Bad", "Good"], "Man(a)", "Bad", "!Good"),
        True,
    ),
    "a contradicted proposition": (
        _kb("thing = {a}", ["Man(thing)", "Bad"], "Man(a)", "Bad", "!Bad"),
        False,
    ),
    # Tweety reads an exclusive disjunction as "an odd number of operands
    # hold": with three true operands it holds.
    "exclusive disjunction, three true operands": (
        _kb(
            "thing = {a, b, c}",
            ["Man(thing)"],
            "Man(a) ^^ Man(b) ^^ Man(c)",
            "Man(a)",
            "Man(b)",
            "Man(c)",
        ),
        True,
    ),
    "exclusive disjunction, two true operands": (
        _kb(
            "thing = {a, b, c}",
            ["Man(thing)"],
            "Man(a) ^^ Man(b) ^^ Man(c)",
            "Man(a)",
            "Man(b)",
            "!Man(c)",
        ),
        False,
    ),
    # Over three operands an exclusive disjunction and a chain of
    # equivalences agree; over two they are each other's negation.
    "exclusive disjunction, two operands both true": (
        _kb("thing = {a, b}", ["Man(thing)"], "Man(a) ^^ Man(b)", "Man(a)", "Man(b)"),
        False,
    ),
    # Controls: no parentheses to lose, no proposition, no exclusive
    # disjunction.
    "control: consistent": (
        _kb("thing = {a, b}", ["Man(thing)"], "Man(a)", "!Man(b)"),
        True,
    ),
    "control: inconsistent": (
        _kb("thing = {a}", ["Man(thing)"], "Man(a)", "!Man(a)"),
        False,
    ),
}


@pytest.mark.parametrize("solver", ["prover9", "mace4"])
@pytest.mark.parametrize("label", list(DECIDED))
def test_the_external_solvers_decide_the_set_they_were_given(fol, solver, label):
    text, expected = DECIDED[label]

    verdict, message, backend = _handler(fol).check_consistency_by(text, solver=solver)

    assert (verdict, backend) == (expected, solver), message


QUERIES = {
    "not entailed past a negated conjunction": (
        _kb("thing = {a, b}", ["Man(thing)"], "Man(a)", "!(Man(a) && Man(b))"),
        "Man(b)",
        False,
    ),
    "a proposition as goal": (
        _kb("thing = {a}", ["Man(thing)", "Bad", "Good"], "Bad", "Bad => Good"),
        "Good",
        True,
    ),
    "control: entailed": (
        _kb("thing = {a, b}", ["Man(thing)"], "Man(a)", "!(Man(a) && Man(b))"),
        "Man(a)",
        True,
    ),
}


@pytest.mark.parametrize("label", list(QUERIES))
def test_prover9_answers_the_query_it_was_given(fol, label):
    """``solver_fallback`` is ``False``: Prover9 answered."""
    text, goal, expected = QUERIES[label]
    handler = _handler(fol, "prover9")
    belief_set = handler.create_belief_set_from_string(text)

    assert handler.fol_query(belief_set, goal) == (expected, False)


@pytest.mark.parametrize("name", ["Zed", "_zed"])
def test_a_constant_ladr_would_read_as_a_variable_is_refused(fol, name):
    """The Tweety parser reads an uppercase name as a variable, so such a
    constant only comes from a formula built in code. LADR would read it as a
    variable, and the writer refuses it rather than send another problem."""
    import jpype

    commons = "org.tweetyproject.logics.commons.syntax."
    array_list = jpype.JClass("java.util.ArrayList")
    sort = jpype.JClass(commons + "Sort")("thing")
    term = jpype.JClass(commons + "Constant")(name, sort)
    predicate = jpype.JClass(commons + "Predicate")("Man", array_list([sort]))
    atom = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolAtom")(
        predicate, array_list([term])
    )

    with pytest.raises(fol.UnwritableFormula, match=name):
        fol._ladr_text(atom)


def _with_an_unwritable_formula(handler):
    """A belief set holding ``Man(Zed)``, the atom added in code: the parser
    would read ``Zed`` as a variable, and so would LADR."""
    import jpype

    belief_set = handler.create_belief_set_from_string(
        _kb("thing = {a}", ["Man(thing)"], "Man(a)")
    )
    signature = belief_set.getSignature()
    zed = jpype.JClass("org.tweetyproject.logics.commons.syntax.Constant")(
        "Zed", signature.getSort("thing")
    )
    atom = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolAtom")(
        signature.getPredicate("Man"), jpype.JClass("java.util.ArrayList")([zed])
    )
    belief_set.add(atom)
    return belief_set


@pytest.mark.parametrize("solver", ["prover9", "mace4"])
def test_an_unwritable_formula_is_not_an_unavailable_solver(fol, solver):
    """The writer's refusal is a defect of our input, like an input Prover9
    refuses (#2489): the check the phases call and the async API raise it.
    Read as a failed run, it let the in-JVM reasoner answer for Prover9, and
    Mace4 degraded to "unavailable"."""
    handler = _handler(fol, solver)
    belief_set = _with_an_unwritable_formula(handler)

    with pytest.raises(fol.UnwritableFormula, match="Zed"):
        handler.check_consistency_by(belief_set, solver=solver)
    with pytest.raises(fol.UnwritableFormula, match="Zed"):
        asyncio.run(handler.fol_check_consistency(belief_set))


def test_an_unwritable_query_is_not_a_fallback(fol):
    """The query path likewise: no in-JVM answer with ``solver_fallback``."""
    handler = _handler(fol, "prover9")
    belief_set = _with_an_unwritable_formula(handler)

    with pytest.raises(fol.UnwritableFormula, match="Zed"):
        handler.fol_query(belief_set, "Man(a)")


# The phases build their belief sets from text, which the writer can always
# write, so these double the writer: it refuses as it would a formula built
# in code. Synthetic formulas, as in the #2489 phase tests.
_SURVIVORS = ["forall X: (Man(X) => Mortal(X))", "Man(socrates)", "Mortal(plato)"]
# Tweety refuses this one, so the combined check fails and isolation runs.
_UNPARSABLE = "Man(socrates"


def _refuse(*_args):
    from argumentation_analysis.agents.core.logic.fol_handler import (
        UnwritableFormula,
    )

    raise UnwritableFormula("no LADR text for the term Zed")


def _metadata(formulas):
    from argumentation_analysis.agents.core.logic.fol_logic_agent import (
        FOLLogicAgent,
    )

    return FOLLogicAgent.extract_fol_metadata(formulas)


@pytest.mark.parametrize("solver", ["prover9", "mace4"])
def test_an_unwritable_formula_fails_the_external_phase(fol, monkeypatch, solver):
    """``_invoke_external_fol_solver`` leaves as an exception, so the executor
    marks the phase FAILED; its error dict would record a completed phase."""
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_external_fol_solver,
    )

    monkeypatch.setattr(fol, "_ladr_text", _refuse)
    meta = _metadata(_SURVIVORS)
    context = {
        "phase_fol_output": {
            "formulas": meta["formulas"],
            "fol_signature": meta["signature_lines"],
        },
        "fol_solver": solver,
    }

    with pytest.raises(fol.UnwritableFormula, match="Zed"):
        asyncio.run(_invoke_external_fol_solver("", context))


def _run_fol_phase(fol, formulas):
    from argumentation_analysis.core import config
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_fol_reasoning,
    )

    if config.settings is not fol.settings:
        pytest.skip("core.config was reloaded; the phase and the handler differ")
    fol.settings.solver = fol.SolverChoice.PROVER9
    context = {
        "phase_extract_output": {"arguments": [{"text": "an argument"}]},
        "formulas": list(formulas),
        "_state_object": None,
    }
    return asyncio.run(_invoke_fol_reasoning("text", context))


def test_an_unwritable_formula_fails_the_fol_phase(fol, monkeypatch):
    """The main FOL phase raises at the first refusal. Read as a Tweety parse
    failure, it sent every formula to isolation, one check each, before the
    first of them raised."""
    refusals = []

    def refuse(*args):
        refusals.append(args)
        _refuse()

    monkeypatch.setattr(fol, "_ladr_text", refuse)

    with pytest.raises(fol.UnwritableFormula, match="Zed"):
        _run_fol_phase(fol, _SURVIVORS)
    assert len(refusals) == 1


def test_isolation_does_not_drop_an_unwritable_formula(fol, monkeypatch):
    """When isolation runs, a formula the writer refuses is not Tweety's
    poison: the phase raises rather than drop it."""
    monkeypatch.setattr(fol, "_ladr_text", _refuse)

    with pytest.raises(fol.UnwritableFormula, match="Zed"):
        _run_fol_phase(fol, _SURVIVORS + [_UNPARSABLE])


def test_isolation_does_not_degrade_an_unwritable_combined_set(fol, monkeypatch):
    """Each survivor is written alone; the input of the survivors together is
    refused, and the phase raises instead of publishing them unverified."""
    real = fol._prover9_input

    def refuses_sets(belief_set, *rest):
        if belief_set.size() > 1:
            _refuse()
        return real(belief_set, *rest)

    monkeypatch.setattr(fol, "_prover9_input", refuses_sets)

    with pytest.raises(fol.UnwritableFormula, match="Zed"):
        _run_fol_phase(fol, _SURVIVORS + [_UNPARSABLE])
