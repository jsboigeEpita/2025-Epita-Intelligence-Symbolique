"""#2850 lot 9 — a document that fits one call is read WHOLE, in one call.

Lot 8 spread the extraction over k = min(3, ceil(L/3000)) windows of 3 000
characters. Below 3 × window those windows TILE the document, so a 5 400-char
document was read twice to produce one stitched read — and beyond 9 000
characters the plan samples instead of reading.

Lot 9 replaces the band it can afford to: when the document fits ONE call's
completion budget, the extraction reads the document itself, once. The
k-window sample stays for everything beyond, untouched.

The capacity is not a taste: it comes from the two measurements lot 8 posted
(the completion shape of an extraction answer, and the peak density of the
units the 48 local states carry) plus the run's own completion cap. The
witnesses below pin the number TO those measurements, so a later change of
the cap or of the tokens-per-unit shows up here rather than as a truncated
answer in a paid pass.

Born red on the lot-8 tree: a 5 400-char document cost two calls, and the
record said ``windows: 2`` where it should say the document was read whole.
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
from argumentation_analysis.reporting.restitution.reading_record import (
    build_reading_record,
    format_reading_line,
)


def _lot9() -> Any:
    """The lot-9 names, imported where they are used.

    Kept out of the module header on purpose: on the pre-lot-9 tree the
    behavioural witnesses below then run and FAIL on their own measure
    (two calls where one was promised) instead of the whole file dying at
    collection — a collection error proves no behaviour, it only proves an
    import is missing.
    """
    from argumentation_analysis.core import reading_window

    return reading_window


INVOKE = "argumentation_analysis.orchestration.invoke_callables"

#: The run's own completion cap (``EXTRACTION_MAX_TOKENS`` default).
_CAP = 8192

#: The band lot 9 owns: longer than today's window, within one call.
_BAND_LEN = 5400
_BAND_MARKER_AT = 5300
END_MARKER = "MARQUEFIN"
MIDDLE_MARKER = "MARQUEMILIEU"
_MARKERS = {MIDDLE_MARKER: 4500, END_MARKER: _BAND_MARKER_AT}


def _doc(length: int) -> str:
    """``mot `` repeated to the exact length, markers spliced in place."""
    text = "mot " * (length // 4)
    text += "x" * (length - len(text))
    assert len(text) == length, len(text)
    for marker, at in _MARKERS.items():
        if at + len(marker) <= length:
            text = text[:at] + marker + text[at + len(marker) :]
    assert len(text) == length
    return text


def _resp(payload: Dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
    )


def _faithful_fake(calls: List[str]):
    """Answer exactly the markers the received window carries — never more."""

    def _fake(_client: Any, model: Any = None, messages: Any = None, **kw: Any):
        user = messages[-1]["content"]
        calls.append(user)
        found = [m for m in _MARKERS if m in user]
        return _resp(
            {
                "arguments": [
                    {"text": f"unite de {m}", "source_quote": m} for m in found
                ],
                "claims": [],
                "summary": "synthese",
            }
        )

    return _fake


def _run(text: str, state: Any) -> "tuple[Dict[str, Any], List[str]]":
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


class TestTheBandIsReadWholeInOneCall:
    """The DoD's own claim: within one call's capacity, the text is read once."""

    def test_the_whole_document_is_one_call(self) -> None:
        doc = _doc(_BAND_LEN)
        out, calls = _run(doc, UnifiedAnalysisState(doc))
        capacity = _lot9().one_call_extraction_capacity(_CAP)
        assert len(calls) == 1, (
            f"a {_BAND_LEN}-char document fits one call's measured capacity "
            f"({capacity} chars) and must be read once — got {len(calls)} calls"
        )
        assert calls[0] == doc, (
            "the single call must carry the DOCUMENT, byte for byte — a "
            "stitch of windows is what lot 9 replaces"
        )

    def test_the_last_part_of_the_document_reaches_the_llm_population(self) -> None:
        doc = _doc(_BAND_LEN)
        out, _ = _run(doc, UnifiedAnalysisState(doc))
        quotes = {a["source_quote"] for a in out["arguments"]}
        assert {MIDDLE_MARKER, END_MARKER} <= quotes, (
            "the markers past the old 3 000-char window sit inside the single "
            f"read and must be extracted — got {sorted(quotes)}"
        )

    def test_the_payload_counts_the_whole_document_as_read(self) -> None:
        doc = _doc(_BAND_LEN)
        out, _ = _run(doc, UnifiedAnalysisState(doc))
        assert out["reading_window_chars"] == _BAND_LEN
        assert out["source_length"] == _BAND_LEN


class TestTheRecordStatesAnIntegralRead:
    """One call, one span, the whole text — and the reader's line says it."""

    def test_the_entry_keeps_the_one_window_form(self) -> None:
        doc = _doc(_BAND_LEN)
        state = UnifiedAnalysisState(doc)
        _run(doc, state)
        entry = state.reading_window_status["fact_extraction"]
        assert "windows" not in entry, (
            "one answered window is not a stratified read — the k-fields "
            f"belong to multi-window records: {entry}"
        )
        assert (
            entry["window"] == _BAND_LEN
        ), f"the recorded window IS the document, not 3 000: {entry}"
        assert entry.get("chars_read") in (None, 0), entry

    def test_the_reader_line_says_the_document_was_read_whole(self) -> None:
        doc = _doc(_BAND_LEN)
        state = UnifiedAnalysisState(doc)
        _run(doc, state)
        record = build_reading_record(state)
        line = next(ln for ln in record.lines if ln.site == "fact_extraction")
        rendered = format_reading_line(line, record.source_chars)
        assert "document lu en entier" in rendered, rendered
        # #3393 — the count the line names is what was READ, in one
        # convention (« N caractères »): « 5400 de 5400 » borrowed the
        # window's grammar, which printed « 8000 de 921 » the day the
        # request exceeded the document.
        assert f"({_BAND_LEN} caractères)" in rendered, rendered
        assert "fenêtre" not in rendered, (
            "one call is not a window count — a plural 'fenêtres' would "
            f"describe a plan the run did not follow: {rendered}"
        )


class TestBeyondOneCallTheSampleRemains:
    """The lot-8 fallback is untouched — the dispatch says it serves beyond."""

    def test_a_long_document_still_reads_three_windows(self) -> None:
        doc = _doc(60000)
        _out, calls = _run(doc, UnifiedAnalysisState(doc))
        assert len(calls) == 3, (
            "past one call's capacity the three-window sample still governs "
            f"— got {len(calls)} calls"
        )
        assert all(len(c) <= LLM_EXTRACTION_WINDOW for c in calls)

    def test_the_sample_plan_itself_is_unchanged(self) -> None:
        assert stratified_window_offsets(60000, LLM_EXTRACTION_WINDOW) == [
            0,
            (60000 - LLM_EXTRACTION_WINDOW) // 2,
            60000 - LLM_EXTRACTION_WINDOW,
        ]


class TestTheShortDocumentIsUntouched:
    """Below today's window nothing moves — the replay band's control."""

    def test_a_document_within_the_window_is_the_same_single_call(self) -> None:
        doc = _doc(1500)
        out, calls = _run(doc, UnifiedAnalysisState(doc))
        assert len(calls) == 1
        assert calls[0] == doc, "byte-identical request, as before lot 9"
        assert out["reading_window_chars"] == 1500


class TestTheCapacityIsMeasuredNotGuessed:
    """The number is pinned to the two measurements and to the run's cap."""

    def test_the_default_cap_yields_the_measured_capacity(self) -> None:
        rw = _lot9()
        units = (_CAP - rw.EXTRACTION_FIXED_TOKENS) // rw.EXTRACTION_TOKENS_PER_UNIT
        expected = units * rw.EXTRACTION_PEAK_CHARS_PER_UNIT
        assert rw.one_call_extraction_capacity(_CAP) == expected
        assert expected >= 2 * LLM_EXTRACTION_WINDOW, (
            "the capacity must buy at least the two-window band lot 9 "
            f"replaces, else the lot changes nothing: {expected}"
        )

    def test_a_disabled_cap_keeps_todays_window(self) -> None:
        rw = _lot9()
        assert rw.one_call_extraction_capacity(0) == LLM_EXTRACTION_WINDOW, (
            "with EXTRACTION_MAX_TOKENS unset the provider decides the "
            "ceiling — an integral read would be a promise nothing backs"
        )

    def test_a_cap_below_the_fixed_cost_keeps_todays_window(self) -> None:
        rw = _lot9()
        assert (
            rw.one_call_extraction_capacity(rw.EXTRACTION_FIXED_TOKENS)
            == LLM_EXTRACTION_WINDOW
        )

    def test_the_capacity_never_shrinks_the_window(self) -> None:
        rw = _lot9()
        for cap in (1, 100, 1000, 2000, 4000, 8192, 16384):
            assert rw.one_call_extraction_capacity(cap) >= LLM_EXTRACTION_WINDOW

    def test_the_band_is_exactly_above_one_window_and_within_capacity(self) -> None:
        rw = _lot9()
        capacity = rw.one_call_extraction_capacity(_CAP)
        assert not rw.reads_whole_text_in_one_call(
            LLM_EXTRACTION_WINDOW, _CAP
        ), "the window itself keeps the selector's call (lot 8 control)"
        assert rw.reads_whole_text_in_one_call(LLM_EXTRACTION_WINDOW + 1, _CAP)
        assert rw.reads_whole_text_in_one_call(capacity, _CAP)
        assert not rw.reads_whole_text_in_one_call(capacity + 1, _CAP), (
            "one character past the capacity is a promise the completion "
            "budget cannot keep"
        )
