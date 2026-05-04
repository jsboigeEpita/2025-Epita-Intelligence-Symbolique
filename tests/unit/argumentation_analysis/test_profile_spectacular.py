"""Tests for PhaseTimingCollector and generate_report from profile_spectacular."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# scripts/ is not a package, import by path
_SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPT_DIR))


class TestPhaseTimingCollector:
    def test_init_empty(self):
        from profile_spectacular import PhaseTimingCollector

        collector = PhaseTimingCollector()
        assert collector.phase_timings == []
        assert collector._original_execute is None

    def test_collect_timing(self):
        """Simulate a phase result and verify timing collection."""
        from profile_spectacular import PhaseTimingCollector

        collector = PhaseTimingCollector()

        # Simulate what instrumented_execute does
        fake_result = MagicMock()
        fake_result.capability = "test_capability"
        fake_result.status.value = "completed"
        fake_result.duration_seconds = 1.234
        fake_result.error = None

        collector.phase_timings.append(
            {
                "phase": "test_phase",
                "capability": fake_result.capability,
                "status": fake_result.status.value,
                "duration_seconds": round(fake_result.duration_seconds, 4),
                "error": fake_result.error,
            }
        )

        assert len(collector.phase_timings) == 1
        entry = collector.phase_timings[0]
        assert entry["phase"] == "test_phase"
        assert entry["capability"] == "test_capability"
        assert entry["status"] == "completed"
        assert entry["duration_seconds"] == 1.234
        assert entry["error"] is None

    def test_uninstall_without_install(self):
        from profile_spectacular import PhaseTimingCollector

        collector = PhaseTimingCollector()
        collector.uninstall()  # should not raise
        assert collector._original_execute is None


class TestGenerateReport:
    def _make_profiling_data(self, **overrides):
        """Create minimal profiling data for generate_report."""
        data = {
            "wall_clock_seconds": 10.5,
            "total_phase_time_seconds": 9.2,
            "overhead_seconds": 1.3,
            "memory_peak_mb": 150.0,
            "phase_timings": [
                {
                    "phase": "extraction",
                    "capability": "fact_extraction",
                    "duration_seconds": 3.0,
                    "status": "completed",
                    "error": None,
                },
                {
                    "phase": "fallacy_detection",
                    "capability": "neural_fallacy_detection",
                    "duration_seconds": 4.0,
                    "status": "completed",
                    "error": None,
                },
                {
                    "phase": "synthesis",
                    "capability": "narrative_synthesis",
                    "duration_seconds": 2.2,
                    "status": "completed",
                    "error": None,
                },
            ],
            "top_functions_cumulative": [
                {
                    "function": "module.py:run_analysis",
                    "calls": 10,
                    "total_time_s": 5.0,
                    "cumulative_time_s": 8.0,
                },
            ],
            "top_allocators_kb": [
                {"file": "module.py:42", "size_kb": 1024.0, "count": 500},
            ],
            "workflow_summary": {
                "completed": 3,
                "failed": 0,
                "skipped": 0,
                "total": 3,
            },
        }
        data.update(overrides)
        return data

    def test_report_contains_sections(self):
        from profile_spectacular import generate_report

        profiling = self._make_profiling_data()
        report = generate_report(profiling)

        assert "# Spectacular Workflow Profiling Report" in report
        assert "## Executive Summary" in report
        assert "## Per-Phase Wall-Clock Breakdown" in report
        assert "## Optimization Recommendations" in report

    def test_report_has_snapshot_header(self):
        from profile_spectacular import generate_report

        profiling = self._make_profiling_data()
        report = generate_report(profiling)

        assert "**Snapshot**" in report
        assert "point-in-time" in report

    def test_report_shows_phases(self):
        from profile_spectacular import generate_report

        profiling = self._make_profiling_data()
        report = generate_report(profiling)

        assert "extraction" in report
        assert "fallacy_detection" in report
        assert "synthesis" in report

    def test_report_no_phases(self):
        from profile_spectacular import generate_report

        profiling = self._make_profiling_data(phase_timings=[])
        report = generate_report(profiling)

        assert "## Per-Phase Wall-Clock Breakdown" in report

    def test_report_with_failed_phase(self):
        from profile_spectacular import generate_report

        profiling = self._make_profiling_data()
        profiling["phase_timings"][0]["status"] = "failed"
        profiling["phase_timings"][0]["error"] = "timeout"
        report = generate_report(profiling)

        assert "failed" in report

    def test_report_no_hot_functions(self):
        from profile_spectacular import generate_report

        profiling = self._make_profiling_data(top_functions_cumulative=[])
        report = generate_report(profiling)

        # Should not crash and should still have recommendations
        assert "## Optimization Recommendations" in report

    def test_report_llm_recommendation(self):
        from profile_spectacular import generate_report

        # Make LLM phases dominate (>60% of phase time)
        profiling = self._make_profiling_data()
        # fact_extraction + neural_fallacy_detection + narrative_synthesis = 9.2s total
        # all are LLM-dependent = 100% > 60%
        report = generate_report(profiling)
        assert "LLM calls account for" in report

    def test_report_high_overhead_recommendation(self):
        from profile_spectacular import generate_report

        profiling = self._make_profiling_data(
            overhead_seconds=5.0, wall_clock_seconds=10.5
        )
        report = generate_report(profiling)
        assert "Orchestration overhead" in report
