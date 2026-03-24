"""Tests for _llm_enrich_quality (#208-F).

Verifies LLM enrichment pass in the quality evaluator pipeline phase.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestLlmEnrichQuality:
    """Tests for _llm_enrich_quality function."""

    async def test_returns_none_when_no_api_key(self):
        """LLM enrichment returns None gracefully when OPENAI_API_KEY is absent."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _llm_enrich_quality,
        )

        with patch.dict("os.environ", {}, clear=True):
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
            "argumentation_analysis.orchestration.unified_pipeline._get_openai_client",
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
            "argumentation_analysis.orchestration.unified_pipeline._get_openai_client",
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

        llm_response = json.dumps({
            "enrichments": [{
                "arg_id": "arg_1",
                "implicit_assumptions": ["The economy is stable"],
                "reasoning_assessment": "moderate",
                "evidence_quality": "weak",
                "improvement_suggestion": "Add empirical data",
            }]
        })

        mock_message = MagicMock()
        mock_message.content = llm_response
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline._get_openai_client",
            return_value=(mock_client, "gpt-5-mini"),
        ):
            result = await _llm_enrich_quality(
                {"arg_1": {
                    "note_finale": 5.0,
                    "scores_par_vertu": {"clarity": 6.0, "coherence": 4.0},
                }},
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
            "argumentation_analysis.orchestration.unified_pipeline._get_openai_client",
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
            "argumentation_analysis.orchestration.unified_pipeline._get_openai_client",
            return_value=(mock_client, "gpt-5-mini"),
        ):
            result = await _llm_enrich_quality(
                {"arg_1": {"note_finale": 5.0, "scores_par_vertu": {"clarity": 6.0}}},
                [{"text": "Some argument text"}],
            )

        assert result is None

    async def test_llm_enrichment_caps_at_4_arguments(self):
        """LLM enrichment only sends at most 4 arguments to the LLM."""
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
            f"arg_{i}": {"note_finale": float(i), "scores_par_vertu": {"clarity": float(i)}}
            for i in range(1, 8)
        }
        raw_args = [{"text": f"Argument {i}"} for i in range(1, 8)]

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline._get_openai_client",
            return_value=(mock_client, "gpt-5-mini"),
        ):
            await _llm_enrich_quality(heuristic, raw_args)

        # Verify the prompt only contains 4 arguments (cap)
        call_args = mock_client.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][1]["content"]
        # Count [arg_N] occurrences
        import re
        arg_refs = re.findall(r"\[arg_\d+\]", user_msg)
        assert len(arg_refs) <= 4

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
            "argumentation_analysis.orchestration.unified_pipeline._get_openai_client",
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
            "argumentation_analysis.orchestration.unified_pipeline._llm_enrich_quality",
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
            "argumentation_analysis.orchestration.unified_pipeline._llm_enrich_quality",
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
