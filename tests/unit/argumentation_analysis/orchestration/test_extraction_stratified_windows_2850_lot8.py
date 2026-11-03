"""#2850 lot 8 — the LLM extraction window itself reads every third.

The audit's headline defect: doc_A reads 5 643 of 56 430 chars, and all 5
LLM units came from tier 1 (offsets 1479-2872, all < 3000) — the extraction
window ``[:3000]`` never let the LLM SEE tiers 2-3, so whatever it found was
an opening-sample, quoted downstream as the analysis. Lot 8 stratifies the
read: k = min(3, ceil(L / 3000)) windows, the FIRST still the #1737
selector's (a TOC head is skipped, not re-read raw), the tails at fixed
offsets — never one wider call (#2912 is that defect, named excluded).

These witnesses are born red on the pre-lot-8 tree: one window meant one
call, one tier, and a ``reading_window_chars`` of exactly 3 000. The mock
pair (``_get_openai_client`` + ``_guarded_chat_completion``) keeps every run
hermetic — zero network (#3072). The fake is FAITHFUL per window: it answers
exactly the markers present in the window content it received, so a run that
never reads a tier cannot report its unit (the population witness can only
pass if the window really carried the marker).
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.core.reading_window import (
    LLM_EXTRACTION_WINDOW,
    stratified_window_offsets,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState

INVOKE = "argumentation_analysis.orchestration.invoke_callables"

# Three markers, one per third, spliced INSIDE the k=3 windows of a
# 60 000-char document (offsets 0 / 28 500 / 57 000 → windows [0-3000],
# [28500-31500], [57000-60000]): 1 000, 29 500 and 58 500 all sit inside.
_DOC_LEN = 60000
M1, M2, M3 = "MARQUEUN", "MARQUEDEUX", "MARQUETROIS"
_MARKERS = {M1: 1000, M2: 29500, M3: 58500}

assert stratified_window_offsets(_DOC_LEN, LLM_EXTRACTION_WINDOW) == [
    0,
    (_DOC_LEN - LLM_EXTRACTION_WINDOW) // 2,
    _DOC_LEN - LLM_EXTRACTION_WINDOW,
], "the witness' window arithmetic must hold before the run"


def _synthetic_doc(length: int = _DOC_LEN) -> str:
    """``mot `` repeated to the exact length, markers spliced in place.

    Splicing (not inserting) keeps the length exact, so the offsets asserted
    above are the offsets the run computes."""
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


def _faithful_fake(calls: List[str]):
    """Answer the markers present in the window content received — never more.

    A window that carries no marker gets an EMPTY extraction: the population
    witness then fails, which is the point — the tier really has to be read."""

    def _fake(_client: Any, model: Any = None, messages: Any = None, **kw: Any):
        user = messages[-1]["content"]
        calls.append(user)
        found = [m for m in (M1, M2, M3) if m in user]
        return _resp(
            {
                "arguments": [
                    {"text": f"unité de {m}", "source_quote": m} for m in found
                ],
                "claims": [],
                "summary": "synthèse",
            }
        )

    return _fake


def _run(text: str, state: Any) -> tuple[Dict[str, Any], List[str]]:
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_fact_extraction,
    )

    calls: List[str] = []
    with patch(
        f"{INVOKE}._get_openai_client", return_value=(MagicMock(), "gpt-witness")
    ), patch(
        f"{INVOKE}._guarded_chat_completion",
        AsyncMock(side_effect=_faithful_fake(calls)),
    ):
        out = asyncio.run(_invoke_fact_extraction(text, {"_state_object": state}))
    return out, calls


class TestStratifiedWindows:
    """k windows, one LLM call each, the union disclosed in counts."""

    def test_three_distinct_windows_cover_every_third(self) -> None:
        doc = _synthetic_doc()
        out, calls = _run(doc, UnifiedAnalysisState(doc))
        assert len(calls) == 3, (
            f"a {len(doc)}-char document must be read by k = min(3, "
            f"ceil(L/3000)) = 3 windows, one LLM call each — got {len(calls)}"
        )
        assert all(len(c) <= LLM_EXTRACTION_WINDOW for c in calls)
        assert len(set(calls)) == 3, "the three windows must be three distinct reads"
        # Each marker was SEEN by exactly the window that carries it.
        assert sum(M1 in c for c in calls) == 1
        assert sum(M2 in c for c in calls) == 1
        assert sum(M3 in c for c in calls) == 1

    def test_llm_population_reaches_every_third(self) -> None:
        """The DoD bar: ≥ 1 LLM unit per third, from the extraction itself
        (not the heuristic population that already spans the text)."""
        doc = _synthetic_doc()
        out, _ = _run(doc, UnifiedAnalysisState(doc))
        quotes = {a["source_quote"] for a in out["arguments"]}
        assert {M1, M2, M3} <= quotes, (
            "every third the windows read must contribute at least one unit "
            f"to the merged LLM population — got {sorted(quotes)}"
        )

    def test_payload_and_record_carry_the_union_not_the_first_window(self) -> None:
        doc = _synthetic_doc()
        state = UnifiedAnalysisState(doc)
        out, _ = _run(doc, state)
        # Windows [0-3000], [28500-31500], [57000-60000]: disjoint spans,
        # union 9 000 — hand-derived, never the implementation's arithmetic.
        assert out["reading_window_chars"] == 3 * LLM_EXTRACTION_WINDOW
        entry = state.reading_window_status["fact_extraction"]
        assert entry["windows"] == 3, entry
        assert entry["chars_read"] == 3 * LLM_EXTRACTION_WINDOW, entry
        assert out["source_length"] == _DOC_LEN

    def test_a_failed_window_reads_nothing_and_says_so(self) -> None:
        """A window that answers no parseable JSON read NOTHING: the record
        and the payload count the windows that answered, and the union of
        THEIR spans only — a failed window's span would state a figure
        stronger than its measurement (#3099/#1019)."""

        def _fake(_client: Any, model: Any = None, messages: Any = None, **kw: Any):
            user = messages[-1]["content"]
            if M2 in user:  # the middle window answers garbage, three times
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(message=SimpleNamespace(content="garbage"))
                    ]
                )
            found = [m for m in (M1, M3) if m in user]
            return _resp(
                {
                    "arguments": [
                        {"text": f"unité de {m}", "source_quote": m} for m in found
                    ],
                    "claims": [],
                    "summary": "s",
                }
            )

        doc = _synthetic_doc()
        state = UnifiedAnalysisState(doc)
        with patch(
            f"{INVOKE}._get_openai_client", return_value=(MagicMock(), "gpt-witness")
        ), patch(f"{INVOKE}._guarded_chat_completion", AsyncMock(side_effect=_fake)):
            from argumentation_analysis.orchestration.invoke_callables import (
                _invoke_fact_extraction,
            )

            out = asyncio.run(_invoke_fact_extraction(doc, {"_state_object": state}))
        entry = state.reading_window_status["fact_extraction"]
        assert entry["windows"] == 2, (
            f"two windows answered — the record must count those, not the "
            f"plan: {entry}"
        )
        # Windows 1 and 3 answered: [0-3000] + [57000-60000] = 6 000 chars.
        assert entry["chars_read"] == 2 * LLM_EXTRACTION_WINDOW, entry
        assert out["reading_window_chars"] == 2 * LLM_EXTRACTION_WINDOW
        assert {M1, M3} <= {a["source_quote"] for a in out["arguments"]}
        assert M2 not in {a["source_quote"] for a in out["arguments"]}


class TestShortDocumentUnchanged:
    """The replay-band control: a document that fits one window keeps
    EXACTLY today's single call, byte-identical — a new cassette key would
    be a STOP per the DoD, not a repair."""

    def test_one_call_whole_document_byte_identical(self) -> None:
        doc = ("mot " * 375)[:1500]  # 1 500 chars, fits the window
        assert len(doc) == 1500
        calls: List[str] = []
        with patch(
            f"{INVOKE}._get_openai_client", return_value=(MagicMock(), "gpt-witness")
        ), patch(
            f"{INVOKE}._guarded_chat_completion",
            AsyncMock(side_effect=_faithful_fake(calls)),
        ):
            from argumentation_analysis.orchestration.invoke_callables import (
                _invoke_fact_extraction,
            )

            state = UnifiedAnalysisState(doc)
            out = asyncio.run(_invoke_fact_extraction(doc, {"_state_object": state}))
        assert len(calls) == 1, "a document within one window is ONE call, unchanged"
        assert calls[0] == doc, (
            "the single window must be the whole document, byte-identical to "
            "the pre-lot-8 request — the replay band's cassette keys"
        )
        assert out["reading_window_chars"] == len(doc)
        entry = state.reading_window_status["fact_extraction"]
        assert "windows" not in entry, (
            "a one-window read keeps today's entry untouched — no k-fields "
            f"on a record that never stratified: {entry}"
        )


class TestStratifiedOffsetsContract:
    """The pure plan: tiling below 3 × window, head/middle/end beyond."""

    def test_short_is_single_raw_offset(self) -> None:
        assert stratified_window_offsets(1500, 3000) == [0]

    def test_tiling_documents_leave_nothing_unread(self) -> None:
        # L ≤ k × window ⇒ the windows tile: the union covers [0, L).
        for length in (3001, 6000, 9000):
            offsets = stratified_window_offsets(length, 3000)
            covered = 0
            reach = -1
            for o in offsets:
                hi = min(o + 3000, length)
                covered += max(0, hi - max(o, reach))
                reach = max(reach, hi)
            assert covered == length, (
                f"below 3×window the plan must tile the whole document — "
                f"L={length}, offsets={offsets}, union={covered}"
            )

    def test_beyond_cap_samples_head_middle_end(self) -> None:
        offsets = stratified_window_offsets(56430, 3000)
        assert len(offsets) == 3
        assert offsets[0] == 0
        assert offsets[-1] == 56430 - 3000
        assert offsets[1] == (56430 - 3000) // 2
