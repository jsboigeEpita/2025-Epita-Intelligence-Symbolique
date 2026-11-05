"""#2850 lot 10 — the wiring: whole text read in k calls, on the real sites.

The mechanism is pinned in ``test_reading_window_lot10_2850.py``; this file
pins that the SITES use it, on synthetic opaque text:

- the wide net pools the candidates of every chunk — a candidate the LAST
  chunk carries is no longer lost (the opening-window defect), and the
  record says how many chunks carried the read;
- the personas read the document through the first reading's positions —
  the historian and the strategist see a passage located at 35k of a 40k
  document, and the recorded status says ``anchored_on_defining_moves``;
- without a usable position the opening window survives and the record
  says ``head_fallback_no_first_reading``.

No LLM, no network: the fakes are async doubles.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from semantic_kernel.kernel import Kernel
from unittest.mock import AsyncMock, create_autospec

from argumentation_analysis.agents.core.context.historian import (
    build_historical_context,
)
from argumentation_analysis.agents.core.context.strategist import (
    build_strategic_read,
)
from argumentation_analysis.core.reading_window import (
    STATUS_ANCHORED_ON_MOVES,
    STATUS_HEAD_FALLBACK_NO_MOVES,
    WHOLE_TEXT_CALL_CAPACITY,
)
from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)

_PROSE = "une phrase de contexte, avec des virgules; et une autre clause. "

_TAXONOMY = [
    {
        "PK": "10",
        "path": "2",
        "depth": "1",
        "text_fr": "Hors sujet",
        "text_en": "Irrelevance",
        "desc_fr": "Arguments sans rapport",
        "desc_en": "Unrelated arguments",
        "example_fr": "",
        "example_en": "",
        "nom_vulgarisé": "Hors sujet",
    },
    {
        "PK": "11",
        "path": "2.1",
        "depth": "2",
        "text_fr": "Ad Hominem",
        "text_en": "Ad Hominem",
        "desc_fr": "Attaque la personne",
        "desc_en": "Attacks the person",
        "example_fr": "",
        "example_en": "",
        "nom_vulgarisé": "Ad Hominem",
    },
]


def _text(chars: int) -> str:
    return (_PROSE * (chars // len(_PROSE) + 1))[:chars]


class _RecordingState:
    def __init__(self, **fields):
        self.reading_window_status = {}
        self.__dict__.update(fields)

    def record_reading_window(self, site, selection, extra=None):
        entry = {
            "status": getattr(selection, "status", str(selection)),
            "offset": getattr(selection, "offset", 0),
            "window": getattr(selection, "window", 0),
        }
        if extra:
            entry.update(extra)
        self.reading_window_status[site] = entry


class TestWideNetWholeText:
    async def test_the_last_chunk_candidate_is_pooled_and_recorded(self):
        """The opening-window defect: a candidate the tail carries used to be
        invisible (only ``[:8000]`` was read). The whole text is read now, and
        the pool must contain the tail's candidate."""
        tail = ("segment de queue unique, " * 5)[:120]
        text = _text(40_000 - len(tail)) + tail
        calls = {"n": 0}

        async def _reply(chat_history=None, settings=None, kernel=None, **kw):
            calls["n"] += 1
            if calls["n"] < 7:  # the last chunk only carries it
                return "[]"
            return json.dumps(
                [
                    {
                        "fallacy_name": "Hors sujet",
                        "root_category": "Hors sujet",
                        "confidence": 0.9,
                        "quote": tail,
                    }
                ]
            )

        state = _RecordingState()
        plugin = FallacyWorkflowPlugin(
            master_kernel=create_autospec(Kernel, instance=True),
            llm_service=AsyncMock(),
            taxonomy_data=_TAXONOMY,
            reading_state=state,
        )
        plugin.llm_service.get_chat_message_content = _reply

        candidates = await plugin._wide_net_candidates(text)

        assert calls["n"] == 7, "k = ceil(40000/6016) = 7"
        assert "10" in candidates, "the tail chunk's candidate is pooled"
        assert (
            plugin._wide_net_quotes["10"] == tail
        ), "the quote pooled is the tail's — the last chunk was really read"
        entry = state.reading_window_status["fallacy_widenet"]
        assert entry["chunks"] == 7
        assert entry["chars_read"] == 40_000
        assert entry["window"] == WHOLE_TEXT_CALL_CAPACITY

    async def test_a_failed_chunk_is_not_counted_as_read(self):
        """A call that failed read nothing: it must not pad the record's
        chars_read (the honest failure path of lot 8's fallback contract)."""
        text = _text(20_000)
        calls = {"n": 0}

        async def _reply(chat_history=None, settings=None, kernel=None, **kw):
            calls["n"] += 1
            if calls["n"] == 2:
                raise TimeoutError("provider stalled")
            return "[]"

        state = _RecordingState()
        plugin = FallacyWorkflowPlugin(
            master_kernel=create_autospec(Kernel, instance=True),
            llm_service=AsyncMock(),
            taxonomy_data=_TAXONOMY,
            reading_state=state,
        )
        plugin.llm_service.get_chat_message_content = _reply

        await plugin._wide_net_candidates(text)

        entry = state.reading_window_status["fallacy_widenet"]
        assert entry["chunks"] == 4
        assert entry["chars_read"] < 20_000, "the failed chunk is not counted as read"


class TestPersonasReadTheDocument:
    def _state(self, text, moves):
        return _RecordingState(
            raw_text=text,
            source_metadata={"speaker": "Speaker_A", "venue": "assembly"},
            stakes_and_stakeholders={"stakes": [], "stakeholders": []},
            defining_moves={
                "moves": moves,
                "dropped_quotes": 0,
                "status": "ok",
                "read_scope": {"whole_document": True},
                "basis": "first_reading",
            },
        )

    async def test_the_historian_reads_a_tail_position_not_the_opening(self):
        text = _text(40_000)
        moves = [
            {
                "kind": "thesis",
                "reading": "la thèse",
                "quote": text[100:120],
                "offset": 100,
            },
            {
                "kind": "device",
                "reading": "le mécanisme",
                "quote": text[35_000:35_030],
                "offset": 35_000,
            },
        ]
        state = self._state(text, moves)
        prompts = []

        async def _call(prompt: str) -> str:
            prompts.append(prompt)
            return json.dumps({"situation": "s", "items": []})

        await build_historical_context(state, llm_callable=_call)

        assert prompts, "the persona called the model"
        assert (
            text[35_000:35_030] in prompts[0]
        ), "the tail passage reaches the historian's prompt"
        entry = state.reading_window_status["historian"]
        assert entry["status"] == STATUS_ANCHORED_ON_MOVES
        assert entry["chars_read"] > 0

    async def test_the_strategist_reads_the_same_anchored_document(self):
        text = _text(40_000)
        moves = [
            {
                "kind": "device",
                "reading": "le mécanisme",
                "quote": text[35_000:35_030],
                "offset": 35_000,
            },
        ]
        state = self._state(text, moves)
        prompts = []

        async def _call(prompt: str) -> str:
            prompts.append(prompt)
            return "{}"

        await build_strategic_read(state, llm_callable=_call)

        assert prompts and text[35_000:35_030] in prompts[0]
        assert state.reading_window_status["strategist"]["status"] == (
            STATUS_ANCHORED_ON_MOVES
        )

    async def test_without_a_first_reading_the_opening_window_says_fallback(self):
        tail = ("marqueur de queue " * 8)[:140]
        text = _text(20_000 - len(tail)) + tail
        state = self._state(text, [])
        prompts = []

        async def _call(prompt: str) -> str:
            prompts.append(prompt)
            return json.dumps({"situation": "s", "items": []})

        await build_historical_context(state, llm_callable=_call)

        entry = state.reading_window_status["historian"]
        assert entry["status"] == STATUS_HEAD_FALLBACK_NO_MOVES
        assert text[:3000] in prompts[0], "the opening window is what survives"
        assert tail not in prompts[0], "the fallback reads the opening, not the tail"
