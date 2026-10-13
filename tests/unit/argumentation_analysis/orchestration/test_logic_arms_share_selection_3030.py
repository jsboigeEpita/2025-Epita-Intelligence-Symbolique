"""#3030 — the coverage record names what every arm actually formalises.

Father defect: `_invoke_propositional_logic` / `_invoke_fol_reasoning`
computed the stratified population selection INSIDE the Pass 2 gate and
recorded it as the coverage, while the degraded arms below (NL fallback
`translate_batch(args[:4])`, PL template `[_pl_atom(a) for a in args]`)
formalised the EXTRACTION WINDOW — a run whose Pass 2 yields no formula
thus records a selection it never translated.

Fix shape (a): ONE selection, computed before the arms — Pass 2 batches,
the NL fallback and the PL template all read `_pl_targets`/`_fol_targets`,
so the existing coverage record tells the truth for every arm. The gate's
`args` half is replaced by the population (`_pl_targets`) whose emptiness
subsumes the window's only empty path (the degenerate `scores: {}` branch
measured in TestTheWindowCanOnlyBeEmptyThroughScores).

Witnesses are born red on the pre-fix tree: the captured translate texts
and the template metrics describe the WINDOW, not the recorded selection.
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch, MagicMock, AsyncMock

from argumentation_analysis.core.shared_state import UnifiedAnalysisState

# The window (extraction) and the population (state) are DELIBERATELY
# disjoint: a witness whose two sources coincide cannot see the swap.
_WINDOW = [f"window claim number {i} about policy" for i in range(6)]
_POP = {
    f"pop_{i + 1}": f"population unit {i + 1} anchored in the corpus" for i in range(12)
}


def _populated_state() -> UnifiedAnalysisState:
    """A state whose merged population is the 12 identified arguments."""
    raw = " ".join(f"Sentence {i} of the corpus carries one unit." for i in range(40))
    state = UnifiedAnalysisState(raw)
    state.identified_arguments = dict(_POP)
    # Offsets spread over the raw text so the stratified selection is not a head.
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


def _mock_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = json.dumps(payload)
    return resp


def _expected_selection_texts(state: UnifiedAnalysisState, budget: int) -> list:
    from argumentation_analysis.orchestration.selection import (
        merged_population_units,
        select_for_budget,
        state_text_length,
    )

    units = merged_population_units(state)
    selection = select_for_budget(units, budget, text_length=state_text_length(state))
    return [u.text for u in selection.selected]


def _expected_selection_ids(state: UnifiedAnalysisState, budget: int) -> list:
    from argumentation_analysis.orchestration.selection import (
        merged_population_units,
        select_for_budget,
        state_text_length,
    )

    units = merged_population_units(state)
    selection = select_for_budget(units, budget, text_length=state_text_length(state))
    return [u.unit_id for u in selection.selected]


def _capturing_translator(captured: list):
    """Patch NLToLogicTranslator.translate_batch to record the texts it got.

    Returns nothing valid so the PL run falls through to the template arm —
    the arm whose inputs the coverage record must also describe.
    """

    async def _capture(self, texts, logic_type=None, check_consistency=False):
        captured.extend(texts)
        return SimpleNamespace(translations=[])

    return _capture


def _succeeding_translator(captured: list, n_valid: int = 3):
    """#3030 residual (coord review R1088) — a translator whose fallback
    SUCCEEDS: it returns ``n_valid`` valid translations of the texts sent.
    The run then stops at the fallback arm (the PL template only fires on
    empty), so the coverage record must describe the units the fallback
    ATTEMPTED — the 4-unit head — not the 10-unit selection Pass 2 failed
    to translate.
    """

    async def _capture(self, texts, logic_type=None, check_consistency=False):
        captured.extend(texts)
        translations = [
            SimpleNamespace(
                is_valid=True,
                formula=f"p_sel_{i} => q_sel_{i}",
                original_text=t,
            )
            for i, t in enumerate(texts[:n_valid])
        ]
        return SimpleNamespace(translations=translations)

    return _capture


class TestTheWindowCanOnlyBeEmptyThroughScores:
    """The measurement behind replacing the gate's `args` half (#3030 DoD 3).

    `_extract_arguments_from_context` is non-empty on every branch EXCEPT the
    degenerate `scores: {}` dict — the one path where the old `and args` gate
    did real work. The population check subsumes it: `_pl_targets` is empty
    exactly when there is nothing to formalise, window or population.
    """

    def _extract(self, context, text="A long enough input text for the tails."):
        from argumentation_analysis.orchestration.invoke_callables import (
            _extract_arguments_from_context,
        )

        return _extract_arguments_from_context(text, context)

    def test_arguments_branch_is_never_empty(self):
        out = self._extract({"phase_extract_output": {"arguments": [{"text": "a"}]}})
        assert out == ["a"]

    def test_claims_branch_is_never_empty(self):
        out = self._extract({"phase_extract_output": {"claims": [{"text": "c"}]}})
        assert out == ["c"]

    def test_scores_branch_is_the_only_empty_path(self):
        out = self._extract({"phase_extract_output": {"scores": {}}})
        assert out == []

    def test_scores_branch_with_keys_is_not_empty(self):
        out = self._extract({"phase_extract_output": {"scores": {"arg_1": 0.5}}})
        assert out == ["arg_1"]

    def test_sentence_tail_is_never_empty(self):
        out = self._extract(
            {}, "One sentence that is long enough. Another sentence also long."
        )
        assert len(out) >= 2 and all(out)

    def test_placeholder_tail_is_never_empty(self):
        assert self._extract({}, "short") == ["argument_placeholder"]


class TestPLDegradedArmsReadTheSelection:
    """Stateful PL run, fake model, Pass 2 returns no formula: the coverage
    record of `propositional_logic` must describe the texts actually
    formalised by the fallback NL arm and the template arm (#3030 DoD 1)."""

    def _run(self, state, ctx):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        pass1 = _mock_response({"propositions": ["unit_present", "corpus_anchor"]})
        no_formula = _mock_response({"formulas": []})
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            side_effect=[pass1] + [no_formula] * 8
        )
        captured: list = []
        with patch("openai.AsyncOpenAI", return_value=client), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}
        ), patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator.translate_batch",
            _capturing_translator(captured),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                _invoke_propositional_logic(state.raw_text, ctx)
            )
        return result, captured

    def test_coverage_record_names_the_texts_the_arms_formalise(self):
        state = _populated_state()
        expected = _expected_selection_texts(state, 10)
        result, captured = self._run(state, _context(state))

        record = state.analysis_coverage["propositional_logic"]
        # The NL fallback received the selection's first texts — population
        # units, never the window's head (the pre-fix defect).
        assert captured == expected[:4]
        assert not any(w in captured for w in _WINDOW)
        # The template arm formalised the whole selection, so its metric
        # equals the recorded k — not the window size.
        assert result["pl_metrics"]["template"] == record["k"] == len(expected)
        # And the mapping the payload ships describes those same texts.
        assert set(result["argument_mapping"].values()) == {t[:60] for t in expected}


class TestFOLDegradedArmReadsTheSelection:
    """Same witness on the FOL axis: Pass 2 empty, NL fallback fires — the
    texts it receives must be the recorded selection, not the window."""

    def _run(self, state, ctx):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        pass1 = _mock_response(
            {"sorts": {"Person": ["socrates"]}, "predicates": {"Mortal": ["Person"]}}
        )
        no_formula = _mock_response({"formulas": []})
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            side_effect=[pass1] + [no_formula] * 8
        )
        captured: list = []
        with patch("openai.AsyncOpenAI", return_value=client), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}
        ), patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator.translate_batch",
            _capturing_translator(captured),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                _invoke_fol_reasoning(state.raw_text, ctx)
            )
        return result, captured

    def test_fallback_translates_the_recorded_selection(self):
        state = _populated_state()
        expected = _expected_selection_texts(state, 10)
        result, captured = self._run(state, _context(state))

        record = state.analysis_coverage["fol_reasoning"]
        assert record["k"] == len(expected)
        assert captured == expected[:4]
        assert not any(w in captured for w in _WINDOW)
        # No template arm exists on FOL (#1278): an empty Pass 2 plus an
        # empty fallback fails loud, never fabricates.
        assert result["fol_status"] == "unavailable:no-translation"


class TestNLToLogicIsUnaffected:
    """#3030 DoD 4 — `_invoke_nl_to_logic`'s only `args` use is the stateless
    mint; stateful runs already translate the selection. Same witness shape
    pins that against drift (green before and after the #3030 fix)."""

    def test_stateful_run_translates_the_selection_not_the_window(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_nl_to_logic,
        )

        state = _populated_state()
        expected = _expected_selection_texts(state, 6)
        captured: list = []

        async def _capture(self, texts, logic_type=None, check_consistency=False):
            captured.extend(texts)
            return SimpleNamespace(
                translations=[],
                overall_consistency=None,
                consistency_message="",
                method="capture",
            )

        with patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator.translate_batch",
            _capture,
        ):
            asyncio.get_event_loop().run_until_complete(
                _invoke_nl_to_logic(state.raw_text, _context(state))
            )

        assert captured == expected
        assert not any(w in captured for w in _WINDOW)
        record = state.analysis_coverage["nl_to_logic"]
        assert record["k"] == len(expected)

    def test_stateless_run_mints_units_from_the_window(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_nl_to_logic,
        )

        captured: list = []

        async def _capture(self, texts, logic_type=None, check_consistency=False):
            captured.extend(texts)
            return SimpleNamespace(
                translations=[],
                overall_consistency=None,
                consistency_message="",
                method="capture",
            )

        ctx = {"phase_extract_output": {"arguments": [{"text": w} for w in _WINDOW]}}
        with patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator.translate_batch",
            _capture,
        ):
            asyncio.get_event_loop().run_until_complete(
                _invoke_nl_to_logic("A text long enough for the tails.", ctx)
            )

        # No state: the fallback mints arg_N units from the window (stated
        # behaviour of merged_population_units) — and 6 ≤ 6 units means the
        # identity selection, so the window texts pass through in order.
        assert captured == _WINDOW


class TestFallbackSuccessReRecordsAttempted:
    """#3030 residual (coord review R1088) — Pass 2 yields nothing AND the
    NL fallback SUCCEEDS: the record written at the Pass 2 gate says k=10,
    but at most 4 units were attempted. When the fallback is the producing
    arm it must re-record the coverage over the units it ATTEMPTED (the
    4-unit head), bands and span recomputed — not only the validly
    translated ones, like Pass 2 counts its batches."""

    def _run_pl(self, state, ctx):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        pass1 = _mock_response({"propositions": ["unit_present", "corpus_anchor"]})
        no_formula = _mock_response({"formulas": []})
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            side_effect=[pass1] + [no_formula] * 8
        )
        captured: list = []
        with patch("openai.AsyncOpenAI", return_value=client), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}
        ), patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator.translate_batch",
            _succeeding_translator(captured, n_valid=3),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                _invoke_propositional_logic(state.raw_text, ctx)
            )
        return result, captured

    def _run_fol(self, state, ctx):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        pass1 = _mock_response(
            {"sorts": {"Person": ["socrates"]}, "predicates": {"Mortal": ["Person"]}}
        )
        no_formula = _mock_response({"formulas": []})
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            side_effect=[pass1] + [no_formula] * 8
        )
        captured: list = []
        with patch("openai.AsyncOpenAI", return_value=client), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}
        ), patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator.translate_batch",
            _succeeding_translator(captured, n_valid=3),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                _invoke_fol_reasoning(state.raw_text, ctx)
            )
        return result, captured

    def test_pl_record_names_the_attempted_head_when_fallback_produces(self):
        state = _populated_state()
        expected_texts = _expected_selection_texts(state, 10)
        expected_ids = _expected_selection_ids(state, 10)
        result, captured = self._run_pl(state, _context(state))

        # The fallback fired on the selection's head and produced.
        assert captured == expected_texts[:4]
        assert result["pl_metrics"]["fallback_nl"] == 3
        assert len(result["formulas"]) == 3
        # The record now names the units ATTEMPTED by the producing arm —
        # 4, not 10 — with the same population denominator and the same
        # text-band geometry.
        record = state.analysis_coverage["propositional_logic"]
        assert record["k"] == 4
        assert record["N"] == 12
        assert record["unit_ids"] == expected_ids[:4]
        assert record["bands_total"] == 3

    def test_fol_record_names_the_attempted_head_when_fallback_produces(self):
        state = _populated_state()
        expected_texts = _expected_selection_texts(state, 10)
        expected_ids = _expected_selection_ids(state, 10)
        result, captured = self._run_fol(state, _context(state))

        assert captured == expected_texts[:4]
        assert len(result["formulas"]) == 3
        record = state.analysis_coverage["fol_reasoning"]
        assert record["k"] == 4
        assert record["N"] == 12
        assert record["unit_ids"] == expected_ids[:4]
        assert record["bands_total"] == 3
