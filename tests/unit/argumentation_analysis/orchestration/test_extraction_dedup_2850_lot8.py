"""#2850 lot 8 R1135 — the extraction dedups per category, across windows only.

Lot 8 merged the k windows' items through ONE ``_seen`` set, keyed on
``(text, source_quote)`` and shared by arguments, claims and fallacies, and it
added each item the moment it was read. Two defects followed:

* a claim worded exactly like an argument vanished — same pair, and the
  arguments are merged first, so the claim never reached the payload the
  analysts read (``claim_count`` under-reported what the call said);
* two identical units inside ONE answer collapsed, which is not duplication
  of OUR making: the windows overlap by construction (they tile below
  3 × window), so a unit read twice is the plan's overlap; a unit a single
  answer reports twice is the model's own output, and merging it is a silent
  rewrite of the measurement.

These witnesses are hermetic in the lot 8 manner (``_get_openai_client`` +
``_guarded_chat_completion`` mocked, zero network — #3072).
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.core.reading_window import LLM_EXTRACTION_WINDOW
from argumentation_analysis.core.shared_state import UnifiedAnalysisState

INVOKE = "argumentation_analysis.orchestration.invoke_callables"

_DOC_LEN = 60000  # three windows, so cross-window merging is really exercised
M1, M2, M3 = "MARQUEUN", "MARQUEDEUX", "MARQUETROIS"
_MARKERS = {M1: 1000, M2: 29500, M3: 58500}

SHARED_TEXT = "Le fournil ne petille que si la bonde reste ouverte."
SHARED_QUOTE = M1


def _synthetic_doc(length: int = _DOC_LEN) -> str:
    doc = "mot " * (length // 4)
    assert len(doc) == length, len(doc)
    for marker, at in _MARKERS.items():
        doc = doc[:at] + marker + doc[at + len(marker) :]
    assert len(doc) == length
    return doc


def _resp(payload: Dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
    )


def _run(text: str, payload_for) -> Dict[str, Any]:
    """Run the extraction with a fake answer built per window."""

    def _fake(_client: Any, model: Any = None, messages: Any = None, **kw: Any):
        return _resp(payload_for(messages[-1]["content"]))

    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_fact_extraction,
    )

    with patch(
        f"{INVOKE}._get_openai_client", return_value=(MagicMock(), "gpt-witness")
    ), patch(f"{INVOKE}._guarded_chat_completion", AsyncMock(side_effect=_fake)):
        state = UnifiedAnalysisState(text)
        return asyncio.run(_invoke_fact_extraction(text, {"_state_object": state}))


class TestOneSeenSetPerCategory:
    """A claim identical to an argument is a claim, not a repeat of it."""

    def test_a_claim_worded_like_an_argument_survives(self) -> None:
        payload = {
            "arguments": [{"text": SHARED_TEXT, "source_quote": SHARED_QUOTE}],
            "claims": [{"text": SHARED_TEXT, "source_quote": SHARED_QUOTE}],
            "fallacies": [],
            "summary": "s",
        }
        out = _run(_synthetic_doc(), lambda _window: payload)
        assert out["argument_count"] == 1, out
        assert out["claim_count"] == 1, (
            "the claim carries the same (text, quote) pair as the argument, but "
            "it is a different extraction — a shared _seen set swallowed it"
        )

    def test_a_fallacy_is_not_merged_into_a_unit_of_the_same_wording(self) -> None:
        payload = {
            "arguments": [{"text": SHARED_TEXT, "source_quote": SHARED_QUOTE}],
            "claims": [],
            "fallacies": [{"type": SHARED_TEXT, "source_quote": SHARED_QUOTE}],
            "summary": "s",
        }
        out = _run(_synthetic_doc(), lambda _window: payload)
        assert len(out["fallacies"]) == 1, out


class TestDedupIsAcrossWindowsOnly:
    """The overlap belongs to the plan; a repeated item inside one answer does not."""

    def test_the_same_unit_read_by_every_window_is_kept_once(self) -> None:
        doc = _synthetic_doc()
        payload = {
            "arguments": [{"text": SHARED_TEXT, "source_quote": SHARED_QUOTE}],
            "claims": [],
            "fallacies": [],
            "summary": "s",
        }
        (out,) = (_run(doc, lambda _window: payload),)
        assert len(out["arguments"]) == 1, (
            "three overlapping windows report the same unit — that is the "
            f"plan's duplication and must collapse, got {out['arguments']}"
        )

    def test_two_identical_units_in_one_answer_are_both_kept(self) -> None:
        payload = {
            "arguments": [
                {"text": SHARED_TEXT, "source_quote": SHARED_QUOTE},
                {"text": SHARED_TEXT, "source_quote": SHARED_QUOTE},
            ],
            "claims": [],
            "fallacies": [],
            "summary": "s",
        }
        out = _run(_synthetic_doc(), lambda _window: payload)
        assert len(out["arguments"]) == 2, (
            "a single answer reporting the same unit twice is the model's own "
            "output: merging it inside the window is a silent rewrite, and "
            f"only the cross-window overlap is ours — got {out['arguments']}"
        )
