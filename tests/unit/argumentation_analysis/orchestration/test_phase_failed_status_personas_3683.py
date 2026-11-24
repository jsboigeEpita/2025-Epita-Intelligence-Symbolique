"""#3683 — a phase killed by its budget leaves four records at their default.

Measured (issue #3683, hermetic probe on #3087 / #3681's witness template):
when one of these four phases dies at its phase budget, the executor writes
the #1608 message into ``state.errors`` and NOTHING else — the record keeps
its default. The #3087 failure father knew only the absence-ledger axes, and
item 42 (#3681) added ``first_reading``; these four capabilities are in
neither branch of ``_record_phase_failed_status``.

Recorded states on one seat: 12 executor budget cuts in 193 snapshots, ALL
of them ``coverage_review`` at its 300 s budget, and in all 12 the record
still says ``status: "no_llm"``, ``reason: ""``. The three other phases were
cut in 0 of the 193: for them the defect is possible, not observed.

The contract pinned here, per the issue's definition of done:

* ``historical_context``, ``strategic_read``, ``coverage_review``:
  ``status`` discriminates the budget cut (``timeout``) from any other
  executor-level failure (``phase_failed``), the executor's OWN message
  lands in the record's own cause field (``error`` for the first two,
  ``reason`` for the coverage review — the field its producer fills on
  ``llm_error`` / ``parse_error``), and the rest of the record is preserved;
* ``cross_passage_consistency`` keeps its own vocabulary: ``status`` stays
  ``unreachable`` and ``reason`` names the cut (``phase_budget_exceeded``,
  else ``phase_failed``);
* the failure sense is TYPED on the PhaseResult (``error_kind`` of #3681),
  never recovered by matching text in the message (#1019);
* ``cross_passage_note`` names the cut through its closed clause table
  (#3488), with the exact clause « la phase a dépassé son budget de temps »;
* the budgets themselves are NOT changed — the timeout is 0.05 s in the
  probe, and no phase budget in the workflow moves.

Born red on ``main`` ``de05227f3`` (and on its descendant ``30c2a0da1``):
each of the four executor-path witnesses fails, the record keeping its
default; the cross-passage note has no clause for the two new reasons. The
controls legitimately pass before and after.

Hermetic: no LLM, no JVM, no network, no corpus. The timeout is produced by
the phase budget and the exception by the provider, exactly as in #3087's
and #3681's witnesses. Synthetic text only.
"""

from __future__ import annotations

import asyncio
import copy
from types import SimpleNamespace
from typing import Any, Optional

import pytest

from argumentation_analysis.agents.core.reading import (
    coverage_review_note,
    cross_passage_note,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    CAPABILITY_STATE_WRITERS,
    _record_phase_failed_status,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowExecutor,
)
from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    _format_historical_block,
    _format_strategic_block,
)

FOUR = (
    "historical_context",
    "strategic_read",
    "cross_passage_consistency",
    "coverage_review",
)
# The four records as ``UnifiedAnalysisState`` stores them, read from a real
# state — never a hand copy that could drift from the class. The control
# below holds the hand-pinned table to what the class builds.
_PINNED_DEFAULTS: dict[str, dict[str, Any]] = {
    "historical_context": {
        "situation": "",
        "items": [],
        "status": "no_llm",
        "basis": "model_knowledge",
    },
    "strategic_read": {
        "players": [],
        "options": [],
        "preferences": {},
        "reading": "",
        "game": {},
        "status": "no_llm",
        "basis": "model_knowledge",
    },
    "cross_passage_consistency": {
        "status": "unreachable",
        "reason": "",
        "checked": 0,
        "dropped_formulas": 0,
        "unquoted_slots": [],
        "pairs_decided": 0,
        "findings": [],
        "basis": "cross_passage_consistency",
    },
    "coverage_review": {
        "status": "no_llm",
        "items": [],
        "examined": 0,
        "examined_by_class": {},
        "document_chars": 0,
        "dropped": {},
        "reason": "",
        "basis": "coverage_review",
    },
}


def _default_records() -> dict[str, dict[str, Any]]:
    """The four records exactly as ``UnifiedAnalysisState`` stores them."""
    real = UnifiedAnalysisState("texte synthétique")
    return {key: copy.deepcopy(getattr(real, key)) for key in FOUR}


class _FakeState:
    """The surfaces the executor's FAILED branch and the notes touch.

    The four records start as the REAL defaults (``_default_records``); the
    rest is the two surfaces the failure sink may reach.
    """

    def __init__(self) -> None:
        for key, record in _default_records().items():
            setattr(self, key, copy.deepcopy(record))
        self.errors: list[dict[str, Any]] = []
        self.structured_arg_status: dict[str, Any] = {}

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
    state: Optional[Any] = None,
    state_writers: Optional[dict[str, Any]] = None,
) -> Any:
    workflow = (
        WorkflowBuilder("w3683")
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


async def _slow() -> Any:
    await asyncio.sleep(2.0)


async def _explodes() -> Any:
    raise RuntimeError("the phase producer exploded")


# =============================================================================
# Witness 1 — the measured case: the phase budget kills the phase
# =============================================================================


class TestABudgetCutNamesItselfOnEachRecord:
    @pytest.mark.parametrize("capability", FOUR)
    async def test_the_cut_reaches_the_record(self, capability: str):
        """On main the record keeps its default, so the panel reads « no LLM,
        by design » about a phase that HAD been attempted and cut."""
        state = await _run_phase(capability, _slow, timeout=0.05)
        record = getattr(state, capability)
        assert state.errors, "the executor must still log the #1608 message"
        if capability == "cross_passage_consistency":
            assert record["status"] == "unreachable", record
            assert record["reason"] == "phase_budget_exceeded", record
        else:
            assert record["status"] == "timeout", record
            cause_field = "reason" if capability == "coverage_review" else "error"
            assert "budget" in record[cause_field], record
            assert "0.05" in record[cause_field], record

    @pytest.mark.parametrize("capability", FOUR)
    async def test_the_rest_of_the_record_survives(self, capability: str):
        """The failure must not erase the shape a writer reads."""
        state = await _run_phase(capability, _slow, timeout=0.05)
        record = getattr(state, capability)
        default = _default_records()[capability]
        for key, value in default.items():
            if key in ("status", "reason", "error"):
                continue
            assert record[key] == value, (capability, key, record)

    async def test_the_cross_passage_note_names_the_cut(self):
        """The one render that changes: « Contrôle non atteint : aucune
        incohérence rapportée. » said nothing about a 300 s cut; the clause
        table now names the cause, in reader words (#3488)."""
        state = await _run_phase("cross_passage_consistency", _slow, timeout=0.05)
        note = cross_passage_note(state)
        assert "la phase a dépassé son budget de temps" in note, note
        assert "phase_budget_exceeded" not in note, note
        assert "non atteint" in note, note

    async def test_the_note_keeps_the_record_shape(self):
        """The note is a RENDER of the record: the record keeps its raw key,
        and the other fields of a cut check are still there."""
        state = await _run_phase("cross_passage_consistency", _slow, timeout=0.05)
        record = state.cross_passage_consistency
        assert record["checked"] == 0
        assert record["findings"] == []
        assert record["basis"] == "cross_passage_consistency"


# =============================================================================
# Witness 2 — any other executor-level failure is a phase_failed
# =============================================================================


class TestAnExceptionNamesItselfOnEachRecord:
    @pytest.mark.parametrize("capability", FOUR)
    async def test_a_raised_producer_is_a_phase_failed(self, capability: str):
        """The sense is typed on the PhaseResult, so the record does not have
        to guess: an exception is ``phase_failed``, not a budget cut."""
        state = await _run_phase(capability, _explodes, timeout=None)
        record = getattr(state, capability)
        if capability == "cross_passage_consistency":
            assert record["status"] == "unreachable", record
            assert record["reason"] == "phase_failed", record
        else:
            assert record["status"] == "phase_failed", record
            cause_field = "reason" if capability == "coverage_review" else "error"
            assert "exploded" in record[cause_field], record

    async def test_the_note_says_the_phase_failed_without_a_raw_key(self):
        state = await _run_phase("cross_passage_consistency", _explodes, timeout=None)
        note = cross_passage_note(state)
        assert note, "an unreachable record still renders its named absence"
        assert "phase_failed" not in note, note
        assert "la phase a dépassé son budget de temps" not in note, note
        assert "la phase a échoué" in note, note


# =============================================================================
# Control 1 — the default record is unchanged when no phase runs
# =============================================================================


def test_no_phase_running_leaves_the_four_defaults_untouched():
    """The pinned table is what the real class builds — and a state no phase
    ran on still carries exactly that."""
    assert _default_records() == _PINNED_DEFAULTS
    state = _FakeState()
    for capability, default in _PINNED_DEFAULTS.items():
        assert getattr(state, capability) == default, capability


# =============================================================================
# Control 2 — a COMPLETED ``ok`` record is unchanged through its own writer
# =============================================================================


_OK_PAYLOADS: dict[str, dict[str, Any]] = {
    "historical_context": {
        "situation": "Une situation synthétique.",
        "items": [],
        "status": "ok",
    },
    "strategic_read": {
        "players": [],
        "options": [],
        "preferences": {},
        "reading": "Une lecture synthétique.",
        "game": {},
        "status": "ok",
    },
    "cross_passage_consistency": {
        "status": "checked",
        "reason": "",
        "checked": 4,
        "dropped_formulas": 0,
        "unquoted_slots": [],
        "pairs_decided": 1,
        "findings": [],
    },
    "coverage_review": {
        "status": "ok",
        "items": [],
        "examined": 2,
        "candidates": 3,
        "briefed": 3,
        "dropped": {},
        "reason": "",
    },
}


@pytest.mark.parametrize("capability", FOUR)
async def test_a_completed_phase_still_lands_through_its_own_writer(capability: str):
    """The failure leg must not hijack the success path."""
    payload = _OK_PAYLOADS[capability]

    async def ok() -> Any:
        return payload

    state = await _run_phase(
        capability,
        ok,
        timeout=None,
        state_writers=CAPABILITY_STATE_WRITERS,
    )
    record = getattr(state, capability)
    assert record["status"] == payload["status"], record
    if capability in ("historical_context", "strategic_read"):
        assert "error" not in record, record
    if capability in ("coverage_review", "cross_passage_consistency"):
        assert record["reason"] == "", record
    if capability == "cross_passage_consistency":
        assert record["checked"] == 4
        assert record["pairs_decided"] == 1
    if capability == "historical_context":
        assert record["situation"] == "Une situation synthétique."
    if capability == "strategic_read":
        assert record["reading"] == "Une lecture synthétique."


# =============================================================================
# Control 2b — a PARTIAL record survives a cut: the failure does not erase
# what an earlier phase of the same run already wrote
# =============================================================================


class TestAPartialRecordSurvivesTheFailure:
    async def test_a_partly_filled_historian_record_keeps_its_content(self):
        """A record rebuilt from scratch would read as a valid default with a
        new status. The failure must preserve what the record already said:
        the situation and the items a writer later reads are not the
        failure's to drop."""
        state = _FakeState()
        state.historical_context = {
            "situation": "Une situation déjà lue.",
            "items": [{"event": "un événement synthétique", "year": 1998}],
            "status": "no_llm",
            "basis": "model_knowledge",
            "blind_spot": "un angle mort déjà nommé",
        }
        await _run_phase("historical_context", _slow, timeout=0.05, state=state)
        record = state.historical_context
        assert record["status"] == "timeout"
        assert record["situation"] == "Une situation déjà lue."
        assert record["items"] == [{"event": "un événement synthétique", "year": 1998}]
        assert record["blind_spot"] == "un angle mort déjà nommé"
        assert record["basis"] == "model_knowledge"

    async def test_a_partly_filled_strategist_record_keeps_its_content(self):
        state = _FakeState()
        state.strategic_read = {
            "players": [{"name": "un acteur synthétique", "quote": "", "offset": 3}],
            "options": ["une option"],
            "preferences": {"un acteur synthétique": ["une option"]},
            "reading": "Une lecture déjà écrite.",
            "game": {"winner": "un vainqueur calculé"},
            "status": "no_llm",
            "basis": "model_knowledge",
        }
        await _run_phase("strategic_read", _slow, timeout=0.05, state=state)
        record = state.strategic_read
        assert record["status"] == "timeout"
        assert record["reading"] == "Une lecture déjà écrite."
        assert record["game"] == {"winner": "un vainqueur calculé"}
        assert record["players"][0]["name"] == "un acteur synthétique"

    async def test_a_partly_filled_coverage_record_keeps_its_content(self):
        state = _FakeState()
        state.coverage_review = {
            "status": "no_llm",
            "items": [{"quote": "une citation synthétique", "offset": 12}],
            "examined": 7,
            "examined_by_class": {"une_classe": 3},
            "document_chars": 4321,
            "dropped": {},
            "reason": "",
            "basis": "coverage_review",
        }
        await _run_phase("coverage_review", _slow, timeout=0.05, state=state)
        record = state.coverage_review
        assert record["status"] == "timeout"
        assert record["examined"] == 7
        assert record["examined_by_class"] == {"une_classe": 3}
        assert record["document_chars"] == 4321
        assert record["items"] == [{"quote": "une citation synthétique", "offset": 12}]

    async def test_a_partly_filled_cross_passage_record_keeps_its_content(self):
        state = _FakeState()
        state.cross_passage_consistency = {
            "status": "unreachable",
            "reason": "no_llm_translation_route",
            "checked": 5,
            "dropped_formulas": 2,
            "unquoted_slots": ["un_emplacement"],
            "pairs_decided": 1,
            "findings": [{"left": {}, "right": {}}],
            "basis": "cross_passage_consistency",
        }
        await _run_phase("cross_passage_consistency", _slow, timeout=0.05, state=state)
        record = state.cross_passage_consistency
        assert record["status"] == "unreachable"
        assert record["reason"] == "phase_budget_exceeded"
        assert record["checked"] == 5
        assert record["dropped_formulas"] == 2
        assert record["unquoted_slots"] == ["un_emplacement"]
        assert record["pairs_decided"] == 1
        assert record["findings"] == [{"left": {}, "right": {}}]


# =============================================================================
# The sense is TYPED on the PhaseResult — never a text match (#1019)
# =============================================================================


class TestTheSenseIsTypedNotGuessed:
    """Through the sink itself, with the two inputs decorrelated: a message
    that SPEAKS of a budget does not make a cut, and a cut does not need the
    word to be recognised."""

    @pytest.mark.parametrize("capability", FOUR)
    def test_a_message_naming_a_budget_is_not_a_cut(self, capability: str):
        state = _FakeState()
        _record_phase_failed_status(
            state,
            capability,
            "RuntimeError: upstream spoke of its 0.05s budget and exploded",
            error_kind="exception",
        )
        record = getattr(state, capability)
        if capability == "cross_passage_consistency":
            assert record["reason"] == "phase_failed", record
        else:
            assert record["status"] == "phase_failed", record

    @pytest.mark.parametrize("capability", FOUR)
    def test_a_cut_needs_no_recognisable_word(self, capability: str):
        state = _FakeState()
        _record_phase_failed_status(state, capability, "", error_kind="timeout")
        record = getattr(state, capability)
        if capability == "cross_passage_consistency":
            assert record["reason"] == "phase_budget_exceeded", record
        else:
            assert record["status"] == "timeout", record
            cause_field = "reason" if capability == "coverage_review" else "error"
            assert record[cause_field] == "phase failed at executor level"

    @pytest.mark.parametrize("capability", FOUR)
    def test_an_untyped_call_is_never_read_as_a_cut(self, capability: str):
        """A caller that predates the typed field passes no ``error_kind``:
        the record says the phase failed, and does not invent a cut."""
        state = _FakeState()
        _record_phase_failed_status(state, capability, "the phase died")
        record = getattr(state, capability)
        if capability == "cross_passage_consistency":
            assert record["reason"] == "phase_failed", record
        else:
            assert record["status"] == "phase_failed", record

    def test_the_cause_field_is_the_one_each_producer_fills(self):
        """``error`` for the historian and the strategist, ``reason`` for the
        coverage review: the field a failed read already lands in, so a
        reader has ONE field to read for both failure kinds."""
        from argumentation_analysis.orchestration.state_writers import (
            _PHASE_FAILED_CAUSE_FIELDS,
        )

        assert _PHASE_FAILED_CAUSE_FIELDS == {
            "historical_context": "error",
            "strategic_read": "error",
            "coverage_review": "reason",
        }

    @pytest.mark.parametrize("capability", FOUR)
    def test_the_table_covers_exactly_the_four_capabilities(self, capability: str):
        """Every capability the issue names reaches a leg: none is left to
        the default-return branch of the sink."""
        from argumentation_analysis.orchestration.state_writers import (
            _absence_ledger_axes,
        )

        state = _FakeState()
        before = copy.deepcopy(getattr(state, capability))
        _record_phase_failed_status(state, capability, "cut", error_kind="timeout")
        assert getattr(state, capability) != before, capability
        assert capability not in _absence_ledger_axes()

    def test_a_state_without_the_record_is_left_alone(self):
        """Defensive, like the ledger leg: a state that predates the record
        raises nothing and gains nothing."""
        bare: dict[str, Any] = {}
        _record_phase_failed_status(
            bare, "coverage_review", "cut", error_kind="timeout"
        )
        _record_phase_failed_status(
            bare, "cross_passage_consistency", "cut", error_kind="timeout"
        )
        assert bare == {}

        class _NoAttr:
            pass

        holder = _NoAttr()
        _record_phase_failed_status(
            holder, "historical_context", "cut", error_kind="timeout"
        )
        assert not hasattr(holder, "historical_context")


# =============================================================================
# Control 3 — the four render strings on default records are byte-identical
# =============================================================================


def test_the_four_default_renders_are_byte_identical():
    state = _FakeState()
    assert _format_historical_block(state.historical_context) == (
        "  (aucune situation historique — l'historien n'a rien rendu sur ce "
        "run ; ne comble pas ce vide par une histoire)"
    )
    assert _format_strategic_block(state.strategic_read) == (
        "  (aucune lecture stratégique — le stratège n'a rien rendu sur ce "
        "run ; ne produis pas la tienne)"
    )
    assert cross_passage_note(state) == (
        "[COHÉRENCE ENTRE PASSAGES ÉLOIGNÉS — contrôle par le raisonneur "
        "propositionnel]\n"
        "Contrôle non atteint : aucune incohérence rapportée."
    )
    assert coverage_review_note(state) == ""


# =============================================================================
# Control 4 — a capability outside the table leaves the four records alone
# =============================================================================


async def test_another_capabilitys_failure_leaves_the_four_records_alone():
    state = await _run_phase("quality_evaluation", _explodes, timeout=None)
    for capability, default in _default_records().items():
        assert getattr(state, capability) == default, capability


async def test_another_capabilitys_budget_cut_leaves_the_four_records_alone():
    state = await _run_phase("quality_evaluation", _slow, timeout=0.05)
    for capability, default in _default_records().items():
        assert getattr(state, capability) == default, capability


# =============================================================================
# Control 5 — a cut on one capability leaves its three siblings alone
# =============================================================================


@pytest.mark.parametrize("capability", FOUR)
async def test_a_cut_on_one_capability_leaves_its_siblings_alone(capability: str):
    state = await _run_phase(capability, _slow, timeout=0.05)
    for sibling, default in _default_records().items():
        if sibling == capability:
            continue
        assert getattr(state, sibling) == default, sibling


# =============================================================================
# Control 6 — a dict state works too (the writer's own dual convention)
# =============================================================================


async def test_the_failure_leg_writes_a_dict_state_as_well():
    state: dict[str, Any] = {
        key: copy.deepcopy(value) for key, value in _default_records().items()
    }
    state["errors"] = []
    state["structured_arg_status"] = {}
    state["log_error"] = lambda agent, message: state["errors"].append(
        {"agent_name": agent, "message": message}
    )
    # A dict state carries no attributes, so the executor's log_error guard
    # skips it; the failure leg is what must handle the mapping.
    result = await _run_phase("coverage_review", _slow, timeout=0.05, state=state)
    assert result is state
    assert state["coverage_review"]["status"] == "timeout"
    assert "0.05" in state["coverage_review"]["reason"]
