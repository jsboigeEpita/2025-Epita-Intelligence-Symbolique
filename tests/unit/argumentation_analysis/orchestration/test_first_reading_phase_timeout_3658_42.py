"""#3658 item 42 — a first reading killed by its phase budget says so.

Measured (free doc_J re-run, i1207): the first-reading phase at cap 16 384
exceeded its 180 s budget. The executor built a non-empty PhaseResult error
naming the budget (#1608) and wrote it to ``state.errors`` — but the state's
``defining_moves`` kept its DEFAULT record (``status: "no_llm"``,
``error: ""``): the first-reading state writer runs only on COMPLETED phases,
and the #3087 failure father covered only the structured-arg ledger axes. The
panel therefore read « aucun lecteur n'a lu le document » about a reading
that HAD been attempted and cut — the same defect shape #3087 repaired,
measured here on a different record.

The contract pinned here:

* the executor's ONE failure sink files a first-reading record whose
  ``status`` discriminates the budget cut (``timeout``) from any other
  executor-level failure (``phase_failed``), and whose ``error`` is the
  executor's own message — never a parse of ``state.errors`` (#1019);
* the failure sense is TYPED on the PhaseResult (``error_kind``), not
  recovered by matching text in the message;
* ``first_reading_note`` names the cut with its cause instead of telling the
  writer nobody read the document;
* the honest default (``no_llm``, no error) keeps its sentence verbatim, a
  COMPLETED read still lands through its own writer, and a failure of any
  other capability leaves the reading record untouched.

Born red on main ``3a94db222``: the three executor-path witnesses fail (the
record keeps the ``no_llm`` default). The controls legitimately pass before
and after. Hermetic: no LLM, no JVM — the timeout is produced by the phase
budget and the exception by the provider, exactly as in #3087's witnesses.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Optional

from argumentation_analysis.agents.core.reading import first_reading_note
from argumentation_analysis.orchestration.state_writers import (
    _write_first_reading_to_state,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowExecutor,
)


def _default_record() -> dict[str, Any]:
    """The exact default ``UnifiedAnalysisState`` stores for the reading."""
    return {
        "moves": [],
        "dropped_quotes": 0,
        "status": "no_llm",
        "error": "",
        "read_scope": {},
        "basis": "first_reading",
    }


class _FakeState:
    """The two surfaces the executor's FAILED branch and the note touch."""

    def __init__(self) -> None:
        self.defining_moves = _default_record()
        self.errors: list[dict[str, Any]] = []

    def log_error(self, agent_name: str, message: str) -> None:
        self.errors.append({"agent_name": agent_name, "message": message})


def _registry_with(invoke: Any) -> Any:
    """A one-provider registry whose provider's invoke is the given callable."""

    async def _invoke(_input: Any, _ctx: dict[str, Any]) -> Any:
        return await invoke()

    provider = SimpleNamespace(name="stub", invoke=_invoke)
    return SimpleNamespace(find_for_capability=lambda _cap: [provider])


async def _run_phase(
    capability: str,
    invoke: Any,
    timeout: Optional[float],
    *,
    state: Optional[_FakeState] = None,
    state_writers: Optional[dict[str, Any]] = None,
) -> _FakeState:
    workflow = (
        WorkflowBuilder("w3658_42")
        .add_phase(
            "the_phase",
            capability=capability,
            optional=True,
            timeout_seconds=timeout,
        )
        .build()
    )
    executor = WorkflowExecutor(registry=_registry_with(invoke))
    if state is None:
        state = _FakeState()
    await executor.execute(
        workflow,
        "texte synthétique",
        state=state,
        state_writers=state_writers,
    )
    return state


# =============================================================================
# Defect witness 1 — the measured case: the phase budget kills the reading
# =============================================================================


class TestBudgetCutReachesTheRecord:
    async def test_the_cut_is_recorded_as_a_timeout_with_its_budget(self):
        """On main the record keeps ``no_llm`` / ``error: ""``. After the fix
        it says ``timeout`` and carries the executor's own message — the one
        that names the budget (#1608). The rest of the record survives: the
        failure must not erase the shape a writer reads."""

        async def slow() -> Any:
            await asyncio.sleep(2.0)

        state = await _run_phase("first_reading", slow, timeout=0.05)
        record = state.defining_moves
        assert record["status"] == "timeout", record
        assert "budget" in record["error"]
        assert "0.05" in record["error"]
        assert record["moves"] == []
        assert record["basis"] == "first_reading"

    async def test_the_note_says_the_cut_not_that_nobody_read(self):
        """The measured false sentence: « aucun lecteur n'a lu le document »
        about a reading that was attempted and cut. The note now names the
        cut and its cause."""

        async def slow() -> Any:
            await asyncio.sleep(2.0)

        state = await _run_phase("first_reading", slow, timeout=0.05)
        note = first_reading_note(state)
        assert "budget de temps" in note, note
        assert "0.05" in note, note
        assert "aucun lecteur n'a lu" not in note, note


# =============================================================================
# Defect witness 2 — any other executor-level failure is a phase_failed
# =============================================================================


class TestExceptionReachesTheRecord:
    async def test_a_raised_producer_is_a_phase_failed_with_its_message(self):
        """The sense is typed on the PhaseResult, so the record does not have
        to guess: an exception is ``phase_failed``, not a budget cut, and its
        own message rides the record instead of a generic sentence."""

        async def explodes() -> Any:
            raise RuntimeError("the reading producer exploded")

        state = await _run_phase("first_reading", explodes, timeout=None)
        record = state.defining_moves
        assert record["status"] == "phase_failed", record
        assert "exploded" in record["error"]
        note = first_reading_note(state)
        assert "phase_failed" in note, note
        assert "exploded" in note, note
        assert "aucun lecteur n'a lu" not in note, note


# =============================================================================
# Control 1 — the honest default keeps its sentence (anti-regression)
# =============================================================================


def test_the_honest_default_still_says_nobody_read():
    """A reading that genuinely never ran (no LLM wired) must keep saying so:
    the sentence is a claim about the document, and it stays true here."""

    note = first_reading_note(_FakeState())
    assert "aucun lecteur n'a lu" in note, note


# =============================================================================
# Control 2 — a COMPLETED read still lands through its own writer
# =============================================================================


async def test_a_completed_read_still_lands_through_its_own_writer():
    """The failure leg must not hijack the success path: a completed read is
    written by ``_write_first_reading_to_state`` exactly as before."""

    async def reads() -> Any:
        return {
            "moves": [],
            "dropped_quotes": 0,
            "status": "ok",
            "read_scope": {"whole_document": True},
        }

    state = await _run_phase(
        "first_reading",
        reads,
        timeout=None,
        state_writers={"first_reading": _write_first_reading_to_state},
    )
    record = state.defining_moves
    assert record["status"] == "ok", record
    assert "error" not in record
    note = first_reading_note(state)
    assert "le document a été lu en entier" in note, note


# =============================================================================
# Control 3 — another capability's failure leaves the reading record alone
# =============================================================================


async def test_another_capabilitys_failure_leaves_the_reading_record_alone():
    """The first-reading leg is keyed on the capability, not bolted onto the
    generic sink: a ``quality_evaluation`` failure must not write a reading."""

    async def explodes() -> Any:
        raise RuntimeError("quality exploded")

    state = await _run_phase("quality_evaluation", explodes, timeout=None)
    assert state.defining_moves == _default_record()
