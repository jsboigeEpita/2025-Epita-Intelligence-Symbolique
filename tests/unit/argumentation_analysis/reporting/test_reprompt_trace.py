"""Tests for RepromptTraceExtractor and RepromptTrace."""

import json
from unittest.mock import MagicMock

import pytest

from argumentation_analysis.reporting.reprompt_trace import (
    RepromptTrace,
    RepromptTraceExtractor,
)


class TestRepromptTrace:
    def test_to_dict(self):
        t = RepromptTrace(
            phase_name="Extraction",
            turn=3,
            attempt_idx=1,
            fingerprint_before=[2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            fingerprint_after=[3, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            delta=[1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            outcome="ok",
            agent_name="InformalAgent",
        )
        d = t.to_dict()
        assert d["phase_name"] == "Extraction"
        assert d["attempt_idx"] == 1
        assert d["outcome"] == "ok"

    def test_total_delta(self):
        t = RepromptTrace(
            phase_name="Detection",
            turn=1,
            attempt_idx=1,
            fingerprint_before=[0, 0, 0],
            fingerprint_after=[2, 3, 0],
            delta=[2, 3, 0],
            outcome="ok",
        )
        assert t.total_delta == 5

    def test_grew(self):
        t_ok = RepromptTrace(
            phase_name="X", turn=1, attempt_idx=1,
            fingerprint_before=[0], fingerprint_after=[1],
            delta=[1], outcome="ok",
        )
        assert t_ok.grew is True

        t_fail = RepromptTrace(
            phase_name="X", turn=1, attempt_idx=1,
            fingerprint_before=[0], fingerprint_after=[0],
            delta=[0], outcome="gave_up",
        )
        assert t_fail.grew is False

    def test_to_json(self):
        t = RepromptTrace(
            phase_name="Extraction", turn=1, attempt_idx=1,
            fingerprint_before=[0], fingerprint_after=[1],
            delta=[1], outcome="ok",
        )
        data = json.loads(t.to_json())
        assert data["outcome"] == "ok"

    def test_to_markdown(self):
        t = RepromptTrace(
            phase_name="Detection", turn=2, attempt_idx=1,
            fingerprint_before=[0], fingerprint_after=[1],
            delta=[1], outcome="ok", agent_name="InformalAgent",
        )
        md = t.to_markdown()
        assert "### Re-prompt #1" in md
        assert "Detection" in md
        assert "InformalAgent" in md


class TestRepromptTraceExtractor:
    def test_record_creates_trace(self):
        ext = RepromptTraceExtractor()
        ext.record(
            phase_name="Extraction",
            turn=3,
            attempt_idx=1,
            fingerprint_before=(2, 1, 0),
            fingerprint_after=(3, 2, 0),
            outcome="ok",
            agent_name="ExtractAgent",
        )
        assert len(ext.traces) == 1
        assert ext.traces[0].phase_name == "Extraction"

    def test_to_json_output(self):
        ext = RepromptTraceExtractor()
        ext.record("Extraction", 1, 1, (0,), (1,), "ok")
        ext.record("Detection", 2, 1, (1,), (1,), "gave_up")
        data = json.loads(ext.to_json())
        assert data["total_traces"] == 2
        assert "Extraction" in data["phases_affected"]
        assert data["outcomes"]["ok"] == 1
        assert data["outcomes"]["gave_up"] == 1

    def test_to_markdown_summary(self):
        ext = RepromptTraceExtractor()
        ext.record("Extraction", 1, 1, (0,), (1,), "ok", "ExtractAgent")
        md = ext.to_markdown()
        assert "# Re-Prompt Trace Report" in md
        assert "| Extraction |" in md

    def test_to_markdown_empty(self):
        ext = RepromptTraceExtractor()
        md = ext.to_markdown()
        assert "No re-prompt events" in md

    def test_from_phase_log(self):
        phase_log = [
            {"phase": "Extraction", "turn": 1, "agent": "ExtractAgent", "content": "..."},
            {"phase": "Extraction", "turn": 1, "agent": "ExtractAgent", "content": "rp...", "re_prompt": 1},
            {"phase": "Detection", "turn": 2, "agent": "InformalAgent", "content": "rp2...", "re_prompt": 1},
        ]
        fingerprints = {
            "Extraction:1": [(0, 0, 0), (1, 1, 0)],
            "Detection:2": [(1, 1, 0), (1, 2, 0)],
        }
        ext = RepromptTraceExtractor.from_phase_log(phase_log, fingerprints)
        assert len(ext.traces) == 2

    def test_to_dict(self):
        ext = RepromptTraceExtractor()
        ext.record("Extraction", 1, 1, (0,), (1,), "ok")
        d = ext.to_dict()
        assert d["total_traces"] == 1
        assert len(d["traces"]) == 1
