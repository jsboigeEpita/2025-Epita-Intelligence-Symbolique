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
from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult, BenchmarkRunner
from argumentation_analysis.evaluation.result_collector import ResultCollector
from argumentation_analysis.evaluation.judge import LLMJudge, JudgeScore


# =====================================================================
# ModelConfig Tests
# =====================================================================


class TestModelConfig:
    def test_basic_creation(self):
        mc = ModelConfig(model_id="gpt-5-mini", base_url="https://api.openai.com/v1", api_key="sk-test")
        assert mc.model_id == "gpt-5-mini"
        assert mc.display_name == "gpt-5-mini"

    def test_custom_display_name(self):
        mc = ModelConfig(model_id="x", base_url="y", api_key="z", display_name="My Model")
        assert mc.display_name == "My Model"

    def test_thinking_model_flag(self):
        mc = ModelConfig(model_id="qwen", base_url="u", api_key="k", is_thinking_model=True)
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
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_CHAT_MODEL_ID": "gpt-test",
            "OPENAI_BASE_URL": "https://test.api/v1",
        }, clear=False):
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
            workflow_name="test", model_name="m", document_index=0,
            document_name="d", success=True, duration_seconds=0.5,
            phases_completed=1, phases_total=1, phases_failed=0, phases_skipped=0,
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
            {"source_name": "Test Doc", "full_text": "This is a test argument about policy.", "extracts": []},
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
            "phases": {"p1": MagicMock(status=MagicMock(value="completed"), capability="test", output={"data": 1})},
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
            workflow_name=wf, model_name=model, document_index=idx,
            document_name=f"doc_{idx}", success=success, duration_seconds=1.0,
            phases_completed=2, phases_total=3, phases_failed=0, phases_skipped=1,
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
