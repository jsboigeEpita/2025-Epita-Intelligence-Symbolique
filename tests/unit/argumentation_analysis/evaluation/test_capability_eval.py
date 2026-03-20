"""
Tests for capability_eval.py — systematic capability contribution analysis.

Tests cover:
- CapabilityConfig normalization
- PRESET_CONFIGS completeness
- FilteredRegistry allowlist enforcement
- EvalCell.composite_score property
- run_single_cell (mocked registry and judge)
- compute_marginal_scores
- compute_synergies
- build_report
- write_cells_jsonl / write_report (file I/O)
"""

import json
import pytest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.evaluation.capability_eval import (
    CapabilityConfig,
    PRESET_CONFIGS,
    FilteredRegistry,
    EvalCell,
    MarginalScore,
    SynergyScore,
    CapabilityEvalReport,
    compute_marginal_scores,
    compute_synergies,
    build_report,
    write_cells_jsonl,
    write_report,
    run_single_cell,
    _build_eval_workflow,
    EVAL_WORKFLOW_PHASES,
)


# ---------------------------------------------------------------------------
# CapabilityConfig
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCapabilityConfig:
    def test_deduplicates_capabilities(self):
        cfg = CapabilityConfig(
            name="test",
            capabilities=["fact_extraction", "fact_extraction", "argument_quality"],
        )
        assert cfg.capabilities.count("fact_extraction") == 1

    def test_sorts_capabilities(self):
        cfg = CapabilityConfig(name="t", capabilities=["z_cap", "a_cap", "m_cap"])
        assert cfg.capabilities == ["a_cap", "m_cap", "z_cap"]

    def test_description_default(self):
        cfg = CapabilityConfig(name="t", capabilities=[])
        assert cfg.description == ""


# ---------------------------------------------------------------------------
# PRESET_CONFIGS
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPresetConfigs:
    def test_all_required_configs_present(self):
        required = {"baseline", "quality", "fallacy", "counter", "debate", "logic", "full"}
        assert required.issubset(set(PRESET_CONFIGS.keys()))

    def test_baseline_is_minimal(self):
        assert PRESET_CONFIGS["baseline"].capabilities == ["fact_extraction"]

    def test_full_has_most_capabilities(self):
        cap_counts = {name: len(cfg.capabilities) for name, cfg in PRESET_CONFIGS.items()}
        assert cap_counts["full"] == max(cap_counts.values())

    def test_all_configs_have_descriptions(self):
        for name, cfg in PRESET_CONFIGS.items():
            assert cfg.description, f"Config '{name}' missing description"


# ---------------------------------------------------------------------------
# FilteredRegistry
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFilteredRegistry:
    def _make_registry(self, caps_per_provider):
        """Build a mock registry where find_for_capability returns providers."""
        registry = MagicMock()
        def find(capability):
            return caps_per_provider.get(capability, [])
        registry.find_for_capability.side_effect = find
        return registry

    def test_allowed_capability_returns_providers(self):
        mock_prov = MagicMock()
        reg = self._make_registry({"argument_quality": [mock_prov]})
        filtered = FilteredRegistry(reg, {"argument_quality"})

        result = filtered.find_for_capability("argument_quality")
        assert result == [mock_prov]

    def test_blocked_capability_returns_empty(self):
        mock_prov = MagicMock()
        reg = self._make_registry({"fallacy_detection": [mock_prov]})
        filtered = FilteredRegistry(reg, {"argument_quality"})  # fallacy not allowed

        result = filtered.find_for_capability("fallacy_detection")
        assert result == []

    def test_empty_allowlist_blocks_everything(self):
        reg = self._make_registry({"fact_extraction": [MagicMock()]})
        filtered = FilteredRegistry(reg, set())

        assert filtered.find_for_capability("fact_extraction") == []

    def test_delegates_other_attrs(self):
        reg = MagicMock()
        reg.some_attr = "hello"
        filtered = FilteredRegistry(reg, set())

        assert filtered.some_attr == "hello"


# ---------------------------------------------------------------------------
# EvalCell
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestEvalCell:
    def _make_cell(self, overall=4.0, depth=4.0, completeness=4.0,
                   accuracy=4.0, coherence=4.0, actionability=4.0):
        return EvalCell(
            config_name="test", capabilities_active=["cap_a"],
            document_name="doc_001", document_index=0,
            phases_run=3, phases_skipped=1, phases_failed=0,
            overall=overall, depth=depth, completeness=completeness,
            accuracy=accuracy, coherence=coherence, actionability=actionability,
        )

    def test_composite_all_equal(self):
        cell = self._make_cell()
        assert cell.composite_score == pytest.approx(4.0, abs=0.01)

    def test_composite_only_overall(self):
        cell = self._make_cell(overall=5.0, depth=0, completeness=0,
                               accuracy=0, coherence=0, actionability=0)
        # 5.0 * 0.40 = 2.0
        assert cell.composite_score == pytest.approx(2.0, abs=0.01)

    def test_timestamp_auto_set(self):
        cell = EvalCell(
            config_name="c", capabilities_active=[], document_name="d",
            document_index=0, phases_run=0, phases_skipped=0, phases_failed=0,
        )
        assert cell.timestamp != ""

    def test_no_error_by_default(self):
        cell = EvalCell(
            config_name="c", capabilities_active=[], document_name="d",
            document_index=0, phases_run=0, phases_skipped=0, phases_failed=0,
        )
        assert cell.judge_error is None


# ---------------------------------------------------------------------------
# _build_eval_workflow
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBuildEvalWorkflow:
    def test_workflow_created(self):
        workflow = _build_eval_workflow()
        assert workflow is not None
        assert workflow.name == "capability_eval"

    def test_all_phases_optional(self):
        workflow = _build_eval_workflow()
        for phase in workflow.phases:
            assert phase.optional is True, f"Phase '{phase.name}' should be optional"

    def test_phase_count_matches_definition(self):
        workflow = _build_eval_workflow()
        assert len(workflow.phases) == len(EVAL_WORKFLOW_PHASES)

    def test_no_circular_dependencies(self):
        workflow = _build_eval_workflow()
        errors = workflow.validate()
        assert errors == [], f"Workflow has validation errors: {errors}"


# ---------------------------------------------------------------------------
# run_single_cell
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRunSingleCell:
    def _make_executor(self, status_map=None):
        """Build a mock WorkflowExecutor that returns fixed phase statuses."""
        from argumentation_analysis.orchestration.workflow_dsl import PhaseResult, PhaseStatus

        if status_map is None:
            status_map = {"extract": "completed", "quality": "completed", "fallacy": "skipped"}

        async def fake_execute(workflow, input_data, state=None, **kwargs):
            results = {}
            for name, status_str in status_map.items():
                r = MagicMock(spec=PhaseResult)
                r.status = MagicMock()
                r.status.value = status_str
                results[name] = r
            return results

        executor = MagicMock()
        executor.execute = fake_execute
        return executor

    @pytest.mark.asyncio
    async def test_counts_phases_correctly(self):
        config = PRESET_CONFIGS["quality"]
        registry = MagicMock()
        executor = self._make_executor({
            "extract": "completed",
            "quality": "completed",
            "fallacy": "skipped",
            "other": "failed",
        })
        workflow = _build_eval_workflow()

        with patch("argumentation_analysis.evaluation.capability_eval.FilteredRegistry") as mock_fr:
            mock_fr.return_value = registry
            cell = await run_single_cell(
                config=config,
                document_text="Test text",
                document_name="doc_001",
                document_index=0,
                full_registry=registry,
                judge=None,
                workflow=workflow,
                executor=executor,
            )

        assert cell.phases_run == 2
        assert cell.phases_skipped == 1
        assert cell.phases_failed == 1

    @pytest.mark.asyncio
    async def test_skip_judge_when_none(self):
        config = PRESET_CONFIGS["baseline"]
        registry = MagicMock()
        executor = self._make_executor({"extract": "completed"})
        workflow = _build_eval_workflow()

        with patch("argumentation_analysis.evaluation.capability_eval.FilteredRegistry"):
            cell = await run_single_cell(
                config=config,
                document_text="Test",
                document_name="doc",
                document_index=0,
                full_registry=registry,
                judge=None,
                workflow=workflow,
                executor=executor,
            )

        # No judge → all scores remain 0
        assert cell.overall == 0.0
        assert cell.judge_error is None

    @pytest.mark.asyncio
    async def test_judge_score_applied(self):
        from argumentation_analysis.evaluation.judge import JudgeScore

        config = PRESET_CONFIGS["quality"]
        registry = MagicMock()
        executor = self._make_executor()
        workflow = _build_eval_workflow()

        fake_score = JudgeScore(
            completeness=4.0, accuracy=3.5, depth=4.5,
            coherence=4.0, actionability=3.8, overall=4.2,
            reasoning="Good.", judge_model="test-model",
        )
        judge = MagicMock()
        judge.evaluate = AsyncMock(return_value=fake_score)

        with patch("argumentation_analysis.evaluation.capability_eval.FilteredRegistry"):
            cell = await run_single_cell(
                config=config,
                document_text="Test text",
                document_name="doc",
                document_index=0,
                full_registry=registry,
                judge=judge,
                workflow=workflow,
                executor=executor,
            )

        assert cell.overall == 4.2
        assert cell.depth == 4.5

    @pytest.mark.asyncio
    async def test_judge_error_recorded(self):
        config = PRESET_CONFIGS["baseline"]
        registry = MagicMock()
        executor = self._make_executor()
        workflow = _build_eval_workflow()

        judge = MagicMock()
        judge.evaluate = AsyncMock(side_effect=RuntimeError("API error"))

        with patch("argumentation_analysis.evaluation.capability_eval.FilteredRegistry"):
            cell = await run_single_cell(
                config=config,
                document_text="Test",
                document_name="doc",
                document_index=0,
                full_registry=registry,
                judge=judge,
                workflow=workflow,
                executor=executor,
            )

        assert cell.judge_error == "API error"
        assert cell.overall == 0.0


# ---------------------------------------------------------------------------
# compute_marginal_scores
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestComputeMarginalScores:
    def _make_cell(self, caps, overall):
        c = EvalCell(
            config_name="c", capabilities_active=list(caps),
            document_name="d", document_index=0,
            phases_run=0, phases_skipped=0, phases_failed=0,
            overall=overall, depth=overall, completeness=overall,
            accuracy=overall, coherence=overall, actionability=overall,
        )
        return c

    def test_positive_marginal(self):
        """Cap A adds value: configs with A score higher than without."""
        cells = [
            self._make_cell(["cap_a"], 5.0),
            self._make_cell([], 3.0),
        ]
        marginals = compute_marginal_scores(cells)
        cap_a = next(m for m in marginals if m.capability == "cap_a")
        assert cap_a.marginal_contribution == pytest.approx(2.0, abs=0.01)

    def test_empty_cells(self):
        assert compute_marginal_scores([]) == []

    def test_sorted_descending(self):
        cells = [
            self._make_cell(["cap_b"], 5.0),
            self._make_cell(["cap_a"], 4.0),
            self._make_cell([], 3.0),
        ]
        marginals = compute_marginal_scores(cells)
        contributions = [m.marginal_contribution for m in marginals]
        assert contributions == sorted(contributions, reverse=True)

    def test_n_with_n_without(self):
        cells = [
            self._make_cell(["cap_x"], 4.0),
            self._make_cell(["cap_x"], 5.0),
            self._make_cell([], 3.0),
        ]
        marginals = compute_marginal_scores(cells)
        cap_x = next(m for m in marginals if m.capability == "cap_x")
        assert cap_x.n_with == 2
        assert cap_x.n_without == 1


# ---------------------------------------------------------------------------
# compute_synergies
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestComputeSynergies:
    def _make_cell(self, caps, overall):
        c = EvalCell(
            config_name="c", capabilities_active=list(caps),
            document_name="d", document_index=0,
            phases_run=0, phases_skipped=0, phases_failed=0,
            overall=overall, depth=overall, completeness=overall,
            accuracy=overall, coherence=overall, actionability=overall,
        )
        return c

    def test_empty_cells(self):
        assert compute_synergies([]) == []

    def test_returns_list_of_synergy_scores(self):
        cells = [
            self._make_cell(["a"], 3.0),
            self._make_cell(["b"], 3.0),
            self._make_cell(["a", "b"], 7.0),
            self._make_cell([], 2.0),
        ]
        synergies = compute_synergies(cells)
        assert len(synergies) >= 1
        assert all(isinstance(s, SynergyScore) for s in synergies)


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBuildReport:
    def _make_cell(self, cfg, doc, overall):
        c = EvalCell(
            config_name=cfg, capabilities_active=["cap_a"],
            document_name=doc, document_index=0,
            phases_run=1, phases_skipped=0, phases_failed=0,
            overall=overall, depth=overall, completeness=overall,
            accuracy=overall, coherence=overall, actionability=overall,
        )
        return c

    def test_empty(self):
        report = build_report([], [], [])
        assert report.total_cells == 0
        assert report.best_config is None

    def test_best_config_selected(self):
        cells = [
            self._make_cell("baseline", "d1", 3.0),
            self._make_cell("full", "d1", 5.0),
        ]
        report = build_report(cells, [], [])
        assert report.best_config == "full"

    def test_config_scores_sorted(self):
        cells = [
            self._make_cell("full", "d1", 5.0),
            self._make_cell("baseline", "d1", 3.0),
        ]
        report = build_report(cells, [], [])
        composites = [cs["avg_composite"] for cs in report.config_scores]
        assert composites == sorted(composites, reverse=True)

    def test_marginal_scores_included(self):
        marginals = [MarginalScore("cap_a", 4.0, 3.0, 1.0, 5, 5)]
        report = build_report([], marginals, [])
        assert len(report.marginal_scores) == 1
        assert report.marginal_scores[0]["capability"] == "cap_a"


# ---------------------------------------------------------------------------
# write_cells_jsonl
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestWriteCellsJsonl:
    def test_writes_valid_jsonl(self, tmp_path):
        cells = [
            EvalCell(
                config_name="baseline", capabilities_active=["fact_extraction"],
                document_name="doc_001", document_index=0,
                phases_run=2, phases_skipped=1, phases_failed=0,
                overall=4.0, depth=3.5, completeness=4.0,
                accuracy=4.0, coherence=4.2, actionability=3.8,
                reasoning="Decent.",
            )
        ]
        out = tmp_path / "cells.jsonl"
        write_cells_jsonl(cells, out)

        lines = out.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["config_name"] == "baseline"
        assert data["overall"] == 4.0

    def test_creates_parent_dirs(self, tmp_path):
        out = tmp_path / "sub" / "cells.jsonl"
        write_cells_jsonl([], out)
        assert out.exists()


# ---------------------------------------------------------------------------
# write_report
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestWriteReport:
    def test_creates_json_and_markdown(self, tmp_path):
        report = CapabilityEvalReport(
            configs_evaluated=["baseline", "full"],
            num_documents=5,
            total_cells=10,
            config_scores=[{
                "config_name": "full",
                "capabilities": ["cap_a", "cap_b"],
                "n_docs": 5,
                "avg_composite": 0.8,
                "avg_overall": 4.0,
                "avg_depth": 3.5,
                "avg_completeness": 3.8,
                "avg_phases_run": 6.0,
            }],
            marginal_scores=[{
                "capability": "cap_a",
                "avg_score_with": 4.0,
                "avg_score_without": 3.0,
                "marginal_contribution": 1.0,
                "n_with": 5,
                "n_without": 5,
            }],
            best_config="full",
            best_composite=0.8,
        )
        write_report(report, tmp_path)

        assert (tmp_path / "capability_eval_report.json").exists()
        assert (tmp_path / "capability_eval_report.md").exists()

    def test_json_valid(self, tmp_path):
        report = CapabilityEvalReport()
        write_report(report, tmp_path)
        data = json.loads((tmp_path / "capability_eval_report.json").read_text(encoding="utf-8"))
        assert "total_cells" in data

    def test_markdown_has_section_headers(self, tmp_path):
        report = CapabilityEvalReport(marginal_scores=[])
        write_report(report, tmp_path)
        md = (tmp_path / "capability_eval_report.md").read_text(encoding="utf-8")
        assert "Configuration Rankings" in md
        assert "Marginal Capability Contributions" in md
