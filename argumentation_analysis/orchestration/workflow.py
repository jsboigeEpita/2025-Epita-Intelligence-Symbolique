# Archived: 2026-03-24 — Minimal shim for backward compatibility (#215)
# Original: 115-line ParallelWorkflowManager, superseded by workflow_dsl.py
# Full archive: docs/archives/orchestration_legacy/workflow_parallel.py
import warnings


class ParallelWorkflowManager:
    """Deprecated. Use workflow_dsl.WorkflowBuilder + WorkflowExecutor instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "ParallelWorkflowManager is deprecated. Use WorkflowBuilder from "
            "orchestration.workflow_dsl instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    async def execute_parallel_workflow(self, text, taxonomy_branches):
        raise NotImplementedError(
            "ParallelWorkflowManager has been archived. "
            "Use WorkflowBuilder + WorkflowExecutor from workflow_dsl.py."
        )
