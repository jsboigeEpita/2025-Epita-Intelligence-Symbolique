# -*- coding: utf-8 -*-
"""#2295 — the argumentative-sequence fields on the trace entry.

Post-arbitration contract (main ``2ab380c2`` + the #2315 rebase): the
``move``/``anchor`` fields are optional, but invalid values FAIL LOUD at
the write site — the move is produced by code (``move="assert"`` in the
writer), so an out-of-vocabulary value is a caller bug, never model
variance, and dropping it would erase the difference between « no move
wanted » and « invalid move wiped » (#1019). The #2315 rebase tightens
exactly one thing: an anchor of length zero designates nothing, so
``length`` must be strictly positive (main accepted ``>= 0``).
"""

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState


def _state():
    return UnifiedAnalysisState(initial_text="Texte source de référence.")


class TestOptionalFields:
    def test_legacy_four_args_produce_no_new_keys(self):
        state = _state()
        state.add_trace_entry("extract", "Agent", ["extract"], "summary")
        entry = state.analysis_trace[0]
        assert "move" not in entry, "legacy call sites must stay untouched"
        assert "anchor" not in entry

    def test_move_and_anchor_roundtrip(self):
        state = _state()
        state.add_trace_entry(
            "extract",
            "Agent",
            ["arg_1"],
            "assert arg_1",
            anchor={"offset": 12, "length": 7},
            move="assert",
        )
        entry = state.analysis_trace[0]
        assert entry["move"] == "assert"
        assert entry["anchor"] == {"offset": 12, "length": 7}


class TestClosedVocabulary:
    @pytest.mark.parametrize(
        "move", ["assert", "concede", "retract", "challenge", "withdraw"]
    )
    def test_all_five_moves_accepted(self, move):
        state = _state()
        state.add_trace_entry(
            "p", "a", [], "s", anchor={"offset": 0, "length": 3}, move=move
        )
        assert state.analysis_trace[0]["move"] == move

    def test_unknown_move_raises_fail_loud(self):
        # Retained arbitration: the move is written by code — an
        # out-of-vocabulary value is a caller bug and must fail where it
        # is fixable, not be logged then dropped.
        state = _state()
        with pytest.raises(ValueError, match="hors vocabulaire"):
            state.add_trace_entry(
                "p", "a", [], "s", anchor={"offset": 0, "length": 3}, move="shout"
            )
        assert state.analysis_trace == [], "a rejected entry is not stored"


class TestAnchorValidation:
    def test_negative_offset_raises(self):
        state = _state()
        with pytest.raises(ValueError, match="anchor invalide"):
            state.add_trace_entry(
                "p", "a", [], "s", anchor={"offset": -1, "length": 3}, move="assert"
            )

    def test_zero_length_raises(self):
        # #2315 rebase: a zero-length anchor designates nothing — the span
        # must be non-empty. Main's `>= 0` accepted it; born-red against it.
        state = _state()
        with pytest.raises(ValueError, match="anchor invalide"):
            state.add_trace_entry(
                "p", "a", [], "s", anchor={"offset": 4, "length": 0}, move="assert"
            )

    def test_non_int_raises(self):
        state = _state()
        with pytest.raises(ValueError, match="anchor invalide"):
            state.add_trace_entry(
                "p", "a", [], "s", anchor={"offset": "4", "length": 3}, move="assert"
            )

    def test_extra_keys_never_pass_through(self):
        state = _state()
        state.add_trace_entry(
            "p",
            "a",
            [],
            "s",
            anchor={"offset": 4, "length": 3, "excerpt": "texte réel du corpus"},
            move="assert",
        )
        assert state.analysis_trace[0]["anchor"] == {"offset": 4, "length": 3}
