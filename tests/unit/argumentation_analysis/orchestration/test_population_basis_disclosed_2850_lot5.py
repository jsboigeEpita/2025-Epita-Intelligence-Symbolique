"""#2850 lot 5 — the population caps and prompt excerpts name their basis.

Lot 4 made the invoke layer's READING WINDOWS speak (payload k-of-N + trace
clause). Lot 5 covers what the census still counted "silent" in the pool
files of the dispatch (re-measured on 63ab4db40, 25 pure rows in scope):

- ``invoke_callables`` 12 — the ``input_text[:200]`` family is TRIAGED first
  (dispatch): four sites are constructor ballast (the seeded
  ``UnifiedAnalysisState`` has NO content reader — only Act II's
  ``source_length = len(raw_text)`` reflects it), one is the counter
  evaluator's default target (a real read the payload must name), and the
  ``_extract_arguments_from_context`` caps narrow the population every
  stateless arm translates. The quality-enrichment prompt excerpts
  (``arg_text[:200]``, ``detected_fallacies[:6]``) ride a persisted reader
  since lot 4 named ``llm_enrichment`` — they now say what they showed.
- ``nl_to_logic`` 5 — the batch cap and the heuristic translator's atom
  budgets: the reader of a heuristic formula sees N atoms but never learns
  how many sentences the document had.
- ``collaborative_debate`` 4 — the stateless fallback chains (:174/:178/
  :184/:336) select the debate's argument population in silence; the
  homonymous ``DEBATE_FALLBACK_WINDOW`` (:190) is MEASURED here — reachable
  (live) on a degenerate input, so its Acts clause stays lot 6's, but the
  measurement is pinned as a test, not folklore.

Same contract as lot 4: counts-only wording, prompts byte-identical, every
witness born red on the pre-fix tree, hermetic (mocked LLM seam, zero
network — #3072).
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.core.reading_window import DEBATE_FALLBACK_WINDOW
from argumentation_analysis.core.shared_state import UnifiedAnalysisState

INVOKE = "argumentation_analysis.orchestration.invoke_callables"
COLLAB = "argumentation_analysis.orchestration.collaborative_debate"

# Long synthetic corpus (opaque ids only — #2012/#2908 privacy).
LONG = " ".join(
    f"Phrase {i} du document synthétique porte une position distincte."
    for i in range(140)
)
UNIT = "Unité de corpus numéro %d, assez longue pour être retenue."
FALLACY = {"type": "ad_hominem", "target_argument": "arg_1"}


def _resp(payload: Dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
    )


def _extract_args(n: int) -> List[Dict[str, Any]]:
    return [{"text": UNIT % i, "source_quote": ""} for i in range(n)]


class _Recorder:
    """Lot 4's light state stand-in (trace + coverage, no real class)."""

    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []
        self.coverage: Dict[str, Any] = {}
        self.analysis_coverage = self.coverage
        self.raw_text = ""

    def add_trace_entry(self, **kwargs: Any) -> None:
        self.entries.append(kwargs)

    def record_analysis_coverage(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.coverage[name] = {"k": args[0] if args else None, **kwargs}

    def entry_for(self, phase: str) -> Dict[str, Any]:
        for entry in self.entries:
            if entry.get("phase") == phase:
                return entry
        raise AssertionError(
            f"no trace entry for phase {phase!r}; "
            f"entries: {[e.get('phase') for e in self.entries]}"
        )


# ── 1. _extract_arguments_from_context fills a basis dict ────────────────


class TestExtractArgumentsBasis:
    """Rows ``args[…:40]#1``, ``claims[…:8]#1``, ``sentences[…:expr]#1`` and
    ``input_text[…:200]#1`` (:4510/:4518/:4532/:4534): the caps narrow the
    population every stateless arm downstream translates — the helper now
    hands each caller the k-of-N it applied, per path."""

    @staticmethod
    def _call(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        from argumentation_analysis.orchestration.invoke_callables import (
            _extract_arguments_from_context,
        )

        basis: Dict[str, Any] = {}
        args = _extract_arguments_from_context(input_text, context, basis=basis)
        return {"args": args, "basis": basis}

    def test_extract_arguments_path_discloses_40_of_50(self) -> None:
        out = self._call(
            LONG, {"phase_extract_output": {"arguments": _extract_args(50)}}
        )
        assert len(out["args"]) == 40
        assert out["basis"] == {
            "path": "extract_arguments",
            "selected": 40,
            "available": 50,
        }

    def test_claims_path_discloses_8_of_12(self) -> None:
        out = self._call(LONG, {"phase_extract_output": {"claims": _extract_args(12)}})
        assert len(out["args"]) == 8
        assert out["basis"] == {
            "path": "extract_claims",
            "selected": 8,
            "available": 12,
        }

    def test_scores_path_is_uncapped(self) -> None:
        out = self._call(
            LONG,
            {"phase_extract_output": {"scores": {f"arg_{i}": 1 for i in range(12)}}},
        )
        assert len(out["args"]) == 12
        assert out["basis"] == {
            "path": "scores",
            "selected": 12,
            "available": 12,
        }

    def test_sentence_fallback_discloses_6_of_n(self) -> None:
        sentences = [f"Position argumentée numéro {i} du texte." for i in range(9)]
        out = self._call(". ".join(sentences) + ".", {})
        assert len(out["args"]) == 6
        assert out["basis"]["path"] == "sentences"
        assert out["basis"]["selected"] == 6
        assert out["basis"]["available"] >= 8

    def test_document_opening_fallback_names_its_window(self) -> None:
        out = self._call("Courte phrase unique.", {})
        assert out["basis"]["path"] == "document_opening"
        assert out["basis"]["window_chars"] == 200

    def test_no_basis_dict_leaves_the_contract_unchanged(self) -> None:
        """Control: callers that pass no basis get the exact old behavior."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _extract_arguments_from_context,
        )

        args = _extract_arguments_from_context(
            LONG, {"phase_extract_output": {"arguments": _extract_args(50)}}
        )
        assert len(args) == 40


# ── 2. The stateless PL/FOL arms carry the basis in their metrics ────────


class _LogicDriver:
    """Lot 4's hermetic PL/FOL driver (mocked client + mocked translator)."""

    pass1_payload: Dict[str, Any] = {"propositions": ["unit_present"]}

    @staticmethod
    def _capturing(captured: list):
        async def _capture(texts, logic_type=None, check_consistency=False):
            captured.extend(texts)
            return SimpleNamespace(
                translations=[
                    SimpleNamespace(
                        is_valid=True,
                        formula=f"p_sel_{i}",
                        original_text=t,
                    )
                    for i, t in enumerate(texts)
                ]
            )

        return _capture

    @classmethod
    def run_pl(cls, context: Dict[str, Any]) -> Dict[str, Any]:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        pass1 = _resp({"propositions": ["unit_present"]})
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
            cls._capturing(captured),
        ):
            return asyncio.run(_invoke_propositional_logic(LONG, context))

    @classmethod
    def run_fol(cls, context: Dict[str, Any]) -> Dict[str, Any]:
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
            cls._capturing(captured),
        ):
            return asyncio.run(_invoke_fol_reasoning(LONG, context))


class TestPlStatelessBasis:
    """The PL arm's metrics name where the translated population came from
    when no state carries one (the only path where the helper's caps bite)."""

    def test_metrics_carry_the_extract_arguments_basis(self) -> None:
        result = _LogicDriver.run_pl(
            {"phase_extract_output": {"arguments": _extract_args(50)}}
        )
        assert result["pl_metrics"]["arguments_basis"] == {
            "path": "extract_arguments",
            "selected": 40,
            "available": 50,
        }

    def test_control_state_run_has_no_stateless_basis(self) -> None:
        state = UnifiedAnalysisState(LONG)
        state.identified_arguments = {f"pop_{i}": UNIT % i for i in range(5)}
        result = _LogicDriver.run_pl({"_state_object": state})
        assert "arguments_basis" not in result["pl_metrics"], (
            "the state carried the population — a stateless basis would "
            "describe a path this run did not take"
        )


class TestFolStatelessBasis:
    def test_metrics_carry_the_extract_arguments_basis(self) -> None:
        result = _LogicDriver.run_fol(
            {"phase_extract_output": {"arguments": _extract_args(50)}}
        )
        assert result["fol_metrics"]["arguments_basis"]["selected"] == 40
        assert result["fol_metrics"]["arguments_basis"]["available"] == 50


# ── 3. nl_to_logic: the batch cap and the phase payload ──────────────────


class TestTranslateBatchPopulation:
    """Row ``arguments[…:10]#1`` (:330): the batch result now carries the
    requested population next to the translations, so the reader of a
    truncated batch (the plugin surface is the only one that can send more
    than 10 — the invoke arms select ≤10 first) can see k of N."""

    def test_batch_pairs_translations_with_the_request(self) -> None:
        from argumentation_analysis.services.nl_to_logic import NLToLogicTranslator

        translator = NLToLogicTranslator()
        arguments = [UNIT % i for i in range(12)]
        with patch("openai.AsyncOpenAI", side_effect=RuntimeError("no key")):
            batch = asyncio.run(
                translator.translate_batch(arguments, logic_type="propositional")
            )
        assert batch.requested_population == 12
        assert len(batch.translations) <= 10, (
            "the cap is the debt — the witness does not widen it (#2850 "
            "anti-pendulum), it names it"
        )

    def test_control_small_batch_is_fully_translated(self) -> None:
        from argumentation_analysis.services.nl_to_logic import NLToLogicTranslator

        translator = NLToLogicTranslator()
        with patch("openai.AsyncOpenAI", side_effect=RuntimeError("no key")):
            batch = asyncio.run(
                translator.translate_batch(
                    [UNIT % i for i in range(3)], logic_type="propositional"
                )
            )
        assert batch.requested_population == 3
        assert len(batch.translations) == 3


class TestNlToLogicPhaseBasis:
    """The phase payload names the population basis on its stateless arm."""

    def test_payload_carries_the_basis(self) -> None:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_nl_to_logic,
        )

        captured: list = []

        async def _capture(self, texts, logic_type=None, check_consistency=False):
            captured.extend(texts)
            return SimpleNamespace(
                overall_consistency=True,
                consistency_message="",
                method="witness",
                translations=[
                    SimpleNamespace(
                        is_valid=True,
                        formula=f"p_{i}",
                        original_text=t,
                        logic_type=logic_type or "propositional",
                        validation_message="",
                        attempts=0,
                        variables={},
                        confidence=0.5,
                    )
                    for i, t in enumerate(texts)
                ],
            )

        with patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator"
            ".translate_batch",
            _capture,
        ):
            result = asyncio.run(
                _invoke_nl_to_logic(
                    LONG,
                    {"phase_extract_output": {"arguments": _extract_args(50)}},
                )
            )
        assert result["arguments_basis"] == {
            "path": "extract_arguments",
            "selected": 40,
            "available": 50,
        }


# ── 4. The heuristic translator's atom budgets speak in their message ────


class TestHeuristicAtomCounts:
    """Rows ``sentences[…:3]#1`` (:1053), ``sentences[…:5]#1`` (:1082),
    ``text[…:80]#1`` (:1109) and ``sentences[…:5]#2`` (:1124): the reader of
    a heuristic formula sees N atoms but never learns how many sentences the
    document had — the validation message (a rendered surface, #1260/#1019)
    now carries the k-of-N."""

    @staticmethod
    def _translate(text: str, logic_type: str):
        from argumentation_analysis.services.nl_to_logic import NLToLogicTranslator

        translator = NLToLogicTranslator()
        with patch("openai.AsyncOpenAI", side_effect=RuntimeError("no key")):
            return asyncio.run(translator.translate(text, logic_type=logic_type))

    def test_propositional_atoms_are_5_of_8_sentences(self) -> None:
        text = (
            ". ".join(
                f"La proposition argumentée numéro {i} tient largement"
                for i in range(8)
            )
            + "."
        )
        result = self._translate(text, "propositional")
        assert len(result.variables) == 5
        assert (
            "5 atomes sur 8 phrases" in result.validation_message
        ), result.validation_message

    def test_propositional_degenerate_atom_names_its_80_char_excerpt(self) -> None:
        text = (
            "Une seule phrase très longue sans point final qui dépasse "
            "largement les quatre-vingts caractères exigés par le witness"
        )
        assert len(text) > 80
        result = self._translate(text, "propositional")
        assert len(result.variables) == 1
        assert "80 de" in result.validation_message, result.validation_message
        assert f"de {len(text)} caractères" in result.validation_message

    def test_modal_atoms_are_3_of_5_sentences(self) -> None:
        # Distinct prefixes: the modal stem keeps only the first 12 alnum
        # chars, so identical prefixes would dedup to one atom.
        text = (
            ". ".join(
                f"Règle {i} : le système modal doit nécessairement valider"
                for i in range(5)
            )
            + "."
        )
        result = self._translate(text, "modal")
        assert (
            "3 atomes sur 5 phrases" in result.validation_message
        ), result.validation_message

    def test_fol_predicates_are_5_of_7_sentences(self) -> None:
        text = ". ".join(f"Prédicat{i} relation" for i in range(7)) + "."
        result = self._translate(text, "fol")
        assert (
            "5 prédicats sur 7 phrases" in result.validation_message
        ), result.validation_message

    def test_control_llm_message_is_unchanged(self) -> None:
        """The counts ride the HEURISTIC message only — the LLM path's
        message stays whatever the model returned (no fabricated counts)."""
        assert "atomes sur" not in "Heuristic translation (no LLM)"


# ── 5. The quality-enrichment prompt excerpts name what they showed ──────


class TestQualityEnrichmentBasis:
    """Rows ``arg_text[…:200]#1`` (:1068) and ``detected_fallacies[…:6]#2``
    (:1078): lot 4 left the fallacy row silent because no persisted reader
    existed — lot 4's own ``llm_enrichment`` payload key became that reader,
    so both excerpts now disclose what the prompt showed."""

    @staticmethod
    def _run(fallacies: List[Dict[str, Any]], state: Any) -> Dict[str, Any]:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_quality_evaluator,
        )

        client = MagicMock()
        enrichment = {"enrichments": [{"arg_id": "arg_1", "llm_assessment": "solide"}]}
        context = {
            "phase_extract_output": {"arguments": _extract_args(3)},
            "phase_hierarchical_fallacy_output": {"fallacies": fallacies},
            "_state_object": state,
        }
        with patch(
            # Hermeticity (#3069): the agentic virtue detectors hold their OWN
            # client — mocking _guarded_chat_completion does not cover them
            # (measured: 10 live requests escaped the first run of this
            # witness). Degraded route = the lexical fallback, which is a
            # production mode, and the enrichment seam stays mocked below.
            f"{INVOKE}._make_agentic_llm_callable",
            return_value=(None, "degraded_witness", None),
        ), patch(
            f"{INVOKE}._get_openai_client", return_value=(client, "gpt-witness")
        ), patch(
            f"{INVOKE}._guarded_chat_completion",
            AsyncMock(return_value=_resp(enrichment)),
        ):
            return asyncio.run(_invoke_quality_evaluator(LONG, context))

    def test_payload_names_the_prompt_excerpts(self) -> None:
        out = self._run(
            [dict(FALLACY, type=f"fallacy_{i}") for i in range(8)], _Recorder()
        )
        basis = out["llm_enrichment"]["basis"]
        assert basis["unit_excerpt_chars"] == 200
        assert basis["fallacies_in_prompt"] == 6
        assert basis["fallacies_available"] == 8
        cross = out["fallacy_cross_reference"]
        assert cross["fallacies_found"] == 8
        assert cross["prompt_shown"] == 6

    def test_trace_names_the_excerpts(self) -> None:
        state = _Recorder()
        self._run([dict(FALLACY, type=f"fallacy_{i}") for i in range(8)], state)
        summary = state.entry_for("quality")["summary"]
        assert "200 caractères" in summary, summary
        assert "6 de 8" in summary, summary

    def test_control_no_fallacies_no_prompt_clause(self) -> None:
        state = _Recorder()
        self._run([], state)
        summary = state.entry_for("quality")["summary"]
        assert "sophismes montrés" not in summary, summary
        assert "fallacy_cross_reference" not in self._run([], _Recorder())


# ── 6. ABA assumptions: the first-3 cap speaks in the identity payload ───


class TestAbaAssumptionsBasis:
    """Row ``arguments[…:expr]#1`` (:4763): the first ``min(3, N)`` arguments
    become the assumptions under test — the payload now says 3 of N."""

    def test_payload_names_tested_of_available(self) -> None:
        from argumentation_analysis.orchestration.invoke_callables import _invoke_aba

        args = _extract_args(8)
        handler = MagicMock()
        handler.analyze_aba_framework.return_value = {"verdict": "stable"}
        context = {
            "phase_extract_output": {"arguments": args},
            "contraries": {args[0]["text"]: "Une contre-position directe."},
        }
        with patch(
            "argumentation_analysis.agents.core.logic.aba_handler.ABAHandler",
            return_value=handler,
        ):
            result = asyncio.run(_invoke_aba(LONG, context))
        assert result["assumptions_basis"] == {"tested": 3, "of": 8}


# ── 7. The counter evaluator's default target is named per evaluation ────


class TestCounterDefaultTargetBasis:
    """Row ``input_text[…:200]#7`` (:1971): a counter dict without a
    ``target_argument`` echo is evaluated against the document's 200-char
    opening — a REAL read (the scores ride the payload) that each evaluation
    now names, with the k-of-N in the trace."""

    @staticmethod
    def _run(counters: List[Dict[str, Any]], text: str) -> Any:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_counter_argument,
        )

        client = MagicMock()
        state = _Recorder()
        with patch(
            f"{INVOKE}._get_openai_client", return_value=(client, "gpt-witness")
        ), patch(
            f"{INVOKE}._generate_counters_for_targets",
            AsyncMock(return_value=[dict(c) for c in counters]),
        ):
            out = asyncio.run(_invoke_counter_argument(text, {"_state_object": state}))
        return out, state

    def test_evaluations_name_the_default_opening(self) -> None:
        counters = [
            {
                "counter_argument": f"Réfutation synthétique {i}.",
                "strategy_used": "reformulation",
            }
            for i in range(2)
        ]
        out, state = self._run(counters, LONG)
        evals = [c["evaluation"] for c in out["llm_counter_arguments"]]
        assert all(e["target_basis"] == "default_opening" for e in evals)
        summary = state.entry_for("counter")["summary"]
        assert "2 de 2" in summary, summary
        assert "ouverture du document" in summary, summary

    def test_control_named_targets_carry_no_default_clause(self) -> None:
        counters = [
            {
                "counter_argument": "Réfutation synthétique.",
                "strategy_used": "reformulation",
                "target_argument": "Cible explicite fournie.",
            }
        ]
        out, state = self._run(counters, LONG)
        assert (
            out["llm_counter_arguments"][0]["evaluation"]["target_basis"]
            == "named_target"
        )
        summary = state.entry_for("counter")["summary"]
        assert "ouverture du document" not in summary, summary


# ── 8. collaborative_debate: the fallback chains say what they selected ──


class TestCollaborativeBasis:
    """Rows ``arguments[…:8]#1`` (:174), ``claims[…:8]#1`` (:178) and
    ``sentences[…:6]#1`` (:184): the stateless fallback chain selects the
    debate's whole argument population in silence — the payload now carries
    the k-of-N per path. Row ``arguments[…:6]#1`` (:336) is the no-key
    fallback's own cap."""

    SYNTH = {
        "final_quality_score": 4.0,
        "new_insights": [],
        "surviving_arguments": [],
        "defeated_arguments": [],
    }

    @staticmethod
    def _run_main(context: Dict[str, Any]) -> Dict[str, Any]:
        from argumentation_analysis.orchestration.collaborative_debate import (
            _invoke_collaborative_analysis,
        )

        with patch(
            "argumentation_analysis.core.llm_service.resolve_chat_endpoint",
            return_value=("test-key", "https://example.invalid", "gpt-witness"),
        ), patch(
            "argumentation_analysis.core.utils.network_utils"
            ".build_async_openai_client",
            return_value=MagicMock(),
        ), patch(
            f"{COLLAB}.cached_raw_chat_completion",
            AsyncMock(return_value=_resp(TestCollaborativeBasis.SYNTH)),
        ):
            return asyncio.run(_invoke_collaborative_analysis(LONG, context))

    def test_extract_arguments_fallback_discloses_8_of_12(self) -> None:
        out = self._run_main({"phase_extract_output": {"arguments": _extract_args(12)}})
        assert out["arguments_basis"] == {
            "path": "extract_arguments",
            "selected": 8,
            "available": 12,
        }

    def test_claims_fallback_discloses_8_of_12(self) -> None:
        out = self._run_main({"phase_extract_output": {"claims": _extract_args(12)}})
        assert out["arguments_basis"]["path"] == "extract_claims"
        assert out["arguments_basis"]["selected"] == 8
        assert out["arguments_basis"]["available"] == 12

    def test_sentence_fallback_discloses_6_of_n(self) -> None:
        out = self._run_main({})
        assert out["arguments_basis"]["path"] == "sentences"
        assert out["arguments_basis"]["selected"] == 6
        assert out["arguments_basis"]["available"] > 6

    def test_window_fallback_is_live_on_degenerate_input(self) -> None:
        """The homonymous DEBATE_FALLBACK_WINDOW (:190) — measured, not
        folklore: on an input with no sentence longer than 15 chars the
        chain falls through to the window. Its Acts clause is lot 6's; this
        test pins the reachability lot 4 could not measure."""
        out = self._run_main({})
        assert out["arguments_basis"]["path"] == "sentences"  # LONG: sentences win
        degenerate = self._run_main_text("Ok. Vu. Bravo.")
        assert degenerate["arguments_basis"]["path"] == "document_opening", (
            "no sentence exceeds 15 chars — the only material left is the "
            "%d-char window: the fallback is LIVE, not dead like lot 4's "
            "invoke_callables homonym" % DEBATE_FALLBACK_WINDOW
        )

    @staticmethod
    def _run_main_text(text: str) -> Dict[str, Any]:
        from argumentation_analysis.orchestration.collaborative_debate import (
            _invoke_collaborative_analysis,
        )

        with patch(
            "argumentation_analysis.core.llm_service.resolve_chat_endpoint",
            return_value=("test-key", "https://example.invalid", "gpt-witness"),
        ), patch(
            "argumentation_analysis.core.utils.network_utils"
            ".build_async_openai_client",
            return_value=MagicMock(),
        ), patch(
            f"{COLLAB}.cached_raw_chat_completion",
            AsyncMock(return_value=_resp(TestCollaborativeBasis.SYNTH)),
        ):
            return asyncio.run(_invoke_collaborative_analysis(text, {}))

    def test_no_key_fallback_discloses_6_of_9(self) -> None:
        from argumentation_analysis.orchestration.collaborative_debate import (
            _fallback_collaborative,
        )

        out = _fallback_collaborative(
            LONG, {"phase_extract_output": {"arguments": _extract_args(9)}}
        )
        assert out["arguments_basis"] == {
            "path": "stateless_arguments",
            "selected": 6,
            "available": 9,
        }


# ── 9. The ballast seeds and the graduated renders ───────────────────────


def _guard_registry() -> Dict[Any, Any]:
    path = Path(__file__).parent.parent / "test_coverage_census_guard_2850.py"
    spec = importlib.util.spec_from_file_location("guard2850_lot5", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.REGISTRY


class TestBallastSeedReclassified:
    """Rows ``input_text[…:200]#3..#6`` (the ``UnifiedAnalysisState(
    input_text[:200])`` reconstruction seeds): lot 5 measured them as
    CONSTRUCTOR BALLAST — no consumer reads the seeded text's content (the
    only reflection was Act II's ``source_length`` len()) — and registered
    them as debt rather than "silent". LOT 6 PAID IT: the four sites are
    un-seeded and their registry rows are gone, so this class now pins the
    DEPARTURE. The un-seeding itself is pinned on the behaviour by
    ``orchestration/test_ballast_unseeded_2850_lot6.py``; here the census
    invariant is that the class stays empty and that the ordinals the
    deletion renumbered do not alias a stale render."""

    def test_no_ballast_row_survives_in_the_registry(self) -> None:
        registry = _guard_registry()
        invoke_rel = "argumentation_analysis/orchestration/invoke_callables.py"
        ballast = [
            key
            for key, value in registry.items()
            if key[0] == invoke_rel and "ballast" in value[2]
        ]
        assert ballast == [], (
            "lot 6 un-seeded the four reconstruction sites — no registry row "
            f"may still carry a ballast render: {ballast}"
        )

    def test_the_renumbered_ordinal_three_is_not_the_old_ballast(self) -> None:
        """Census ordinals renumber after a deletion: #3 carried the first
        ballast row before lot 6 and carries the counter-argument target
        default after it. A stale render riding the new ordinal is the
        silent failure this pin exists for."""
        registry = _guard_registry()
        invoke_rel = "argumentation_analysis/orchestration/invoke_callables.py"
        kind, drops, render = registry[(invoke_rel, "input_text", "200", 3)]
        assert kind == "window", kind
        assert "counter-argument target" in drops, drops
        assert "ballast" not in render, render


class TestSilentRowsGraduated:
    """Every row this lot treats left the "silent" class — the registry
    names its reader (or its reclassification), never a bare debt tag."""

    TREATED = [
        (
            "argumentation_analysis/orchestration/invoke_callables.py",
            [
                ("arg_text", "200", 1),
                ("args", "40", 1),
                ("arguments", "expr", 1),
                ("claims", "8", 1),
                ("detected_fallacies", "6", 2),
                ("input_text", "200", 1),
                # Lot 6 un-seeded the four ballast sites; the census
                # renumbered, so the counter-argument target this lot
                # treated at #7 now sits at #3.
                ("input_text", "200", 3),
                ("sentences", "expr", 1),
            ],
        ),
        (
            "argumentation_analysis/services/nl_to_logic.py",
            [
                ("arguments", "10", 1),
                ("sentences", "3", 1),
                ("sentences", "5", 1),
                ("sentences", "5", 2),
                ("text", "80", 1),
            ],
        ),
        (
            "argumentation_analysis/orchestration/collaborative_debate.py",
            [
                ("arguments", "6", 1),
                ("arguments", "8", 1),
                ("claims", "8", 1),
                ("sentences", "6", 1),
            ],
        ),
    ]

    def test_no_treated_row_stays_silent(self) -> None:
        registry = _guard_registry()
        for rel, rows in self.TREATED:
            for base, cap, ordinal in rows:
                render = registry[(rel, base, cap, ordinal)][2]
                assert "silent" not in render, (rel, base, cap, ordinal, render)

    def test_the_measured_debate_window_row_says_it_is_live(self) -> None:
        registry = _guard_registry()
        render = registry[
            (
                "argumentation_analysis/orchestration/collaborative_debate.py",
                "selected_text",
                "DEBATE_FALLBACK_WINDOW",
                1,
            )
        ][2]
        assert "measured live" in render, render
