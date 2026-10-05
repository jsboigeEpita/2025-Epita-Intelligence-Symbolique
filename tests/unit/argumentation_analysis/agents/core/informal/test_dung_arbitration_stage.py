"""Unit tests for the selectable dung_arbitration stage (Track I1 #1501).

JVM/LLM-free: the stage reuses ``neuro_symbolic_arbitrator.arbitrate`` with the
pure-python grounded solver, so every test runs on synthetic opaque atoms. The
anti-#1019 contract is asserted explicitly — the stage CHANGES the verdict when
enabled and there is something genuine to arbitrate, and is transparent
(output == input) otherwise.

The declared Walton-Krabbe relations channel was retired (#1649 R1065): no
producer ever fed it, so its tests went with it. The verdict-change witnesses
below run on the surviving attack source — same-span rivalry — and on the
generic ``conflict_policy`` injection point.
"""

from __future__ import annotations

from argumentation_analysis.agents.core.informal.dung_arbitration_stage import (
    arbitrate_detections,
)
from argumentation_analysis.agents.core.informal.neuro_symbolic_arbitrator import (
    SophismCandidate,
)


def _cand(
    cid: str, family: str = "f", span: str = "s", conf: float = 0.5
) -> SophismCandidate:
    return SophismCandidate(
        candidate_id=cid, family=family, span_id=span, confidence=conf
    )


class TestArbitrateDetectionsSelector:
    def test_off_is_passthrough_backward_compat(self) -> None:
        cands = [_cand("s0"), _cand("s1")]
        verdict = arbitrate_detections(cands, dung_arbitration=False)
        assert verdict.enabled is False
        assert verdict.surviving_ids == frozenset({"s0", "s1"})
        assert verdict.eliminated_ids == {}
        assert verdict.attacks == frozenset()
        assert verdict.honest_absent is True
        assert verdict.surviving_count == verdict.input_count == 2

    def test_on_no_attacks_is_honest_absent_transparent(self) -> None:
        # Different spans → no rivalry → no attacks → output == input.
        cands = [_cand("s0", span="x"), _cand("s1", span="y")]
        verdict = arbitrate_detections(cands, dung_arbitration=True)
        assert verdict.enabled is True
        assert verdict.surviving_ids == frozenset({"s0", "s1"})
        assert verdict.honest_absent is True
        assert verdict.eliminated_ids == {}


class TestVerdictChangeAntiTheatre:
    """DoD #2/#3: the stage MUST change the verdict on a genuine case (anti-#1019).

    Since the Walton-Krabbe channel's retirement (#1649 R1065), the genuine case
    is same-span rivalry: two candidates anchored on the same span with different
    families and ranked confidences.
    """

    def test_same_span_rivalry_filters_weaker_candidate(self) -> None:
        # Two families disagree on the same span; the more confident detection
        # attacks the weaker one. Under grounded, the attacker is unattacked →
        # accepted; the weaker is defeated (FP filtered).
        cands = [
            _cand("s0", family="appeal_to_authority", span="span_a", conf=0.9),
            _cand("r0", family="counter_example", span="span_a", conf=0.95),
        ]

        off = arbitrate_detections(cands, dung_arbitration=False)
        on = arbitrate_detections(cands, dung_arbitration=True)

        # Verdict CHANGES: s0 survives off, eliminated on.
        assert "s0" in off.surviving_ids
        assert "s0" not in on.surviving_ids
        assert on.eliminated_ids["s0"] == "defeated_by_rival_candidate"
        # The surviving rival is reinstated.
        assert "r0" in on.surviving_ids
        assert on.honest_absent is False
        assert ("r0", "s0") in on.attacks

    def test_fp_filter_scenario_concrete(self) -> None:
        # A hasty-generalization false positive (fp) is out-ranked on its own
        # span by a stronger detection of another family. The stage filters it.
        cands = [
            _cand("fp", family="hasty_generalization", span="span_x", conf=0.7),
            _cand("cnt", family="false_dilemma", span="span_x", conf=0.95),
        ]
        on = arbitrate_detections(cands, dung_arbitration=True)
        off = arbitrate_detections(cands, dung_arbitration=False)
        assert off.surviving_ids == frozenset({"fp", "cnt"})
        assert on.surviving_ids == frozenset({"cnt"})
        assert on.eliminated_ids["fp"] == "defeated_by_rival_candidate"

    def test_same_family_same_span_is_not_a_conflict(self) -> None:
        # A passage may legitimately surface the same fallacy twice: same span,
        # same family → no edge, both survive (the rivalry signal is disagreement,
        # not multiplicity).
        cands = [
            _cand("d0", family="hasty_generalization", span="span_a", conf=0.7),
            _cand("d1", family="hasty_generalization", span="span_a", conf=0.9),
        ]
        on = arbitrate_detections(cands, dung_arbitration=True)
        assert on.honest_absent is True
        assert on.surviving_ids == frozenset({"d0", "d1"})
        assert on.attacks == frozenset()

    def test_confidence_tie_eliminates_both(self) -> None:
        # Exact confidence tie on a rival pair — cannot rank; mutual attack,
        # both fall under grounded (mirrors #1429's documented tie semantics).
        cands = [
            _cand("a", family="f1", span="span_t", conf=0.8),
            _cand("b", family="f2", span="span_t", conf=0.8),
        ]
        on = arbitrate_detections(cands, dung_arbitration=True)
        assert on.surviving_ids == frozenset()
        assert set(on.eliminated_ids) == {"a", "b"}
        assert on.honest_absent is False

    def test_injected_policy_grounded_chain_semantics(self) -> None:
        # Genuine grounded semantics, not blind attack-counting, still provable
        # through the generic ``conflict_policy`` injection point (the surviving
        # cross-candidate escape hatch). Chain: defender → refuter → target.
        # defender (unattacked) is in; refuter is attacked by defender (in) → out;
        # target's only attacker (refuter) is counter-attacked by defender (in) →
        # target is DEFENDED and survives. The refuter does not eliminate it.
        cands = [
            _cand("target", span="a"),
            _cand("refuter", span="b"),
            _cand("defender", span="c"),
        ]
        declared = {("refuter", "target"), ("defender", "refuter")}
        on = arbitrate_detections(
            cands,
            dung_arbitration=True,
            conflict_policy=lambda candidates: declared,
        )
        assert "defender" in on.surviving_ids
        assert "target" in on.surviving_ids
        assert "refuter" not in on.surviving_ids
