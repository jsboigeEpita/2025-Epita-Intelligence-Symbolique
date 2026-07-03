"""CONV-B #1391 anti-inerte guard — the REAL consumer of translate_to_modal's
output (the ModalHandler parser via ``validate_modal_formula``) must accept the
belief-set format the translator produces, and must reject malformed input.

CONTEXT (#1391, builds on the R319-R321 lesson restated in #1380)
-----------------------------------------------------------------
The plugin method ``translate_to_modal`` wraps ``NLToLogicTranslator`` which
validates each modal formula line via ``bridge.modal_handler.validate_modal_formula``
(Tweety MlParser). A unit test that MOCKS the translator (see
test_nl_to_logic_plugin.py) proves the wrapper plumbing but NOT that the belief
set the translator emits actually parses in Tweety -- exactly the "registration
!= wiring" gap that left CONV-B modal at 0 for the whole R530-R540 arc.

This test calls the REAL validate path (``_validate_with_tweety`` with a live
JVM/ModalHandler via ``tweety_bridge_fixture``) on a belief set built by the
production ``_build_modal_belief_set`` helper. It fails loud if:
  - a valid modal belief set ever stops parsing (format drift), or
  - a malformed belief set ever parses (false-green theater).

This is the guard the #1391 DoD requires ("appelle le VRAI consommateur").
"""

import pytest

from argumentation_analysis.services.nl_to_logic import (
    NLToLogicTranslator,
    _build_modal_belief_set,
)

pytestmark = pytest.mark.tweety


def test_build_modal_belief_set_format():
    """The belief-set builder emits the type(<atom>) + formula format (#1391)."""
    bs = _build_modal_belief_set(
        ["vote", "protest", "vote"],  # duplicate -> de-duped
        ["[](vote)", "<>(protest)"],
    )
    assert bs == "type(vote)\ntype(protest)\n\n[](vote)\n<>(protest)"


def test_build_modal_belief_set_rejects_illegal_atoms():
    """Illegal constant identifiers (underscores) are dropped by the builder."""
    bs = _build_modal_belief_set(
        ["action", "bad_atom"],  # "action" legal, "bad_atom" underscored -> filtered
        ["[](action)"],
    )
    assert "type(action)" in bs
    assert "bad_atom" not in bs  # filtered (normalizer is defense-in-depth)


async def test_validate_with_tweety_accepts_valid_modal_belief_set(
    tweety_bridge_fixture,
):
    """REAL consumer: a type()-declared modal belief set parses in Tweety.

    Ground-truth format: ``type(<atom>)`` declarations (the real MlParser
    grammar, firsthand-confirmed via test_modal_logic_agent.py:316 and the
    SPASS track test_track_c_modal_spass_1279 -- NOT ``constant <atom>``
    which is the TweetyBridgeSK simulation format the parser rejects).
    Guards the translator's validate path against format drift.
    """
    translator = NLToLogicTranslator(max_retries=1, logic_type="modal")
    bs = _build_modal_belief_set(["action"], ["[](action)"])
    is_valid, msg = await translator._validate_with_tweety(bs, "modal")
    assert is_valid is True, f"Valid modal belief set rejected: {msg}"


async def test_validate_with_tweety_rejects_malformed_modal(
    tweety_bridge_fixture,
):
    """REAL consumer: a malformed modal formula is rejected (anti-theater)."""
    translator = NLToLogicTranslator(max_retries=1, logic_type="modal")
    # Unbalanced parentheses -> MlParser must reject, never false-green.
    bs = _build_modal_belief_set(["p"], ["[]((p"])
    is_valid, msg = await translator._validate_with_tweety(bs, "modal")
    assert is_valid is False, "Malformed modal formula parsed (false-green!)"
