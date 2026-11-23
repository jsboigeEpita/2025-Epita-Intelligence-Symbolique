"""#3658 item 41(c) — a cut that kept NOTHING still names the cut.

Measured defect (coordinator State, R1207, free doc_J run i1207): the reading
spent its whole 8 192 cap before writing one readable object, and the record
read ``parse_error`` with no mention of the length stop — #3677 sets
``degraded`` only on the ``ok`` path. The panel could not tell an empty answer
from one that was cut mid-object with nothing surviving.

Born red on ``main``: both witnesses below — the producer's record and the
invoke's composed detail — name the cut only after this PR.

Seat-free: invented text and answers, a plain callable exposing the two
attributes the production persona callable sets (#3677's documented seam).
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.reading import build_first_reading
from argumentation_analysis.orchestration import invoke_callables as ic

_CAP = 8192

#: Invented document — a real shape, never a corpus sentence.
_DOC = (
    "The report opens by conceding that the measure cost the region dearly. "
    "It then claims the effort was worth it, resting on a single figure. "
    "A closing paragraph urges the reader to choose a side."
)

#: A reply no parser can read: the cut lost every object, so the salvage keeps
#: nothing — the exact i1207 shape ("no 'moves' list in the answer").
_NOTHING_KEEPABLE = (
    "the model spent its budget reasoning and the answer was cut mid-obj"
)


class _CutToNothing:
    """A callable whose call stopped on ``length`` and kept nothing."""

    last_finish_reason = "length"
    last_max_tokens = _CAP

    async def __call__(self, prompt: str) -> str:
        return _NOTHING_KEEPABLE


async def test_a_cut_that_kept_nothing_records_degraded_with_the_cut_reason():
    result = await build_first_reading(SimpleNamespace(raw_text=_DOC), _CutToNothing())
    assert result.status == "parse_error", result.status
    assert result.degraded is True, (
        "a length-stopped parse_error must carry degraded: true — the record "
        "says the answer was cut, not merely unreadable"
    )
    reason = result.degraded_reason
    assert "finish_reason=length" in reason, reason
    assert f"cap {_CAP}" in reason, reason
    assert "nothing" in reason.lower(), reason


async def test_an_uncut_parse_error_stays_a_plain_parse_error():
    """Positive control: an unreadable answer the call COMPLETED is a plain
    parse_error — the signal is the finish reason, never an inference."""

    class _Complete:
        last_finish_reason = "stop"
        last_max_tokens = _CAP

        async def __call__(self, prompt: str) -> str:
            return _NOTHING_KEEPABLE

    result = await build_first_reading(SimpleNamespace(raw_text=_DOC), _Complete())
    assert result.status == "parse_error", result.status
    assert result.degraded is False, result.degraded_reason


async def test_the_invoke_detail_keeps_the_cut_reason(monkeypatch):
    """The invoke composes its own detail WITH the producer's cut reason — the
    i1207 record read as a bare ``first_reading parse_error`` line."""
    monkeypatch.setattr(
        ic,
        "_build_persona_callable",
        lambda site, max_completion_tokens=None: (_CutToNothing(), ""),
    )
    payload = await ic._invoke_first_reading(
        "ignored", {"_state_object": SimpleNamespace(raw_text=_DOC)}
    )
    assert payload["status"] == "parse_error", payload
    assert payload.get("degraded") is True, payload
    reason = payload.get("degraded_reason", "")
    assert "parse_error" in reason, reason
    assert "finish_reason=length" in reason, reason


def test_the_nothing_kept_variant_of_the_reason_is_truthful():
    """The kept-something wording must not leak into the kept-nothing case."""
    from argumentation_analysis.agents.core.reading.first_reading import (
        _cut_degraded_reason,
    )

    reason = _cut_degraded_reason(cap=_CAP, kept_nothing=True)
    assert "were kept" not in reason, reason
    assert "finish_reason=length" in reason and f"cap {_CAP}" in reason, reason
