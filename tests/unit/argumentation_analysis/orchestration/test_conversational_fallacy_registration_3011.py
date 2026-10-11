"""#3011 — the conversational lane registers fallacy fields and counts failures.

The parent-harness registration loop (``conversational_orchestrator``) passed
neither ``confidence`` nor ``problematic_quote`` to ``add_fallacy`` — the
confidence lived only as prose in the fallback justification — and an
``except Exception: pass`` made a failing registration vanish under the
summary line. Born red on main ``6e52577de`` (issue #3011, refs #2972/#3010).

Synthetic detections only — no corpus sentence. The state is the real
``UnifiedAnalysisState`` (its ``add_fallacy`` is the contract under test,
``core/shared_state.py:361``), driven through the same sys.modules seam the
KK witnesses use.
"""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState


def _fake_invoke_module(
    monkeypatch: pytest.MonkeyPatch,
    per_arg_fallacies: List[Dict[str, Any]],
    whole_text_fallacies: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Swap invoke_callables for controlled detections (KK-test seam).

    The fake proxies the real module's namespace: ``conversational_orchestrator``
    imports ``LLMBudgetExceeded``/``_bump_sk_budget`` from it at module level
    (l. 37), so a bare stub only works when the orchestrator is already in
    sys.modules — in an isolated session it dies at import (measured).
    """
    import types

    import argumentation_analysis.orchestration.invoke_callables as real_invoke

    fake = types.ModuleType(real_invoke.__name__)
    fake.__dict__.update(real_invoke.__dict__)

    async def fake_per_arg(text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "fallacies": per_arg_fallacies,
            "exploration_method": "per_argument_parallel",
        }

    async def fake_whole_text(text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"fallacies": whole_text_fallacies or []}

    fake._invoke_hierarchical_fallacy_per_argument = fake_per_arg
    fake._invoke_hierarchical_fallacy = fake_whole_text
    monkeypatch.setitem(sys.modules, real_invoke.__name__, fake)


def _run(text: str, state: Any) -> Optional[Dict[str, Any]]:
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        _run_parent_harness_fallback,
    )

    return asyncio.get_event_loop().run_until_complete(
        _run_parent_harness_fallback(text, state)
    )


class TestRegistrationCarriesFields:
    """Witness 1 + 2: fields land as fields; an unmeasured confidence stays absent."""

    def test_confidence_and_quote_land_as_fields(self, monkeypatch):
        _fake_invoke_module(
            monkeypatch,
            [
                {
                    "fallacy_type": "Ad hominem",
                    "justification": "attack on the person, not the point",
                    "confidence": 0.8,
                    "problematic_quote": "a synthetic quote",
                }
            ],
        )
        state = UnifiedAnalysisState("synthetic text")
        _run("synthetic text", state)
        entries = list(state.identified_fallacies.values())
        assert len(entries) == 1
        assert entries[0]["confidence"] == 0.8
        assert entries[0]["problematic_quote"] == "a synthetic quote"

    def test_unmeasured_confidence_stores_no_key(self, monkeypatch):
        _fake_invoke_module(
            monkeypatch,
            [{"fallacy_type": "Ad hominem", "explanation": "carries no confidence"}],
        )
        state = UnifiedAnalysisState("synthetic text")
        _run("synthetic text", state)
        entries = list(state.identified_fallacies.values())
        assert len(entries) == 1
        # Unmeasured is absent, never 0.0 (#1019).
        assert "confidence" not in entries[0]

    def test_fallback_justification_drops_the_confidence_prose(self, monkeypatch):
        _fake_invoke_module(
            monkeypatch,
            # No justification, no explanation: only the fallback fires.
            [{"fallacy_type": "Ad hominem", "confidence": 0.9}],
        )
        state = UnifiedAnalysisState("synthetic text")
        _run("synthetic text", state)
        entries = list(state.identified_fallacies.values())
        assert len(entries) == 1
        assert "confidence" not in entries[0]["justification"]
        assert entries[0]["confidence"] == 0.9


class TestRegistrationFailureCounted:
    """Witness 3: a failing registration is counted and surfaced, not swallowed."""

    def test_failure_counted_logged_and_summarized(self, monkeypatch, caplog):
        _fake_invoke_module(
            monkeypatch,
            [{"fallacy_type": "Ad hominem", "explanation": "synthetic detection"}],
        )

        class RaisingState(UnifiedAnalysisState):
            """Real state whose registration always fails (synthetic defect)."""

            def add_fallacy(self, *args: Any, **kwargs: Any) -> str:
                raise RuntimeError("synthetic registration failure")

        state = RaisingState("synthetic text")
        with caplog.at_level("INFO", logger="ConversationalOrchestrator"):
            result = _run("synthetic text", state)
        assert result is not None
        assert result["fallacies_registered"] == 0
        assert result["fallacies_registration_failed"] == 1
        # The failure is logged with its reason…
        assert any(
            "synthetic registration failure" in rec.getMessage()
            for rec in caplog.records
            if rec.levelno >= logging.WARNING
        )
        # …and the summary line reports it next to registered/skipped.
        assert any(
            "1 failed" in rec.getMessage()
            for rec in caplog.records
            if "registered" in rec.getMessage()
        )
