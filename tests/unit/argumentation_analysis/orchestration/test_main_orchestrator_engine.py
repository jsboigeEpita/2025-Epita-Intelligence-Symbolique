# tests/unit/argumentation_analysis/orchestration/test_main_orchestrator_engine.py
"""Tests for MainOrchestrator — central orchestration engine."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from argumentation_analysis.orchestration.engine.main_orchestrator import (
    MainOrchestrator,
)
from argumentation_analysis.orchestration.engine.strategy import OrchestrationStrategy
from argumentation_analysis.orchestration.engine.config import OrchestrationConfig


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_kernel():
    return MagicMock()


@pytest.fixture
def mock_config():
    return OrchestrationConfig()


@pytest.fixture
def mock_strategic():
    m = MagicMock()
    m.initialize_analysis.return_value = {"objectives": ["obj1", "obj2"]}
    return m


@pytest.fixture
def mock_tactical():
    m = MagicMock()
    m.process_strategic_objectives.return_value = {"tasks_created": 5, "tasks": []}
    return m


@pytest.fixture
def mock_operational():
    return MagicMock()


@pytest.fixture
def orchestrator(mock_config, mock_kernel):
    """MainOrchestrator with mocked DirectOperationalExecutor."""
    with patch(
        "argumentation_analysis.orchestration.engine.main_orchestrator.DirectOperationalExecutor",
        create=True,
    ):
        with patch(
            "argumentation_analysis.orchestration.operational.direct_executor.DirectOperationalExecutor",
            create=True,
        ):
            orch = MainOrchestrator(config=mock_config, kernel=mock_kernel)
            orch.direct_operational_executor = MagicMock()
            orch.specialized_orchestrators_map = {}
            return orch


@pytest.fixture
def full_orchestrator(mock_config, mock_kernel, mock_strategic, mock_tactical, mock_operational):
    """MainOrchestrator with all managers configured."""
    with patch(
        "argumentation_analysis.orchestration.engine.main_orchestrator.DirectOperationalExecutor",
        create=True,
    ):
        with patch(
            "argumentation_analysis.orchestration.operational.direct_executor.DirectOperationalExecutor",
            create=True,
        ):
            orch = MainOrchestrator(
                config=mock_config,
                kernel=mock_kernel,
                strategic_manager=mock_strategic,
                tactical_coordinator=mock_tactical,
                operational_manager=mock_operational,
            )
            orch.direct_operational_executor = MagicMock()
            orch.direct_operational_executor.execute_operational_pipeline = AsyncMock(
                return_value={"status": "success", "summary": {"success_rate": 0.9}}
            )
            orch.specialized_orchestrators_map = {}
            return orch


# ── __init__ ────────────────────────────────────────────────────────────

class TestMainOrchestratorInit:
    """Tests for MainOrchestrator.__init__."""

    def test_stores_config(self, orchestrator, mock_config):
        assert orchestrator.config is mock_config

    def test_stores_kernel(self, orchestrator, mock_kernel):
        assert orchestrator.kernel is mock_kernel

    def test_optional_managers_none_by_default(self, orchestrator):
        assert orchestrator.strategic_manager is None
        assert orchestrator.tactical_coordinator is None
        assert orchestrator.operational_manager is None

    def test_managers_stored(self, full_orchestrator, mock_strategic, mock_tactical, mock_operational):
        assert full_orchestrator.strategic_manager is mock_strategic
        assert full_orchestrator.tactical_coordinator is mock_tactical
        assert full_orchestrator.operational_manager is mock_operational

    def test_direct_executor_set(self, orchestrator):
        assert orchestrator.direct_operational_executor is not None


# ── run_analysis ────────────────────────────────────────────────────────

class TestRunAnalysis:
    """Tests for run_analysis() strategy dispatch."""

    @pytest.mark.parametrize("strategy,method_name", [
        (OrchestrationStrategy.HIERARCHICAL_FULL, "_execute_hierarchical_full"),
        (OrchestrationStrategy.STRATEGIC_ONLY, "_execute_strategic_only"),
        (OrchestrationStrategy.TACTICAL_COORDINATION, "_execute_tactical_coordination"),
        (OrchestrationStrategy.OPERATIONAL_DIRECT, "_execute_operational_direct"),
        (OrchestrationStrategy.SPECIALIZED_DIRECT, "_execute_specialized_direct"),
        (OrchestrationStrategy.HYBRID, "_execute_hybrid"),
        (OrchestrationStrategy.SERVICE_MANAGER, "_execute_service_manager"),
        (OrchestrationStrategy.FALLBACK, "_execute_fallback"),
        (OrchestrationStrategy.COMPLEX_PIPELINE, "_execute_complex_pipeline"),
        (OrchestrationStrategy.MANUAL_SELECTION, "_execute_manual_selection"),
    ])
    async def test_dispatches_to_correct_method(self, orchestrator, strategy, method_name):
        expected = {"status": "success", "test": True}
        with patch(
            "argumentation_analysis.orchestration.engine.main_orchestrator.select_strategy",
            new_callable=AsyncMock,
            return_value=strategy,
        ):
            with patch.object(orchestrator, method_name, new_callable=AsyncMock, return_value=expected) as mock_method:
                result = await orchestrator.run_analysis("sample text")
                mock_method.assert_called_once_with("sample text")
                assert result == expected


# ── _execute_fallback ───────────────────────────────────────────────────

class TestExecuteFallback:
    """Tests for _execute_fallback()."""

    async def test_returns_fallback_status(self, orchestrator):
        result = await orchestrator._execute_fallback("some text")
        assert result["status"] == "fallback_activated"
        assert result["strategy_used"] == OrchestrationStrategy.FALLBACK.value

    async def test_truncates_long_text(self, orchestrator):
        long_text = "a" * 200
        result = await orchestrator._execute_fallback(long_text)
        assert result["input_text_snippet"].endswith("...")
        assert len(result["input_text_snippet"]) == 103  # 100 + "..."

    async def test_short_text_preserved(self, orchestrator):
        result = await orchestrator._execute_fallback("short")
        assert result["input_text_snippet"] == "short"


# ── _execute_complex_pipeline ───────────────────────────────────────────

class TestExecuteComplexPipeline:
    """Tests for _execute_complex_pipeline()."""

    async def test_returns_success(self, orchestrator):
        result = await orchestrator._execute_complex_pipeline("text")
        assert result["status"] == "success"
        assert result["strategy_used"] == OrchestrationStrategy.COMPLEX_PIPELINE.value


# ── _execute_manual_selection ───────────────────────────────────────────

class TestExecuteManualSelection:
    """Tests for _execute_manual_selection()."""

    async def test_returns_success(self, orchestrator):
        result = await orchestrator._execute_manual_selection("text")
        assert result["status"] == "success"
        assert result["strategy_used"] == OrchestrationStrategy.MANUAL_SELECTION.value


# ── _synthesize_hierarchical_results ────────────────────────────────────

class TestSynthesizeHierarchicalResults:
    """Tests for _synthesize_hierarchical_results()."""

    async def test_empty_results(self, orchestrator):
        result = await orchestrator._synthesize_hierarchical_results({})
        assert result["overall_score"] == 0.0
        assert result["strategic_alignment"] == 0.0

    async def test_strategic_alignment(self, orchestrator):
        results = {"strategic_analysis": {"objectives": ["o1", "o2"]}}
        synthesis = await orchestrator._synthesize_hierarchical_results(results)
        assert synthesis["strategic_alignment"] == pytest.approx(0.5)  # 2/4

    async def test_strategic_alignment_capped(self, orchestrator):
        results = {"strategic_analysis": {"objectives": ["o1", "o2", "o3", "o4", "o5"]}}
        synthesis = await orchestrator._synthesize_hierarchical_results(results)
        assert synthesis["strategic_alignment"] == 1.0

    async def test_tactical_efficiency(self, orchestrator):
        results = {"tactical_coordination": {"tasks_created": 5}}
        synthesis = await orchestrator._synthesize_hierarchical_results(results)
        assert synthesis["tactical_efficiency"] == pytest.approx(0.5)  # 5/10

    async def test_operational_success(self, orchestrator):
        results = {"operational_results": {"summary": {"success_rate": 0.9}}}
        synthesis = await orchestrator._synthesize_hierarchical_results(results)
        assert synthesis["operational_success"] == 0.9

    async def test_overall_score_average(self, orchestrator):
        results = {
            "strategic_analysis": {"objectives": ["o1", "o2", "o3", "o4"]},  # alignment=1.0
            "tactical_coordination": {"tasks_created": 10},  # efficiency=1.0
            "operational_results": {"summary": {"success_rate": 1.0}},  # success=1.0
        }
        synthesis = await orchestrator._synthesize_hierarchical_results(results)
        assert synthesis["overall_score"] == pytest.approx(1.0)

    async def test_high_score_recommendation(self, orchestrator):
        results = {
            "strategic_analysis": {"objectives": ["o1", "o2", "o3", "o4"]},
            "tactical_coordination": {"tasks_created": 10},
            "operational_results": {"summary": {"success_rate": 1.0}},
        }
        synthesis = await orchestrator._synthesize_hierarchical_results(results)
        assert any("efficace" in r for r in synthesis["recommendations"])

    async def test_low_score_recommendation(self, orchestrator):
        results = {}
        synthesis = await orchestrator._synthesize_hierarchical_results(results)
        assert any("améliorer" in r for r in synthesis["recommendations"])

    async def test_mid_score_recommendation(self, orchestrator):
        results = {
            "strategic_analysis": {"objectives": ["o1", "o2", "o3"]},  # 0.75
            "tactical_coordination": {"tasks_created": 7},  # 0.7
            "operational_results": {"summary": {"success_rate": 0.5}},  # 0.5
        }
        synthesis = await orchestrator._synthesize_hierarchical_results(results)
        # average ~0.65 → satisfaisante
        assert any("satisfaisante" in r for r in synthesis["recommendations"])

    async def test_exception_handled(self, orchestrator):
        # Provide data that causes an error (None in objectives list)
        results = {"strategic_analysis": None}
        synthesis = await orchestrator._synthesize_hierarchical_results(results)
        # Should not crash — either error key or 0 scores
        assert isinstance(synthesis, dict)


# ── _execute_operational_tasks ──────────────────────────────────────────

class TestExecuteOperationalTasks:
    """Tests for _execute_operational_tasks()."""

    async def test_no_executor_returns_error(self, orchestrator):
        orchestrator.direct_operational_executor = None
        result = await orchestrator._execute_operational_tasks("text", {})
        assert result["status"] == "error"
        assert result["tasks_executed"] == 0

    async def test_delegates_to_executor(self, full_orchestrator):
        result = await full_orchestrator._execute_operational_tasks("text", {"tasks": []})
        full_orchestrator.direct_operational_executor.execute_operational_pipeline.assert_called_once()
        assert result["status"] == "success"

    async def test_executor_exception(self, full_orchestrator):
        full_orchestrator.direct_operational_executor.execute_operational_pipeline = AsyncMock(
            side_effect=RuntimeError("executor crashed")
        )
        result = await full_orchestrator._execute_operational_tasks("text", {})
        assert result["status"] == "error"
        assert "executor crashed" in result["error_message"]


# ── _execute_hierarchical_full ──────────────────────────────────────────

class TestExecuteHierarchicalFull:
    """Tests for _execute_hierarchical_full()."""

    async def test_no_managers_returns_success(self, orchestrator):
        # No strategic/tactical/operational managers → still succeeds with empty results
        result = await orchestrator._execute_hierarchical_full("test text")
        assert result["status"] == "success"

    async def test_with_all_managers(self, full_orchestrator):
        result = await full_orchestrator._execute_hierarchical_full("analyze this")
        assert result["status"] == "success"
        assert "strategic_analysis" in result
        assert "tactical_coordination" in result
        assert "operational_results" in result

    async def test_strategic_error(self, full_orchestrator, mock_strategic):
        mock_strategic.initialize_analysis.side_effect = RuntimeError("strategic fail")
        result = await full_orchestrator._execute_hierarchical_full("text")
        assert result["status"] == "error"

    async def test_text_snippet_in_result(self, orchestrator):
        result = await orchestrator._execute_hierarchical_full("short")
        assert result["input_text_snippet"] == "short"

    async def test_long_text_truncated(self, orchestrator):
        long_text = "x" * 200
        result = await orchestrator._execute_hierarchical_full(long_text)
        assert result["input_text_snippet"].endswith("...")


# ── _execute_strategic_only ─────────────────────────────────────────────

class TestExecuteStrategicOnly:
    """Tests for _execute_strategic_only()."""

    async def test_no_manager_returns_error(self, orchestrator):
        result = await orchestrator._execute_strategic_only("text")
        assert result["status"] == "error"
        assert "non configuré" in result.get("error_message", "")

    async def test_with_manager_success(self, orchestrator):
        mock_mgr = AsyncMock()
        mock_mgr.initialize_analysis.return_value = {"objectives": ["o1"]}
        orchestrator.config.strategic_manager_instance = mock_mgr
        result = await orchestrator._execute_strategic_only("text")
        assert result["status"] == "success"

    async def test_with_manager_no_objectives(self, orchestrator):
        mock_mgr = AsyncMock()
        mock_mgr.initialize_analysis.return_value = {"other": "data"}
        orchestrator.config.strategic_manager_instance = mock_mgr
        result = await orchestrator._execute_strategic_only("text")
        assert result["status"] == "partial_failure"


# ── _execute_tactical_coordination ──────────────────────────────────────

class TestExecuteTacticalCoordination:
    """Tests for _execute_tactical_coordination()."""

    async def test_missing_managers_error(self, orchestrator):
        result = await orchestrator._execute_tactical_coordination("text")
        assert result["status"] == "error"

    async def test_both_managers_success(self, orchestrator):
        strat = AsyncMock()
        strat.initialize_analysis.return_value = {"objectives": ["o1"]}
        tact = AsyncMock()
        tact.process_strategic_objectives.return_value = {"tasks": []}
        orchestrator.config.strategic_manager_instance = strat
        orchestrator.config.tactical_coordinator_instance = tact
        result = await orchestrator._execute_tactical_coordination("text")
        assert result["status"] == "success"

    async def test_no_objectives_partial_failure(self, orchestrator):
        strat = AsyncMock()
        strat.initialize_analysis.return_value = {"no_objectives": True}
        tact = AsyncMock()
        orchestrator.config.strategic_manager_instance = strat
        orchestrator.config.tactical_coordinator_instance = tact
        result = await orchestrator._execute_tactical_coordination("text")
        assert result["status"] == "partial_failure"


# ── _execute_operational_direct ─────────────────────────────────────────

class TestExecuteOperationalDirect:
    """Tests for _execute_operational_direct()."""

    async def test_missing_components_error(self, orchestrator):
        result = await orchestrator._execute_operational_direct("text")
        assert result["status"] == "error"
        assert "Configuration incomplète" in result.get("error_message", "")

    async def test_full_pipeline(self, full_orchestrator):
        result = await full_orchestrator._execute_operational_direct("analyze this")
        assert result["status"] == "success"

    async def test_exception_handled(self, full_orchestrator, mock_strategic):
        mock_strategic.initialize_analysis.side_effect = Exception("boom")
        result = await full_orchestrator._execute_operational_direct("text")
        assert result["status"] == "error"


# ── _execute_service_manager ────────────────────────────────────────────

class TestExecuteServiceManager:
    """Tests for _execute_service_manager()."""

    async def test_no_service_manager(self, orchestrator):
        orchestrator.config = MagicMock()
        orchestrator.config.get.return_value = None
        result = await orchestrator._execute_service_manager("text")
        assert result["status"] == "error"

    async def test_with_service_manager(self, orchestrator):
        mock_sm = AsyncMock()
        mock_sm.get_services_status.return_value = {"services": "ok"}
        orchestrator.config = MagicMock()
        orchestrator.config.get.return_value = mock_sm
        result = await orchestrator._execute_service_manager("text")
        assert result["status"] == "success"
        assert result["service_status_report"]["services"] == "ok"

    async def test_attribute_error(self, orchestrator):
        orchestrator.config = MagicMock()
        orchestrator.config.get.side_effect = AttributeError("no get")
        result = await orchestrator._execute_service_manager("text")
        assert result["status"] == "error"


# ── _execute_hybrid ─────────────────────────────────────────────────────

class TestExecuteHybrid:
    """Tests for _execute_hybrid()."""

    async def test_both_succeed(self, orchestrator):
        with patch.object(orchestrator, "_execute_tactical_coordination", new_callable=AsyncMock,
                          return_value={"status": "success"}):
            with patch.object(orchestrator, "_execute_specialized_direct", new_callable=AsyncMock,
                              return_value={"status": "success"}):
                result = await orchestrator._execute_hybrid("text")
                assert result["status"] == "success"

    async def test_one_fails_partial(self, orchestrator):
        with patch.object(orchestrator, "_execute_tactical_coordination", new_callable=AsyncMock,
                          return_value={"status": "error", "error_message": "fail"}):
            with patch.object(orchestrator, "_execute_specialized_direct", new_callable=AsyncMock,
                              return_value={"status": "success"}):
                result = await orchestrator._execute_hybrid("text")
                assert result["status"] == "partial_failure"

    async def test_both_fail(self, orchestrator):
        with patch.object(orchestrator, "_execute_tactical_coordination", new_callable=AsyncMock,
                          return_value={"status": "error", "error_message": "f1"}):
            with patch.object(orchestrator, "_execute_specialized_direct", new_callable=AsyncMock,
                              return_value={"status": "error", "error_message": "f2"}):
                result = await orchestrator._execute_hybrid("text")
                assert result["status"] == "error"


# ── _select_specialized_orchestrator ────────────────────────────────────

class TestSelectSpecializedOrchestrator:
    """Tests for _select_specialized_orchestrator()."""

    async def test_empty_map_returns_none(self, orchestrator):
        orchestrator.specialized_orchestrators_map = {}
        result = await orchestrator._select_specialized_orchestrator()
        assert result is None

    async def test_returns_highest_priority(self, orchestrator):
        orchestrator.specialized_orchestrators_map = {
            "low": {"priority": 10, "orchestrator": MagicMock(), "types": []},
            "high": {"priority": 1, "orchestrator": MagicMock(), "types": []},
        }
        name, data = await orchestrator._select_specialized_orchestrator()
        assert name == "high"

    async def test_filters_by_analysis_type(self, orchestrator):
        from argumentation_analysis.core.enums import AnalysisType
        orchestrator.config.analysis_type_enum = AnalysisType.LOGICAL
        orchestrator.specialized_orchestrators_map = {
            "logic": {"priority": 2, "orchestrator": MagicMock(), "types": [AnalysisType.LOGICAL]},
            "other": {"priority": 1, "orchestrator": MagicMock(), "types": [AnalysisType.RHETORICAL]},
        }
        name, data = await orchestrator._select_specialized_orchestrator()
        assert name == "logic"


# ── _execute_specialized_direct ─────────────────────────────────────────

class TestExecuteSpecializedDirect:
    """Tests for _execute_specialized_direct()."""

    async def test_no_orchestrator_selected(self, orchestrator):
        with patch.object(orchestrator, "_select_specialized_orchestrator", new_callable=AsyncMock, return_value=None):
            result = await orchestrator._execute_specialized_direct("text")
            assert result["status"] == "no_orchestrator_selected"

    async def test_missing_orchestrator_instance(self, orchestrator):
        with patch.object(orchestrator, "_select_specialized_orchestrator", new_callable=AsyncMock,
                          return_value=("test", {"orchestrator": None, "priority": 1})):
            result = await orchestrator._execute_specialized_direct("text")
            assert result["status"] == "error"

    async def test_exception_handled(self, orchestrator):
        with patch.object(orchestrator, "_select_specialized_orchestrator", new_callable=AsyncMock,
                          side_effect=RuntimeError("boom")):
            result = await orchestrator._execute_specialized_direct("text")
            assert result["status"] == "error"


# ── _run_logic_complex_analysis ─────────────────────────────────────────

class TestRunLogicComplexAnalysis:
    """Tests for _run_logic_complex_analysis()."""

    async def test_no_method(self, orchestrator):
        mock_orch = MagicMock(spec=[])
        # LogiqueComplexeOrchestrator might not be available
        with patch("argumentation_analysis.orchestration.engine.main_orchestrator.LogiqueComplexeOrchestrator", None):
            result = await orchestrator._run_logic_complex_analysis("text", mock_orch)
            assert result["status"] == "limited"

    async def test_exception(self, orchestrator):
        mock_orch = MagicMock()
        mock_orch.analyze_complex_logic = AsyncMock(side_effect=Exception("logic error"))
        with patch("argumentation_analysis.orchestration.engine.main_orchestrator.LogiqueComplexeOrchestrator", type(mock_orch)):
            result = await orchestrator._run_logic_complex_analysis("text", mock_orch)
            assert result["status"] == "error"


# ── Integration scenarios ───────────────────────────────────────────────

class TestMainOrchestratorScenarios:
    """Integration scenarios."""

    async def test_fallback_strategy_end_to_end(self, orchestrator):
        with patch(
            "argumentation_analysis.orchestration.engine.main_orchestrator.select_strategy",
            new_callable=AsyncMock,
            return_value=OrchestrationStrategy.FALLBACK,
        ):
            result = await orchestrator.run_analysis("any text")
            assert result["status"] == "fallback_activated"

    async def test_hierarchical_with_full_stack(self, full_orchestrator):
        with patch(
            "argumentation_analysis.orchestration.engine.main_orchestrator.select_strategy",
            new_callable=AsyncMock,
            return_value=OrchestrationStrategy.HIERARCHICAL_FULL,
        ):
            result = await full_orchestrator.run_analysis("analyze this deeply")
            assert result["status"] == "success"
            assert "hierarchical_coordination" in result
