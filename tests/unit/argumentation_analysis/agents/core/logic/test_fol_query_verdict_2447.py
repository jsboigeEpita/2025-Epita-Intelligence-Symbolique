"""#2447 (item 6) — ``FOLHandler.execute_fol_query`` has three answers, not two.

Its failure paths (no initializer, no belief set, a parse or reasoner error)
returned ``False``, which reads as "not entailed". A query the reasoner never
answered is now ``None``, with a message naming why, like the sync consistency
check (#1192) and the modal path (#1634).

No JVM: ``jpype`` and the initializer are doubles. The real-Tweety half of the
DoD (a constant declared only in a sort) is in
``tests/integration/workers/test_worker_fol_tweety.py``.
"""

import typing
from typing import Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

from argumentation_analysis.agents.core.logic import fol_handler as fol_handler_module
from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.agents.core.logic.tweety_initializer import (
    TweetyInitializer,
)
from argumentation_analysis.core.config import SolverChoice

KB = "human = {socrate}\ntype(Mortal(human))\n\nMortal(socrate)\n"


@pytest.fixture
def handler():
    initializer = MagicMock(spec=TweetyInitializer)
    initializer.get_fol_parser.return_value = MagicMock()
    with patch.object(fol_handler_module, "settings") as settings:
        settings.solver = SolverChoice.TWEETY
        h = FOLHandler(initializer_instance=initializer)
    return h


@pytest.fixture
def fake_jpype():
    """``FolParser`` is a double, so no JVM is needed to reach the reasoner."""
    with patch.object(fol_handler_module, "jpype") as jpype:
        yield jpype


def _parser_of(fake_jpype):
    return fake_jpype.JClass.return_value.return_value


def _answering(handler, entailed):
    reasoner = MagicMock()
    reasoner.query.return_value = entailed
    handler._initializer_instance.get_reasoner.return_value = reasoner
    return reasoner


def test_no_initializer_is_no_verdict(handler, fake_jpype):
    handler._initializer_instance = None
    with patch.object(
        handler, "create_belief_set_from_string", return_value=MagicMock()
    ):
        entailed, msg = handler.execute_fol_query(KB, "Mortal(socrate)")
    assert entailed is None, msg
    assert "initializer" in msg


def test_a_belief_set_parse_error_is_no_verdict(handler, fake_jpype):
    with patch.object(
        handler,
        "create_belief_set_from_string",
        side_effect=ValueError("Erreur de parsing Tweety: Predicate 'x' ..."),
    ):
        entailed, msg = handler.execute_fol_query("x ::", "Mortal(socrate)")
    assert entailed is None, msg
    assert "Erreur de parsing Tweety" in msg


def test_no_belief_set_is_no_verdict(handler, fake_jpype):
    with patch.object(handler, "create_belief_set_from_string", return_value=None):
        entailed, msg = handler.execute_fol_query(KB, "Mortal(socrate)")
    assert entailed is None, msg
    assert "belief set" in msg


def test_a_query_parse_error_is_no_verdict(handler, fake_jpype):
    """The case measured on ``main``: an undeclared constant in the query."""
    _answering(handler, True)
    _parser_of(fake_jpype).parseFormula.side_effect = RuntimeError(
        "Constant 'platon' has not been declared."
    )
    entailed, msg = handler.execute_fol_query(MagicMock(), "Mortal(platon)")
    assert entailed is None, msg
    assert "Constant 'platon' has not been declared." in msg


def test_a_reasoner_error_is_no_verdict(handler, fake_jpype):
    reasoner = _answering(handler, True)
    reasoner.query.side_effect = RuntimeError("reasoner crashed")
    entailed, msg = handler.execute_fol_query(MagicMock(), "Mortal(socrate)")
    assert entailed is None, msg
    assert "reasoner crashed" in msg


@pytest.mark.parametrize("answer", [True, False])
def test_a_reasoner_answer_is_a_decided_verdict(handler, fake_jpype, answer):
    """Non-vacuity: when the reasoner answers, its answer comes back as is,
    ``False`` included."""
    reasoner = _answering(handler, answer)
    entailed, msg = handler.execute_fol_query(MagicMock(), "Mortal(socrate)")
    assert entailed is answer
    assert msg.endswith("not entailed") is (not answer)
    reasoner.query.assert_called_once()


def test_the_bridge_wrapper_declares_the_tri_state():
    hints = typing.get_type_hints(TweetyBridge.execute_fol_query)
    assert hints["return"] == Tuple[Optional[bool], str]
