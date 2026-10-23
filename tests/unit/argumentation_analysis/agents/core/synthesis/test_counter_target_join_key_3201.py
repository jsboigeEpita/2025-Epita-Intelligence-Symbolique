"""#3201 — a counter artifact line carries its TARGET, the writer's join key.

The briefing built ``strategy=<…> score=<…> — <counter_content>`` for every
counter. The record itself carries ``target_arg_id`` (28 of 41 counters) or
``target_unresolved_reason`` (13 of 41), and neither reached the line. The writer
therefore bound counters to units by content resemblance: it attributed an
unresolved counter (ca_1) to the reply of arg_18 while the true rebuttals of
arg_18 (ca_4..ca_6) went uncited.

The repair is a join key on the line — not a writer rule, not a drop of the
unresolved counters (they are real rebuttals, merely unanchored), and not a
change to the producer that stamps ``target_arg_id``.

Every fixture here is synthetic: opaque ids (arg_a, ca_x) and invented filler
text. Deterministic — no JVM, no LLM, no network.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)

#: The producer's own wording when the echoed target resolves no offered id
#: (``state_writers.py``) — quoted, never invented here.
_UNRESOLVED_REASON = "target id absent from the run's identified arguments"


def _state(**fields) -> SimpleNamespace:
    base = dict(
        identified_arguments={},
        identified_fallacies={},
        counter_arguments=[],
        argument_quality_scores={},
        propositional_analysis_results=[],
        fol_analysis_results=[],
        modal_analysis_results=[],
        dung_frameworks={},
        jtms_retraction_chain=[],
        belief_revision_results=[],
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _counters() -> list:
    """One linked counter (ca_x → arg_a) and one unlinked (ca_y)."""
    return [
        {
            "id": "ca_x",
            "strategy": "direct_refutation",
            "score": 0.42,
            "counter_content": "invented filler alpha",
            "target_arg_id": "arg_a",
        },
        {
            "id": "ca_y",
            "strategy": "counter_example",
            "score": 0.31,
            "counter_content": "invented filler beta",
            "target_unresolved_reason": _UNRESOLVED_REASON,
        },
    ]


def _counter_lines(briefing: str) -> list:
    return [
        line
        for line in briefing.splitlines()
        if line.startswith("[artifact:counter_arguments.")
    ]


def _briefing(state) -> str:
    return DeepSynthesisAgent.build_artifact_briefing(state)


# ============================================================================
# The measured defect — the join key the writer was never given
# ============================================================================


class TestTheCounterLineCarriesItsTarget:
    def test_a_linked_counter_names_its_target(self):
        line = _counter_lines(_briefing(_state(counter_arguments=_counters())))[0]

        assert line.startswith("[artifact:counter_arguments.ca_x] ")
        assert "target=arg_a" in line

    def test_an_unlinked_counter_says_unresolved_and_why(self):
        line = _counter_lines(_briefing(_state(counter_arguments=_counters())))[1]

        assert line.startswith("[artifact:counter_arguments.ca_y] ")
        assert f"target=unresolved ({_UNRESOLVED_REASON})" in line

    def test_an_unresolved_counter_is_still_evidence(self):
        """Anti-pendulum: unanchored rebuttals are not dropped from the list."""
        lines = _counter_lines(_briefing(_state(counter_arguments=_counters())))

        assert len(lines) == 2
        assert "invented filler beta" in lines[1]

    def test_a_record_without_target_or_reason_fabricates_nothing(self):
        """Legacy shape: no target, no reason → ``target=unresolved`` alone."""
        legacy = [
            {
                "id": "ca_z",
                "strategy": "direct_refutation",
                "score": 0.2,
                "counter_content": "invented filler gamma",
            }
        ]
        line = _counter_lines(_briefing(_state(counter_arguments=legacy)))[0]

        assert "target=unresolved" in line
        assert "target=unresolved (" not in line


# ============================================================================
# Control — same lines, same order, same everything else, byte for byte
# ============================================================================


class TestTheLineIsTheOldLinePlusTheTarget:
    def test_the_linked_line_is_the_old_line_plus_the_target(self):
        line = _counter_lines(_briefing(_state(counter_arguments=_counters())))[0]

        assert line == (
            "[artifact:counter_arguments.ca_x] "
            "strategy=direct_refutation score=0.42 target=arg_a "
            "— invented filler alpha"
        )

    def test_the_unlinked_line_is_the_old_line_plus_the_target(self):
        line = _counter_lines(_briefing(_state(counter_arguments=_counters())))[1]

        assert line == (
            "[artifact:counter_arguments.ca_y] "
            "strategy=counter_example score=0.31 "
            f"target=unresolved ({_UNRESOLVED_REASON}) "
            "— invented filler beta"
        )

    def test_the_line_count_and_order_are_unchanged(self):
        """Adding the key on some records changes neither the set nor its order."""
        linked = _counters()
        no_targets = [
            {k: v for k, v in ca.items() if not k.startswith("target_")}
            for ca in linked
        ]

        with_keys = _counter_lines(_briefing(_state(counter_arguments=linked)))
        without_keys = _counter_lines(_briefing(_state(counter_arguments=no_targets)))

        assert len(with_keys) == len(without_keys) == 2
        assert [line.split("]")[0] for line in with_keys] == [
            line.split("]")[0] for line in without_keys
        ]

    def test_the_rest_of_the_briefing_is_byte_identical(self):
        """The key is the only difference: every other line is untouched."""
        linked = _counters()
        no_targets = [
            {k: v for k, v in ca.items() if not k.startswith("target_")}
            for ca in linked
        ]

        with_keys = _briefing(_state(counter_arguments=linked)).splitlines()
        without_keys = _briefing(_state(counter_arguments=no_targets)).splitlines()

        assert len(with_keys) == len(without_keys)
        for a, b in zip(with_keys, without_keys):
            if a.startswith("[artifact:counter_arguments."):
                continue
            assert a == b
