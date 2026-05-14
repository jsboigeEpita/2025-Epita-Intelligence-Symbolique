"""Tests for structured logging with correlation IDs (#454).

Validates:
- PhaseLogger injects correlation_id and phase_name into log records
- JsonFormatter produces valid JSON output
- HumanFormatter includes correlation prefix
- correlation_id propagates across a multi-phase workflow run
- LOG_FORMAT=json activates JSON output
"""
import json
import logging
import os
import uuid

import pytest

from argumentation_analysis.orchestration.structured_logging import (
    HumanFormatter,
    JsonFormatter,
    PhaseLogger,
    generate_correlation_id,
    get_phase_logger,
)


class TestPhaseLogger:
    """Test PhaseLogger adapter."""

    def test_correlation_id_injected(self):
        logger = logging.getLogger("test_correlation")
        adapter = PhaseLogger(logger, correlation_id="abc-123")
        record = adapter.logger.makeRecord(
            "test", logging.INFO, "", 0, "hello", (), None
        )
        adapter.process("hello", {"extra": {}})
        # The extra should be in the kwargs
        assert adapter.extra.get("correlation_id") == "abc-123"

    def test_phase_name_injected(self):
        adapter = PhaseLogger(
            logging.getLogger("test_phase"),
            correlation_id="cid",
            phase_name="extract",
        )
        assert adapter.extra.get("phase_name") == "extract"

    def test_with_phase_returns_child(self):
        parent = PhaseLogger(
            logging.getLogger("test_child"),
            correlation_id="parent-cid",
        )
        child = parent.with_phase("fallacy_detect")
        assert child.extra.get("correlation_id") == "parent-cid"
        assert child.extra.get("phase_name") == "fallacy_detect"
        # Parent should NOT have phase_name
        assert "phase_name" not in parent.extra

    def test_generate_correlation_id(self):
        cid = generate_correlation_id()
        # Must be a valid UUID
        uuid.UUID(cid)  # raises ValueError if invalid


class TestJsonFormatter:
    """Test JSON log formatter."""

    def test_produces_valid_json(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "test message"
        assert parsed["level"] == "INFO"
        assert "timestamp" in parsed

    def test_includes_correlation_id(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="with correlation", args=(), exc_info=None,
        )
        record.correlation_id = "cid-456"
        record.phase_name = "extract"
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["correlation_id"] == "cid-456"
        assert parsed["phase_name"] == "extract"


class TestHumanFormatter:
    """Test human-readable formatter."""

    def test_no_prefix_without_context(self):
        formatter = HumanFormatter("%(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="plain message", args=(), exc_info=None,
        )
        output = formatter.format(record)
        assert output == "plain message"

    def test_prefix_with_correlation_id(self):
        formatter = HumanFormatter("%(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="contextual message", args=(), exc_info=None,
        )
        record.correlation_id = "abcdefgh-1234"
        output = formatter.format(record)
        assert "[abcdefgh]" in output
        assert "contextual message" in output

    def test_prefix_with_phase_name(self):
        formatter = HumanFormatter("%(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="phase message", args=(), exc_info=None,
        )
        record.phase_name = "extract"
        output = formatter.format(record)
        assert "[extract]" in output


class TestLogFormatEnv:
    """Test LOG_FORMAT environment variable control."""

    def test_json_format_env(self, monkeypatch):
        # Reset the configured flag
        import argumentation_analysis.orchestration.structured_logging as sl_mod
        monkeypatch.setenv("LOG_FORMAT", "json")
        monkeypatch.setattr(sl_mod, "_configured", False)

        slog = get_phase_logger("test_env_json", correlation_id="env-test")
        # Verify we got a PhaseLogger
        assert isinstance(slog, PhaseLogger)
        assert slog.extra["correlation_id"] == "env-test"

    def test_human_format_default(self, monkeypatch):
        import argumentation_analysis.orchestration.structured_logging as sl_mod
        monkeypatch.delenv("LOG_FORMAT", raising=False)
        monkeypatch.setattr(sl_mod, "_configured", False)

        slog = get_phase_logger("test_env_human", correlation_id="human-test")
        assert isinstance(slog, PhaseLogger)


class TestCorrelationPropagation:
    """Test that correlation_id propagates across simulated multi-phase run."""

    def test_correlation_propagates_across_phases(self):
        cid = str(uuid.uuid4())
        phases = ["extract", "fallacy_detect", "fol_validate", "synthesis"]

        collected = []
        for phase_name in phases:
            slog = get_phase_logger(
                "test_propagation", correlation_id=cid, phase_name=phase_name
            )
            collected.append({
                "correlation_id": slog.extra.get("correlation_id"),
                "phase_name": slog.extra.get("phase_name"),
            })

        # All entries share the same correlation_id
        assert all(e["correlation_id"] == cid for e in collected)
        # Each has its own phase_name
        assert [e["phase_name"] for e in collected] == phases
