# -*- coding: utf-8 -*-
"""#2494 on the real JVM: the in-JVM FOL reasoner's verdict is read for what
it decides.

Measured on ``main``: ``SimpleFolReasoner`` ranges its quantifiers over the
declared sort, but builds its Herbrand base from the constants that appear in a
formula or in the query, so an atom over any other declared constant is always
false. Its domain is also closed: a set that needs an individual nobody named
reads inconsistent. Four classically consistent sets were decided
inconsistent. Synthetic predicates and constants only.
"""

import asyncio
import re
import sys
from unittest.mock import MagicMock

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2494 tests require the real JVM (jpype mocked by --disable-jvm-session)",
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


CONSISTENT = {
    "existential beside a named constant": _kb(
        "thing = {socrates}", ["Man(thing)"], "Man(socrates)", "exists X: (!Man(X))"
    ),
    "two existentials, one declared constant": _kb(
        "thing = {w}", ["Man(thing)"], "exists X: (Man(X))", "exists X: (!Man(X))"
    ),
    "existential over a declared-only constant": _kb(
        "thing = {w}", ["Man(thing)"], "exists X: (Man(X))"
    ),
    "universal over declared-only constants": _kb(
        "thing = {a, b}", ["Man(thing)"], "forall X: (Man(X))"
    ),
    # The rows below go through the witnessed copy. Tweety's str() printed
    # the first as "!Man(a)&&Man(b)", and its toNnf() left the last two
    # quantifiers under a negation: the copy's first version read the first
    # and the last inconsistent, decided.
    "negated conjunction beside a declared-only constant": _kb(
        "thing = {a, b, c}", ["Man(thing)"], "Man(a)", "!(Man(a) && Man(b))"
    ),
    "negated universal": _kb(
        "thing = {a}", ["Man(thing)"], "Man(a)", "!(forall X: (Man(X)))"
    ),
    "universal premise": _kb(
        "thing = {a}",
        ["Man(thing)", "Bad"],
        "Man(a)",
        "(forall X: (Man(X))) => Bad",
        "!Bad",
    ),
    "negated implication hides an existential": _kb(
        "thing = {a}",
        ["Man(thing)", "Bad"],
        "Man(a)",
        "Bad",
        "!(Bad => (forall X: (Man(X))))",
    ),
}


@pytest.mark.parametrize("label", list(CONSISTENT))
def test_a_consistent_set_is_not_decided_inconsistent(handler, label):
    """Born red: ``main`` returned ``(False, "... inconsistent", "tweety")``."""
    verdict, message, solver = handler.check_consistency_by(
        CONSISTENT[label], solver="tweety"
    )

    assert (verdict, solver) == (True, "tweety"), message


EXACT = {
    "consistent ground set": (
        _kb(
            "thing = {socrates, plato}", ["Man(thing)"], "Man(socrates)", "!Man(plato)"
        ),
        True,
    ),
    "ground contradiction": (
        _kb("thing = {a}", ["Man(thing)"], "Man(a)", "!Man(a)"),
        False,
    ),
    "syllogism refuted": (
        _kb(
            "thing = {socrates}",
            ["Man(thing)", "Mortal(thing)"],
            "forall X: (Man(X) => Mortal(X))",
            "Man(socrates)",
            "!Mortal(socrates)",
        ),
        False,
    ),
    "existential refuted by a universal": (
        _kb("thing = {a}", ["Man(thing)"], "forall X: (Man(X))", "exists X: (!Man(X))"),
        False,
    ),
    "universal premise refuted": (
        _kb(
            "thing = {a}",
            ["Man(thing)", "Bad"],
            "forall X: (Man(X))",
            "(forall X: (Man(X))) => Bad",
            "!Bad",
        ),
        False,
    ),
}


ROUND_TRIP = [
    "!(Man(a) && Man(b))",
    "(forall X: (Man(X))) => Man(a)",
    "Man(a) <=> (exists X: (!Man(X)))",
    "!(exists X: (Man(X) || R(X, a)))",
    "!(!(Man(a)) || (Man(b) && !Man(a)))",
    "forall X: (exists Y: (R(X, Y) && !(R(Y, X) => Man(Y))))",
    "Bad",
    "+",
    "Man(a) ^^ Man(b) ^^ R(a, b)",
]


@pytest.mark.parametrize("text", ROUND_TRIP)
def test_the_copy_writes_each_formula_back_as_itself(handler, text):
    """The witnessed copy is written as text and parsed again. ``str()`` on
    a Tweety formula does not survive that: ``!(Man(a) && Man(b))`` prints as
    ``!Man(a)&&Man(b)``, and ``!(exists X: ...)`` prints as text the parser
    refuses."""
    import jpype

    from argumentation_analysis.agents.core.logic import fol_handler as fol

    belief_set = handler.create_belief_set_from_string(
        _kb("thing = {a, b}", ["Man(thing)", "R(thing, thing)", "Bad"], "Man(a)")
    )
    parser_cls = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
    parser = parser_cls()
    parser.setSignature(belief_set.getSignature())
    formula = parser.parseFormula(text)
    reparser = parser_cls()
    reparser.setSignature(belief_set.getSignature())

    written = fol._tweety_text(formula)

    assert reparser.parseFormula(written).equals(formula), written


# LADR back to the parser's syntax, token by token (#2504). The writer
# parenthesises every sub-formula, so no precedence is left to guess.
_FROM_LADR = [
    ("<->", "<=>"),
    ("->", "=>"),
    ("&", "&&"),
    ("|", "||"),
    ("-", "!"),
    ("$T", "+"),
    ("$F", "-"),
]


@pytest.mark.parametrize("text", [t for t in ROUND_TRIP if "^^" not in t])
def test_the_ladr_input_means_each_formula(handler, text):
    """#2504: Prover9 and Mace4 read the formula of the belief set, written
    by the same writer. LADR has no exclusive disjunction; those rows are
    decided on the binaries in ``test_worker_ladr_from_structure_2504.py``."""
    import jpype

    from argumentation_analysis.agents.core.logic import fol_handler as fol

    belief_set = handler.create_belief_set_from_string(
        _kb("thing = {a, b}", ["Man(thing)", "R(thing, thing)", "Bad"], "Man(a)")
    )
    parser_cls = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
    parser = parser_cls()
    parser.setSignature(belief_set.getSignature())
    formula = parser.parseFormula(text)
    reparser = parser_cls()
    reparser.setSignature(belief_set.getSignature())

    ladr = fol._ladr_text(formula)
    back = ladr
    for ladr_token, tweety_token in _FROM_LADR:
        back = back.replace(ladr_token, tweety_token)
    back = re.sub(r"\b(all|exists) (\w+) \(", r"\1 \2: (", back)
    back = re.sub(r"\ball ", "forall ", back)
    back = re.sub(r"\bp_(\w+)", r"\1", back)

    assert reparser.parseFormula(back).equals(formula), (ladr, back)


@pytest.mark.parametrize("label", list(EXACT))
def test_a_verdict_the_domain_decides_stays_decided(handler, label):
    """Control: no existential under a universal, so the witnessed domain is
    exact and both verdicts stay decided."""
    text, expected = EXACT[label]

    verdict, message, _ = handler.check_consistency_by(text, solver="tweety")

    assert verdict is expected, message


INEXACT = {
    # Consistent, but only over an infinite domain.
    "infinite models only": _kb(
        "thing = {a}",
        ["Less(thing, thing)"],
        "forall X: (exists Y: (Less(X, Y)))",
        "forall X: (!Less(X, X))",
        "forall X: (forall Y: (forall Z: ((Less(X, Y) && Less(Y, Z)) => Less(X, Z))))",
    ),
    # Inconsistent; the finite domain cannot tell it from the one above.
    "refuted existential under a universal": _kb(
        "thing = {a}",
        ["R(thing, thing)"],
        "forall X: (exists Y: (R(X, Y)))",
        "forall X: (forall Y: (!R(X, Y)))",
    ),
}


@pytest.mark.parametrize("label", list(INEXACT))
def test_an_existential_under_a_universal_is_not_decided(handler, label):
    """Born red on ``infinite models only`` (``main``: ``False``). A finite
    domain cannot stand in for a Skolem function, so "no model" reads
    ``None``, not ``False``."""
    verdict, message, solver = handler.check_consistency_by(
        INEXACT[label], solver="tweety"
    )

    assert (verdict, solver) == (None, "tweety"), message
    assert "no verdict" in message


def test_the_async_check_reads_the_same_domain(handler):
    """``_fol_check_consistency_with_tweety`` (fallback and comparison
    baseline) goes through the same reading."""
    belief_set = handler.create_belief_set_from_string(
        CONSISTENT["existential beside a named constant"]
    )

    verdict, message = asyncio.run(
        handler._fol_check_consistency_with_tweety(belief_set)
    )

    assert verdict is True, message


def test_over_the_atom_budget_no_inconsistency_is_published(handler, monkeypatch):
    """Over ``_IN_JVM_MAX_ATOMS`` the witnessed copy is not built. The plain
    check still answers "consistent" when it finds a model, and its
    "inconsistent" reads ``None``: a witness is missing from its domain."""
    from argumentation_analysis.agents.core.logic import fol_handler as fol

    monkeypatch.setattr(fol, "_IN_JVM_MAX_ATOMS", 0)

    needs_a_witness, message, _ = handler.check_consistency_by(
        CONSISTENT["existential beside a named constant"], solver="tweety"
    )
    has_a_model, control_message, _ = handler.check_consistency_by(
        EXACT["consistent ground set"][0].replace("!Man(plato)", "exists X: (!Man(X))"),
        solver="tweety",
    )

    assert needs_a_witness is None, message
    assert has_a_model is True, control_message
