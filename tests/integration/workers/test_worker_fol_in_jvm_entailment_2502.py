# -*- coding: utf-8 -*-
"""#2502 on the real JVM: the in-JVM FOL reasoner's "entailed" is read for what
its domain decides.

Measured on ``main``: asked directly, ``SimpleFolReasoner`` answers over the
same split, closed domain as its consistency check (#2494). ``Man(s)``
entailed ``forall X: (Man(X))``, and ``Man(a)`` over ``{a, b}`` entailed
``exists X: (!Man(X))``. Entailment is now the inconsistency of the set plus
the query's negation, read by ``_in_jvm_consistency``. Synthetic predicates and
constants only.
"""

import sys
from unittest.mock import MagicMock

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2502 tests require the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]


@pytest.fixture(scope="module")
def handler():
    from argumentation_analysis.core.jvm_setup import initialize_jvm

    initialize_jvm()
    from argumentation_analysis.agents.core.logic import fol_handler as fol
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    return fol.FOLHandler(TweetyBridge().initializer)


def _kb(sort, predicates, *formulas):
    return "\n".join([sort] + [f"type({p})" for p in predicates] + list(formulas))


NOT_ENTAILED = {
    "a universal from one instance": (
        _kb("thing = {s}", ["Man(thing)"], "Man(s)"),
        "forall X: (Man(X))",
    ),
    "an existential satisfied only by a declared-only constant": (
        _kb("thing = {a, b}", ["Man(thing)"], "Man(a)"),
        "exists X: (!Man(X))",
    ),
}


@pytest.mark.parametrize("label", list(NOT_ENTAILED))
def test_a_query_that_does_not_follow_is_not_entailed(handler, label):
    """Born red: ``main`` returned ``(True, "... entailed")``."""
    text, query = NOT_ENTAILED[label]

    verdict, message = handler.execute_fol_query(text, query)

    assert verdict is False, message


DECIDED = {
    "an instance of a universal over a declared-only constant": (
        _kb("thing = {a, b}", ["Man(thing)"], "forall X: (Man(X))"),
        "Man(b)",
        True,
    ),
    "syllogism": (
        _kb(
            "thing = {socrates}",
            ["Man(thing)", "Mortal(thing)"],
            "forall X: (Man(X) => Mortal(X))",
            "Man(socrates)",
        ),
        "Mortal(socrates)",
        True,
    ),
    "a ground atom nothing states": (
        _kb("thing = {a, b}", ["Man(thing)"], "Man(a)"),
        "Man(b)",
        False,
    ),
    "an existential from a ground fact": (
        _kb("thing = {a}", ["Man(thing)"], "Man(a)"),
        "exists X: (Man(X))",
        True,
    ),
    "a universal from universals": (
        _kb(
            "thing = {a}",
            ["Man(thing)", "Mortal(thing)"],
            "forall X: (Man(X))",
            "forall X: (Man(X) => Mortal(X))",
        ),
        "forall X: (Mortal(X))",
        True,
    ),
}


@pytest.mark.parametrize("label", list(DECIDED))
def test_a_query_the_domain_decides_stays_decided(handler, label):
    """Controls: each verdict is the classical one."""
    text, query, expected = DECIDED[label]

    verdict, message = handler.execute_fol_query(text, query)

    assert verdict is expected, message


def test_a_query_only_an_infinite_domain_refutes_reads_none(handler):
    """The set has infinite models only, and none of them makes ``R`` reflexive
    somewhere. Over a finite domain it has no model, so ``main`` answered
    "entailed". A finite domain cannot tell, so the answer is ``None``."""
    text = _kb(
        "thing = {a}",
        ["R(thing, thing)"],
        "forall X: (exists Y: (R(X, Y)))",
        "forall X: (!R(X, X))",
        "forall X: (forall Y: (forall Z: ((R(X, Y) && R(Y, Z)) => R(X, Z))))",
    )

    verdict, message = handler.execute_fol_query(text, "exists X: (R(X, X))")

    assert verdict is None, message
    assert "no verdict" in message


def test_fol_query_reads_the_same_domain(handler, monkeypatch):
    """``fol_query`` under the TWEETY solver (and every fallback to it) goes
    through the same reading."""
    from argumentation_analysis.agents.core.logic import fol_handler as fol

    monkeypatch.setattr(fol.settings, "solver", fol.SolverChoice.TWEETY)
    text, query = NOT_ENTAILED["a universal from one instance"]
    belief_set = handler.create_belief_set_from_string(text)

    assert handler.fol_query(belief_set, query) == (False, False)


def test_over_the_atom_budget_a_ground_query_is_still_decided(handler, monkeypatch):
    """Over ``_IN_JVM_MAX_ATOMS`` the witnessed copy is not built. A query
    that needs a witness reads ``None``; a ground query keeps its verdict."""
    from argumentation_analysis.agents.core.logic import fol_handler as fol

    monkeypatch.setattr(fol, "_IN_JVM_MAX_ATOMS", 0)
    text, query = NOT_ENTAILED["a universal from one instance"]
    ground_text, ground_query, expected = DECIDED["a ground atom nothing states"]

    needs_a_witness, message = handler.execute_fol_query(text, query)
    ground, ground_message = handler.execute_fol_query(ground_text, ground_query)

    assert needs_a_witness is None, message
    assert ground is expected, ground_message


def test_the_query_executor_returns_the_verdict(handler):
    """Born red: ``QueryExecutor`` handed ``fol_query`` its Python wrapper and
    tested the returned tuple for ``bool``, so every FOL query read ``None``."""
    from argumentation_analysis.agents.core.logic.belief_set import (
        FirstOrderBeliefSet,
    )
    from argumentation_analysis.agents.core.logic.query_executor import (
        QueryExecutor,
    )

    executor = QueryExecutor()
    text, query = NOT_ENTAILED["a universal from one instance"]
    control_text, control_query, _ = DECIDED["syllogism"]

    refused, message = executor.execute_query(FirstOrderBeliefSet(text), query)
    accepted, control_message = executor.execute_query(
        FirstOrderBeliefSet(control_text), control_query
    )

    assert refused is False, message
    assert accepted is True, control_message
