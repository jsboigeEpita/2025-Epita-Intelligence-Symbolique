"""#1907 cross-act residue — the forces slot must not praise a weak axis.

The documented residue (coordinator read of a real run, 2026-09-04): Act II
tells the reader the quality axis "ne discrimine pas" (best score of the
entire discourse: 0.5 pertinence, 0.2 clarity — six notes under the weak
threshold), while Act III's data block hands the top-N of that same weak set
to the conductor under a slot literally labelled ``[CE QUI TIENT — forces
(qualité)]`` — so a 0.2 clarity reaches the page as "what the discourse has
going for it".

Measured source-first on this branch: ``_collect_quality_strengths`` had no
threshold — ANY virtue with a score > 0 became a "force" (max-aggregated,
sorted), so the father emitted the identical shape for a non-discriminating
weak axis and for a genuinely discriminating one. The contrast test below is
the qualification: it fails on that behavior.

The fix anchors "force" on the quality instrument's own shared scale
``{0.0, 0.2, 0.5, 1.0}`` (``_snap_to_scale``, agentic_virtue_detectors; the
lexical detectors emit the same bands): a force is a virtue that reached the
TOP band (1.0) on at least one argument. 0.5 is the instrument's own
"partiel" wording — a partial is not "ce qui tient". When no virtue
qualifies, the slot renders the pre-existing honest-absence wording — the
renderer already had both states; only the father never produced the empty
one.

Scope guards: tri-state statuses, R2 admission (#2085), the appendix, the
weaknesses slot and the verdict band's axis-coverage counting are untouched
— an available-but-weak axis still counts as *measured* (Act II may weave
virtues as character); what empties is praise, not measurement.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

# Synthetic fixtures, opaque IDs. The weak axis is the documented shape of the
# real run (best 0.5 / floor 0.2 across arguments — "non discriminant").
_WEAK_AXIS = {
    "arg_1": {"scores": {"pertinence": 0.5, "clarte": 0.2}},
    "arg_2": {"scores": {"pertinence": 0.2, "clarte": 0.2}},
    "arg_3": {"scores": {"pertinence": 0.5, "clarte": 0.2}},
}
_DISCRIMINATING_AXIS = {
    "arg_1": {"scores": {"pertinence": 1.0, "clarte": 0.2}},
    "arg_2": {"scores": {"pertinence": 0.9, "clarte": 0.2}},
}
_ARGS = {
    "arg_1": "Une revendication synthetique.",
    "arg_2": "Une seconde revendication.",
}


def _state(quality: dict) -> SimpleNamespace:
    return SimpleNamespace(
        identified_arguments=_ARGS,
        identified_fallacies={},
        argument_quality_scores=quality,
        counter_arguments=[],
    )


def _forces_slot(prompt: str) -> str:
    start = prompt.find("[CE QUI TIENT — forces (qualité)]")
    assert start != -1, "forces slot missing from the Act III prompt"
    end = prompt.find("[", start + 1)
    return prompt[start : end if end != -1 else len(prompt)]


class TestForcesRequireTopBand:
    """The father: only the instrument's top band (1.0) is a force."""

    def test_weak_non_discriminating_axis_yields_no_strengths(self):
        ev = build_act3_evidence(_state(_WEAK_AXIS))
        assert ev.quality_strengths == [], (
            "#1907 cross-act: a weak axis (best 0.5, floor 0.2) must not "
            "produce 'forces' — that is the documented best-of-a-bad-set "
            f"fabrication, got {ev.quality_strengths!r}"
        )

    def test_partial_score_is_not_a_force(self):
        ev = build_act3_evidence(_state({"arg_1": {"scores": {"pertinence": 0.5}}}))
        assert ev.quality_strengths == [], (
            "0.5 is the instrument's own 'partiel' band — a partial is not "
            "'ce qui tient'."
        )

    def test_discriminating_axis_keeps_its_forces(self):
        ev = build_act3_evidence(_state(_DISCRIMINATING_AXIS))
        got = {s.virtue: s.score for s in ev.quality_strengths}
        assert got == {"pertinence": 1.0}, (
            f"a genuinely strong virtue survives (discriminant => forces "
            f"conservées); weak ones stay excluded, got {got!r}"
        )

    def test_values_at_or_above_one_still_qualify(self):
        # Tolerance for non-canonical writers: the collector's contract
        # accepts any numeric scale; >= 1.0 admits the /10-shaped entries of
        # the historical rich fixture unchanged.
        ev = build_act3_evidence(
            _state({"arg_1": {"scores": {"pertinence": 8.0, "clarte": 5.0}}})
        )
        got = {s.virtue: s.score for s in ev.quality_strengths}
        assert got == {"pertinence": 8.0, "clarte": 5.0}


class TestCrossActContradictionClosed:
    """The slot as the Act III conductor actually reads it."""

    def test_weak_axis_slot_says_absence_not_best_of_weak(self):
        prompt = build_act3_prompt(build_act3_evidence(_state(_WEAK_AXIS)))
        slot = _forces_slot(prompt)
        assert "non concluable" in slot, (
            "#1907: with a non-discriminating axis the forces slot must be "
            "empty AND said to be empty — the renderer's honest-absence "
            f"wording, got: {slot!r}"
        )
        assert "pertinence" not in slot and "clarte" not in slot

    def test_discriminating_axis_slot_lists_the_force(self):
        prompt = build_act3_prompt(build_act3_evidence(_state(_DISCRIMINATING_AXIS)))
        slot = _forces_slot(prompt)
        assert "pertinence (meilleur score du discours : 1.0)" in slot
        assert "clarte" not in slot

    def test_weak_but_present_axis_still_counts_as_measured(self):
        # Scope guard: what empties is praise, not measurement. The axis was
        # evaluated (scores exist) — Act II's availability signal and the
        # verdict band's coverage counting must not change.
        ev = build_act3_evidence(_state(_WEAK_AXIS))
        assert ev.quality_axis_available is True
        ev_strong = build_act3_evidence(_state(_DISCRIMINATING_AXIS))
        assert ev_strong.quality_axis_available is True
