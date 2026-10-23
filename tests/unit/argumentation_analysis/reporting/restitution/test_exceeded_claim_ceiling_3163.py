"""#3163 — the EXCEEDED ceiling licenses breadth of axes, never extent read.

The band counts axes that produced non-trivial content (6 of 6 on R1107c) — by
design, and not the defect. The defect was the ceiling text: it turned that
count into « elle couvre largement les dimensions », while the same prompt
carried reading bounds where no axis read more than 15 of 90 units (extraction
7 of 90, fallacy detection / FOL / PL 10 of 90). The writer put « broad
coverage » and the bounds side by side in one closing paragraph.

The band thresholds are untouched (`_EXCEEDED_MIN_AXES` and friends) — the axis
count is right, the words it licenses were not.

R1108 review: the first ceiling hard-coded « six axes ou plus », but the band
is EXCEEDED from `_EXCEEDED_MIN_AXES` = 5, and five of the six five-axis shapes
of `_ALL_AXES` are EXCEEDED (measured by the coordinator on every subset) — on
those shapes the prompt told the writer that six axes spoke when five did, a
figure the record contradicts. The count in the ceiling is now derived from the
thresholds, and a five-axis EXCEEDED shape is witnessed.

The #1605 deterministic gate is *out of scope* here, and this is stated rather
than assumed: it removes an assertion resting on an axis that produced nothing,
matched per axis by `_AXIS_CLAIM_MARKERS`. An extent claim (« couvre
largement ») asserts how much was READ, not which axis spoke, so no per-axis
marker table can catch it — the fix belongs in the ceiling text itself.
"""

from __future__ import annotations

from pathlib import Path

from argumentation_analysis.reporting.restitution import act3_conclusion_plugin
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    _ALL_AXES,
    _BAND_EXCEEDED,
    _BAND_MATCH,
    _EXCEEDED_MIN_AXES,
    _MATCH_MIN_AXES,
    _band_claim_ceiling,
    _compute_verdict_band,
)

_EXTENT_WORDS = ("couvre largement", "couvre les", "couvre l'", "couvre ")


def _ceiling(band: str) -> str:
    return _band_claim_ceiling(band)


class TestTheCeilingClaimsNoExtent:
    def test_exceeded_names_axes_and_states_no_extent(self):
        text = _ceiling(_BAND_EXCEEDED)
        for word in _EXTENT_WORDS:
            assert word not in text, f"{word!r} is an extent claim: {text}"
        assert "AXES" in text and "bornes" in text, (
            "the ceiling says what the band measures (axes) and points at the "
            "reading bounds instead of asserting extent"
        )

    def test_match_names_axes_and_states_no_extent(self):
        text = _ceiling(_BAND_MATCH)
        for word in _EXTENT_WORDS:
            assert word not in text, f"{word!r} is an extent claim: {text}"

    def test_the_module_carries_no_extent_phrase_any_more(self):
        source = Path(act3_conclusion_plugin.__file__).read_text(encoding="utf-8")
        assert "couvre largement" not in source


class TestTheBandItselfIsUnchanged:
    def test_six_axes_with_formal_depth_and_quality_stay_exceeded(self):
        verdict = _compute_verdict_band(list(_ALL_AXES))
        assert verdict.band == _BAND_EXCEEDED
        assert verdict.axes_count == 6

    def test_the_thresholds_are_untouched(self):
        assert _EXCEEDED_MIN_AXES == 5
        assert _MATCH_MIN_AXES == 4

    def test_the_ceiling_still_differs_per_band(self):
        assert _ceiling(_BAND_EXCEEDED) != _ceiling(_BAND_MATCH)


class TestAFiveAxisExceededShape:
    """R1108 review: EXCEEDED fires from `_EXCEEDED_MIN_AXES` = 5, so five of
    the six five-axis shapes of `_ALL_AXES` are EXCEEDED (measured on every
    subset). On those shapes a ceiling that says « six axes » tells the writer
    a figure the record contradicts — the count must be derived, not
    hard-coded."""

    def test_five_axes_still_exceeded_and_the_ceiling_derives_its_count(self):
        five_axes = [a for a in _ALL_AXES if a != "counter_arguments"]
        assert len(five_axes) == 5
        verdict = _compute_verdict_band(five_axes)
        assert verdict.band == _BAND_EXCEEDED, (
            "the shape is EXCEEDED with five axes — if this changed, pick "
            "another of the five EXCEEDED five-axis shapes"
        )
        text = _ceiling(_BAND_EXCEEDED)
        assert (
            "six axes" not in text
        ), f"a five-axis EXCEEDED run read this ceiling: {text}"
        assert (
            f"au moins {_EXCEEDED_MIN_AXES}" in text
        ), "the count is derived from the threshold, not hard-coded"
