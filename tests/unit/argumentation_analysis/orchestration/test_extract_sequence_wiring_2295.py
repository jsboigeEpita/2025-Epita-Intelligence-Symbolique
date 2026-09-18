# -*- coding: utf-8 -*-
"""#2295 — the ONE instrumented writer site: fact extraction.

The extraction writer receives ``source_quote`` verbatim from the LLM —
the only place where a genuine character anchor in the source text is
available at write time. Each extracted dict-argument emits a trace
entry ``move="assert"`` referencing its opaque arg id; the anchor is
present only when the quote occurs EXACTLY ONCE in the source text
(retained arbitration ``2ab380c2``: absent, paraphrased and ambiguous
quotes all leave the anchor out — tri-state, never a fabricated 0).
The #2315 rebase adds the bound: the writer caps assert entries at 12
and names the truncation in a legacy-style commentary entry.
"""

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_fact_extraction_to_state,
)

_TEXT = (
    "La première prémisse ouvre le débat. Ensuite la concession arrive. "
    "Enfin la conclusion ferme."
)


def _run(output):
    state = UnifiedAnalysisState(initial_text=_TEXT)
    _write_fact_extraction_to_state(output, state, {})
    return state


class TestAnchoredAsserts:
    def test_dict_arg_with_locatable_quote_gets_anchored_assert(self):
        state = _run(
            {
                "arguments": [
                    {
                        "text": "la conclusion ferme",
                        "source_quote": "la conclusion ferme",
                    }
                ]
            }
        )
        asserts = [e for e in state.analysis_trace if e.get("move") == "assert"]
        assert len(asserts) == 1
        entry = asserts[0]
        assert entry["phase"] == "extract"
        assert entry["anchor"]["offset"] == _TEXT.index("la conclusion ferme")
        assert entry["anchor"]["length"] == len("la conclusion ferme")
        # reacts_to widened to identifiers (#2295): the assert references
        # the argument it introduces.
        assert entry["reacts_to"] == ["arg_1"]

    def test_out_of_text_order_extraction_keeps_trace_append_order(self):
        # The LLM lists arguments in ITS order (here: conclusion first);
        # the trace records that order — the READER is what re-orders by
        # anchor. The writer must not pre-sort.
        state = _run(
            {
                "arguments": [
                    {
                        "text": "la conclusion ferme",
                        "source_quote": "la conclusion ferme",
                    },
                    {
                        "text": "La première prémisse",
                        "source_quote": "La première prémisse",
                    },
                ]
            }
        )
        asserts = [e for e in state.analysis_trace if e.get("move") == "assert"]
        assert [a["anchor"]["offset"] for a in asserts] == [
            _TEXT.index("la conclusion ferme"),
            _TEXT.index("La première prémisse"),
        ]

    def test_summary_carries_no_source_text(self):
        quote = "la conclusion ferme"
        state = _run({"arguments": [{"text": quote, "source_quote": quote}]})
        entry = [e for e in state.analysis_trace if e.get("move") == "assert"][0]
        assert quote not in entry["summary"], (
            "privacy: the summary must stay opaque (arg id only), the anchor "
            "is integers"
        )


class TestHonestAbsence:
    def test_quote_not_in_text_gets_no_anchor(self):
        state = _run(
            {"arguments": [{"text": "argument absent", "source_quote": "introuvable"}]}
        )
        asserts = [e for e in state.analysis_trace if e.get("move") == "assert"]
        assert len(asserts) == 1
        assert "anchor" not in asserts[0], (
            "an unlocatable quote is the honest-absence tri-state — never "
            "a fabricated offset 0"
        )

    def test_dict_arg_without_quote_gets_no_anchor(self):
        state = _run({"arguments": [{"text": "argument sans citation"}]})
        asserts = [e for e in state.analysis_trace if e.get("move") == "assert"]
        assert len(asserts) == 1
        assert "anchor" not in asserts[0]

    def test_bare_string_arg_gets_assert_without_anchor(self):
        state = _run({"arguments": ["La première prémisse ouvre le débat."]})
        asserts = [e for e in state.analysis_trace if e.get("move") == "assert"]
        assert len(asserts) == 1
        assert "anchor" not in asserts[0]


class TestBound:
    def test_trace_entries_are_capped_exactly_and_truncation_named(self):
        args = [{"text": f"argument synthetique {i}"} for i in range(30)]
        state = _run({"arguments": args})
        asserts = [e for e in state.analysis_trace if e.get("move") == "assert"]
        assert len(asserts) == 12, (
            "bounded trace growth — a corpus doc must not flood the trace "
            "that the synthesis prompt reads"
        )
        # All arguments still reach the state — the cap bounds the TRACE,
        # never the analysis substrate.
        assert len(state.identified_arguments) == 30
        # The cap is never silent: one legacy-style commentary entry names it.
        notes = [e for e in state.analysis_trace if e.get("move") is None]
        assert len(notes) == 1
        assert "tronquée" in notes[0]["summary"]
        assert "anchor" not in notes[0], (
            "the truncation note designates no span — it must not leak into "
            "the sequence reader as a move"
        )
