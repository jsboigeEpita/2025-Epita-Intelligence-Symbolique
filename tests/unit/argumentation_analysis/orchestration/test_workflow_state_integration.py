# -*- coding: utf-8 -*-
"""
Tests for UnifiedAnalysisState integration with WorkflowExecutor.

Covers: state injection, state writers, end-to-end workflow with state,
error handling, run_unified_analysis with state, JSON serialization.
"""

import asyncio
import json
import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentType,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowExecutor,
    PhaseStatus,
)


# ============================================================
# State injection into context
# ============================================================


class TestStateInjection:
    @pytest.mark.asyncio
    async def test_state_injected_into_context(self):
        """When state is provided, it appears in ctx['unified_state']."""
        received_ctx = {}

        async def capture_invoke(text, ctx):
            received_ctx.update(ctx)
            return {"ok": True}

        registry = CapabilityRegistry()
        registry.register(
            name="comp",
            component_type=ComponentType.AGENT,
            capabilities=["cap"],
            invoke=capture_invoke,
        )

        workflow = WorkflowBuilder("test").add_phase("p1", capability="cap").build()
        state = UnifiedAnalysisState("hello")
        executor = WorkflowExecutor(registry)
        await executor.execute(workflow, "hello", state=state)

        assert received_ctx.get("unified_state") is state

    @pytest.mark.asyncio
    async def test_no_state_means_no_unified_state_in_context(self):
        """When state is None, ctx does not contain 'unified_state'."""
        received_ctx = {}

        async def capture_invoke(text, ctx):
            received_ctx.update(ctx)
            return {"ok": True}

        registry = CapabilityRegistry()
        registry.register(
            name="comp",
            component_type=ComponentType.AGENT,
            capabilities=["cap"],
            invoke=capture_invoke,
        )

        workflow = WorkflowBuilder("test").add_phase("p1", capability="cap").build()
        executor = WorkflowExecutor(registry)
        await executor.execute(workflow, "hello")

        assert "unified_state" not in received_ctx

    @pytest.mark.asyncio
    async def test_state_accessible_by_downstream_phases(self):
        """Downstream phase can read from unified_state set by upstream writer."""
        downstream_state_ref = {}

        async def phase_a(text, ctx):
            return {"score": 0.9}

        async def phase_b(text, ctx):
            us = ctx.get("unified_state")
            downstream_state_ref["has_state"] = us is not None
            if us:
                downstream_state_ref["quality_count"] = len(us.argument_quality_scores)
            return {"done": True}

        def writer_a(output, state, ctx):
            state.add_quality_score("arg_1", {"clarity": 0.9}, 0.9)

        registry = CapabilityRegistry()
        registry.register("a", ComponentType.AGENT, capabilities=["cap_a"], invoke=phase_a)
        registry.register("b", ComponentType.AGENT, capabilities=["cap_b"], invoke=phase_b)

        workflow = (
            WorkflowBuilder("chain")
            .add_phase("a", capability="cap_a")
            .add_phase("b", capability="cap_b", depends_on=["a"])
            .build()
        )
        state = UnifiedAnalysisState("test")
        executor = WorkflowExecutor(registry)
        await executor.execute(
            workflow, "test", state=state, state_writers={"cap_a": writer_a}
        )

        assert downstream_state_ref["has_state"] is True
        assert downstream_state_ref["quality_count"] == 1


# ============================================================
# State writers — individual writer functions
# ============================================================


class TestStateWriters:
    def test_write_quality_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_quality_to_state,
        )

        state = UnifiedAnalysisState("test")
        output = {"clarity": 0.8, "coherence": 0.7, "note_finale": 0.75}
        ctx = {"input_data": "test"}
        _write_quality_to_state(output, state, ctx)
        assert len(state.argument_quality_scores) == 1
        assert state.argument_quality_scores["arg_input"]["overall"] == 0.75

    def test_write_counter_argument_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_counter_argument_to_state,
        )

        state = UnifiedAnalysisState("test")
        output = {
            "parsed_argument": {"premise": "All cats are animals"},
            "suggested_strategy": {"strategy_name": "counter_example", "confidence": 0.8},
        }
        ctx = {"input_data": "test"}
        _write_counter_argument_to_state(output, state, ctx)
        assert len(state.counter_arguments) == 1
        assert state.counter_arguments[0]["strategy"] == "counter_example"

    def test_write_jtms_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_jtms_to_state,
        )

        state = UnifiedAnalysisState("test")
        output = {"beliefs": {"claim_0": "True", "claim_1": "None"}, "belief_count": 2}
        ctx = {}
        _write_jtms_to_state(output, state, ctx)
        assert len(state.jtms_beliefs) == 2

    def test_write_debate_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_debate_to_state,
        )

        state = UnifiedAnalysisState("test")
        output = {"winner": "Team A", "scores": {}}
        ctx = {"input_data": "Should AI be regulated?"}
        _write_debate_to_state(output, state, ctx)
        assert len(state.debate_transcripts) == 1
        assert state.debate_transcripts[0]["winner"] == "Team A"

    def test_write_governance_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_governance_to_state,
        )

        state = UnifiedAnalysisState("test")
        output = {"available_methods": ["majority", "borda", "condorcet"]}
        ctx = {}
        _write_governance_to_state(output, state, ctx)
        assert len(state.governance_decisions) == 1
        assert "majority" in state.governance_decisions[0]["scores"]

    def test_write_camembert_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_camembert_to_state,
        )

        state = UnifiedAnalysisState("test")
        output = {
            "detections": [
                {"text": "you're dumb", "label": "ad_hominem", "confidence": 0.92},
                {"text": "everyone knows", "label": "ad_populum", "confidence": 0.78},
            ]
        }
        ctx = {}
        _write_camembert_to_state(output, state, ctx)
        assert len(state.neural_fallacy_scores) == 2
        assert state.neural_fallacy_scores[0]["label"] == "ad_hominem"

    def test_write_semantic_index_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_semantic_index_to_state,
        )

        state = UnifiedAnalysisState("test")
        output = {
            "results": [
                {"id": "doc_1", "score": 0.85, "snippet": "relevant text"},
            ]
        }
        ctx = {"input_data": "search query"}
        _write_semantic_index_to_state(output, state, ctx)
        assert len(state.semantic_index_refs) == 1
        assert state.semantic_index_refs[0]["document_id"] == "doc_1"

    def test_write_speech_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_speech_to_state,
        )

        state = UnifiedAnalysisState("test")
        output = {
            "segments": [
                {"start": 0.0, "end": 1.5, "text": "Hello world", "speaker": "A"},
            ]
        }
        ctx = {}
        _write_speech_to_state(output, state, ctx)
        assert len(state.transcription_segments) == 1
        assert state.transcription_segments[0]["speaker"] == "A"

    def test_writer_tolerates_none_output(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_quality_to_state,
        )

        state = UnifiedAnalysisState("test")
        _write_quality_to_state(None, state, {})
        assert len(state.argument_quality_scores) == 0

    def test_writer_tolerates_non_dict_output(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_jtms_to_state,
        )

        state = UnifiedAnalysisState("test")
        _write_jtms_to_state("not a dict", state, {})
        assert len(state.jtms_beliefs) == 0


# ============================================================
# WorkflowExecutor with state — end-to-end
# ============================================================


class TestWorkflowExecutorWithState:
    @pytest.mark.asyncio
    async def test_state_writer_called_on_completion(self):
        """State writer is called when phase completes successfully."""
        writer_calls = []

        async def fake_invoke(text, ctx):
            return {"value": 42}

        def fake_writer(output, state, ctx):
            writer_calls.append(output)

        registry = CapabilityRegistry()
        registry.register("c", ComponentType.AGENT, capabilities=["cap"], invoke=fake_invoke)

        workflow = WorkflowBuilder("test").add_phase("p1", capability="cap").build()
        state = UnifiedAnalysisState("test")
        executor = WorkflowExecutor(registry)
        results = await executor.execute(
            workflow, "test", state=state, state_writers={"cap": fake_writer}
        )

        assert results["p1"].status == PhaseStatus.COMPLETED
        assert len(writer_calls) == 1
        assert writer_calls[0] == {"value": 42}

    @pytest.mark.asyncio
    async def test_state_writer_not_called_on_failure(self):
        """State writer is NOT called when phase fails."""
        writer_calls = []

        async def failing_invoke(text, ctx):
            raise RuntimeError("boom")

        def fake_writer(output, state, ctx):
            writer_calls.append(output)

        registry = CapabilityRegistry()
        registry.register(
            "c", ComponentType.AGENT, capabilities=["cap"], invoke=failing_invoke
        )

        workflow = WorkflowBuilder("test").add_phase("p1", capability="cap").build()
        state = UnifiedAnalysisState("test")
        executor = WorkflowExecutor(registry)
        results = await executor.execute(
            workflow, "test", state=state, state_writers={"cap": fake_writer}
        )

        assert results["p1"].status == PhaseStatus.FAILED
        assert len(writer_calls) == 0

    @pytest.mark.asyncio
    async def test_writer_failure_does_not_crash_workflow(self):
        """If a state writer raises, the workflow continues normally."""

        async def ok_invoke(text, ctx):
            return {"done": True}

        def bad_writer(output, state, ctx):
            raise ValueError("writer exploded")

        registry = CapabilityRegistry()
        registry.register("c", ComponentType.AGENT, capabilities=["cap"], invoke=ok_invoke)

        workflow = WorkflowBuilder("test").add_phase("p1", capability="cap").build()
        state = UnifiedAnalysisState("test")
        executor = WorkflowExecutor(registry)
        results = await executor.execute(
            workflow, "test", state=state, state_writers={"cap": bad_writer}
        )

        # Phase should still be COMPLETED even though writer failed
        assert results["p1"].status == PhaseStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_workflow_results_stored_in_state(self):
        """After workflow completes, summary is stored in state.workflow_results."""

        async def ok_invoke(text, ctx):
            return {"ok": True}

        registry = CapabilityRegistry()
        registry.register("c", ComponentType.AGENT, capabilities=["cap"], invoke=ok_invoke)

        workflow = WorkflowBuilder("wf").add_phase("p1", capability="cap").build()
        state = UnifiedAnalysisState("test")
        executor = WorkflowExecutor(registry)
        await executor.execute(workflow, "test", state=state)

        assert "wf" in state.workflow_results
        assert state.workflow_results["wf"]["completed"] == 1
        assert state.workflow_results["wf"]["phases"]["p1"] == "completed"

    @pytest.mark.asyncio
    async def test_error_logged_in_state_on_failure(self):
        """Failed phases log their error in state via log_error()."""

        async def fail_invoke(text, ctx):
            raise RuntimeError("Something broke")

        registry = CapabilityRegistry()
        registry.register(
            "c", ComponentType.AGENT, capabilities=["cap"], invoke=fail_invoke
        )

        workflow = WorkflowBuilder("wf").add_phase("p1", capability="cap").build()
        state = UnifiedAnalysisState("test")
        executor = WorkflowExecutor(registry)
        await executor.execute(workflow, "test", state=state)

        # Errors should be logged in state
        assert len(state.errors) >= 1
        assert any("Something broke" in e.get("message", "") for e in state.errors)


# ============================================================
# run_unified_analysis with state
# ============================================================


class TestRunUnifiedAnalysisWithState:
    @pytest.mark.asyncio
    async def test_creates_state_by_default(self):
        """run_unified_analysis with create_state=True (default) returns state."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        result = await run_unified_analysis(
            "Les vaccins sont efficaces.",
            workflow_name="light",
            registry=registry,
        )

        assert "unified_state" in result
        assert result["unified_state"] is not None
        assert isinstance(result["unified_state"], UnifiedAnalysisState)
        assert "state_snapshot" in result
        assert isinstance(result["state_snapshot"], dict)

    @pytest.mark.asyncio
    async def test_no_state_when_disabled(self):
        """run_unified_analysis with create_state=False does not create state."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        result = await run_unified_analysis(
            "Test text.",
            workflow_name="light",
            registry=registry,
            create_state=False,
        )

        assert "unified_state" not in result

    @pytest.mark.asyncio
    async def test_state_populated_after_quality_phase(self):
        """After light workflow, state should have quality scores populated."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        result = await run_unified_analysis(
            "La peine de mort devrait être abolie car elle ne dissuade pas.",
            workflow_name="light",
            registry=registry,
        )

        state = result.get("unified_state")
        assert state is not None

        # Quality phase should have written scores
        if result["phases"]["quality"].status == PhaseStatus.COMPLETED:
            assert len(state.argument_quality_scores) > 0

        # Workflow results should be stored
        assert "light_analysis" in state.workflow_results


# ============================================================
# State snapshot JSON serialization
# ============================================================


class TestStateSnapshotSerialization:
    def test_empty_state_snapshot_serializable(self):
        """Empty state produces a JSON-serializable snapshot."""
        state = UnifiedAnalysisState("test")
        snapshot = state.get_state_snapshot(summarize=True)
        json_str = json.dumps(snapshot)
        assert isinstance(json_str, str)

    def test_populated_state_snapshot_serializable(self):
        """Populated state with all dimensions produces a JSON-serializable snapshot."""
        state = UnifiedAnalysisState("test")
        state.add_counter_argument("arg", "counter", "strategy", 0.8)
        state.add_quality_score("arg_1", {"clarity": 0.9}, 0.9)
        state.add_jtms_belief("B1", True, ["j1"])
        state.add_dung_framework("F1", ["a", "b"], [["a", "b"]])
        state.add_governance_decision("majority", "option_A", {"A": 3.0, "B": 1.0})
        state.add_debate_transcript("topic", [{"speaker": "A", "text": "hi"}], "A")
        state.add_neural_fallacy_score("text", "ad_hominem", 0.9)
        state.add_transcription_segment(0.0, 1.5, "Hello", "Speaker1")
        state.add_semantic_index_ref("query", "doc1", 0.7, "snippet")
        state.set_workflow_results("test_wf", {"completed": 1})

        # Summarized snapshot
        summary = state.get_state_snapshot(summarize=True)
        json.dumps(summary)  # should not raise

        # Full snapshot
        full = state.get_state_snapshot(summarize=False)
        json.dumps(full)  # should not raise

        # Check counts in summary
        assert summary["counter_argument_count"] == 1
        assert summary["quality_scores_count"] == 1
        assert summary["neural_fallacy_score_count"] == 1
        assert summary["transcription_segment_count"] == 1
        assert summary["semantic_index_ref_count"] == 1
