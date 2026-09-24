"""#2344: the analysis pipeline never passes a keyword fallback off as an authentic run.

Measured on ``main`` ``ca62ade79``, ``require_real_llm=True`` and
``enable_fallback=False``, with no API key:
- the run fell back to keyword matching anyway;
- the status was ``completed``;
- ``success_rate`` was 1.0;
- the cause appeared nowhere.

A missing module did the same.

Now ``enable_fallback`` governs every fallback, each fallback carries its cause
(``fallback_cause``), and a run with a fallback is ``degraded``, not
``completed``.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

import argumentation_analysis.utils.analysis_config as analysis_config
from argumentation_analysis.utils.analysis_config import (
    AnalysisConfig,
    AnalysisMode,
    UnifiedAnalysisPipeline,
    create_analysis_pipeline,
)

TEXT = "Il faut attaquer la personne plutôt que ses idées."


def _pipeline(**overrides) -> UnifiedAnalysisPipeline:
    fields = dict(
        analysis_modes=[AnalysisMode.FALLACIES],
        retry_count=3,
        retry_delay=0.01,
        require_real_llm=True,
    )
    fields.update(overrides)
    return UnifiedAnalysisPipeline(AnalysisConfig(**fields))


def _no_key():
    return patch.object(analysis_config.settings.openai, "api_key", None)


def _no_module():
    # A ``None`` entry in ``sys.modules`` makes the import raise ImportError.
    return patch.dict(sys.modules, {"config.unified_config": None})


class TestFallbackNeedsPermission:
    async def test_no_key_without_fallback_is_an_error(self):
        pipeline = _pipeline(enable_fallback=False)
        with _no_key():
            result = await pipeline.analyze_text(TEXT)
        assert result.status == "error"
        assert any("OPENAI_API_KEY" in e for e in result.errors), result.errors
        assert result.results == {}

    async def test_missing_module_without_fallback_is_an_error(self):
        pipeline = _pipeline(enable_fallback=False)
        with _no_module():
            result = await pipeline.analyze_text(TEXT)
        assert result.status == "error"
        assert any("config.unified_config" in e for e in result.errors), result.errors

    async def test_a_missing_key_is_not_retried(self):
        # Retrying cannot supply a key: one attempt, then the fallback decision.
        pipeline = _pipeline(enable_fallback=False)
        real = pipeline._real_llm_analysis
        with _no_key(), patch.object(
            pipeline, "_real_llm_analysis", side_effect=real
        ) as spy:
            await pipeline.analyze_text(TEXT)
        assert spy.call_count == 1


class TestFallbackIsNamed:
    async def test_no_key_fallback_carries_its_cause_and_degrades_the_run(self):
        pipeline = _pipeline(enable_fallback=True)
        with _no_key():
            result = await pipeline.analyze_text(TEXT)

        mode_result = result.results["fallacies"]
        assert mode_result["fallback"] is True
        assert mode_result["authentic"] is False
        assert "OPENAI_API_KEY" in mode_result["fallback_cause"]
        assert result.status == "degraded"
        (warning,) = result.warnings
        assert warning.startswith("fallacies : analyse de repli, non authentique")
        assert "OPENAI_API_KEY" in warning

    async def test_exhausted_retries_name_the_last_error(self):
        pipeline = _pipeline(enable_fallback=True, retry_count=2)
        with patch.object(
            pipeline, "_real_llm_analysis", side_effect=RuntimeError("boom-2344")
        ):
            result = await pipeline.analyze_text(TEXT)
        assert (
            result.results["fallacies"]["fallback_cause"] == "RuntimeError: boom-2344"
        )
        assert result.status == "degraded"

    async def test_summary_counts_a_fallback_run_apart_from_successes(self):
        pipeline = _pipeline(enable_fallback=True)
        with _no_key():
            await pipeline.analyze_text(TEXT)
        summary = pipeline.get_session_summary()
        assert summary["successful_analyses"] == 0
        assert summary["degraded_analyses"] == 1
        assert summary["failed_analyses"] == 0
        assert summary["success_rate"] == 0

    async def test_a_run_without_fallback_stays_completed(self):
        # The negative control: the mock path is not a fallback.
        pipeline = _pipeline(require_real_llm=False)
        result = await pipeline.analyze_text(TEXT)
        assert result.status == "completed"
        assert result.warnings == []


class TestFactoryRejectsAnUnknownMode:
    def test_unknown_mode_raises_and_names_the_valid_ones(self):
        with pytest.raises(ValueError, match=r"'fallacy'.*fallacies"):
            create_analysis_pipeline(analysis_modes=["fallacy", "unified"])
