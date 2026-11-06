"""#3446 item 3 — the wide-net record names what the cap dropped, and
exists when the descent expires.

Cycle 3 measured the hole: on the longest panel document the wide-net
descent hit its 300 s cap (#1087) and fell back to per-argument — and NO
``fallacy_widenet`` record exists for that document, because the cap
cancels the whole coroutine while the k chunk calls are still in flight,
before the record at the end of phase 1. The record also says nothing
about the pool cap: ``MAX_CANDIDATES`` (20) silently drops every PK beyond
it, so « the cap favours the opening » could not even be asked.

This file pins the two sides of the repair (the ceiling itself does NOT
move — the anti-pendulum rule of the issue):

1. the record carries ``pool_before_cap`` (distinct PKs pooled across the
   ANSWERED chunks) and, when the cap bit, ``dropped_by_cap`` — each
   dropped PK with the chunk index it first appeared in (plan order,
   0-based);
2. a cancelled phase-1 still records: over the chunks that ANSWERED before
   the cap, with ``expired: True`` — the cancellation then travels
   untouched (the caller's per-argument fallback answers next).

Born red on ``6690030ee``: the cap fields are absent from the record
(KeyError), and the expiry path leaves ``reading_window_status`` empty.

Synthetic opaque text, sleeping fakes, no network, no key. Every
branching fake is keyed on CHUNK CONTENT (a spliced marker), never on call
count — a counter blurs under retries (R1312).
"""

from __future__ import annotations

import asyncio
import json
import unittest.mock as um
from typing import Any, Dict, List, Optional

import pytest
from semantic_kernel.contents import AuthorRole
from semantic_kernel.kernel import Kernel

from argumentation_analysis.core.reading_window import WHOLE_TEXT_CALL_CAPACITY
from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)

_PROSE = "une affirmation, une autre; voici une clause, encore une, et voici. "
#: Unique markers spliced into the synthetic docs: the prose repeats with a
#: ~67-char period, so a raw substring appears in EVERY chunk — only a
#: spliced token keys one chunk.
_HEAD_MARKER = "MARQUETETE0"
_QUEUE_MARKER = "MARQUEQUEUE7"


def _root(i: int) -> Dict[str, str]:
    """One taxonomy root with a fixed-width, unique, non-colliding name.

    Equal-length labels cannot substring-match each other (a substring of
    an equal-length string IS that string), so the deep-index mapping is
    exact — 26 replies map to 26 distinct PKs.
    """
    label = f"Témoin muet {i:02d}"
    return {
        "PK": f"T{i:02d}",
        "path": f"{i + 1}",
        "depth": "1",
        "text_fr": label,
        "text_en": label,
        "desc_fr": label,
        "desc_en": label,
        "example_fr": "",
        "example_en": "",
        "nom_vulgarisé": label,
    }


_TAXONOMY = [_root(i) for i in range(26)]


def _doc(chars: int, markers: Dict[str, int]) -> str:
    """Repetitive prose of the exact length, unique markers spliced in.

    ``markers`` maps marker -> offset; ``-1`` anchors the marker flush
    against the END of the doc (it replaces the last ``len(marker)``
    characters — splicing at ``chars - 1`` would GROW the text). The
    length never changes.
    """
    text = (_PROSE * (chars // len(_PROSE) + 1))[:chars]
    for marker, at in markers.items():
        pos = chars - len(marker) if at < 0 else at
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


class _ChunkedService:
    """Answers each chunk from its spliced marker; can hang one chunk.

    The hang is the #1087 descent cap seen from inside: the outer
    ``wait_for`` cancels the whole phase while this call sleeps.
    """

    service_id = "witness-widenet-cap"

    def __init__(
        self,
        by_marker: Dict[str, List[str]],
        hang_marker: Optional[str] = None,
        hang_seconds: float = 30.0,
    ):
        self._by_marker = by_marker
        self._hang_marker = hang_marker
        self._hang_seconds = hang_seconds
        self.prompts: List[str] = []

    async def get_chat_message_content(
        self, chat_history=None, settings=None, kernel=None, **kw
    ):
        prompt = _users_prompt(chat_history)
        self.prompts.append(prompt)
        if self._hang_marker and self._hang_marker in prompt:
            await asyncio.sleep(self._hang_seconds)
        for marker, names in self._by_marker.items():
            if marker in prompt:
                return json.dumps(
                    [
                        {
                            "fallacy_name": name,
                            "root_category": name,
                            "confidence": 0.5,
                            "quote": f"citation verbatim du témoin {name}.",
                        }
                        for name in names
                    ]
                )
        return "[]"


def _plugin(state, service) -> FallacyWorkflowPlugin:
    return FallacyWorkflowPlugin(
        master_kernel=um.create_autospec(Kernel, instance=True),
        llm_service=service,
        taxonomy_data=_TAXONOMY,
        reading_state=state,
    )


def _users_prompt(chat_history) -> str:
    return "\n<<MSG>>\n".join(
        str(m.content)
        for m in (chat_history.messages or [])
        if getattr(m, "role", None) == AuthorRole.USER
    )


def _names(*indices: int) -> List[str]:
    return [f"Témoin muet {i:02d}" for i in indices]


class TestTheCapRecord:
    """The record names what the cap dropped — born red on ``6690030ee``:
    the entry carries neither ``pool_before_cap`` nor ``dropped_by_cap``."""

    async def test_the_record_names_what_the_cap_dropped(self):
        """Chunk 0 lists T00..T24 (25 PKs), chunk 1 lists T20..T25 — the
        pool holds 26 distinct PKs, the cap keeps the first 20 in plan
        order, and the record must SAY the six it dropped, with the chunk
        each first appeared in."""
        length = WHOLE_TEXT_CALL_CAPACITY + 100
        text = _doc(length, {_HEAD_MARKER: 0, _QUEUE_MARKER: -1})
        service = _ChunkedService(
            {
                _HEAD_MARKER: _names(*range(25)),
                _QUEUE_MARKER: _names(*range(20, 26)),
            }
        )
        state = _RecordingState()
        plugin = _plugin(state, service)

        await plugin._wide_net_candidates(text)

        entry = state.reading_window_status["fallacy_widenet"]
        assert entry["pool_before_cap"] == 26, (
            "26 distinct PKs were pooled across the answered chunks — the "
            f"record must say it, got {entry.get('pool_before_cap')!r}"
        )
        expected_dropped = {f"T{i:02d}": 0 for i in range(20, 25)}
        expected_dropped["T25"] = 1
        assert entry["dropped_by_cap"] == expected_dropped, (
            "the cap dropped T20..T24 (first seen in chunk 0) and T25 "
            f"(first seen in chunk 1), got {entry.get('dropped_by_cap')!r}"
        )
        assert entry["chunks"] == 2
        assert entry["chars_read"] == length

    async def test_the_cap_did_not_move(self):
        """Anti-pendulum pin: the repair must not raise the ceiling to
        make the drop disappear. The pool of 26 still returns the first
        20, in plan order."""
        assert FallacyWorkflowPlugin.MAX_CANDIDATES == 20
        length = WHOLE_TEXT_CALL_CAPACITY + 100
        text = _doc(length, {_HEAD_MARKER: 0, _QUEUE_MARKER: -1})
        service = _ChunkedService(
            {
                _HEAD_MARKER: _names(*range(25)),
                _QUEUE_MARKER: _names(*range(20, 26)),
            }
        )
        plugin = _plugin(_RecordingState(), service)

        candidates = await plugin._wide_net_candidates(text)

        assert candidates == [f"T{i:02d}" for i in range(20)], (
            "the cap still keeps the FIRST 20 PKs in plan order — raising "
            "it is the pendulum this issue forbids"
        )

    async def test_a_pool_under_the_cap_names_no_drop(self):
        """The honest absent case: nothing dropped means no
        ``dropped_by_cap`` key, and no ``expired`` — but the pool size is
        still said (it is what the cap is compared against)."""
        length = WHOLE_TEXT_CALL_CAPACITY + 100
        text = _doc(length, {_HEAD_MARKER: 0, _QUEUE_MARKER: -1})
        service = _ChunkedService(
            {_HEAD_MARKER: _names(0, 1), _QUEUE_MARKER: _names(1, 2)}
        )
        state = _RecordingState()
        plugin = _plugin(state, service)

        candidates = await plugin._wide_net_candidates(text)

        assert candidates == ["T00", "T01", "T02"]
        entry = state.reading_window_status["fallacy_widenet"]
        assert entry["pool_before_cap"] == 3
        assert "dropped_by_cap" not in entry
        assert "expired" not in entry


class TestTheExpiredDescent:
    """A cancelled phase-1 still records — born red on ``6690030ee``: the
    cap cancels the coroutine before its record, and the state's table
    stays empty for that document."""

    async def test_the_record_exists_when_the_descent_expires(self):
        """The #1087 300 s cap seen from inside: chunk 0 answers three
        PKs, chunk 1 hangs — the cancellation (here ``wait_for``) must
        still leave a record over the ANSWERED chunk, marked expired, and
        the cancellation must travel (TimeoutError reaches the caller)."""
        length = WHOLE_TEXT_CALL_CAPACITY + 100
        text = _doc(length, {_HEAD_MARKER: 0, _QUEUE_MARKER: -1})
        service = _ChunkedService(
            {_HEAD_MARKER: _names(0, 1, 2)}, hang_marker=_QUEUE_MARKER
        )
        state = _RecordingState()
        plugin = _plugin(state, service)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(plugin._wide_net_candidates(text), timeout=0.4)

        entry = state.reading_window_status["fallacy_widenet"]
        assert entry["expired"] is True, (
            "the phase was cancelled mid-flight — the record must say so, "
            f"got {entry!r}"
        )
        assert entry["chunks"] == 2, "2 chunks were asked"
        assert (
            entry["chars_read"] == WHOLE_TEXT_CALL_CAPACITY
        ), "only the ANSWERED chunk's span counts as read"
        assert (
            entry["pool_before_cap"] == 3
        ), "the pool is computed over the answered chunks"
        assert "dropped_by_cap" not in entry

    async def test_the_expired_path_writes_no_quote_evidence(self):
        """The expired gesture is the record, nothing else: no candidate
        quote is installed (the phase never returned), the plugin instance
        holds no evidence from a cancelled pass."""
        length = WHOLE_TEXT_CALL_CAPACITY + 100
        text = _doc(length, {_HEAD_MARKER: 0, _QUEUE_MARKER: -1})
        service = _ChunkedService(
            {_HEAD_MARKER: _names(0, 1, 2)}, hang_marker=_QUEUE_MARKER
        )
        plugin = _plugin(_RecordingState(), service)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(plugin._wide_net_candidates(text), timeout=0.4)

        assert plugin._wide_net_quotes == {}


class TestTheSingleChunkShape:
    """Companions green before AND after the repair: the single-chunk
    record keeps today's exact shape (no extra keys) — the repair must not
    grow the record where the cap never had meaning."""

    async def test_a_single_chunk_document_records_no_extra(self):
        text = _doc(WHOLE_TEXT_CALL_CAPACITY - 100, {_HEAD_MARKER: 0})
        service = _ChunkedService({_HEAD_MARKER: _names(0, 1)})
        state = _RecordingState()
        plugin = _plugin(state, service)

        await plugin._wide_net_candidates(text)

        entry = state.reading_window_status["fallacy_widenet"]
        assert set(entry) == {"status", "offset", "window"}, (
            "one chunk, no drop: the entry stays byte-identical to today — "
            f"got {sorted(entry)}"
        )
