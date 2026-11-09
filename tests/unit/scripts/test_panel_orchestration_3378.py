"""#3378 — the five engines meet the panel through the existing blind judge.

No network, no encrypted corpus: loading and state production are injected.
The judge remains ``scripts/dataset/judge_panel.py``; these tests pin the
input/output contract around it, never a second judging implementation.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import compare_orchestration_modes as harness
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from scripts.dataset.judge_panel import pipeline_text_from_state

SYNTHETIC_TEXT = "Une proposition synthétique, suivie d'une réponse argumentée."


class TestPanelInputAndJudgeContract:
    def test_panel_documents_reuse_the_judges_loader(self):
        seen = []

        def loader(panel):
            seen.extend(panel)
            return {doc_id: SYNTHETIC_TEXT for doc_id in panel}

        docs = harness.load_panel_documents(["doc_A", "doc_B"], loader=loader)

        assert seen == ["doc_A", "doc_B"]
        assert list(docs) == ["doc_A", "doc_B"]

    def test_panel_documents_refuse_a_document_the_corpus_does_not_carry(self):
        with pytest.raises(ValueError, match="doc_Z"):
            harness.load_panel_documents(
                ["doc_A", "doc_Z"], loader=lambda panel: {"doc_A": SYNTHETIC_TEXT}
            )

    def test_a_state_dump_is_the_full_snapshot_and_the_measured_usage(self, tmp_path):
        state = UnifiedAnalysisState(SYNTHETIC_TEXT)
        state.act1_framing = "Cadrage synthétique."
        result = harness.ModeResult(
            mode="pipeline_spectacular",
            corpus_id="doc_A",
            success=True,
            panel_state=state,
            extra_metrics={
                "llm_usage": {"phase": {"calls": 2, "prompt_tokens": 8}},
            },
        )

        artifacts = harness.write_panel_mode_artifacts(result, tmp_path)

        assert artifacts is not None
        assert artifacts.state["raw_text"] == SYNTHETIC_TEXT
        assert artifacts.state["act1_framing"] == "Cadrage synthétique."
        assert artifacts.signature["llm_usage"]["phase"]["calls"] == 2
        assert "raw_text" not in artifacts.signature["state"]
        judged = pipeline_text_from_state(artifacts.state, artifacts.signature)
        assert "Cadrage synthétique." in judged

    def test_an_artifact_is_never_silently_overwritten(self, tmp_path):
        state = UnifiedAnalysisState(SYNTHETIC_TEXT)
        result = harness.ModeResult(
            mode="pipeline_spectacular",
            corpus_id="doc_A",
            success=True,
            panel_state=state,
        )
        harness.write_panel_mode_artifacts(result, tmp_path)
        with pytest.raises(ValueError, match="refusing to overwrite"):
            harness.write_panel_mode_artifacts(result, tmp_path)

    def test_a_stateless_engine_has_an_honest_absence(self):
        # #3472: hierarchical_delegation left this class — its adapter hands
        # the judge the run's own record, so it is in the stateful set and a
        # result WITHOUT a panel_state now names the runner, not the engine
        # (``runner_failed_before_state_capture``). A mode still outside the
        # set keeps the engine absence.
        assert "hierarchical_delegation" in harness.PANEL_STATEFUL_MODES
        result = harness.ModeResult(
            mode="pipeline_standard", corpus_id="doc_A", success=True
        )

        assert (
            harness.panel_state_absence_reason(result)
            == "engine_has_no_unified_analysis_state"
        )

    def test_a_failed_state_run_is_an_absence_never_a_complete_arm(self):
        result = harness.ModeResult(
            mode="pipeline_spectacular",
            corpus_id="doc_A",
            success=False,
            panel_state=UnifiedAnalysisState(SYNTHETIC_TEXT),
        )

        assert harness.panel_state_absence_reason(result) == "incomplete_partial_state"

    def test_the_manifest_matches_the_exact_panel_not_a_file_count(self, tmp_path):
        state_dir = tmp_path / "pipeline_spectacular" / "states"
        signature_dir = tmp_path / "pipeline_spectacular" / "signatures"
        state_dir.mkdir(parents=True)
        signature_dir.mkdir(parents=True)
        (state_dir / "state_full_doc_B.json").write_text("{}", encoding="utf-8")
        (signature_dir / "signature_doc_B.json").write_text("{}", encoding="utf-8")
        manifest = harness.build_panel_manifest(
            out_dir=tmp_path,
            panel=["doc_A"],
            requested_modes=["pipeline_spectacular"],
            judge_model="judge-fixture",
            wall_seconds=900.0,
        )
        payload = json.loads(manifest.read_text(encoding="utf-8"))

        assert payload["judge_commands"] == {}
        assert "pipeline_spectacular" in payload["state_absences"]

    def test_the_manifest_points_to_the_same_judge_for_each_state(self, tmp_path):
        state_dir = tmp_path / "pipeline_spectacular" / "states"
        signature_dir = tmp_path / "pipeline_spectacular" / "signatures"
        state_dir.mkdir(parents=True)
        signature_dir.mkdir(parents=True)
        (state_dir / "state_full_doc_A.json").write_text("{}", encoding="utf-8")
        (signature_dir / "signature_doc_A.json").write_text("{}", encoding="utf-8")
        manifest = harness.build_panel_manifest(
            out_dir=tmp_path,
            panel=["doc_A"],
            requested_modes=["pipeline_spectacular", "hierarchical_delegation"],
            judge_model="judge-fixture",
            wall_seconds=900.0,
        )
        payload = json.loads(manifest.read_text(encoding="utf-8"))

        assert payload["judge_model"] == "judge-fixture"
        assert payload["judge_calls_made"] is False
        assert payload["engine_runs_executed"] is False
        assert payload["wall_seconds"] == 900.0
        command = payload["judge_commands"]["pipeline_spectacular"]
        assert "scripts/dataset/judge_panel.py" in command
        assert "--dry-run" in command
        assert "hierarchical_delegation" in payload["state_absences"]


class TestStateBearingEnginesExposeTheirRealState:
    def test_pipeline_exposes_the_state_its_workflow_wrote(self):
        observed = {}

        async def fake_run(**kwargs):
            observed.update(kwargs)
            assert kwargs["workflow_name"] == "spectacular"
            assert kwargs["state"].raw_text == SYNTHETIC_TEXT
            assert kwargs["deanonymized"] is False
            assert kwargs["render_restitution"] is True
            assert kwargs["source_metadata"]["opaque_id"] == "doc_A"
            return {
                "state_snapshot": {},
                "summary": {},
                "unified_state": kwargs["state"],
                "restitution_report": object(),
            }

        async def drive():
            with patch(
                "argumentation_analysis.orchestration.unified_pipeline"
                ".run_unified_analysis",
                side_effect=fake_run,
            ):
                return await harness.run_pipeline_mode(
                    SYNTHETIC_TEXT,
                    "doc_A",
                    "spectacular",
                    max_wall_seconds=None,
                    panel_mode=True,
                )

        result = asyncio.run(drive())
        assert observed["checkpoint_callback"] is not None
        assert result.panel_state is observed["state"]
        assert result.panel_state_reason == "completed"
        assert result.extra_metrics["panel_workflow"] == "spectacular"

    def test_conversational_generates_acts_in_panel_mode(self):
        state = UnifiedAnalysisState(SYNTHETIC_TEXT)

        async def fake_run(**kwargs):
            assert kwargs["render_restitution"] is True
            assert kwargs["source_metadata"]["opaque_id"] == "doc_A"
            return {
                "state_snapshot": {},
                "conversation_log": [],
                "unified_state": state,
                "phases": [],
                "budget": {},
            }

        async def drive():
            with patch(
                "argumentation_analysis.orchestration.conversational_orchestrator"
                ".run_conversational_analysis",
                side_effect=fake_run,
            ):
                return await harness.run_conversational_mode(
                    SYNTHETIC_TEXT, "doc_A", panel_mode=True
                )

        result = asyncio.run(drive())
        assert result.panel_state is state
        assert state.deanonymized is False
        assert state.source_metadata["opaque_id"] == "doc_A"

    def test_the_bridge_builds_its_acts_after_its_own_phases(self):
        calls = []
        observed = {}

        async def fake_hierarchical(**kwargs):
            observed.update(kwargs)
            calls.append("phases")
            return {
                "summary": {"completed": 2, "total": 2},
                "objectives": [{"id": "o1"}],
                "conclusion": "Conclusion synthétique.",
            }

        async def fake_generate(state, text):
            calls.append("acts")
            state.act1_framing = "Cadrage synthétique."
            state.act2_narrative = "Récit synthétique."
            state.act3_conclusion = "Conclusion synthétique."
            return object()

        async def drive():
            with patch(
                "argumentation_analysis.orchestration.registry_setup" ".setup_registry",
                return_value=object(),
            ), patch(
                "argumentation_analysis.orchestration.hierarchical.orchestrator"
                ".run_hierarchical_analysis",
                side_effect=fake_hierarchical,
            ), patch(
                "argumentation_analysis.reporting.restitution.conversational_adapter"
                ".generate_and_render_for_conversational_state",
                side_effect=fake_generate,
            ):
                return await harness.run_hierarchical_bridge_mode(
                    SYNTHETIC_TEXT,
                    "doc_A",
                    max_wall_seconds=None,
                    panel_mode=True,
                    source_metadata={"opaque_id": "doc_A"},
                )

        result = asyncio.run(drive())
        assert calls == ["phases", "acts"]
        assert result.panel_state is observed["state"]
        assert result.panel_state.act1_framing == "Cadrage synthétique."
        assert result.panel_state_reason == "completed"


class TestRunAllWritesOneDirectoryPerMode:
    def test_each_run_has_an_accounting_window_and_its_own_judge_directory(
        self, tmp_path, monkeypatch
    ):
        windows = []

        class _State:
            def __init__(self, text):
                self.text = text

            def get_state_snapshot(self, summarize=False):
                assert summarize is False
                return {"raw_text": self.text, "act1_framing": "Acte synthétique"}

        async def fake_runner(text, corpus_id, **kwargs):
            from argumentation_analysis.services.llm_cache import _usage_stats

            _usage_stats.record(10, 2, None, model="fixture-model")
            windows.append(corpus_id)
            return harness.ModeResult(
                mode="pipeline_spectacular",
                corpus_id=corpus_id,
                success=True,
                panel_state=_State(text),
            )

        monkeypatch.setitem(harness.MODE_RUNNERS, "pipeline_spectacular", fake_runner)
        monkeypatch.setattr(harness, "initialize_jvm", lambda: None, raising=False)

        results = asyncio.run(
            harness.run_all(
                modes=["pipeline_spectacular"],
                corpora=["doc_A"],
                document_texts={"doc_A": SYNTHETIC_TEXT},
                panel_out_dir=tmp_path,
                panel_judge_model="judge-fixture",
            )
        )

        assert windows == ["doc_A"]
        assert len(results) == 1
        states_dir = tmp_path / "pipeline_spectacular" / "states"
        signatures_dir = tmp_path / "pipeline_spectacular" / "signatures"
        state = json.loads(
            (states_dir / "state_full_doc_A.json").read_text(encoding="utf-8")
        )
        signature = json.loads(
            (signatures_dir / "signature_doc_A.json").read_text(encoding="utf-8")
        )
        assert state["llm_usage"]["(unattributed)"]["calls"] == 1
        assert state["llm_usage"]["(unattributed)"]["prompt_tokens"] == 10
        assert signature["opaque_id"] == "doc_A"
        assert "raw_text" not in signature["state"]
        manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        usage = manifest["engine_usage"]["pipeline_spectacular"]
        assert manifest["engine_runs_executed"] is True
        assert usage["documents"] == 1
        assert usage["live_calls"] == 1
        assert usage["prompt_tokens"] == 10
        assert usage["computed_cost_usd"] is None

    def test_a_dry_run_prices_nothing_and_names_every_absent_arm(
        self, tmp_path, monkeypatch, capsys
    ):
        async def forbidden_runner(*args, **kwargs):
            raise AssertionError("a dry run must not execute an engine")

        monkeypatch.setitem(
            harness.MODE_RUNNERS, "pipeline_spectacular", forbidden_runner
        )
        monkeypatch.setattr(harness, "initialize_jvm", lambda: None, raising=False)

        results = asyncio.run(
            harness.run_all(
                modes=["pipeline_spectacular"],
                corpora=["doc_A"],
                dry_run=True,
                document_texts={"doc_A": SYNTHETIC_TEXT},
                panel_out_dir=tmp_path,
                panel_judge_model="judge-fixture",
            )
        )
        output = capsys.readouterr().out
        manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

        assert results == []
        assert manifest["judge_calls_made"] is False
        assert manifest["engine_runs_executed"] is False
        assert manifest["engine_usage"] == {}
        assert manifest["judge_commands"] == {}
        assert manifest["state_absences"]["pipeline_spectacular"].startswith(
            "incomplete_state_surface"
        )
        assert "no engine was run" in output

    def test_an_existing_panel_mode_cannot_be_silently_dropped(self):
        assert "pipeline_spectacular" in harness.MODE_RUNNERS
