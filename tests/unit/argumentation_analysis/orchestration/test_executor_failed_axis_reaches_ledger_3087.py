"""#3087 — a ledger axis that fails at executor level reaches the absence ledger.

Measured on three paid one-document passes (R1096/R1097/R1099): the
``belief_revision`` phase timed out at its 180 s budget, the only trace was
``state.errors``, and Act III said "two lost angles" while three were lost.
The ledger's five state writers run only on COMPLETED phases, so an axis that
dies at executor level (timeout, exception, unwired invoke) left NO ledger
entry — a label with a reader and no writer (family #1019).

The repair's contract, pinned here:

* the executor's failure sink (``workflow_dsl._store_phase_result``) is the
  ONE father: any FAILED phase whose capability is a ledger axis files a
  ``phase_failed`` entry, whatever the failure sense;
* the set of ledger axes comes from ONE table — the reader's own label map
  (``act3_conclusion_plugin._ABSENT_DIMENSION_LABELS``), never a second
  hand-kept list;
* ``_write_belief_revision_to_state`` files the success side too
  (``evaluated``), and the invoke's honest-absent JVM branch files
  ``unavailable`` — reason read from the OUTPUT's declared fields, never
  parsed from ``state.errors``;
* anti-regression: ``no_genuine_relations`` stays unlisted (an honest absence
  is not a degradation).

Every executor-path witness runs the REAL ``WorkflowExecutor.execute`` — the
timeout is produced by the phase budget, the exception by the provider —
never by a hand-written ledger entry. No JVM, no LLM (hermetic).

Born red on main ``1b4e7039f``: the four defect witnesses fail (no writer
exists); the three controls (unlisted honest absence, non-ledger capability,
table-driven coverage) legitimately pass.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

from argumentation_analysis.orchestration.state_writers import (
    _STRUCTURED_ARG_INPUT_KEYS,
    _write_belief_revision_to_state,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowExecutor,
)

# The reader's label for the measured axis — pinned so the witness proves the
# FRENCH label reaches the absence list, not just the capability key.
_BELIEF_LABEL = "la révision des croyances (le point de rupture minimal)"


class _FakeState:
    """The three surfaces the executor + the reader touch: the ledger (with
    its recorder), the error registry the FAILED branch writes, and nothing
    else (``_collect_undecided_formal_axes`` getattr-skips absent containers).
    Stores exactly the shape ``add_structured_arg_status`` stores."""

    def __init__(self) -> None:
        self.structured_arg_status: Dict[str, Dict[str, Any]] = {}
        self.errors: List[Dict[str, Any]] = []

    def add_structured_arg_status(
        self,
        capability: str,
        status: str,
        degraded: bool,
        reason: str,
        extension_count: int = 0,
    ) -> None:
        self.structured_arg_status[capability] = {
            "capability": capability,
            "status": status,
            "degraded": degraded,
            "reason": reason,
            "extension_count": extension_count,
        }

    def log_error(self, agent_name: str, message: str) -> None:
        self.errors.append({"agent_name": agent_name, "message": message})

    def add_belief_revision_result(self, *args: Any, **kwargs: Any) -> None:
        """No-op — the writer's downstream state write is not under test."""


def _absent_capabilities(state: Any) -> List[Any]:
    """The reader's own collector — the witness asserts on the real read."""
    from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
        _collect_absent_dimensions,
    )

    return _collect_absent_dimensions(state)


def _registry_with(invoke) -> Any:
    """A one-provider registry whose provider's invoke is the given callable."""

    async def _invoke(_input: Any, _ctx: Dict[str, Any]) -> Any:
        return await invoke()

    provider = SimpleNamespace(name="stub", invoke=_invoke)
    return SimpleNamespace(find_for_capability=lambda _cap: [provider])


async def _run_phase(capability: str, invoke, timeout: Optional[float]) -> Any:
    workflow = (
        WorkflowBuilder("w3087")
        .add_phase(
            "the_phase",
            capability=capability,
            optional=True,
            timeout_seconds=timeout,
        )
        .build()
    )
    executor = WorkflowExecutor(registry=_registry_with(invoke))
    state = _FakeState()
    await executor.execute(workflow, "texte synthétique", state=state)
    return state


# =============================================================================
# Defect witness 1 — the measured case: belief_revision times out at its budget
# =============================================================================


class TestBeliefRevisionTimeoutReachesLedger:
    async def test_timeout_axes_is_said_with_its_french_label(self):
        """The doc_A shape: the budget kills the phase, not the provider.

        On main the ledger stays empty and Act III says nothing — the report
        said 2 lost angles when 3 were. After the fix the reader lists the
        axis, its French label, a discriminating failure status, and the
        budget the phase exceeded (#1608's enriched message)."""

        async def slow() -> Any:
            await asyncio.sleep(2.0)

        state = await _run_phase("belief_revision", slow, timeout=0.05)
        absent = _absent_capabilities(state)
        matches = [d for d in absent if d.capability == "belief_revision"]
        assert (
            matches
        ), "belief_revision timed out at executor level and vanished from the absence list"
        entry = matches[0]
        assert entry.label == _BELIEF_LABEL
        assert entry.status == "phase_failed"
        assert "exceeded" in entry.reason and "budget" in entry.reason


# =============================================================================
# Defect witness 2 — one of the five existing axes dies at executor level
# =============================================================================


class TestExistingAxisExceptionReachesLedger:
    async def test_setaf_raise_is_listed_with_failure_status(self):
        """An axis whose handler raises (JVM up) must not vanish either: the
        ledger's writer for it runs only on COMPLETED, so the executor is the
        only place its loss can be said."""

        async def explodes() -> Any:
            raise RuntimeError("SetAF handler exploded")

        state = await _run_phase("setaf_reasoning", explodes, timeout=None)
        absent = _absent_capabilities(state)
        matches = [d for d in absent if d.capability == "setaf_reasoning"]
        assert (
            matches
        ), "setaf_reasoning raised at executor level and vanished from the absence list"
        entry = matches[0]
        assert entry.status == "phase_failed"
        assert "exploded" in entry.reason


# =============================================================================
# Defect witness 3 — belief_revision files its success side too
# =============================================================================


class TestBeliefRevisionWriterFilesLedgerEntry:
    @staticmethod
    def _output(**extra: Any) -> Dict[str, Any]:
        base: Dict[str, Any] = {
            "method": "dalal",
            "original": ["arg_1"],
            "revised": ["arg_2"],
            "minimal_retraction": {"cardinality": 1, "options": [["arg_1"]]},
        }
        base.update(extra)
        return base

    def test_success_files_evaluated_not_degraded(self):
        """A completed revision is an honest presence: ``evaluated``,
        ``degraded=False`` — the reader stays silent, and the ledger's
        vocabulary is complete in both directions."""

        state = _FakeState()
        _write_belief_revision_to_state(self._output(), state, {})
        entry = state.structured_arg_status["belief_revision"]
        assert entry["status"] == "evaluated"
        assert entry["degraded"] is False
        assert _absent_capabilities(state) == []

    def test_jvm_absent_files_unavailable_degraded(self):
        """The invoke's honest-absent return (#1646): the handler never ran,
        only the JVM-free insight did. The axis contributed no revision and
        the ledger says so — reason read from the OUTPUT's declared message,
        never parsed from ``state.errors``."""

        state = _FakeState()
        _write_belief_revision_to_state(
            self._output(
                degraded=True,
                absent_reason="jvm_not_started",
                message="belief revision unavailable: JVM not started (honest-absent)",
            ),
            state,
            {},
        )
        entry = state.structured_arg_status["belief_revision"]
        assert entry["status"] == "unavailable"
        assert entry["degraded"] is True
        assert "JVM not started" in entry["reason"]
        absent = _absent_capabilities(state)
        assert [d.capability for d in absent] == ["belief_revision"]


# =============================================================================
# Control 1 — an honest absence is still not a degradation (anti-regression)
# =============================================================================


def test_no_genuine_relations_stays_unlisted():
    state = _FakeState()
    state.add_structured_arg_status(
        "setaf_reasoning", "no_genuine_relations", False, "ran empty", 0
    )
    assert _absent_capabilities(state) == []


# =============================================================================
# Control 2 — the father is table-driven: a non-ledger failure writes nothing
# =============================================================================


async def test_non_ledger_capability_failure_writes_no_ledger_entry():
    async def explodes() -> Any:
        raise RuntimeError("quality exploded")

    state = await _run_phase("quality_evaluation", explodes, timeout=None)
    assert state.structured_arg_status == {}
    assert _absent_capabilities(state) == []


# =============================================================================
# Control 3 — the ONE table is load-bearing: unlabel the axis, coverage stops
# =============================================================================


async def test_unlabelling_the_axis_stops_the_coverage(monkeypatch):
    """The label map IS the membership table. Delete the belief_revision label
    and the executor no longer covers its failures — proving the coverage is
    derived, not hand-kept beside the map."""

    from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
        _ABSENT_DIMENSION_LABELS,
    )

    monkeypatch.delitem(_ABSENT_DIMENSION_LABELS, "belief_revision")

    async def slow() -> Any:
        await asyncio.sleep(2.0)

    state = await _run_phase("belief_revision", slow, timeout=0.05)
    assert "belief_revision" not in state.structured_arg_status


# =============================================================================
# Drift guard — every translation axis is a ledger axis (one table, no gap)
# =============================================================================


def test_every_translation_axis_is_a_ledger_axis():
    """A formalism added to ``_STRUCTURED_ARG_INPUT_KEYS`` without a reader
    label would fail at executor level UNSAID — the exact defect, on a new
    axis. This pins ``_STRUCTURED_ARG_INPUT_KEYS ⊆ label-map keys`` and the
    measured axis's own membership."""

    from argumentation_analysis.orchestration.state_writers import (
        _absence_ledger_axes,
    )

    axes = _absence_ledger_axes()
    assert set(_STRUCTURED_ARG_INPUT_KEYS) <= axes
    assert "belief_revision" in axes
