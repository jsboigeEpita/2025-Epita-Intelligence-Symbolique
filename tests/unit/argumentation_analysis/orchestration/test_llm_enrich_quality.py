"""Tests for _llm_enrich_quality (#208-F, #290).

Verifies LLM enrichment pass in the quality evaluator pipeline phase,
including fallacy context integration and per-argument llm_assessment.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestLlmEnrichQuality:
    """Tests for _llm_enrich_quality function."""

    async def test_returns_none_when_no_api_key(self):
        """LLM enrichment returns None gracefully when no API key is available.

        Patch _get_openai_client to return its documented no-key sentinel
        ``(None, "")`` rather than clearing os.environ: on CI (which provisions
        a real key via secrets) the env-clear did not prevent a live client, so
        the enrichment made a real LLM call instead of the no-key short-circuit.
        """
        from argumentation_analysis.orchestration.unified_pipeline import (
            _llm_enrich_quality,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(None, ""),
        ):
            result = await _llm_enrich_quality(
                {"arg_1": {"note_finale": 5.0, "scores_par_vertu": {"clarity": 6.0}}},
                [{"text": "Some argument"}],
            )
        assert result is None

    async def test_returns_none_when_empty_heuristic_results(self):
        """LLM enrichment returns None when no valid heuristic results to summarize."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _llm_enrich_quality,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(MagicMock(), "gpt-5-mini"),
        ):
            result = await _llm_enrich_quality({}, [])
        assert result is None

    async def test_returns_none_when_heuristic_values_not_dicts(self):
        """LLM enrichment skips non-dict heuristic entries."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _llm_enrich_quality,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(MagicMock(), "gpt-5-mini"),
        ):
            result = await _llm_enrich_quality(
                {"arg_1": "not a dict", "arg_2": 42},
                [{"text": "arg"}],
            )
        assert result is None

    async def test_successful_llm_enrichment(self):
        """LLM enrichment returns parsed JSON when LLM responds correctly."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _llm_enrich_quality,
        )

        llm_response = json.dumps(
            {
                "enrichments": [
                    {
                        "arg_id": "arg_1",
                        "implicit_assumptions": ["The economy is stable"],
                        "reasoning_assessment": "moderate",
                        "evidence_quality": "weak",
                        "improvement_suggestion": "Add empirical data",
                    }
                ]
            }
        )

        mock_message = MagicMock()
        mock_message.content = llm_response
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(mock_client, "gpt-5-mini"),
        ):
            result = await _llm_enrich_quality(
                {
                    "arg_1": {
                        "note_finale": 5.0,
                        "scores_par_vertu": {"clarity": 6.0, "coherence": 4.0},
                    }
                },
                [{"text": "The economy grows because of tax cuts"}],
            )

        assert result is not None
        assert "enrichments" in result
        assert result["enrichments"][0]["arg_id"] == "arg_1"
        assert result["enrichments"][0]["reasoning_assessment"] == "moderate"

    async def test_llm_enrichment_handles_markdown_json(self):
        """LLM enrichment correctly strips ```json fences from response."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _llm_enrich_quality,
        )

        llm_response = '```json\n{"enrichments": [{"arg_id": "arg_1"}]}\n```'

        mock_message = MagicMock()
        mock_message.content = llm_response
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(mock_client, "gpt-5-mini"),
        ):
            result = await _llm_enrich_quality(
                {"arg_1": {"note_finale": 7.0, "scores_par_vertu": {"clarity": 8.0}}},
                [{"text": "Strong argument with evidence"}],
            )

        assert result is not None
        assert result["enrichments"][0]["arg_id"] == "arg_1"

    async def test_llm_enrichment_returns_none_on_exception(self):
        """LLM enrichment returns None gracefully when LLM call throws."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _llm_enrich_quality,
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API timeout")
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(mock_client, "gpt-5-mini"),
        ):
            result = await _llm_enrich_quality(
                {"arg_1": {"note_finale": 5.0, "scores_par_vertu": {"clarity": 6.0}}},
                [{"text": "Some argument text"}],
            )

        assert result is None

    async def test_llm_enrichment_covers_the_whole_selection(self):
        """#2959 — every evaluated unit goes to the LLM. The former [:4] cap
        predates the budget-bounded stratified selection (#2850: raw_args IS
        the selection, ≤8 by construction) and silently left half of it
        without a narrative — an empty llm_assessment read as "the model had
        nothing to say" about a unit it was never shown."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _llm_enrich_quality,
        )

        mock_message = MagicMock()
        mock_message.content = '{"enrichments": []}'
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        heuristic = {
            f"arg_{i}": {
                "note_finale": float(i),
                "scores_par_vertu": {"clarity": float(i)},
            }
            for i in range(1, 8)
        }
        raw_args = [
            {"unit_id": f"arg_{i}", "text": f"Argument {i}"} for i in range(1, 8)
        ]

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(mock_client, "gpt-5-mini"),
        ):
            await _llm_enrich_quality(heuristic, raw_args)

        call_args = mock_client.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][1]["content"]
        # Count [arg_N] occurrences — all seven, none dropped silently
        import re

        arg_refs = re.findall(r"\[arg_\d+\]", user_msg)
        assert len(arg_refs) == 7

    async def test_llm_enrichment_uses_get_openai_client(self):
        """LLM enrichment uses the shared _get_openai_client helper."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _llm_enrich_quality,
        )

        mock_message = MagicMock()
        mock_message.content = '{"enrichments": []}'
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(mock_client, "test-model"),
        ) as mock_get:
            await _llm_enrich_quality(
                {"arg_1": {"note_finale": 5.0, "scores_par_vertu": {"clarity": 6.0}}},
                [{"text": "Test"}],
            )

        mock_get.assert_called_once()
        # Verify the model from _get_openai_client is used
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "test-model"


class TestInvokeQualityWithLlmEnrichment:
    """Tests for _invoke_quality_evaluator with LLM enrichment integration."""

    async def test_quality_output_includes_llm_enrichment_when_available(self):
        """Quality evaluator output includes llm_enrichment key when LLM succeeds."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_quality_evaluator,
        )

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {
            "note_finale": 6.5,
            "scores_par_vertu": {"clarity": 7.0, "coherence": 6.0},
        }

        enrichment_data = {
            "enrichments": [{"arg_id": "arg_1", "reasoning_assessment": "strong"}]
        }

        with patch(
            "argumentation_analysis.agents.core.quality.quality_evaluator.ArgumentQualityEvaluator",
            return_value=mock_evaluator,
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._llm_enrich_quality",
            return_value=enrichment_data,
        ):
            context = {
                "phase_extract_output": {
                    "arguments": [{"text": "A clear argument with evidence"}]
                }
            }
            result = await _invoke_quality_evaluator("Test", context)

        assert "llm_enrichment" in result
        assert result["llm_enrichment"] == enrichment_data

    async def test_quality_output_omits_llm_enrichment_when_unavailable(self):
        """Quality evaluator output has no llm_enrichment key when LLM returns None."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_quality_evaluator,
        )

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {
            "note_finale": 6.5,
            "scores_par_vertu": {"clarity": 7.0, "coherence": 6.0},
        }

        with patch(
            "argumentation_analysis.agents.core.quality.quality_evaluator.ArgumentQualityEvaluator",
            return_value=mock_evaluator,
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._llm_enrich_quality",
            return_value=None,
        ):
            context = {
                "phase_extract_output": {
                    "arguments": [{"text": "A clear argument with evidence"}]
                }
            }
            result = await _invoke_quality_evaluator("Test", context)

        assert "llm_enrichment" not in result
        assert "per_argument_scores" in result


class TestLlmEnrichQualityWithFallacies:
    """Tests for #290 — fallacy context in LLM enrichment."""

    async def test_fallacy_context_included_in_llm_prompt(self):
        """When fallacies are detected, they appear in the LLM prompt."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _llm_enrich_quality,
        )

        mock_message = MagicMock()
        mock_message.content = '{"enrichments": []}'
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        fallacies = [
            {"type": "ad_hominem", "target_argument": "Argument about economy"},
            {"type": "appeal_to_authority", "target_argument": "Elon Musk said"},
        ]

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(mock_client, "gpt-5-mini"),
        ):
            await _llm_enrich_quality(
                {"arg_1": {"note_finale": 5.0, "scores_par_vertu": {"clarity": 6.0}}},
                [{"text": "Some argument"}],
                detected_fallacies=fallacies,
            )

        call_args = mock_client.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][1]["content"]
        assert "DETECTED FALLACIES" in user_msg
        assert "ad_hominem" in user_msg
        assert "appeal_to_authority" in user_msg

    async def test_no_fallacy_context_when_none(self):
        """When no fallacies, prompt has no fallacy section."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _llm_enrich_quality,
        )

        mock_message = MagicMock()
        mock_message.content = '{"enrichments": []}'
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(mock_client, "gpt-5-mini"),
        ):
            await _llm_enrich_quality(
                {"arg_1": {"note_finale": 5.0, "scores_par_vertu": {"clarity": 6.0}}},
                [{"text": "Some argument"}],
                detected_fallacies=None,
            )

        call_args = mock_client.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][1]["content"]
        assert "DETECTED FALLACIES" not in user_msg

    async def test_llm_assessment_merged_into_per_arg_scores(self):
        """LLM enrichment merges llm_assessment into per_argument_scores."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_quality_evaluator,
        )

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {
            "note_finale": 6.0,
            "scores_par_vertu": {"clarity": 7.0, "coherence": 5.0},
        }

        enrichment_data = {
            "enrichments": [
                {
                    "arg_id": "arg_1",
                    "reasoning_assessment": "moderate",
                    "evidence_quality": "weak",
                    "bias_indicators": ["confirmation bias"],
                    "llm_assessment": "This argument relies on unsubstantiated claims.",
                }
            ]
        }

        with patch(
            "argumentation_analysis.agents.core.quality.quality_evaluator.ArgumentQualityEvaluator",
            return_value=mock_evaluator,
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._llm_enrich_quality",
            return_value=enrichment_data,
        ):
            context = {
                "phase_extract_output": {
                    "arguments": [{"text": "An argument about economy policy"}]
                }
            }
            result = await _invoke_quality_evaluator("Test", context)

        arg1 = result["per_argument_scores"]["arg_1"]
        assert (
            arg1["llm_assessment"] == "This argument relies on unsubstantiated claims."
        )
        assert arg1["reasoning_assessment"] == "moderate"
        assert arg1["evidence_quality"] == "weak"
        assert arg1["bias_indicators"] == ["confirmation bias"]

    async def test_llm_assessment_not_merged_when_no_enrichment(self):
        """Without LLM enrichment, per_argument_scores have no llm_assessment."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_quality_evaluator,
        )

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {
            "note_finale": 6.0,
            "scores_par_vertu": {"clarity": 7.0},
        }

        with patch(
            "argumentation_analysis.agents.core.quality.quality_evaluator.ArgumentQualityEvaluator",
            return_value=mock_evaluator,
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._llm_enrich_quality",
            return_value=None,
        ):
            context = {
                "phase_extract_output": {"arguments": [{"text": "A simple argument"}]}
            }
            result = await _invoke_quality_evaluator("Test", context)

        arg1 = result["per_argument_scores"]["arg_1"]
        assert "llm_assessment" not in arg1


class TestLlmEnrichMatchesById2959:
    """#2959 — the enrichment matches units BY ID, never by position.

    #2850's stratified selection keys heuristic results by each unit's state
    id, so ids and positions stopped coinciding: parsing ``arg_16`` as
    position 16 sent another unit's text — or none at all — to the LLM
    (measured on doc_A: every enriched unit read ``Text: ""``). These
    witnesses assert on the PROMPT the fake client receives, not on the
    returned narrative.
    """

    @staticmethod
    def _client() -> AsyncMock:
        mock_message = MagicMock()
        mock_message.content = '{"enrichments": []}'
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        return mock_client

    @staticmethod
    def _block(user_msg: str, uid: str) -> str:
        """The unit's own prompt block: from its ``[uid]`` marker to the next."""
        part = user_msg.split(f"[{uid}] score=", 1)[1]
        return part.split("[arg_", 1)[0]

    @staticmethod
    def _scores() -> dict:
        return {"note_finale": 5.0, "scores_par_vertu": {"clarity": 5.0}}

    async def _prompt(self, heuristic: dict, raw_args: list) -> str:
        from argumentation_analysis.orchestration.unified_pipeline import (
            _llm_enrich_quality,
        )

        client = self._client()
        with patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(client, "gpt-5-mini"),
        ):
            await _llm_enrich_quality(heuristic, raw_args)
        call_args = client.chat.completions.create.call_args
        return call_args.kwargs["messages"][1]["content"]

    async def test_out_of_range_ids_carry_their_own_text(self):
        """Ids outside arg_1..n — the measured doc_A shape (arg_16, arg_23…)
        where the positional read fell off the selection and sent ``Text: ""``:
        each unit's OWN text must reach the prompt."""
        ids_and_texts = [
            ("arg_16", "TEXT_OF_UNIT_SIXTEEN"),
            ("arg_23", "TEXT_OF_UNIT_TWENTY_THREE"),
            ("arg_30", "TEXT_OF_UNIT_THIRTY"),
            ("arg_45", "TEXT_OF_UNIT_FORTY_FIVE"),
        ]
        heuristic = {uid: self._scores() for uid, _ in ids_and_texts}
        raw_args = [{"unit_id": uid, "text": text} for uid, text in ids_and_texts]
        user_msg = await self._prompt(heuristic, raw_args)
        for uid, text in ids_and_texts:
            assert f"[{uid}] score=" in user_msg
            assert text in self._block(user_msg, uid)

    async def test_id_position_divergence_shows_no_foreign_text(self):
        """arg_2 sitting at position 3: the positional read would show
        position 2's text — the id's OWN text must be there instead, and the
        foreign one absent from its block."""
        heuristic = {"arg_2": self._scores()}
        raw_args = [
            {"unit_id": "arg_9", "text": "FOREIGN_TEXT_POSITION_ONE"},
            {"unit_id": "arg_7", "text": "FOREIGN_TEXT_POSITION_TWO"},
            {"unit_id": "arg_2", "text": "OWN_TEXT_OF_ARG_TWO"},
        ]
        user_msg = await self._prompt(heuristic, raw_args)
        block = self._block(user_msg, "arg_2")
        assert "OWN_TEXT_OF_ARG_TWO" in block
        assert "FOREIGN_TEXT_POSITION_TWO" not in block

    async def test_unknown_id_is_skipped_not_mismatched(self):
        """An id with no unit in the selection yields NO block at all — the
        old code fabricated one (``Text: ""``) from a positional read."""
        heuristic = {"arg_40": self._scores(), "arg_16": self._scores()}
        raw_args = [{"unit_id": "arg_16", "text": "TEXT_OF_UNIT_SIXTEEN"}]
        user_msg = await self._prompt(heuristic, raw_args)
        assert "[arg_40]" not in user_msg
        assert "[arg_16] score=" in user_msg

    async def test_stateless_units_still_mint_positional_ids(self):
        """The stateless fallback (units carrying no unit_id) still answers
        to arg_{i+1} — same minting as _eval_unit, so the id-based matching
        follows it there instead of breaking the fallback lane."""
        heuristic = {"arg_1": self._scores()}
        raw_args = [{"text": "STATELESS_TEXT"}]
        user_msg = await self._prompt(heuristic, raw_args)
        assert "STATELESS_TEXT" in self._block(user_msg, "arg_1")


class TestQualityStateWriterLlmAssessment:
    """Tests for #290 — llm_assessment persisted in state."""

    def test_add_quality_score_with_llm_assessment(self):
        """add_quality_score stores llm_assessment when provided."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text="test")
        state.add_quality_score(
            "arg_1",
            {"clarity": 7.0},
            7.0,
            llm_assessment="Strong argument with good evidence.",
        )
        entry = state.argument_quality_scores["arg_1"]
        assert entry["llm_assessment"] == "Strong argument with good evidence."
        assert entry["overall"] == 7.0

    def test_add_quality_score_without_llm_assessment(self):
        """add_quality_score omits llm_assessment when not provided."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text="test")
        state.add_quality_score("arg_1", {"clarity": 7.0}, 7.0)
        entry = state.argument_quality_scores["arg_1"]
        assert "llm_assessment" not in entry

    async def test_state_writer_passes_llm_assessment(self):
        """_write_quality_to_state passes llm_assessment from output to state."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_quality_to_state,
        )
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text="test")
        output = {
            "per_argument_scores": {
                "arg_1": {
                    "note_finale": 6.5,
                    "scores_par_vertu": {"clarity": 7.0},
                    "llm_assessment": "Moderately strong reasoning.",
                }
            }
        }
        _write_quality_to_state(output, state, {})
        entry = state.argument_quality_scores["arg_1"]
        assert entry["llm_assessment"] == "Moderately strong reasoning."
        assert entry["overall"] == 6.5

    async def test_state_writer_no_llm_assessment_when_absent(self):
        """_write_quality_to_state does not add llm_assessment if not in output."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_quality_to_state,
        )
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text="test")
        output = {
            "per_argument_scores": {
                "arg_1": {
                    "note_finale": 5.0,
                    "scores_par_vertu": {"clarity": 5.0},
                }
            }
        }
        _write_quality_to_state(output, state, {})
        entry = state.argument_quality_scores["arg_1"]
        assert "llm_assessment" not in entry
