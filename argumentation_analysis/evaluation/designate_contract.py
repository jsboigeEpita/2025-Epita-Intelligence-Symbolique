"""PARITY ORACLE for the ``designate`` runtime-export contract (#1983).

This module answers the second item of the external analysis that proposed
replacing "reuse EPITA" with a *tiny runtime-export contract* — six runtime
operations (designate, handoff, observe/commit, resolveCapability,
terminate/budget, actExternally), each with an EXISTING EPITA behaviour as its
parity oracle, then a minimal autonomous implementation. This issue opens ONLY
the first operation, deliberately not an Epic.

## Why designate first

It is the only one of the six that is simultaneously the best-instrumented
here and absent downstream (measured by ``scripts/coursia/check_vendored_drift.py``,
recorded in ``docs/architecture/COURSIA_ESSENCE_EXPORT.md``): the vended CoursIA
fork carries ``_shared_state.py`` at 1121 lines against 1483 upstream, and is
missing ``DesignationRecord``, ``record_designation``, ``_designation_fingerprint``,
``backfill_last_designation_for``, ``_designation_delta_summary``,
``record_cap_breach``. The ``@kernel_function record_designation`` is missing from
``_state_manager_plugin.py`` too — so downstream the operation has NO callable
surface. A parity oracle can only be built here.

This is an EXTRACTION, not a rewrite: every check below points to the
issue-numbered ground-truth test it was derived from, so a future minimal
implementation (the follow-up issue, decided at the oracle's evidence) can be
squared against it without re-deriving the contract.

## SPEC — the ``designate`` contract, in observable terms

### Signature (surface CONV-C, on ``UnifiedAnalysisState``)

    record_designation(agent, motivation, trigger, turn=None) -> int
    backfill_last_designation_for(agent) -> bool
    designate_next_agent(agent_name) -> None
    record_designation_unresolved(requested_agent, present_agents, turn=None,
                                  selection_path="") -> None
    record_cap_breach(cap_kind, turn, detail="") -> None

### Signature (tactical mirror, on ``TacticalState``, #1735)

    record_allocation_motivation(task_id, motivation) -> bool

### Signature (room resolution, module-level, #1760)

    _resolve_room_agents(room_policy, phase_agents, all_agents) -> list

### Pre-conditions

- ``agent`` is the exact name of a designated specialist.
- ``motivation`` is the PM's *why now* (1-2 sentences) — the central CONV-C
  requirement: designations are motivated, not round-robin.
- ``trigger`` in {"initial", "deepening", "synergy", "convergence"}.
- ``turn`` defaults to ``len(trace)+1`` so the PM need not track it.
- ``room_policy`` is one of the four documented policies (phase_casting,
  truth, reprompt, all_agents); any other value fails loud.

### Post-conditions / what must remain observable

1. **The designation** is recorded in ``deliberation_trace`` as a record
   carrying ``designated_agent``, ``motivation``, ``trigger``, ``turn``, with
   an auto-derived turn and the explicit turn honored.
2. **Its motivation** is carried by the record — the "why" is never dropped.
3. **Its fingerprint** (``state_fingerprint_before``) is captured at the
   moment of the designation (a lightweight count of the dimensions the PM
   reasons about); ``state_fingerprint_after``/``delta_summary`` are ``None``
   until the designated agent returns.
4. **The backfill after action** closes the record when — and only when —
   the designated agent actually returns: ``backfill_last_designation_for``
   sets ``state_fingerprint_after`` + ``delta_summary`` for the matching
   agent, leaves an open record for a non-matching one, and steps over any
   marker sitting on top of the open record.

### Consumer invariants (why it matters downstream)

- A delegation outside the room leaves a READABLE trace entry
  (``designation_unresolved`` marker with the requested agent and the present
  roster), distinguishable from a merely-pending designation.
- The published turn count (both readers, #1765) counts designations by
  allow-list — no marker inflates it.
- The room is a SWITCHABLE policy: under ``all_agents`` the room is the full
  roster, so an off-casting designation is structurally possible rather than
  merely discouraged; the other policies keep the phase casting.

## Anti-pendules binding on this issue

- No autonomous implementation here — the spec and oracle first. The minimal
  implementation is the follow-up, decided at the oracle's evidence.
- Not an Epic: exactly one contract, not the six.
- The oracle must pass against the CURRENT implementation WITHOUT modifying
  it (if ``shared_state.py`` must change to make it pass, the oracle is wrong).
- Do not treat the downstream absence as proof of intent — what is measured is
  that the vendored file reproduces neither HEAD nor the pinned commit
  (verdict ``partial``). The parity oracle is what lets that be settled.

The LLM-free deterministic checks below reproduce, on an injectable subject,
the observable parts of the four ground-truth tests. Each check receives a
FRESH subject (via the ``subject_factory``) so the checks are independent and
a degraded subject reddens precisely the check it violates. They are meant to
be run against the current ``UnifiedAnalysisState`` (all green) and against a
degraded subject (a designation with no motivation, or with no backfill) to
show the oracle reddens.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List

# ---------------------------------------------------------------------------
# Outcome types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    """The verdict of one observable check on the designate contract.

    ``observable`` is the contract item being asserted. ``test_source`` is the
    issue-numbered ground-truth test the assertion was extracted from — this is
    what makes the oracle an extraction rather than a rewrite. ``passed`` is
    the boolean verdict; ``detail`` explains a failure or cites a green path.
    """

    observable: str
    test_source: str
    passed: bool
    detail: str


@dataclass
class DesignateAssessment:
    """Aggregate verdict over the designate contract checks."""

    checks: List[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.passed]

    def __bool__(self) -> bool:
        return self.passed


# ---------------------------------------------------------------------------
# Observable-check builders (each extracts ONE test's lesson)
# ---------------------------------------------------------------------------
# Every check receives a FRESH ``subject`` built by the caller's
# ``subject_factory``, so the checks never contaminate one another and a
# degraded subject flips exactly the check it violates.


def _check_designation_recorded(subject: Any) -> CheckResult:
    """A designation is recorded with agent/trigger/turn (derived turn)."""
    turn = subject.record_designation(
        "FormalAgent", "raison de la designation", "deepening"
    )
    last = subject.deliberation_trace[-1]
    ok = (
        len(subject.deliberation_trace) == 1
        and last["designated_agent"] == "FormalAgent"
        and last["trigger"] == "deepening"
        and last["turn"] == turn == 1
    )
    detail = (
        f"designation recorded (turn={turn}, agent=FormalAgent, trigger=deepening)"
        if ok
        else f"designation NOT recorded as expected: trace={subject.deliberation_trace!r}"
    )
    return CheckResult("designation_recorded", test_1334_designation_source, ok, detail)


def _check_auto_increment_turn(subject: Any) -> CheckResult:
    """Turn auto-derives (len(trace)+1) so the PM does not track it."""
    # Fresh subject → trace starts empty, so turns are (1, 2, 3).
    t1 = subject.record_designation("ExtractAgent", "etat vide", "initial")
    t2 = subject.record_designation(
        "InformalAgent", "extraire les sophismes", "deepening"
    )
    t3 = subject.record_designation("QualityAgent", "evaluer la qualite", "synergy")
    ok = (t1, t2, t3) == (1, 2, 3)
    detail = (
        f"auto-increment turns = {(t1, t2, t3)}"
        if ok
        else f"turns = {(t1, t2, t3)}, expected (1,2,3)"
    )
    return CheckResult(
        "designation_turn_auto_increments", test_1334_designation_source, ok, detail
    )


def _check_motivation_carried(subject: Any) -> CheckResult:
    """The record carries its motivation — the "why" is never dropped.

    CONV-C central requirement: designations are motivated, not round-robin.
    A designation whose record carries no motivation is the defect (also the
    object of the tactical mirror #1735).
    """
    subject.record_designation("InformalAgent", "contradiction sur arg_3", "deepening")
    motivation = subject.deliberation_trace[-1].get("motivation")
    ok = bool(motivation) and "contradiction" in motivation
    detail = (
        f"motivation carried: {motivation!r}"
        if ok
        else f"motivation empty/absent: {motivation!r} — designation without a why"
    )
    return CheckResult(
        "designation_motivation_carried", test_1735_motivation_source, ok, detail
    )


def _check_fingerprint_before(subject: Any) -> CheckResult:
    """The state fingerprint is captured before, None after, until backfill."""
    subject.add_identified_arguments(["premisses: P conclusion: Q"])
    subject.record_designation(
        "FormalAgent", "argument extrait, formaliser", "deepening"
    )
    record = subject.deliberation_trace[-1]
    fp = record.get("state_fingerprint_before")
    ok = (
        fp is not None
        and fp.get("argument_count") == 1
        and record.get("state_fingerprint_after") is None
        and record.get("delta_summary") is None
    )
    detail = (
        f"fingerprint before={fp}, after/delta=None"
        if ok
        else f"fingerprint before={fp}, after={record.get('state_fingerprint_after')!r}, delta={record.get('delta_summary')!r}"
    )
    return CheckResult(
        "designation_fingerprint_before", test_1334_fingerprint_source, ok, detail
    )


def _check_backfill_after_matching_agent(subject: Any) -> CheckResult:
    """Backfill closes the record when the designated agent returns."""
    subject.add_identified_arguments(["premisses: P conclusion: Q"])
    subject.record_designation("FormalAgent", "formaliser", "deepening")
    closed = subject.backfill_last_designation_for("FormalAgent")
    record = subject.deliberation_trace[-1]
    ok = (
        closed is True
        and record.get("state_fingerprint_after") is not None
        and record.get("delta_summary") is not None
    )
    detail = (
        f"backfill closed record: after={record.get('state_fingerprint_after')}, delta={record.get('delta_summary')!r}"
        if ok
        else f"backfill return={closed}, after={record.get('state_fingerprint_after')!r}, delta={record.get('delta_summary')!r}"
    )
    return CheckResult(
        "designation_backfill_after_matching", test_1334_backfill_source, ok, detail
    )


def _check_backfill_leaves_non_matching_open(subject: Any) -> CheckResult:
    """Backfill does NOT close a record for a different agent.

    The record is closed only when ``agent`` matches ``designated_agent`` —
    not the PM speaking its own freshly-opened record, nor a round-robin
    interloper.
    """
    subject.record_designation("FormalAgent", "motivation", "initial")
    closed = subject.backfill_last_designation_for("QualityAgent")
    record = subject.deliberation_trace[-1]
    ok = closed is False and record.get("state_fingerprint_after") is None
    detail = (
        f"non-matching open record preserved (return={closed}, after=None)"
        if ok
        else f"non-matching backfill returned {closed}, after={record.get('state_fingerprint_after')!r}"
    )
    return CheckResult(
        "designation_backfill_non_matching_open", test_1334_backfill_source, ok, detail
    )


def _check_backfill_steps_over_marker(subject: Any) -> CheckResult:
    """A marker on top of an open record must be stepped over (#1751)."""
    subject.record_designation("FormalAgent", "motivation", "initial")
    subject.record_designation_unresolved(
        requested_agent="InformalAgent",
        present_agents=["ProjectManager", "FormalAgent", "QualityAgent"],
    )
    closed = subject.backfill_last_designation_for("FormalAgent")
    designations = [
        r for r in subject.deliberation_trace if r.get("record_type") is None
    ]
    ok = (
        closed is True
        and designations
        and designations[0].get("state_fingerprint_after") is not None
    )
    detail = (
        "backfill stepped over the marker and closed the real record"
        if ok
        else f"backfill return={closed}, designations={designations!r}"
    )
    return CheckResult(
        "designation_backfill_steps_over_marker", test_1751_marker_source, ok, detail
    )


def _check_absorption_leaves_readable_marker(subject: Any) -> CheckResult:
    """A designation outside the room leaves a readable trace entry (#1751).

    A count says there is a problem; the corrective action needs names — the
    marker names the requested agent and the present roster so a reader can
    tell "wrong room" from "typo".
    """
    subject.record_designation_unresolved(
        requested_agent="CounterAgent",
        present_agents=["ProjectManager", "FormalAgent", "QualityAgent"],
    )
    markers = [
        r
        for r in subject.deliberation_trace
        if r.get("record_type") == "designation_unresolved"
    ]
    ok = (
        len(markers) == 1
        and markers[0]["requested_agent"] == "CounterAgent"
        and sorted(markers[0]["present_agents"])
        == sorted(["ProjectManager", "FormalAgent", "QualityAgent"])
    )
    detail = (
        f"unresolved marker names request+roster: {markers[0]!r}"
        if ok
        else f"no readable marker: trace={subject.deliberation_trace!r}"
    )
    return CheckResult(
        "absorption_readable_marker", test_1751_absorption_source, ok, detail
    )


def _check_turn_count_allowlist(subject: Any) -> CheckResult:
    """The published turn count counts designations, not markers (#1751/#1765).

    A designation is a record carrying no ``record_type``; markers must not
    inflate the published turn count.
    """
    subject.record_designation("FormalAgent", "m", "initial")
    subject.record_designation_unresolved(
        requested_agent="InformalAgent",
        present_agents=["ProjectManager", "FormalAgent", "QualityAgent"],
    )
    subject.record_cap_breach(cap_kind="wall_clock", turn=1, detail="d")
    count = subject.get_state_snapshot(summarize=True)["deliberation_turn_count"]
    ok = count == 1
    detail = (
        f"published turn count = {count} (1 designation, markers excluded)"
        if ok
        else f"published turn count = {count}, expected 1"
    )
    return CheckResult("turn_count_allowlist", test_1751_count_source, ok, detail)


def _check_room_all_agents_returns_full_roster() -> CheckResult:
    """The room is a switchable policy: all_agents → full roster (#1760)."""
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        ROOM_POLICY_ALL_AGENTS,
        ROOM_POLICY_PHASE_CASTING,
        ROOM_POLICY_REPROMPT,
        ROOM_POLICY_TRUTH,
        _resolve_room_agents,
    )

    phase = ["ProjectManager", "FormalAgent", "QualityAgent"]
    every = [
        "ExtractAgent",
        "InformalAgent",
        "FormalAgent",
        "QualityAgent",
        "CounterAgent",
        "DebateAgent",
        "GovernanceAgent",
    ]
    ok_all = _resolve_room_agents(ROOM_POLICY_ALL_AGENTS, phase, every) == every
    ok_others = all(
        _resolve_room_agents(policy, phase, every) == phase
        for policy in (
            ROOM_POLICY_PHASE_CASTING,
            ROOM_POLICY_TRUTH,
            ROOM_POLICY_REPROMPT,
        )
    )
    ok = ok_all and ok_others
    detail = (
        "room policy switchable: all_agents→full roster, others→phase casting"
        if ok
        else f"room not switchable (all_agents ok={ok_all}, others ok={ok_others})"
    )
    return CheckResult("room_policy_switchable", test_1760_room_source, ok, detail)


def _check_room_policy_unknown_fails_loud() -> CheckResult:
    """A typo'd policy must fail loud, not silently run the baseline (#1760)."""
    import asyncio

    from argumentation_analysis.orchestration.conversational_orchestrator import (
        run_conversational_analysis,
    )

    try:
        asyncio.run(run_conversational_analysis(text="x", room_policy="room8"))
    except ValueError as exc:
        ok = "room_policy" in str(exc)
        detail = (
            f"unknown policy failed loud (ValueError: {exc})"
            if ok
            else f"ValueError not about room_policy: {exc}"
        )
    except Exception as exc:  # noqa: BLE001 - any loud failure beats silent baseline
        return CheckResult(
            "room_policy_unknown_fails_loud",
            test_1760_room_source,
            False,
            f"unexpected failure type: {type(exc).__name__}: {exc}",
        )
    else:
        return CheckResult(
            "room_policy_unknown_fails_loud",
            test_1760_room_source,
            False,
            "unknown policy did NOT fail loud — it silently ran the baseline",
        )
    return CheckResult(
        "room_policy_unknown_fails_loud", test_1760_room_source, ok, detail
    )


# ---------------------------------------------------------------------------
# Assess entry points
# ---------------------------------------------------------------------------
# Each takes a ``subject_factory`` (a zero-arg callable returning a FRESH
# subject) so every check runs against an isolated state — the checks are
# independent, and a degraded factory reddens exactly the check it violates.
#


def assess_designate_subject(subject_factory: Callable[[], Any]) -> DesignateAssessment:
    """Run the CONV-C designate checks against a factory of subjects.

    ``subject_factory`` returns a fresh object with the designate surface
    (``record_designation``, ``backfill_last_designation_for``,
    ``deliberation_trace``, ``record_designation_unresolved``,
    ``record_cap_breach``, ``get_state_snapshot``, ``add_identified_arguments``).
    Against the current ``UnifiedAnalysisState`` every check passes; against a
    degraded factory (no motivation, or no backfill) the relevant check reddens.
    """
    checks = [
        _check_designation_recorded(subject_factory()),
        _check_auto_increment_turn(subject_factory()),
        _check_motivation_carried(subject_factory()),
        _check_fingerprint_before(subject_factory()),
        _check_backfill_after_matching_agent(subject_factory()),
        _check_backfill_leaves_non_matching_open(subject_factory()),
        _check_backfill_steps_over_marker(subject_factory()),
        _check_absorption_leaves_readable_marker(subject_factory()),
        _check_turn_count_allowlist(subject_factory()),
    ]
    return DesignateAssessment(checks=checks)


def assess_designate_motivation_mirror(
    subject_factory: Callable[[], Any],
) -> DesignateAssessment:
    """Run the tactical-mirror motivation checks (#1735).

    The tactical tier records *why* it allocates each task, mirroring the
    CONV-C record_designation. The write point refuses a blank motivation —
    the defect (allocation without a why) the write point exists to forbid.
    This surface is a separate state object (``TacticalState``), hence its own
    entry point.
    """
    checks = [
        _check_mirror_blank_motivation_refused(subject_factory()),
        _check_mirror_real_motivation_accepted(subject_factory()),
    ]
    return DesignateAssessment(checks=checks)


def assess_designate_room_policy() -> DesignateAssessment:
    """Run the room-policy checks (#1760).

    These are module-level (they do not depend on a state subject) and verify
    that the room the PM steers in is a switchable policy and that an unknown
    policy fails loud.
    """
    return DesignateAssessment(
        checks=[
            _check_room_all_agents_returns_full_roster(),
            _check_room_policy_unknown_fails_loud(),
        ]
    )


def _check_mirror_blank_motivation_refused(subject: Any) -> CheckResult:
    """A blank motivation must be refused at the write point (#1735)."""
    try:
        subject.record_allocation_motivation("task-1", "   ")
    except ValueError:
        return CheckResult(
            "tactical_motivation_blank_refused",
            test_1735_mirror_source,
            True,
            "blank motivation refused (ValueError 'non vide')",
        )
    return CheckResult(
        "tactical_motivation_blank_refused",
        test_1735_mirror_source,
        False,
        "blank motivation was NOT refused — allocation without a why is possible",
    )


def _check_mirror_real_motivation_accepted(subject: Any) -> CheckResult:
    """A real motivation passes and is stored stripped (#1735)."""
    stored = None
    try:
        ok = subject.record_allocation_motivation("task-1", "  raison réelle  ") is True
        stored = subject.task_assignments_motivation.get("task-1")
    except AttributeError:
        ok = False
    ok = ok and stored == "raison réelle"
    return CheckResult(
        "tactical_motivation_real_accepted",
        test_1735_mirror_source,
        ok,
        (
            f"real motivation stored={stored!r}"
            if ok
            else f"real motivation not stored as expected: {stored!r}"
        ),
    )


# ---------------------------------------------------------------------------
# Ground-truth test citations (the oracle points AT these, never rewrites)
# ---------------------------------------------------------------------------

test_1334_designation_source = "tests/unit/argumentation_analysis/test_conv_c_deliberation_trace_1334.py::test_record_designation_appends_motivated_record"
test_1334_fingerprint_source = "tests/unit/argumentation_analysis/test_conv_c_deliberation_trace_1334.py::test_designation_fingerprint_reflects_state_growth"
test_1334_backfill_source = "tests/unit/argumentation_analysis/test_conv_c_deliberation_trace_1334.py (#1334 phase 3 backfill; test_record_designation_appends_motivated_record)"
test_1735_motivation_source = "tests/unit/argumentation_analysis/orchestration/hierarchical/test_delegation_motivated_designation_1735.py::test_every_allocation_carries_non_empty_motivation"
test_1735_mirror_source = "tests/unit/argumentation_analysis/orchestration/hierarchical/test_delegation_motivated_designation_1735.py::test_blank_motivation_is_refused"
test_1751_marker_source = "tests/unit/argumentation_analysis/orchestration/test_designation_absorption_1751.py::test_marker_does_not_block_backfill_of_an_open_designation"
test_1751_absorption_source = "tests/unit/argumentation_analysis/orchestration/test_designation_absorption_1751.py::test_the_marker_names_the_request_and_the_room"
test_1751_count_source = "tests/unit/argumentation_analysis/orchestration/test_designation_absorption_1751.py::test_marker_is_not_counted_as_a_deliberation_turn"
test_1760_room_source = "tests/unit/argumentation_analysis/orchestration/test_steering_room_1760.py::test_unknown_room_policy_fails_loud"
