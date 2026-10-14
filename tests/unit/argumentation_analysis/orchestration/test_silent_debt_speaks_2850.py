"""#2850 batch 1 (dispatch R1089) — the first live caps speak.

Measured first (the aggregate table on the issue): 81 registry rows still
carry "silent" as their disclosure; 36 sites are living-direct. This slice
treats the first ones — all in ``invoke_callables.py``, all reached by the
spectacular/standard/full workflows:

- governance positions (``arguments[:6]`` / ``claims[:6]``) — shape (a):
  the positions read the merged population through the coverage layer and
  ``record_analysis_coverage("governance", ...)`` names the selection
  (the slice-A pattern the jtms/atms premises already follow);
- jtms sub-populations (``raw_claims[:6]``, ``detected_fallacies[:6]``,
  ``counter_args[:4]`` x2, ``sentences[:8]``) — shape (b): the cap stays
  (they are LLM-produced facts / detections, not the argument population),
  and the payload plus the trace summary say k of N. The trace summary is
  a real render surface: deep_synthesis reads ``analysis_trace`` for its
  sections, and text_sequence renders it in the restitution.

Born red on ``db9129c11``: the governance record is absent and its
positions are the extraction window's head; the jtms payload carries no
totals and the trace line names no drop.
"""

import asyncio
from unittest.mock import MagicMock, patch

from argumentation_analysis.core.shared_state import UnifiedAnalysisState

# The window (extraction) and the population (state) are DELIBERATELY
# disjoint — a witness whose two sources coincide cannot see the swap
# (same fixture discipline as #3030/#3031).
_WINDOW = [f"window claim number {i} about policy" for i in range(6)]
_POP = {
    f"pop_{i + 1}": f"population unit {i + 1} anchored in the corpus" for i in range(12)
}


def _populated_state() -> UnifiedAnalysisState:
    """A state whose merged population is the 12 identified arguments."""
    raw = " ".join(f"Sentence {i} of the corpus carries one unit." for i in range(40))
    state = UnifiedAnalysisState(raw)
    state.identified_arguments = dict(_POP)
    span = len(raw) // len(_POP)
    state.argument_provenance = {
        pop_id: {"producer": "extract", "offset": i * span}
        for i, pop_id in enumerate(_POP)
    }
    return state


def _context(state: UnifiedAnalysisState) -> dict:
    return {
        "_state_object": state,
        "source_metadata": {"opaque_id": "corpus_witness"},
        "phase_extract_output": {"arguments": [{"text": w} for w in _WINDOW]},
    }


def _expected_selection(state: UnifiedAnalysisState, budget: int):
    from argumentation_analysis.orchestration.selection import (
        merged_population_units,
        select_for_budget,
        state_text_length,
    )

    units = merged_population_units(state)
    selection = select_for_budget(units, budget, text_length=state_text_length(state))
    return selection


def _mock_json_response(payload: str) -> MagicMock:
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = payload
    return resp


class TestGovernancePositionsReadThePopulation:
    """Shape (a): the conflict detector's positions are the recorded
    stratified selection, never the extraction window's head."""

    def test_positions_and_record_name_the_population(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_governance,
        )

        state = _populated_state()
        selection = _expected_selection(state, 6)
        expected_texts = [u.text for u in selection.selected]
        expected_ids = [u.unit_id for u in selection.selected]
        client = MagicMock()
        client.chat.completions.create = MagicMock(
            side_effect=lambda **kw: _mock_json_response(
                '{"recommended_method": "majority"}'
            )
        )
        with patch("openai.AsyncOpenAI", return_value=client), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}
        ):
            result = asyncio.get_event_loop().run_until_complete(
                _invoke_governance(state.raw_text, _context(state))
            )

        positions = list(result["positions"].values())
        assert positions == expected_texts
        assert not any(w in positions for w in _WINDOW)
        record = state.analysis_coverage["governance"]
        assert record["k"] == 6
        assert record["N"] == 12
        assert record["unit_ids"] == expected_ids


class TestGovernanceClaimsFallbackRecordsKofN:
    """Shape (b): claims are not the argument population — the cap stays,
    but the record names k of N claims when a state object is present."""

    def test_claims_head_is_recorded_k_of_n(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_governance,
        )

        state = UnifiedAnalysisState(
            "A raw text long enough. Another sentence also long enough."
        )
        claims = [{"text": f"measured claim number {i}"} for i in range(9)]
        ctx = {
            "_state_object": state,
            "phase_extract_output": {"arguments": [], "claims": claims},
        }
        client = MagicMock()
        client.chat.completions.create = MagicMock(
            side_effect=lambda **kw: _mock_json_response(
                '{"recommended_method": "majority"}'
            )
        )
        with patch("openai.AsyncOpenAI", return_value=client), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}
        ):
            result = asyncio.get_event_loop().run_until_complete(
                _invoke_governance(state.raw_text, ctx)
            )

        positions = list(result["positions"].values())
        assert positions == [f"measured claim number {i}" for i in range(6)]
        record = state.analysis_coverage["governance"]
        assert record["k"] == 6
        assert record["N"] == 9
        assert record["unit_ids"] == [f"claim_{i + 1}" for i in range(6)]


class TestJtmsSubPopulationCapsAreDisclosed:
    """Shape (b): the jtms caps stay, but the payload and the trace
    summary say k of N (the trace feeds deep-synthesis's sections)."""

    def _run(self, state, ctx):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_jtms,
        )

        return asyncio.get_event_loop().run_until_complete(
            _invoke_jtms(state.raw_text, ctx)
        )

    def test_payload_and_trace_name_the_drops(self):
        state = _populated_state()
        ctx = _context(state)
        ctx["phase_extract_output"]["claims"] = [
            {"text": f"claim number {i}"} for i in range(9)
        ]
        ctx["phase_hierarchical_fallacy_output"] = {
            "fallacies": [
                {"type": f"fallacy_{i}", "target_argument": "pop_1"} for i in range(9)
            ]
        }
        ctx["phase_counter_output"] = {
            "llm_counter_arguments": [
                {"counter_argument": f"counter number {i}", "target_unit_id": "pop_1"}
                for i in range(7)
            ]
        }
        result = self._run(state, ctx)

        assert result["claims_in_network"] == 6
        assert result["claims_total"] == 9
        assert result["fallacies_considered"] == 6
        assert result["fallacies_total"] == 9
        assert result["counter_arguments_considered"] == 4
        assert result["counter_arguments_total"] == 7
        # The existing count key still reports the capped head (its own
        # disclosure now has a total next to it).
        assert result["counter_argument_count"] == 4

        jtms_trace = [t for t in state.analysis_trace if t.get("phase") == "jtms"]
        assert jtms_trace, "jtms trace entry missing"
        summary = jtms_trace[-1]["summary"]
        assert "6 de 9 sophismes" in summary
        assert "4 de 7 contre-arguments" in summary

    def test_sentence_fallback_names_its_drop(self):
        text = (
            ". ".join(
                f"Sentence number {i} is long enough to be counted here"
                for i in range(12)
            )
            + "."
        )
        state = UnifiedAnalysisState(text)
        ctx = {
            "_state_object": state,
            "phase_extract_output": {"arguments": [], "claims": []},
        }
        result = self._run(state, ctx)

        assert result["arguments_from_sentences"] == 8
        assert result["sentences_total"] == 12
        jtms_trace = [t for t in state.analysis_trace if t.get("phase") == "jtms"]
        assert jtms_trace, "jtms trace entry missing"
        assert "8 de 12 phrases" in jtms_trace[-1]["summary"]


# ---------------------------------------------------------------------------
# Batch 2 (dispatch R1089, slice 2) — aspic + debate speak; the jtms
# detected_fallacies contract moves to its true site (the census walk is BFS,
# not file order: ord=1 is the jtms site, ord=2 the enrichment prompt).
# ---------------------------------------------------------------------------


class _FakeAspicHandler:
    """Stands in for the JVM-bound handler so the witness runs in the gate
    filter — the selection, the record and the trace all fire before it."""

    seen = None

    def analyze_aspic_framework(self, strict, defeasible, axioms):
        type(self).seen = {
            "strict": strict,
            "defeasible": defeasible,
            "axioms": axioms,
        }
        return {"extensions": [[]]}


class TestAspicDefeasibleRulesReadTheSelection:
    """Shape (a): the defeasible rules cite the stratified selection of the
    frame's units — join-safe ids, never the extraction window's head."""

    def test_rules_record_and_trace_name_the_selection(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, patch as _patch

        from argumentation_analysis.orchestration.invoke_callables import _invoke_aspic

        state = _populated_state()
        selection = _expected_selection(state, 4)
        expected_ids = [u.unit_id for u in selection.selected]
        expected_texts = [u.text for u in selection.selected]
        ctx = _context(state)
        ctx["phase_extract_output"]["claims"] = [
            {"text": f"measured claim number {i}"} for i in range(9)
        ]
        ctx["phase_hierarchical_fallacy_output"] = {
            "fallacies": [{"type": f"fallacy_{i}"} for i in range(7)]
        }
        # The translator is an LLM-consuming seam with its own client path
        # (not the mocked openai.AsyncOpenAI): scripted empty so the witness
        # pays for no network and the derived-rules branch stays active.
        _no_translate = SimpleNamespace(
            relations=[], cause="witness_no_translate", error=None
        )
        with _patch(
            "argumentation_analysis.agents.core.logic.aspic_handler.ASPICHandler",
            _FakeAspicHandler,
        ), _patch(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_aspic_rules",
            AsyncMock(return_value=_no_translate),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                _invoke_aspic(state.raw_text, ctx)
            )

        # The rules cite the SELECTION's unit ids, never the window's texts.
        rule_bodies = [
            r["body"][0]
            for r in _FakeAspicHandler.seen["defeasible"]
            if str(r.get("name", "")).startswith("def_arg")
        ]
        assert rule_bodies == expected_ids
        assert not any(w in str(_FakeAspicHandler.seen) for w in _WINDOW)
        # The record names the selection; the payload and trace say k of N.
        record = state.analysis_coverage["aspic"]
        assert record["k"] == 4
        assert record["N"] == 12
        assert record["unit_ids"] == expected_ids
        assert result["aspic_units_considered"] == 4
        assert result["aspic_units_total"] == 12
        assert result["aspic_claims_considered"] == 4
        assert result["aspic_claims_total"] == 9
        assert result["aspic_fallacies_considered"] == 3
        assert result["aspic_fallacies_total"] == 7
        aspic_trace = [t for t in state.analysis_trace if t.get("phase") == "aspic"]
        assert aspic_trace, "aspic trace entry missing"
        summary = aspic_trace[-1]["summary"]
        assert "4 de 12 unités" in summary
        assert "4 de 9 claims" in summary
        assert "3 de 7 sophismes" in summary


class TestDebateMaterialReadsTheSelection:
    """Shape (a): the ARGUMENTS block lists the recorded stratified
    selection, and the material's headers name every sub-population cap."""

    def test_material_headers_and_record_name_the_population(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_debate_analysis,
        )

        state = _populated_state()
        selection = _expected_selection(state, 6)
        expected_texts = [u.text for u in selection.selected]
        expected_ids = [u.unit_id for u in selection.selected]
        ctx = _context(state)
        ctx["phase_hierarchical_fallacy_output"] = {
            "fallacies": [{"type": f"fallacy_{i}"} for i in range(12)]
        }
        ctx["phase_quality_output"] = {
            "per_argument_scores": {f"arg_{i}": {"note_finale": 7.0} for i in range(9)}
        }
        captured = {}

        def _capture(**kw):
            captured["messages"] = kw["messages"]
            return _mock_json_response('{"winner": "Agent A", "debate_quality": 4}')

        client = MagicMock()
        client.chat.completions.create = MagicMock(side_effect=_capture)
        with patch("openai.AsyncOpenAI", return_value=client), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}
        ):
            asyncio.get_event_loop().run_until_complete(
                _invoke_debate_analysis(state.raw_text, ctx)
            )

        user_prompt = str(captured["messages"][-1]["content"])
        # The ARGUMENTS block is the selection, never the window's head.
        for text in expected_texts:
            assert text in user_prompt
        assert not any(w in user_prompt for w in _WINDOW)
        assert "(6 de 12 unités de la population, sélection stratifiée)" in user_prompt
        assert "FALLACIES detected (5 de 12)" in user_prompt
        assert "QUALITY SCORES (6 de 9 arguments scorés)" in user_prompt
        record = state.analysis_coverage["debate"]
        assert record["k"] == 6
        assert record["N"] == 12
        assert record["unit_ids"] == expected_ids
        debate_trace = [t for t in state.analysis_trace if t.get("phase") == "debate"]
        assert debate_trace, "debate trace entry missing"
        summary = debate_trace[-1]["summary"]
        assert "6 de 12 unités débattues" in summary
        assert "5 de 12 sophismes" in summary
        assert "6 de 9 scores de qualité" in summary
