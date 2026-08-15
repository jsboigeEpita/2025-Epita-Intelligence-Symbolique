"""#1760 — the PM steers in a room whose description doesn't match it.

``phase_configs`` freezes 3 macro-phases with a hard-coded casting of 3-4
agents while ``AGENT_CONFIG["ProjectManager"]`` hands the PM a static map of
8 and a free-steering mandate. The PM designates real, wired agents that are
simply absent from the room it sits in — #1751 made the absorption
observable (``designation_unresolved`` markers); this lane carries the fix.

## Three voies, switchable, settled by measurement

* ``truth`` — the PM prompt names the actual roster of the current phase.
* ``reprompt`` — an absorbed designation hands the floor back to the PM with
  the present roster (capped per phase).
* ``all_agents`` — the room IS the full roster; no designation can be
  structurally impossible.

## What these tests assert — and refuse to assert

The DoD's first test demands an assertion on the **constructed prompt**, not
on the contents of ``AGENT_CONFIG``: a prompt that exists only as a config
entry has never been shown to a model. Conversely the anti-pendule test
demands a capability map that still names all eight specialists after the
fix — amputating the map to kill impossible designations would restore the
steering loss the mandate condemns ("restaurer la conduite est le but ; la
restreindre serait pire que le défaut").
"""

from unittest.mock import MagicMock

import pytest

from argumentation_analysis.orchestration.conversational_orchestrator import (
    _absorption_feedback,
    _apply_room_truth_to_pm,
    _fresh_absorbed_designation,
    _pm_instructions_with_room,
    _pm_room_section,
    _resolve_room_agents,
    ROOM_POLICY_ALL_AGENTS,
    ROOM_POLICY_PHASE_CASTING,
    ROOM_POLICY_REPROMPT,
    ROOM_POLICY_TRUTH,
    run_conversational_analysis,
)

# The phase-2 casting of the real ``phase_configs`` — where both measured
# absorptions of the R808 sweep were emitted from.
PHASE_2_CASTING = ["ProjectManager", "FormalAgent", "QualityAgent"]

# Every specialist the PM's capability map names. The room truth must not
# amputate this list (anti-pendule).
CAPABILITY_MAP_AGENTS = [
    "ExtractAgent",
    "InformalAgent",
    "FormalAgent",
    "QualityAgent",
    "CounterAgent",
    "DebateAgent",
    "GovernanceAgent",
    "JTMS",
]


def _agent(name: str) -> MagicMock:
    agent = MagicMock()
    agent.name = name
    return agent


def _state(text: str = "Texte argumentatif de test."):
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    return UnifiedAnalysisState(text)


class TestRoomTruthNamesTheExactRoster:
    """DoD #1: the constructed PM prompt names exactly the phase roster."""

    def test_room_section_names_every_present_agent(self):
        section = _pm_room_section(PHASE_2_CASTING)
        for name in PHASE_2_CASTING:
            assert name in section, f"{name} absent from the room section"

    def test_room_section_names_no_absent_agent(self):
        """ "Exactly" excludes the map-only specialists from the ROOM line."""
        section = _pm_room_section(PHASE_2_CASTING)
        absent = [
            n for n in CAPABILITY_MAP_AGENTS if n not in PHASE_2_CASTING and n != "JTMS"
        ]
        for name in absent:
            assert name not in section, (
                f"{name} is not in this phase's room but the room section "
                "names it — the prompt would describe the wrong room again"
            )

    def test_full_instructions_carry_the_room_and_keep_the_map(self):
        """The room truth is additive: 8-capability map stays, roster is named."""
        instructions = _pm_instructions_with_room(30, PHASE_2_CASTING)
        for name in PHASE_2_CASTING:
            assert name in instructions
        # The capability map is NOT amputated down to the roster (anti-pendule:
        # that would forbid the designations instead of steering them).
        for name in CAPABILITY_MAP_AGENTS:
            assert name in instructions, (
                f"{name} vanished from the PM capability map — the fix amputated "
                "the PM's steering knowledge instead of telling it the truth"
            )

    def test_room_section_does_not_accumulate_across_phases(self):
        """Rebuilt from the template each phase — phase 2's room must replace
        phase 1's, not stack on top of it."""
        pm = _agent("ProjectManager")
        pm.instructions = _pm_instructions_with_room(
            30, ["ProjectManager", "ExtractAgent", "InformalAgent"]
        )
        _apply_room_truth_to_pm(pm, PHASE_2_CASTING, 30)
        assert "ExtractAgent" in pm.instructions  # still on the capability map
        room_start = pm.instructions.index("SALLE ACTUELLE")
        room = pm.instructions[room_start:]
        assert "ExtractAgent" not in room, "phase 1's room leaked into phase 2's"
        assert pm.instructions.count("SALLE ACTUELLE") == 1

    def test_apply_room_truth_to_pm_is_a_noop_without_a_pm(self):
        _apply_room_truth_to_pm(None, PHASE_2_CASTING, 30)  # must not raise


class TestHonouredDesignationStaysHonoured:
    """DoD #2 (anti-pendule): green BEFORE the fix and green AFTER.

    A fix that breaks honoured designations, or that empties the defect by
    emptying the PM's steering, is the false fix.
    """

    def test_in_room_designation_is_still_selected(self):
        """Pre-existing behaviour on main: a designation inside the room is
        honoured by the selection strategy. Must survive every voie."""
        from argumentation_analysis.core.strategies import (
            DelegatingSelectionStrategy,
        )

        import asyncio

        state = _state()
        agents = [_agent(n) for n in PHASE_2_CASTING]
        strategy = DelegatingSelectionStrategy(agents, state)

        state.designate_next_agent("FormalAgent")
        selected = asyncio.run(strategy.next(agents, []))

        assert selected.name == "FormalAgent"
        markers = [
            r
            for r in state.deliberation_trace
            if r.get("record_type") == "designation_unresolved"
        ]
        assert markers == []

    def test_capability_map_still_names_all_eight(self):
        """The map is the PM's steering knowledge — pre-existing content that
        the fix must not amputate."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        instructions = AGENT_CONFIG["ProjectManager"]["instructions"]
        for name in CAPABILITY_MAP_AGENTS:
            assert name in instructions


class TestAllAgentsRoom:
    """Voie 3: the room IS the full roster — the defect becomes structurally
    impossible, not merely discouraged."""

    def test_policy_returns_the_full_roster(self):
        phase = [_agent(n) for n in PHASE_2_CASTING]
        every = [_agent(n) for n in CAPABILITY_MAP_AGENTS if n != "JTMS"]
        room = _resolve_room_agents(ROOM_POLICY_ALL_AGENTS, phase, every)
        assert [a.name for a in room] == [a.name for a in every]

    def test_other_policies_keep_the_phase_casting(self):
        phase = [_agent(n) for n in PHASE_2_CASTING]
        every = [_agent(n) for n in CAPABILITY_MAP_AGENTS if n != "JTMS"]
        for policy in (
            ROOM_POLICY_PHASE_CASTING,
            ROOM_POLICY_TRUTH,
            ROOM_POLICY_REPROMPT,
        ):
            room = _resolve_room_agents(policy, phase, every)
            assert [a.name for a in room] == PHASE_2_CASTING

    def test_strategy_over_full_roster_honours_off_casting_designation(self):
        """The measured defect (R808: CounterAgent designated from the
        phase-2 room, absorbed) is structurally impossible over the full
        roster: the designated agent IS in the room."""
        from argumentation_analysis.core.strategies import (
            DelegatingSelectionStrategy,
        )

        import asyncio

        state = _state()
        every = [_agent(n) for n in CAPABILITY_MAP_AGENTS if n != "JTMS"]
        strategy = DelegatingSelectionStrategy(every, state)

        state.designate_next_agent("CounterAgent")  # absent from phase-2 casting
        selected = asyncio.run(strategy.next(every, []))

        assert selected.name == "CounterAgent"
        markers = [
            r
            for r in state.deliberation_trace
            if r.get("record_type") == "designation_unresolved"
        ]
        assert markers == []


class TestAbsorptionReprompt:
    """Voie 2: the floor comes back to the PM with the present roster."""

    def test_fresh_marker_is_returned_only_when_the_count_grew(self):
        state = _state()
        assert _fresh_absorbed_designation(state, 0) is None  # nothing yet

        state.record_designation_unresolved(
            requested_agent="CounterAgent",
            present_agents=PHASE_2_CASTING,
            selection_path="delegating",
        )
        fresh = _fresh_absorbed_designation(state, 0)
        assert fresh is not None and fresh["requested_agent"] == "CounterAgent"
        # A marker from an earlier turn must not re-fire the re-prompt.
        assert _fresh_absorbed_designation(state, 1) is None

    def test_feedback_names_the_request_and_the_present_roster(self):
        feedback = _absorption_feedback("CounterAgent", PHASE_2_CASTING)
        assert "CounterAgent" in feedback
        for name in PHASE_2_CASTING:
            assert name in feedback, (
                f"{name} absent from the roster handed back to the PM — it "
                "cannot re-designate among agents it is not told are present"
            )


class TestPolicyValidation:
    def test_unknown_room_policy_fails_loud(self):
        """Anti-#1019: a typo'd policy must not silently run the baseline and
        pass itself off as a variant row."""
        import asyncio

        with pytest.raises(ValueError, match="room_policy"):
            asyncio.run(
                run_conversational_analysis(
                    text="x", room_policy="room8"  # plausible typo
                )
            )
