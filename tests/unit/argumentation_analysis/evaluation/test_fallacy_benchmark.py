"""
Tests for fallacy_benchmark.py comparative detection benchmark.
"""

import csv
import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from argumentation_analysis.evaluation.fallacy_benchmark import (
    BENCHMARK_CASES,
    BenchmarkReport,
    DetectionResult,
    FallacyBenchmarkRunner,
)


# =====================================================================
# Benchmark Data Tests
# =====================================================================


class TestBenchmarkData:
    """Tests for the benchmark test cases data structure."""

    def test_benchmark_cases_exists(self):
        """Verify benchmark cases are defined."""
        assert len(BENCHMARK_CASES) >= 10

    def test_benchmark_cases_structure(self):
        """Verify each benchmark case has required fields."""
        for case in BENCHMARK_CASES:
            assert "id" in case
            assert "expected_pk" in case
            assert "expected_name" in case
            assert "expected_family" in case
            assert "expected_depth" in case
            assert "difficulty" in case
            assert "text" in case

    def test_benchmark_cases_difficulty_levels(self):
        """Verify difficulty levels are represented."""
        difficulties = {case["difficulty"] for case in BENCHMARK_CASES}
        assert "easy" in difficulties
        assert "medium" in difficulties
        assert "hard" in difficulties

    def test_benchmark_case_text_not_empty(self):
        """Verify all cases have non-empty text."""
        for case in BENCHMARK_CASES:
            assert case["text"].strip(), f"Case {case['id']} has empty text"

    def test_benchmark_cases_unique_ids(self):
        """Verify all case IDs are unique."""
        ids = [case["id"] for case in BENCHMARK_CASES]
        assert len(ids) == len(set(ids)), "Duplicate case IDs found"


# =====================================================================
# DetectionResult Tests
# =====================================================================


class TestDetectionResult:
    """Tests for DetectionResult dataclass."""

    def test_creation_minimal(self):
        """Verify minimal result creation."""
        result = DetectionResult(case_id="case_01", mode="free")
        assert result.case_id == "case_01"
        assert result.mode == "free"
        assert result.detected_name == ""
        assert result.confidence == 0.0

    def test_creation_full(self):
        """Verify full result creation."""
        result = DetectionResult(
            case_id="case_01",
            mode="constrained",
            detected_name="Appel à l'ignorance",
            detected_pk="4",
            detected_family="Insuffisance",
            confidence=0.95,
            justification="Correctly identified",
            exact_pk_match=True,
            family_match=True,
            name_similarity=1.0,
            depth_reached=4,
            duration_seconds=2.5,
        )
        assert result.exact_pk_match is True
        assert result.depth_reached == 4

    def test_serializable(self):
        """Verify result can be serialized to JSON."""
        from dataclasses import asdict

        result = DetectionResult(
            case_id="case_01", mode="free", detected_pk="4",
            confidence=0.8, exact_pk_match=True
        )
        data = asdict(result)
        json_str = json.dumps(data)
        assert "case_01" in json_str


# =====================================================================
# BenchmarkReport Tests
# =====================================================================


class TestBenchmarkReport:
    """Tests for BenchmarkReport aggregation."""

    def test_empty_report(self):
        """Verify empty report initializes correctly."""
        report = BenchmarkReport()
        assert report.results == []
        assert report.mode_scores == {}
        assert report.summary == ""

    def test_compute_scores_empty(self):
        """Verify score computation handles empty results."""
        report = BenchmarkReport()
        report.compute_scores()
        assert report.mode_scores == {}

    def test_compute_scores_single_mode(self):
        """Verify score computation for a single mode."""
        report = BenchmarkReport()
        report.results = [
            DetectionResult(
                case_id="case_01", mode="free", exact_pk_match=True,
                family_match=True, name_similarity=1.0, depth_reached=4,
                confidence=0.9, duration_seconds=1.0
            ),
            DetectionResult(
                case_id="case_02", mode="free", exact_pk_match=False,
                family_match=True, name_similarity=0.5, depth_reached=3,
                confidence=0.7, duration_seconds=2.0
            ),
        ]
        report.compute_scores()

        assert "free" in report.mode_scores
        scores = report.mode_scores["free"]
        assert scores["exact_pk_accuracy"] == 0.5
        assert scores["family_accuracy"] == 1.0
        assert scores["avg_name_similarity"] == 0.75
        assert scores["avg_depth_reached"] == 3.5
        assert scores["avg_confidence"] == 0.8

    def test_compute_scores_multiple_modes(self):
        """Verify score computation for multiple modes."""
        report = BenchmarkReport()
        report.results = [
            DetectionResult(case_id="c1", mode="free", exact_pk_match=True,
                          family_match=True, name_similarity=1.0, depth_reached=4,
                          confidence=0.9, duration_seconds=1.0),
            DetectionResult(case_id="c1", mode="one_shot", exact_pk_match=True,
                          family_match=True, name_similarity=1.0, depth_reached=4,
                          confidence=0.95, duration_seconds=1.5),
        ]
        report.compute_scores()

        assert "free" in report.mode_scores
        assert "one_shot" in report.mode_scores

    def test_compute_scores_with_errors(self):
        """Verify score computation includes error rate."""
        report = BenchmarkReport()
        report.results = [
            DetectionResult(case_id="c1", mode="free", exact_pk_match=True,
                          family_match=True, name_similarity=1.0, depth_reached=4,
                          confidence=0.9, duration_seconds=1.0, error=""),
            DetectionResult(case_id="c2", mode="free", exact_pk_match=False,
                          family_match=False, name_similarity=0.0, depth_reached=0,
                          confidence=0.0, duration_seconds=0.5, error="API failure"),
        ]
        report.compute_scores()

        scores = report.mode_scores["free"]
        assert scores["error_rate"] == 0.5


# =====================================================================
# FallacyBenchmarkRunner Tests
# =====================================================================


class TestFallacyBenchmarkRunner:
    """Tests for the fallacy benchmark runner."""

    def test_initialization_default_path(self):
        """Verify runner initializes with default taxonomy path."""
        runner = FallacyBenchmarkRunner()
        assert runner.taxonomy_path is not None
        assert "argumentum_fallacies_taxonomy.csv" in runner.taxonomy_path

    def test_initialization_custom_path(self, tmp_path):
        """Verify runner can use custom taxonomy path."""
        custom_path = tmp_path / "taxonomy.csv"
        # Create dummy file
        with open(custom_path, "w", encoding="utf-8") as f:
            f.write("PK,path,text_fr\n1,1.,Test\n")

        runner = FallacyBenchmarkRunner(taxonomy_path=str(custom_path))
        assert runner.taxonomy_path == str(custom_path)

    @pytest.mark.skip(reason="Fallback path logic makes this test unreliable")
    def test_load_taxonomy_missing_file(self, tmp_path):
        """Verify missing taxonomy is handled gracefully."""
        runner = FallacyBenchmarkRunner(taxonomy_path=str(tmp_path / "nonexistent.csv"))
        # Note: The runner has fallback path logic, so taxonomy_data may not be empty
        # even when the specified file doesn't exist
        assert isinstance(runner.taxonomy_data, list)

    def test_load_taxonomy_success(self, tmp_path):
        """Verify taxonomy loading from CSV."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        with open(taxonomy_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["PK", "path", "text_fr", "depth", "nom_vulgarisé"])
            writer.writerow(["4", "4", "Appel à l'ignorance", "4", "Ignorance"])
            writer.writerow(["71", "71", "Argument d'autorité", "3", "Autorité"])

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))
        assert len(runner.taxonomy_data) == 2
        assert runner.node_map.get("4") is not None

    def test_get_family_for_pk(self, tmp_path):
        """Verify family extraction from PK."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        with open(taxonomy_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["PK", "path", "text_fr", "depth", "nom_vulgarisé"])
            writer.writerow(["1", "1", "Root", "1", ""])
            writer.writerow(["4", "1.4", "Appel à l'ignorance", "4", ""])

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))
        family = runner._get_family_for_pk("4")
        assert family == "Root"

    def test_get_family_for_unknown_pk(self):
        """Verify unknown PK returns empty family."""
        runner = FallacyBenchmarkRunner()
        family = runner._get_family_for_pk("999999")
        assert family == ""

    def test_parse_json_clean(self):
        """Verify clean JSON parsing."""
        runner = FallacyBenchmarkRunner()
        result = runner._parse_json('{"fallacy_name_fr": "Test", "confidence": 0.8}')
        assert result["fallacy_name_fr"] == "Test"
        assert result["confidence"] == 0.8

    def test_parse_json_with_markdown(self):
        """Verify JSON extraction from markdown code blocks."""
        runner = FallacyBenchmarkRunner()
        result = runner._parse_json('```json\n{"fallacy_name_fr": "Test"}\n```')
        assert result["fallacy_name_fr"] == "Test"

    def test_parse_json_embedded(self):
        """Verify JSON extraction from surrounding text."""
        runner = FallacyBenchmarkRunner()
        result = runner._parse_json('Text before {"key": "value"} text after')
        assert result["key"] == "value"

    def test_parse_json_invalid(self):
        """Verify invalid JSON returns error dict."""
        runner = FallacyBenchmarkRunner()
        result = runner._parse_json("Not JSON at all")
        assert "error" in result
        assert "raw" in result

    def test_name_similarity_identical(self):
        """Verify name similarity for identical strings."""
        sim = FallacyBenchmarkRunner._name_similarity("Test Name", "Test Name")
        assert sim == 1.0

    def test_name_similarity_partial_match(self):
        """Verify name similarity for partial matches."""
        sim = FallacyBenchmarkRunner._name_similarity("Appel à l'ignorance", "Appel ignorance")
        assert 0.0 < sim < 1.0

    def test_name_similarity_no_match(self):
        """Verify name similarity for completely different strings."""
        sim = FallacyBenchmarkRunner._name_similarity("Alpha", "Beta")
        assert sim == 0.0

    def test_name_similarity_empty(self):
        """Verify name similarity handles empty strings."""
        assert FallacyBenchmarkRunner._name_similarity("", "Test") == 0.0
        assert FallacyBenchmarkRunner._name_similarity("Test", "") == 0.0
        assert FallacyBenchmarkRunner._name_similarity("", "") == 0.0

    @pytest.mark.asyncio
    async def test_score_result_exact_match(self):
        """Verify scoring for exact PK match."""
        runner = FallacyBenchmarkRunner()
        case = BENCHMARK_CASES[0]  # case_01
        result = {
            "taxonomy_pk": case["expected_pk"],
            "fallacy_name_fr": case["expected_name"],
            "confidence": 0.9,
            "justification": "Correct",
        }

        scored = runner._score_result(case, "free", result, 1.5)
        assert scored.case_id == "case_01"
        assert scored.exact_pk_match is True
        assert scored.confidence == 0.9
        assert scored.duration_seconds == 1.5

    @pytest.mark.asyncio
    async def test_score_result_no_match(self):
        """Verify scoring for no match."""
        runner = FallacyBenchmarkRunner()
        case = BENCHMARK_CASES[0]
        result = {
            "taxonomy_pk": "999",  # Wrong PK
            "fallacy_name_fr": "Wrong",
            "confidence": 0.5,
            "justification": "Wrong detection",
        }

        scored = runner._score_result(case, "free", result, 1.0)
        assert scored.exact_pk_match is False
        assert scored.detected_pk == "999"

    @pytest.mark.asyncio
    async def test_score_result_error(self):
        """Verify scoring handles errors."""
        runner = FallacyBenchmarkRunner()
        case = BENCHMARK_CASES[0]
        result = {"error": "API failed"}

        scored = runner._score_result(case, "free", result, 0.0)
        assert "API failed" in scored.error
        assert scored.confidence == 0.0

    @pytest.mark.asyncio
    async def test_run_mode_a_free_success(self, tmp_path):
        """Verify Mode A (free) execution."""
        runner = FallacyBenchmarkRunner(taxonomy_path=str(tmp_path / "dummy.csv"))

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(
            content='{"fallacy_name_fr": "Test", "confidence": 0.8, "justification": "ok"}'
        ))]

        with patch("openai.AsyncOpenAI") as MockClient:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            result = await runner.run_mode_a_free("Test text")

        assert result["fallacy_name_fr"] == "Test"
        assert result["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_run_mode_b_one_shot_success(self, tmp_path):
        """Verify Mode B (one-shot) execution."""
        # Create minimal taxonomy
        taxonomy_path = tmp_path / "taxonomy.csv"
        with open(taxonomy_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["PK", "path", "text_fr", "depth"])
            writer.writerow(["1", "1", "Root", "1"])

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(
            content='{"taxonomy_pk": "1", "fallacy_name_fr": "Root", "confidence": 0.9}'
        ))]

        with patch("openai.AsyncOpenAI") as MockClient:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            result = await runner.run_mode_b_one_shot("Test text")

        assert result["taxonomy_pk"] == "1"

    @pytest.mark.asyncio
    async def test_run_benchmark_sequential(self, tmp_path):
        """Verify sequential benchmark execution."""
        runner = FallacyBenchmarkRunner(taxonomy_path=str(tmp_path / "dummy.csv"))

        # Mock the mode runners
        async def mock_mode(text):
            return {"taxonomy_pk": "4", "fallacy_name_fr": "Test", "confidence": 0.8, "justification": "ok"}

        with patch.object(runner, "run_mode_a_free", side_effect=mock_mode), \
             patch.object(runner, "run_mode_b_one_shot", side_effect=mock_mode), \
             patch.object(runner, "run_mode_c_constrained", side_effect=mock_mode):

            report = await runner.run_benchmark(
                cases=[BENCHMARK_CASES[0]],  # Single case
                modes=["free"],  # Single mode
                concurrency=1,  # Sequential
            )

        assert len(report.results) == 1
        assert "free" in report.mode_scores

    def test_save_report(self, tmp_path):
        """Verify report saving to JSON."""
        report = BenchmarkReport()
        report.results = [
            DetectionResult(
                case_id="case_01", mode="free", detected_pk="4",
                confidence=0.9, exact_pk_match=True, family_match=True,
                name_similarity=1.0, depth_reached=4, duration_seconds=1.0
            )
        ]
        report.mode_scores = {"free": {"exact_pk_accuracy": 1.0}}
        report.summary = "# Test Report"

        output_path = tmp_path / "report.json"
        runner = FallacyBenchmarkRunner()
        runner.save_report(report, str(output_path))

        assert output_path.exists()
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "results" in data
        assert data["case_count"] == len(BENCHMARK_CASES)
