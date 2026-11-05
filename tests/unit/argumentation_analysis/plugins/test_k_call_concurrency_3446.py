"""#3446 — the k reading calls fly concurrently under ONE named bound.

Cycle 2 measured the cost of flying them sequentially: a 179k-char document
is 30 extraction + 30 wide-net calls wall-to-wall, and #3435 measured ONE
stalled call freezing a whole phase (the budget and the client's retries
never composed). This file pins the three properties the dispatch asks:

1. WALL: k sleeping calls answer in ~ceil(k/bound) call durations, not k —
   through each real site (fact extraction, wide net, one-shot), not just
   the helper;
2. PLAN ORDER: answers merge in the order of the PLAN, whatever order the
   calls complete in — cross-window dedup, first-quote-wins and the first
   non-empty summary read the same sequence the sequential loop read;
3. ANSWERED ONLY (item 2): the one-shot's ``chars_read`` counts the chunks
   that ANSWERED, like the wide net — a chunk whose call failed read
   nothing.

The bound itself is ONE name beside ``WHOLE_TEXT_CALL_CAPACITY``
(``K_CALL_CONCURRENCY``): a gather without a bound would move the stall from
"one phase" to "the provider's rate limiter", which is not a repair.

Every failing/branching fake is keyed on CHUNK CONTENT (a unique spliced
marker), never on call count — retries would blur a counter (#2850 lot 10's
lesson, R1312).

Item 3 of the issue (the wide-net cap of 20 favouring the opening) is
deliberately NOT coded here: the coordinator measures it on the cycle-3
states.

Synthetic opaque text only; sleeping fakes, no network, no key.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
import unittest.mock as um
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from semantic_kernel.contents import AuthorRole
from semantic_kernel.kernel import Kernel

from argumentation_analysis.core import reading_window
from argumentation_analysis.core.reading_window import WHOLE_TEXT_CALL_CAPACITY
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)

INVOKE = "argumentation_analysis.orchestration.invoke_callables"

_PROSE = "une affirmation, une autre; voici une clause, encore une, et voici. "
#: Unique markers spliced into the synthetic docs: the prose repeats with a
#: ~67-char period, so a raw substring appears in EVERY chunk — only a
#: spliced token keys one chunk.
_HEAD_MARKER = "MARQUETETE0"
_MID_MARKER = "MARQUEMILIEU3"
_MARKERS = {_HEAD_MARKER: 0, _MID_MARKER: -1}

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


def _doc(chars: int, markers: Dict[str, int] | None = None) -> str:
    """Repetitive prose of the exact length, unique markers spliced in.

    ``markers`` maps marker -> offset (negative counts from the end, only
    for -1: the last capacity-chunk). The length never changes.
    """
    text = (_PROSE * (chars // len(_PROSE) + 1))[:chars]
    for marker, at in (markers or {}).items():
        pos = chars + at if at < 0 else at
        text = text[:pos] + marker + text[pos + len(marker) :]
    assert len(text) == chars
    return text


class _RecordingState:
    """Same mirror as the lot-7 file — the real record entry shape."""

    def __init__(self):
        self.reading_window_status = {}

    def record_reading_window(self, site, selection, extra=None):
        entry = {
            "status": getattr(selection, "status", str(selection)),
            "offset": getattr(selection, "offset", 0),
            "window": getattr(selection, "window", 0),
        }
        if extra:
            entry.update(extra)
        self.reading_window_status[site] = entry


def _plugin(state=None, service=None):
    return FallacyWorkflowPlugin(
        master_kernel=um.create_autospec(Kernel, instance=True),
        llm_service=service or um.AsyncMock(),
        taxonomy_data=_TAXONOMY,
        reading_state=state,
    )


def _users_prompt(chat_history) -> str:
    return "\n<<MSG>>\n".join(
        str(m.content)
        for m in (chat_history.messages or [])
        if getattr(m, "role", None) == AuthorRole.USER
    )


# ---------------------------------------------------------------------------
# The helper itself: bound honoured, plan order kept, bad bounds loud.
# ---------------------------------------------------------------------------


class TestTheHelper:
    """The helper is NEW API (#3446): on the pre-fix tree these redden at
    the lazy import — clean failures, not a collection error that would
    take the SITE witnesses down with them (same discipline as the lot-9
    file: a collection error proves no behaviour)."""

    @staticmethod
    def _helper():
        from argumentation_analysis.core.reading_window import (
            K_CALL_CONCURRENCY,
            gather_k_calls,
        )

        return gather_k_calls, K_CALL_CONCURRENCY

    async def test_results_come_back_in_plan_order_not_completion_order(self):
        """The last call completes FIRST; the list must still read plan
        order — every merge downstream reads that order."""

        async def _call(i: int) -> int:
            await asyncio.sleep((5 - i) * 0.01)
            return i

        gather_k_calls, _ = self._helper()
        out = await gather_k_calls([_call(i) for i in range(5)])
        assert out == [0, 1, 2, 3, 4]

    async def test_the_bound_is_honoured_not_ignored(self):
        """bound=1 serialises (wall ~ k durations); bound=k overlaps (wall ~
        1 duration). Both through the SAME helper — the semaphore is the
        mechanism, not decoration."""
        k, sleep = 6, 0.05

        async def _call(i: int) -> int:
            await asyncio.sleep(sleep)
            return i

        gather_k_calls, _ = self._helper()
        t0 = time.monotonic()
        await gather_k_calls([_call(i) for i in range(k)], bound=1)
        serialised = time.monotonic() - t0
        assert (
            serialised >= k * sleep * 0.8
        ), f"bound=1 must serialise (~{k * sleep:.2f}s), measured {serialised:.2f}s"

        t0 = time.monotonic()
        await gather_k_calls([_call(i) for i in range(k)], bound=k)
        overlapped = time.monotonic() - t0
        assert (
            overlapped < k * sleep * 0.6
        ), f"bound={k} must overlap (~{sleep:.2f}s), measured {overlapped:.2f}s"

    async def test_a_non_positive_bound_fails_loud_and_empty_is_empty(self):
        for bad in (0, -3):
            gather_k_calls, _ = self._helper()
            with pytest.raises(ValueError):
                await gather_k_calls([], bound=bad)
        gather_k_calls, _ = self._helper()
        assert await gather_k_calls([]) == []

    async def test_the_default_bound_is_the_named_constant_at_call_time(self):
        """The default reads ``K_CALL_CONCURRENCY`` at CALL time — a
        monkeypatched knob is honoured (a def-time default would freeze the
        first value it saw, and the knob would be dead)."""
        gather_k_calls, K_CALL_CONCURRENCY = self._helper()
        assert K_CALL_CONCURRENCY >= 1
        k, sleep = 3, 0.03

        async def _call(i: int) -> int:
            await asyncio.sleep(sleep)
            return i

        with um.patch.object(reading_window, "K_CALL_CONCURRENCY", 1):
            t0 = time.monotonic()
            await gather_k_calls([_call(i) for i in range(k)])
            wall = time.monotonic() - t0
        assert wall >= k * sleep * 0.8, (
            f"the patched bound=1 must serialise (~{k * sleep:.2f}s), "
            f"measured {wall:.2f}s — the default ignored the knob"
        )


# ---------------------------------------------------------------------------
# Site 1 — fact extraction: wall + plan-order merge (dedup, first summary).
# ---------------------------------------------------------------------------


class TestExtractionFliesConcurrently:
    def _run(self, doc: str, state: Any, fake: Any) -> Dict[str, Any]:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fact_extraction,
        )

        with um.patch(
            f"{INVOKE}._get_openai_client",
            return_value=(um.MagicMock(), "gpt-witness"),
        ), um.patch(
            f"{INVOKE}._guarded_chat_completion", um.AsyncMock(side_effect=fake)
        ):
            return asyncio.run(_invoke_fact_extraction(doc, {"_state_object": state}))

    @staticmethod
    def _resp(payload: Dict[str, Any]) -> SimpleNamespace:
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))
            ]
        )

    def test_k_sleeping_calls_answer_in_ceil_k_over_bound_waves(self):
        """Born red on the sequential loop: k = 10 windows of 50 ms each
        took ~500 ms wall; under the bound they take ~3 waves. The 0.6 x
        floor margin leaves room for a noisy timer while staying
        unreachable for a sequential loop."""
        k = math.ceil(60_000 / WHOLE_TEXT_CALL_CAPACITY)
        assert k == 10
        sleep = 0.05
        doc = _doc(60_000)

        async def _fake(
            _client: Any, model: Any = None, messages: Any = None, **kw: Any
        ):
            await asyncio.sleep(sleep)
            return self._resp({"arguments": [], "claims": [], "summary": "s"})

        t0 = time.monotonic()
        out = self._run(doc, UnifiedAnalysisState(doc), _fake)
        wall = time.monotonic() - t0
        assert out["extraction_status"] == "ok"
        floor = k * sleep
        # 0.8, not 0.6: sleeps only overshoot, never undershoot, so the
        # sequential floor (0.50s+, measured 0.69s on the pre-fix tree)
        # stays well above the threshold while 2-3 overlapped waves keep
        # 2x headroom on a loaded box.
        assert wall < floor * 0.8, (
            f"{k} calls of {sleep}s each must overlap under the bound "
            f"(sequential floor {floor:.2f}s), measured {wall:.2f}s wall — "
            "the extraction windows still fly sequentially (#3446)"
        )

    def test_the_merge_reads_plan_order_when_completion_order_reverses(self):
        """Every window reports the SAME argument; the FIRST window's call
        completes LAST (it sleeps). The merge must still dedup across
        windows and keep the FIRST window's summary — the exact byte
        sequence a sequential loop produced."""
        length = WHOLE_TEXT_CALL_CAPACITY * 2 + 500
        doc = _doc(length, {_HEAD_MARKER: 0})
        assert math.ceil(length / WHOLE_TEXT_CALL_CAPACITY) == 3

        async def _fake(
            _client: Any, model: Any = None, messages: Any = None, **kw: Any
        ):
            user = messages[-1]["content"]
            shared = {
                "arguments": [{"text": "unite partagee", "source_quote": "q"}],
                "claims": [],
            }
            if _HEAD_MARKER in user:
                await asyncio.sleep(0.12)  # plan order 0 — completes LAST
                return self._resp({**shared, "summary": "premiere"})
            return self._resp({**shared, "summary": "derniere"})

        out = self._run(doc, UnifiedAnalysisState(doc), _fake)
        texts = [a["text"] for a in out["arguments"]]
        assert texts == ["unite partagee"], (
            "the shared unit must appear ONCE (cross-window dedup) whatever "
            f"order the windows completed in — got {texts}"
        )
        assert out["summary"] == "premiere", (
            "the FIRST window's summary wins even when its call completes "
            f"last — got {out['summary']!r}"
        )
        assert out["reading_window_chars"] == length, "all windows answered"


# ---------------------------------------------------------------------------
# Site 2 — wide net: wall + first-quote-wins under reversed completion.
# ---------------------------------------------------------------------------


class _WideNetService:
    """Answers a wide-net prompt; the delay can depend on the chunk (the
    chunk carrying ``slow_marker`` sleeps longest, completing last)."""

    #: SK's Kernel.add_service reads this; an AsyncMock fakes it for free,
    #: a plain class must carry it.
    service_id = "witness-widenet"

    def __init__(
        self, base_delay: float, slow_marker: str, slow_delay: float, quotes: List[str]
    ):
        self._base_delay = base_delay
        self._slow_marker = slow_marker
        self._slow_delay = slow_delay
        self._quotes = quotes
        self.prompts: List[str] = []

    async def get_chat_message_content(
        self, chat_history=None, settings=None, kernel=None, **kw
    ):
        prompt = _users_prompt(chat_history)
        self.prompts.append(prompt)
        if self._slow_marker in prompt:
            await asyncio.sleep(self._slow_delay)
            quote = self._quotes[0]
        else:
            await asyncio.sleep(self._base_delay)
            quote = self._quotes[-1]
        return json.dumps(
            [
                {
                    "fallacy_name": "Ad Hominem",
                    "root_category": "",
                    "quote": quote,
                    "confidence": 0.5,
                }
            ]
        )


class TestWideNetFliesConcurrently:
    async def test_k_sleeping_chunks_answer_in_one_wave(self):
        """Born red on the sequential loop: 3 chunks of 50 ms cost ~150 ms
        serially; concurrently (bound >= 3) they answer in one ~50 ms
        wave."""
        length = WHOLE_TEXT_CALL_CAPACITY * 2 + 100
        text = _doc(length)
        assert math.ceil(length / WHOLE_TEXT_CALL_CAPACITY) == 3
        service = _WideNetService(0.05, "\x00never", 0.05, ["Q", "Q"])
        plugin = _plugin(state=_RecordingState(), service=service)
        t0 = time.monotonic()
        candidates = await plugin._wide_net_candidates(text)
        wall = time.monotonic() - t0
        assert candidates == ["11"]
        floor = 3 * 0.05
        assert wall < floor * 0.7, (
            f"3 chunks of 50 ms must overlap (sequential floor {floor:.2f}s), "
            f"measured {wall:.2f}s wall — the wide net still flies "
            "sequentially (#3446)"
        )
        assert len(service.prompts) == 3

    async def test_first_quote_wins_means_first_chunk_not_first_answered(self):
        """Plan order under reversed completion: chunk 0 (marker) sleeps
        120 ms, chunk 1 answers in 5 ms — chunk 1's answer is processed
        FIRST by the event loop, yet the shared PK's evidence must be
        chunk 0's quote. A merge keyed on completion order would record
        "SECOND"."""
        length = WHOLE_TEXT_CALL_CAPACITY + 100
        text = _doc(length, {_HEAD_MARKER: 0})
        assert math.ceil(length / WHOLE_TEXT_CALL_CAPACITY) == 2
        service = _WideNetService(0.005, _HEAD_MARKER, 0.12, ["PREMIER", "SECOND"])
        plugin = _plugin(state=_RecordingState(), service=service)
        candidates = await plugin._wide_net_candidates(text)
        assert candidates == ["11"]
        assert plugin._wide_net_quotes.get("11") == "PREMIER", (
            "first-quote-wins means the FIRST CHUNK's quote, whatever order "
            "the calls completed in — got "
            f"{plugin._wide_net_quotes.get('11')!r}"
        )


# ---------------------------------------------------------------------------
# Site 3 — one-shot: wall + item 2 (chars_read counts ANSWERED chunks only).
# ---------------------------------------------------------------------------


class _OneShotService:
    """Answers one-shot calls; the chunk carrying ``fail_marker`` raises
    (the synthetic #3435 stall), the others answer a valid detection."""

    service_id = "witness-one-shot"

    def __init__(self, fail_marker: str = "\x00never", delay: float = 0.0):
        self._fail_marker = fail_marker
        self._delay = delay
        self.prompts: List[str] = []

    async def get_chat_message_content(
        self, chat_history=None, settings=None, kernel=None, **kw
    ):
        prompt = _users_prompt(chat_history)
        self.prompts.append(prompt)
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._fail_marker in prompt:
            raise RuntimeError("stalled chunk — synthetic #3435 stall")
        return json.dumps(
            {
                "fallacy_name": "Ad Hominem",
                "taxonomy_pk": "11",
                "explanation": "synthetic",
                "confidence": 0.5,
            }
        )


def _one_shot_plugin(state, service):
    plugin = _plugin(state=state, service=service)
    plugin._create_one_shot_kernel = lambda: (um.MagicMock(), um.MagicMock())
    return plugin


class TestOneShotFliesConcurrently:
    async def test_k_sleeping_chunks_answer_in_one_wave(self):
        k = 4
        length = WHOLE_TEXT_CALL_CAPACITY * (k - 1) + 100
        text = _doc(length)
        assert math.ceil(length / WHOLE_TEXT_CALL_CAPACITY) == k
        service = _OneShotService(delay=0.05)
        plugin = _one_shot_plugin(_RecordingState(), service)
        t0 = time.monotonic()
        result = await plugin._run_one_shot(text)
        wall = time.monotonic() - t0
        parsed = json.loads(result)
        assert parsed.get("exploration_method") == "one_shot"
        floor = k * 0.05
        assert wall < floor * 0.6, (
            f"{k} chunks of 50 ms must overlap under the bound (sequential "
            f"floor {floor:.2f}s), measured {wall:.2f}s wall — the one-shot "
            "still flies sequentially (#3446)"
        )

    async def test_a_failed_chunk_is_not_counted_as_read(self):
        """Item 2, born red: the record used to sum the PLANNED chunks
        before any call answered. Three chunks, the MIDDLE one's call fails
        (keyed on its content, not its position in the call list):
        chars_read must say the two ANSWERED chunks' lengths, never three
        capacities' worth."""
        k = 3
        length = WHOLE_TEXT_CALL_CAPACITY * (k - 1) + 100
        # The marker sits 50 chars into the middle chunk — only that chunk
        # carries it (the prose repeats, the spliced token does not).
        text = _doc(length, {_MID_MARKER: WHOLE_TEXT_CALL_CAPACITY + 50})
        assert math.ceil(length / WHOLE_TEXT_CALL_CAPACITY) == k
        assert _MID_MARKER not in text[:WHOLE_TEXT_CALL_CAPACITY]
        state = _RecordingState()
        service = _OneShotService(fail_marker=_MID_MARKER)
        plugin = _one_shot_plugin(state, service)
        result = await plugin._run_one_shot(text)
        entry = state.reading_window_status["fallacy_one_shot"]
        assert entry["chunks"] == k, "the plan still names the k chunks asked"
        _answered_expected = WHOLE_TEXT_CALL_CAPACITY + (
            length - 2 * WHOLE_TEXT_CALL_CAPACITY
        )
        assert entry["chars_read"] == _answered_expected, (
            "only the chunks that ANSWERED were read — the failed middle "
            f"chunk read nothing, expected {_answered_expected} "
            f"(first + tail), got {entry['chars_read']} for {k} planned "
            f"chunks of {WHOLE_TEXT_CALL_CAPACITY}"
        )
        # The run still answers: the two answered chunks pool a detection.
        parsed = json.loads(result)
        assert parsed.get("exploration_method") == "one_shot"
        assert len(parsed.get("fallacies") or []) >= 1

    async def test_all_chunks_answering_keeps_the_whole_document_read(self):
        """Control: no failure — chars_read is the whole document, exactly
        the lot-10 record (the answered-only rule must not undercount a
        healthy run)."""
        length = WHOLE_TEXT_CALL_CAPACITY * 2 + 100
        text = _doc(length)
        state = _RecordingState()
        plugin = _one_shot_plugin(state, _OneShotService())
        await plugin._run_one_shot(text)
        entry = state.reading_window_status["fallacy_one_shot"]
        assert entry["chars_read"] == length, (
            "a fully answered plan reads the whole document — "
            f"got {entry['chars_read']} of {length}"
        )
