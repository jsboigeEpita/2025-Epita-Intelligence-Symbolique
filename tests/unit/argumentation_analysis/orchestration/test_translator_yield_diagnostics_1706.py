"""#1706 — every structured-arg translator must report raw / kept / dropped.

``CAUSE_NO_GENUINE_RELATIONS`` is documented as a statement about the *source*
("the text has no structured relations", ``state_writers`` l.190). It is
returned identically in two disjoint situations:

  1. the model proposed **nothing** (``raw = 0``);
  2. the model proposed items and **every one was dropped** at validation
     (unknown / fabricated ids → bare ``continue`` in ``_validate_*``).

The two have opposite consequences — (1) is a prompt/model question, (2) is a
plumbing question — and until #1706 only the ASPIC axis could tell them apart
(#1649's counter). On the other four axes an absence carried no information,
which is how a coordinator read "the arbiter almost never speaks" out of a
silence nothing was measuring.

These tests pin the instrument, not the wording: for each axis the two
situations must yield the **same cause** (that ambiguity is real and stays) and
**different diagnostics** (that ambiguity must be resolvable from a run's log).

No JVM, no real LLM. Synthetic atoms only (privacy HARD — no corpus tokens).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Tuple

import pytest

from argumentation_analysis.orchestration.structured_arg_translator import (
    CAUSE_NO_GENUINE_RELATIONS,
    _raw_count,
    translate_to_aba_contraries,
    translate_to_aspic_rules,
    translate_to_bipolar_supports,
    translate_to_setaf_attacks,
    translate_to_weighted_attacks,
)

_INVENTORY = ["alpha claim", "beta claim"]  # → ids arg1, arg2
_UNKNOWN = "arg99"  # never in the inventory → every item is dropped

# axis label, translate fn, payload key, one fabricated item, one genuine item
_AXES: List[Tuple[str, Any, str, Dict[str, Any], Dict[str, Any]]] = [
    (
        "Bipolar",
        translate_to_bipolar_supports,
        "supports",
        {"source": _UNKNOWN, "target": "arg1"},
        {"source": "arg1", "target": "arg2"},
    ),
    (
        "ABA",
        translate_to_aba_contraries,
        "contraries",
        {"assumption": _UNKNOWN, "contrary": "not alpha"},
        {"assumption": "arg1", "contrary": "not alpha"},
    ),
    (
        "ASPIC+",
        translate_to_aspic_rules,
        "rules",
        {"premises": [_UNKNOWN], "conclusion": _UNKNOWN},
        {"premises": ["arg1"], "conclusion": "arg2"},
    ),
    (
        "SetAF",
        translate_to_setaf_attacks,
        "attacks",
        {"attackers": [_UNKNOWN], "target": "arg1"},
        {"attackers": ["arg1"], "target": "arg2"},
    ),
    (
        "Weighted",
        translate_to_weighted_attacks,
        "attacks",
        {"source": _UNKNOWN, "target": "arg1", "weight": 0.8},
        {"source": "arg1", "target": "arg2", "weight": 0.8},
    ),
]


class _Collector(logging.Handler):
    """Collect formatted records straight off the module logger.

    Deliberately not ``caplog``: the project's logging setup reconfigures the
    root handlers, and a diagnostic that only shows up under a particular
    global config is not the instrument we want to certify.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.lines: List[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


@pytest.fixture
def yield_lines():
    """Capture the ``yield (#1706)`` lines emitted during the test."""
    log = logging.getLogger("UnifiedPipeline")
    handler = _Collector()
    previous = log.level
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    try:
        yield handler.lines
    finally:
        log.removeHandler(handler)
        log.setLevel(previous)


def _patch_llm(monkeypatch, payload: Dict[str, Any]) -> None:
    async def _fake(input_text: str, arguments: List[str], relation_kind: str):
        return payload

    monkeypatch.setattr(
        "argumentation_analysis.orchestration.structured_arg_translator."
        "_llm_extract_relations",
        _fake,
    )


def _yield_counts(lines: List[str]) -> Tuple[int, int, int]:
    """Extract ``(raw, kept, dropped)`` from the single yield line emitted."""
    hits = [ln for ln in lines if "yield (#1706)" in ln]
    assert len(hits) == 1, f"expected exactly one yield line, got {len(hits)}: {hits}"
    m = re.search(r"raw=(\d+) kept=(\d+) dropped=(-?\d+)", hits[0])
    assert m, f"yield line does not carry parsable counts: {hits[0]!r}"
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


@pytest.mark.parametrize(
    "axis,fn,key,fabricated,genuine",
    _AXES,
    ids=[a[0] for a in _AXES],
)
class TestYieldIsReportedOnEveryAxis:
    async def test_model_silent_reports_raw_zero(
        self, axis, fn, key, fabricated, genuine, monkeypatch, yield_lines
    ):
        """Situation 1: the model proposed nothing."""
        _patch_llm(monkeypatch, {key: []})
        result = await fn("text", _INVENTORY)
        assert result.cause == CAUSE_NO_GENUINE_RELATIONS
        assert _yield_counts(yield_lines) == (0, 0, 0)

    async def test_all_dropped_reports_raw_nonzero(
        self, axis, fn, key, fabricated, genuine, monkeypatch, yield_lines
    ):
        """Situation 2: the model proposed items, validation dropped them all.

        This is the case an un-instrumented axis could not distinguish from
        situation 1 — the arming input, not a restatement of the guard.
        """
        _patch_llm(monkeypatch, {key: [fabricated, fabricated]})
        result = await fn("text", _INVENTORY)
        assert result.cause == CAUSE_NO_GENUINE_RELATIONS  # same cause as above
        assert _yield_counts(yield_lines) == (2, 0, 2)

    async def test_kept_items_are_counted(
        self, axis, fn, key, fabricated, genuine, monkeypatch, yield_lines
    ):
        """A surviving item is reported as kept, not dropped — no free pass."""
        _patch_llm(monkeypatch, {key: [genuine, fabricated]})
        result = await fn("text", _INVENTORY)
        assert result.relations, f"{axis}: genuine item should have survived"
        assert _yield_counts(yield_lines) == (2, 1, 1)

    async def test_malformed_payload_does_not_raise(
        self, axis, fn, key, fabricated, genuine, monkeypatch, yield_lines
    ):
        """A diagnostic must never be the thing that kills a run.

        ``len()`` on a non-list payload would crash the translation for the
        sake of a counter.
        """
        _patch_llm(monkeypatch, {key: {"not": "a list"}})
        result = await fn("text", _INVENTORY)
        assert result.cause == CAUSE_NO_GENUINE_RELATIONS
        assert _yield_counts(yield_lines) == (0, 0, 0)


class TestYieldResolvesTheAmbiguity:
    """The point of the instrument, stated as one assertion per half."""

    @pytest.mark.parametrize(
        "axis,fn,key,fabricated,genuine", _AXES, ids=[a[0] for a in _AXES]
    )
    async def test_same_cause_different_diagnostic(
        self, axis, fn, key, fabricated, genuine, monkeypatch, yield_lines
    ):
        _patch_llm(monkeypatch, {key: []})
        silent = await fn("text", _INVENTORY)
        silent_line = [ln for ln in yield_lines if "yield (#1706)" in ln][0]

        yield_lines.clear()
        _patch_llm(monkeypatch, {key: [fabricated]})
        dropped = await fn("text", _INVENTORY)
        dropped_line = [ln for ln in yield_lines if "yield (#1706)" in ln][0]

        # The ambiguity is real: the API cannot tell these apart …
        assert silent.cause == dropped.cause == CAUSE_NO_GENUINE_RELATIONS
        assert not silent.relations and not dropped.relations
        # … and the log now can.
        assert silent_line != dropped_line


class TestRawCountTolerance:
    """``_raw_count`` must be at least as tolerant as the validators it mirrors."""

    @pytest.mark.parametrize(
        "payload",
        [None, [], "string", 42, {"k": None}, {"k": 7}, {"k": {"nested": 1}}],
    )
    def test_never_raises_on_any_payload(self, payload):
        assert _raw_count(payload, "k") == 0

    def test_counts_a_list(self):
        assert _raw_count({"k": [1, 2, 3]}, "k") == 3
