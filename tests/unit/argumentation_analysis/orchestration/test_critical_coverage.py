"""Coverage improvements for critical orchestration and evaluation modules.

#329 Track 2: Adds tests for uncovered hot-path callables in:
- pipeline_utils.py (edge cases: never-expire, clear, cleanup, metrics context)
- workflows.py (_should_rerun_fallacy, iterative workflow, catalog, reset)
- workflow_dsl.py (condition, input_transform, loop, state writer)
"""

import asyncio
import time

import pytest

from argumentation_analysis.orchestration.pipeline_utils import (
    AnalysisCache,
    CacheEntry,
    PipelineMetrics,
    _MetricsContext,
    BatchRequest,
    BatchResult,
    run_batch_analysis,
)
from argumentation_analysis.orchestration.workflows import (
    _should_rerun_fallacy,
    _increment_fallacy_rerun,
    build_iterative_analysis_workflow,
    build_nl_to_logic_workflow,
    build_quality_gated_counter_workflow,
    build_debate_governance_loop_workflow,
    build_jtms_dung_loop_workflow,
    build_neural_symbolic_fallacy_workflow,
    build_hierarchical_fallacy_workflow,
    get_workflow_catalog,
    reset_workflow_catalog,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowExecutor,
    PhaseStatus,
    LoopConfig,
)
from argumentation_analysis.core.capability_registry import CapabilityRegistry

# ============================================================
# pipeline_utils.py edge cases
# ============================================================


class TestCacheEntryNeverExpires:
    def test_ttl_zero_never_expires(self):
        entry = CacheEntry(value="x", created_at=0, ttl_seconds=0)
        assert not entry.is_expired()

    def test_ttl_negative_never_expires(self):
        entry = CacheEntry(value="x", created_at=0, ttl_seconds=-5)
        assert not entry.is_expired()


class TestAnalysisCacheClear:
    def test_clear_removes_all_entries(self):
        cache = AnalysisCache(ttl_seconds=60)
        cache.set("a", "t1", 1)
        cache.set("b", "t2", 2)
        assert cache.get("a", "t1") == 1
        cache.clear()
        assert cache.get("a", "t1") is None
        assert cache.get("b", "t2") is None


class TestAnalysisCacheCleanup:
    def test_cleanup_expired_removes_old_entries(self):
        cache = AnalysisCache(ttl_seconds=0.05)
        cache.set("old", "type", "stale")
        time.sleep(0.08)
        removed = cache.cleanup_expired()
        assert removed == 1
        assert cache.get("old", "type") is None

    def test_cleanup_keeps_fresh_entries(self):
        cache = AnalysisCache(ttl_seconds=60)
        cache.set("fresh", "type", "ok")
        removed = cache.cleanup_expired()
        assert removed == 0
        assert cache.get("fresh", "type") == "ok"


class TestPipelineMetricsFifo:
    def test_fifo_eviction_at_max_entries(self):
        metrics = PipelineMetrics(max_entries=3)
        for i in range(5):
            metrics.record(f"type{i}", 0.1, True)
        assert metrics.get_summary()["total_analyses"] == 3


class TestMetricsContextManager:
    def test_track_success(self):
        metrics = PipelineMetrics()
        with metrics.track("phase_a") as ctx:
            time.sleep(0.01)
            ctx.set_result({"confidence": 0.85})
        summary = metrics.get_summary()
        assert summary["total_analyses"] == 1
        assert summary["successful"] == 1
        assert summary["avg_confidence"] == 0.85

    def test_track_exception_records_failure(self):
        metrics = PipelineMetrics()
        with pytest.raises(RuntimeError):
            with metrics.track("failing_phase"):
                raise RuntimeError("boom")
        summary = metrics.get_summary()
        assert summary["total_analyses"] == 1
        assert summary["failed"] == 1

    def test_track_with_metadata(self):
        metrics = PipelineMetrics()
        with metrics.track("meta_phase", metadata={"key": "val"}):
            pass
        summary = metrics.get_summary()
        assert summary["total_analyses"] == 1

    def test_set_result_without_confidence(self):
        metrics = PipelineMetrics()
        with metrics.track("no_conf") as ctx:
            ctx.set_result({"no_confidence_key": True})
        summary = metrics.get_summary()
        assert summary["avg_confidence"] is None

    def test_empty_summary(self):
        metrics = PipelineMetrics()
        summary = metrics.get_summary()
        assert summary["total_analyses"] == 0


class TestBatchFailFast:
    @pytest.mark.asyncio
    async def test_fail_fast_stops_on_error(self):
        call_count = 0

        async def failing_analyze(text, analysis_type, params=None):
            nonlocal call_count
            call_count += 1
            if "fail" in text:
                raise ValueError("intentional")
            await asyncio.sleep(0.05)
            return {"ok": True}

        requests = [
            BatchRequest(id="1", text="fail_first", analysis_type="t"),
            BatchRequest(id="2", text="slow_second", analysis_type="t"),
        ]
        results = await run_batch_analysis(
            requests,
            analyze_fn=failing_analyze,
            max_concurrent=1,
            fail_fast=True,
        )
        assert len(results) == 2
        assert not results[0].success


# ============================================================
# workflows.py — _should_rerun_fallacy and builders
# ============================================================


class TestShouldRerunFallacy:
    def test_no_rerun_when_no_retractions(self):
        ctx = {"phase_jtms_output": {"undermined_count": 0, "beliefs": {}}}
        assert not _should_rerun_fallacy(ctx)

    def test_rerun_when_undermined_count_positive(self):
        ctx = {"phase_jtms_output": {"undermined_count": 3}}
        assert _should_rerun_fallacy(ctx)

    def test_rerun_when_invalid_beliefs(self):
        ctx = {
            "phase_jtms_output": {
                "beliefs": {
                    "b1": {"valid": True},
                    "b2": {"valid": False},
                }
            }
        }
        assert _should_rerun_fallacy(ctx)

    def test_no_rerun_at_max_count(self):
        ctx = {
            "_fallacy_rerun_count": 2,
            "phase_jtms_output": {"undermined_count": 5},
        }
        assert not _should_rerun_fallacy(ctx)

    def test_no_rerun_when_jtms_output_not_dict(self):
        ctx = {"phase_jtms_output": "not a dict"}
        assert not _should_rerun_fallacy(ctx)

    def test_no_rerun_when_beliefs_not_dict(self):
        ctx = {"phase_jtms_output": {"beliefs": "not a dict"}}
        assert not _should_rerun_fallacy(ctx)

    def test_rerun_at_count_one(self):
        ctx = {
            "_fallacy_rerun_count": 1,
            "phase_jtms_output": {"undermined_count": 1},
        }
        assert _should_rerun_fallacy(ctx)


class TestIncrementFallacyRerun:
    def test_increment_from_zero(self):
        ctx = {}
        _increment_fallacy_rerun(ctx)
        assert ctx["_fallacy_rerun_count"] == 1

    def test_increment_from_existing(self):
        ctx = {"_fallacy_rerun_count": 1}
        _increment_fallacy_rerun(ctx)
        assert ctx["_fallacy_rerun_count"] == 2


class TestWorkflowBuilders:
    """Test that all workflow builders produce valid definitions."""

    def test_iterative_workflow_builds(self):
        wf = build_iterative_analysis_workflow()
        assert wf.name == "iterative_analysis"
        assert len(wf.phases) >= 6

    def test_nl_to_logic_workflow_builds(self):
        wf = build_nl_to_logic_workflow()
        assert wf.name == "nl_to_logic_analysis"
        phase_names = [p.name for p in wf.phases]
        assert "nl_to_logic" in phase_names

    def test_quality_gated_counter_builds(self):
        wf = build_quality_gated_counter_workflow()
        assert wf.name == "quality_gated_counter"

    def test_debate_governance_loop_builds(self):
        wf = build_debate_governance_loop_workflow()
        assert wf.name == "debate_governance_loop"

    def test_jtms_dung_loop_builds(self):
        wf = build_jtms_dung_loop_workflow()
        assert wf.name == "jtms_dung_loop"

    def test_neural_symbolic_fallacy_builds(self):
        wf = build_neural_symbolic_fallacy_workflow()
        assert wf.name == "neural_symbolic_fallacy"

    def test_hierarchical_fallacy_builds(self):
        wf = build_hierarchical_fallacy_workflow()
        assert wf.name == "hierarchical_fallacy"


class TestWorkflowCatalog:
    def test_catalog_contains_core_workflows(self):
        reset_workflow_catalog()
        catalog = get_workflow_catalog()
        assert "light" in catalog
        assert "standard" in catalog
        assert "full" in catalog
        assert "iterative" in catalog
        assert "quality_gated" in catalog
        assert "nl_to_logic" in catalog
        reset_workflow_catalog()

    def test_reset_clears_catalog(self):
        get_workflow_catalog()
        reset_workflow_catalog()
        from argumentation_analysis.orchestration.workflows import WORKFLOW_CATALOG

        assert len(WORKFLOW_CATALOG) == 0


# ============================================================
# workflow_dsl.py — execution edge cases
# ============================================================


class TestWorkflowCondition:
    @pytest.mark.asyncio
    async def test_condition_false_skips_phase(self):
        registry = CapabilityRegistry()
        registry.register_service(
            name="svc",
            capabilities=["test_cap"],
            service_class=type("S", (), {}),
            invoke=lambda text, ctx: {"result": "should_not_run"},
        )

        workflow = (
            WorkflowBuilder("cond_test")
            .add_conditional_phase(
                "p1",
                capability="test_cap",
                condition=lambda ctx: False,
            )
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, input_data="test")
        assert results["p1"].status == PhaseStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_condition_true_runs_phase(self):
        registry = CapabilityRegistry()

        async def mock_invoke(text, ctx):
            return {"result": "ok"}

        registry.register_service(
            name="svc",
            capabilities=["test_cap"],
            service_class=type("S", (), {}),
            invoke=mock_invoke,
        )

        workflow = (
            WorkflowBuilder("cond_true")
            .add_conditional_phase(
                "p1",
                capability="test_cap",
                condition=lambda ctx: True,
            )
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, input_data="test")
        assert results["p1"].status == PhaseStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_condition_exception_proceeds(self):
        registry = CapabilityRegistry()

        async def mock_invoke(text, ctx):
            return {"result": "ok"}

        registry.register_service(
            name="svc",
            capabilities=["test_cap"],
            service_class=type("S", (), {}),
            invoke=mock_invoke,
        )

        def bad_condition(ctx):
            raise ValueError("condition error")

        workflow = (
            WorkflowBuilder("cond_err")
            .add_conditional_phase(
                "p1",
                capability="test_cap",
                condition=bad_condition,
            )
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, input_data="test")
        assert results["p1"].status == PhaseStatus.COMPLETED


class TestWorkflowInputTransform:
    @pytest.mark.asyncio
    async def test_input_transform_applied(self):
        registry = CapabilityRegistry()
        transformed = []

        async def capture_invoke(text, ctx):
            transformed.append(text)
            return {"got": text}

        registry.register_service(
            name="svc",
            capabilities=["test_cap"],
            service_class=type("S", (), {}),
            invoke=capture_invoke,
        )

        workflow = (
            WorkflowBuilder("transform_test")
            .add_phase(
                "p1",
                capability="test_cap",
                input_transform=lambda inp, ctx: inp.upper(),
            )
            .build()
        )
        executor = WorkflowExecutor(registry)
        await executor.execute(workflow, input_data="hello")
        assert transformed[0] == "HELLO"

    @pytest.mark.asyncio
    async def test_input_transform_fallback_on_error(self):
        registry = CapabilityRegistry()
        invoked_with = []

        async def capture_invoke(text, ctx):
            invoked_with.append(text)
            return {"got": text}

        registry.register_service(
            name="svc",
            capabilities=["test_cap"],
            service_class=type("S", (), {}),
            invoke=capture_invoke,
        )

        def bad_transform(inp, ctx):
            raise RuntimeError("transform error")

        workflow = (
            WorkflowBuilder("transform_err")
            .add_phase(
                "p1",
                capability="test_cap",
                input_transform=bad_transform,
            )
            .build()
        )
        executor = WorkflowExecutor(registry)
        await executor.execute(workflow, input_data="original")
        assert invoked_with[0] == "original"


class TestWorkflowLoop:
    @pytest.mark.asyncio
    async def test_loop_executes_multiple_iterations(self):
        registry = CapabilityRegistry()
        call_count = 0

        async def counting_invoke(text, ctx):
            nonlocal call_count
            call_count += 1
            return {"iteration": call_count}

        registry.register_service(
            name="svc",
            capabilities=["test_cap"],
            service_class=type("S", (), {}),
            invoke=counting_invoke,
        )

        workflow = (
            WorkflowBuilder("loop_test")
            .add_loop(
                "p1",
                capability="test_cap",
                max_iterations=3,
                convergence_fn=lambda prev, curr: False,
            )
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, input_data="test")
        assert results["p1"].status == PhaseStatus.COMPLETED
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_loop_converges_early(self):
        registry = CapabilityRegistry()
        call_count = 0

        async def invoke(text, ctx):
            nonlocal call_count
            call_count += 1
            return {"iteration": call_count}

        registry.register_service(
            name="svc",
            capabilities=["test_cap"],
            service_class=type("S", (), {}),
            invoke=invoke,
        )

        def converge_on_second(prev, curr):
            return curr.get("iteration", 0) >= 2

        workflow = (
            WorkflowBuilder("converge_test")
            .add_loop(
                "p1",
                capability="test_cap",
                max_iterations=5,
                convergence_fn=converge_on_second,
            )
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, input_data="test")
        assert results["p1"].status == PhaseStatus.COMPLETED
        assert call_count == 2


class TestWorkflowStateWriter:
    @pytest.mark.asyncio
    async def test_state_writer_called_on_completion(self):
        registry = CapabilityRegistry()

        async def mock_invoke(text, ctx):
            return {"result": "ok"}

        registry.register_service(
            name="svc",
            capabilities=["test_cap"],
            service_class=type("S", (), {}),
            invoke=mock_invoke,
        )

        written = []

        def mock_writer(output, state, ctx):
            written.append(output)

        mock_state = type(
            "State",
            (),
            {
                "log_error": lambda s, p, e: None,
                "set_workflow_results": lambda s, n, d: None,
            },
        )()

        workflow = (
            WorkflowBuilder("sw_test").add_phase("p1", capability="test_cap").build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(
            workflow,
            input_data="test",
            state=mock_state,
            state_writers={"test_cap": mock_writer},
        )
        assert results["p1"].status == PhaseStatus.COMPLETED
        assert len(written) == 1
        assert written[0] == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_state_writer_error_does_not_fail_phase(self):
        registry = CapabilityRegistry()

        async def mock_invoke(text, ctx):
            return {"result": "ok"}

        registry.register_service(
            name="svc",
            capabilities=["test_cap"],
            service_class=type("S", (), {}),
            invoke=mock_invoke,
        )

        def bad_writer(output, state, ctx):
            raise RuntimeError("writer failed")

        mock_state = type(
            "State",
            (),
            {
                "log_error": lambda s, p, e: None,
                "set_workflow_results": lambda s, n, d: None,
            },
        )()

        workflow = (
            WorkflowBuilder("sw_err").add_phase("p1", capability="test_cap").build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(
            workflow,
            input_data="test",
            state=mock_state,
            state_writers={"test_cap": bad_writer},
        )
        assert results["p1"].status == PhaseStatus.COMPLETED
