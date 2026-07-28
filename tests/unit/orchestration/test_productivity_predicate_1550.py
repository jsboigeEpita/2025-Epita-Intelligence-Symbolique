# -*- coding: utf-8 -*-
"""Tests for #1550 — the productivity predicate mirror-error fix.

CC #1531 item 1 (PR #1545) made the per-objective ``success_rate`` count
production rather than execution — closing a real false positive (1.0 on empty
tasks). But its discriminant was binary: ``completed and not degraded``. A task
that produced a REAL artifact AND honestly flagged a partial degradation
(``degraded``) fell in the same bucket as a task that produced nothing. Real
production was erased by the partial-degradation admission — a verdict of void
on production, the mirror image of the original defect.

Firsthand (coordinator R722, ``results/task-obj-2-1_results.json``): obj-2
returned ``outputs.fallacies`` with 6 items (taxonomy depth 5),
``completion_status: completed``, ``degraded: True`` (a secondary per-argument
lift step skipped for want of extractable arguments). The task DID detect
fallacies — yet scored 0.0.

The fix (``_task_productivity``): ``degraded`` discounts a task that produced
(0.5); only the ABSENCE of a substantive artifact zeroes it (0.0); a clean run
is 1.0 even on an empty corpus.

These tests are sync and LLM-free. They live in a dedicated module WITHOUT
``pytestmark = pytest.mark.asyncio`` so the sync functions do not inherit an
asyncio mark they cannot satisfy (lesson R722). The 0.5 case is the mutation
guard: the pre-fix binary predicate could only emit 0.0 or 1.0, so asserting
0.5 proves the new discount path — a test that would still pass under the old
predicate proves nothing (DoD #4).
"""

from argumentation_analysis.orchestration.hierarchical.delegation_orchestrator import (
    DelegationOrchestrator,
    _task_productivity,
)

# ``_aggregate_results_by_objective`` is a @staticmethod on DelegationOrchestrator
# — the site #1550 targets (the per-objective success_rate).
_aggregate_results_by_objective = DelegationOrchestrator._aggregate_results_by_objective


# ── Unit: _task_productivity — three cases, three distinct scores ──────────


def test_clean_production_is_full():
    """A non-degraded completed task scores 1.0 — even with empty findings."""
    assert (
        _task_productivity({"status": "completed", "outputs": {"fallacies": []}}) == 1.0
    )


def test_degraded_with_artifact_is_half_the_mutation_guard():
    """A degraded task that STILL produced a substantive artifact scores 0.5.

    This is the obj-2 shape (firsthand): ``degraded: True`` AND a non-empty
    ``fallacies`` list. Pre-fix this scored 0.0 (``completed and not degraded``
    → False); the 0.5 assertion is the mutation discriminator — the binary
    predicate could never emit it.
    """
    result = {
        "status": "completed",
        "degraded": True,
        "degradation_reasons": ["degraded"],
        "outputs": {
            "fallacies": [{"taxonomy_pk": "1389", "taxonomy_path": "7.3.2.3.3"}],
            "degraded": True,
            "last_error": "per-argument fallacy lift skipped",
        },
    }
    assert _task_productivity(result) == 0.5


def test_degraded_without_artifact_is_zero_item1_case_stays_closed():
    """A self-declared non-analysis with no artifact scores 0.0.

    The three item-1 forms (``degraded`` flag with empty output, ``status:
    unavailable``, ``extraction_status: failed``) all stay 0.0 — the mirror fix
    must not re-open the false positive item 1 closed.
    """
    # degraded flag, no substantive artifact (a scalar count, not a collection)
    assert (
        _task_productivity(
            {"status": "completed", "degraded": True, "outputs": {"total_fallacies": 0}}
        )
        == 0.0
    )
    # status: unavailable — self-declared non-analysis
    assert (
        _task_productivity(
            {
                "status": "completed",
                "degraded": True,
                "outputs": {"status": "unavailable"},
            }
        )
        == 0.0
    )
    # no outputs at all (the test_degraded_run_does_not_conclude_success shape)
    assert (
        _task_productivity(
            {
                "status": "completed",
                "degraded": True,
                "degradation_reasons": ["degraded"],
            }
        )
        == 0.0
    )


def test_three_scores_are_distinct():
    """DoD #4: the three situations yield three distinct scores."""
    scores = {
        "clean": _task_productivity(
            {"status": "completed", "outputs": {"fallacies": []}}
        ),
        "partial": _task_productivity(
            {
                "status": "completed",
                "degraded": True,
                "outputs": {"fallacies": [{"x": 1}]},
            }
        ),
        "void": _task_productivity(
            {"status": "completed", "degraded": True, "outputs": {"total_fallacies": 0}}
        ),
    }
    assert scores == {"clean": 1.0, "partial": 0.5, "void": 0.0}, scores
    assert len(set(scores.values())) == 3, "scores are not three distinct values"


def test_failed_execution_is_zero():
    """A task that did not complete scores 0.0 regardless of outputs."""
    assert (
        _task_productivity({"status": "failed", "outputs": {"fallacies": [1]}}) == 0.0
    )


# ── Integration: the per-objective rate (the site #1550 targets) ───────────


def _obj_result(oid, **kwargs):
    base = {"objective_id": oid, "status": "completed", "capability": "stub"}
    base.update(kwargs)
    return base


def test_aggregate_obj2_partial_production_scores_above_zero():
    """DoD #1: obj-2 (degraded + real fallacies) rates > 0.

    Reproduces the firsthand obj-2 shape on the REAL aggregation path
    (``_aggregate_results_by_objective``) — the exact site #1550 targets. No
    LLM run: the artifact shape is the one captured in
    ``results/task-obj-2-1_results.json``.
    """
    objectives = [{"id": "obj-2", "description": "Détecter les sophismes"}]
    results = [
        _obj_result(
            "obj-2",
            degraded=True,
            degradation_reasons=["degraded"],
            outputs={
                "fallacies": [{"taxonomy_pk": "1389"}],
                "degraded": True,
                "last_error": "per-argument fallacy lift skipped",
            },
        )
    ]
    rate = _aggregate_results_by_objective(objectives, results)
    assert rate["obj-2"]["success_rate"] == 0.5, rate
    assert rate["obj-2"]["success_rate"] > 0, "obj-2 produced → must not be zero"


def test_aggregate_item1_void_case_stays_zero():
    """DoD #2: the item-1 void case (degraded, no artifact) stays 0.0."""
    objectives = [{"id": "obj-1", "description": "Détecter les sophismes"}]
    results = [
        _obj_result(
            "obj-1",
            degraded=True,
            degradation_reasons=["status=unavailable"],
            outputs={"status": "unavailable"},
        )
    ]
    rate = _aggregate_results_by_objective(objectives, results)
    assert rate["obj-1"]["success_rate"] == 0.0, rate


def test_aggregate_mixed_objective_averages_partial_and_full():
    """An objective with one partial (0.5) and one clean (1.0) task rates 0.75.

    The rate is an honest average of per-task productivities, so a partially
    degraded objective that still produced reads between 0 and 1 — not the 0.0
    the binary predicate forced, nor a fabricated 1.0.
    """
    objectives = [{"id": "obj-x", "description": "mixed"}]
    results = [
        _obj_result(
            "obj-x",
            degraded=True,
            outputs={"fallacies": [{"a": 1}]},
        ),
        _obj_result("obj-x", outputs={"fallacies": []}),
    ]
    rate = _aggregate_results_by_objective(objectives, results)
    assert rate["obj-x"]["success_rate"] == 0.75, rate
