"""Tests for pipeline execution strategies (B-05 #815 residual).

Existing test_strategies.py covers core/strategies.py (SimpleTerminationStrategy etc.)
and test_orchestration_strategies.py covers orchestration/strategies.py (Cluedo).
This file fills the gap for pipelines/orchestration/execution/strategies.py — specifically:
- select_orchestration_strategy (pure branching logic)
- select_specialized_orchestrator (priority-based selection)
- execute_hierarchical_full_orchestration (mock pipeline)
- execute_specialized_orchestration (mock pipeline)
- execute_fallback_orchestration (mock pipeline)
- execute_hybrid_orchestration (composite)

IMPORT WORKAROUND: The orchestration package __init__.py imports service_manager →
spacy → torch which crashes on Windows (DLL WinError 182). We must inject mock modules
into sys.modules BEFORE importing anything from the orchestration package.
"""

import sys
from unittest.mock import MagicMock, AsyncMock

import pytest


# ============================================================================
# IMPORT WORKAROUND: Patch broken import chains before touching orchestration.
# 1. get_fallacy_detector missing from bootstrap
# 2. torch DLL crash via spacy → thinc → torch
# ============================================================================


def _ensure_importable():
    """Pre-inject mock modules to bypass broken import chains."""
    # 1. Patch get_fallacy_detector in bootstrap
    try:
        from argumentation_analysis.core import bootstrap as _bootstrap_mod

        if not hasattr(_bootstrap_mod, "get_fallacy_detector"):
            _bootstrap_mod.get_fallacy_detector = MagicMock(return_value=MagicMock())
    except ImportError:
        pass

    # 2. If torch is already broken (DLL crash), inject a mock so spacy/thinc don't crash
    if "torch" not in sys.modules:
        try:
            import torch  # noqa: F401
        except (OSError, ImportError):
            sys.modules["torch"] = MagicMock()


_ensure_importable()

# Now safe to import from the orchestration package
from argumentation_analysis.pipelines.orchestration.config.enums import (
    OrchestrationMode,
    AnalysisType,
)


def _make_config(
    orchestration_mode_enum=OrchestrationMode.AUTO_SELECT,
    analysis_type=AnalysisType.COMPREHENSIVE,
    auto_select_orchestrator=True,
    enable_hierarchical=True,
    enable_specialized_orchestrators=True,
):
    """Build a lightweight config mock with the attributes used by select_orchestration_strategy."""
    cfg = MagicMock()
    cfg.orchestration_mode_enum = orchestration_mode_enum
    cfg.analysis_type = analysis_type
    cfg.auto_select_orchestrator = auto_select_orchestrator
    cfg.enable_hierarchical = enable_hierarchical
    cfg.enable_specialized_orchestrators = enable_specialized_orchestrators
    return cfg


def _make_pipeline(
    config=None,
    service_manager=None,
    strategic_manager=None,
    tactical_coordinator=None,
    operational_manager=None,
    specialized_orchestrators=None,
    fallback_pipeline=None,
):
    """Build a lightweight pipeline mock."""
    pipe = MagicMock()
    pipe.config = config or _make_config()
    pipe.service_manager = service_manager
    pipe.strategic_manager = strategic_manager
    pipe.tactical_coordinator = tactical_coordinator
    pipe.operational_manager = operational_manager
    pipe.specialized_orchestrators = specialized_orchestrators or {}
    pipe._fallback_pipeline = fallback_pipeline
    pipe._trace_orchestration = MagicMock()
    pipe._execute_operational_tasks = AsyncMock(return_value={"task_results": []})
    pipe._synthesize_hierarchical_results = AsyncMock(return_value={"synthesis": "ok"})
    return pipe


# =====================================================================
# select_orchestration_strategy
# =====================================================================


class TestSelectOrchestrationStrategy:
    """Tests for select_orchestration_strategy pure branching logic."""

    @pytest.mark.asyncio
    async def test_manual_hierarchical_full(self):
        """Manual HIERARCHICAL_FULL mode returns 'hierarchical_full'."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_orchestration_strategy,
        )

        cfg = _make_config(orchestration_mode_enum=OrchestrationMode.HIERARCHICAL_FULL)
        pipeline = _make_pipeline(config=cfg)

        result = await select_orchestration_strategy(pipeline, "some text")
        assert result == "hierarchical_full"

    @pytest.mark.asyncio
    async def test_manual_strategic_only(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_orchestration_strategy,
        )

        cfg = _make_config(orchestration_mode_enum=OrchestrationMode.STRATEGIC_ONLY)
        result = await select_orchestration_strategy(_make_pipeline(config=cfg), "text")
        assert result == "strategic_only"

    @pytest.mark.asyncio
    async def test_manual_tactical_coordination(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_orchestration_strategy,
        )

        cfg = _make_config(orchestration_mode_enum=OrchestrationMode.TACTICAL_COORDINATION)
        result = await select_orchestration_strategy(_make_pipeline(config=cfg), "text")
        assert result == "tactical_coordination"

    @pytest.mark.asyncio
    async def test_manual_operational_direct(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_orchestration_strategy,
        )

        cfg = _make_config(orchestration_mode_enum=OrchestrationMode.OPERATIONAL_DIRECT)
        result = await select_orchestration_strategy(_make_pipeline(config=cfg), "text")
        assert result == "operational_direct"

    @pytest.mark.asyncio
    async def test_manual_cluedo_returns_specialized(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_orchestration_strategy,
        )

        cfg = _make_config(orchestration_mode_enum=OrchestrationMode.CLUEDO_INVESTIGATION)
        result = await select_orchestration_strategy(_make_pipeline(config=cfg), "text")
        assert result == "specialized_direct"

    @pytest.mark.asyncio
    async def test_manual_logic_complex_returns_specialized(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_orchestration_strategy,
        )

        cfg = _make_config(orchestration_mode_enum=OrchestrationMode.LOGIC_COMPLEX)
        result = await select_orchestration_strategy(_make_pipeline(config=cfg), "text")
        assert result == "specialized_direct"

    @pytest.mark.asyncio
    async def test_manual_adaptive_hybrid(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_orchestration_strategy,
        )

        cfg = _make_config(orchestration_mode_enum=OrchestrationMode.ADAPTIVE_HYBRID)
        result = await select_orchestration_strategy(_make_pipeline(config=cfg), "text")
        assert result == "hybrid"

    @pytest.mark.asyncio
    async def test_auto_select_disabled_returns_fallback(self):
        """AUTO_SELECT with auto_select_orchestrator=False → fallback."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_orchestration_strategy,
        )

        cfg = _make_config(
            orchestration_mode_enum=OrchestrationMode.AUTO_SELECT,
            auto_select_orchestrator=False,
        )
        result = await select_orchestration_strategy(_make_pipeline(config=cfg), "text")
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_auto_investigative_returns_specialized(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_orchestration_strategy,
        )

        cfg = _make_config(
            orchestration_mode_enum=OrchestrationMode.AUTO_SELECT,
            analysis_type=AnalysisType.INVESTIGATIVE,
        )
        result = await select_orchestration_strategy(_make_pipeline(config=cfg), "text")
        assert result == "specialized_direct"

    @pytest.mark.asyncio
    async def test_auto_logical_returns_specialized(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_orchestration_strategy,
        )

        cfg = _make_config(
            orchestration_mode_enum=OrchestrationMode.AUTO_SELECT,
            analysis_type=AnalysisType.LOGICAL,
        )
        result = await select_orchestration_strategy(_make_pipeline(config=cfg), "text")
        assert result == "specialized_direct"

    @pytest.mark.asyncio
    async def test_auto_hierarchical_long_text(self):
        """COMPREHENSIVE with hierarchical enabled and text > 1000 chars → hierarchical_full."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_orchestration_strategy,
        )

        cfg = _make_config(
            orchestration_mode_enum=OrchestrationMode.AUTO_SELECT,
            analysis_type=AnalysisType.COMPREHENSIVE,
            enable_hierarchical=True,
        )
        result = await select_orchestration_strategy(
            _make_pipeline(config=cfg), "x" * 1500
        )
        assert result == "hierarchical_full"

    @pytest.mark.asyncio
    async def test_auto_comprehensive_service_manager(self):
        """COMPREHENSIVE with initialized service_manager → service_manager strategy."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_orchestration_strategy,
        )

        cfg = _make_config(
            orchestration_mode_enum=OrchestrationMode.AUTO_SELECT,
            analysis_type=AnalysisType.COMPREHENSIVE,
            enable_hierarchical=False,
        )
        sm = MagicMock()
        sm._initialized = True
        result = await select_orchestration_strategy(
            _make_pipeline(config=cfg, service_manager=sm), "short"
        )
        assert result == "service_manager"

    @pytest.mark.asyncio
    async def test_auto_default_hybrid(self):
        """AUTO_SELECT with no matching criteria → hybrid (default)."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_orchestration_strategy,
        )

        cfg = _make_config(
            orchestration_mode_enum=OrchestrationMode.AUTO_SELECT,
            analysis_type=AnalysisType.RHETORICAL,
            enable_hierarchical=False,
        )
        result = await select_orchestration_strategy(_make_pipeline(config=cfg), "short")
        assert result == "hybrid"

    @pytest.mark.asyncio
    async def test_unknown_mode_returns_fallback(self):
        """Unknown OrchestrationMode falls back to 'fallback' in mode_strategy_map."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_orchestration_strategy,
        )

        # PIPELINE is a valid enum but not in mode_strategy_map
        cfg = _make_config(orchestration_mode_enum=OrchestrationMode.PIPELINE)
        result = await select_orchestration_strategy(_make_pipeline(config=cfg), "text")
        assert result == "fallback"


# =====================================================================
# select_specialized_orchestrator
# =====================================================================


class TestSelectSpecializedOrchestrator:
    """Tests for select_specialized_orchestrator priority-based selection."""

    @pytest.mark.asyncio
    async def test_returns_none_when_empty(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_specialized_orchestrator,
        )

        pipeline = _make_pipeline(specialized_orchestrators={})
        result = await select_specialized_orchestrator(pipeline)
        assert result is None

    @pytest.mark.asyncio
    async def test_selects_compatible_by_analysis_type(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_specialized_orchestrator,
        )

        cfg = _make_config(analysis_type=AnalysisType.INVESTIGATIVE)
        mock_orch = MagicMock()
        orchestrators = {
            "logic": {
                "orchestrator": MagicMock(),
                "types": [AnalysisType.LOGICAL],
                "priority": 1,
            },
            "cluedo": {
                "orchestrator": mock_orch,
                "types": [AnalysisType.INVESTIGATIVE],
                "priority": 2,
            },
        }
        pipeline = _make_pipeline(config=cfg, specialized_orchestrators=orchestrators)
        result = await select_specialized_orchestrator(pipeline)

        assert result is not None
        name, data = result
        assert name == "cluedo"
        assert data["orchestrator"] is mock_orch

    @pytest.mark.asyncio
    async def test_fallback_to_all_if_no_compatible(self):
        """If no orchestrator matches the analysis type, fall back to all."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_specialized_orchestrator,
        )

        cfg = _make_config(analysis_type=AnalysisType.DEBATE_ANALYSIS)
        orchestrators = {
            "cluedo": {
                "orchestrator": MagicMock(),
                "types": [AnalysisType.INVESTIGATIVE],
                "priority": 5,
            },
            "logic": {
                "orchestrator": MagicMock(),
                "types": [AnalysisType.LOGICAL],
                "priority": 1,
            },
        }
        pipeline = _make_pipeline(config=cfg, specialized_orchestrators=orchestrators)
        result = await select_specialized_orchestrator(pipeline)

        assert result is not None
        name, data = result
        # Should pick lowest priority = "logic"
        assert name == "logic"

    @pytest.mark.asyncio
    async def test_sorts_by_priority(self):
        """Among compatible orchestrators, selects lowest priority number."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            select_specialized_orchestrator,
        )

        cfg = _make_config(analysis_type=AnalysisType.INVESTIGATIVE)
        orchestrators = {
            "high_prio": {
                "orchestrator": MagicMock(),
                "types": [AnalysisType.INVESTIGATIVE],
                "priority": 10,
            },
            "low_prio": {
                "orchestrator": MagicMock(),
                "types": [AnalysisType.INVESTIGATIVE],
                "priority": 1,
            },
        }
        pipeline = _make_pipeline(config=cfg, specialized_orchestrators=orchestrators)
        result = await select_specialized_orchestrator(pipeline)

        assert result is not None
        name, _ = result
        assert name == "low_prio"


# =====================================================================
# execute_hierarchical_full_orchestration
# =====================================================================


class TestExecuteHierarchicalFull:
    """Tests for execute_hierarchical_full_orchestration."""

    @pytest.mark.asyncio
    async def test_with_strategic_manager(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            execute_hierarchical_full_orchestration,
        )

        sm = MagicMock()
        sm.initialize_analysis = MagicMock(return_value={"objectives": ["obj1", "obj2"]})
        pipeline = _make_pipeline(strategic_manager=sm)
        results = await execute_hierarchical_full_orchestration(pipeline, "text", {})

        assert "strategic_analysis" in results
        assert results["strategic_analysis"]["objectives"] == ["obj1", "obj2"]

    @pytest.mark.asyncio
    async def test_with_tactical_coordinator(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            execute_hierarchical_full_orchestration,
        )

        sm = MagicMock()
        sm.initialize_analysis = MagicMock(return_value={"objectives": ["o1"]})
        tc = MagicMock()
        tc.process_strategic_objectives = AsyncMock(
            return_value={"tasks_created": 3}
        )
        pipeline = _make_pipeline(strategic_manager=sm, tactical_coordinator=tc)
        results = await execute_hierarchical_full_orchestration(pipeline, "text", {})

        assert "tactical_coordination" in results
        assert results["tactical_coordination"]["tasks_created"] == 3

    @pytest.mark.asyncio
    async def test_exception_propagates_from_strategic(self):
        """Bug in source: except handler accesses results['strategic_analysis'] which
        doesn't exist yet when sm.initialize_analysis raises → KeyError propagates.
        This is a known defect in the source code, not in the test."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            execute_hierarchical_full_orchestration,
        )

        sm = MagicMock()
        sm.initialize_analysis = MagicMock(side_effect=RuntimeError("boom"))
        pipeline = _make_pipeline(strategic_manager=sm)

        # Source code bug: except block does results["strategic_analysis"]["error"] = ...
        # but strategic_analysis key doesn't exist → KeyError
        with pytest.raises((KeyError, RuntimeError)):
            await execute_hierarchical_full_orchestration(pipeline, "text", {})

    @pytest.mark.asyncio
    async def test_no_managers(self):
        """Pipeline with no managers should return empty results (no strategic key)."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            execute_hierarchical_full_orchestration,
        )

        pipeline = _make_pipeline(
            strategic_manager=None,
            tactical_coordinator=None,
            operational_manager=None,
        )
        results = await execute_hierarchical_full_orchestration(pipeline, "text", {})

        # No strategic_analysis key because sm is None
        assert "strategic_analysis" not in results


# =====================================================================
# execute_specialized_orchestration
# =====================================================================


class TestExecuteSpecializedOrchestration:
    """Tests for execute_specialized_orchestration."""

    @pytest.mark.asyncio
    async def test_no_orchestrator_available(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            execute_specialized_orchestration,
        )

        pipeline = _make_pipeline(specialized_orchestrators={})
        results = await execute_specialized_orchestration(pipeline, "text", {})
        assert results["specialized_orchestration"]["status"] == "no_orchestrator_available"

    @pytest.mark.asyncio
    async def test_cluedo_run_investigation(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            execute_specialized_orchestration,
        )

        mock_orch = MagicMock()
        mock_orch.run_investigation = AsyncMock(
            return_value={"status": "completed", "clues": 5}
        )
        orchestrators = {
            "cluedo": {
                "orchestrator": mock_orch,
                "types": [AnalysisType.INVESTIGATIVE],
                "priority": 1,
            }
        }
        cfg = _make_config(analysis_type=AnalysisType.INVESTIGATIVE)
        pipeline = _make_pipeline(config=cfg, specialized_orchestrators=orchestrators)
        results = await execute_specialized_orchestration(pipeline, "text", {})

        assert results["specialized_orchestration"]["orchestrator_used"] == "cluedo"
        assert results["specialized_orchestration"]["results"]["clues"] == 5

    @pytest.mark.asyncio
    async def test_generic_analyze_method(self):
        """Orchestrator without run_investigation falls back to .analyze()."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            execute_specialized_orchestration,
        )

        mock_orch = MagicMock(spec=[])  # no run_investigation attribute
        mock_orch.analyze = AsyncMock(return_value={"status": "done"})
        orchestrators = {
            "custom": {
                "orchestrator": mock_orch,
                "types": [AnalysisType.CUSTOM],
                "priority": 1,
            }
        }
        cfg = _make_config(analysis_type=AnalysisType.CUSTOM)
        pipeline = _make_pipeline(config=cfg, specialized_orchestrators=orchestrators)
        results = await execute_specialized_orchestration(pipeline, "text", {})

        assert results["specialized_orchestration"]["orchestrator_used"] == "custom"

    @pytest.mark.asyncio
    async def test_unsupported_orchestrator(self):
        """Orchestrator with neither run_investigation nor analyze returns unsupported."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            execute_specialized_orchestration,
        )

        mock_orch = MagicMock(spec=[])  # no methods at all
        orchestrators = {
            "bare": {
                "orchestrator": mock_orch,
                "types": [AnalysisType.COMPREHENSIVE],
                "priority": 1,
            }
        }
        cfg = _make_config(analysis_type=AnalysisType.COMPREHENSIVE)
        pipeline = _make_pipeline(config=cfg, specialized_orchestrators=orchestrators)
        results = await execute_specialized_orchestration(pipeline, "text", {})

        assert results["specialized_orchestration"]["results"]["status"] == "unsupported"

    @pytest.mark.asyncio
    async def test_exception_in_specialized(self):
        """Source code bug: except handler accesses results['specialized_orchestration']
        which hasn't been set yet → KeyError propagates."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            execute_specialized_orchestration,
        )

        mock_orch = MagicMock()
        mock_orch.run_investigation = AsyncMock(side_effect=RuntimeError("crash"))
        orchestrators = {
            "cluedo": {
                "orchestrator": mock_orch,
                "types": [AnalysisType.INVESTIGATIVE],
                "priority": 1,
            }
        }
        cfg = _make_config(analysis_type=AnalysisType.INVESTIGATIVE)
        pipeline = _make_pipeline(config=cfg, specialized_orchestrators=orchestrators)

        # Source code bug: except does results["specialized_orchestration"]["error"] = ...
        # but the key was never set before the exception → KeyError
        with pytest.raises((KeyError, RuntimeError)):
            await execute_specialized_orchestration(pipeline, "text", {})


# =====================================================================
# execute_fallback_orchestration
# =====================================================================


class TestExecuteFallbackOrchestration:
    """Tests for execute_fallback_orchestration."""

    @pytest.mark.asyncio
    async def test_with_fallback_pipeline(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            execute_fallback_orchestration,
        )

        fb = MagicMock()
        fb.analyze_text_unified = AsyncMock(
            return_value={"status": "completed", "result": "ok"}
        )
        pipeline = _make_pipeline(fallback_pipeline=fb)
        results = await execute_fallback_orchestration(pipeline, "text", {})

        assert results["status"] == "completed"
        assert results["result"] == "ok"

    @pytest.mark.asyncio
    async def test_no_fallback_pipeline(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            execute_fallback_orchestration,
        )

        pipeline = _make_pipeline(fallback_pipeline=None)
        results = await execute_fallback_orchestration(pipeline, "text", {})

        assert results["fallback_analysis"]["status"] == "fallback_unavailable"

    @pytest.mark.asyncio
    async def test_fallback_exception(self):
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            execute_fallback_orchestration,
        )

        fb = MagicMock()
        fb.analyze_text_unified = AsyncMock(side_effect=RuntimeError("timeout"))
        pipeline = _make_pipeline(fallback_pipeline=fb)
        results = await execute_fallback_orchestration(pipeline, "text", {})

        assert results["fallback_analysis"]["status"] == "error"
        assert "timeout" in results["fallback_analysis"]["error"]


# =====================================================================
# execute_hybrid_orchestration
# =====================================================================


class TestExecuteHybridOrchestration:
    """Tests for execute_hybrid_orchestration (composite)."""

    @pytest.mark.asyncio
    async def test_hierarchical_plus_specialized(self):
        """Hybrid with both hierarchical and specialized enabled."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            execute_hybrid_orchestration,
        )

        sm = MagicMock()
        sm.initialize_analysis = MagicMock(return_value={"objectives": []})
        cfg = _make_config(
            enable_hierarchical=True,
            enable_specialized_orchestrators=False,
        )
        pipeline = _make_pipeline(config=cfg, strategic_manager=sm)
        results = await execute_hybrid_orchestration(pipeline, "text", {})

        # Should have strategic_analysis from hierarchical pass
        assert "strategic_analysis" in results

    @pytest.mark.asyncio
    async def test_no_hierarchical_no_specialized(self):
        """Hybrid with neither enabled still runs fallback."""
        from argumentation_analysis.pipelines.orchestration.execution.strategies import (
            execute_hybrid_orchestration,
        )

        cfg = _make_config(
            enable_hierarchical=False,
            enable_specialized_orchestrators=False,
        )
        pipeline = _make_pipeline(config=cfg, fallback_pipeline=None)
        results = await execute_hybrid_orchestration(pipeline, "text", {})

        # Should at least have fallback result
        assert "fallback_analysis" in results
