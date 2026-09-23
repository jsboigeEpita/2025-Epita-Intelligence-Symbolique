# -*- coding: utf-8 -*-
"""#2514 on the real JVM and the bundled EProver: a declared constant that no
formula names is in its sort.

Measured on ``main``: Tweety's ``TPTPWriter`` relativises each quantifier to
its sort (``! [X]: (thing(X) => Man(X))``) and asserts ``thing(c)`` only for
the constants the base's formulas name. A sort whose constants no formula
names could be empty for EProver, so a contradiction between universals read
consistent; a constant named only in the query was outside every sort, so a
universal did not reach it. All three EProver sites published those verdicts
as decided. Synthetic predicates and constants only.
"""

import asyncio
import sys
from unittest.mock import MagicMock

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2514 tests require the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]

_RULE_ONLY = "thing = {a}\ntype(Man(thing))\n\nforall X: (Man(X))"
_RULE_AND_FACT = "thing = {a, b}\ntype(Man(thing))\n\nforall X: (Man(X))\nMan(b)"
_ALL_NAMED = "thing = {a}\ntype(Man(thing))\n\nforall X: (Man(X))\n!Man(a)"


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


@pytest.fixture
def eprover(fol):
    if fol._get_eprover_path() is None:
        pytest.skip("the EProver binary is not wired on this seat")
    return fol


def _handler(fol, solver=None):
    """A handler built the way ``TweetyBridge`` builds it, under ``solver``."""
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    if solver is not None:
        fol.settings.solver = fol.SolverChoice(solver)
    return fol.FOLHandler(TweetyBridge().initializer)


def _lent_constant_contradiction():
    """The isolation net's per-formula check (#2492): a self-contradictory
    universal, over a constant the set lends and the formula does not name."""
    from argumentation_analysis.agents.core.logic.fol_logic_agent import (
        FOLLogicAgent,
    )

    meta = FOLLogicAgent.extract_fol_metadata(
        ["forall X: (Man(X) && !Man(X))"], domain={"socrates"}
    )
    return "\n".join(meta["signature_lines"] + [""] + meta["formulas"])


def _tptp(fol, belief_set):
    import jpype

    text = jpype.JClass("java.io.StringWriter")()
    jpype.JClass("org.tweetyproject.logics.fol.writer.TPTPWriter")(text).printBase(
        belief_set
    )
    return str(text.toString())


def test_a_universal_contradiction_is_inconsistent_under_eprover(eprover):
    """DoD 1, the sync check the phases call. ``main``: ``True``, next to
    ``False`` from Tweety, Prover9 and Mace4."""
    verdict, message, solver = _handler(eprover).check_consistency_by(
        _lent_constant_contradiction(), solver="eprover"
    )

    assert (verdict, solver) == (False, "eprover"), message


def test_the_async_eprover_check_decides_it_too(eprover):
    """``fol_check_consistency`` under EPROVER, the async API."""
    handler = _handler(eprover, "eprover")
    belief_set = handler.create_belief_set_from_string(_lent_constant_contradiction())

    verdict, message = asyncio.run(handler.fol_check_consistency(belief_set))

    assert verdict is False, message


def test_forall_entails_exists_under_eprover(eprover):
    """``main``: not entailed, because the sort could be empty."""
    handler = _handler(eprover)
    belief_set = handler.create_belief_set_from_string(_RULE_ONLY)

    assert handler._fol_query_with_eprover(belief_set, "exists X: (Man(X))") is True


def test_a_universal_reaches_a_constant_named_only_in_the_query(eprover):
    """``main``: not entailed, although ``Man(b)`` makes the sort non-empty:
    ``a`` was outside it."""
    handler = _handler(eprover, "eprover")
    belief_set = handler.create_belief_set_from_string(_RULE_AND_FACT)

    assert handler.fol_query(belief_set, "Man(a)") == (True, False)


def test_a_set_that_names_its_constants_is_decided_as_before(eprover):
    """DoD 2, control: green on ``main``."""
    handler = _handler(eprover)

    assert handler.check_consistency_by(_ALL_NAMED, solver="eprover")[::2] == (
        False,
        "eprover",
    )
    belief_set = handler.create_belief_set_from_string(_RULE_AND_FACT)
    assert handler._fol_query_with_eprover(belief_set, "Man(b)") is True


def test_a_set_that_names_its_constants_goes_to_eprover_as_is(fol):
    """DoD 2: no copy when every declared constant is named. JVM only."""
    belief_set = _handler(fol).create_belief_set_from_string(_ALL_NAMED)

    assert fol._eprover_belief_set(belief_set) is belief_set


def test_the_copy_puts_every_declared_constant_in_its_sort(fol):
    """The TPTP Tweety writes for the copy asserts each declared constant's
    sort, the ones no formula names included. JVM only, no binary."""
    handler = _handler(fol)
    belief_set = handler.create_belief_set_from_string(_RULE_AND_FACT)
    assert "thing(a)" not in _tptp(fol, belief_set)

    written = _tptp(fol, fol._eprover_belief_set(belief_set))

    assert "thing(a)" in written and "thing(b)" in written, written


def _writer_refuses(fol, monkeypatch):
    def refuse(*_args):
        raise fol.UnwritableFormula("no Tweety text for the term Zed")

    monkeypatch.setattr(fol, "_tweety_text", refuse)


def test_a_copy_that_cannot_be_written_raises_in_the_sync_check(eprover, monkeypatch):
    """DoD 3: a defect of our input, not a degraded EProver."""
    _writer_refuses(eprover, monkeypatch)

    with pytest.raises(eprover.UnwritableFormula, match="Zed"):
        _handler(eprover).check_consistency_by(
            _lent_constant_contradiction(), solver="eprover"
        )


def test_a_copy_that_cannot_be_written_is_not_a_fallback(eprover, monkeypatch):
    """DoD 3: the async check and the query raise instead of answering with
    the in-JVM reasoner."""
    handler = _handler(eprover, "eprover")
    contradiction = handler.create_belief_set_from_string(
        _lent_constant_contradiction()
    )
    rule_and_fact = handler.create_belief_set_from_string(_RULE_AND_FACT)
    _writer_refuses(eprover, monkeypatch)

    with pytest.raises(eprover.UnwritableFormula, match="Zed"):
        asyncio.run(handler.fol_check_consistency(contradiction))
    with pytest.raises(eprover.UnwritableFormula, match="Zed"):
        handler.fol_query(rule_and_fact, "Man(a)")
