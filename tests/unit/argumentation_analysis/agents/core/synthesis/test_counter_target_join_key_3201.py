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


# ============================================================================
# Rework (coordinator review) — items 2/3 of the issue: the licence the key
# grants, and the report-builder join that still matched by resemblance
# ============================================================================


class TestTheBriefingLicensesTheTarget:
    """The line carries the key; nothing said what the key licenses.

    The R1109 render banded two raw scores (« moderate to high ») and bound an
    unresolved counter to a unit by resemblance — with no licence stated, the
    writer supplied the inference. The licence rides next to the line, the
    same place the cause classes state theirs (#3123).
    """

    def test_the_briefing_states_what_a_target_licenses(self):
        briefing = _briefing(_state(counter_arguments=_counters()))
        assert "READING RULES" in briefing
        assert (
            "a counter is the rebuttal of a unit only when its line says "
            "target=<that unit>" in briefing
        )
        assert "never as any unit's rebuttal" in briefing

    def test_the_briefing_states_that_a_score_is_raw(self):
        briefing = _briefing(_state(counter_arguments=_counters()))
        assert "score= is the producer's raw score" in briefing
        assert "never as a strength band" in briefing
        assert "« modérée »" in briefing

    def test_the_rules_are_static_not_counter_dependent(self):
        """The licence is stated even when the run produced no counter."""
        assert "target=<that unit>" in _briefing(_state())


class TestTheArgumentMapJoinsOnTheRecordKey:
    """``_build_argument_map`` fed the « Attacked by » column by text match.

    Measured on the stored states: 23 of 28 linked counters (doc_A) and 28 of
    39 (doc_B) reached no argument, because a generated counter does not echo
    its target's first 60 characters. The record's ``target_arg_id`` is the
    join; the text match survives only for a legacy record carrying neither
    target field.
    """

    ARGS = {
        "arg_a": "claim alpha asserted early in the discourse",
        "arg_b": "claim beta asserted later in the discourse",
    }

    def _map_entry(self, counter: dict):
        state = _state(
            identified_arguments=dict(self.ARGS), counter_arguments=[counter]
        )
        entries = DeepSynthesisAgent._build_argument_map(state)
        return {e.arg_id: e for e in entries}

    def test_a_keyed_counter_reaches_its_target_without_text_match(self):
        # The witness the review asked for: target_arg_id=arg_a, and an
        # original_argument that does NOT text-match any argument.
        counter = {
            "id": "ca_k",
            "strategy": "direct_refutation",
            "score": 0.5,
            "counter_content": "invented filler delta",
            "original_argument": "a wholly different phrasing the map never sees",
            "target_arg_id": "arg_a",
        }
        entries = self._map_entry(counter)
        assert "counter_ca_k" in entries["arg_a"].attacked_by
        assert entries["arg_b"].attacked_by == []

    def test_a_legacy_record_is_still_text_matched(self):
        """Control: no target field at all → the historical text match runs."""
        counter = {
            "id": "ca_l",
            "strategy": "direct_refutation",
            "score": 0.5,
            "counter_content": "invented filler epsilon",
            "original_argument": "claim alpha asserted early",
        }
        entries = self._map_entry(counter)
        assert "counter_ca_l" in entries["arg_a"].attacked_by
        assert entries["arg_b"].attacked_by == []

    def test_an_explicitly_unresolved_counter_is_not_reanchored(self):
        # The record states it is unresolved: matching it by resemblance
        # would anchor exactly what the producer said it could not.
        counter = {
            "id": "ca_u",
            "strategy": "counter_example",
            "score": 0.5,
            "counter_content": "invented filler zeta",
            "original_argument": "claim alpha asserted early",
            "target_unresolved_reason": _UNRESOLVED_REASON,
        }
        entries = self._map_entry(counter)
        assert entries["arg_a"].attacked_by == []
        assert entries["arg_b"].attacked_by == []

    def test_a_keyed_counter_pointing_outside_the_map_builds_no_edge(self):
        # The key names an id the run never identified: no edge, and no
        # fallback to resemblance — the record's key is authoritative.
        counter = {
            "id": "ca_o",
            "strategy": "direct_refutation",
            "score": 0.5,
            "counter_content": "invented filler eta",
            "original_argument": "claim alpha asserted early",
            "target_arg_id": "arg_absent",
        }
        entries = self._map_entry(counter)
        assert entries["arg_a"].attacked_by == []
        assert entries["arg_b"].attacked_by == []
