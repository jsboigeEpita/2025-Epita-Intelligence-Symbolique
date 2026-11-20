"""#3538 — the stakes document read is recorded on the shared state.

The census row and ``political/README.md`` said the 3,000-character excerpt
was recorded (``record_reading_window``); the code never passed the state to
``selected_text``, so ``state.reading_window_status["stakes_extractor"]``
was never written and the reading record could not say what stakes read.

Witnesses here (all free: no key, no network, no corpus — the LLM call is a
loopback fake):

- the document read IS recorded after the phase (status, offset, window);
- the excerpt inside the prompt is byte-identical to the recorded slice
  (the fix threads a recorder, it does not move the window);
- a run with no LLM client records nothing for that site (nothing was read
  — the excerpt computation sits after the ``llm_client is None`` return);
- positive control: the same state carries the ``stakes`` coverage entry
  from ``record_analysis_coverage`` — the phase wrote to THIS state;
- mutation: the state dropped from the ``selected_text`` call, the entry
  disappears — the witness depends on the fix, not on a passing shape.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

import argumentation_analysis.orchestration.invoke_callables as ic
from argumentation_analysis.core.reading_window import (
    LLM_EXTRACTION_WINDOW,
    select_reading_head,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState

# Synthetic, corpus-free: ~60,000 characters of ordinary prose so the head
# selection is a plain offset-0 head (reading_window.py:763 docstring) and
# the window is the full 3,000.
_SENTENCES = 1150
_TEXT = " ".join(
    f"Phrase synthetique numero {i} du temoin stakes, ponctuee."
    for i in range(1, _SENTENCES + 1)
)

_PROMPTS: List[str] = []


def _state() -> UnifiedAnalysisState:
    """A real production state — the recorder under test is the real one."""
    state = UnifiedAnalysisState("stakes-reading-recorded-3538 synthetic probe")
    state.raw_text = _TEXT
    state.identified_arguments = {
        "arg_1": _TEXT[200:340],
        "arg_2": _TEXT[1200:1340],
    }
    return state


def _reply() -> Any:
    content = json.dumps(
        {
            "stakes": [],
            "stakeholders": [],
            "rhetorical_register": "",
            "discursive_arena": "",
        }
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


async def _fake_llm_call(client: Any, **kwargs: Any) -> Any:
    _PROMPTS.append(kwargs["messages"][0]["content"])
    return _reply()


def _wire_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ic, "_get_openai_client", lambda: (object(), "loopback-model"))
    monkeypatch.setattr(ic, "_guarded_chat_completion", _fake_llm_call)


class TestStakesReadingRecorded:
    """Ask 1: after the phase, the document read sits on the state."""

    async def test_the_document_read_is_recorded(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _PROMPTS.clear()
        _wire_loopback(monkeypatch)
        state = _state()

        output = await ic._invoke_stakes_extractor(
            "unused when the state carries raw_text", {"_state_object": state}
        )
        assert "degraded" not in output, f"phase degraded: {output!r}"

        entry = state.reading_window_status.get("stakes_extractor")
        assert entry is not None, (
            "no reading_window_status entry for stakes_extractor — the "
            "document read is not recorded (#3538)"
        )
        selection = select_reading_head(_TEXT, LLM_EXTRACTION_WINDOW)
        assert entry["window"] == selection.window
        assert entry["offset"] == selection.offset
        assert entry["status"] == "selected"

    async def test_the_prompt_carries_the_recorded_slice(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ask 3 proxy: the excerpt sent IS the slice the record names."""
        _PROMPTS.clear()
        _wire_loopback(monkeypatch)
        state = _state()
        await ic._invoke_stakes_extractor(
            "unused when the state carries raw_text", {"_state_object": state}
        )
        assert _PROMPTS, "the loopback fake saw no stakes prompt"
        entry = state.reading_window_status["stakes_extractor"]
        recorded_slice = _TEXT[entry["offset"] : entry["offset"] + entry["window"]]
        assert (
            recorded_slice and recorded_slice in _PROMPTS[0]
        ), "the prompt excerpt is not the recorded slice — the window moved"


class TestNoClientRecordsNothing:
    """Ask 2: nothing was read, nothing is recorded."""

    async def test_no_client_writes_no_entry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ic, "_get_openai_client", lambda: (None, ""))
        state = _state()
        await ic._invoke_stakes_extractor(
            "unused when the state carries raw_text", {"_state_object": state}
        )
        assert "stakes_extractor" not in state.reading_window_status


class TestPositiveControl:
    """The state the phase wrote to is the production one."""

    async def test_coverage_entry_names_the_same_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _PROMPTS.clear()
        _wire_loopback(monkeypatch)
        state = _state()
        await ic._invoke_stakes_extractor(
            "unused when the state carries raw_text", {"_state_object": state}
        )
        assert (
            "stakes" in state.analysis_coverage
        ), "no stakes coverage entry — the phase did not write to this state"


class TestMutationControl:
    """The state dropped from the selected_text call, the entry disappears."""

    async def test_state_dropped_goes_red(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import argumentation_analysis.agents.core.political.stakes_extractor as se

        real = se.selected_text

        def _stateless(text: str, window: int, site: str, state: Any = None) -> str:
            return real(text, window, site)

        monkeypatch.setattr(se, "selected_text", _stateless)
        _PROMPTS.clear()
        _wire_loopback(monkeypatch)
        state = _state()
        await ic._invoke_stakes_extractor(
            "unused when the state carries raw_text", {"_state_object": state}
        )
        assert "stakes_extractor" not in state.reading_window_status, (
            "the entry survived the mutation — the witness does not depend "
            "on the state being passed"
        )
