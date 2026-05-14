"""Tests for workflow checkpoint/resume (issue #451).

Covers:
- CheckpointManager atomic writes, loads, removal
- serialize/deserialize phase results
- WorkflowExecutor resume_from skips completed phases
- Crash simulation: phases 1-3 reused, 4-8 re-run, final state matches
"""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from argumentation_analysis.orchestration.checkpoint import (
    CheckpointManager,
    deserialize_phase_outputs,
    serialize_phase_result,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseResult,
    PhaseStatus,
    WorkflowBuilder,
    WorkflowExecutor,
)

# ---------------------------------------------------------------------------
# CheckpointManager tests
# ---------------------------------------------------------------------------


class TestCheckpointManager:
    def test_save_and_load(self, tmp_path: Path):
        mgr = CheckpointManager(tmp_path / "ckpt")
        mgr.save(
            doc_id="doc_001",
            workflow="spectacular",
            completed_phases=["extract", "quality"],
            phase_outputs={
                "extract": {
                    "status": "completed",
                    "output_json": '"data"',
                    "duration_s": 1.0,
                },
            },
        )
        loaded = mgr.load("doc_001")
        assert loaded is not None
        assert loaded["opaque_id"] == "doc_001"
        assert loaded["completed_phases"] == ["extract", "quality"]

    def test_load_missing_returns_none(self, tmp_path: Path):
        mgr = CheckpointManager(tmp_path / "ckpt")
        assert mgr.load("nonexistent") is None

    def test_load_corrupt_returns_none(self, tmp_path: Path):
        mgr = CheckpointManager(tmp_path / "ckpt")
        mgr.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        bad = mgr.checkpoint_dir / "bad.checkpoint.json"
        bad.write_text("{invalid json", encoding="utf-8")
        assert mgr.load("bad") is None

    def test_remove(self, tmp_path: Path):
        mgr = CheckpointManager(tmp_path / "ckpt")
        mgr.save(
            doc_id="to_remove", workflow="test", completed_phases=[], phase_outputs={}
        )
        assert mgr.load("to_remove") is not None
        mgr.remove("to_remove")
        assert mgr.load("to_remove") is None

    def test_remove_missing_is_noop(self, tmp_path: Path):
        mgr = CheckpointManager(tmp_path / "ckpt")
        mgr.remove("nonexistent")  # should not raise

    def test_list_incomplete(self, tmp_path: Path):
        mgr = CheckpointManager(tmp_path / "ckpt")
        mgr.save(doc_id="doc_a", workflow="w", completed_phases=["x"], phase_outputs={})
        mgr.save(doc_id="doc_b", workflow="w", completed_phases=["y"], phase_outputs={})
        assert mgr.list_incomplete() == ["doc_a", "doc_b"]

    def test_atomic_write_no_partial(self, tmp_path: Path):
        """Verify no .tmp files remain after successful write."""
        mgr = CheckpointManager(tmp_path / "ckpt")
        mgr.save(doc_id="atomic", workflow="w", completed_phases=[], phase_outputs={})
        tmps = list(mgr.checkpoint_dir.glob("*.tmp"))
        assert len(tmps) == 0

    def test_state_snapshot_preserved(self, tmp_path: Path):
        mgr = CheckpointManager(tmp_path / "ckpt")
        snapshot = {"fallacy_count": 5, "arguments": {"a1": "claim"}}
        mgr.save(
            doc_id="snap_test",
            workflow="w",
            completed_phases=["extract"],
            phase_outputs={},
            state_snapshot=snapshot,
        )
        loaded = mgr.load("snap_test")
        assert loaded["state_snapshot"] == snapshot


# ---------------------------------------------------------------------------
# serialize / deserialize tests
# ---------------------------------------------------------------------------


class TestSerializeDeserialize:
    def test_serialize_completed_with_output(self):
        result = serialize_phase_result("extract", "completed", {"key": "val"}, 1.5)
        assert result["status"] == "completed"
        assert result["output_json"] is not None
        assert json.loads(result["output_json"]) == {"key": "val"}
        assert result["duration_s"] == 1.5

    def test_serialize_non_serializable_output(self):
        result = serialize_phase_result("phase", "completed", object(), 0.1)
        assert result["output_json"] is not None  # default=str handles it

    def test_serialize_failed_phase(self):
        result = serialize_phase_result("bad", "failed", None, 0.5, error="boom")
        assert result["status"] == "failed"
        assert result["output_json"] is None
        assert result["error"] == "boom"

    def test_deserialize_round_trip(self):
        original = {"key": [1, 2, 3]}
        serialized = serialize_phase_result("p", "completed", original, 1.0)
        deserialized = deserialize_phase_outputs({"p": serialized})
        assert deserialized["p"] == original

    def test_deserialize_null_output(self):
        serialized = {
            "status": "completed",
            "output_json": None,
            "duration_s": 0.1,
            "error": None,
        }
        result = deserialize_phase_outputs({"p": serialized})
        assert result["p"] is None


# ---------------------------------------------------------------------------
# WorkflowExecutor resume tests
# ---------------------------------------------------------------------------


def _make_registry_with_invoke(phase_outputs: dict):
    """Build a mock registry that returns providers with canned outputs."""
    registry = MagicMock()

    def find_for_capability(cap):
        name = cap.replace("_capability", "")
        provider = MagicMock()
        provider.name = name
        output = phase_outputs.get(name, f"output_{name}")
        provider.invoke = AsyncMock(return_value=output)
        return [provider]

    registry.find_for_capability = find_for_capability
    return registry


class TestWorkflowExecutorResume:
    @pytest.mark.asyncio
    async def test_resume_skips_completed_phases(self):
        """Phases in resume_from should be skipped, not executed."""
        workflow = (
            WorkflowBuilder("test")
            .add_phase("a", capability="a")
            .add_phase("b", capability="b", depends_on=["a"])
            .add_phase("c", capability="c", depends_on=["b"])
            .build()
        )
        invoke_counts = {"a": 0, "b": 0, "c": 0}
        registry = MagicMock()

        def find_for_capability(cap):
            provider = MagicMock()
            provider.name = cap

            async def invoke(*args, **kwargs):
                invoke_counts[cap] += 1
                return f"out_{cap}"

            provider.invoke = invoke
            return [provider]

        registry.find_for_capability = find_for_capability

        executor = WorkflowExecutor(registry)

        # Resume from phase 'a' already completed
        context = {
            "phase_a_output": "out_a",
            "phase_a_result": PhaseResult(
                phase_name="a",
                status=PhaseStatus.COMPLETED,
                capability="a",
                output="out_a",
            ),
        }
        results = await executor.execute(
            workflow,
            input_data="test text",
            context=context,
            resume_from={"a"},
        )

        assert results["a"].status == PhaseStatus.SKIPPED
        assert results["b"].status == PhaseStatus.COMPLETED
        assert results["c"].status == PhaseStatus.COMPLETED
        assert invoke_counts == {"a": 0, "b": 1, "c": 1}

    @pytest.mark.asyncio
    async def test_checkpoint_callback_called_per_level(self):
        """Callback should be invoked after each DAG level."""
        workflow = (
            WorkflowBuilder("test")
            .add_phase("x", capability="x")
            .add_phase("y", capability="y", depends_on=["x"])
            .build()
        )
        registry = _make_registry_with_invoke({"x": "ox", "y": "oy"})
        executor = WorkflowExecutor(registry)

        callbacks = []

        def cb(results, ctx):
            callbacks.append(set(results.keys()))

        await executor.execute(workflow, input_data="t", checkpoint_callback=cb)

        assert len(callbacks) == 2
        assert callbacks[0] == {"x"}
        assert callbacks[1] == {"x", "y"}

    @pytest.mark.asyncio
    async def test_crash_and_resume_final_state_matches(self):
        """Simulate crash after phase 2 of 4, resume, verify final results.

        In a real crash (process dies), the checkpoint captures phases that
        completed before the crash point.  Here we simulate by:
        1. Running a normal execution with callback to capture checkpoint state
        2. Manually reconstructing resume context from the first N phases
        3. Running resume execution with those phases skipped
        """
        workflow = (
            WorkflowBuilder("test")
            .add_phase("p1", capability="p1")
            .add_phase("p2", capability="p2", depends_on=["p1"])
            .add_phase("p3", capability="p3", depends_on=["p2"])
            .add_phase("p4", capability="p4", depends_on=["p3"])
            .build()
        )

        # --- Run 1: full execution to capture baseline outputs ---
        call_log_full: list[str] = []
        registry_full = MagicMock()

        def find_full(cap):
            provider = MagicMock()
            provider.name = cap

            async def invoke(*args, **kwargs):
                call_log_full.append(cap)
                return f"out_{cap}"

            provider.invoke = invoke
            return [provider]

        registry_full.find_for_capability = find_full

        executor = WorkflowExecutor(registry_full)
        results_full = await executor.execute(workflow, input_data="t")

        assert all(
            results_full[p].status == PhaseStatus.COMPLETED
            for p in ["p1", "p2", "p3", "p4"]
        )

        # Simulate: crash after p2, checkpoint has p1 + p2 outputs
        crash_after = {"p1", "p2"}
        checkpoint_outputs = {name: results_full[name].output for name in crash_after}

        # --- Run 2: resume from checkpoint ---
        call_log_resume: list[str] = []
        registry_resume = MagicMock()

        def find_resume(cap):
            provider = MagicMock()
            provider.name = cap

            async def invoke(*args, **kwargs):
                call_log_resume.append(cap)
                return f"out_{cap}"

            provider.invoke = invoke
            return [provider]

        registry_resume.find_for_capability = find_resume

        context = {}
        for name in crash_after:
            context[f"phase_{name}_output"] = checkpoint_outputs[name]
            context[f"phase_{name}_result"] = PhaseResult(
                phase_name=name,
                status=PhaseStatus.COMPLETED,
                capability=name,
                output=checkpoint_outputs[name],
            )

        executor2 = WorkflowExecutor(registry_resume)
        resumed_results = await executor2.execute(
            workflow,
            input_data="t",
            context=context,
            resume_from=crash_after,
        )

        # p1, p2 skipped (from checkpoint); p3, p4 executed
        assert call_log_resume == ["p3", "p4"]
        assert resumed_results["p1"].status == PhaseStatus.SKIPPED
        assert resumed_results["p2"].status == PhaseStatus.SKIPPED
        assert resumed_results["p3"].status == PhaseStatus.COMPLETED
        assert resumed_results["p4"].status == PhaseStatus.COMPLETED

        # Final outputs match the full (non-crashed) run
        assert context["phase_p1_output"] == results_full["p1"].output
        assert context["phase_p2_output"] == results_full["p2"].output
        assert resumed_results["p3"].output == results_full["p3"].output
        assert resumed_results["p4"].output == results_full["p4"].output

    @pytest.mark.asyncio
    async def test_resume_without_context_reconstructs_skipped(self):
        """When resume_from is set but context lacks entries, phases get SKIPPED."""
        workflow = (
            WorkflowBuilder("test")
            .add_phase("a", capability="a")
            .add_phase("b", capability="b", depends_on=["a"])
            .build()
        )
        registry = _make_registry_with_invoke({"a": "oa", "b": "ob"})
        executor = WorkflowExecutor(registry)

        results = await executor.execute(workflow, input_data="t", resume_from={"a"})
        assert results["a"].status == PhaseStatus.SKIPPED
        assert results["b"].status == PhaseStatus.COMPLETED
