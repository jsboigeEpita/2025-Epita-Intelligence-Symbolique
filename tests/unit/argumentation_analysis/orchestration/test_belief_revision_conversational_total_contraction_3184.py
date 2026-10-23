"""#3184 — the conversational producer can contract EVERYTHING, and says so.

``conversational_orchestrator._run_belief_revision_from_state`` is the second
belief-revision producer (the pipeline handler ``_invoke_belief_revision`` is
the first). It is pure Python: no JVM, no handler size bound, no not-computed
state. It starts from ``revised = list(original)`` and removes every belief a
fallacy targets, so a run whose fallacies cover every belief writes
``revised: []`` as a REAL total contraction.

#3178 taught both readers that an EMPTY ``revised`` on a
``belief_revision_results`` entry is the not-computed marker — a rule measured
on the pipeline producer, whose handler always leaves at least the incoming
belief. Applied to this producer, the same rule turned a total contraction into
« NOT COMPUTED » and its retractions vanished from Section 6.

#3184 rework restores the conversational reading without giving up the pipeline
one: the producer now STATES ``degraded=False`` on every entry it writes, a
stated marker always wins, and the empty-means-unrun fallback applies only to an
unmarked entry whose method is not the always-runs one.

These tests exercise the ACTUAL producer on a real ``UnifiedAnalysisState`` —
beliefs added through ``add_jtms_belief``, fallacies through ``add_fallacy`` —
and then read the persisted entry through the actual readers. No LLM, no
network, no JVM: the only optional dependency is the pure-Python SAT oracle the
insight already uses (``python-sat``, a pinned dep), which the existing
``TestMinimalRetractionInsight`` suite asserts is importable.
"""

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.conversational_orchestrator import (
    _run_belief_revision_from_state,
)


def _state_with_valid_beliefs(count: int = 3):
    """A real state carrying ``count`` arguments, each with a VALID JTMS belief.

    The producer reads ``jtms_beliefs[*]["valid"]`` and keeps the belief's
    ``name``; targeting the argument id makes the fallacy match it
    (``bname == target_arg``).
    """
    state = UnifiedAnalysisState("Text about a policy claim and its evidence")
    names = []
    for i in range(1, count + 1):
        arg_id = state.add_argument(f"Argument {i} about policy")
        state.add_jtms_belief(name=arg_id, valid=True, justifications=[])
        names.append(arg_id)
    return state, names


def _belief_revision_briefing_lines(state):
    """The briefing lines the report's evidence table devotes to the field."""
    text = DeepSynthesisAgent.build_artifact_briefing(state)
    marker = "[artifact:belief_revision_results."
    return [line for line in text.splitlines() if marker in line]


class TestTheProducerStatesItsTriState:
    """DoD 1 — the entry states ``degraded=False``; the reader stops guessing."""

    def test_a_total_contraction_is_persisted_as_such(self):
        state, names = _state_with_valid_beliefs(3)
        for name in names:
            state.add_fallacy("ad_hominem", "Attack", target_arg_id=name)

        result = _run_belief_revision_from_state(state)

        assert result is not None
        assert result["method"] == "fallacy_contraction"
        assert result["original_count"] == 3
        assert result["revised_count"] == 0
        assert len(result["removed"]) == 3

        assert len(state.belief_revision_results) == 1
        entry = state.belief_revision_results[0]
        assert entry["original"] == names
        assert entry["revised"] == []

        # The producer ALWAYS runs, so it states its tri-state. `is False` is
        # the point: an absent marker would also be falsy-adjacent, and #3178
        # stores only a real bool.
        assert entry["degraded"] is False
        assert isinstance(entry["degraded"], bool)

    def test_the_marker_is_a_bool_not_a_truthy_surrogate(self):
        state, names = _state_with_valid_beliefs(1)
        state.add_fallacy("ad_hominem", "Attack", target_arg_id=names[0])

        _run_belief_revision_from_state(state)

        degraded = state.belief_revision_results[0]["degraded"]
        assert type(degraded) is bool
        assert degraded is False

    def test_a_partial_contraction_also_states_it(self):
        # Control — the marker is not reserved to the total case.
        state, names = _state_with_valid_beliefs(3)
        state.add_fallacy("ad_hominem", "Attack", target_arg_id=names[0])

        _run_belief_revision_from_state(state)

        entry = state.belief_revision_results[0]
        assert entry["revised"] == names[1:]
        assert entry["degraded"] is False

    def test_the_insight_survives_the_total_contraction(self):
        # The minimal retraction is computed JVM-free from the same beliefs:
        # three negated beliefs make three independent clashes, so the smallest
        # set to give up is of cardinal 3 — the insight names the total
        # contraction rather than degrading to -1.
        state, names = _state_with_valid_beliefs(3)
        for name in names:
            state.add_fallacy("ad_hominem", "Attack", target_arg_id=name)

        _run_belief_revision_from_state(state)

        insight = state.belief_revision_results[0]["minimal_retraction"]
        assert insight is not None
        assert insight["degraded"] is False
        assert insight["cardinality"] == 3
        # One belief is one clause; a negated belief adds its negation clause,
        # so the base has 2 * 3 clauses and every one of them is touchable.
        assert insight["base_size"] == 2 * len(names)
        assert insight["touched_count"] == 2 * len(names)


class TestTheReaderReportsTheTotalContraction:
    """DoD 2 — the readers name the contraction, never « NOT COMPUTED »."""

    def test_the_ran_predicate_trusts_the_stated_marker(self):
        state, names = _state_with_valid_beliefs(3)
        for name in names:
            state.add_fallacy("ad_hominem", "Attack", target_arg_id=name)

        _run_belief_revision_from_state(state)

        entry = state.belief_revision_results[0]
        assert DeepSynthesisAgent._belief_revision_ran(entry) is True

    def test_the_evidence_line_says_three_of_three(self):
        state, names = _state_with_valid_beliefs(3)
        for name in names:
            state.add_fallacy("ad_hominem", "Attack", target_arg_id=name)

        _run_belief_revision_from_state(state)

        lines = _belief_revision_briefing_lines(state)
        assert len(lines) == 1
        line = lines[0]
        assert "NOT COMPUTED" not in line
        assert f"contracted={sorted(names)}" in line
        assert f"({len(names)} of {len(names)})" in line

    def test_section_six_carries_every_contracted_belief(self):
        state, names = _state_with_valid_beliefs(3)
        for name in names:
            state.add_fallacy("ad_hominem", "Attack", target_arg_id=name)

        _run_belief_revision_from_state(state)

        retractions = DeepSynthesisAgent._build_belief_retractions(state)
        assert {r.belief_name for r in retractions} == set(names)
        assert {r.trigger for r in retractions} == {"fallacy_contraction_contraction"}

    def test_the_discriminator_is_the_producer_never_the_emptiness(self):
        # Control — an UNMARKED empty `revised` from the pipeline producer (the
        # R1108 dumps) still reads as NOT COMPUTED on the very same state type.
        # The rework must not re-open that reading.
        state = UnifiedAnalysisState("Text")
        state.add_belief_revision_result(
            method="dalal",
            original=["arg_1", "arg_2"],
            revised=[],
        )
        entry = state.belief_revision_results[0]
        assert "degraded" not in entry
        assert DeepSynthesisAgent._belief_revision_ran(entry) is False
        assert DeepSynthesisAgent._build_belief_retractions(state) == []
        assert "NOT COMPUTED" in DeepSynthesisAgent._belief_revision_line(entry)


class TestNothingIsWrittenWhenNothingContract:
    """Control — the stated marker never appears on an entry that was not written."""

    def test_no_fallacy_writes_no_revision(self):
        state, _names = _state_with_valid_beliefs(3)

        assert _run_belief_revision_from_state(state) is None
        assert state.belief_revision_results == []

    def test_a_fallacy_aimed_at_no_belief_writes_no_revision(self):
        state, _names = _state_with_valid_beliefs(2)
        state.add_fallacy("ad_hominem", "Attack", target_arg_id="arg_absent")

        assert _run_belief_revision_from_state(state) is None
        assert state.belief_revision_results == []

    def test_an_invalid_belief_is_not_contracted(self):
        # Only VALID beliefs enter ``original``; a fallacy aimed at an invalid
        # one contracts nothing and the producer returns None.
        state = UnifiedAnalysisState("Text")
        arg_id = state.add_argument("An invalid belief")
        state.add_jtms_belief(name=arg_id, valid=False, justifications=[])
        state.add_fallacy("ad_hominem", "Attack", target_arg_id=arg_id)

        assert _run_belief_revision_from_state(state) is None
        assert state.belief_revision_results == []
