"""#3199 — a half-sourced conflict core is never a shared batch.

The measured shape (R1108 restitution): a PL MUS core opposing formula 9
(``p``, sources ``[arg_53, arg_65, arg_76]`` — one translation batch) and
formula 15 (``! p``, sources ``[]`` — no source unit). The classifier ran
``known_sides = [side for side in sides if side]``, so the sourceless side
never entered the ladder: with one known side left, the union-find found a
single component and returned ``batch_attribution`` — a class whose meaning
("conflicting formulas that share one translation batch") the sourceless
formula contradicts by construction. It belongs to no batch.

Witnessed here:

* the half-sourced core classifies ``unattributed_side`` — the class that
  says one side carries no source unit — and records the known side in
  ``pairs[0]["sources"]`` (never ``batch_attribution``);
* the controls keep the ladder honest: a shared batch (overlap) stays
  ``batch_attribution``, disjoint units stay ``between_sources``;
* the rungs that ATTRIBUTE cannot fire over a sourceless side either: a
  known speaker on the sourced flank is no longer absorbed into
  ``self_contradiction``, and a third sourceless core formula downgrades
  ``between_voices`` — the sourceless formula belongs to no speaker;
* the FOL twin keeps parity: a ground pair with one sourceless side takes
  the same class, and a summary holding both shapes keeps the positively
  attributed pair's cause;
* ``cause_phrase`` names the missing flank ("sans unité source") and never
  says "lot de traduction" for it.

Opaque atoms and unit ids only — no corpus token. Zero LLM, zero JVM.
"""

from __future__ import annotations

from argumentation_analysis.orchestration.fol_cause import (
    cause_phrase,
    classify_inconsistency,
    classify_pl_inconsistency,
)


class TestPlHalfSourcedCore:
    def test_witness_half_sourced_core_is_not_batch_attribution(self):
        # The issue's DoD shape, verbatim: one side sourced (a batch of two
        # units), one side sourceless. Born-red on main: the empty side was
        # filtered out of the ladder and the single known component read as
        # "batch_attribution".
        cause = classify_pl_inconsistency(
            ["p", "! p"], [["u1", "u2"], []], {}, core_indices=[0, 1]
        )
        assert cause["cause"] != "batch_attribution"
        assert cause["cause"] == "unattributed_side"

    def test_the_known_side_is_recorded(self):
        cause = classify_pl_inconsistency(
            ["p", "! p"], [["u1", "u2"], []], {}, core_indices=[0, 1]
        )
        assert cause["pairs"], "the mixed shape states its known flank"
        assert cause["pairs"][0]["sources"] == [["u1", "u2"], []]
        assert cause["pairs"][0]["cause"] == "unattributed_side"
        assert cause["units_known"] is True

    def test_the_phrase_names_the_missing_flank(self):
        cause = classify_pl_inconsistency(
            ["p", "! p"], [["u1", "u2"], []], {}, core_indices=[0, 1]
        )
        phrase = cause_phrase(cause)
        assert "sans unité source" in phrase
        assert "u1" in phrase and "u2" in phrase, "the known flank is named"
        assert (
            "lot de traduction" not in phrase
        ), "the sourceless formula shares no batch"
        assert "cœur minimal" in phrase, "the MUS mechanism still rides along"

    def test_control_shared_batch_still_batch_attribution(self):
        # DoD control: both sides sourced, overlapping at u2 — one entangled
        # component, the honest coarse attribution.
        cause = classify_pl_inconsistency(
            ["p", "! p"], [["u1", "u2"], ["u2", "u3"]], {}, core_indices=[0, 1]
        )
        assert cause["cause"] == "batch_attribution"

    def test_control_disjoint_units_still_between_sources(self):
        # DoD control: both sides sourced, no shared batch — separable units.
        cause = classify_pl_inconsistency(
            ["p", "! p"], [["u1"], ["u2"]], {}, core_indices=[0, 1]
        )
        assert cause["cause"] == "between_sources"

    def test_all_sides_empty_stays_undetermined(self):
        # The pre-existing honest boundary: no known unit at all.
        cause = classify_pl_inconsistency(
            ["p", "! p"], [[], []], {}, core_indices=[0, 1]
        )
        assert cause["cause"] == "undetermined"
        assert cause["pairs"] == []


class TestPlAttributionRungsCannotAbsorbASourcelessSide:
    def test_a_known_speaker_is_not_self_contradiction_over_a_sourceless_side(self):
        # The sourced flank attributes to Speaker_A, but the opposite formula
        # belongs to no unit — "auto-contradiction de Speaker_A" would claim
        # the whole conflict sits inside that voice. It does not.
        cause = classify_pl_inconsistency(
            ["p", "! p"],
            [["u1"], []],
            {"u1": "Speaker_A"},
            core_indices=[0, 1],
        )
        assert cause["cause"] == "unattributed_side"
        assert cause["pairs"][0]["speakers"] == [["Speaker_A"], []]
        assert "Speaker_A" in cause_phrase(cause)

    def test_between_voices_degrades_over_a_third_sourceless_core_formula(self):
        # A minimal chain core of three: two voiced flanks AND a sourceless
        # formula the UNSAT needs ("p", "p => q", "!q" — remove any one and
        # the set is satisfiable). "contradiction entre voix" would attribute
        # the whole conflict to the two voices; the third formula belongs to
        # no voice, so the mixed class carries, with both voices on the known
        # flank.
        cause = classify_pl_inconsistency(
            ["p", "p => q", "! q"],
            [["u1"], ["u2"], []],
            {"u1": "Speaker_A", "u2": "Speaker_B"},
            core_indices=[0, 1, 2],
        )
        assert cause["cause"] == "unattributed_side"
        assert sorted(cause["pairs"][0]["speakers"][0]) == [
            "Speaker_A",
            "Speaker_B",
        ]
        assert sorted(cause["pairs"][0]["sources"][0]) == ["u1", "u2"]


class TestFolTwinParity:
    def test_a_ground_pair_with_one_sourceless_side_takes_the_same_class(self):
        # FOL parity: the pair ladder's final ``else`` used to read
        # "batch_attribution" for every pair missing a source on one side.
        cause = classify_inconsistency(["P(a)", "!P(a)"], [["u1"], []], {})
        assert cause["cause"] == "unattributed_side"
        pair = cause["pairs"][0]
        assert pair["sources"] == [["u1"], []]
        assert pair["cause"] == "unattributed_side"
        assert "sans unité source" in cause_phrase(cause)

    def test_control_disjoint_units_still_between_sources(self):
        cause = classify_inconsistency(["P(a)", "!P(a)"], [["u1"], ["u2"]], {})
        assert cause["cause"] == "between_sources"

    def test_control_shared_batch_still_batch_attribution(self):
        cause = classify_inconsistency(
            ["P(a)", "!P(a)"], [["u1", "u2"], ["u2", "u3"]], {}
        )
        assert cause["cause"] == "batch_attribution"

    def test_a_voiced_pair_outranks_a_half_sourced_pair_in_the_summary(self):
        # Two ground pairs: one positively attributed (two voices), one
        # half-sourced. The summary keeps the established attribution — the
        # half-sourced pair does not drag the whole verdict down with it.
        cause = classify_inconsistency(
            ["P(a)", "!P(a)", "Q(b)", "!Q(b)"],
            [["u1"], ["u2"], ["u3"], []],
            {"u1": "Speaker_A", "u2": "Speaker_B"},
        )
        assert cause["cause"] == "between_voices"
        kinds = {p["cause"] for p in cause["pairs"]}
        assert kinds == {"between_voices", "unattributed_side"}
