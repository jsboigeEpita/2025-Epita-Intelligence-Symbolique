"""Tests for conversational vs sequential benchmark framework (#308).

Validates:
- RunMetrics extraction from pipeline results
- BenchmarkReport aggregation and averages
- State field fill rate computation
- Cross-reference density calculation
- Report formatting and serialization
"""

import json
import pytest
import tempfile
import os
from unittest.mock import MagicMock

from argumentation_analysis.evaluation.conversational_benchmark import (
    BENCHMARK_TEXTS,
    ALL_STATE_FIELDS,
    RunMetrics,
    BenchmarkReport,
    ConversationalBenchmarkRunner,
    extract_metrics,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState

# ── Test Data ─────────────────────────────────────────────────────────────


def _make_populated_state(text: str = "Test text") -> UnifiedAnalysisState:
    """Create a state with some populated fields for testing."""
    state = UnifiedAnalysisState(text)
    state.add_argument("Argument 1: reform is needed")
    state.add_argument("Argument 2: system will collapse")
    state.add_argument("Argument 3: deficit projection")
    state.add_fallacy(fallacy_type="Ad Hominem", justification="Personal attack")
    state.add_fallacy(fallacy_type="Appel à la peur", justification="Fear appeal")
    state.add_quality_score("arg_1", {"clarity": 0.8}, 0.7)
    state.add_quality_score("arg_2", {"clarity": 0.5}, 0.4)
    state.add_counter_argument("Argument 1", "Counter 1", "reductio", 0.8)
    state.add_jtms_belief("reform", True, justifications=["precedent"])
    state.add_jtms_belief("collapse", False, justifications=["fear"])
    state.add_debate_transcript("reform debate", exchanges=[], winner="opponent")
    state.add_governance_decision("vote", {"gov": 0.6, "opp": 0.4}, "gov")
    state.add_fol_analysis_result(["P(x)"], True, ["P(a)"], 0.9)
    state.add_propositional_analysis_result(["a => b"], True, {"a": True})
    return state


def _make_result_dict(state: UnifiedAnalysisState, mode: str = "standard") -> dict:
    """Create a pipeline result dict with given state."""
    return {
        "workflow_name": mode,
        "unified_state": state,
        "summary": {
            "completed": 8,
            "failed": 1,
            "skipped": 2,
            "total": 11,
        },
        "total_messages": 15 if mode == "conversational" else 0,
    }


# ============================================================
# Test: Benchmark texts
# ============================================================


@pytest.mark.unit
class TestBenchmarkTexts:
    def test_benchmark_has_three_texts(self):
        assert len(BENCHMARK_TEXTS) == 3

    def test_texts_are_non_empty(self):
        for text_id, text in BENCHMARK_TEXTS.items():
            assert len(text) > 100, f"{text_id} is too short"

    def test_texts_contain_french_content(self):
        for text_id, text in BENCHMARK_TEXTS.items():
            assert any(
                w in text.lower() for w in ["les", "que", "est", "des"]
            ), f"{text_id} doesn't look like French text"


# ============================================================
# Test: RunMetrics extraction
# ============================================================


@pytest.mark.unit
class TestMetricsExtraction:
    def test_extract_from_populated_state(self):
        state = _make_populated_state()
        result = _make_result_dict(state)
        metrics = extract_metrics("test", "standard", result, 42.5)

        assert metrics.text_id == "test"
        assert metrics.mode == "standard"
        assert metrics.wall_clock_seconds == 42.5
        assert metrics.argument_count == 3
        assert metrics.fallacy_count == 2
        assert metrics.quality_scores_count == 2
        assert metrics.counter_argument_count == 1
        assert metrics.jtms_belief_count == 2
        assert metrics.debate_transcript_count == 1
        assert metrics.governance_decision_count == 1
        assert metrics.fol_count == 1
        assert metrics.pl_count == 1
        assert metrics.completed_phases == 8
        assert metrics.failed_phases == 1
        assert metrics.skipped_phases == 2
        assert metrics.error == ""

    def test_extract_fill_rate_populated(self):
        state = _make_populated_state()
        result = _make_result_dict(state)
        metrics = extract_metrics("test", "standard", result, 10.0)

        # At least raw_text + identified_arguments + fallacies + quality + counter + jtms + debate + governance + fol + pl
        assert metrics.state_field_fill_rate > 0.3

    def test_extract_fill_rate_empty(self):
        state = UnifiedAnalysisState("Test")
        result = _make_result_dict(state)
        metrics = extract_metrics("test", "standard", result, 1.0)

        # Only raw_text should be filled
        assert metrics.state_field_fill_rate <= 0.1

    def test_extract_cross_ref_density(self):
        state = _make_populated_state()
        result = _make_result_dict(state)
        metrics = extract_metrics("test", "standard", result, 10.0)

        # We have quality scores on arg_1, arg_2 (out of 3 args)
        # cross_ref_density = (with_quality + with_fallacy + with_counter + with_formal) / (4 * total)
        assert metrics.cross_ref_density >= 0.0

    def test_extract_conversational_messages(self):
        state = _make_populated_state()
        result = _make_result_dict(state, mode="conversational")
        metrics = extract_metrics("test", "conversational", result, 60.0)

        assert metrics.total_messages == 15

    def test_extract_no_state(self):
        result = {"summary": {"completed": 0, "failed": 0, "skipped": 0}}
        metrics = extract_metrics("test", "standard", result, 5.0)

        assert metrics.error == "No unified_state in result"
        assert metrics.argument_count == 0


# ============================================================
# Test: BenchmarkReport
# ============================================================


@pytest.mark.unit
class TestBenchmarkReport:
    def _make_sample_runs(self) -> list:
        runs = []
        for text_id in ["text_a", "text_b"]:
            for mode in ["standard", "full", "conversational"]:
                runs.append(
                    RunMetrics(
                        text_id=text_id,
                        mode=mode,
                        wall_clock_seconds=100.0 if mode != "conversational" else 300.0,
                        argument_count=5,
                        fallacy_count=2,
                        quality_scores_count=4,
                        counter_argument_count=3,
                        jtms_belief_count=5,
                        state_field_fill_rate=0.45,
                        cross_ref_density=0.3,
                        total_messages=15 if mode == "conversational" else 0,
                    )
                )
        return runs

    def test_compute_averages(self):
        report = BenchmarkReport(runs=self._make_sample_runs())
        report.compute_averages()

        assert "standard" in report.mode_averages
        assert "full" in report.mode_averages
        assert "conversational" in report.mode_averages
        assert report.mode_averages["standard"]["avg_arguments"] == 5.0
        assert report.mode_averages["conversational"]["avg_messages"] == 15.0

    def test_compute_averages_with_errors(self):
        runs = self._make_sample_runs()
        runs[0].error = "Connection failed"
        report = BenchmarkReport(runs=runs)
        report.compute_averages()

        # standard has 2 runs, 1 with error → 1 successful
        assert report.mode_averages["standard"]["run_count"] == 1
        assert report.mode_averages["standard"]["error_rate"] == 0.5

    def test_empty_report(self):
        report = BenchmarkReport()
        report.compute_averages()
        assert report.mode_averages == {}

    def test_report_json_serialization(self):
        report = BenchmarkReport(runs=self._make_sample_runs())
        report.compute_averages()

        runner = ConversationalBenchmarkRunner()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            runner.save_report(report, path)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert len(data["runs"]) == 6
            assert "standard" in data["mode_averages"]
            assert data["text_count"] == 3  # default BENCHMARK_TEXTS
            assert "timestamp" in data
        finally:
            os.unlink(path)


# ============================================================
# Test: Runner configuration
# ============================================================


@pytest.mark.unit
class TestBenchmarkRunner:
    def test_default_configuration(self):
        runner = ConversationalBenchmarkRunner()
        assert len(runner.texts) == 3
        assert runner.modes == ["standard", "full", "conversational"]

    def test_custom_texts(self):
        runner = ConversationalBenchmarkRunner(
            texts={"custom": "Custom text for testing."},
            modes=["standard"],
        )
        assert len(runner.texts) == 1
        assert runner.modes == ["standard"]

    def test_all_state_fields_list(self):
        """ALL_STATE_FIELDS should cover the key state dimensions."""
        assert len(ALL_STATE_FIELDS) >= 25
        assert "identified_arguments" in ALL_STATE_FIELDS
        assert "identified_fallacies" in ALL_STATE_FIELDS
        assert "counter_arguments" in ALL_STATE_FIELDS
        assert "argument_quality_scores" in ALL_STATE_FIELDS


# ============================================================
# Test: Report formatting
# ============================================================


@pytest.mark.unit
class TestReportFormatting:
    def test_summary_contains_table(self):
        runs = [
            RunMetrics(
                text_id="test",
                mode="standard",
                wall_clock_seconds=50.0,
                argument_count=5,
                fallacy_count=2,
                state_field_fill_rate=0.45,
            ),
        ]
        report = BenchmarkReport(runs=runs)
        report.compute_averages()

        runner = ConversationalBenchmarkRunner()
        summary = runner._format_summary(report)

        assert "Conversational vs Sequential Benchmark" in summary
        assert "Per-Run Results" in summary
        assert "Mode Averages" in summary
        assert "standard" in summary

    def test_summary_shows_errors(self):
        runs = [
            RunMetrics(text_id="test", mode="standard", error="API timeout"),
        ]
        report = BenchmarkReport(runs=runs)
        runner = ConversationalBenchmarkRunner()
        summary = runner._format_summary(report)
        assert "ERROR" in summary
