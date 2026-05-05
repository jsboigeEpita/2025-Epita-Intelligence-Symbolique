"""Tests for ConversationalTraceAnalyzer (#218, #208-S).

Validates:
- Dataclass properties (PhaseTrace.duration, agents_active, total_content)
- ConvergenceMetrics computation (coverage_ratio, is_converged)
- ConversationalTraceAnalyzer lifecycle (start → phases → turns → stop)
- generate_report() structure and content
- generate_markdown_report() format
- _count_state_fields() utility
- Edge cases (empty state, no phases, no turns)
"""

import time
import pytest

from argumentation_analysis.orchestration.trace_analyzer import (
    TurnTrace,
    PhaseTrace,
    ConvergenceMetrics,
    ConversationalTraceAnalyzer,
    _count_state_fields,
)

# ── Dataclass properties ──


class TestPhaseTrace:
    def test_duration_with_times(self):
        p = PhaseTrace(name="test", start_time=100.0, end_time=105.5)
        assert p.duration == 5.5

    def test_duration_no_end_time(self):
        p = PhaseTrace(name="test", start_time=100.0, end_time=0.0)
        assert p.duration == 0.0

    def test_total_content(self):
        p = PhaseTrace(
            name="test",
            turns=[
                TurnTrace(phase="test", turn=1, agent="A", content_length=100),
                TurnTrace(phase="test", turn=2, agent="B", content_length=250),
            ],
        )
        assert p.total_content == 350

    def test_total_content_empty(self):
        p = PhaseTrace(name="test")
        assert p.total_content == 0

    def test_agents_active(self):
        p = PhaseTrace(
            name="test",
            turns=[
                TurnTrace(phase="test", turn=1, agent="PM", content_length=10),
                TurnTrace(phase="test", turn=2, agent="Extract", content_length=20),
                TurnTrace(phase="test", turn=3, agent="PM", content_length=15),
            ],
        )
        active = p.agents_active
        assert set(active) == {"PM", "Extract"}

    def test_agents_active_empty(self):
        p = PhaseTrace(name="test")
        assert p.agents_active == []


# ── ConvergenceMetrics ──


class TestConvergenceMetrics:
    def test_coverage_ratio(self):
        m = ConvergenceMetrics(state_fields_populated=5, total_state_fields=20)
        assert m.coverage_ratio == 0.25

    def test_coverage_ratio_zero_total(self):
        m = ConvergenceMetrics(state_fields_populated=0, total_state_fields=0)
        assert m.coverage_ratio == 0.0

    def test_is_converged_true(self):
        m = ConvergenceMetrics(
            arguments_found=3, fallacies_found=1, quality_scores_count=2
        )
        assert m.is_converged is True

    def test_is_converged_no_arguments(self):
        m = ConvergenceMetrics(
            arguments_found=0, fallacies_found=1, quality_scores_count=2
        )
        assert m.is_converged is False

    def test_is_converged_no_quality(self):
        m = ConvergenceMetrics(
            arguments_found=3, fallacies_found=0, quality_scores_count=0
        )
        assert m.is_converged is False

    def test_is_converged_zero_fallacies_ok(self):
        """Zero fallacies is valid (text may not contain any)."""
        m = ConvergenceMetrics(
            arguments_found=2, fallacies_found=0, quality_scores_count=1
        )
        assert m.is_converged is True


# ── _count_state_fields ──


class TestCountStateFields:
    def test_counts_populated(self):
        snapshot = {"a": "hello", "b": [], "c": {"x": 1}, "d": "", "e": None}
        counts = _count_state_fields(snapshot)
        assert counts["total"] == 5
        assert counts["populated"] == 2  # "a" and "c"

    def test_empty_snapshot(self):
        counts = _count_state_fields({})
        assert counts == {"total": 0, "populated": 0}

    def test_all_empty(self):
        snapshot = {"a": [], "b": {}, "c": "", "d": None, "e": 0, "f": False}
        counts = _count_state_fields(snapshot)
        assert counts["total"] == 6
        assert counts["populated"] == 0


# ── ConversationalTraceAnalyzer lifecycle ──


class TestTraceAnalyzerLifecycle:
    def test_start_resets_state(self):
        analyzer = ConversationalTraceAnalyzer()
        analyzer.phases.append(PhaseTrace(name="old"))
        analyzer.start()
        assert analyzer.phases == []
        assert analyzer._start_time > 0

    def test_stop_records_end_time(self):
        analyzer = ConversationalTraceAnalyzer()
        analyzer.start()
        analyzer.stop()
        assert analyzer._end_time >= analyzer._start_time

    def test_stop_closes_open_phase(self):
        analyzer = ConversationalTraceAnalyzer()
        analyzer.start()
        analyzer.begin_phase("Phase1")
        assert analyzer._current_phase.end_time == 0.0
        analyzer.stop()
        assert analyzer._current_phase.end_time > 0

    def test_begin_phase_closes_previous(self):
        analyzer = ConversationalTraceAnalyzer()
        analyzer.start()
        analyzer.begin_phase("Phase1")
        phase1 = analyzer._current_phase
        analyzer.begin_phase("Phase2")
        assert phase1.end_time > 0
        assert analyzer._current_phase.name == "Phase2"

    def test_begin_phase_with_state_snapshot(self):
        analyzer = ConversationalTraceAnalyzer()
        analyzer.start()
        analyzer.begin_phase("P1", {"a": "val", "b": [], "c": 42})
        assert analyzer._current_phase.state_before["total"] == 3
        assert analyzer._current_phase.state_before["populated"] == 2

    def test_end_phase_records_state_after(self):
        analyzer = ConversationalTraceAnalyzer()
        analyzer.start()
        analyzer.begin_phase("P1")
        analyzer.end_phase("P1", {"x": "data", "y": []})
        assert analyzer._current_phase.state_after["populated"] == 1
        assert len(analyzer._state_snapshots) == 1

    def test_end_phase_wrong_name_ignored(self):
        analyzer = ConversationalTraceAnalyzer()
        analyzer.start()
        analyzer.begin_phase("P1")
        analyzer.end_phase("WrongName", {"x": 1})
        assert analyzer._current_phase.end_time == 0.0  # Not closed

    def test_record_turn_adds_to_current_phase(self):
        analyzer = ConversationalTraceAnalyzer()
        analyzer.start()
        analyzer.begin_phase("P1")
        analyzer.record_turn(phase="P1", turn=1, agent="PM", content="Hello world")
        assert len(analyzer._current_phase.turns) == 1
        assert analyzer._current_phase.turns[0].content_length == 11

    def test_record_turn_wrong_phase_ignored(self):
        analyzer = ConversationalTraceAnalyzer()
        analyzer.start()
        analyzer.begin_phase("P1")
        analyzer.record_turn(phase="P2", turn=1, agent="PM", content="test")
        assert len(analyzer._current_phase.turns) == 0

    def test_record_turn_empty_content(self):
        analyzer = ConversationalTraceAnalyzer()
        analyzer.start()
        analyzer.begin_phase("P1")
        analyzer.record_turn(phase="P1", turn=1, agent="A", content="")
        assert analyzer._current_phase.turns[0].content_length == 0


# ── compute_convergence ──


class TestComputeConvergence:
    def test_full_state(self):
        analyzer = ConversationalTraceAnalyzer()
        snapshot = {
            "initial_text": "Some text",
            "identified_arguments": [{"id": "a1"}, {"id": "a2"}],
            "identified_fallacies": [{"type": "ad_hominem"}],
            "argument_quality_scores": {"a1": 7.5, "a2": 4.0},
            "counter_arguments": [{"target": "a2"}],
            "propositional_analysis_results": [{"formula": "p->q"}],
            "fol_analysis_results": [],
            "empty_field": [],
        }
        metrics = analyzer.compute_convergence(snapshot)
        assert metrics.arguments_found == 2
        assert metrics.fallacies_found == 1
        assert metrics.quality_scores_count == 2
        assert metrics.counter_arguments_count == 1
        assert metrics.formal_results_count == 1
        assert metrics.is_converged is True
        assert metrics.coverage_ratio > 0.5

    def test_empty_state(self):
        analyzer = ConversationalTraceAnalyzer()
        metrics = analyzer.compute_convergence({})
        assert metrics.arguments_found == 0
        assert metrics.is_converged is False
        assert metrics.coverage_ratio == 0.0


# ── generate_report ──


class TestGenerateReport:
    def _run_full_lifecycle(self):
        analyzer = ConversationalTraceAnalyzer()
        analyzer.start()

        analyzer.begin_phase("Extraction", {"text": "hello", "args": []})
        analyzer.record_turn("Extraction", 1, "PM", "Let's extract arguments")
        analyzer.record_turn("Extraction", 2, "ExtractAgent", "Found 2 arguments")
        analyzer.end_phase(
            "Extraction",
            {
                "text": "hello",
                "identified_arguments": [{"id": "a1"}, {"id": "a2"}],
                "identified_fallacies": [],
                "argument_quality_scores": {"a1": 6},
            },
        )

        analyzer.begin_phase("Synthesis")
        analyzer.record_turn("Synthesis", 1, "PM", "Synthesize")
        analyzer.end_phase(
            "Synthesis",
            {
                "text": "hello",
                "identified_arguments": [{"id": "a1"}, {"id": "a2"}],
                "identified_fallacies": [{"type": "ad_hominem"}],
                "argument_quality_scores": {"a1": 6, "a2": 3},
            },
        )

        analyzer.stop()
        return analyzer

    def test_report_structure(self):
        analyzer = self._run_full_lifecycle()
        report = analyzer.generate_report()
        assert report["total_phases"] == 2
        assert report["total_turns"] == 3
        assert report["total_duration_seconds"] >= 0
        assert len(report["phases"]) == 2

    def test_report_phase_details(self):
        analyzer = self._run_full_lifecycle()
        report = analyzer.generate_report()
        extraction = report["phases"][0]
        assert extraction["name"] == "Extraction"
        assert extraction["turns"] == 2
        assert set(extraction["agents"]) == {"PM", "ExtractAgent"}

    def test_report_convergence(self):
        analyzer = self._run_full_lifecycle()
        report = analyzer.generate_report()
        assert "convergence" in report
        conv = report["convergence"]
        assert conv["arguments_found"] == 2
        assert conv["fallacies_found"] == 1
        assert conv["quality_scores"] == 2
        assert conv["is_converged"] is True

    def test_report_no_phases(self):
        analyzer = ConversationalTraceAnalyzer()
        analyzer.start()
        analyzer.stop()
        report = analyzer.generate_report()
        assert report["total_phases"] == 0
        assert report["total_turns"] == 0
        assert "convergence" not in report

    def test_markdown_report(self):
        analyzer = self._run_full_lifecycle()
        md = analyzer.generate_markdown_report()
        assert "# Conversational Analysis Trace Report" in md
        assert "Phase: Extraction" in md
        assert "Convergence" in md
        assert "Arguments: 2" in md
