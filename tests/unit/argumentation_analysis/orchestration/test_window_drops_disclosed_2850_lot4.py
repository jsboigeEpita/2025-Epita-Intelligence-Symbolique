"""#2850 lot 4 — the reading windows of the invoke layer disclose their drop.

The census guard (``test_coverage_census_guard_2850``) still counted seven
`selected_text` rows of ``invoke_callables`` as "Acts silent": the
extraction window (3000), the two logic arms' document window (4000) and
per-argument window (2000), and two text fallbacks (counter 500,
governance 2000). Each feeds an LLM input from a capped reading and said
nothing downstream — the reader of a long document could not tell a
fully-read document from a 3,000-char head (#2850's first measurement).

Two more rows are settled elsewhere: the debate fallback (1500) is
UNREACHABLE — the phase returns early on empty arguments (``no_arguments_
upstream``, :2063) and on every path that reaches the fallback the
ARGUMENTS block is appended unconditionally (:2190), so ``debate_parts``
is never empty; the dead read is deleted (anti-pendulum: subtract). The
Act III excerpt rows live in the restitution test file.

The disclosure lands where the reader is: the phase payload where one
exists, and the phase TRACE summary — the rendered surface (the
coordinator's own read of the document on 19/10 found the lot-2/lot-3
clauses there). Wording is counts-only; no source text leaves the state.

Every witness is born red on the pre-fix tree; the mock pair
(``_get_openai_client`` + ``_guarded_chat_completion``) keeps the runs
hermetic — zero network (#3072).
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.core.reading_window import (
    DEBATE_FALLBACK_WINDOW,
    LLM_EXTRACTION_WINDOW,
    LOGIC_ARGUMENT_WINDOW,
    LOGIC_READING_WINDOW,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import (
    _COUNTER_ARGUMENT_FALLBACK_WINDOW,
    _GOVERNANCE_DELIBERATION_WINDOW,
)

INVOKE = "argumentation_analysis.orchestration.invoke_callables"

# A synthetic document longer than every window here (≈9.5 k chars): a
# witness on a text shorter than its window cannot see a truncation.
LONG = " ".join(
    f"Phrase {i} du document synthétique porte une unité distincte et dense."
    for i in range(140)
)
assert len(LONG) > LOGIC_READING_WINDOW * 2, len(LONG)

# A unit longer than the per-argument window (2000) but not absurd.
LONG_UNIT = " ".join(f"Mot{i} de l'unité longue et détaillée." for i in range(220))
assert len(LONG_UNIT) > LOGIC_ARGUMENT_WINDOW, len(LONG_UNIT)


def _resp(payload: Dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
    )


class _Recorder:
    """Minimal state stand-in: trace entries, coverage, reading windows.

    Deliberately NOT a ``UnifiedAnalysisState``: ``selected_text`` resolves
    its recorder through ``reading_state_from_context``, which filters on
    the real class, so the light recorder proves the phase still works when
    the window cannot be recorded — and it captures the trace entries the
    witnesses read.
    """

    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []
        self.coverage: Dict[str, Any] = {}
        self.analysis_coverage = self.coverage
        self.windows: Dict[str, Any] = {}

    def add_trace_entry(self, **kwargs: Any) -> None:
        self.entries.append(kwargs)

    def record_analysis_coverage(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.coverage[name] = {"k": args[0] if args else None, **kwargs}

    def record_reading_window(self, site: str, selection: Any) -> None:
        self.windows[site] = selection

    def entry_for(self, phase: str) -> Dict[str, Any]:
        for entry in self.entries:
            if entry.get("phase") == phase:
                return entry
        raise AssertionError(
            f"no trace entry for phase {phase!r}; entries: "
            f"{[e.get('phase') for e in self.entries]}"
        )


def _long_state() -> UnifiedAnalysisState:
    """A state whose merged population holds 12 units, every one of them
    longer than the per-argument window, spread over the document."""
    state = UnifiedAnalysisState(LONG)
    state.identified_arguments = {f"pop_{i + 1}": LONG_UNIT for i in range(12)}
    span = len(LONG) // 12
    state.argument_provenance = {
        f"pop_{i + 1}": {"producer": "extract", "offset": i * span} for i in range(12)
    }
    return state


def _capturing_success(captured: list, n_valid: int = 3):
    async def _capture(self, texts, logic_type=None, check_consistency=False):
        captured.extend(texts)
        return SimpleNamespace(
            translations=[
                SimpleNamespace(
                    is_valid=True,
                    formula=f"p_sel_{i} => q_sel_{i}",
                    original_text=t,
                )
                for i, t in enumerate(texts[:n_valid])
            ]
        )

    return _capture


class TestExtractionWindowDisclosed:
    """Row ``selected_text[LLM_EXTRACTION_WINDOW]#1`` (:8565)."""

    @staticmethod
    def _run(text: str, state: Any) -> Dict[str, Any]:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fact_extraction,
        )

        client = MagicMock()
        payload = {
            "arguments": [{"text": "u1", "source_quote": "q1"}],
            "claims": [{"text": "c1", "source_quote": "q1"}],
            "summary": "s",
        }
        with patch(
            f"{INVOKE}._get_openai_client", return_value=(client, "gpt-witness")
        ), patch(
            f"{INVOKE}._guarded_chat_completion",
            AsyncMock(return_value=_resp(payload)),
        ):
            return asyncio.run(_invoke_fact_extraction(text, {"_state_object": state}))

    def test_payload_pairs_the_window_with_the_source(self) -> None:
        out = self._run(LONG, _Recorder())
        assert out["source_length"] == len(LONG)
        assert out["reading_window_chars"] == LLM_EXTRACTION_WINDOW, (
            "the payload must carry the k of the k-of-N pair — source_length "
            "alone tells the reader how long the document was, never how much "
            "of it the extraction actually read"
        )

    def test_trace_names_the_window_and_the_source(self) -> None:
        state = _Recorder()
        self._run(LONG, state)
        summary = state.entry_for("extract")["summary"]
        assert str(LLM_EXTRACTION_WINDOW) in summary, summary
        assert str(len(LONG)) in summary, summary


class TestPropositionalLogicWindowsDisclosed:
    """Rows ``selected_text[LOGIC_READING_WINDOW]#1`` (:8848) and
    ``selected_text[LOGIC_ARGUMENT_WINDOW]#1`` (:8931)."""

    @staticmethod
    def _run(state: UnifiedAnalysisState) -> Dict[str, Any]:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        pass1 = _resp({"propositions": ["unit_present", "corpus_anchor"]})
        no_formula = _resp({"formulas": []})
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            side_effect=[pass1] + [no_formula] * 8
        )
        captured: list = []
        with patch("openai.AsyncOpenAI", return_value=client), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}
        ), patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator"
            ".translate_batch",
            _capturing_success(captured),
        ):
            return asyncio.get_event_loop().run_until_complete(
                _invoke_propositional_logic(state.raw_text, {"_state_object": state})
            )

    def test_metrics_pair_the_document_window_with_the_source(self) -> None:
        state = _long_state()
        result = self._run(state)
        metrics = result["pl_metrics"]
        assert metrics["source_total"] == len(LONG)
        assert metrics["reading_window_chars"] == LOGIC_READING_WINDOW, (
            "the phase feeds Pass 1 from a %d-char head and must say so"
            % LOGIC_READING_WINDOW
        )

    def test_metrics_name_the_argument_window_population(self) -> None:
        state = _long_state()
        result = self._run(state)
        metrics = result["pl_metrics"]
        assert metrics["argument_window_cap"] == LOGIC_ARGUMENT_WINDOW
        assert metrics["argument_window_population"] == 10
        assert metrics["argument_window_over_cap"] == 10, (
            "every selected unit is longer than the per-argument window — the "
            "single-text batch reads a 2000-char head of it and the run must "
            "say how many units that truncation touches"
        )

    def test_trace_names_both_windows(self) -> None:
        state = _long_state()
        self._run(state)
        entry = next(
            e for e in state.analysis_trace if e["phase"] == "propositional_logic"
        )
        summary = entry["summary"]
        assert (
            str(len(LONG)) in summary and str(LOGIC_READING_WINDOW) in summary
        ), summary
        assert str(LOGIC_ARGUMENT_WINDOW) in summary, summary


class TestFolWindowsDisclosed:
    """Rows ``selected_text[LOGIC_READING_WINDOW]#2`` (:9406) and
    ``selected_text[LOGIC_ARGUMENT_WINDOW]#2`` (:9506) — same shape on the
    FOL arm, which reads the ORIGINAL document (``_doc_text_fol``)."""

    @staticmethod
    def _run(state: UnifiedAnalysisState) -> Dict[str, Any]:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        pass1 = _resp(
            {"sorts": {"Person": ["socrates"]}, "predicates": {"Mortal": ["Person"]}}
        )
        no_formula = _resp({"formulas": []})
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            side_effect=[pass1] + [no_formula] * 8
        )
        captured: list = []
        with patch("openai.AsyncOpenAI", return_value=client), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}
        ), patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator"
            ".translate_batch",
            _capturing_success(captured),
        ):
            return asyncio.get_event_loop().run_until_complete(
                _invoke_fol_reasoning(state.raw_text, {"_state_object": state})
            )

    def test_metrics_pair_the_document_window_with_the_source(self) -> None:
        state = _long_state()
        result = self._run(state)
        metrics = result["fol_metrics"]
        assert metrics["source_total"] == len(LONG)
        assert metrics["reading_window_chars"] == LOGIC_READING_WINDOW

    def test_metrics_name_the_argument_window_population(self) -> None:
        state = _long_state()
        result = self._run(state)
        metrics = result["fol_metrics"]
        assert metrics["argument_window_cap"] == LOGIC_ARGUMENT_WINDOW
        assert metrics["argument_window_population"] == 10
        assert metrics["argument_window_over_cap"] == 10

    def test_trace_names_both_windows(self) -> None:
        state = _long_state()
        self._run(state)
        entry = next(e for e in state.analysis_trace if e["phase"] == "fol_reasoning")
        summary = entry["summary"]
        assert (
            str(len(LONG)) in summary and str(LOGIC_READING_WINDOW) in summary
        ), summary
        assert str(LOGIC_ARGUMENT_WINDOW) in summary, summary


class TestGovernanceFallbackDisclosed:
    """Row ``selected_text[_GOVERNANCE_DELIBERATION_WINDOW]#1`` (:2912).

    The fallback fires exactly when the phase has no upstream material at
    all — and then no conflict exists, so the pre-fix trace (gated on
    ``conflict_count > 0``) never ran and the reader could not learn that
    the deliberation read a 2,000-char head.
    """

    @staticmethod
    def _run(text: str, state: Any) -> Dict[str, Any]:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_governance,
        )

        client = MagicMock()
        payload = {"recommended_method": "majority", "consensus_potential": "high"}
        context = {
            # `scores: {}` is the only shape that leaves the extract-derived
            # populations empty (#3030 measured) — the reachable degenerate
            # branch where the deliberation window is the only material.
            "phase_extract_output": {"scores": {}},
            "_state_object": state,
        }
        with patch(
            f"{INVOKE}._get_openai_client", return_value=(client, "gpt-witness")
        ), patch(
            f"{INVOKE}._guarded_chat_completion",
            AsyncMock(return_value=_resp(payload)),
        ):
            return asyncio.run(_invoke_governance(text, context))

    def test_payload_pairs_the_deliberation_window_with_the_source(self) -> None:
        out = self._run(LONG, _Recorder())
        assert out["deliberation_source_length"] == len(LONG)
        assert out["deliberation_window_chars"] == _GOVERNANCE_DELIBERATION_WINDOW

    def test_trace_names_the_fallback_reading_even_with_zero_conflicts(self) -> None:
        state = _Recorder()
        self._run(LONG, state)
        summary = state.entry_for("governance")["summary"]
        assert "0 conflits" in summary or "0 conflit" in summary, summary
        assert str(_GOVERNANCE_DELIBERATION_WINDOW) in summary, summary
        assert str(len(LONG)) in summary, summary


class TestCounterFallbackDisclosed:
    """Row ``selected_text[_COUNTER_ARGUMENT_FALLBACK_WINDOW]#1`` (:1811)."""

    @staticmethod
    def _run(text: str, state: Any) -> Dict[str, Any]:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_counter_argument,
        )

        client = MagicMock()
        counters = [
            {
                "counter_argument": "Une réfutation synthétique.",
                "strategy_used": "socratic_questioning",
            }
        ]
        with patch(
            f"{INVOKE}._get_openai_client", return_value=(client, "gpt-witness")
        ), patch(
            f"{INVOKE}._generate_counters_for_targets",
            AsyncMock(return_value=list(counters)),
        ), patch(
            f"{INVOKE}._evaluate_counter_arguments",
            side_effect=lambda cs, _text: cs,
        ):
            return asyncio.run(_invoke_counter_argument(text, {"_state_object": state}))

    def test_trace_names_the_fallback_reading(self) -> None:
        state = _Recorder()
        out = self._run(LONG, state)
        assert out.get("llm_counter_arguments"), "the LLM arm must have produced"
        summary = state.entry_for("counter")["summary"]
        assert str(_COUNTER_ARGUMENT_FALLBACK_WINDOW) in summary, summary
        assert str(len(LONG)) in summary, summary

    def test_no_window_claim_without_a_prefix(self) -> None:
        """A run whose unit population is empty (no state units, no extract)
        is the only path to the fallback — a SHORT text is fully read, and
        the trace must not claim a truncation that did not happen."""
        state = _Recorder()
        self._run("Texte court mais suffisant.", state)
        summary = state.entry_for("counter")["summary"]
        assert str(_COUNTER_ARGUMENT_FALLBACK_WINDOW) not in summary or (
            "0 " in summary
        ), summary


class TestDebateFallbackIsDead:
    """Row ``selected_text[DEBATE_FALLBACK_WINDOW]#1`` (:2266) — deleted.

    Not a disclosure: the read cannot happen. The phase returns before the
    LLM branch when ``raw_arguments`` is empty (:2063, ``no_arguments_
    upstream``) and appends the ARGUMENTS block unconditionally whenever it
    is not (:2190), so ``debate_parts`` is never empty on the paths that
    reach the fallback. This pins the two guards; the deletion is measured
    by the census row leaving the tree.
    """

    def test_empty_arguments_return_before_the_material(self) -> None:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_debate_analysis,
        )

        state = _Recorder()
        with patch(
            f"{INVOKE}._get_openai_client", return_value=(MagicMock(), "gpt-witness")
        ):
            out = asyncio.run(_invoke_debate_analysis(LONG, {"_state_object": state}))
        assert out.get("debate_degraded_reason") == "no_arguments_upstream"
        summary = state.entry_for("debate")["summary"]
        assert "NON TENU" in summary, summary

    def test_the_material_is_always_structured_when_the_llm_runs(self) -> None:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_debate_analysis,
        )

        state = _Recorder()
        client = MagicMock()
        payload = {
            "strongest_argument": "a",
            "weakest_argument": "b",
            "winner": "Agent A",
            "debate_quality": 4,
            "key_exchanges": [],
            "new_insights": [],
        }
        context = {
            "phase_extract_output": {
                "arguments": [{"text": "Un argument de synthèse."}]
            },
            "_state_object": state,
        }
        with patch(
            f"{INVOKE}._get_openai_client", return_value=(client, "gpt-witness")
        ), patch(
            f"{INVOKE}._guarded_chat_completion",
            AsyncMock(return_value=_resp(payload)),
        ):
            asyncio.run(_invoke_debate_analysis(LONG, context))
        summary = state.entry_for("debate")["summary"]
        assert "ARGUMENTS identified" not in summary  # counts live in the trace
        assert str(DEBATE_FALLBACK_WINDOW) not in summary, (
            "with arguments present the material is built from the structured "
            "parts — the %d-char fallback window must not feed the prompt"
            % DEBATE_FALLBACK_WINDOW
        )
