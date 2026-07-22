"""Unit tests for the selectable dung_arbitration stage (Track I1 #1501, PR1).

JVM/LLM-free: the stage reuses ``neuro_symbolic_arbitrator.arbitrate`` with the
pure-python grounded solver, so every test runs on synthetic opaque atoms. The
anti-#1019 contract is asserted explicitly — the stage CHANGES the verdict when
enabled and there is something genuine to arbitrate, and is transparent
(output == input) otherwise.
"""

from __future__ import annotations

from argumentation_analysis.agents.core.debate.protocols import SpeechAct
from argumentation_analysis.agents.core.informal.dung_arbitration_stage import (
    WALTON_KRABBE_ATTACKING_ACTS,
    arbitrate_detections,
    combine_conflict_policies,
    walton_krabbe_conflict_policy,
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


class TestWaltonKrabbeConflictPolicy:
    def test_declared_refutation_becomes_attack(self) -> None:
        cands = [_cand("a"), _cand("b")]
        policy = walton_krabbe_conflict_policy({"a": frozenset({"b"})})
        assert policy(cands) == {("a", "b")}

    def test_unknown_challenger_ignored(self) -> None:
        cands = [_cand("a")]  # challenger 'b' absent
        policy = walton_krabbe_conflict_policy({"b": frozenset({"a"})})
        assert policy(cands) == set()

    def test_self_loop_ignored(self) -> None:
        cands = [_cand("a")]
        policy = walton_krabbe_conflict_policy({"a": frozenset({"a"})})
        assert policy(cands) == set()

    def test_unknown_target_ignored(self) -> None:
        cands = [_cand("a")]
        policy = walton_krabbe_conflict_policy({"a": frozenset({"ghost"})})
        assert policy(cands) == set()

    def test_empty_relations_is_honest_absent(self) -> None:
        cands = [_cand("a"), _cand("b")]
        policy = walton_krabbe_conflict_policy({})
        assert policy(cands) == set()


class TestCombineConflictPolicies:
    def test_union_of_attacks(self) -> None:
        cands = [_cand("a"), _cand("b"), _cand("c")]
        p1 = walton_krabbe_conflict_policy({"a": frozenset({"b"})})
        p2 = walton_krabbe_conflict_policy({"c": frozenset({"b"})})
        combined = combine_conflict_policies(p1, p2)
        assert combined(cands) == {("a", "b"), ("c", "b")}


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
        # Different spans, no declared refutations → no attacks → output == input.
        cands = [_cand("s0", span="x"), _cand("s1", span="y")]
        verdict = arbitrate_detections(cands, dung_arbitration=True)
        assert verdict.enabled is True
        assert verdict.surviving_ids == frozenset({"s0", "s1"})
        assert verdict.honest_absent is True
        assert verdict.eliminated_ids == {}


class TestVerdictChangeAntiTheatre:
    """DoD #2/#3: the stage MUST change the verdict on a genuine case (anti-#1019)."""

    def test_walton_krabbe_refutation_filters_candidate(self) -> None:
        # s0 is refuted by a surviving refuter r0 on a different span. Under
        # grounded, r0 is unattacked → accepted; s0 is defeated (FP filtered).
        cands = [
            _cand("s0", family="appeal_to_authority", span="span_a", conf=0.9),
            _cand("r0", family="counter_example", span="span_b", conf=0.95),
        ]
        relations = {"r0": frozenset({"s0"})}

        off = arbitrate_detections(cands, dung_arbitration=False)
        on = arbitrate_detections(
            cands, dung_arbitration=True, walton_krabbe_relations=relations
        )

        # Verdict CHANGES: s0 survives off, eliminated on.
        assert "s0" in off.surviving_ids
        assert "s0" not in on.surviving_ids
        assert on.eliminated_ids["s0"] == "defeated_by_walton_krabbe_refutation"
        # The refuter survives (defended argument reinstated).
        assert "r0" in on.surviving_ids
        assert on.honest_absent is False
        assert ("r0", "s0") in on.attacks

    def test_fp_filter_scenario_concrete(self) -> None:
        # A hasty-generalization false positive (fp) is refuted by a surviving
        # empirical counter-argument (cnt). The stage filters the FP.
        cands = [
            _cand("fp", family="hasty_generalization", span="span_x", conf=0.7),
            _cand("cnt", family="empirical_evidence", span="span_y", conf=0.95),
        ]
        relations = {"cnt": frozenset({"fp"})}
        on = arbitrate_detections(
            cands, dung_arbitration=True, walton_krabbe_relations=relations
        )
        off = arbitrate_detections(cands, dung_arbitration=False)
        assert off.surviving_ids == frozenset({"fp", "cnt"})
        assert on.surviving_ids == frozenset({"cnt"})
        assert on.eliminated_ids["fp"] == "defeated_by_walton_krabbe_refutation"

    def test_mutual_refutation_eliminates_both(self) -> None:
        # s0 ↔ r0 mutual refutation (Walton-Krabbe tie) → grounded = ∅, both out.
        cands = [_cand("s0", span="a"), _cand("r0", span="b")]
        relations = {"s0": frozenset({"r0"}), "r0": frozenset({"s0"})}
        on = arbitrate_detections(
            cands, dung_arbitration=True, walton_krabbe_relations=relations
        )
        assert on.surviving_ids == frozenset()
        assert set(on.eliminated_ids) == {"s0", "r0"}
        assert on.honest_absent is False

    def test_refuter_defeated_does_not_eliminate_target(self) -> None:
        # Genuine grounded semantics, not blind attack-counting. Chain:
        #   defender → refuter → target
        # defender (unattacked) is in; refuter is attacked by defender (in) → out;
        # target's only attacker (refuter) is counter-attacked by defender (in) →
        # target is DEFENDED and survives. The refuter does not eliminate it.
        cands = [
            _cand("target", span="a"),
            _cand("refuter", span="b"),
            _cand("defender", span="c"),
        ]
        relations = {
            "refuter": frozenset({"target"}),
            "defender": frozenset({"refuter"}),
        }
        on = arbitrate_detections(
            cands, dung_arbitration=True, walton_krabbe_relations=relations
        )
        assert "defender" in on.surviving_ids
        assert "target" in on.surviving_ids
        assert "refuter" not in on.surviving_ids


class TestAttackingActsContract:
    def test_attacking_acts_are_refute_and_challenge(self) -> None:
        assert WALTON_KRABBE_ATTACKING_ACTS == frozenset(
            {SpeechAct.REFUTE, SpeechAct.CHALLENGE}
        )
        # Cooperative acts are excluded (they never yield an attack).
        assert SpeechAct.CONCEDE not in WALTON_KRABBE_ATTACKING_ACTS
        assert SpeechAct.SUPPORT not in WALTON_KRABBE_ATTACKING_ACTS
