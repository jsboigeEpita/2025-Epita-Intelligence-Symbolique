# -*- coding: utf-8 -*-
"""#2295 — the deciding reader: the text sequence reaches the Acte II prose.

``collect_text_sequence`` reads the move-bearing anchored entries of
``analysis_trace`` and orders them by TEXT position (anchor offset), not
by execution clock (append/timestamp order). ``build_act2_prompt``
renders the ordered sequence with its honest verdict: when the anchor
order differs from the analysis order, the narrative says so — that
difference is the whole point of #2295 (the state currently flattens the
argumentative construction; the sequence is what restores it).
"""

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    Act2Evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.text_sequence import (
    collect_text_sequence,
)


def _entry(move, offset, arg_id, length=5):
    e = {
        "phase": "extract",
        "agent": "FactExtractionAgent",
        "reacts_to": [arg_id],
        "summary": f"{move} {arg_id}",
        "timestamp": "2026-09-19T00:00:00Z",
        "move": move,
        "anchor": {"offset": offset, "length": length},
    }
    return e


def _state(entries):
    return SimpleNamespace(analysis_trace=list(entries))


class TestCollect:
    def test_moves_sorted_by_text_offset_not_append_order(self):
        # Appended (LLM/extraction) order: arg_2 BEFORE arg_1;
        # text order: arg_1 (offset 40) before arg_2 (offset 5)… inverted
        # on purpose: arg_2 sits at offset 5, arg_1 at offset 40.
        state = _state(
            [
                _entry("assert", 40, "arg_1"),
                _entry("assert", 5, "arg_2"),
            ]
        )
        seq = collect_text_sequence(state)
        assert seq is not None
        assert [m.arg_ref for m in seq.moves] == ["arg_2", "arg_1"]
        assert seq.order_differs is True

    def test_same_order_yields_false(self):
        state = _state(
            [
                _entry("assert", 5, "arg_1"),
                _entry("assert", 40, "arg_2"),
            ]
        )
        seq = collect_text_sequence(state)
        assert seq.order_differs is False

    def test_single_anchored_move_has_indeterminate_order(self):
        state = _state([_entry("assert", 5, "arg_1")])
        seq = collect_text_sequence(state)
        assert seq is not None
        assert seq.order_differs is None

    def test_unanchored_move_never_enters_the_sequence(self):
        # DoD negative control: an entry without an anchor must not be
        # attributed offset 0 — it is excluded from the anchored sequence.
        unanchored = {
            "phase": "extract",
            "agent": "A",
            "reacts_to": ["arg_9"],
            "summary": "assert arg_9",
            "timestamp": "t",
            "move": "assert",
        }
        state = _state([unanchored, _entry("assert", 5, "arg_1")])
        seq = collect_text_sequence(state)
        assert [m.arg_ref for m in seq.moves] == ["arg_1"]

    def test_no_move_bearing_entries_yields_none(self):
        state = _state(
            [
                {
                    "phase": "p",
                    "agent": "a",
                    "reacts_to": [],
                    "summary": "s",
                    "timestamp": "t",
                }
            ]
        )
        assert collect_text_sequence(state) is None

    def test_mixed_vocabulary_keeps_move_labels(self):
        state = _state(
            [
                _entry("challenge", 5, "arg_1"),
                _entry("concede", 40, "arg_2"),
            ]
        )
        seq = collect_text_sequence(state)
        assert [m.move for m in seq.moves] == ["challenge", "concede"]


class TestPromptRendering:
    def _evidence(self, seq):
        ev = Act2Evidence()
        ev.text_sequence = seq
        return ev

    def test_prompt_carries_the_sequence_section(self):
        state = _state(
            [
                _entry("assert", 40, "arg_1"),
                _entry("assert", 5, "arg_2"),
            ]
        )
        prompt = build_act2_prompt(self._evidence(collect_text_sequence(state)))
        assert "SÉQUENCE DU TEXTE" in prompt
        assert "arg_2" in prompt and "arg_1" in prompt
        # the honest verdict: the reader is told the two orders differ
        assert "diffère" in prompt

    def test_prompt_absent_without_sequence(self):
        prompt = build_act2_prompt(Act2Evidence())
        assert "SÉQUENCE DU TEXTE" not in prompt, (
            "honest absence — no anchored moves, no section, never a "
            "fabricated sequence"
        )

    def test_prompt_section_carries_no_source_text(self):
        state = _state(
            [
                _entry("assert", 40, "arg_1"),
                _entry("assert", 5, "arg_2"),
            ]
        )
        prompt = build_act2_prompt(self._evidence(collect_text_sequence(state)))
        assert "Texte source" not in prompt
        # opaque ids + offsets only
        assert "offset" in prompt
