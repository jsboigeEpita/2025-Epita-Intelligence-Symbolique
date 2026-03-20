"""
Tests for the evaluation module (model_registry, benchmark_runner, result_collector, judge).
"""

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argumentation_analysis.evaluation.model_registry import ModelConfig, ModelRegistry
from argumentation_analysis.evaluation.benchmark_runner import (
    BenchmarkResult,
    BenchmarkRunner,
)
from argumentation_analysis.evaluation.result_collector import ResultCollector
from argumentation_analysis.evaluation.judge import LLMJudge, JudgeScore

# =====================================================================
# ModelConfig Tests
# =====================================================================


class TestModelConfig:
    def test_basic_creation(self):
        mc = ModelConfig(
            model_id="gpt-5-mini",
            base_url="https://api.openai.com/v1",
            api_key="sk-test",
        )
        assert mc.model_id == "gpt-5-mini"
        assert mc.display_name == "gpt-5-mini"

    def test_custom_display_name(self):
        mc = ModelConfig(
            model_id="x", base_url="y", api_key="z", display_name="My Model"
        )
        assert mc.display_name == "My Model"

    def test_thinking_model_flag(self):
        mc = ModelConfig(
            model_id="qwen", base_url="u", api_key="k", is_thinking_model=True
        )
        assert mc.is_thinking_model is True


# =====================================================================
# ModelRegistry Tests
# =====================================================================


class TestModelRegistry:
    def test_register_and_get(self):
        reg = ModelRegistry()
        cfg = ModelConfig(model_id="test", base_url="http://localhost", api_key="key")
        reg.register("test", cfg)
        assert reg.get("test") is cfg

    def test_get_unknown_raises(self):
        reg = ModelRegistry()
        with pytest.raises(KeyError, match="not registered"):
            reg.get("nonexistent")

    def test_list_models(self):
        reg = ModelRegistry()
        reg.register("a", ModelConfig("a", "u", "k"))
        reg.register("b", ModelConfig("b", "u", "k"))
        assert set(reg.list_models().keys()) == {"a", "b"}

    def test_activate_sets_env(self):
        reg = ModelRegistry()
        reg.register("test", ModelConfig("my-model", "http://local:5000/v1", "my-key"))
        saved = reg.save_env()
        reg.activate("test")
        assert os.environ["OPENAI_CHAT_MODEL_ID"] == "my-model"
        assert os.environ["OPENAI_BASE_URL"] == "http://local:5000/v1"
        assert os.environ["OPENAI_API_KEY"] == "my-key"
        assert reg.active == "test"
        reg.restore_env(saved)

    def test_save_and_restore_env(self):
        reg = ModelRegistry()
        original_key = os.environ.get("OPENAI_API_KEY")
        saved = reg.save_env()
        os.environ["OPENAI_API_KEY"] = "temporary"
        reg.restore_env(saved)
        assert os.environ.get("OPENAI_API_KEY") == original_key

    def test_from_env(self):
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "OPENAI_CHAT_MODEL_ID": "gpt-test",
                "OPENAI_BASE_URL": "https://test.api/v1",
            },
            clear=False,
        ):
            reg = ModelRegistry.from_env()
            assert "default" in reg.list_models()


# =====================================================================
# BenchmarkResult Tests
# =====================================================================


class TestBenchmarkResult:
    def test_basic_creation(self):
        r = BenchmarkResult(
            workflow_name="light",
            model_name="test",
            document_index=0,
            document_name="doc0",
            success=True,
            duration_seconds=1.5,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
        )
        assert r.success
        assert r.timestamp  # auto-set

    def test_serializable(self):
        r = BenchmarkResult(
            workflow_name="test",
            model_name="m",
            document_index=0,
            document_name="d",
            success=True,
            duration_seconds=0.5,
            phases_completed=1,
            phases_total=1,
            phases_failed=0,
            phases_skipped=0,
        )
        data = asdict(r)
        json_str = json.dumps(data)
        assert "workflow_name" in json_str


# =====================================================================
# BenchmarkRunner Tests
# =====================================================================


class TestBenchmarkRunner:
    def _make_runner_with_dataset(self):
        reg = ModelRegistry()
        reg.register("mock", ModelConfig("mock-model", "http://mock/v1", "mock-key"))
        runner = BenchmarkRunner(reg)
        runner._dataset = [
            {
                "source_name": "Test Doc",
                "full_text": "This is a test argument about policy.",
                "extracts": [],
            },
            {"source_name": "Empty Doc", "full_text": None, "extracts": []},
        ]
        return runner

    def test_dataset_not_loaded_raises(self):
        reg = ModelRegistry()
        runner = BenchmarkRunner(reg)
        with pytest.raises(RuntimeError, match="not loaded"):
            _ = runner.dataset

    def test_get_document_text(self):
        runner = self._make_runner_with_dataset()
        assert "test argument" in runner.get_document_text(0)

    def test_get_empty_document_text(self):
        runner = self._make_runner_with_dataset()
        assert runner.get_document_text(1) == ""

    def test_get_document_name(self):
        runner = self._make_runner_with_dataset()
        assert runner.get_document_name(0) == "Test Doc"

    @pytest.mark.asyncio
    async def test_run_cell_empty_document(self):
        runner = self._make_runner_with_dataset()
        result = await runner.run_cell("light", "mock", 1)
        assert not result.success
        assert "no text" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_cell_success(self):
        runner = self._make_runner_with_dataset()
        mock_result = {
            "phases": {
                "p1": MagicMock(
                    status=MagicMock(value="completed"),
                    capability="test",
                    output={"data": 1},
                )
            },
            "summary": {"completed": 1, "total": 1, "failed": 0, "skipped": 0},
            "unified_state": None,
        }
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await runner.run_cell("light", "mock", 0, timeout=10.0)
        assert result.success
        assert result.phases_completed == 1

    @pytest.mark.asyncio
    async def test_run_cell_timeout(self):
        runner = self._make_runner_with_dataset()

        async def slow(*a, **kw):
            import asyncio

            await asyncio.sleep(10)

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            side_effect=slow,
        ):
            result = await runner.run_cell("light", "mock", 0, timeout=0.1)
        assert not result.success
        assert "Timeout" in result.error

    @pytest.mark.asyncio
    async def test_run_cell_exception(self):
        runner = self._make_runner_with_dataset()
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ):
            result = await runner.run_cell("light", "mock", 0)
        assert not result.success
        assert "boom" in result.error


# =====================================================================
# ResultCollector Tests
# =====================================================================


class TestResultCollector:
    def _make_result(self, wf="light", model="test", idx=0, success=True):
        return BenchmarkResult(
            workflow_name=wf,
            model_name=model,
            document_index=idx,
            document_name=f"doc_{idx}",
            success=success,
            duration_seconds=1.0,
            phases_completed=2,
            phases_total=3,
            phases_failed=0,
            phases_skipped=1,
        )

    def test_save_and_load(self, tmp_path):
        collector = ResultCollector(tmp_path)
        r = self._make_result()
        collector.save(r)
        loaded = collector.load_all()
        assert len(loaded) == 1
        assert loaded[0]["workflow_name"] == "light"

    def test_save_batch(self, tmp_path):
        collector = ResultCollector(tmp_path)
        results = [self._make_result(wf=f"wf_{i}") for i in range(3)]
        collector.save_batch(results)
        assert len(collector.load_all()) == 3

    def test_query_by_workflow(self, tmp_path):
        collector = ResultCollector(tmp_path)
        collector.save(self._make_result(wf="light"))
        collector.save(self._make_result(wf="standard"))
        assert len(collector.query(workflow_name="light")) == 1

    def test_query_by_model(self, tmp_path):
        collector = ResultCollector(tmp_path)
        collector.save(self._make_result(model="a"))
        collector.save(self._make_result(model="b"))
        assert len(collector.query(model_name="a")) == 1

    def test_query_success_only(self, tmp_path):
        collector = ResultCollector(tmp_path)
        collector.save(self._make_result(success=True))
        collector.save(self._make_result(success=False))
        assert len(collector.query(success_only=True)) == 1

    def test_generate_summary(self, tmp_path):
        collector = ResultCollector(tmp_path)
        collector.save(self._make_result(wf="light", model="a"))
        collector.save(self._make_result(wf="standard", model="b"))
        summary = collector.generate_summary()
        assert summary["total"] == 2
        assert "a" in summary["by_model"]
        assert "light" in summary["by_workflow"]

    def test_empty_summary(self, tmp_path):
        collector = ResultCollector(tmp_path)
        summary = collector.generate_summary()
        assert summary["total"] == 0

    def test_export_csv(self, tmp_path):
        collector = ResultCollector(tmp_path)
        collector.save(self._make_result())
        csv_path = collector.export_csv()
        assert csv_path.exists()
        content = csv_path.read_text()
        assert "workflow_name" in content
        assert "light" in content

    def test_load_empty(self, tmp_path):
        collector = ResultCollector(tmp_path)
        assert collector.load_all() == []


# =====================================================================
# LLMJudge Tests
# =====================================================================


class TestLLMJudge:
    def test_parse_json_response_clean(self):
        judge = LLMJudge()
        raw = '{"completeness": 4, "accuracy": 3, "depth": 3, "coherence": 4, "actionability": 3, "overall": 3, "reasoning": "Good"}'
        result = judge._parse_json_response(raw)
        assert result["completeness"] == 4
        assert result["overall"] == 3

    def test_parse_json_response_with_markdown(self):
        judge = LLMJudge()
        raw = '```json\n{"completeness": 5, "overall": 4, "reasoning": "ok"}\n```'
        result = judge._parse_json_response(raw)
        assert result["completeness"] == 5

    def test_parse_json_response_embedded(self):
        judge = LLMJudge()
        raw = 'Here is my evaluation:\n{"completeness": 2, "overall": 2, "reasoning": "weak"}\nEnd.'
        result = judge._parse_json_response(raw)
        assert result["completeness"] == 2

    def test_parse_json_response_invalid(self):
        judge = LLMJudge()
        result = judge._parse_json_response("Not JSON at all")
        assert result == {}

    @pytest.mark.asyncio
    async def test_evaluate_returns_score(self):
        judge = LLMJudge()
        mock_response_content = '{"completeness": 4, "accuracy": 3, "depth": 3, "coherence": 4, "actionability": 3, "overall": 3, "reasoning": "Decent analysis"}'

        mock_message = MagicMock()
        mock_message.content = mock_response_content
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            score = await judge.evaluate(
                input_text="Test text",
                workflow_name="light",
                analysis_results={"summary": "test"},
            )
        assert isinstance(score, JudgeScore)
        assert score.overall == 3

    @pytest.mark.asyncio
    async def test_evaluate_handles_error(self):
        judge = LLMJudge()
        with patch("openai.AsyncOpenAI", side_effect=RuntimeError("No client")):
            score = await judge.evaluate(
                input_text="Test",
                workflow_name="light",
                analysis_results={},
            )
        assert score.overall == 0
        assert "failed" in score.reasoning.lower()

    def test_prepare_results_strips_raw_text(self):
        judge = LLMJudge()
        results = {
            "raw_text": "A" * 5000,
            "identified_arguments": [{"text": "arg1"}, {"text": "arg2"}],
        }
        prepared = judge._prepare_results_for_judge(results)
        # raw_text should be truncated with char count
        assert "chars total" in prepared["raw_text"]
        assert len(prepared["raw_text"]) < 200
        # arguments preserved (< MAX_LIST_ITEMS)
        assert len(prepared["identified_arguments"]) == 2

    def test_prepare_results_trims_long_lists(self):
        judge = LLMJudge()
        results = {
            "beliefs": [{"id": i} for i in range(30)],
        }
        prepared = judge._prepare_results_for_judge(results)
        # 5 items + 1 summary string
        assert len(prepared["beliefs"]) == 6
        assert "25 more" in prepared["beliefs"][-1]

    def test_prepare_results_handles_nested(self):
        judge = LLMJudge()
        results = {
            "phases": {
                "phase1": {"raw_text": "B" * 300, "output": "ok"},
            }
        }
        prepared = judge._prepare_results_for_judge(results)
        assert "chars total" in prepared["phases"]["phase1"]["raw_text"]
        assert prepared["phases"]["phase1"]["output"] == "ok"


# =====================================================================
# Baseline Corpus Tests
# =====================================================================


class TestBaselineCorpus:
    """Tests for the baseline capability evaluation corpus."""

    @property
    def corpus_path(self) -> Path:
        """Path to the baseline corpus file."""
        return Path(__file__).parent.parent.parent.parent.parent / (
            "argumentation_analysis/evaluation/corpus/baseline_corpus_v1.json"
        )

    def test_corpus_file_exists(self):
        """Verify the baseline corpus file exists."""
        assert self.corpus_path.exists(), f"Corpus file not found at {self.corpus_path}"

    def test_corpus_loads_valid_json(self):
        """Verify the corpus file is valid JSON."""
        import json

        with open(self.corpus_path, "r", encoding="utf-8") as f:
            # Strip BOM if present before parsing
            content = f.read()
            if content.startswith("\ufeff"):
                content = content[1:]
            data = json.loads(content)
        assert isinstance(data, dict)

    def test_corpus_has_required_metadata(self):
        """Verify the corpus has all required metadata fields."""
        import json

        with open(self.corpus_path, "r", encoding="utf-8") as f:
            content = f.read()
            if content.startswith("\ufeff"):
                content = content[1:]
            corpus = json.loads(content)

        assert "corpus_name" in corpus
        assert "corpus_version" in corpus
        assert "created_date" in corpus
        assert "description" in corpus
        assert "documents" in corpus
        assert "metadata" in corpus

    def test_corpus_metadata_valid(self):
        """Verify corpus metadata contains expected values."""
        import json

        with open(self.corpus_path, "r", encoding="utf-8") as f:
            content = f.read()
            if content.startswith("\ufeff"):
                content = content[1:]
            corpus = json.loads(content)

        assert corpus["corpus_name"] == "capability_evaluation_baseline_v1"
        assert corpus["metadata"]["language"] == "french"
        # total_documents matches the actual document count (corpus grows over time)
        actual_count = len(corpus["documents"])
        assert corpus["metadata"]["total_documents"] == actual_count

    def test_corpus_documents_structure(self):
        """Verify each document has the required structure."""
        import json

        with open(self.corpus_path, "r", encoding="utf-8") as f:
            content = f.read()
            if content.startswith("\ufeff"):
                content = content[1:]
            corpus = json.loads(content)

        documents = corpus["documents"]
        assert len(documents) >= 12  # Corpus grows over time; v1.1 has 22

        for doc in documents:
            assert "id" in doc, f"Document missing 'id' field: {doc}"
            assert "text" in doc, f"Document {doc.get('id')} missing 'text' field"
            assert "expected_fallacies" in doc
            assert "expected_quality_score_range" in doc
            assert "difficulty" in doc
            assert isinstance(doc["expected_fallacies"], list)
            assert isinstance(doc["expected_quality_score_range"], list)
            assert len(doc["expected_quality_score_range"]) == 2
            assert doc["difficulty"] in ["easy", "medium", "hard"]

    def test_corpus_document_ids_unique(self):
        """Verify all document IDs are unique."""
        import json

        with open(self.corpus_path, "r", encoding="utf-8") as f:
            content = f.read()
            if content.startswith("\ufeff"):
                content = content[1:]
            corpus = json.loads(content)

        ids = [doc["id"] for doc in corpus["documents"]]
        assert len(ids) == len(set(ids)), "Document IDs are not unique"

    def test_corpus_difficulty_distribution(self):
        """Verify the corpus has documents from all difficulty levels."""
        import json

        with open(self.corpus_path, "r", encoding="utf-8") as f:
            content = f.read()
            if content.startswith("\ufeff"):
                content = content[1:]
            corpus = json.loads(content)

        difficulties = [doc["difficulty"] for doc in corpus["documents"]]
        assert "easy" in difficulties
        assert "medium" in difficulties
        assert "hard" in difficulties

        expected_dist = corpus["metadata"]["difficulty_distribution"]
        # Verify metadata matches actual distribution
        actual_easy = sum(1 for d in difficulties if d == "easy")
        actual_medium = sum(1 for d in difficulties if d == "medium")
        actual_hard = sum(1 for d in difficulties if d == "hard")
        assert expected_dist["easy"] == actual_easy
        assert expected_dist["medium"] == actual_medium
        assert expected_dist["hard"] == actual_hard

    def test_corpus_fallacy_coverage(self):
        """Verify the corpus covers the expected fallacies."""
        import json

        with open(self.corpus_path, "r", encoding="utf-8") as f:
            content = f.read()
            if content.startswith("\ufeff"):
                content = content[1:]
            corpus = json.loads(content)

        expected_fallacies = corpus["metadata"]["expected_fallacy_coverage"]
        assert len(expected_fallacies) >= 14  # Should cover common fallacies

        # Verify at least some documents have expected fallacies
        docs_with_fallacies = [
            doc for doc in corpus["documents"] if doc["expected_fallacies"]
        ]
        assert len(docs_with_fallacies) >= 8

    def test_corpus_text_not_empty(self):
        """Verify all documents have non-empty text."""
        import json

        with open(self.corpus_path, "r", encoding="utf-8") as f:
            content = f.read()
            if content.startswith("\ufeff"):
                content = content[1:]
            corpus = json.loads(content)

        for doc in corpus["documents"]:
            assert doc["text"].strip(), f"Document {doc['id']} has empty text"

    def test_corpus_sample_document_content(self):
        """Verify a sample document has expected content."""
        import json

        with open(self.corpus_path, "r", encoding="utf-8") as f:
            content = f.read()
            if content.startswith("\ufeff"):
                content = content[1:]
            corpus = json.loads(content)

        # Find corpus_001 (simple political argument, no fallacies)
        doc_001 = next(
            (d for d in corpus["documents"] if d["id"] == "corpus_001"), None
        )
        assert doc_001 is not None
        assert doc_001["difficulty"] == "easy"
        assert len(doc_001["expected_fallacies"]) == 0
        assert "Monsieur le Président" in doc_001["text"]

        # Find corpus_002 (ad hominem, guilt by association)
        doc_002 = next(
            (d for d in corpus["documents"] if d["id"] == "corpus_002"), None
        )
        assert doc_002 is not None
        assert doc_002["difficulty"] == "medium"
        assert "ad_hominem" in doc_002["expected_fallacies"]
        assert "guilt_by_association" in doc_002["expected_fallacies"]


# =====================================================================
# SynergyAnalyzer Tests
# =====================================================================


class TestSynergyAnalyzer:
    """Tests for the synergy analyzer module."""

    def test_analyzer_initialization(self, tmp_path):
        """Verify analyzer can be initialized with custom results directory."""
        from argumentation_analysis.evaluation.synergy_analyzer import SynergyAnalyzer

        analyzer = SynergyAnalyzer(tmp_path)
        assert analyzer.results_dir == tmp_path

    def test_analyzer_load_corpus(self, tmp_path):
        """Verify corpus loading works."""
        from argumentation_analysis.evaluation.synergy_analyzer import SynergyAnalyzer

        analyzer = SynergyAnalyzer(tmp_path)
        corpus = analyzer.load_corpus()

        assert isinstance(corpus, dict)
        assert "corpus_name" in corpus
        assert corpus["corpus_name"] == "capability_evaluation_baseline_v1"

    def test_get_document_metadata(self, tmp_path):
        """Verify document metadata retrieval."""
        from argumentation_analysis.evaluation.synergy_analyzer import SynergyAnalyzer

        analyzer = SynergyAnalyzer(tmp_path)

        # Test valid document index
        meta = analyzer.get_document_metadata(0)
        assert meta["id"] == "corpus_001"
        assert meta["difficulty"] == "easy"
        assert isinstance(meta["expected_fallacies"], list)

        # Test out of range index
        meta_invalid = analyzer.get_document_metadata(999)
        assert meta_invalid["difficulty"] == "unknown"

    def test_analyze_workflow_performance_empty_results(self, tmp_path):
        """Verify analysis handles empty results gracefully."""
        from argumentation_analysis.evaluation.synergy_analyzer import SynergyAnalyzer

        analyzer = SynergyAnalyzer(tmp_path)
        metrics = analyzer.analyze_workflow_performance()

        assert metrics == {}

    def test_analyze_workflow_performance_with_results(self, tmp_path):
        """Verify workflow metrics are computed correctly."""
        from argumentation_analysis.evaluation.synergy_analyzer import SynergyAnalyzer
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        # Create sample results
        collector = ResultCollector(tmp_path)
        collector.save(
            BenchmarkResult(
                workflow_name="light",
                model_name="test",
                document_index=0,
                document_name="corpus_001",
                success=True,
                duration_seconds=1.5,
                phases_completed=3,
                phases_total=3,
                phases_failed=0,
                phases_skipped=0,
            )
        )
        collector.save(
            BenchmarkResult(
                workflow_name="light",
                model_name="test",
                document_index=1,
                document_name="corpus_002",
                success=False,
                duration_seconds=0.5,
                phases_completed=1,
                phases_total=3,
                phases_failed=1,
                phases_skipped=0,
                error="Test error",
            )
        )

        analyzer = SynergyAnalyzer(tmp_path)
        metrics = analyzer.analyze_workflow_performance()

        assert "light" in metrics
        assert metrics["light"].total_runs == 2
        assert metrics["light"].success_rate == 0.5
        assert metrics["light"].avg_duration == 1.5
        assert metrics["light"].completion_ratio == 1.0

    def test_compare_workflows(self, tmp_path):
        """Verify workflow comparison generates proper structure."""
        from argumentation_analysis.evaluation.synergy_analyzer import SynergyAnalyzer
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        collector = ResultCollector(tmp_path)
        collector.save(
            BenchmarkResult(
                workflow_name="light",
                model_name="test",
                document_index=0,
                document_name="corpus_001",
                success=True,
                duration_seconds=1.0,
                phases_completed=3,
                phases_total=3,
                phases_failed=0,
                phases_skipped=0,
            )
        )

        analyzer = SynergyAnalyzer(tmp_path)
        comparison = analyzer.compare_workflows()

        assert "workflows" in comparison
        assert "best_by_success_rate" in comparison
        assert "best_by_speed" in comparison
        assert "best_by_completion" in comparison
        assert "summary" in comparison
        assert comparison["summary"]["total_workflows_analyzed"] == 1

    def test_generate_recommendations_empty(self, tmp_path):
        """Verify recommendations handle empty results."""
        from argumentation_analysis.evaluation.synergy_analyzer import SynergyAnalyzer

        analyzer = SynergyAnalyzer(tmp_path)
        recommendations = analyzer.generate_recommendations()

        assert recommendations == []

    def test_generate_recommendations_with_data(self, tmp_path):
        """Verify recommendations are generated from results."""
        from argumentation_analysis.evaluation.synergy_analyzer import SynergyAnalyzer
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        # Create results for multiple workflows
        collector = ResultCollector(tmp_path)
        for idx in range(3):
            collector.save(
                BenchmarkResult(
                    workflow_name="light",
                    model_name="test",
                    document_index=idx,
                    document_name=f"corpus_00{idx+1}",
                    success=True,
                    duration_seconds=1.0,
                    phases_completed=3,
                    phases_total=3,
                    phases_failed=0,
                    phases_skipped=0,
                )
            )
        for idx in range(3):
            collector.save(
                BenchmarkResult(
                    workflow_name="standard",
                    model_name="test",
                    document_index=idx,
                    document_name=f"corpus_00{idx+1}",
                    success=True,
                    duration_seconds=2.5,
                    phases_completed=5,
                    phases_total=6,
                    phases_failed=0,
                    phases_skipped=1,
                )
            )

        analyzer = SynergyAnalyzer(tmp_path)
        recommendations = analyzer.generate_recommendations()

        assert len(recommendations) > 0
        # Check recommendation structure
        rec = recommendations[0]
        assert hasattr(rec, "use_case")
        assert hasattr(rec, "recommended_workflow")
        assert hasattr(rec, "confidence")
        assert hasattr(rec, "reasoning")
        assert 0.0 <= rec.confidence <= 1.0

    def test_generate_report(self, tmp_path):
        """Verify report generation creates valid JSON."""
        from argumentation_analysis.evaluation.synergy_analyzer import SynergyAnalyzer
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult
        import json

        # Add sample data
        collector = ResultCollector(tmp_path)
        collector.save(
            BenchmarkResult(
                workflow_name="light",
                model_name="test",
                document_index=0,
                document_name="corpus_001",
                success=True,
                duration_seconds=1.0,
                phases_completed=3,
                phases_total=3,
                phases_failed=0,
                phases_skipped=0,
            )
        )

        analyzer = SynergyAnalyzer(tmp_path)
        report_path = analyzer.generate_report()

        assert report_path.exists()
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        assert "comparison" in report
        assert "recommendations" in report
        assert "workflow_phases" in report

    def test_export_markdown_report(self, tmp_path):
        """Verify markdown report generation."""
        from argumentation_analysis.evaluation.synergy_analyzer import SynergyAnalyzer
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        # Add sample data
        collector = ResultCollector(tmp_path)
        collector.save(
            BenchmarkResult(
                workflow_name="light",
                model_name="test",
                document_index=0,
                document_name="corpus_001",
                success=True,
                duration_seconds=1.0,
                phases_completed=3,
                phases_total=3,
                phases_failed=0,
                phases_skipped=0,
            )
        )

        analyzer = SynergyAnalyzer(tmp_path)
        report_path = analyzer.export_markdown_report()

        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")

        assert "# Synergy Analysis Report" in content
        assert "## Executive Summary" in content
        assert "## Workflow Comparison" in content
        assert "## Recommendations" in content
        assert "## Workflow Phases" in content
