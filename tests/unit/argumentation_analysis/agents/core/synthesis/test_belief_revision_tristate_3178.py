"""#3178 — an unrun belief revision is not a total contraction, and the JTMS
chain is a DERIVED witness.

Measured on the R1108 render (doc_A): ``belief_revision_results[0]`` held
``original`` = 40 units, ``revised: []``, ``minimal_retraction`` cardinality 5
of 45 with 10 units touched. The deep synthesis read ``original - revised`` and
told the reader « the contraction set spans essentially the whole argument
range » — while Act III said « de nombreux engagements survivent intacts ».
``revised: []`` was the producer's NOT-COMPUTED marker (the handler size bound
refused the revision), not a measurement.

The same report counted ``jtms_retraction_chain`` as an independent witness
agreeing with the fallacies. That chain is built FROM the fallacies
(``invoke_callables._invoke_jtms`` step 4), so the convergence holds by
construction (#3145 family). The chain also carries ``{trigger, retracted,
cascaded, reason}`` while both readers asked for ``belief_name`` — every entry
rendered ``belief=?``.
"""

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
    BeliefRetraction,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_belief_revision_to_state,
)


def _briefing_lines(state, field_name):
    text = DeepSynthesisAgent.build_artifact_briefing(state)
    marker = f"[artifact:{field_name}."
    return [line for line in text.splitlines() if marker in line]


def _forty_units():
    return [f"arg_{i}" for i in range(1, 41)]


def _measured_revision_entry():
    """The R1108 shape: 40 units in, ``revised: []``, insight 5 of 45."""
    return {
        "id": "brevision_1",
        "method": "dalal",
        "original": _forty_units(),
        "revised": [],
        "minimal_retraction": {
            "cardinality": 5,
            "options": [],
            "options_total": 32,
            "base_size": 45,
            "touched_count": 10,
            "degraded": False,
        },
    }


class TestUnrunRevisionIsNotAContraction:
    """DoD 1 — the evidence line reports the minimal retraction, never 40/40."""

    def test_the_line_says_not_computed_and_carries_the_insight(self):
        state = SimpleNamespace(
            belief_revision_results=[_measured_revision_entry()],
        )
        lines = _briefing_lines(state, "belief_revision_results")
        assert len(lines) == 1
        line = lines[0]

        assert "NOT COMPUTED" in line
        assert "cardinality 5 of 45" in line
        assert "10 units touched" in line
        assert "NOT a contraction" in line

    def test_the_line_does_not_claim_forty_contracted_units(self):
        state = SimpleNamespace(
            belief_revision_results=[_measured_revision_entry()],
        )
        # #3184 review: scoped to the revision LINE — a whole-briefing guard
        # reddens on any future unrelated line carrying the word.
        line = _briefing_lines(state, "belief_revision_results")[0]
        assert "contracted" not in line
        assert "of 40" not in line
        assert "40 of 40" not in line

    def test_the_marker_names_the_reason_when_it_was_persisted(self):
        entry = _measured_revision_entry()
        entry["degraded"] = True
        entry["absent_reason"] = "handler_size_bound"
        state = SimpleNamespace(belief_revision_results=[entry])

        line = _briefing_lines(state, "belief_revision_results")[0]
        assert "NOT COMPUTED (handler_size_bound)" in line
        assert "cardinality 5 of 45" in line

    def test_an_old_entry_without_the_marker_still_reads_as_unrun(self):
        # The R1108 dumps pre-date the persisted marker: their empty
        # ``revised`` must still read as not computed (a revision that ran
        # always returns at least the incoming belief).
        state = SimpleNamespace(
            belief_revision_results=[_measured_revision_entry()],
        )
        line = _briefing_lines(state, "belief_revision_results")[0]
        assert "no reason recorded in this entry" in line

    def test_a_refused_insight_is_said_absent(self):
        entry = _measured_revision_entry()
        entry["minimal_retraction"] = {
            "cardinality": -1,
            "base_size": 45,
            "refusal": "cardinality_bound",
            "degraded": True,
        }
        state = SimpleNamespace(belief_revision_results=[entry])
        line = _briefing_lines(state, "belief_revision_results")[0]
        assert "minimal retraction NOT computed (cardinality_bound)" in line


class TestRevisionThatRan:
    """Control — a real revision still reports what it contracted."""

    def test_a_partial_contraction_names_what_went_and_its_denominator(self):
        state = SimpleNamespace(
            belief_revision_results=[
                {
                    "method": "dalal",
                    "original": ["u1", "u2", "u3", "u4", "u5", "u6"],
                    "revised": ["u1", "u2", "u3", "u4", "n_not_fallacy_abc"],
                }
            ]
        )
        line = _briefing_lines(state, "belief_revision_results")[0]
        assert "contracted=['u5', 'u6'] (2 of 6)" in line
        assert "NOT COMPUTED" not in line

    def test_a_revision_that_contracted_nothing_says_zero_of_n(self):
        state = SimpleNamespace(
            belief_revision_results=[
                {
                    "method": "dalal",
                    "original": ["u1", "u2"],
                    "revised": ["u1", "u2", "n_not_fallacy_abc"],
                }
            ]
        )
        line = _briefing_lines(state, "belief_revision_results")[0]
        assert "contracted=[] (0 of 2)" in line


class TestTheConversationalProducerCanContractEverything:
    """#3184 rework — the second producer always runs, so its empty ``revised``
    is a REAL total contraction.

    ``conversational_orchestrator._run_belief_revision_from_state`` is pure
    Python: no JVM, no handler size bound, no not-computed state. It removes
    every belief a fallacy targets, so when the fallacies cover every belief it
    writes ``revised: []`` — which the pipeline-shaped rule read as
    « NOT COMPUTED » and whose retractions then vanished from Section 6. Before
    #3178 the same entry read correctly; the rework restores that without
    giving up the pipeline reading.
    """

    def _entry(self, **overrides):
        entry = {
            "method": "fallacy_contraction",
            "original": ["u1", "u2", "u3"],
            "revised": [],
            "minimal_retraction": {
                "cardinality": 1,
                "options": ["u1"],
                "options_total": 3,
                "base_size": 6,
                "touched_count": 3,
                "degraded": False,
            },
        }
        entry.update(overrides)
        return entry

    def test_an_unmarked_total_contraction_is_reported_as_such(self):
        state = SimpleNamespace(belief_revision_results=[self._entry()])
        line = _briefing_lines(state, "belief_revision_results")[0]
        assert "NOT COMPUTED" not in line
        assert "contracted=['u1', 'u2', 'u3'] (3 of 3)" in line

    def test_its_retractions_reach_section_six(self):
        state = SimpleNamespace(belief_revision_results=[self._entry()])
        retractions = DeepSynthesisAgent._build_belief_retractions(state)
        assert [r.belief_name for r in retractions] == ["u1", "u2", "u3"]

    def test_a_stated_marker_wins_over_the_fallback(self):
        # The producer that KNOWS says so: degraded=False is trusted even with
        # an empty revised; degraded=True is trusted on this method too.
        ran = self._entry(degraded=False)
        did_not_run = self._entry(degraded=True, absent_reason="jvm_absent")
        assert DeepSynthesisAgent._belief_revision_ran(ran)
        assert not DeepSynthesisAgent._belief_revision_ran(did_not_run)

    def test_the_pipeline_reading_is_untouched(self):
        # Control — an unmarked pipeline entry with an empty revised still
        # reads as not computed (the R1108 dumps).
        assert not DeepSynthesisAgent._belief_revision_ran(
            {
                "method": "dalal",
                "original": _forty_units(),
                "revised": [],
            }
        )


class TestRevisionsInTheReportTrace:
    """DoD 1 — the unrun revision contributes no retraction to Section 6."""

    def test_the_unrun_revision_yields_no_retraction(self):
        state = UnifiedAnalysisState(initial_text="test")
        state.add_belief_revision_result(
            "dalal",
            _forty_units(),
            [],
            minimal_retraction=_measured_revision_entry()["minimal_retraction"],
            degraded=True,
            absent_reason="handler_size_bound",
        )
        assert DeepSynthesisAgent._build_belief_retractions(state) == []

    def test_a_ran_revision_still_yields_its_contractions(self):
        state = UnifiedAnalysisState(initial_text="test")
        state.add_belief_revision_result(
            "dalal", ["u1", "u2", "u3"], ["u1", "n_not_fallacy_abc"]
        )
        retractions = DeepSynthesisAgent._build_belief_retractions(state)
        assert [r.belief_name for r in retractions] == ["u2", "u3"]
        assert all(r.trigger == "dalal_contraction" for r in retractions)


class TestJtmsChainIsDerived:
    """DoD 2 — the line reads the producer's keys and labels itself derived."""

    def _chain(self):
        return [
            {
                "trigger": "arg_7: ad hominem",
                "retracted": ["b_stable", "b_weak"],
                "cascaded": ["b_downstream"],
                "reason": "directly set to False",
            }
        ]

    def test_the_line_reads_the_keys_the_producer_writes(self):
        state = SimpleNamespace(jtms_retraction_chain=self._chain())
        line = _briefing_lines(state, "jtms_retraction_chain")[0]

        assert "belief=?" not in line
        assert "trigger=arg_7: ad hominem" in line
        assert "b_stable" in line
        assert "b_downstream" in line
        assert "reason=directly set to False" in line

    def test_the_line_is_labelled_derived_from_fallacies(self):
        state = SimpleNamespace(jtms_retraction_chain=self._chain())
        line = _briefing_lines(state, "jtms_retraction_chain")[0]
        assert "DERIVED from detected fallacies" in line
        assert "not an independent witness" in line

    def test_each_retracted_belief_becomes_a_named_retraction(self):
        state = SimpleNamespace(jtms_retraction_chain=self._chain())
        retractions = DeepSynthesisAgent._build_belief_retractions(state)

        assert [r.belief_name for r in retractions] == ["b_stable", "b_weak"]
        assert all(isinstance(r, BeliefRetraction) for r in retractions)
        assert all(r.was_valid is True for r in retractions)
        assert all(r.trigger == "arg_7: ad hominem" for r in retractions)


class TestTheMarkerSurvivesTheState:
    """DoD 3 — the marker is persisted at the construction site."""

    def test_the_entry_keeps_degraded_and_the_reason(self):
        state = UnifiedAnalysisState(initial_text="test")
        state.add_belief_revision_result(
            "dalal", ["u1"], [], degraded=True, absent_reason="handler_size_bound"
        )
        entry = state.belief_revision_results[0]
        assert entry["degraded"] is True
        assert entry["absent_reason"] == "handler_size_bound"

    def test_an_unstated_marker_stays_absent_never_false(self):
        state = UnifiedAnalysisState(initial_text="test")
        state.add_belief_revision_result("dalal", ["u1"], ["u1"])
        entry = state.belief_revision_results[0]
        assert "degraded" not in entry
        assert "absent_reason" not in entry

    def test_the_writer_forwards_the_producer_marker(self):
        # Cause 1 measured end to end: the producer's refusal shape goes
        # through the writer, and the briefing built from the resulting state
        # says NOT COMPUTED instead of 40 of 40.
        state = UnifiedAnalysisState(initial_text="test")
        output = {
            "method": "dalal",
            "original": _forty_units(),
            "revised": [],
            "minimal_retraction": _measured_revision_entry()["minimal_retraction"],
            "degraded": True,
            "absent_reason": "handler_size_bound",
            "message": "belief revision refused by name",
        }
        _write_belief_revision_to_state(output, state, {})

        entry = state.belief_revision_results[0]
        assert entry["degraded"] is True
        assert entry["absent_reason"] == "handler_size_bound"

        line = _briefing_lines(state, "belief_revision_results")[0]
        assert "NOT COMPUTED (handler_size_bound)" in line
        assert "cardinality 5 of 45" in line

    def test_the_writer_leaves_an_absent_marker_absent(self):
        state = UnifiedAnalysisState(initial_text="test")
        output = {
            "method": "dalal",
            "original": ["u1", "u2"],
            "revised": ["u1", "u2", "n_not_fallacy_abc"],
        }
        _write_belief_revision_to_state(output, state, {})
        entry = state.belief_revision_results[0]
        assert "degraded" not in entry
