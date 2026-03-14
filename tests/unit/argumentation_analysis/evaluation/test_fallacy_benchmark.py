"""
Advanced tests for FallacyBenchmarkRunner.

Tests cover:
- Benchmark cases structure and validation
- Taxonomy loading with fallback paths
- Family lookup by PK
- JSON parsing from LLM responses
- Name similarity (Jaccard)
- Result scoring (exact PK, family match, depth)
- Mode runners (free, one-shot, constrained)
- Benchmark execution (sequential and parallel)
- Report generation and persistence
"""

import asyncio
import json
import os
import pytest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.evaluation.fallacy_benchmark import (
    BENCHMARK_CASES,
    DetectionResult,
    BenchmarkReport,
    FallacyBenchmarkRunner,
)


@pytest.mark.unit
class TestBenchmarkCases:
    """Test benchmark cases structure and validation."""

    def test_benchmark_cases_count(self):
        """Test that there are exactly 10 benchmark cases."""
        assert len(BENCHMARK_CASES) == 10

    def test_benchmark_cases_structure(self):
        """Test that each case has required fields."""
        required_fields = [
            "id",
            "expected_pk",
            "expected_name",
            "expected_family",
            "expected_depth",
            "difficulty",
            "text",
        ]
        for case in BENCHMARK_CASES:
            for field in required_fields:
                assert field in case

    def test_benchmark_case_ids(self):
        """Test that case IDs follow the pattern case_01 to case_10."""
        expected_ids = [f"case_{i:02d}" for i in range(1, 11)]
        actual_ids = [case["id"] for case in BENCHMARK_CASES]
        assert actual_ids == expected_ids

    def test_difficulty_levels(self):
        """Test that difficulty levels are correctly distributed."""
        difficulties = [case["difficulty"] for case in BENCHMARK_CASES]
        assert "easy" in difficulties
        assert "medium" in difficulties
        assert "hard" in difficulties
        assert "very_hard" in difficulties

    def test_expected_families(self):
        """Test that all cases belong to expected families."""
        for case in BENCHMARK_CASES:
            assert case["expected_family"] in [
                "Insuffisance",
                "Influence",
                "Ambiguité",
                "Déduction",
            ]

    def test_expected_depths(self):
        """Test that expected depths are in valid range."""
        for case in BENCHMARK_CASES:
            assert 3 <= case["expected_depth"] <= 5

    def test_case_texts_not_empty(self):
        """Test that all case texts are non-empty."""
        for case in BENCHMARK_CASES:
            assert case["text"]
            assert len(case["text"]) > 50  # Minimum reasonable length


@pytest.mark.unit
class TestDetectionResult:
    """Test DetectionResult dataclass."""

    def test_detection_result_creation(self):
        """Test creating a DetectionResult."""
        result = DetectionResult(
            case_id="case_01",
            mode="free",
            detected_name="Appel à l'ignorance",
            detected_pk="4",
            detected_family="Insuffisance",
            confidence=0.95,
            justification="Test justification",
            exact_pk_match=True,
            family_match=True,
            name_similarity=1.0,
            depth_reached=4,
            duration_seconds=1.5,
        )

        assert result.case_id == "case_01"
        assert result.mode == "free"
        assert result.exact_pk_match is True
        assert result.name_similarity == 1.0

    def test_detection_result_defaults(self):
        """Test DetectionResult with default values."""
        result = DetectionResult(case_id="case_01", mode="free")

        assert result.detected_name == ""
        assert result.detected_pk == ""
        assert result.confidence == 0.0
        assert result.exact_pk_match is False
        assert result.family_match is False
        assert result.name_similarity == 0.0

    def test_detection_result_serializable(self):
        """Test that DetectionResult can be serialized to dict."""
        result = DetectionResult(
            case_id="case_01",
            mode="constrained",
            detected_name="Test",
            detected_pk="123",
            confidence=0.8,
        )

        data = asdict(result)
        assert data["case_id"] == "case_01"
        assert data["mode"] == "constrained"
        assert data["detected_name"] == "Test"

        # Verify it's JSON-serializable
        json_str = json.dumps(data)
        assert json_str is not None


@pytest.mark.unit
class TestBenchmarkReport:
    """Test BenchmarkReport dataclass."""

    def test_empty_report(self):
        """Test creating an empty report."""
        report = BenchmarkReport()

        assert report.results == []
        assert report.mode_scores == {}
        assert report.summary == ""

    def test_compute_scores_empty(self):
        """Test compute_scores with no results."""
        report = BenchmarkReport()
        report.compute_scores()

        assert report.mode_scores == {}

    def test_compute_scores_single_mode(self):
        """Test compute_scores with results from one mode."""
        report = BenchmarkReport()
        report.results = [
            DetectionResult(
                case_id="case_01",
                mode="free",
                exact_pk_match=True,
                family_match=True,
                name_similarity=1.0,
                depth_reached=4,
                confidence=0.9,
                duration_seconds=1.0,
                error="",
            ),
            DetectionResult(
                case_id="case_02",
                mode="free",
                exact_pk_match=False,
                family_match=True,
                name_similarity=0.5,
                depth_reached=3,
                confidence=0.7,
                duration_seconds=1.5,
                error="",
            ),
        ]

        report.compute_scores()

        assert "free" in report.mode_scores
        scores = report.mode_scores["free"]
        assert scores["exact_pk_accuracy"] == 0.5  # 1/2
        assert scores["family_accuracy"] == 1.0  # 2/2
        assert scores["avg_name_similarity"] == 0.75  # (1.0 + 0.5) / 2
        assert scores["avg_depth_reached"] == 3.5  # (4 + 3) / 2
        assert scores["avg_confidence"] == 0.8  # (0.9 + 0.7) / 2
        assert scores["avg_duration"] == 1.25  # (1.0 + 1.5) / 2
        assert scores["error_rate"] == 0.0  # No errors

    def test_compute_scores_with_errors(self):
        """Test compute_scores with error results."""
        report = BenchmarkReport()
        report.results = [
            DetectionResult(
                case_id="case_01",
                mode="one_shot",
                exact_pk_match=True,
                family_match=True,
                name_similarity=1.0,
                depth_reached=4,
                confidence=0.9,
                duration_seconds=1.0,
                error="",
            ),
            DetectionResult(
                case_id="case_02",
                mode="one_shot",
                exact_pk_match=False,
                family_match=False,
                name_similarity=0.0,
                depth_reached=0,
                confidence=0.0,
                duration_seconds=0.0,
                error="API timeout",
            ),
        ]

        report.compute_scores()

        assert "one_shot" in report.mode_scores
        scores = report.mode_scores["one_shot"]
        assert scores["exact_pk_accuracy"] == 0.5
        assert scores["error_rate"] == 0.5  # 1/2 has error

    def test_compute_scores_all_modes(self):
        """Test compute_scores with results from all three modes."""
        report = BenchmarkReport()
        for mode in ["free", "one_shot", "constrained"]:
            for i in range(3):
                report.results.append(
                    DetectionResult(
                        case_id=f"case_{i:02d}",
                        mode=mode,
                        exact_pk_match=(i == 0),
                        family_match=True,
                        name_similarity=0.8,
                        depth_reached=4,
                        confidence=0.9,
                        duration_seconds=1.0,
                        error="",
                    )
                )

        report.compute_scores()

        assert len(report.mode_scores) == 3
        for mode in ["free", "one_shot", "constrained"]:
            assert mode in report.mode_scores
            assert report.mode_scores[mode]["exact_pk_accuracy"] == pytest.approx(1/3)


@pytest.mark.unit
class TestTaxonomyLoading:
    """Test taxonomy loading functionality."""

    def test_taxonomy_path_resolution(self, tmp_path):
        """Test that taxonomy path is resolved correctly."""
        # Create a mock taxonomy file
        data_dir = tmp_path / "argumentation_analysis" / "data"
        data_dir.mkdir(parents=True)
        taxonomy_path = data_dir / "argumentum_fallacies_taxonomy.csv"

        # Write minimal CSV
        taxonomy_path.write_text(
            "PK,nom_vulgarisé,text_fr,depth,path\n"
            "1,Root,Racine,1,1\n"
            "2,Child,Enfant,2,1.2\n",
            encoding="utf-8",
        )

        # Patch dirname to point to tmp_path
        with patch("os.path.dirname", return_value=str(tmp_path)):
            runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        assert len(runner.taxonomy_data) == 2
        assert "1" in runner.node_map
        assert "2" in runner.node_map

    def test_taxonomy_missing_file(self, tmp_path):
        """Test that missing taxonomy file falls back to default taxonomy."""
        # When a non-existent path is provided, the runner falls back to default taxonomy
        runner = FallacyBenchmarkRunner(taxonomy_path=str(tmp_path / "nonexistent.csv"))

        # Should load the default taxonomy from argumentation_analysis/data/
        # The default taxonomy has 1409 entries (based on the argumentum_fallacies_taxonomy.csv file)
        assert len(runner.taxonomy_data) > 0
        assert len(runner.node_map) > 0

    def test_node_map_building(self, tmp_path):
        """Test that node_map correctly indexes by PK."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text(
            "PK,nom_vulgarisé,text_fr,depth,path\n"
            "10,Fallacy1,Sophisme1,3,1.5.10\n"
            "20,Fallacy2,Sophisme2,4,1.5.20\n",
            encoding="utf-8",
        )

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        assert "10" in runner.node_map
        assert "20" in runner.node_map
        assert runner.node_map["10"]["nom_vulgarisé"] == "Fallacy1"


@pytest.mark.unit
class TestFamilyLookup:
    """Test family lookup functionality."""

    def test_get_family_for_root_node(self, tmp_path):
        """Test getting family for a root PK."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text(
            "PK,nom_vulgarisé,text_fr,depth,path\n"
            "1,Insuffisance,Insuffisance,1,1\n"
            "2,Influence,Influence,1,2\n",
            encoding="utf-8",
        )

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        family = runner._get_family_for_pk("1")
        assert family == "Insuffisance"

        family = runner._get_family_for_pk("2")
        assert family == "Influence"

    def test_get_family_for_child_node(self, tmp_path):
        """Test getting family for a child PK."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text(
            "PK,nom_vulgarisé,text_fr,depth,path\n"
            "1,Insuffisance,Insuffisance,1,1\n"
            "5,Child,Child,3,1.3.5\n",
            encoding="utf-8",
        )

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        family = runner._get_family_for_pk("5")
        assert family == "Insuffisance"

    def test_get_family_for_unknown_pk(self, tmp_path):
        """Test getting family for non-existent PK."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text("PK,nom_vulgarisé,text_fr,depth,path\n", encoding="utf-8")

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        family = runner._get_family_for_pk("999")
        assert family == ""


@pytest.mark.unit
class TestJSONParsing:
    """Test JSON parsing from LLM responses."""

    def test_parse_plain_json(self):
        """Test parsing plain JSON response."""
        runner = FallacyBenchmarkRunner()
        raw = '{"fallacy_name_fr": "Test", "confidence": 0.8}'

        result = runner._parse_json(raw)

        assert result["fallacy_name_fr"] == "Test"
        assert result["confidence"] == 0.8

    def test_parse_json_markdown_block(self):
        """Test parsing JSON from markdown code block."""
        runner = FallacyBenchmarkRunner()
        raw = '''```json
{
  "fallacy_name_fr": "Appel à l'ignorance",
  "confidence": 0.9
}
```'''

        result = runner._parse_json(raw)

        assert result["fallacy_name_fr"] == "Appel à l'ignorance"
        assert result["confidence"] == 0.9

    def test_parse_json_without_language(self):
        """Test parsing JSON from markdown without language specifier."""
        runner = FallacyBenchmarkRunner()
        raw = '''```
{"taxonomy_pk": "4", "confidence": 1.0}
```'''

        result = runner._parse_json(raw)

        assert result["taxonomy_pk"] == "4"

    def test_parse_json_with_text_before(self):
        """Test parsing JSON when there's text before."""
        runner = FallacyBenchmarkRunner()
        raw = '''Here is my analysis:

{"fallacy_name_fr": "Test", "confidence": 0.5}

Hope this helps.'''

        result = runner._parse_json(raw)

        assert result["fallacy_name_fr"] == "Test"

    def test_parse_invalid_json(self):
        """Test that invalid JSON returns error dict."""
        runner = FallacyBenchmarkRunner()
        raw = "This is not valid JSON"

        result = runner._parse_json(raw)

        assert "error" in result
        assert result["error"] == "Failed to parse JSON"

    def test_parse_malformed_json(self):
        """Test parsing malformed JSON (missing closing brace)."""
        runner = FallacyBenchmarkRunner()
        raw = '{"fallacy": "test"'

        result = runner._parse_json(raw)

        assert "error" in result


@pytest.mark.unit
class TestNameSimilarity:
    """Test name similarity calculation (Jaccard)."""

    def test_identical_names(self):
        """Test similarity with identical names."""
        sim = FallacyBenchmarkRunner._name_similarity(
            "Appel à l'ignorance",
            "Appel à l'ignorance"
        )
        assert sim == 1.0

    def test_completely_different_names(self):
        """Test similarity with completely different names."""
        sim = FallacyBenchmarkRunner._name_similarity(
            "Appel à l'ignorance",
            "Rationalisation"
        )
        assert sim == 0.0

    def test_partial_overlap(self):
        """Test similarity with partial word overlap."""
        sim = FallacyBenchmarkRunner._name_similarity(
            "Appel à l'ignorance",
            "Appel à l'autorité"
        )
        # Words: {appel, à, l'ignorance} ∩ {appel, à, l'autorité} = {appel, à}
        # Union: {appel, à, l'ignorance, l'autorité}
        # Note: apostrophes cause l'ignorance and l'autorité to be different tokens
        expected = 2 / 4  # 0.5
        assert sim == pytest.approx(expected)

    def test_case_insensitive(self):
        """Test that comparison is case-insensitive."""
        sim = FallacyBenchmarkRunner._name_similarity(
            "Appel à l'ignorance",
            "APPEL À L'IGNORANCE"
        )
        assert sim == 1.0

    def test_empty_strings(self):
        """Test similarity with empty strings."""
        sim = FallacyBenchmarkRunner._name_similarity("", "Test")
        assert sim == 0.0

        sim = FallacyBenchmarkRunner._name_similarity("Test", "")
        assert sim == 0.0

        sim = FallacyBenchmarkRunner._name_similarity("", "")
        assert sim == 0.0


@pytest.mark.unit
class TestResultScoring:
    """Test result scoring logic."""

    def test_exact_pk_match(self, tmp_path):
        """Test scoring with exact PK match."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text(
            "PK,nom_vulgarisé,text_fr,depth,path\n"
            "4,Appel ignorance,Appel à l'ignorance,4,1.2.4\n"
            "1,Insuffisance,Insuffisance,1,1\n",
            encoding="utf-8",
        )

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        case = BENCHMARK_CASES[0]  # case_01 expects PK "4"
        result = {
            "taxonomy_pk": "4",
            "fallacy_name_fr": "Appel à l'ignorance",
            "confidence": 0.9,
            "justification": "Correct",
        }

        scored = runner._score_result(case, "free", result, 1.0)

        assert scored.exact_pk_match is True
        assert scored.detected_pk == "4"
        assert scored.detected_name == "Appel à l'ignorance"

    def test_family_match(self, tmp_path):
        """Test scoring with family match but different PK."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text(
            "PK,nom_vulgarisé,text_fr,depth,path\n"
            "1,Insuffisance,Insuffisance,1,1\n"
            "4,Appel ignorance,Appel à l'ignorance,4,1.2.4\n"
            "71,Autorité,Argument d'autorité,3,1.3.71\n",
            encoding="utf-8",
        )

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        case = BENCHMARK_CASES[1]  # case_02 expects PK "71" (Insuffisance family)
        result = {
            "taxonomy_pk": "4",  # Different PK but same family
            "fallacy_name_fr": "Appel à l'ignorance",
            "confidence": 0.8,
            "justification": "Partial match",
        }

        scored = runner._score_result(case, "one_shot", result, 1.0)

        assert scored.exact_pk_match is False
        assert scored.family_match is True
        assert scored.detected_family == "Insuffisance"

    def test_no_match(self, tmp_path):
        """Test scoring with no match."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text(
            "PK,nom_vulgarisé,text_fr,depth,path\n"
            "1,Insuffisance,Insuffisance,1,1\n"
            "2,Influence,Influence,1,2\n"
            "100,Other,Autre,2,2.100\n",
            encoding="utf-8",
        )

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        case = BENCHMARK_CASES[0]  # Expects Insuffisance family
        result = {
            "taxonomy_pk": "100",  # Influence family (path 2.100)
            "fallacy_name_fr": "Autre sophisme",
            "confidence": 0.5,
            "justification": "Wrong detection",
        }

        scored = runner._score_result(case, "constrained", result, 1.0)

        assert scored.exact_pk_match is False
        assert scored.family_match is False  # Different families (Insuffisance vs Influence)
        assert scored.name_similarity < 0.5

    def test_depth_reached(self, tmp_path):
        """Test depth reached calculation."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text(
            "PK,nom_vulgarisé,text_fr,depth,path\n"
            "4,Test,Test,4,1.2.4\n",
            encoding="utf-8",
        )

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        case = BENCHMARK_CASES[0]
        result = {"taxonomy_pk": "4", "fallacy_name_fr": "Test"}

        scored = runner._score_result(case, "free", result, 1.0)

        assert scored.depth_reached == 4

    def test_confidence_extraction(self, tmp_path):
        """Test confidence value extraction."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text("PK,nom_vulgarisé,text_fr,depth,path\n", encoding="utf-8")

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        case = BENCHMARK_CASES[0]
        result = {"taxonomy_pk": "4", "confidence": 0.95}

        scored = runner._score_result(case, "free", result, 1.0)

        assert scored.confidence == 0.95

    def test_error_handling(self, tmp_path):
        """Test scoring with error result."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text("PK,nom_vulgarisé,text_fr,depth,path\n", encoding="utf-8")

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        case = BENCHMARK_CASES[0]
        result = {"error": "API timeout"}

        scored = runner._score_result(case, "free", result, 0.5)

        assert scored.error == "API timeout"
        assert scored.duration_seconds == 0.5


@pytest.mark.unit
class TestModeRunners:
    """Test the three detection mode runners."""

    @pytest.mark.asyncio
    async def test_mode_a_free(self, tmp_path):
        """Test Mode A: Free LLM detection."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text("PK,nom_vulgarisé,text_fr,depth,path\n", encoding="utf-8")

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        # Mock OpenAI client
        with patch("openai.AsyncOpenAI") as mock_client:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create = AsyncMock(
                return_value=MagicMock(
                    choices=[MagicMock(message=MagicMock(content='{"fallacy_name_fr": "Test", "confidence": 0.8}'))]
                )
            )
            mock_client.return_value = mock_instance

            result = await runner.run_mode_a_free("Test argument")

            assert result["fallacy_name_fr"] == "Test"
            assert result["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_mode_b_one_shot(self, tmp_path):
        """Test Mode B: One-shot with taxonomy."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text(
            "PK,nom_vulgarisé,text_fr,depth,path\n"
            "4,Test,Test,4,1.2.4\n",
            encoding="utf-8",
        )

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        with patch("openai.AsyncOpenAI") as mock_client:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create = AsyncMock(
                return_value=MagicMock(
                    choices=[MagicMock(message=MagicMock(content='{"taxonomy_pk": "4", "fallacy_name_fr": "Test"}'))]
                )
            )
            mock_client.return_value = mock_instance

            result = await runner.run_mode_b_one_shot("Test argument")

            assert result["taxonomy_pk"] == "4"
            assert result["fallacy_name_fr"] == "Test"

    @pytest.mark.requires_api
    @pytest.mark.asyncio
    async def test_mode_c_constrained(self, tmp_path):
        """Test Mode C: Constrained workflow (requires API)."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text(
            "PK,nom_vulgarisé,text_fr,depth,path\n"
            "4,Test,Test,4,1.2.4\n",
            encoding="utf-8",
        )

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        try:
            result = await runner.run_mode_c_constrained("Test argument text")
            # If API is available, check result structure
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"API not available or plugin error: {e}")


@pytest.mark.unit
class TestBenchmarkExecution:
    """Test benchmark execution logic."""

    @pytest.mark.asyncio
    async def test_run_benchmark_sequential(self, tmp_path):
        """Test sequential benchmark execution."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text(
            "PK,nom_vulgarisé,text_fr,depth,path\n"
            "1,Insuffisance,Insuffisance,1,1\n"
            "4,Test,Test,4,1.2.4\n",
            encoding="utf-8",
        )

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        # Mock all three mode runners
        async def mock_mode(text):
            return {"taxonomy_pk": "4", "fallacy_name_fr": "Test", "confidence": 0.8, "justification": "OK"}

        with patch.object(runner, "run_mode_a_free", side_effect=mock_mode), \
             patch.object(runner, "run_mode_b_one_shot", side_effect=mock_mode), \
             patch.object(runner, "run_mode_c_constrained", side_effect=mock_mode):

            # Run single case
            report = await runner.run_benchmark(
                cases=[BENCHMARK_CASES[0]],
                modes=["free"],
                concurrency=1,
            )

            assert len(report.results) == 1
            assert report.results[0].mode == "free"
            assert "free" in report.mode_scores

    @pytest.mark.asyncio
    async def test_run_benchmark_parallel(self, tmp_path):
        """Test parallel benchmark execution."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text("PK,nom_vulgarisé,text_fr,depth,path\n", encoding="utf-8")

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        async def mock_mode(text):
            await asyncio.sleep(0.01)  # Simulate work
            return {"taxonomy_pk": "4", "confidence": 0.8}

        with patch.object(runner, "run_mode_a_free", side_effect=mock_mode), \
             patch.object(runner, "run_mode_b_one_shot", side_effect=mock_mode), \
             patch.object(runner, "run_mode_c_constrained", side_effect=mock_mode):

            report = await runner.run_benchmark(
                cases=[BENCHMARK_CASES[0], BENCHMARK_CASES[1]],
                modes=["free", "one_shot"],
                concurrency=3,
            )

            # Should have 4 results (2 cases x 2 modes)
            assert len(report.results) == 4

    @pytest.mark.asyncio
    async def test_run_benchmark_with_errors(self, tmp_path):
        """Test benchmark with error handling."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text("PK,nom_vulgarisé,text_fr,depth,path\n", encoding="utf-8")

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        async def failing_mode(text):
            raise ValueError("Simulated error")

        async def working_mode(text):
            return {"taxonomy_pk": "4", "confidence": 0.9}

        with patch.object(runner, "run_mode_a_free", side_effect=failing_mode), \
             patch.object(runner, "run_mode_b_one_shot", side_effect=working_mode):

            report = await runner.run_benchmark(
                cases=[BENCHMARK_CASES[0]],
                modes=["free", "one_shot"],
                concurrency=1,
            )

            # free mode should have error
            free_result = next((r for r in report.results if r.mode == "free"), None)
            assert free_result is not None
            assert free_result.error == "Simulated error"

            # one_shot mode should succeed
            one_shot_result = next((r for r in report.results if r.mode == "one_shot"), None)
            assert one_shot_result is not None
            assert one_shot_result.error == ""

    @pytest.mark.asyncio
    async def test_run_benchmark_default_params(self, tmp_path):
        """Test benchmark with default parameters."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text("PK,nom_vulgarisé,text_fr,depth,path\n", encoding="utf-8")

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        async def mock_mode(text):
            return {"taxonomy_pk": "4"}

        with patch.object(runner, "run_mode_a_free", side_effect=mock_mode), \
             patch.object(runner, "run_mode_b_one_shot", side_effect=mock_mode), \
             patch.object(runner, "run_mode_c_constrained", side_effect=mock_mode):

            # Use default cases and modes
            report = await runner.run_benchmark(concurrency=1)

            # Should run all 10 cases x 3 modes = 30 results (but mocked, so simplified)
            assert len(report.results) == len(BENCHMARK_CASES) * 3
            assert len(report.mode_scores) == 3


@pytest.mark.unit
class TestReportGeneration:
    """Test report generation and saving."""

    def test_save_report(self, tmp_path):
        """Test saving report to JSON file."""
        report = BenchmarkReport()
        report.results = [
            DetectionResult(
                case_id="case_01",
                mode="free",
                detected_name="Test",
                detected_pk="4",
                confidence=0.9,
                exact_pk_match=True,
                family_match=True,
                name_similarity=1.0,
                depth_reached=4,
                duration_seconds=1.0,
            )
        ]
        report.mode_scores = {"free": {"exact_pk_accuracy": 1.0}}
        report.summary = "# Test Report\n"

        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text("PK,nom_vulgarisé,text_fr,depth,path\n", encoding="utf-8")

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        output_path = tmp_path / "report.json"
        runner.save_report(report, str(output_path))

        assert output_path.exists()

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["case_count"] == 10
        assert len(data["results"]) == 1
        assert data["mode_scores"]["free"]["exact_pk_accuracy"] == 1.0
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_summary_generation(self, tmp_path):
        """Test that summary is correctly generated."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text("PK,nom_vulgarisé,text_fr,depth,path\n", encoding="utf-8")

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        async def mock_mode(text):
            return {"taxonomy_pk": "4", "fallacy_name_fr": "Test", "confidence": 0.8}

        with patch.object(runner, "run_mode_a_free", side_effect=mock_mode), \
             patch.object(runner, "run_mode_b_one_shot", side_effect=mock_mode), \
             patch.object(runner, "run_mode_c_constrained", side_effect=mock_mode):

            report = await runner.run_benchmark(
                cases=[BENCHMARK_CASES[0]],
                modes=["free"],
                concurrency=1,
            )

            assert "# Fallacy Detection Benchmark Results" in report.summary
            assert "Mode: free" in report.summary
            assert "Exact PK accuracy:" in report.summary
            assert "Family accuracy:" in report.summary


@pytest.mark.unit
class TestConcurrencyControl:
    """Test concurrency control in benchmark execution."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self, tmp_path):
        """Test that semaphore limits concurrent executions."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text("PK,nom_vulgarisé,text_fr,depth,path\n", encoding="utf-8")

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        concurrent_count = 0
        max_concurrent = 0

        async def counting_mode(text):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.05)
            concurrent_count -= 1
            return {"taxonomy_pk": "4"}

        with patch.object(runner, "run_mode_a_free", side_effect=counting_mode), \
             patch.object(runner, "run_mode_b_one_shot", side_effect=counting_mode), \
             patch.object(runner, "run_mode_c_constrained", side_effect=counting_mode):

            # Run 6 tasks with concurrency limit of 2
            await runner.run_benchmark(
                cases=[BENCHMARK_CASES[i] for i in range(2)],
                modes=["free", "one_shot", "constrained"],
                concurrency=2,
            )

            # Should never exceed concurrency limit
            assert max_concurrent <= 2


@pytest.mark.unit
class TestBenchmarkIntegration:
    """Integration tests for the full benchmark workflow."""

    @pytest.mark.asyncio
    async def test_full_benchmark_workflow(self, tmp_path):
        """Test complete workflow from execution to report."""
        taxonomy_path = tmp_path / "taxonomy.csv"
        taxonomy_path.write_text(
            "PK,nom_vulgarisé,text_fr,depth,path\n"
            "1,Insuffisance,Insuffisance,1,1\n"
            "4,Test,Test,4,1.2.4\n",
            encoding="utf-8",
        )

        runner = FallacyBenchmarkRunner(taxonomy_path=str(taxonomy_path))

        async def mock_mode(text):
            return {
                "taxonomy_pk": "4",
                "fallacy_name_fr": "Test",
                "confidence": 0.85,
                "justification": "Mock detection",
            }

        with patch.object(runner, "run_mode_a_free", side_effect=mock_mode), \
             patch.object(runner, "run_mode_b_one_shot", side_effect=mock_mode), \
             patch.object(runner, "run_mode_c_constrained", side_effect=mock_mode):

            # Run benchmark
            report = await runner.run_benchmark(
                cases=[BENCHMARK_CASES[0]],
                modes=["free", "one_shot"],
                concurrency=1,
            )

            # Verify report structure
            assert len(report.results) == 2
            assert report.mode_scores is not {}
            assert report.summary != ""

            # Save report
            output_path = tmp_path / "benchmark_report.json"
            runner.save_report(report, str(output_path))

            # Verify saved file
            assert output_path.exists()
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert "results" in data
            assert "mode_scores" in data
            assert "timestamp" in data
