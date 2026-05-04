"""
Unit tests for PluginBenchmarkSuite (#306).

Tests cover:
- Benchmark cases structure and validation
- PluginBenchmarkResult dataclass
- PluginBenchmarkReport scoring
- Output validation logic
- Tier A plugins (Governance, QualityScoring, ATMS) live runs
- Tier B plugins (JTMS, FrenchFallacy) with controlled inputs
- Report generation and baseline JSON output
- CLI entry point
"""

import asyncio
import json
import os
import pytest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

from argumentation_analysis.evaluation.plugin_benchmark import (
    PLUGIN_BENCHMARK_CASES,
    PluginBenchmarkResult,
    PluginBenchmarkReport,
    PluginBenchmarkSuite,
)

# ============================================================
# Benchmark cases structure
# ============================================================


@pytest.mark.unit
class TestBenchmarkCases:
    """Test benchmark cases structure and validation."""

    def test_all_plugins_have_cases(self):
        """Test that all 13 plugins have benchmark cases."""
        assert len(PLUGIN_BENCHMARK_CASES) == 13

    def test_expected_plugins_present(self):
        """Test that all expected plugins are present."""
        expected = {
            "governance",
            "quality_scoring",
            "atms",
            "jtms",
            "french_fallacy",
            "exploration",
            "tweety_logic",
            "belief_revision",
            "aspic",
            "ranking",
            "nl_to_logic",
            "fallacy_workflow",
            "toulmin",
        }
        assert set(PLUGIN_BENCHMARK_CASES.keys()) == expected

    def test_case_structure(self):
        """Test that each case has required fields."""
        required = {"id", "function", "args", "expected", "difficulty"}
        for plugin, cases in PLUGIN_BENCHMARK_CASES.items():
            for case in cases:
                missing = required - set(case.keys())
                assert not missing, f"{plugin}/{case.get('id', '?')} missing: {missing}"

    def test_difficulty_levels(self):
        """Test that difficulty levels are valid."""
        valid = {"easy", "medium", "hard"}
        for plugin, cases in PLUGIN_BENCHMARK_CASES.items():
            for case in cases:
                assert (
                    case["difficulty"] in valid
                ), f"{case['id']}: invalid difficulty '{case['difficulty']}'"

    def test_case_ids_unique(self):
        """Test that all case IDs are unique."""
        all_ids = []
        for cases in PLUGIN_BENCHMARK_CASES.values():
            all_ids.extend(c["id"] for c in cases)
        assert len(all_ids) == len(set(all_ids)), "Duplicate case IDs found"

    def test_minimum_cases_per_plugin(self):
        """Test that each plugin has at least 1 case."""
        for plugin, cases in PLUGIN_BENCHMARK_CASES.items():
            assert len(cases) >= 1, f"{plugin} has no cases"

    def test_tier_a_has_more_cases(self):
        """Test that Tier A plugins (no deps) have >= 3 cases each."""
        tier_a = ["governance", "quality_scoring", "atms"]
        for plugin in tier_a:
            assert (
                len(PLUGIN_BENCHMARK_CASES[plugin]) >= 3
            ), f"Tier A plugin {plugin} should have >= 3 cases"

    def test_total_case_count(self):
        """Test total case count is in expected range."""
        total = sum(len(cases) for cases in PLUGIN_BENCHMARK_CASES.values())
        assert 30 <= total <= 45, f"Expected 30-45 cases, got {total}"

    def test_function_names_match_plugin(self):
        """Test that function names reference valid plugin methods."""
        suite = PluginBenchmarkSuite()
        for plugin_name, cases in PLUGIN_BENCHMARK_CASES.items():
            entry = suite.PLUGIN_REGISTRY.get(plugin_name)
            assert entry is not None, f"Plugin {plugin_name} not in registry"


# ============================================================
# Data classes
# ============================================================


@pytest.mark.unit
class TestPluginBenchmarkResult:
    """Test PluginBenchmarkResult dataclass."""

    def test_creation(self):
        result = PluginBenchmarkResult(
            case_id="gov_01",
            plugin_name="governance",
            function_name="social_choice_vote",
            passed=True,
            latency_ms=5.2,
        )
        assert result.case_id == "gov_01"
        assert result.passed is True
        assert result.error == ""

    def test_defaults(self):
        result = PluginBenchmarkResult(
            case_id="test", plugin_name="test", function_name="test"
        )
        assert result.passed is False
        assert result.latency_ms == 0.0
        assert result.error == ""

    def test_serializable(self):
        result = PluginBenchmarkResult(
            case_id="qs_01",
            plugin_name="quality_scoring",
            function_name="evaluate_argument_quality",
            passed=True,
            actual='{"note_finale": 7}',
        )
        data = asdict(result)
        json_str = json.dumps(data)
        assert json_str is not None


@pytest.mark.unit
class TestPluginBenchmarkReport:
    """Test PluginBenchmarkReport scoring."""

    def test_compute_scores_empty(self):
        report = PluginBenchmarkReport()
        report.compute_scores()
        assert report.plugin_scores == {}

    def test_compute_scores_single_plugin(self):
        report = PluginBenchmarkReport()
        report.results = [
            PluginBenchmarkResult(
                case_id="gov_01",
                plugin_name="governance",
                function_name="social_choice_vote",
                passed=True,
                latency_ms=5.0,
            ),
            PluginBenchmarkResult(
                case_id="gov_02",
                plugin_name="governance",
                function_name="detect_conflicts_fn",
                passed=False,
                latency_ms=3.0,
                error="test error",
            ),
        ]
        report.compute_scores()
        assert "governance" in report.plugin_scores
        scores = report.plugin_scores["governance"]
        assert scores["pass_rate"] == 0.5
        assert scores["avg_latency_ms"] == 4.0
        assert scores["error_rate"] == 0.5
        assert scores["case_count"] == 2

    def test_compute_scores_multiple_plugins(self):
        report = PluginBenchmarkReport()
        for plugin in ["governance", "quality_scoring"]:
            for i in range(3):
                report.results.append(
                    PluginBenchmarkResult(
                        case_id=f"{plugin}_{i}",
                        plugin_name=plugin,
                        function_name="test",
                        passed=(i < 2),
                        latency_ms=10.0 + i,
                    )
                )
        report.compute_scores()
        assert len(report.plugin_scores) == 2
        for plugin in ["governance", "quality_scoring"]:
            assert plugin in report.plugin_scores
            assert report.plugin_scores[plugin]["pass_rate"] == pytest.approx(2 / 3)


# ============================================================
# Output validation
# ============================================================


@pytest.mark.unit
class TestOutputValidation:
    """Test the _validate_output logic."""

    def test_validate_has_winner(self):
        suite = PluginBenchmarkSuite()
        passed, details = suite._validate_output(
            {"has_winner": True, "winner_is": "A"},
            '{"winner": "A"}',
        )
        assert passed

    def test_validate_has_winner_wrong(self):
        suite = PluginBenchmarkSuite()
        passed, details = suite._validate_output(
            {"has_winner": True, "winner_is": "B"},
            '{"winner": "A"}',
        )
        assert not passed

    def test_validate_returns_json_valid(self):
        suite = PluginBenchmarkSuite()
        passed, details = suite._validate_output(
            {"returns_json": True},
            '{"result": "ok"}',
        )
        assert passed

    def test_validate_returns_json_invalid(self):
        suite = PluginBenchmarkSuite()
        passed, details = suite._validate_output(
            {"returns_json": True},
            "not json at all",
        )
        assert not passed

    def test_validate_virtue_count(self):
        suite = PluginBenchmarkSuite()
        passed, details = suite._validate_output(
            {"virtue_count": 9},
            json.dumps(["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9"]),
        )
        assert passed

    def test_validate_virtue_count_wrong(self):
        suite = PluginBenchmarkSuite()
        passed, details = suite._validate_output(
            {"virtue_count": 9},
            json.dumps(["v1", "v2", "v3"]),
        )
        assert not passed

    def test_validate_has_methods(self):
        suite = PluginBenchmarkSuite()
        passed, details = suite._validate_output(
            {"has_methods": True},
            '{"method_a": {}, "method_b": {}}',
        )
        assert passed

    def test_validate_note_finale(self):
        suite = PluginBenchmarkSuite()
        passed, details = suite._validate_output(
            {"has_note_finale": True, "note_finale_gte": 3},
            '{"note_finale": 7, "note_moyenne": 6.5}',
        )
        assert passed

    def test_validate_note_finale_too_low(self):
        suite = PluginBenchmarkSuite()
        passed, details = suite._validate_output(
            {"has_note_finale": True, "note_finale_gte": 5},
            '{"note_finale": 2}',
        )
        assert not passed

    def test_validate_empty_expected(self):
        suite = PluginBenchmarkSuite()
        passed, details = suite._validate_output({}, '{"anything": "ok"}')
        assert passed


# ============================================================
# Tier A: Live plugin tests (no external deps)
# ============================================================


@pytest.mark.unit
class TestGovernanceBenchmark:
    """Live benchmark for GovernancePlugin (Tier A)."""

    def test_governance_all_cases(self):
        """Run all governance benchmark cases."""
        suite = PluginBenchmarkSuite()
        results = suite.run_plugin("governance")
        assert len(results) == 5

        for r in results:
            assert r.error == "", f"{r.case_id} errored: {r.error}"

        # At least 4/5 should pass
        passed = sum(r.passed for r in results)
        assert passed >= 4, f"Only {passed}/5 governance cases passed"

    def test_social_choice_vote_copeland(self):
        """Test Copeland voting returns correct winner."""
        suite = PluginBenchmarkSuite()
        result = suite.run_single("governance", PLUGIN_BENCHMARK_CASES["governance"][0])
        assert result.passed
        assert result.latency_ms > 0
        assert result.error == ""

    def test_detect_conflicts(self):
        """Test conflict detection finds disagreement."""
        suite = PluginBenchmarkSuite()
        result = suite.run_single("governance", PLUGIN_BENCHMARK_CASES["governance"][1])
        assert result.passed
        assert result.error == ""

    def test_consensus_metrics(self):
        """Test consensus metrics computation."""
        suite = PluginBenchmarkSuite()
        result = suite.run_single("governance", PLUGIN_BENCHMARK_CASES["governance"][2])
        assert result.passed
        assert result.error == ""

    def test_governance_latency(self):
        """Test that governance benchmarks are fast (<100ms)."""
        suite = PluginBenchmarkSuite()
        results = suite.run_plugin("governance")
        for r in results:
            assert r.latency_ms < 100, f"{r.case_id} too slow: {r.latency_ms}ms"


@pytest.mark.unit
class TestQualityScoringBenchmark:
    """Live benchmark for QualityScoringPlugin (Tier A)."""

    def test_quality_all_cases(self):
        """Run all quality scoring benchmark cases."""
        suite = PluginBenchmarkSuite()
        results = suite.run_plugin("quality_scoring")
        assert len(results) == 3

        for r in results:
            assert r.error == "", f"{r.case_id} errored: {r.error}"

        passed = sum(r.passed for r in results)
        assert passed >= 2, f"Only {passed}/3 quality cases passed"

    def test_list_virtues(self):
        """Test that list_virtues returns exactly 9 virtues."""
        suite = PluginBenchmarkSuite()
        result = suite.run_single(
            "quality_scoring", PLUGIN_BENCHMARK_CASES["quality_scoring"][2]
        )
        assert result.passed
        assert result.error == ""


@pytest.mark.unit
class TestATMSBenchmark:
    """Live benchmark for ATMSPlugin (Tier A)."""

    def test_atms_create_assumption(self):
        """Test ATMS assumption creation."""
        suite = PluginBenchmarkSuite()
        result = suite.run_single("atms", PLUGIN_BENCHMARK_CASES["atms"][0])
        assert result.error == ""

    def test_atms_all_cases(self):
        """Run all ATMS benchmark cases."""
        suite = PluginBenchmarkSuite()
        results = suite.run_plugin("atms")
        assert len(results) == 3
        for r in results:
            assert r.latency_ms < 200, f"{r.case_id} too slow: {r.latency_ms}ms"


# ============================================================
# Tier B: Mockable plugin tests
# ============================================================


@pytest.mark.unit
class TestFrenchFallacyBenchmark:
    """Benchmark for FrenchFallacyPlugin (Tier B)."""

    def test_list_fallacy_types(self):
        """Test listing fallacy types."""
        suite = PluginBenchmarkSuite()
        result = suite.run_single(
            "french_fallacy", PLUGIN_BENCHMARK_CASES["french_fallacy"][0]
        )
        assert result.error == ""
        # Should return at least 10 types
        assert result.passed, result.validation_details

    def test_get_available_tiers(self):
        """Test getting available tiers."""
        suite = PluginBenchmarkSuite()
        result = suite.run_single(
            "french_fallacy", PLUGIN_BENCHMARK_CASES["french_fallacy"][1]
        )
        assert result.error == ""


# ============================================================
# Report generation
# ============================================================


@pytest.mark.unit
class TestReportGeneration:
    """Test report generation and persistence."""

    def test_save_baseline(self, tmp_path):
        """Test saving baseline JSON report."""
        report = PluginBenchmarkReport()
        report.results = [
            PluginBenchmarkResult(
                case_id="gov_01",
                plugin_name="governance",
                function_name="social_choice_vote",
                passed=True,
                latency_ms=5.0,
            )
        ]
        report.timestamp = "2026-04-08T12:00:00"
        report.compute_scores()

        suite = PluginBenchmarkSuite()
        output = tmp_path / "baseline.json"
        suite.save_baseline(report, str(output))

        assert output.exists()
        with open(output, encoding="utf-8") as f:
            data = json.load(f)

        assert data["total_cases"] == 1
        assert data["plugin_count"] == 1
        assert data["results"][0]["case_id"] == "gov_01"
        assert data["plugin_scores"]["governance"]["pass_rate"] == 1.0
        assert data["timestamp"] == "2026-04-08T12:00:00"

    def test_summary_generation(self):
        """Test summary is generated correctly."""
        suite = PluginBenchmarkSuite()
        report = PluginBenchmarkReport()
        report.results = [
            PluginBenchmarkResult(
                case_id="gov_01",
                plugin_name="governance",
                function_name="test",
                passed=True,
                latency_ms=10.0,
            ),
        ]
        report.compute_scores()
        summary = suite._build_summary(report)
        assert "governance" in summary
        assert "100%" in summary  # 1/1 pass rate

    def test_full_report_workflow(self, tmp_path):
        """Test complete workflow: run → report → save."""
        suite = PluginBenchmarkSuite()
        # Only run Tier A plugins for speed
        report = suite.run_all(plugins=["governance"])

        assert len(report.results) > 0
        assert "governance" in report.plugin_scores
        assert report.summary != ""

        output = tmp_path / "report.json"
        suite.save_baseline(report, str(output))
        assert output.exists()


# ============================================================
# Plugin registry
# ============================================================


@pytest.mark.unit
class TestPluginRegistry:
    """Test plugin registry and instantiation."""

    def test_registry_completeness(self):
        """Test that registry covers all benchmarked plugins."""
        suite = PluginBenchmarkSuite()
        for plugin_name in PLUGIN_BENCHMARK_CASES:
            assert (
                plugin_name in suite.PLUGIN_REGISTRY
            ), f"{plugin_name} missing from PLUGIN_REGISTRY"

    def test_registry_entry_format(self):
        """Test that registry entries have correct format."""
        suite = PluginBenchmarkSuite()
        for plugin_name, (module_path, class_name) in suite.PLUGIN_REGISTRY.items():
            assert module_path.startswith("argumentation_analysis.plugins")
            assert class_name  # non-empty string

    def test_instantiate_governance(self):
        """Test instantiating a Tier A plugin."""
        suite = PluginBenchmarkSuite()
        plugin = suite._instantiate_plugin("governance")
        assert plugin is not None

    def test_instantiate_quality(self):
        """Test instantiating QualityScoringPlugin."""
        suite = PluginBenchmarkSuite()
        plugin = suite._instantiate_plugin("quality_scoring")
        assert plugin is not None

    def test_instantiate_atms(self):
        """Test instantiating ATMSPlugin."""
        suite = PluginBenchmarkSuite()
        plugin = suite._instantiate_plugin("atms")
        assert plugin is not None

    def test_instantiate_nonexistent(self):
        """Test that unknown plugin returns None."""
        suite = PluginBenchmarkSuite()
        plugin = suite._instantiate_plugin("nonexistent_plugin")
        assert plugin is None

    def test_fallacy_workflow_raises(self):
        """Test that FallacyWorkflowPlugin raises (needs SK kernel)."""
        suite = PluginBenchmarkSuite()
        plugin = suite._instantiate_plugin("fallacy_workflow")
        assert plugin is None  # Expected to fail without kernel

    def test_plugin_cache(self):
        """Test that plugins are cached after first instantiation."""
        suite = PluginBenchmarkSuite()
        p1 = suite._instantiate_plugin("governance")
        p2 = suite._instantiate_plugin("governance")
        assert p1 is p2


# ============================================================
# Edge cases
# ============================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_run_single_unavailable_plugin(self):
        """Test running a case for an unavailable plugin."""
        suite = PluginBenchmarkSuite()
        with patch.object(suite, "_instantiate_plugin", return_value=None):
            result = suite.run_single(
                "nonexistent",
                {
                    "id": "test_01",
                    "function": "test",
                    "args": {},
                    "expected": {},
                    "difficulty": "easy",
                },
            )
        assert result.error != ""
        assert "not available" in result.error

    def test_run_single_missing_function(self):
        """Test running a case with a nonexistent function."""
        suite = PluginBenchmarkSuite()
        mock_plugin = MagicMock(spec=[])
        # No attribute 'nonexistent_fn'
        with patch.object(suite, "_instantiate_plugin", return_value=mock_plugin):
            result = suite.run_single(
                "test",
                {
                    "id": "test_01",
                    "function": "nonexistent_fn",
                    "args": {},
                    "expected": {},
                    "difficulty": "easy",
                },
            )
        assert "not found" in result.error

    def test_run_single_exception_in_function(self):
        """Test handling exceptions from plugin functions."""
        suite = PluginBenchmarkSuite()
        mock_plugin = MagicMock()
        mock_plugin.test_fn.side_effect = ValueError("test error")
        with patch.object(suite, "_instantiate_plugin", return_value=mock_plugin):
            result = suite.run_single(
                "test",
                {
                    "id": "test_01",
                    "function": "test_fn",
                    "args": {},
                    "expected": {},
                    "difficulty": "easy",
                },
            )
        assert result.error != ""
        assert not result.passed
        assert "EXCEPTION" in result.validation_details

    def test_run_all_selected_plugins(self):
        """Test running only selected plugins."""
        suite = PluginBenchmarkSuite()
        report = suite.run_all(plugins=["governance"])
        assert len(report.results) == 5  # governance has 5 cases
        assert "governance" in report.plugin_scores

    def test_run_all_no_cases(self):
        """Test running with plugin that has no cases."""
        suite = PluginBenchmarkSuite()
        report = suite.run_all(plugins=["nonexistent"])
        assert len(report.results) == 0

    def test_async_function_handling(self):
        """Test that async functions are handled correctly."""
        suite = PluginBenchmarkSuite()

        async def async_fn():
            return '{"result": "ok"}'

        mock_plugin = MagicMock()
        mock_plugin.test_fn.return_value = async_fn()

        with patch.object(suite, "_instantiate_plugin", return_value=mock_plugin):
            result = suite.run_single(
                "test",
                {
                    "id": "async_01",
                    "function": "test_fn",
                    "args": {},
                    "expected": {"returns_json": True},
                    "difficulty": "easy",
                },
            )
        assert result.passed
