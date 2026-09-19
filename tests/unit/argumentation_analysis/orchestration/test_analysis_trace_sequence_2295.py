"""#2295 — argumentative sequence on ``analysis_trace``: anchor / move / reacts_to-by-id.

Guards the three-layer delivery, each against the REAL implementation
(anti-#1019: no mocked writer agreeing with itself):

1. Schema (``shared_state.add_trace_entry``): optional ``anchor``+``move``,
   closed Walton-Krabbe vocabulary, fail-loud on violation, and NEVER a
   fabricated offset-0 anchor (tri-état: absent means absent).
2. Instrumented site (``state_writers._write_fact_extraction_to_state``): one
   per-argument ``assert`` entry, anchored ONLY when the verbatim
   ``source_quote`` occurs exactly once in the source text (paraphrase,
   absence and ambiguity each leave the key out, with the reason named).
   The 16 other trace writers are untouched (legacy contract pinned).
3. Sanitize: ``anchor`` (ints) and ``move`` (closed vocab) survive
   sanitization while ``summary`` is dropped as before — the new fields
   carry no source text by construction.
4. Control (#2295 DoD): the anchor order DIFFERS from the timestamp order
   when the extraction lists arguments out of text order — the sequence
   measures the text, not the execution clock.

Privacy: synthetic text only.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation.sanitize_state import sanitize_state
from argumentation_analysis.orchestration.state_writers import (
    _write_fact_extraction_to_state,
)

QUOTE_ALPHA = "La quote alpha est unique ici"
QUOTE_BETA = "La quote beta arrive en second dans le texte"
SOURCE = (
    "Premier paragraphe. "
    + QUOTE_ALPHA
    + ". Milieu du texte, Milieu du texte. "
    + QUOTE_BETA
    + " mais sera listée en premier par l'extraction. Fin du texte."
)


def _new_state() -> UnifiedAnalysisState:
    return UnifiedAnalysisState(SOURCE)


class TestTraceEntrySchema2295:
    """add_trace_entry: optional anchor/move, closed vocab, fail-loud."""

    def test_anchor_and_move_stored_when_provided(self):
        state = _new_state()
        state.add_trace_entry(
            phase="extract",
            agent="FactExtraction",
            reacts_to=["arg_1"],
            summary="assert arg_1 — ancre offset 3, longueur 5.",
            anchor={"offset": 3, "length": 5},
            move="assert",
        )
        entry = state.analysis_trace[-1]
        assert entry["anchor"] == {"offset": 3, "length": 5}
        assert entry["move"] == "assert"
        assert entry["reacts_to"] == ["arg_1"]
        # Legacy fields untouched.
        for key in ("phase", "agent", "summary", "timestamp"):
            assert key in entry

    def test_legacy_call_untouched(self):
        """The 17 pre-existing writers pass no anchor/move — no key appears."""
        state = _new_state()
        state.add_trace_entry(
            phase="quality",
            agent="QualityScorer",
            reacts_to=["extract"],
            summary="legacy entry",
        )
        entry = state.analysis_trace[-1]
        assert "anchor" not in entry
        assert "move" not in entry

    def test_unknown_move_fails_loud(self):
        state = _new_state()
        with pytest.raises(ValueError, match="hors vocabulaire"):
            state.add_trace_entry(
                phase="extract",
                agent="X",
                reacts_to=[],
                summary="s",
                move="shout",
            )

    @pytest.mark.parametrize(
        "anchor",
        [
            {"offset": -1, "length": 5},
            {"offset": 3},
            {"offset": "3", "length": 5},
            {"length": 5},
            "not-a-dict",
        ],
    )
    def test_malformed_anchor_fails_loud(self, anchor):
        state = _new_state()
        with pytest.raises(ValueError, match="anchor invalide"):
            state.add_trace_entry(
                phase="extract",
                agent="X",
                reacts_to=[],
                summary="s",
                anchor=anchor,
            )

    def test_closed_vocabulary_is_walton_krabbe(self):
        assert UnifiedAnalysisState.TRACE_MOVE_VOCABULARY == (
            "assert",
            "concede",
            "retract",
            "challenge",
            "withdraw",
        )


class TestInstrumentedExtractSite2295:
    """_write_fact_extraction_to_state: per-argument assert entries, tri-état."""

    @staticmethod
    def _run_extraction(state, arguments):
        _write_fact_extraction_to_state(
            {"arguments": arguments, "claims": []}, state, {}
        )

    def test_unique_verbatim_quotes_anchor_and_react_by_id(self):
        state = _new_state()
        # Extraction lists beta BEFORE alpha — salience order, not text order.
        self._run_extraction(
            state,
            [
                {"text": "Argument beta", "source_quote": QUOTE_BETA},
                {"text": "Argument alpha", "source_quote": QUOTE_ALPHA},
            ],
        )
        assert len(state.analysis_trace) == 2
        first, second = state.analysis_trace
        # Ids assigned in listing order: beta → arg_1, alpha → arg_2.
        assert first["reacts_to"] == ["arg_1"]
        assert second["reacts_to"] == ["arg_2"]
        for entry in (first, second):
            assert entry["move"] == "assert"
            assert entry["phase"] == "extract"
            assert "anchor" in entry
        # Anchors measured against the source text.
        assert first["anchor"] == {
            "offset": SOURCE.index(QUOTE_BETA),
            "length": len(QUOTE_BETA),
        }
        assert second["anchor"] == {
            "offset": SOURCE.index(QUOTE_ALPHA),
            "length": len(QUOTE_ALPHA),
        }

    def test_anchor_order_differs_from_timestamp_order(self):
        """#2295 DoD control: the sequence measures the TEXT, not the clock.

        Extraction listed arg_1 (beta, late in the text) before arg_2 (alpha,
        early): timestamp order is [arg_1, arg_2], anchor order is
        [arg_2, arg_1]. If both orders coincide on every run, either the text
        is trivial or the anchor is never posed — distinguishable by the
        anchored-entry count asserted here.
        """
        state = _new_state()
        self._run_extraction(
            state,
            [
                {"text": "Argument beta", "source_quote": QUOTE_BETA},
                {"text": "Argument alpha", "source_quote": QUOTE_ALPHA},
            ],
        )
        by_time = [e["reacts_to"][0] for e in state.analysis_trace]
        anchored = [e for e in state.analysis_trace if "anchor" in e]
        assert len(anchored) >= 2, "ancre jamais posée — l'ordre ne dit rien"
        by_text = [
            e["reacts_to"][0]
            for e in sorted(anchored, key=lambda e: e["anchor"]["offset"])
        ]
        assert by_time != by_text
        assert by_time == ["arg_1", "arg_2"]
        assert by_text == ["arg_2", "arg_1"]

    def test_paraphrased_quote_leaves_anchor_out_with_reason(self):
        state = _new_state()
        self._run_extraction(
            state,
            [{"text": "Argument", "source_quote": "citation paraphrasee absente"}],
        )
        entry = state.analysis_trace[-1]
        assert "anchor" not in entry
        assert entry["move"] == "assert"
        assert "introuvable" in entry["summary"]

    def test_ambiguous_quote_leaves_anchor_out_with_reason(self):
        state = _new_state()
        repeated = "Milieu du texte"
        assert SOURCE.count(repeated) == 2
        self._run_extraction(state, [{"text": "Argument", "source_quote": repeated}])
        entry = state.analysis_trace[-1]
        assert "anchor" not in entry
        assert "ambiguë" in entry["summary"]

    def test_missing_quote_leaves_anchor_out_with_reason(self):
        state = _new_state()
        self._run_extraction(state, ["Argument sans quote"])
        entry = state.analysis_trace[-1]
        assert "anchor" not in entry
        assert entry["move"] == "assert"
        assert "non fournie" in entry["summary"]

    def test_entry_without_anchor_is_not_offset_zero(self):
        """Negative control (#2295 DoD): absent anchor ≠ offset 0."""
        state = _new_state()
        self._run_extraction(state, ["Argument sans quote"])
        entry = state.analysis_trace[-1]
        assert "anchor" not in entry
        assert entry.get("anchor", {}).get("offset", "absent") != 0

    def test_no_anchor_when_state_has_no_raw_text(self):
        state = _new_state()
        state.raw_text = ""
        self._run_extraction(state, [{"text": "Argument", "source_quote": QUOTE_ALPHA}])
        entry = state.analysis_trace[-1]
        assert "anchor" not in entry


class TestSanitizeKeepsSequenceFields2295:
    """anchor (ints) + move (closed vocab) survive; summary dropped as before."""

    @staticmethod
    def _state_dict_with_trace():
        return {
            "analysis_trace": [
                {
                    "phase": "extract",
                    "agent": "FactExtraction",
                    "reacts_to": ["arg_2"],
                    "summary": "assert arg_2 — ancre offset 20, longueur 7.",
                    "timestamp": "2026-09-19T00:00:00Z",
                    "anchor": {"offset": 20, "length": 7},
                    "move": "assert",
                }
            ]
        }

    def test_sequence_fields_survive_sanitization(self):
        result = sanitize_state(self._state_dict_with_trace())
        entry = result["analysis_trace"][0]
        assert entry["anchor"] == {"offset": 20, "length": 7}
        assert entry["move"] == "assert"
        assert entry["reacts_to"] == ["arg_2"]
        # The nominative-text leaf is dropped exactly as before #2295.
        assert "summary" not in entry
