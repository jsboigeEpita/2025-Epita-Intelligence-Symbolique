"""Tests for uncovered UnifiedAnalysisState + RhetoricalAnalysisState methods (#815).

Covers methods identified as zero-coverage in B-05 audit:
- Batch add: add_identified_arguments, add_identified_fallacies
- Task lifecycle: mark_task_as_answered, get_last_task_id
- Utility: add_extract, log_error, consume_next_agent_designation
- Trace: add_trace_entry
- Formal analysis results: ranking, aspic, belief_revision, dialogue,
  probabilistic, bipolar, FOL, PL, modal, formal_synthesis
- NL-to-logic: add_nl_to_logic_translation (extended params)

Existing test_shared_state.py covers: init, basic add_*, cross-ref queries.
This file fills the gaps without duplication.
"""

import pytest
from argumentation_analysis.core.shared_state import (
    RhetoricalAnalysisState,
    UnifiedAnalysisState,
)


# ---------------------------------------------------------------------------
# RhetoricalAnalysisState — batch + utility methods
# ---------------------------------------------------------------------------


class TestBatchAddArguments:
    """Tests for add_identified_arguments (batch)."""

    def test_batch_adds_multiple_arguments(self):
        state = RhetoricalAnalysisState("text")
        state.add_identified_arguments(["First argument", "Second argument", "Third"])
        assert len(state.identified_arguments) == 3

    def test_batch_empty_list(self):
        state = RhetoricalAnalysisState("text")
        state.add_identified_arguments([])
        assert len(state.identified_arguments) == 0

    def test_batch_preserves_existing(self):
        state = RhetoricalAnalysisState("text")
        state.add_argument("Pre-existing")
        state.add_identified_arguments(["New one"])
        assert len(state.identified_arguments) == 2


class TestBatchAddFallacies:
    """Tests for add_identified_fallacies (batch)."""

    def test_batch_adds_fallacies(self):
        state = RhetoricalAnalysisState("text")
        fallacies = [
            {"nom": "Ad Hominem", "explication": "Attacks person", "famille": "pertinence"},
            {"nom": "Straw Man", "explication": "Distorts", "famille": "pertinence"},
        ]
        state.add_identified_fallacies(fallacies)
        # identified_fallacies is a dict, not a list
        assert len(state.identified_fallacies) == 2

    def test_batch_fallacy_defaults(self):
        """Missing keys get default values."""
        state = RhetoricalAnalysisState("text")
        state.add_identified_fallacies([{"nom": "Test"}])
        # identified_fallacies is a dict keyed by fallacy_id
        assert len(state.identified_fallacies) == 1
        fid = list(state.identified_fallacies.keys())[0]
        f = state.identified_fallacies[fid]
        assert f["justification"] == "Justification manquante"

    def test_batch_empty_list(self):
        state = RhetoricalAnalysisState("text")
        state.add_identified_fallacies([])
        assert len(state.identified_fallacies) == 0


class TestTaskLifecycle:
    """Tests for mark_task_as_answered and get_last_task_id."""

    def test_mark_task_as_answered(self):
        state = RhetoricalAnalysisState("text")
        tid = state.add_task("Analyse the main claim")
        state.mark_task_as_answered(tid, "The claim is about X", author="Agent1")
        assert tid in state.answers
        assert state.answers[tid]["answer_text"] == "The claim is about X"
        assert state.answers[tid]["author_agent"] == "Agent1"

    def test_mark_nonexistent_task_ignored(self):
        """Marking a nonexistent task as answered is a no-op."""
        state = RhetoricalAnalysisState("text")
        state.mark_task_as_answered("ghost_task", "answer", author="A")
        assert "ghost_task" not in state.answers

    def test_get_last_task_id_returns_unanswered(self):
        state = RhetoricalAnalysisState("text")
        t1 = state.add_task("Task 1")
        t2 = state.add_task("Task 2")
        # Both unanswered → returns last
        result = state.get_last_task_id()
        assert result in {t1, t2}

    def test_get_last_task_id_all_answered(self):
        state = RhetoricalAnalysisState("text")
        t1 = state.add_task("Task 1")
        state.mark_task_as_answered(t1, "Done")
        assert state.get_last_task_id() is None

    def test_get_last_task_id_no_tasks(self):
        state = RhetoricalAnalysisState("text")
        assert state.get_last_task_id() is None


class TestAddExtract:
    """Tests for add_extract."""

    def test_add_extract_returns_id(self):
        state = RhetoricalAnalysisState("text")
        eid = state.add_extract("Introduction", "Some extracted content")
        assert eid.startswith("extract_")

    def test_extract_stored_correctly(self):
        state = RhetoricalAnalysisState("text")
        eid = state.add_extract("Conclusion", "Final words")
        assert len(state.extracts) == 1
        assert state.extracts[0]["name"] == "Conclusion"
        assert state.extracts[0]["content"] == "Final words"

    def test_multiple_extracts(self):
        state = RhetoricalAnalysisState("text")
        state.add_extract("A", "Content A")
        state.add_extract("B", "Content B")
        assert len(state.extracts) == 2


class TestLogError:
    """Tests for log_error."""

    def test_log_error_returns_id(self):
        state = RhetoricalAnalysisState("text")
        eid = state.log_error("Agent1", "Something went wrong")
        assert eid.startswith("error_")

    def test_error_stored_correctly(self):
        state = RhetoricalAnalysisState("text")
        state.log_error("Sherlock", "JVM crashed")
        assert len(state.errors) == 1
        assert state.errors[0]["agent_name"] == "Sherlock"
        assert state.errors[0]["message"] == "JVM crashed"


class TestConsumeDesignation:
    """Tests for consume_next_agent_designation."""

    def test_consume_returns_designated(self):
        state = RhetoricalAnalysisState("text")
        state.designate_next_agent("Watson")
        result = state.consume_next_agent_designation()
        assert result == "Watson"

    def test_consume_clears_designation(self):
        state = RhetoricalAnalysisState("text")
        state.designate_next_agent("Sherlock")
        state.consume_next_agent_designation()
        assert state.consume_next_agent_designation() is None

    def test_consume_without_designation(self):
        state = RhetoricalAnalysisState("text")
        assert state.consume_next_agent_designation() is None


# ---------------------------------------------------------------------------
# UnifiedAnalysisState — formal analysis add_* methods
# ---------------------------------------------------------------------------


class TestAddTraceEntry:
    """Tests for add_trace_entry (Track UU #724)."""

    def test_trace_entry_stored(self):
        state = UnifiedAnalysisState("text")
        state.add_trace_entry("extract", "Sherlock", ["arg_1"], "Found key claim")
        assert len(state.analysis_trace) == 1
        entry = state.analysis_trace[0]
        assert entry["phase"] == "extract"
        assert entry["agent"] == "Sherlock"
        assert entry["reacts_to"] == ["arg_1"]
        assert entry["summary"] == "Found key claim"

    def test_trace_summary_truncated(self):
        state = UnifiedAnalysisState("text")
        long_summary = "x" * 500
        state.add_trace_entry("phase", "Agent", [], long_summary)
        assert len(state.analysis_trace[0]["summary"]) == 280

    def test_trace_timestamp_present(self):
        state = UnifiedAnalysisState("text")
        state.add_trace_entry("p", "A", [], "s")
        assert "timestamp" in state.analysis_trace[0]
        assert "T" in state.analysis_trace[0]["timestamp"]


class TestAddRankingResult:
    """Tests for add_ranking_result."""

    def test_ranking_stored(self):
        state = UnifiedAnalysisState("text")
        rid = state.add_ranking_result(
            "burk", ["a", "b", "c"], [{"winner": "a", "loser": "b"}]
        )
        assert rid.startswith("rank_")
        assert len(state.ranking_results) == 1
        assert state.ranking_results[0]["method"] == "burk"

    def test_ranking_multiple(self):
        state = UnifiedAnalysisState("text")
        state.add_ranking_result("marg", ["x"], [])
        state.add_ranking_result("dfs", ["y"], [])
        assert len(state.ranking_results) == 2


class TestAddAspicResult:
    """Tests for add_aspic_result."""

    def test_aspic_stored(self):
        state = UnifiedAnalysisState("text")
        aid = state.add_aspic_result("grounded", ["ext1"], {"time_ms": 42})
        assert aid.startswith("aspic_")
        assert state.aspic_results[0]["reasoner_type"] == "grounded"
        assert state.aspic_results[0]["statistics"]["time_ms"] == 42


class TestAddBeliefRevisionResult:
    """Tests for add_belief_revision_result."""

    def test_belief_revision_stored(self):
        state = UnifiedAnalysisState("text")
        bid = state.add_belief_revision_result(
            "dalal", ["p", "q"], ["p", "NOT q"]
        )
        assert bid.startswith("brevision_")
        assert state.belief_revision_results[0]["original"] == ["p", "q"]
        assert state.belief_revision_results[0]["revised"] == ["p", "NOT q"]


class TestAddDialogueResult:
    """Tests for add_dialogue_result."""

    def test_dialogue_stored(self):
        state = UnifiedAnalysisState("text")
        did = state.add_dialogue_result(
            "tax_policy", "agreement", [{"speaker": "A", "move": "claim"}]
        )
        assert did.startswith("dialogue_")
        assert state.dialogue_results[0]["outcome"] == "agreement"
        assert len(state.dialogue_results[0]["trace"]) == 1


class TestAddProbabilisticResult:
    """Tests for add_probabilistic_result."""

    def test_probabilistic_stored(self):
        state = UnifiedAnalysisState("text")
        pid = state.add_probabilistic_result(
            ["arg_1", "arg_2"], {"arg_1": 0.8, "arg_2": 0.3}
        )
        assert pid.startswith("prob_")
        assert state.probabilistic_results[0]["acceptance_probabilities"]["arg_1"] == 0.8


class TestAddBipolarResult:
    """Tests for add_bipolar_result."""

    def test_bipolar_stored(self):
        state = UnifiedAnalysisState("text")
        bid = state.add_bipolar_result(
            "evidential", ["a", "b"], [["a", "b"]]
        )
        assert bid.startswith("bipolar_")
        assert state.bipolar_results[0]["framework_type"] == "evidential"


class TestAddFOLAnalysisResult:
    """Tests for add_fol_analysis_result."""

    def test_fol_stored(self):
        state = UnifiedAnalysisState("text")
        fid = state.add_fol_analysis_result(
            ["forall(x) P(x)"], True, ["P(a)"], confidence=0.9, arg_id="arg_1"
        )
        assert fid.startswith("fol_")
        r = state.fol_analysis_results[0]
        assert r["consistent"] is True
        assert r["confidence"] == 0.9
        assert r["arg_id"] == "arg_1"

    def test_fol_without_arg_id(self):
        state = UnifiedAnalysisState("text")
        state.add_fol_analysis_result(["P(x)"], False, [])
        assert "arg_id" not in state.fol_analysis_results[0]


class TestAddPropositionalAnalysisResult:
    """Tests for add_propositional_analysis_result."""

    def test_pl_stored(self):
        state = UnifiedAnalysisState("text")
        pid = state.add_propositional_analysis_result(
            ["p AND q"], True, {"p": True, "q": True}, arg_id="arg_2"
        )
        assert pid.startswith("pl_")
        r = state.propositional_analysis_results[0]
        assert r["satisfiable"] is True
        assert r["model"]["p"] is True
        assert r["arg_id"] == "arg_2"

    def test_pl_no_model(self):
        state = UnifiedAnalysisState("text")
        state.add_propositional_analysis_result(["p AND NOT p"], False)
        r = state.propositional_analysis_results[0]
        assert r["model"] == {}


class TestAddModalAnalysisResult:
    """Tests for add_modal_analysis_result."""

    def test_modal_stored(self):
        state = UnifiedAnalysisState("text")
        mid = state.add_modal_analysis_result(
            ["[]P -> P"], True, ["necessity"]
        )
        assert mid.startswith("modal_")
        r = state.modal_analysis_results[0]
        assert r["valid"] is True
        assert "necessity" in r["modalities"]


class TestAddFormalSynthesisReport:
    """Tests for add_formal_synthesis_report."""

    def test_synthesis_stored(self):
        state = UnifiedAnalysisState("text")
        sid = state.add_formal_synthesis_report(
            "Overall consistent", {"fol": {"consistent": True}}, 0.85
        )
        assert sid.startswith("fsyn_")
        r = state.formal_synthesis_reports[0]
        assert r["summary"] == "Overall consistent"
        assert r["overall_validity"] == 0.85


class TestAddNLToLogicTranslationExtended:
    """Tests for add_nl_to_logic_translation with extended params."""

    def test_translation_with_all_params(self):
        state = UnifiedAnalysisState("text")
        tid = state.add_nl_to_logic_translation(
            original_text="All humans are mortal",
            formula="forall(x) mortal(x)",
            logic_type="FOL",
            is_valid=True,
            variables={"x": "entity"},
            confidence=0.95,
            arg_id="arg_1",
        )
        assert tid.startswith("nll_")
        # Find the translation in the list
        translations = [t for t in state.nl_to_logic_translations if t["id"] == tid]
        assert len(translations) == 1
        t = translations[0]
        assert t["variables"]["x"] == "entity"
        assert t["confidence"] == 0.95
        assert t["arg_id"] == "arg_1"

    def test_translation_minimal_params(self):
        state = UnifiedAnalysisState("text")
        state.add_nl_to_logic_translation(
            "It rains", "rain()", "PL", False
        )
        translations = state.nl_to_logic_translations
        assert len(translations) == 1
        t = translations[0]
        # variables defaults to {} when not provided
        assert t.get("variables") == {}
        assert "arg_id" not in t


class TestStakesAndStakeholders:
    """Tests for stakes_and_stakeholders initial state."""

    def test_initial_structure(self):
        state = UnifiedAnalysisState("text")
        s = state.stakes_and_stakeholders
        assert "stakes" in s
        assert "stakeholders" in s
        assert "rhetorical_register" in s
        assert "discursive_arena" in s
        assert s["stakes"] == []
        assert s["stakeholders"] == []

    def test_stakes_mutable(self):
        state = UnifiedAnalysisState("text")
        state.stakes_and_stakeholders["stakes"].append(
            {"description": "Economic stability", "level": "high"}
        )
        assert len(state.stakes_and_stakeholders["stakes"]) == 1


class TestWorkflowResults:
    """Tests for workflow_results dict operations."""

    def test_workflow_results_initially_empty(self):
        state = UnifiedAnalysisState("text")
        assert state.workflow_results == {}

    def test_workflow_results_accepts_arbitrary_keys(self):
        state = UnifiedAnalysisState("text")
        state.workflow_results["extract"] = {"arguments": ["a"]}
        state.workflow_results["quality"] = {"scores": [0.8]}
        assert "extract" in state.workflow_results
        assert "quality" in state.workflow_results


class TestFormalAnalysisResultsList:
    """Tests that formal analysis result lists grow correctly."""

    def test_multiple_fol_results(self):
        state = UnifiedAnalysisState("text")
        state.add_fol_analysis_result(["P(x)"], True, [])
        state.add_fol_analysis_result(["Q(x)"], False, ["Q(a)"])
        assert len(state.fol_analysis_results) == 2

    def test_multiple_pl_results(self):
        state = UnifiedAnalysisState("text")
        state.add_propositional_analysis_result(["p"], True, {"p": True})
        state.add_propositional_analysis_result(["q"], False)
        assert len(state.propositional_analysis_results) == 2

    def test_multiple_modal_results(self):
        state = UnifiedAnalysisState("text")
        state.add_modal_analysis_result(["[]P"], True, ["necessity"])
        state.add_modal_analysis_result(["<>Q"], True, ["possibility"])
        assert len(state.modal_analysis_results) == 2

    def test_formal_synthesis_multiple(self):
        state = UnifiedAnalysisState("text")
        state.add_formal_synthesis_report("R1", {}, 0.5)
        state.add_formal_synthesis_report("R2", {}, 0.9)
        assert len(state.formal_synthesis_reports) == 2
