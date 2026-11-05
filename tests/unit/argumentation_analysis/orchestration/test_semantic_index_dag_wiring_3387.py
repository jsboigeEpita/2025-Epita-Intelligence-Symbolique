"""#3387 rework — witnesses on the REAL DAG, not on a recorded span.

The review of PR #3426 measured that the wiring the PR shipped was never
reached: the spectacular and standard workflows carried no
``semantic_indexing`` phase at all, and the full workflow's ``index`` phase
sat AFTER the fallacy pass (after ``counter``) — so the spans the selector
spends arrived once the selection was already made, and with no
``first_reading`` in full the index skipped for want of a query on every
run. These witnesses pin the three workflows' DAG shape against the
CALLABLES the registry actually binds, so a phase that declares nothing (or
declares it too late) reddens here:

- every phase whose registry invoke statically reaches
  ``_selection_priority_spans`` (the per-argument selection's hint) runs at
  a strictly LATER execution level than the semantic-index phase — measured
  on the built workflow's ``get_execution_order()``, not on a dump;
- the executor behaviour the optional-on-both-sides wiring relies on: a
  dependent still runs when its optional dependency is SKIPPED.

Born red on ``bf9541136`` (the PR head before this rework, rebased here as
``d289fb006``): spectacular/standard had no ``semantic_indexing`` phase to
resolve (KeyError) and full's ``index`` sat below the fallacy pass.
"""

import ast
from typing import Dict, Set

import pytest

from argumentation_analysis.orchestration.workflows import (
    build_full_workflow,
    build_spectacular_workflow,
    build_standard_workflow,
    reset_workflow_catalog,
)


@pytest.fixture(autouse=True)
def _reset_catalog():
    reset_workflow_catalog()
    yield
    reset_workflow_catalog()


def _call_graph() -> Dict[str, Set[str]]:
    """Static call graph of ``invoke_callables.py``: function -> called names.

    Only direct ``Name`` calls are collected (``_helper(...)``), which is the
    shape every internal hop of the spans chain uses. Attribute calls
    (``obj.method``) are out of scope: they cross module boundaries the
    registry never binds an invoke through.
    """
    import inspect

    from argumentation_analysis.orchestration import invoke_callables

    tree = ast.parse(inspect.getsource(invoke_callables))
    graph: Dict[str, Set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            callees = {
                sub.func.id
                for sub in ast.walk(node)
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
            }
            graph[node.name] = callees
    return graph


def _callers_reaching(graph: Dict[str, Set[str]], target: str) -> Set[str]:
    """Functions from which ``target`` is reachable through the call graph."""
    reaching: Set[str] = set()
    frontier = [target]
    while frontier:
        current = frontier.pop()
        for function, callees in graph.items():
            if current in callees and function not in reaching:
                reaching.add(function)
                frontier.append(function)
    return reaching


def _spans_readers_in_workflow(workflow, index_phase_name: str):
    """(index level, {phase name: level}) for phases whose callable reaches
    ``_selection_priority_spans`` — resolved through the REAL registry."""
    from argumentation_analysis.orchestration.registry_setup import setup_registry

    registry = setup_registry()
    reaching = _callers_reaching(_call_graph(), "_selection_priority_spans")

    levels = {}
    for depth, level in enumerate(workflow.get_execution_order()):
        for phase_name in level:
            levels[phase_name] = depth

    readers = {}
    for phase in workflow.phases:
        for provider in registry.find_for_capability(phase.capability):
            invoke = getattr(provider, "invoke", None)
            if invoke is not None and getattr(invoke, "__name__", "") in reaching:
                readers[phase.name] = levels[phase.name]
                break
    return levels[index_phase_name], readers


class TestSpectacularIndexPrecedesEverySpansReader:
    """The panel's workflow: the index feeds the selection, not the echo."""

    def test_every_spans_reader_runs_after_the_index(self):
        wf = build_spectacular_workflow()
        index_level, readers = _spans_readers_in_workflow(wf, "semantic_indexing")
        # The per-argument fallacy pass is the known reader — the witness is
        # not vacuous: at least one phase must reach the spans function.
        assert "hierarchical_fallacy" in readers, (
            "no phase of spectacular reaches _selection_priority_spans — "
            "the chain the index feeds has disappeared"
        )
        for phase_name, level in readers.items():
            assert level > index_level, (
                f"'{phase_name}' spends semantic_priority_spans (level {level}) "
                f"but the index only runs at level {index_level}: the spans "
                "arrive after the selection is spent"
            )

    def test_fallacy_declares_the_index_dependency(self):
        wf = build_spectacular_workflow()
        deps = wf.get_phase("hierarchical_fallacy").depends_on
        assert "semantic_indexing" in deps


class TestStandardIndexPrecedesEverySpansReader:
    def test_every_spans_reader_runs_after_the_index(self):
        wf = build_standard_workflow()
        index_level, readers = _spans_readers_in_workflow(wf, "semantic_indexing")
        assert "hierarchical_fallacy" in readers
        for phase_name, level in readers.items():
            assert level > index_level, (
                f"'{phase_name}' (level {level}) spends spans the index "
                f"(level {index_level}) has not written yet"
            )


class TestFullIndexPrecedesEverySpansReader:
    def test_every_spans_reader_runs_after_the_index(self):
        wf = build_full_workflow()
        index_level, readers = _spans_readers_in_workflow(wf, "index")
        assert "hierarchical_fallacy" in readers
        for phase_name, level in readers.items():
            assert level > index_level, (
                f"'{phase_name}' (level {level}) spends spans the index "
                f"(level {index_level}) has not written yet"
            )

    def test_fallacy_declares_the_index_dependency(self):
        wf = build_full_workflow()
        deps = wf.get_phase("hierarchical_fallacy").depends_on
        assert "index" in deps

    def test_full_has_a_reading_for_the_index_query(self):
        """The index reads the first reading as its query: full must HAVE the
        reading phase, or the index skips with ``no_reading_query`` on every
        run (the measured state of the PR head)."""
        wf = build_full_workflow()
        assert "first_reading" in {p.name for p in wf.phases}
        assert "first_reading" in wf.get_phase("index").depends_on


class TestOptionalSkippedDependencyStillRuns:
    """The executor behaviour the wiring relies on (#3395's pattern, used by
    this rework): a phase whose OPTIONAL dependency is SKIPPED still runs on
    whatever exists — a skipped index must not skip the fallacy pass."""

    @pytest.mark.asyncio
    async def test_dependent_runs_when_optional_dependency_skips(self):
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
            ComponentType,
        )
        from argumentation_analysis.orchestration.workflow_dsl import (
            PhaseStatus,
            WorkflowBuilder,
            WorkflowExecutor,
        )

        registry = CapabilityRegistry()

        async def _run_down(input_text: str, context: dict) -> dict:
            return {"ran": True}

        registry.register_agent(
            "down_agent", type("A", (), {}), capabilities=["cap_down"], invoke=_run_down
        )

        workflow = (
            WorkflowBuilder("optional_dep_skip")
            .add_phase("up", capability="cap_missing", optional=True)
            .add_phase("down", capability="cap_down", depends_on=["up"])
            .build()
        )

        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "text")

        assert results["up"].status == PhaseStatus.SKIPPED
        assert results["down"].status == PhaseStatus.COMPLETED
