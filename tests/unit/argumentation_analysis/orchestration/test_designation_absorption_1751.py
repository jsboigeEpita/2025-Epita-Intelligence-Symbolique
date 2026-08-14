"""#1751 — an off-casting PM designation must never be silently absorbed.

The conversational PM gets a free-steering mandate and a map of 8 agents, but
it never sits in a room of 8: ``conversational_orchestrator.phase_configs``
freezes three phases with a hard-coded casting of 3-4 agents each, and the
``AgentGroupChat`` is built per phase with that casting alone. When the PM
designates an agent outside its room, the selection strategy logs and falls
through to the default agent — which, the PM being first in every casting, is
**the PM itself**. The designation is recorded in the deliberation trace, so
the trace says "I convene X" while the execution shows the PM taking the floor
again.

Measured on ``sweep_1735_R808_A`` / corpus_A: 13 designations, **2 absorbed**
(``InformalAgent``, ``CounterAgent``), both emitted from the phase-2 room.

## Three sites, not the one the issue named

The issue named ``core/strategies.py:195-204``. Grepping the *shape* rather
than the line turns up three:

===========================================  =========================  =======
site                                         falls back to              log
===========================================  =========================  =======
``DelegatingSelectionStrategy.next``         default agent (= the PM)   ERROR
``BalancedParticipationStrategy.next``       participation balancing    ERROR
``conversational_orchestrator._select_...``  round-robin                DEBUG
===========================================  =========================  =======

## What these tests assert — and what they refuse to assert

The DoD requires an assertion on the **effect**, not on the log. A log line is
not an effect: nothing downstream reads it, and asserting on ``caplog`` would
have passed against a fix that only reworded the message.

They also refuse the weaker reading "an absorbed designation leaves its record
open, so the trace already carries the information". It does not discriminate:
a record left open is *equally* the signature of (a) an absorbed designation,
(b) a designation whose agent simply has not spoken yet, and (c) a run cut by
the wall-clock cap before the agent returned. Three causes, one signature —
:class:`TestAbsorbedIsDistinguishableFromPending` pins exactly that.
"""

import asyncio
from unittest.mock import MagicMock

import pytest


def _agent(name: str) -> MagicMock:
    agent = MagicMock()
    agent.name = name
    return agent


def _state(text: str = "Texte argumentatif de test."):
    """The state the conversational path actually runs on.

    The deliberation trace (and the whole designation-record API) lives on
    ``UnifiedAnalysisState``, NOT on its ``RhetoricalAnalysisState`` base — the
    selection strategies only type-check the base, so the recording call has to
    stay optional. :func:`test_base_state_without_a_trace_still_selects` is the
    control for that.
    """
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    return UnifiedAnalysisState(text)


def _unresolved(state) -> list:
    """The unresolved-designation markers in a state's deliberation trace."""
    return [
        r
        for r in getattr(state, "deliberation_trace", [])
        if r.get("record_type") == "designation_unresolved"
    ]


# The phase-2 casting of the real ``phase_configs``, which is where both
# measured absorptions were emitted from.
PHASE_2_CASTING = ["ProjectManager", "FormalAgent", "QualityAgent"]


class TestOffCastingDesignationLeavesAnObservableEffect:
    """The defect: designating an absent agent produces nothing readable."""

    def test_delegating_strategy_records_an_unresolved_marker(self):
        from argumentation_analysis.core.strategies import (
            DelegatingSelectionStrategy,
        )

        state = _state()
        agents = [_agent(n) for n in PHASE_2_CASTING]
        strategy = DelegatingSelectionStrategy(agents, state)

        state.designate_next_agent("InformalAgent")  # not in the phase-2 room
        selected = asyncio.run(strategy.next(agents, []))

        # The run is not aborted — the PM still takes the floor.
        assert selected.name == "ProjectManager"
        # ...but the floor it takes is no longer indistinguishable from an
        # honoured turn.
        markers = _unresolved(state)
        assert len(markers) == 1, (
            "an off-casting designation must leave a readable trace entry, "
            f"got {state.deliberation_trace!r}"
        )

    def test_the_marker_names_the_request_and_the_room(self):
        """A count says there is a problem; the corrective action needs names."""
        from argumentation_analysis.core.strategies import (
            DelegatingSelectionStrategy,
        )

        state = _state()
        agents = [_agent(n) for n in PHASE_2_CASTING]
        strategy = DelegatingSelectionStrategy(agents, state)

        state.designate_next_agent("CounterAgent")
        asyncio.run(strategy.next(agents, []))

        marker = _unresolved(state)[0]
        assert marker["requested_agent"] == "CounterAgent"
        # The roster actually present is what a re-prompt would have to hand
        # back to the PM, and what tells a reader "wrong room", not "typo".
        assert sorted(marker["present_agents"]) == sorted(PHASE_2_CASTING)

    def test_balanced_strategy_absorbs_the_same_way(self):
        """Sibling site — same shape, same silence, different fallback."""
        from argumentation_analysis.core.strategies import (
            BalancedParticipationStrategy,
        )

        state = _state()
        agents = [_agent(n) for n in PHASE_2_CASTING]
        strategy = BalancedParticipationStrategy(
            agents, state, default_agent_name="ProjectManager"
        )

        state.designate_next_agent("InformalAgent")
        asyncio.run(strategy.next(agents, []))

        assert len(_unresolved(state)) == 1

    def test_round_robin_path_absorbs_the_same_way(self):
        """Third site: the non-AgentGroupChat path, at DEBUG level."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _select_next_agent,
        )

        state = _state()
        agents = [_agent(n) for n in PHASE_2_CASTING]

        state.designate_next_agent("InformalAgent")
        selected = _select_next_agent(state, agents, turn=0)

        assert selected in agents  # round-robin still yields someone
        assert len(_unresolved(state)) == 1


class TestHonouredDesignationIsUnaffected:
    """Anti-pendulum — GREEN before the fix and after.

    Without this half, "fixing" the absorption could mean marking every
    designation, or refusing designations altogether. Both would be worse than
    the defect: the PM's steering is the thing #1751 is trying to restore, not
    remove.
    """

    def test_honoured_designation_returns_the_designated_agent(self):
        from argumentation_analysis.core.strategies import (
            DelegatingSelectionStrategy,
        )

        state = _state()
        agents = [_agent(n) for n in PHASE_2_CASTING]
        strategy = DelegatingSelectionStrategy(agents, state)

        state.designate_next_agent("FormalAgent")  # in the room
        selected = asyncio.run(strategy.next(agents, []))

        assert selected.name == "FormalAgent"

    def test_honoured_designation_records_no_marker(self):
        from argumentation_analysis.core.strategies import (
            DelegatingSelectionStrategy,
        )

        state = _state()
        agents = [_agent(n) for n in PHASE_2_CASTING]
        strategy = DelegatingSelectionStrategy(agents, state)

        state.designate_next_agent("QualityAgent")
        asyncio.run(strategy.next(agents, []))

        assert _unresolved(state) == []

    def test_no_designation_at_all_records_no_marker(self):
        """Absence of a designation is not a failed designation."""
        from argumentation_analysis.core.strategies import (
            DelegatingSelectionStrategy,
        )

        state = _state()
        agents = [_agent(n) for n in PHASE_2_CASTING]
        strategy = DelegatingSelectionStrategy(agents, state)

        asyncio.run(strategy.next(agents, []))

        assert _unresolved(state) == []

    def test_base_state_without_a_trace_still_selects(self):
        """A state that carries no trace must not become a crash site.

        ``RhetoricalAnalysisState`` (the base the strategies type-check) has no
        deliberation trace at all. Recording is therefore best-effort: the
        selection must behave exactly as before on such a state. Without this,
        "make the absorption loud" would turn every non-conversational caller
        of the strategy into an ``AttributeError``.
        """
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
        from argumentation_analysis.core.strategies import (
            DelegatingSelectionStrategy,
        )

        state = RhetoricalAnalysisState("t")
        agents = [_agent(n) for n in PHASE_2_CASTING]
        strategy = DelegatingSelectionStrategy(agents, state)

        state.designate_next_agent("InformalAgent")
        selected = asyncio.run(strategy.next(agents, []))

        assert selected.name == "ProjectManager"


class TestAbsorbedIsDistinguishableFromPending:
    """The defect stated exactly: two different situations, one trace.

    Both states below end with a designation whose agent has not spoken. In one
    the agent was absent from the room (absorbed, and never coming); in the
    other it is present and simply has not had its turn yet. Before the fix the
    two traces are **byte-identical**, so no reader can tell "the chief was
    contradicted" from "the chief is waiting".
    """

    @staticmethod
    def _trace_after_designating(target: str, casting: list) -> list:
        from argumentation_analysis.core.strategies import (
            DelegatingSelectionStrategy,
        )

        state = _state()
        agents = [_agent(n) for n in casting]
        strategy = DelegatingSelectionStrategy(agents, state)
        # The PM motivates, then designates — the real order (CONV-C #1334).
        state.record_designation(
            agent=target,
            motivation="Motivation identique dans les deux branches.",
            trigger="deepening",
        )
        state.designate_next_agent(target)
        asyncio.run(strategy.next(agents, []))
        return state.deliberation_trace

    def test_the_two_traces_differ_by_exactly_the_marker(self):
        absorbed = self._trace_after_designating("InformalAgent", PHASE_2_CASTING)
        pending = self._trace_after_designating("FormalAgent", PHASE_2_CASTING)

        # Guard against a tautology: the DesignationRecord carries no clock and
        # no uuid, so the only thing that may differ is the designated name and
        # the marker itself. Neutralise the name so the comparison is about the
        # marker alone.
        def _normalised(trace):
            out = []
            for record in trace:
                record = dict(record)
                record.pop("designated_agent", None)
                record.pop("requested_agent", None)
                out.append(record)
            return out

        assert _normalised(absorbed) != _normalised(pending), (
            "an absorbed designation and a merely-pending one produce the same "
            "trace — nothing downstream can tell them apart"
        )
        assert len(absorbed) == len(pending) + 1
        assert absorbed[-1]["record_type"] == "designation_unresolved"


class TestTheMarkerDoesNotCorruptItsReaders:
    """A new record type is a new hop for every reader of the trace.

    ``deliberation_turn_count`` used to count every record that was not a
    ``cap_breach`` — an exclusion list that silently absorbs each marker type
    added after it. These two tests are the reason the reader was flipped to an
    allow-list (a designation is a record carrying **no** ``record_type``).
    """

    def test_marker_is_not_counted_as_a_deliberation_turn(self):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _deliberation_turn_count,
        )

        state = _state()
        state.record_designation(agent="FormalAgent", motivation="m", trigger="initial")
        assert _deliberation_turn_count(state) == 1

        state.record_designation_unresolved(
            requested_agent="InformalAgent", present_agents=PHASE_2_CASTING
        )
        state.record_cap_breach(cap_kind="wall_clock", turn=1, detail="d")

        assert (
            _deliberation_turn_count(state) == 1
        ), "markers must not inflate the published turn count"

    def test_marker_does_not_block_backfill_of_an_open_designation(self):
        """A marker sitting on top of an open record must be stepped over."""
        state = _state()
        state.record_designation(agent="FormalAgent", motivation="m", trigger="initial")
        state.record_designation_unresolved(
            requested_agent="InformalAgent", present_agents=PHASE_2_CASTING
        )

        assert state.backfill_last_designation_for("FormalAgent") is True
        designations = [
            r for r in state.deliberation_trace if r.get("record_type") is None
        ]
        assert designations[0]["state_fingerprint_after"] is not None


class TestPhaseCastingDropIsVisible:
    """Scope item 3: a phase name absent from ``agent_by_name`` is dropped.

    ``phase_agents = [agent_by_name[n] for n in phase_agent_names if n in
    agent_by_name]`` silently shrinks the room. A phase that runs with 2 of its
    4 agents is not the phase that was configured, and nothing said so.
    """

    def test_missing_phase_agents_are_named(self):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _resolve_phase_agents,
        )

        agent_by_name = {"ProjectManager": _agent("ProjectManager")}
        resolved, missing = _resolve_phase_agents(
            agent_by_name, ["ProjectManager", "QualityAgent", "FormalAgent"]
        )

        assert [a.name for a in resolved] == ["ProjectManager"]
        assert sorted(missing) == ["FormalAgent", "QualityAgent"]


@pytest.mark.parametrize("target", ["InformalAgent", "CounterAgent"])
def test_the_two_absorptions_measured_on_corpus_a_are_now_visible(target):
    """End-to-end on the exact pair observed in ``sweep_1735_R808_A``.

    Both were emitted from the phase-2 room. This is the run-level statement of
    the defect, kept separate from the unit tests so a change in the phase
    casting shows up here rather than silently weakening them.
    """
    from argumentation_analysis.core.strategies import DelegatingSelectionStrategy

    state = _state()
    agents = [_agent(n) for n in PHASE_2_CASTING]
    strategy = DelegatingSelectionStrategy(agents, state)

    state.designate_next_agent(target)
    asyncio.run(strategy.next(agents, []))

    markers = _unresolved(state)
    assert [m["requested_agent"] for m in markers] == [target]
