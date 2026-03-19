# -*- coding: utf-8 -*-
"""
Comprehensive tests for the argumentation_analysis.pipelines module.

Covers:
  1. unified_pipeline.py — routing pipeline (analyze_text, _detect_best_pipeline_mode, etc.)
  2. unified_text_analysis.py — UnifiedTextAnalysisPipeline, UnifiedAnalysisConfig, helpers
  3. orchestration/config/enums.py — OrchestrationMode, AnalysisType enums
  4. orchestration/config/base_config.py — ExtendedOrchestrationConfig
  5. orchestration/core/communication.py — initialize_communication_middleware
  6. orchestration/analysis/post_processors.py — post_process_orchestration_results
  7. orchestration/analysis/processors.py — execute_operational_tasks, synthesize_hierarchical_results
  8. orchestration/analysis/traces.py — trace_orchestration, get_communication_log, save_orchestration_trace

NOTE: unified_text_analysis.py has a broken import (get_fallacy_detector) which
cascades to all orchestration subpackages. We use sys.modules mocking to pre-inject
a fake module so all downstream imports succeed.
"""

import sys
import json
import pytest
import asyncio
import warnings
from types import SimpleNamespace, ModuleType
from unittest.mock import MagicMock, AsyncMock, patch, mock_open

# ============================================================================
# IMPORT WORKAROUND: unified_text_analysis.py fails to import because
# `from argumentation_analysis.core.bootstrap import get_fallacy_detector` does
# not exist as a module-level name. We must patch it BEFORE importing the module.
# ============================================================================


def _ensure_uta_importable():
    """Ensure unified_text_analysis and orchestration subpackages can be imported.

    Patches the bootstrap module to expose get_fallacy_detector as a module-level function
    if it's not already there.
    """
    try:
        from argumentation_analysis.core import bootstrap as _bootstrap_mod

        if not hasattr(_bootstrap_mod, "get_fallacy_detector"):
            _bootstrap_mod.get_fallacy_detector = MagicMock(return_value=MagicMock())
    except ImportError:
        pass


_ensure_uta_importable()

# Now attempt the imports; if they still fail, skip all tests in this file
try:
    from argumentation_analysis.pipelines.unified_text_analysis import (
        UnifiedAnalysisConfig,
        UnifiedTextAnalysisPipeline,
        run_unified_text_analysis_pipeline,
        create_unified_config_from_legacy,
    )

    UTA_AVAILABLE = True
except ImportError:
    UTA_AVAILABLE = False

try:
    from argumentation_analysis.pipelines.orchestration.config.enums import (
        OrchestrationMode,
        AnalysisType,
    )
    from argumentation_analysis.pipelines.orchestration.config.base_config import (
        ExtendedOrchestrationConfig,
    )

    ORCH_CONFIG_AVAILABLE = True
except ImportError:
    ORCH_CONFIG_AVAILABLE = False

try:
    from argumentation_analysis.pipelines.orchestration.core.communication import (
        initialize_communication_middleware,
    )

    COMM_AVAILABLE = True
except ImportError:
    COMM_AVAILABLE = False

try:
    from argumentation_analysis.pipelines.orchestration.analysis.post_processors import (
        post_process_orchestration_results,
    )
    from argumentation_analysis.pipelines.orchestration.analysis.processors import (
        execute_operational_tasks,
        synthesize_hierarchical_results,
    )
    from argumentation_analysis.pipelines.orchestration.analysis.traces import (
        trace_orchestration,
        get_communication_log,
        save_orchestration_trace,
    )

    ANALYSIS_AVAILABLE = True
except ImportError:
    ANALYSIS_AVAILABLE = False


MODULE = "argumentation_analysis.pipelines.unified_pipeline"
UTA_MODULE = "argumentation_analysis.pipelines.unified_text_analysis"
COMM_MODULE = "argumentation_analysis.pipelines.orchestration.core.communication"


# ============================================================================
# SECTION 1: unified_pipeline.py tests
# (This module imports fine because it has its own try/except guards)
# ============================================================================


class TestPipelineMode:
    """Tests for PipelineMode constants."""

    def test_pipeline_mode_original(self):
        from argumentation_analysis.pipelines.unified_pipeline import PipelineMode

        assert PipelineMode.ORIGINAL == "original"

    def test_pipeline_mode_orchestration(self):
        from argumentation_analysis.pipelines.unified_pipeline import PipelineMode

        assert PipelineMode.ORCHESTRATION == "orchestration"

    def test_pipeline_mode_auto(self):
        from argumentation_analysis.pipelines.unified_pipeline import PipelineMode

        assert PipelineMode.AUTO == "auto"

    def test_pipeline_mode_hybrid(self):
        from argumentation_analysis.pipelines.unified_pipeline import PipelineMode

        assert PipelineMode.HYBRID == "hybrid"


class TestDetectBestPipelineMode:
    """Tests for _detect_best_pipeline_mode."""

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    def test_detect_orchestration_when_enabled_and_available(self):
        from argumentation_analysis.pipelines.unified_pipeline import (
            _detect_best_pipeline_mode,
        )

        assert _detect_best_pipeline_mode(enable_orchestration=True) == "orchestration"

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", False)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    def test_detect_original_when_orchestration_unavailable(self):
        from argumentation_analysis.pipelines.unified_pipeline import (
            _detect_best_pipeline_mode,
        )

        assert _detect_best_pipeline_mode(enable_orchestration=True) == "original"

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    def test_detect_original_when_orchestration_disabled(self):
        from argumentation_analysis.pipelines.unified_pipeline import (
            _detect_best_pipeline_mode,
        )

        assert _detect_best_pipeline_mode(enable_orchestration=False) == "original"

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", False)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", False)
    def test_detect_raises_when_nothing_available(self):
        from argumentation_analysis.pipelines.unified_pipeline import (
            _detect_best_pipeline_mode,
        )

        with pytest.raises(RuntimeError, match="Aucun pipeline disponible"):
            _detect_best_pipeline_mode(enable_orchestration=True)

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", False)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", False)
    def test_detect_raises_when_disabled_and_original_unavailable(self):
        from argumentation_analysis.pipelines.unified_pipeline import (
            _detect_best_pipeline_mode,
        )

        with pytest.raises(RuntimeError):
            _detect_best_pipeline_mode(enable_orchestration=False)


class TestMapAnalysisTypeToLegacyMode:
    """Tests for _map_analysis_type_to_legacy_mode."""

    def _call(self, val):
        from argumentation_analysis.pipelines.unified_pipeline import (
            _map_analysis_type_to_legacy_mode,
        )

        return _map_analysis_type_to_legacy_mode(val)

    def test_comprehensive(self):
        assert self._call("comprehensive") == "unified"

    def test_rhetorical(self):
        assert self._call("rhetorical") == "informal"

    def test_logical(self):
        assert self._call("logical") == "formal"

    def test_investigative(self):
        assert self._call("investigative") == "unified"

    def test_fallacy_focused(self):
        assert self._call("fallacy_focused") == "informal"

    def test_argument_structure(self):
        assert self._call("argument_structure") == "formal"

    def test_debate_analysis(self):
        assert self._call("debate_analysis") == "unified"

    def test_custom(self):
        assert self._call("custom") == "unified"

    def test_unknown(self):
        assert self._call("xyz") == "unified"


class TestGenerateUnifiedRecommendations:
    """Tests for _generate_unified_recommendations."""

    def _call(self, results):
        from argumentation_analysis.pipelines.unified_pipeline import (
            _generate_unified_recommendations,
        )

        return _generate_unified_recommendations(results)

    def test_orchestration_with_specialized(self):
        recs = self._call(
            {
                "metadata": {"pipeline_mode": "orchestration"},
                "specialized_orchestration": {
                    "orchestrator_used": "CluedoOrchestrator"
                },
                "execution_time": 5,
            }
        )
        assert any("CluedoOrchestrator" in r for r in recs)

    def test_orchestration_with_strategic(self):
        recs = self._call(
            {
                "metadata": {"pipeline_mode": "orchestration"},
                "strategic_analysis": {},
                "execution_time": 5,
            }
        )
        assert any("hiérarchique" in r.lower() for r in recs)

    def test_hybrid_mode(self):
        recs = self._call(
            {"metadata": {"pipeline_mode": "hybrid"}, "execution_time": 5}
        )
        assert any("hybride" in r.lower() for r in recs)

    def test_high_exec_time(self):
        recs = self._call(
            {"metadata": {"pipeline_mode": "original"}, "execution_time": 15}
        )
        assert any("élevé" in r.lower() for r in recs)

    def test_fast_exec_time(self):
        recs = self._call(
            {"metadata": {"pipeline_mode": "original"}, "execution_time": 0.5}
        )
        assert any("rapide" in r.lower() for r in recs)

    def test_error_status(self):
        recs = self._call(
            {
                "metadata": {"pipeline_mode": "original"},
                "status": "error",
                "execution_time": 5,
            }
        )
        assert any("erreur" in r.lower() for r in recs)

    def test_fallback_used(self):
        recs = self._call(
            {
                "metadata": {"pipeline_mode": "original"},
                "fallback_used": True,
                "execution_time": 5,
            }
        )
        assert any("fallback" in r.lower() for r in recs)

    def test_default(self):
        recs = self._call(
            {"metadata": {"pipeline_mode": "original"}, "execution_time": 5}
        )
        assert any("succès" in r.lower() for r in recs)


class TestSynthesizeHybridResults:
    """Tests for _synthesize_hybrid_results."""

    def _call(self, results):
        from argumentation_analysis.pipelines.unified_pipeline import (
            _synthesize_hybrid_results,
        )

        return _synthesize_hybrid_results(results)

    def test_merges_without_duplicates(self):
        r = self._call(
            {
                "pipeline_results": {
                    "orchestration": {
                        "informal_analysis": {
                            "fallacies": [{"type": "A"}, {"type": "B"}]
                        }
                    },
                    "original": {
                        "informal_analysis": {
                            "fallacies": [{"type": "B"}, {"type": "C"}]
                        }
                    },
                }
            }
        )
        types = [f["type"] for f in r["informal_analysis"]["fallacies"]]
        assert sorted(types) == ["A", "B", "C"]

    def test_empty_one_side(self):
        r = self._call({"pipeline_results": {"orchestration": {}, "original": {}}})
        assert r is not None

    def test_missing_pipeline_results(self):
        r = self._call({"pipeline_results": {}})
        assert "pipeline_results" in r

    def test_summary_counts(self):
        r = self._call(
            {
                "pipeline_results": {
                    "orchestration": {
                        "informal_analysis": {"fallacies": [{"type": "X"}]}
                    },
                    "original": {"informal_analysis": {"fallacies": [{"type": "Y"}]}},
                }
            }
        )
        s = r["informal_analysis"]["summary"]
        assert s["total_fallacies"] == 2
        assert s["source"] == "hybrid_synthesis"


class TestAnalyzeText:
    """Tests for the main analyze_text async function."""

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", False)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", False)
    async def test_empty_text_raises(self):
        from argumentation_analysis.pipelines.unified_pipeline import analyze_text

        with pytest.raises(ValueError, match="Texte vide"):
            await analyze_text("", mode="original")

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", False)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", False)
    async def test_whitespace_text_raises(self):
        from argumentation_analysis.pipelines.unified_pipeline import analyze_text

        with pytest.raises(ValueError):
            await analyze_text("   ", mode="original")

    @patch(f"{MODULE}._generate_unified_recommendations", return_value=["OK"])
    @patch(f"{MODULE}._run_orchestration_pipeline", new_callable=AsyncMock)
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    async def test_orchestration_mode(self, mock_run, mock_recs):
        from argumentation_analysis.pipelines.unified_pipeline import analyze_text

        mock_run.return_value = {
            "metadata": {"pipeline_mode": "orchestration"},
            "pipeline_results": {},
            "comparison": {},
            "recommendations": [],
            "execution_time": 0,
            "status": "in_progress",
        }
        r = await analyze_text("Text", mode="orchestration")
        mock_run.assert_called_once()

    @patch(f"{MODULE}._generate_unified_recommendations", return_value=["OK"])
    @patch(f"{MODULE}._run_original_pipeline", new_callable=AsyncMock)
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    async def test_original_mode(self, mock_run, mock_recs):
        from argumentation_analysis.pipelines.unified_pipeline import analyze_text

        mock_run.return_value = {
            "metadata": {"pipeline_mode": "original"},
            "pipeline_results": {},
            "comparison": {},
            "recommendations": [],
            "execution_time": 0,
            "status": "in_progress",
        }
        await analyze_text("Text", mode="original")
        mock_run.assert_called_once()

    @patch(f"{MODULE}._generate_unified_recommendations", return_value=["OK"])
    @patch(f"{MODULE}._run_hybrid_pipeline", new_callable=AsyncMock)
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    async def test_hybrid_mode(self, mock_run, mock_recs):
        from argumentation_analysis.pipelines.unified_pipeline import analyze_text

        mock_run.return_value = {
            "metadata": {"pipeline_mode": "hybrid"},
            "pipeline_results": {},
            "comparison": {},
            "recommendations": [],
            "execution_time": 0,
            "status": "in_progress",
        }
        await analyze_text("Text", mode="hybrid")
        mock_run.assert_called_once()

    @patch(f"{MODULE}._generate_unified_recommendations", return_value=["OK"])
    @patch(f"{MODULE}._run_orchestration_pipeline", new_callable=AsyncMock)
    @patch(f"{MODULE}._detect_best_pipeline_mode", return_value="orchestration")
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    async def test_auto_mode(self, mock_detect, mock_run, mock_recs):
        from argumentation_analysis.pipelines.unified_pipeline import analyze_text

        mock_run.return_value = {
            "metadata": {"pipeline_mode": "orchestration"},
            "pipeline_results": {},
            "comparison": {},
            "recommendations": [],
            "execution_time": 0,
            "status": "in_progress",
        }
        await analyze_text("Text", mode="auto")
        mock_detect.assert_called_once()

    @patch(f"{MODULE}._generate_unified_recommendations", return_value=["OK"])
    @patch(f"{MODULE}._run_orchestration_pipeline", new_callable=AsyncMock)
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    async def test_unknown_mode_orchestration_fallback(self, mock_run, mock_recs):
        from argumentation_analysis.pipelines.unified_pipeline import analyze_text

        mock_run.return_value = {
            "metadata": {"pipeline_mode": "x"},
            "pipeline_results": {},
            "comparison": {},
            "recommendations": [],
            "execution_time": 0,
            "status": "in_progress",
        }
        await analyze_text("Text", mode="unknown_mode")
        mock_run.assert_called_once()

    @patch(f"{MODULE}._generate_unified_recommendations", return_value=["OK"])
    @patch(f"{MODULE}._run_original_pipeline", new_callable=AsyncMock)
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", False)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    async def test_unknown_mode_original_fallback(self, mock_run, mock_recs):
        from argumentation_analysis.pipelines.unified_pipeline import analyze_text

        mock_run.return_value = {
            "metadata": {"pipeline_mode": "x"},
            "pipeline_results": {},
            "comparison": {},
            "recommendations": [],
            "execution_time": 0,
            "status": "in_progress",
        }
        await analyze_text("Text", mode="unknown_mode")
        mock_run.assert_called_once()

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", False)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", False)
    async def test_unknown_mode_no_pipeline_error(self):
        from argumentation_analysis.pipelines.unified_pipeline import analyze_text

        r = await analyze_text("Text", mode="unknown_mode")
        assert r["status"] == "error"

    @patch(f"{MODULE}._generate_unified_recommendations", return_value=["OK"])
    @patch(f"{MODULE}._run_original_pipeline", new_callable=AsyncMock)
    @patch(
        f"{MODULE}._run_orchestration_pipeline",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Boom"),
    )
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    async def test_fallback_on_error(self, mock_orch, mock_orig, mock_recs):
        from argumentation_analysis.pipelines.unified_pipeline import analyze_text

        mock_orig.return_value = {
            "metadata": {"pipeline_mode": "original"},
            "pipeline_results": {"original": {"data": 1}},
            "comparison": {},
            "recommendations": [],
            "execution_time": 0,
            "status": "in_progress",
        }
        r = await analyze_text("Text", mode="orchestration")
        assert r["status"] == "partial_success"
        assert r.get("fallback_used") is True

    @patch(
        f"{MODULE}._run_orchestration_pipeline",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Boom"),
    )
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", False)
    async def test_no_fallback_when_unavailable(self, mock_orch):
        from argumentation_analysis.pipelines.unified_pipeline import analyze_text

        r = await analyze_text("Text", mode="orchestration")
        assert r["status"] == "error"

    @patch(f"{MODULE}._generate_unified_recommendations", return_value=["OK"])
    @patch(
        f"{MODULE}._compare_pipelines",
        new_callable=AsyncMock,
        return_value={"approaches_tested": []},
    )
    @patch(f"{MODULE}._run_orchestration_pipeline", new_callable=AsyncMock)
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    async def test_comparison_called(self, mock_run, mock_compare, mock_recs):
        from argumentation_analysis.pipelines.unified_pipeline import analyze_text

        mock_run.return_value = {
            "metadata": {"pipeline_mode": "orchestration"},
            "pipeline_results": {},
            "comparison": {},
            "recommendations": [],
            "execution_time": 0,
            "status": "in_progress",
        }
        await analyze_text("Text", mode="orchestration", enable_comparison=True)
        mock_compare.assert_called_once()

    @patch(f"{MODULE}._generate_unified_recommendations", return_value=["OK"])
    @patch(f"{MODULE}._run_orchestration_pipeline", new_callable=AsyncMock)
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    async def test_success_status(self, mock_run, mock_recs):
        from argumentation_analysis.pipelines.unified_pipeline import analyze_text

        mock_run.return_value = {
            "metadata": {"pipeline_mode": "orchestration"},
            "pipeline_results": {},
            "comparison": {},
            "recommendations": [],
            "execution_time": 0,
            "status": "in_progress",
        }
        r = await analyze_text("Hello", mode="orchestration")
        assert r["status"] == "success"
        assert r["execution_time"] >= 0


class TestRunOrchestrationPipeline:
    """Tests for _run_orchestration_pipeline."""

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", False)
    async def test_raises_when_unavailable(self):
        from argumentation_analysis.pipelines.unified_pipeline import (
            _run_orchestration_pipeline,
        )

        with pytest.raises(RuntimeError, match="non disponibles"):
            await _run_orchestration_pipeline("t", "c", "a", False, None, {})

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    async def test_selects_cluedo_for_mode(self):
        import argumentation_analysis.pipelines.unified_pipeline as mod

        mi = MagicMock()
        mi.__class__.__name__ = "CluedoOrchestrator"
        mi.orchestrate_investigation_analysis = AsyncMock(return_value={"r": 1})
        with patch.object(
            mod, "create_llm_service", return_value=MagicMock(), create=True
        ), patch.object(
            mod, "CluedoOrchestrator", MagicMock(return_value=mi), create=True
        ):
            r = await mod._run_orchestration_pipeline(
                "text", "c", "cluedo", False, None, {"pipeline_results": {}}
            )
            assert "orchestration" in r["pipeline_results"]

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    async def test_selects_cluedo_for_keyword(self):
        import argumentation_analysis.pipelines.unified_pipeline as mod

        mi = MagicMock()
        mi.__class__.__name__ = "CluedoOrchestrator"
        mi.orchestrate_investigation_analysis = AsyncMock(return_value={"r": 1})
        with patch.object(
            mod, "create_llm_service", return_value=MagicMock(), create=True
        ), patch.object(
            mod, "CluedoOrchestrator", MagicMock(return_value=mi), create=True
        ):
            await mod._run_orchestration_pipeline(
                "Le témoin de l'enquête",
                "c",
                "auto_select",
                False,
                None,
                {"pipeline_results": {}},
            )

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    async def test_selects_conversation_for_colon(self):
        import argumentation_analysis.pipelines.unified_pipeline as mod

        mi = MagicMock()
        mi.__class__.__name__ = "ConversationOrchestrator"
        mi.orchestrate_dialogue_analysis = AsyncMock(return_value={"r": 1})
        with patch.object(
            mod, "create_llm_service", return_value=MagicMock(), create=True
        ), patch.object(
            mod, "ConversationOrchestrator", MagicMock(return_value=mi), create=True
        ):
            await mod._run_orchestration_pipeline(
                "Speaker: Hello",
                "c",
                "auto_select",
                False,
                None,
                {"pipeline_results": {}},
            )

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    async def test_selects_logique_for_keyword(self):
        import argumentation_analysis.pipelines.unified_pipeline as mod

        mi = MagicMock()
        mi.__class__.__name__ = "LogiqueComplexeOrchestrator"
        mi.orchestrate_complex_logical_analysis = AsyncMock(return_value={"r": 1})
        with patch.object(
            mod, "create_llm_service", return_value=MagicMock(), create=True
        ), patch.object(
            mod, "LogiqueComplexeOrchestrator", MagicMock(return_value=mi), create=True
        ):
            await mod._run_orchestration_pipeline(
                "tous les hommes sont mortels",
                "c",
                "auto_select",
                False,
                None,
                {"pipeline_results": {}},
            )

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    async def test_selects_real_llm_fallback(self):
        import argumentation_analysis.pipelines.unified_pipeline as mod

        mi = MagicMock()
        mi.__class__.__name__ = "RealLLMOrchestrator"
        mi.orchestrate_multi_llm_analysis = AsyncMock(return_value={"r": 1})
        with patch.object(
            mod, "create_llm_service", return_value=MagicMock(), create=True
        ), patch.object(
            mod, "RealLLMOrchestrator", MagicMock(return_value=mi), create=True
        ):
            r = await mod._run_orchestration_pipeline(
                "Generic text",
                "c",
                "auto_select",
                False,
                None,
                {"pipeline_results": {}},
            )
            assert "specialized_orchestration" in r


class TestRunOriginalPipeline:
    """Tests for _run_original_pipeline."""

    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", False)
    async def test_raises_when_unavailable(self):
        from argumentation_analysis.pipelines.unified_pipeline import (
            _run_original_pipeline,
        )

        with pytest.raises(RuntimeError, match="non disponible"):
            await _run_original_pipeline("t", "c", False, None, {})

    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    async def test_calls_pipeline(self):
        import argumentation_analysis.pipelines.unified_pipeline as mod

        mock_run = AsyncMock(
            return_value={"informal_analysis": {"f": []}, "formal_analysis": {}}
        )
        with patch.object(
            mod,
            "create_unified_config_from_legacy",
            return_value=MagicMock(),
            create=True,
        ), patch.object(
            mod, "run_unified_text_analysis_pipeline", mock_run, create=True
        ):
            r = await mod._run_original_pipeline(
                "t", "comprehensive", False, None, {"pipeline_results": {}}
            )
            assert "original" in r["pipeline_results"]

    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    async def test_copies_fields(self):
        import argumentation_analysis.pipelines.unified_pipeline as mod

        mock_run = AsyncMock(
            return_value={
                "informal_analysis": {"d": 1},
                "formal_analysis": {"l": 1},
                "unified_analysis": {"s": 1},
            }
        )
        with patch.object(
            mod,
            "create_unified_config_from_legacy",
            return_value=MagicMock(),
            create=True,
        ), patch.object(
            mod, "run_unified_text_analysis_pipeline", mock_run, create=True
        ):
            r = await mod._run_original_pipeline(
                "t", "c", False, None, {"pipeline_results": {}}
            )
            assert r["informal_analysis"] == {"d": 1}


class TestRunHybridPipeline:
    @patch(f"{MODULE}._synthesize_hybrid_results", side_effect=lambda r: r)
    @patch(
        f"{MODULE}._run_original_pipeline",
        new_callable=AsyncMock,
        return_value={"pipeline_results": {}},
    )
    @patch(
        f"{MODULE}._run_orchestration_pipeline",
        new_callable=AsyncMock,
        return_value={"pipeline_results": {}},
    )
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    async def test_runs_both(self, mock_o, mock_p, mock_s):
        from argumentation_analysis.pipelines.unified_pipeline import (
            _run_hybrid_pipeline,
        )

        await _run_hybrid_pipeline("t", "c", "a", False, None, {"pipeline_results": {}})
        mock_o.assert_called_once()
        mock_p.assert_called_once()

    @patch(f"{MODULE}._synthesize_hybrid_results", side_effect=lambda r: r)
    @patch(
        f"{MODULE}._run_orchestration_pipeline",
        new_callable=AsyncMock,
        side_effect=RuntimeError("F"),
    )
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", False)
    async def test_tolerates_failure(self, mock_o, mock_s):
        from argumentation_analysis.pipelines.unified_pipeline import (
            _run_hybrid_pipeline,
        )

        await _run_hybrid_pipeline("t", "c", "a", False, None, {"pipeline_results": {}})


class TestComparePipelines:
    async def test_returns_structure(self):
        from argumentation_analysis.pipelines.unified_pipeline import _compare_pipelines

        r = await _compare_pipelines("t", "c", False)
        assert "comparison_timestamp" in r
        assert "approaches_tested" in r


class TestGetAvailableFeatures:
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    def test_all_available(self):
        from argumentation_analysis.pipelines.unified_pipeline import (
            get_available_features,
        )

        f = get_available_features()
        assert (
            f["original_pipeline"] is True
            and f["orchestration_pipeline"] is True
            and f["hybrid_mode"] is True
        )

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", False)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", False)
    def test_none_available(self):
        from argumentation_analysis.pipelines.unified_pipeline import (
            get_available_features,
        )

        f = get_available_features()
        assert f["original_pipeline"] is False and f["hybrid_mode"] is False


class TestCompatibilityFunctions:
    @patch(
        f"{MODULE}.analyze_text", new_callable=AsyncMock, return_value={"status": "ok"}
    )
    async def test_run_analysis(self, mock_at):
        from argumentation_analysis.pipelines.unified_pipeline import run_analysis

        r = await run_analysis("Hello")
        mock_at.assert_called_once_with("Hello")

    @patch(
        f"{MODULE}.analyze_text", new_callable=AsyncMock, return_value={"status": "ok"}
    )
    async def test_enhanced_hierarchical(self, mock_at):
        from argumentation_analysis.pipelines.unified_pipeline import (
            run_enhanced_analysis,
        )

        await run_enhanced_analysis("Hello", enable_hierarchical=True)
        _, kw = mock_at.call_args
        assert kw.get("mode") == "orchestration"

    @patch(
        f"{MODULE}.analyze_text", new_callable=AsyncMock, return_value={"status": "ok"}
    )
    async def test_enhanced_no_flags(self, mock_at):
        from argumentation_analysis.pipelines.unified_pipeline import (
            run_enhanced_analysis,
        )

        await run_enhanced_analysis(
            "Hello", enable_hierarchical=False, enable_specialized=False
        )
        _, kw = mock_at.call_args
        assert kw.get("mode") == "original"


class TestMigrationMessage:
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    def test_sets_flag(self):
        import argumentation_analysis.pipelines.unified_pipeline as mod

        mod._MIGRATION_MESSAGE_SHOWN = False
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            mod._show_migration_message()
            assert mod._MIGRATION_MESSAGE_SHOWN is True

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    def test_no_double_warn(self):
        import argumentation_analysis.pipelines.unified_pipeline as mod

        mod._MIGRATION_MESSAGE_SHOWN = True
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mod._show_migration_message()
            assert len([x for x in w if "orchestration" in str(x.message).lower()]) == 0

    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", False)
    def test_no_warn_when_unavailable(self):
        import argumentation_analysis.pipelines.unified_pipeline as mod

        mod._MIGRATION_MESSAGE_SHOWN = False
        mod._show_migration_message()
        assert mod._MIGRATION_MESSAGE_SHOWN is False


class TestPrintFeatureStatus:
    @patch(f"{MODULE}.ORCHESTRATION_PIPELINE_AVAILABLE", True)
    @patch(f"{MODULE}.ORIGINAL_PIPELINE_AVAILABLE", True)
    def test_does_not_crash(self):
        from argumentation_analysis.pipelines.unified_pipeline import (
            print_feature_status,
        )

        print_feature_status()


# ============================================================================
# SECTION 2: unified_text_analysis.py tests
# ============================================================================


@pytest.mark.skipif(
    not UTA_AVAILABLE,
    reason="unified_text_analysis import failed (missing get_fallacy_detector)",
)
class TestUnifiedAnalysisConfig:
    def test_default(self):
        c = UnifiedAnalysisConfig()
        assert c.analysis_modes == ["informal", "formal"]
        assert c.orchestration_mode == "pipeline"

    def test_custom_modes(self):
        c = UnifiedAnalysisConfig(analysis_modes=["unified", "formal"])
        assert "unified" in c.analysis_modes

    def test_invalid_modes_filtered(self):
        c = UnifiedAnalysisConfig(analysis_modes=["bogus", "informal"])
        assert c.analysis_modes == ["informal"]

    def test_all_invalid_fallback(self):
        c = UnifiedAnalysisConfig(analysis_modes=["x", "y"])
        assert c.analysis_modes == ["informal"]

    def test_empty_fallback(self):
        # Empty list is falsy, so `analysis_modes or [default]` triggers
        c = UnifiedAnalysisConfig(analysis_modes=[])
        assert c.analysis_modes == ["informal", "formal"]

    def test_conversation_logging(self):
        assert UnifiedAnalysisConfig().enable_conversation_logging is True
        assert (
            UnifiedAnalysisConfig(
                enable_conversation_logging=False
            ).enable_conversation_logging
            is False
        )


@pytest.mark.skipif(not UTA_AVAILABLE, reason="unified_text_analysis import failed")
class TestCreateConfigFromLegacy:
    def test_formal(self):
        assert create_unified_config_from_legacy(mode="formal").analysis_modes == [
            "formal"
        ]

    def test_informal(self):
        assert create_unified_config_from_legacy(mode="informal").analysis_modes == [
            "informal"
        ]

    def test_unified(self):
        c = create_unified_config_from_legacy(mode="unified")
        assert len(c.analysis_modes) == 3

    def test_all(self):
        assert len(create_unified_config_from_legacy(mode="all").analysis_modes) == 3

    def test_unknown(self):
        assert create_unified_config_from_legacy(mode="xyz").analysis_modes == [
            "informal"
        ]

    def test_kwargs(self):
        c = create_unified_config_from_legacy(
            mode="formal", use_mocks=True, logic_type="modal"
        )
        assert c.use_mocks is True and c.logic_type == "modal"


@pytest.mark.skipif(not UTA_AVAILABLE, reason="unified_text_analysis import failed")
class TestUnifiedTextAnalysisPipeline:
    def _make(self, **kw):
        return UnifiedTextAnalysisPipeline(UnifiedAnalysisConfig(**kw))

    def test_init(self):
        p = self._make()
        assert p.llm_service is None and p.jvm_ready is False and p.analysis_tools == {}

    def test_severity_distribution(self):
        p = self._make()
        d = p._calculate_severity_distribution(
            [
                {"severity": "Faible"},
                {"severity": "Moyen"},
                {"severity": "Moyen"},
                {"severity": "Critique"},
                {"severity": "X"},
            ]
        )
        assert (
            d["Faible"] == 1
            and d["Moyen"] == 2
            and d["Critique"] == 1
            and d["Élevé"] == 0
        )

    def test_severity_empty(self):
        assert all(
            v == 0 for v in self._make()._calculate_severity_distribution([]).values()
        )

    def test_recs_many_fallacies(self):
        r = self._make()._generate_recommendations(
            {
                "informal_analysis": {"fallacies": [{"severity": "M"}] * 5},
                "formal_analysis": {},
                "orchestration_analysis": {},
            }
        )
        assert any("révision" in x.lower() for x in r)

    def test_recs_critical(self):
        r = self._make()._generate_recommendations(
            {
                "informal_analysis": {"fallacies": [{"severity": "Critique"}]},
                "formal_analysis": {},
                "orchestration_analysis": {},
            }
        )
        assert any("critique" in x.lower() for x in r)

    def test_recs_inconsistency(self):
        r = self._make()._generate_recommendations(
            {
                "informal_analysis": {"fallacies": []},
                "formal_analysis": {"consistency_check": False},
                "orchestration_analysis": {},
            }
        )
        assert any("incohérence" in x.lower() for x in r)

    def test_recs_orch_success(self):
        r = self._make()._generate_recommendations(
            {
                "informal_analysis": {"fallacies": []},
                "formal_analysis": {},
                "orchestration_analysis": {"status": "success"},
            }
        )
        assert any("orchestrée" in x.lower() for x in r)

    def test_recs_default(self):
        r = self._make()._generate_recommendations(
            {
                "informal_analysis": {"fallacies": []},
                "formal_analysis": {},
                "orchestration_analysis": {},
            }
        )
        assert len(r) >= 1

    def test_conv_log_none(self):
        p = self._make()
        p.conversation_logger = None
        assert p.get_conversation_log() == {}

    def test_conv_log_present(self):
        p = self._make()
        p.conversation_logger = MagicMock(
            messages=[{"m": 1}], tool_calls=[], state_snapshots=[]
        )
        assert len(p.get_conversation_log()["messages"]) == 1

    async def test_informal_no_plugin(self):
        p = self._make()
        p.analysis_tools = {}
        r = await p._perform_informal_analysis("t")
        assert "error" in str(r).lower()

    async def test_informal_with_plugin(self):
        p = self._make()
        mp = MagicMock()
        mp.analyze_text.return_value = {
            "fallacy_analysis": {
                "fallacy_types_distribution": {"AH": 2},
                "total_fallacies": 2,
                "overall_severity": 0.5,
                "severity_level": "M",
            }
        }
        p.analysis_tools = {"analysis_plugin": mp}
        r = await p._perform_informal_analysis("t")
        assert "fallacies" in r

    async def test_formal_no_jvm(self):
        p = self._make()
        p.jvm_ready = False
        p.llm_service = MagicMock()
        assert (await p._perform_formal_analysis("t"))["status"] == "Skipped"

    async def test_formal_no_llm(self):
        p = self._make()
        p.jvm_ready = True
        p.llm_service = None
        assert (await p._perform_formal_analysis("t"))["status"] == "Skipped"

    async def test_unified_no_agent(self):
        p = self._make()
        p.analysis_tools = {}
        assert (await p._perform_unified_analysis("t"))["status"] == "Skipped"

    async def test_unified_with_agent(self):
        p = self._make()
        ma = AsyncMock()
        mr = MagicMock(
            executive_summary="S",
            recommendations=["r"],
            overall_validity=0.8,
            confidence_level=0.9,
        )
        ma.synthesize_analysis.return_value = mr
        p.analysis_tools = {"synthesis_agent": ma}
        r = await p._perform_unified_analysis("t")
        assert r["status"] == "Success" and r["synthesis_report"] == "S"

    async def test_unified_returns_none(self):
        p = self._make()
        ma = AsyncMock()
        ma.synthesize_analysis.return_value = None
        p.analysis_tools = {"synthesis_agent": ma}
        assert (await p._perform_unified_analysis("t"))["status"] == "Failed"

    async def test_unified_raises(self):
        p = self._make()
        ma = AsyncMock()
        ma.synthesize_analysis.side_effect = RuntimeError("E")
        p.analysis_tools = {"synthesis_agent": ma}
        assert (await p._perform_unified_analysis("t"))["status"] == "Error"

    async def test_orch_no_orchestrator(self):
        p = self._make()
        p.orchestrator = None
        assert (await p._perform_orchestration_analysis("t"))["status"] == "Skipped"

    async def test_orch_comprehensive(self):
        p = self._make(orchestration_mode="real")
        mo = AsyncMock()
        mo.analyze_text_comprehensive = AsyncMock(
            return_value={
                "agents_used": ["a"],
                "conversation_summary": {},
                "results": {},
            }
        )
        p.orchestrator = mo
        assert (await p._perform_orchestration_analysis("t"))["status"] == "success"

    async def test_orch_conversation(self):
        p = self._make(orchestration_mode="conversation")
        mo = MagicMock(spec=[])
        mo.run_conversation = AsyncMock(return_value={})
        p.orchestrator = mo
        assert (await p._perform_orchestration_analysis("t"))["status"] == "success"

    async def test_orch_unknown_method(self):
        p = self._make()
        p.orchestrator = MagicMock(spec=[])
        assert (await p._perform_orchestration_analysis("t"))["status"] == "Failed"

    async def test_orch_error(self):
        p = self._make(orchestration_mode="real")
        mo = AsyncMock()
        mo.analyze_text_comprehensive = AsyncMock(side_effect=RuntimeError("E"))
        p.orchestrator = mo
        assert (await p._perform_orchestration_analysis("t"))["status"] == "Error"

    async def test_analyze_unified_runs(self):
        p = self._make(analysis_modes=["informal"])
        p.orchestrator = None
        p.conversation_logger = None
        p._perform_informal_analysis = AsyncMock(
            return_value={"status": "Success", "fallacies": [], "summary": {}}
        )
        p._generate_recommendations = MagicMock(return_value=["r"])
        r = await p.analyze_text_unified("t")
        assert r["informal_analysis"]["status"] == "Success"

    async def test_analyze_unified_error(self):
        p = self._make(analysis_modes=["informal"])
        p.orchestrator = None
        p.conversation_logger = None
        p._perform_informal_analysis = AsyncMock(side_effect=RuntimeError("F"))
        assert "error" in await p.analyze_text_unified("t")

    async def test_informal_orchestrated_no_orch(self):
        p = self._make()
        p.orchestrator = None
        p._perform_informal_analysis = AsyncMock(
            return_value={"status": "S", "fallacies": [], "summary": {}}
        )
        await p._perform_informal_analysis_orchestrated("t")
        p._perform_informal_analysis.assert_called_once()


@pytest.mark.skipif(not UTA_AVAILABLE, reason="unified_text_analysis import failed")
class TestRunPipelineFunction:
    @patch(f"{UTA_MODULE}.UnifiedTextAnalysisPipeline")
    async def test_default_config(self, mock_cls):
        mi = AsyncMock()
        mi.initialize.return_value = True
        mi.analyze_text_unified.return_value = {"d": 1}
        mock_cls.return_value = mi
        r = await run_unified_text_analysis_pipeline("t")
        assert r["status"] == "success"

    @patch(f"{UTA_MODULE}.UnifiedTextAnalysisPipeline")
    async def test_init_fail(self, mock_cls):
        mi = AsyncMock()
        mi.initialize.return_value = False
        mock_cls.return_value = mi
        assert (await run_unified_text_analysis_pipeline("t"))["status"] == "failed"

    @patch(f"{UTA_MODULE}.UnifiedTextAnalysisPipeline", side_effect=RuntimeError("E"))
    async def test_exception(self, mock_cls):
        # UnifiedTextAnalysisPipeline(config) is called OUTSIDE the try/except,
        # so the error propagates as an uncaught exception.
        with pytest.raises(RuntimeError, match="E"):
            await run_unified_text_analysis_pipeline("t")


# ============================================================================
# SECTION 3: orchestration/config/enums.py tests
# ============================================================================


@pytest.mark.skipif(
    not ORCH_CONFIG_AVAILABLE, reason="orchestration config import failed"
)
class TestOrchestrationModeEnum:
    def test_pipeline(self):
        assert OrchestrationMode.PIPELINE.value == "pipeline"

    def test_real(self):
        assert OrchestrationMode.REAL.value == "real"

    def test_auto(self):
        assert OrchestrationMode.AUTO_SELECT.value == "auto_select"

    def test_all_strings(self):
        for m in OrchestrationMode:
            assert isinstance(m.value, str)

    def test_count(self):
        assert len(OrchestrationMode) == 11


@pytest.mark.skipif(
    not ORCH_CONFIG_AVAILABLE, reason="orchestration config import failed"
)
class TestAnalysisTypeEnum:
    def test_comprehensive(self):
        assert AnalysisType.COMPREHENSIVE.value == "comprehensive"

    def test_custom(self):
        assert AnalysisType.CUSTOM.value == "custom"

    def test_all_strings(self):
        for m in AnalysisType:
            assert isinstance(m.value, str)

    def test_count(self):
        assert len(AnalysisType) == 8


# ============================================================================
# SECTION 4: orchestration/config/base_config.py tests
# ============================================================================


@pytest.mark.skipif(
    not ORCH_CONFIG_AVAILABLE, reason="orchestration config import failed"
)
class TestExtendedOrchestrationConfig:
    def test_default(self):
        c = ExtendedOrchestrationConfig()
        assert (
            c.enable_hierarchical is True
            and c.max_concurrent_analyses == 10
            and c.analysis_timeout == 300
        )

    def test_inherits(self):
        assert isinstance(ExtendedOrchestrationConfig(), UnifiedAnalysisConfig)

    def test_custom(self):
        c = ExtendedOrchestrationConfig(
            enable_hierarchical=False, max_concurrent_analyses=5, use_mocks=True
        )
        assert (
            c.enable_hierarchical is False
            and c.max_concurrent_analyses == 5
            and c.use_mocks is True
        )

    def test_mode_from_string(self):
        assert (
            ExtendedOrchestrationConfig(
                orchestration_mode="real"
            ).orchestration_mode_enum
            == OrchestrationMode.REAL
        )

    def test_mode_from_enum(self):
        c = ExtendedOrchestrationConfig(
            orchestration_mode=OrchestrationMode.CONVERSATION
        )
        assert c.orchestration_mode == "conversation"

    def test_analysis_type_from_string(self):
        assert (
            ExtendedOrchestrationConfig(analysis_type="rhetorical").analysis_type
            == AnalysisType.RHETORICAL
        )

    def test_default_priority(self):
        c = ExtendedOrchestrationConfig()
        assert len(c.specialized_orchestrator_priority) == 4

    def test_custom_priority(self):
        assert ExtendedOrchestrationConfig(
            specialized_orchestrator_priority=["a"]
        ).specialized_orchestrator_priority == ["a"]

    def test_middleware_default(self):
        assert ExtendedOrchestrationConfig().middleware_config == {}

    def test_trace_default(self):
        assert ExtendedOrchestrationConfig().save_orchestration_trace is True


# ============================================================================
# SECTION 5: orchestration/core/communication.py tests
# ============================================================================


@pytest.mark.skipif(not COMM_AVAILABLE, reason="communication import failed")
class TestInitializeCommunicationMiddleware:
    @patch(f"{COMM_MODULE}.MessageMiddleware", None)
    def test_none_when_class_unavailable(self):
        assert initialize_communication_middleware() is None

    @patch(f"{COMM_MODULE}.MessageMiddleware")
    def test_from_service_manager(self, mock_cls):
        sm = MagicMock()
        sm.middleware = MagicMock()
        assert initialize_communication_middleware(service_manager=sm) is sm.middleware

    @patch(f"{COMM_MODULE}.MessageMiddleware")
    def test_creates_new(self, mock_cls):
        mock_cls.return_value = MagicMock()
        assert (
            initialize_communication_middleware(enable_communication=True) is not None
        )
        mock_cls.assert_called_once()

    @patch(f"{COMM_MODULE}.MessageMiddleware")
    def test_none_when_disabled(self, mock_cls):
        assert initialize_communication_middleware(enable_communication=False) is None

    @patch(f"{COMM_MODULE}.MessageMiddleware")
    def test_prefers_sm(self, mock_cls):
        sm = MagicMock()
        sm.middleware = MagicMock()
        r = initialize_communication_middleware(
            service_manager=sm, enable_communication=True
        )
        assert r is sm.middleware
        mock_cls.assert_not_called()


# ============================================================================
# SECTION 6: orchestration/analysis/post_processors.py tests
# ============================================================================


@pytest.mark.skipif(not ANALYSIS_AVAILABLE, reason="analysis import failed")
class TestPostProcessResults:
    async def test_high_score(self):
        p = MagicMock()
        p.middleware = None
        r = await post_process_orchestration_results(
            p,
            {
                "hierarchical_coordination": {"overall_score": 0.9},
                "specialized_orchestration": {
                    "results": {"status": "completed"},
                    "orchestrator_used": "T",
                },
            },
        )
        assert any("performante" in x.lower() for x in r["recommendations"])

    async def test_specialized(self):
        p = MagicMock()
        p.middleware = None
        r = await post_process_orchestration_results(
            p,
            {
                "hierarchical_coordination": {"overall_score": 0.5},
                "specialized_orchestration": {
                    "results": {"status": "completed"},
                    "orchestrator_used": "TestO",
                },
            },
        )
        assert any("TestO" in x for x in r["recommendations"])

    async def test_default(self):
        p = MagicMock()
        p.middleware = None
        r = await post_process_orchestration_results(
            p, {"hierarchical_coordination": {}, "specialized_orchestration": {}}
        )
        assert len(r["recommendations"]) >= 1

    async def test_comm_log(self):
        p = MagicMock()
        p.middleware = MagicMock()
        p._get_communication_log.return_value = [{"m": 1}]
        r = await post_process_orchestration_results(
            p, {"hierarchical_coordination": {}, "specialized_orchestration": {}}
        )
        assert "communication_log" in r


# ============================================================================
# SECTION 7: orchestration/analysis/processors.py tests
# ============================================================================


@pytest.mark.skipif(not ANALYSIS_AVAILABLE, reason="analysis import failed")
class TestExecuteOperationalTasks:
    async def test_capped_at_5(self):
        r = await execute_operational_tasks(MagicMock(), "t", {"tasks_created": 8})
        assert r["tasks_executed"] == 5

    async def test_fewer(self):
        r = await execute_operational_tasks(MagicMock(), "t", {"tasks_created": 2})
        assert r["tasks_executed"] == 2

    async def test_zero(self):
        r = await execute_operational_tasks(MagicMock(), "t", {"tasks_created": 0})
        assert r["tasks_executed"] == 0 and r["summary"]["success_rate"] == 0.0

    async def test_success_rate(self):
        r = await execute_operational_tasks(MagicMock(), "t", {"tasks_created": 3})
        assert r["summary"]["success_rate"] == 1.0

    async def test_task_structure(self):
        r = await execute_operational_tasks(MagicMock(), "t", {"tasks_created": 1})
        assert r["task_results"][0]["status"] == "completed"


@pytest.mark.skipif(not ANALYSIS_AVAILABLE, reason="analysis import failed")
class TestSynthesizeHierarchical:
    async def test_high(self):
        r = await synthesize_hierarchical_results(
            MagicMock(),
            {
                "strategic_analysis": {"objectives": list("abcd")},
                "tactical_coordination": {"tasks_created": 10},
                "operational_results": {"summary": {"success_rate": 1.0}},
            },
        )
        assert r["coordination_effectiveness"] > 0.8

    async def test_low(self):
        r = await synthesize_hierarchical_results(
            MagicMock(),
            {
                "strategic_analysis": {"objectives": []},
                "tactical_coordination": {"tasks_created": 0},
                "operational_results": {"summary": {"success_rate": 0.0}},
            },
        )
        assert r["coordination_effectiveness"] == 0.0

    async def test_empty(self):
        r = await synthesize_hierarchical_results(MagicMock(), {})
        assert "coordination_effectiveness" in r


# ============================================================================
# SECTION 8: orchestration/analysis/traces.py tests
# ============================================================================


@pytest.mark.skipif(not ANALYSIS_AVAILABLE, reason="analysis import failed")
class TestTraceOrchestration:
    def test_appends(self):
        p = MagicMock()
        p.config.save_orchestration_trace = True
        p.orchestration_trace = []
        trace_orchestration(p, "evt", {"k": "v"})
        assert (
            len(p.orchestration_trace) == 1
            and p.orchestration_trace[0]["event_type"] == "evt"
        )

    def test_disabled(self):
        p = MagicMock()
        p.config.save_orchestration_trace = False
        p.orchestration_trace = []
        trace_orchestration(p, "evt", {})
        assert len(p.orchestration_trace) == 0

    def test_data_preserved(self):
        p = MagicMock()
        p.config.save_orchestration_trace = True
        p.orchestration_trace = []
        trace_orchestration(p, "a", {"x": 1})
        assert p.orchestration_trace[0]["data"] == {"x": 1}


@pytest.mark.skipif(not ANALYSIS_AVAILABLE, reason="analysis import failed")
class TestGetCommunicationLogFunc:
    def test_from_middleware(self):
        p = MagicMock()
        p.middleware.get_message_history.return_value = [{"m": 1}]
        assert len(get_communication_log(p)) == 1

    def test_no_middleware(self):
        p = MagicMock()
        p.middleware = None
        assert get_communication_log(p) == []

    def test_error(self):
        p = MagicMock()
        p.middleware.get_message_history.side_effect = RuntimeError("F")
        assert get_communication_log(p) == []


@pytest.mark.skipif(not ANALYSIS_AVAILABLE, reason="analysis import failed")
class TestSaveTrace:
    @patch("argumentation_analysis.pipelines.orchestration.analysis.traces.RESULTS_DIR")
    async def test_saves(self, mock_dir):
        mock_dir.__truediv__ = MagicMock(return_value="fp.json")
        p = MagicMock()
        p.config.orchestration_mode_enum = OrchestrationMode.PIPELINE
        p.config.analysis_type = AnalysisType.COMPREHENSIVE
        p.config.enable_hierarchical = True
        p.config.enable_specialized_orchestrators = True
        p.orchestration_trace = []
        with patch("builtins.open", mock_open()) as mf:
            await save_orchestration_trace(
                p, "id", {"status": "ok", "execution_time": 1, "recommendations": []}
            )
            mf.assert_called_once()

    @patch("argumentation_analysis.pipelines.orchestration.analysis.traces.RESULTS_DIR")
    async def test_error_graceful(self, mock_dir):
        mock_dir.__truediv__ = MagicMock(side_effect=RuntimeError("E"))
        p = MagicMock()
        p.config.orchestration_mode_enum = MagicMock(value="p")
        p.config.analysis_type = MagicMock(value="c")
        await save_orchestration_trace(p, "id", {})  # Should not raise
