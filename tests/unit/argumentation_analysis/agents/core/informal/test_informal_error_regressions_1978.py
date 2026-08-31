"""#1978 — three error-handling regressions in InformalAgent (the adapter).

Discovered during the #1975 triage of the 9 root 0-byte shells
(test_informal_error_handling was one of them). Each test here pins a
behavior the historical InformalAgent defended but the current adapter
does not.

Per the issue's DoD: each test is red on main before the fix, and the fix
flips it to green. Atomic synthetic inputs only (MagicMock tools, no corpus
content, no real LLM).

Three regressions covered:

1. ``test_analyze_text_none_raises_explicit_type_error`` — when None
   reaches ``analyze_text``, the error must be an explicit, message-bearing
   TypeError. Today ``len(text)`` at line 97 raises a bare ``object of
   type 'NoneType' has no len()`` — a TypeError that does not name the
   API contract. The fix must guard explicitly so a *new* TypeError that
   surfaces later still says "the text arg is None", not "len failed".

2. ``test_analyze_text_degraded_path_isolates_detector_exception`` — when
   the local detector raises in degraded mode, the result must still be
   well-formed (empty fallacies list). The SK path above it already has
   this try/except; the degraded path does not.

3. ``test_tool_with_wrong_type_is_logged_and_ignored`` — passing a
   non-callable as a tool (e.g. ``"fallacy_detector": "string"``) must
   surface as a warning, not be silently absorbed by ``hasattr``. Today
   it is silently dropped (``hasattr("string", "detect") is False``), so
   callers cannot distinguish "I forgot this tool" from "I configured a
   broken tool".
"""

import logging
from unittest.mock import MagicMock

import pytest

from argumentation_analysis.agents.core.informal.informal_agent_adapter import (
    InformalAgent,
)


pytestmark = [pytest.mark.unit, pytest.mark.no_jvm_session]


# ---------------------------------------------------------------------------
# (1) analyze_text(None) — MAJEURE
# ---------------------------------------------------------------------------


class TestAnalyzeTextNone:
    """``analyze_text(None)`` must raise an explicit, message-bearing
    ``TypeError`` that names the contract — not a bare
    ``object of type 'NoneType' has no len()`` from ``len(text)``.

    The issue's anti-pendule is explicit: do NOT wrap analyze_text in a
    global try/except. The fix must guard ``len(text)`` explicitly so
    the error remains visible. So the assertion is *not* "no raise" — it
    is "the TypeError names the API contract".
    """

    def test_analyze_text_none_raises_explicit_type_error(self):
        agent = InformalAgent(
            tools={"fallacy_detector": MagicMock(detect=MagicMock(return_value=[]))}
        )
        with pytest.raises(TypeError) as excinfo:
            agent.analyze_text(None)
        msg = str(excinfo.value)
        # The bug we are fixing is "the TypeError is generic and does not
        # name the API contract". Pin a contract-naming keyword.
        assert "analyze_text" in msg or "text" in msg, (
            f"Expected an explicit TypeError that names the analyze_text / "
            f"text contract, got: {msg!r}"
        )
        # And specifically: NOT the bare len() message.
        assert "has no len()" not in msg, (
            f"Expected an explicit guard, not the bare len() error "
            f"raised by unguarded ``len(text)``. Got: {msg!r}"
        )


# ---------------------------------------------------------------------------
# (2) degraded path isolates detector exception — MINEURE
# ---------------------------------------------------------------------------


class TestDegradedPathIsolatesDetectorException:
    """The SK path has a try/except that absorbs SK agent failures. The
    degraded path (``detector.detect(text)`` at line 121) does not — a
    broken local detector propagates. The fallback is *supposed* to be
    the safety net; today it is the failure surface.
    """

    def test_analyze_text_degraded_path_isolates_detector_exception(self):
        broken_detector = MagicMock()
        broken_detector.detect = MagicMock(
            side_effect=RuntimeError("local detector exploded")
        )
        agent = InformalAgent(tools={"fallacy_detector": broken_detector})
        # SK agent will not be available in the test environment (the
        # InformalAnalysisAgent ctor raises on the ``tools=`` kwarg, so
        # adapter sets _sk_agent = None and falls into degraded mode).
        # The degraded mode should still swallow its own detector failure
        # to match the SK path's behavior.
        result = agent.analyze_text("some text")
        assert isinstance(result, dict)
        assert "fallacies" in result
        # When the local detector raises, the historical contract was
        # "return an empty fallacies list" (no partial result). The fix
        # may also choose to log and return None; we accept either an
        # empty list or None here, but NOT a propagated exception.
        assert result["fallacies"] in ([], None), (
            f"Expected empty fallacies on degraded-path detector failure, "
            f"got {result['fallacies']!r}"
        )
        assert "analysis_timestamp" in result


# ---------------------------------------------------------------------------
# (3) tool type not validated — MINEURE
# ---------------------------------------------------------------------------


class TestToolTypeIsSurfaced:
    """A tool value that lacks the expected interface is silently dropped
    by ``hasattr(detector, "detect")`` (line 120). The caller cannot
    distinguish "I forgot this tool" from "I passed a string by mistake".

    The fix's contract per the issue: *signaler l'outil ignoré* (log it
    as a warning), not *refuser l'outil* (strict type-check, which would
    break MagicMock-based tests).
    """

    def test_tool_with_wrong_type_is_logged_and_ignored(self, caplog):
        # Non-callable, non- `` return_value``-shaped object — silently
        # dropped today. The fix must emit at least one WARNING log line
        # that names the offending tool key.
        agent = InformalAgent(
            tools={"fallacy_detector": "this is not a callable"},
        )
        with caplog.at_level(logging.WARNING, logger=__name__.split(".")[0]):
            result = agent.analyze_text("text")
        # Behavioral minimum: the call still returns a well-formed dict
        # (we did not break MagicMock consumers).
        assert isinstance(result, dict)
        assert "fallacies" in result
        # Discriminator: the offending tool key must appear in a WARNING
        # log line so operators can distinguish "no tool" from "broken
        # tool". We accept any log message that mentions the key.
        offending_logs = [
            record
            for record in caplog.records
            if record.levelno >= logging.WARNING
            and "fallacy_detector" in record.getMessage()
        ]
        assert offending_logs, (
            "Expected a WARNING log naming the 'fallacy_detector' key when "
            "a non-callable tool value is passed. Today the tool is "
            "silently dropped by ``hasattr``. Got log records: "
            f"{[(r.levelname, r.getMessage()) for r in caplog.records]}"
        )