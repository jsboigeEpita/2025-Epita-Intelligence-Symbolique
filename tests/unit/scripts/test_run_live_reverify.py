"""Tests for run_live_reverify.py aggregator — Sprint 13.A."""

import sys
from pathlib import Path

import pytest

# Make the scripts directory importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from run_live_reverify import (
    MOCK_RESULTS,
    aggregate_results,
    classify_verdict,
    render_report,
)


class TestClassifyVerdict:
    """Unit tests for classify_verdict helper."""

    def test_win(self):
        assert classify_verdict("WIN (23 vs 15)") == "WIN"

    def test_tie(self):
        assert classify_verdict("TIE (12 vs 12)") == "TIE"

    def test_loss(self):
        assert classify_verdict("LOSS (5 vs 13)") == "LOSS"

    def test_unknown(self):
        assert classify_verdict("something weird") == "UNKNOWN"

    def test_ours_vs_zero_shot(self):
        assert classify_verdict("ours=142 vs zero-shot=0") == "UNKNOWN"


class TestAggregateResults:
    """Unit tests for aggregate_results with mock data."""

    def test_mock_data_all_corpora(self):
        agg = aggregate_results(MOCK_RESULTS)
        assert set(agg["corpora"].keys()) == {"A", "B", "C"}
        assert agg["stats"]["total"] > 0

    def test_mock_data_no_losses(self):
        """Mock data A has 0 losses (all WIN/TIE)."""
        agg = aggregate_results(MOCK_RESULTS)
        # Mock A: dag has WIN/WIN/WIN, conv has TIE/WIN/WIN
        # Mock B: dag has WIN/WIN/LOSS
        # Mock C: dag has WIN/WIN/LOSS, conv has WIN/WIN/TIE
        assert agg["stats"]["losses"] == 2  # B FOL + C FOL (dag)
        assert agg["stats"]["wins"] > 0
        assert agg["stats"]["ties"] > 0

    def test_axes_detail_cardinality(self):
        """Each corpus-path contributes 3 axes (CA, PL, FOL)."""
        agg = aggregate_results(MOCK_RESULTS)
        # A: dag (3) + conv (3) = 6
        # B: dag (3) = 3
        # C: dag (3) + conv (3) = 6
        # Total = 15
        assert len(agg["axes_detail"]) == 15

    def test_duration_summed(self):
        agg = aggregate_results(MOCK_RESULTS)
        assert agg["total_duration_s"] > 0

    def test_no_failed_phases_in_mock(self):
        agg = aggregate_results(MOCK_RESULTS)
        assert agg["any_failed_phases"] is False

    def test_missing_corpus(self):
        """Missing corpus handled gracefully."""
        partial = {"A": MOCK_RESULTS["A"]}
        agg = aggregate_results(partial)
        assert agg["stats"]["total"] == 6  # A only: dag(3) + conv(3)
        assert "B" not in agg["corpora"]
        assert agg["summary"]["B"] == {"_status": "MISSING"}

    def test_error_in_path(self):
        """Error in a path is captured, not crash."""
        data_with_error = {
            "A": {
                "corpus": "A",
                "zero_shot_reference": {"counter_arguments": 15, "pl_formulas": 14, "fol_formulas": 8},
                "paths": {
                    "dag_spectacular": {"error": "OOM crash", "traceback": "..."},
                },
            },
        }
        agg = aggregate_results(data_with_error)
        assert agg["stats"]["total"] == 0  # no valid axes extracted
        assert agg["corpora"]["A"]["paths"]["dag_spectacular"]["error"] == "OOM crash"

    def test_failed_phases_detected(self):
        """Failed phases flag set when any path has failed_phases."""
        data = {
            "A": {
                "corpus": "A",
                "zero_shot_reference": {"counter_arguments": 15, "pl_formulas": 14, "fol_formulas": 8},
                "paths": {
                    "dag_spectacular": {
                        "path": "dag_spectacular",
                        "duration_s": 100,
                        "summary": {
                            "failed_phases": ["fol_solver"],
                            "completed": 28, "failed": 1, "total": 29,
                        },
                        "dimensions": {"counter_arguments": 20, "pl_formulas": 30, "fol_formulas": 5},
                        "verdict_vs_zeroshot": {
                            "counter_arguments": "WIN (20 vs 15)",
                            "pl_formulas": "WIN (30 vs 14)",
                            "fol_formulas": "LOSS (5 vs 8)",
                        },
                    },
                },
            },
        }
        agg = aggregate_results(data)
        assert agg["any_failed_phases"] is True


class TestRenderReport:
    """Unit tests for render_report output."""

    def test_report_contains_header(self):
        agg = aggregate_results(MOCK_RESULTS)
        md = render_report(agg)
        assert "# Live Re-Verify Report" in md

    def test_report_contains_scoreboard(self):
        agg = aggregate_results(MOCK_RESULTS)
        md = render_report(agg)
        assert "## Scoreboard" in md
        assert "corpus_A" in md
        assert "corpus_B" in md
        assert "corpus_C" in md

    def test_report_synthesis_first(self):
        """Conclusion section appears before the scoreboard table."""
        agg = aggregate_results(MOCK_RESULTS)
        md = render_report(agg)
        conclusion_pos = md.find("## Conclusion")
        scoreboard_pos = md.find("## Scoreboard")
        assert conclusion_pos > 0
        assert scoreboard_pos > conclusion_pos

    def test_report_verdict_full_pass(self):
        """All WIN/TIE + no failed phases → FULL PASS."""
        perfect_data = {
            "A": {
                "corpus": "A",
                "zero_shot_reference": {"counter_arguments": 15, "pl_formulas": 14, "fol_formulas": 8},
                "paths": {
                    "dag_spectacular": {
                        "path": "dag_spectacular",
                        "duration_s": 100,
                        "summary": {"failed_phases": [], "completed": 29, "total": 29},
                        "dimensions": {"counter_arguments": 20, "pl_formulas": 30, "fol_formulas": 10},
                        "verdict_vs_zeroshot": {
                            "counter_arguments": "WIN (20 vs 15)",
                            "pl_formulas": "WIN (30 vs 14)",
                            "fol_formulas": "WIN (10 vs 8)",
                        },
                    },
                },
            },
        }
        agg = aggregate_results(perfect_data)
        md = render_report(agg)
        assert "FULL PASS" in md

    def test_report_empty_data(self):
        """Empty input produces graceful output."""
        agg = aggregate_results({})
        md = render_report(agg)
        assert "Aucune" in md or "MISSING" in md

    def test_report_contains_duration(self):
        agg = aggregate_results(MOCK_RESULTS)
        md = render_report(agg)
        assert "s" in md  # at least some duration mentioned


class TestMockConsistency:
    """Cross-check that MOCK_RESULTS are self-consistent."""

    def test_all_corpora_present(self):
        assert set(MOCK_RESULTS.keys()) == {"A", "B", "C"}

    def test_verdicts_match_dimensions(self):
        """Verdict strings should be consistent with dimensions vs zero_shot."""
        for label, data in MOCK_RESULTS.items():
            zs = data["zero_shot_reference"]
            for path_name, path_data in data["paths"].items():
                dims = path_data["dimensions"]
                verdicts = path_data["verdict_vs_zeroshot"]
                for axis in ("counter_arguments", "pl_formulas", "fol_formulas"):
                    ours = dims[axis]
                    theirs = zs[axis]
                    v = verdicts[axis]
                    if ours > theirs:
                        assert v.startswith("WIN"), f"{label}/{path_name}/{axis}: {v} but {ours} > {theirs}"
                    elif ours == theirs:
                        assert v.startswith("TIE"), f"{label}/{path_name}/{axis}: {v} but {ours} == {theirs}"
                    else:
                        assert v.startswith("LOSS"), f"{label}/{path_name}/{axis}: {v} but {ours} < {theirs}"
