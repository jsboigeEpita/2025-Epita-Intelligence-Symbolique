"""
Tests for run_llm_judge.py — LLM Judge quality scorer runner.

Tests cover:
- load_benchmark_results (JSONL parsing)
- run_judge_on_results (filtering, error handling, output structure)
- build_report (aggregation, ranking)
- write_scores_jsonl / write_report (file I/O)
- JudgeResult.composite_score property
- CLI argparse
"""

import json
import pytest
import asyncio
from dataclasses import asdict
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from argumentation_analysis.evaluation.run_llm_judge import (
    JudgeResult,
    JudgeReport,
    load_benchmark_results,
    run_judge_on_results,
    build_report,
    write_scores_jsonl,
    write_report,
)
from argumentation_analysis.evaluation.judge import LLMJudge, JudgeScore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_benchmark_entry(
    workflow="standard",
    model="default",
    doc_name="corpus_001",
    doc_idx=0,
    success=True,
    raw_text="Sample text for analysis.",
) -> dict:
    return {
        "workflow_name": workflow,
        "model_name": model,
        "document_index": doc_idx,
        "document_name": doc_name,
        "success": success,
        "state_snapshot": {
            "raw_text": raw_text,
            "ranking_results": [],
            "aspic_results": [],
        },
        "phase_results": {},
        "timestamp": "2026-03-20T05:00:00",
    }


def make_judge_score(overall=4.0, depth=3.5) -> JudgeScore:
    return JudgeScore(
        completeness=4.0,
        accuracy=3.5,
        depth=depth,
        coherence=4.2,
        actionability=3.8,
        overall=overall,
        reasoning="Good analysis.",
        judge_model="test-judge-model",
    )


# ---------------------------------------------------------------------------
# JudgeResult
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJudgeResult:
    def test_composite_score_formula(self):
        """composite = 0.40*overall + 0.20*depth + 0.20*completeness + ..."""
        jr = JudgeResult(
            workflow_name="standard",
            model_name="default",
            document_name="doc_001",
            document_index=0,
            judge_model="gpt-5-mini",
            completeness=4.0,
            accuracy=4.0,
            depth=4.0,
            coherence=4.0,
            actionability=4.0,
            overall=4.0,
            reasoning="All 4s.",
        )
        # When all scores are the same, composite equals that score
        assert jr.composite_score == pytest.approx(4.0, abs=0.01)

    def test_composite_weights_overall(self):
        """overall contributes 40% — highest weight."""
        jr = JudgeResult(
            workflow_name="w",
            model_name="m",
            document_name="d",
            document_index=0,
            judge_model="j",
            completeness=0.0,
            accuracy=0.0,
            depth=0.0,
            coherence=0.0,
            actionability=0.0,
            overall=5.0,
            reasoning="",
        )
        # Only overall contributes: 5.0 * 0.40 = 2.0
        assert jr.composite_score == pytest.approx(2.0, abs=0.01)

    def test_timestamp_auto_set(self):
        jr = JudgeResult(
            workflow_name="w",
            model_name="m",
            document_name="d",
            document_index=0,
            judge_model="j",
            completeness=1,
            accuracy=1,
            depth=1,
            coherence=1,
            actionability=1,
            overall=1,
            reasoning="",
        )
        assert jr.timestamp != ""

    def test_no_error_by_default(self):
        jr = JudgeResult(
            workflow_name="w",
            model_name="m",
            document_name="d",
            document_index=0,
            judge_model="j",
            completeness=1,
            accuracy=1,
            depth=1,
            coherence=1,
            actionability=1,
            overall=1,
            reasoning="",
        )
        assert jr.error is None


# ---------------------------------------------------------------------------
# load_benchmark_results
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadBenchmarkResults:
    def test_loads_valid_jsonl(self, tmp_path):
        entries = [
            make_benchmark_entry("standard", "default", "corpus_001"),
            make_benchmark_entry("light", "openrouter", "corpus_002"),
        ]
        path = tmp_path / "results.jsonl"
        path.write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n",
            encoding="utf-8",
        )

        loaded = load_benchmark_results(path)
        assert len(loaded) == 2
        assert loaded[0]["workflow_name"] == "standard"
        assert loaded[1]["document_name"] == "corpus_002"

    def test_skips_blank_lines(self, tmp_path):
        path = tmp_path / "results.jsonl"
        path.write_text(
            json.dumps(make_benchmark_entry()) + "\n\n\n",
            encoding="utf-8",
        )
        loaded = load_benchmark_results(path)
        assert len(loaded) == 1

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        loaded = load_benchmark_results(path)
        assert loaded == []


# ---------------------------------------------------------------------------
# run_judge_on_results
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunJudgeOnResults:
    async def _run(self, entries, mock_score, **kwargs):
        judge = MagicMock(spec=LLMJudge)
        judge.model_name = "test-judge"
        judge.evaluate = AsyncMock(return_value=mock_score)
        return await run_judge_on_results(entries, judge, **kwargs), judge

    @pytest.mark.asyncio
    async def test_evaluates_successful_entry(self):
        entries = [make_benchmark_entry()]
        score = make_judge_score(overall=4.5)

        results, judge = await self._run(entries, score)

        assert len(results) == 1
        assert results[0].overall == 4.5
        assert results[0].error is None
        judge.evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_failed_entries(self):
        entries = [make_benchmark_entry(success=False)]
        score = make_judge_score()

        results, judge = await self._run(entries, score)

        assert results == []
        judge.evaluate.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_entry_without_raw_text(self):
        entry = make_benchmark_entry()
        entry["state_snapshot"]["raw_text"] = ""
        score = make_judge_score()

        results, judge = await self._run([entry], score)

        assert results == []
        judge.evaluate.assert_not_called()

    @pytest.mark.asyncio
    async def test_workflow_filter(self):
        entries = [
            make_benchmark_entry(workflow="standard"),
            make_benchmark_entry(workflow="light", doc_name="corpus_002"),
        ]
        score = make_judge_score()

        results, judge = await self._run(entries, score, workflows_filter=["standard"])

        assert len(results) == 1
        assert results[0].workflow_name == "standard"

    @pytest.mark.asyncio
    async def test_model_filter(self):
        entries = [
            make_benchmark_entry(model="default"),
            make_benchmark_entry(model="openrouter", doc_name="corpus_002"),
        ]
        score = make_judge_score()

        results, judge = await self._run(entries, score, models_filter=["openrouter"])

        assert len(results) == 1
        assert results[0].model_name == "openrouter"

    @pytest.mark.asyncio
    async def test_judge_exception_becomes_error_result(self):
        entry = make_benchmark_entry()
        judge = MagicMock(spec=LLMJudge)
        judge.model_name = "test-judge"
        judge.evaluate = AsyncMock(side_effect=RuntimeError("API timeout"))

        results = await run_judge_on_results([entry], judge)

        assert len(results) == 1
        assert results[0].error == "API timeout"
        assert results[0].overall == 0

    @pytest.mark.asyncio
    async def test_result_fields_populated_from_score(self):
        entry = make_benchmark_entry(
            workflow="formal_debate",
            model="openrouter",
            doc_name="corpus_007",
            doc_idx=6,
        )
        score = make_judge_score(overall=3.8, depth=4.2)
        score.completeness = 4.5
        score.accuracy = 3.0
        score.coherence = 4.0
        score.actionability = 3.5
        score.judge_model = "gpt-5-mini"

        results, _ = await self._run([entry], score)

        r = results[0]
        assert r.workflow_name == "formal_debate"
        assert r.model_name == "openrouter"
        assert r.document_name == "corpus_007"
        assert r.document_index == 6
        assert r.depth == 4.2
        assert r.judge_model == "gpt-5-mini"


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildReport:
    def _make_result(self, model, workflow, overall=4.0, depth=3.5):
        return JudgeResult(
            workflow_name=workflow,
            model_name=model,
            document_name="doc",
            document_index=0,
            judge_model="judge",
            completeness=4.0,
            accuracy=4.0,
            depth=depth,
            coherence=4.0,
            actionability=4.0,
            overall=overall,
            reasoning="",
        )

    def test_empty_results(self):
        report = build_report([])
        assert report.total_cells_evaluated == 0
        assert report.total_errors == 0
        assert report.aggregates == []
        assert report.best_by_quality is None

    def test_counts_errors(self):
        results = [self._make_result("m", "w")]
        results[0].error = "some error"
        report = build_report(results)
        assert report.total_errors == 1
        # Errored result excluded from aggregates
        assert report.aggregates == []

    def test_aggregates_multiple_docs(self):
        results = [
            self._make_result("default", "standard", overall=4.0),
            self._make_result("default", "standard", overall=5.0),
        ]
        report = build_report(results)
        assert len(report.aggregates) == 1
        assert report.aggregates[0]["avg_overall"] == pytest.approx(4.5)
        assert report.aggregates[0]["n_docs"] == 2

    def test_sorted_by_composite_descending(self):
        results = [
            self._make_result("default", "light", overall=2.0, depth=2.0),
            self._make_result("openrouter", "standard", overall=5.0, depth=5.0),
        ]
        report = build_report(results)
        # Best should be first
        assert report.aggregates[0]["model_name"] == "openrouter"

    def test_best_by_quality_populated(self):
        results = [self._make_result("default", "standard", overall=4.0)]
        report = build_report(results)
        assert report.best_by_quality is not None
        assert report.best_by_quality["model"] == "default"
        assert report.best_by_quality["workflow"] == "standard"

    def test_best_by_depth_selects_highest_depth(self):
        results = [
            self._make_result("default", "light", overall=5.0, depth=2.0),
            self._make_result("openrouter", "standard", overall=3.0, depth=5.0),
        ]
        report = build_report(results)
        assert report.best_by_depth["workflow"] == "standard"
        assert report.best_by_depth["avg_depth"] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# write_scores_jsonl
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWriteScoresJsonl:
    def test_creates_file_with_correct_entries(self, tmp_path):
        results = [
            JudgeResult(
                workflow_name="standard",
                model_name="default",
                document_name="doc_001",
                document_index=0,
                judge_model="gpt-5-mini",
                completeness=4.0,
                accuracy=4.0,
                depth=4.0,
                coherence=4.0,
                actionability=4.0,
                overall=4.0,
                reasoning="Good.",
            )
        ]
        out = tmp_path / "scores.jsonl"
        write_scores_jsonl(results, out)

        lines = out.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["workflow_name"] == "standard"
        assert data["overall"] == 4.0

    def test_creates_parent_dirs(self, tmp_path):
        out = tmp_path / "subdir" / "scores.jsonl"
        write_scores_jsonl([], out)
        assert out.exists()


# ---------------------------------------------------------------------------
# write_report
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWriteReport:
    def test_creates_json_and_markdown(self, tmp_path):
        report = JudgeReport(
            total_cells_evaluated=5,
            total_errors=0,
            aggregates=[
                {
                    "model_name": "default",
                    "workflow_name": "standard",
                    "n_docs": 5,
                    "avg_composite": 0.75,
                    "avg_overall": 4.0,
                    "avg_completeness": 3.8,
                    "avg_accuracy": 4.2,
                    "avg_depth": 3.5,
                    "avg_coherence": 4.0,
                    "avg_actionability": 3.9,
                }
            ],
            best_by_quality={
                "model": "default",
                "workflow": "standard",
                "avg_composite": 0.75,
                "avg_overall": 4.0,
            },
            best_by_depth={
                "model": "default",
                "workflow": "standard",
                "avg_depth": 3.5,
            },
        )
        out = tmp_path / "report"
        write_report(report, out)

        assert (tmp_path / "report.json").exists()
        assert (tmp_path / "report.md").exists()

    def test_markdown_contains_table_header(self, tmp_path):
        report = JudgeReport(aggregates=[])
        out = tmp_path / "report"
        write_report(report, out)

        md = (tmp_path / "report.md").read_text(encoding="utf-8")
        assert "| Model | Workflow |" in md

    def test_json_is_valid(self, tmp_path):
        report = JudgeReport()
        out = tmp_path / "r"
        write_report(report, out)

        data = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
        assert "total_cells_evaluated" in data


# ── Regression tests for bugs fixed in cc726a98 ──────────────────────────


class TestMaxDocsRegression:
    """Regression test: max_docs filter must actually limit documents (#133 review).

    Bug: doc_key was added to seen_docs BEFORE the len check, making the
    `continue` branch unreachable. The filter was a no-op.
    """

    @pytest.fixture
    def entries_3_docs(self):
        """3 successful entries from 3 different documents."""
        return [
            {
                "workflow_name": "standard",
                "model_name": "gpt-5-mini",
                "document_name": f"doc_{i}",
                "success": True,
                "state_snapshot": {"raw_text": f"Text for doc {i}. " * 10},
            }
            for i in range(3)
        ]

    async def test_max_docs_2_excludes_third(self, entries_3_docs):
        """With max_docs=2, only 2 unique documents should be evaluated."""
        mock_judge = AsyncMock(spec=LLMJudge)
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeScore(
                overall=4.0,
                completeness=3.5,
                accuracy=4.0,
                depth=3.0,
                coherence=4.5,
                actionability=3.0,
                reasoning="test",
                judge_model="test-model",
            )
        )
        results = await run_judge_on_results(entries_3_docs, mock_judge, max_docs=2)
        # Only 2 docs should have been evaluated
        assert len(results) == 2
        doc_names = {r.document_name for r in results}
        assert len(doc_names) == 2

    async def test_max_docs_1_evaluates_only_first(self, entries_3_docs):
        """With max_docs=1, only 1 document should be evaluated."""
        mock_judge = AsyncMock(spec=LLMJudge)
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeScore(
                overall=4.0,
                completeness=3.5,
                accuracy=4.0,
                depth=3.0,
                coherence=4.5,
                actionability=3.0,
                reasoning="test",
                judge_model="test-model",
            )
        )
        results = await run_judge_on_results(entries_3_docs, mock_judge, max_docs=1)
        assert len(results) == 1

    async def test_max_docs_none_evaluates_all(self, entries_3_docs):
        """With max_docs=None, all documents should be evaluated."""
        mock_judge = AsyncMock(spec=LLMJudge)
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeScore(
                overall=4.0,
                completeness=3.5,
                accuracy=4.0,
                depth=3.0,
                coherence=4.5,
                actionability=3.0,
                reasoning="test",
                judge_model="test-model",
            )
        )
        results = await run_judge_on_results(entries_3_docs, mock_judge, max_docs=None)
        assert len(results) == 3
