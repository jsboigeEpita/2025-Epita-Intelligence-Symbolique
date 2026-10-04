"""Unit tests for the rule-vs-ML detection candidate bridge (Track I1 #1501, PR2).

JVM/LLM-free: the bridge is a pure transformer mapping detection dicts (from
``TaxonomySophismDetector`` rule side, or the hierarchical/ML phase output) to
opaque :class:`SophismCandidate` atoms, plus a multi-source combiner. Every test
runs on synthetic opaque dicts — no detector, no JVM, no LLM.

The contract asserted here is the rule-vs-ML provenance dimension (#1501): a
rule detection and an ML detection of the SAME family stay distinct atoms
(detector is part of the opaque id + span anchor), and the bridge is tolerant of
both the taxonomy shape (``famille``/``name``) and the hierarchical/ML shape
(``family``/``fallacy_type``).
"""

from __future__ import annotations

from argumentation_analysis.agents.core.informal.detection_candidate_bridge import (
    combine_candidate_sources,
    taxonomy_detection_to_candidate,
    taxonomy_detections_to_candidates,
)
from argumentation_analysis.agents.core.informal.neuro_symbolic_arbitrator import (
    SophismCandidate,
)


class TestTaxonomyDetectionToCandidate:
    def test_maps_rule_taxonomy_shape(self) -> None:
        det = {"famille": "Ad Hominem", "confidence": 0.8, "name": "ad_hominem"}
        cand = taxonomy_detection_to_candidate(det, index=2)
        assert cand.family == "Ad Hominem"
        assert cand.confidence == 0.8
        # Default detector label + index baked into the opaque id.
        assert cand.candidate_id == "rule_taxonomy_2"

    def test_tolerates_hierarchical_ml_shape(self) -> None:
        # The ML/hierarchical phase emits family/fallacy_type, not famille/name.
        det = {"fallacy_type": "Straw Man", "confidence": 0.6}
        cand = taxonomy_detection_to_candidate(det, index=0, detector="ml_llm")
        assert cand.family == "Straw Man"
        assert cand.confidence == 0.6
        assert cand.candidate_id == "ml_llm_0"

    def test_missing_family_defaults_opaque(self) -> None:
        cand = taxonomy_detection_to_candidate({"confidence": 0.4}, index=1)
        assert cand.family == "unknown"

    def test_confidence_clamped_to_unit_interval(self) -> None:
        assert (
            taxonomy_detection_to_candidate(
                {"famille": "f", "confidence": 1.5}, index=0
            ).confidence
            == 1.0
        )
        assert (
            taxonomy_detection_to_candidate(
                {"famille": "f", "confidence": -0.2}, index=0
            ).confidence
            == 0.0
        )

    def test_missing_or_bad_confidence_defaults_to_half(self) -> None:
        assert (
            taxonomy_detection_to_candidate({"famille": "f"}, index=0).confidence == 0.5
        )
        assert (
            taxonomy_detection_to_candidate(
                {"famille": "f", "confidence": "oops"}, index=0
            ).confidence
            == 0.5
        )

    def test_nan_confidence_defaults_to_half(self) -> None:
        nan = float("nan")
        assert (
            taxonomy_detection_to_candidate(
                {"famille": "f", "confidence": nan}, index=0
            ).confidence
            == 0.5
        )

    def test_span_id_deterministic_for_same_family_and_detector(self) -> None:
        a = taxonomy_detection_to_candidate({"famille": "Slippery Slope"}, index=0)
        b = taxonomy_detection_to_candidate({"famille": "Slippery Slope"}, index=1)
        # Same (detector, family) ⇒ same opaque anchor (rule detections carry no span).
        assert a.span_id == b.span_id
        assert a.span_id.startswith("span_")

    def test_rule_and_ml_of_same_family_do_not_collapse(self) -> None:
        rule = taxonomy_detection_to_candidate(
            {"famille": "Bandwagon"}, index=0, detector="rule_taxonomy"
        )
        ml = taxonomy_detection_to_candidate(
            {"fallacy_type": "Bandwagon"}, index=0, detector="ml_llm"
        )
        # Provenance keeps the atoms distinct even for the same family label.
        assert rule.span_id != ml.span_id
        assert rule.candidate_id != ml.candidate_id
        assert rule.family == ml.family == "Bandwagon"


class TestTaxonomyDetectionsToCandidates:
    def test_stable_order_and_unique_ids(self) -> None:
        dets = [
            {"famille": "A", "confidence": 0.9},
            {"famille": "B", "confidence": 0.3},
        ]
        cands = taxonomy_detections_to_candidates(dets)
        assert [c.candidate_id for c in cands] == ["rule_taxonomy_0", "rule_taxonomy_1"]
        assert [c.family for c in cands] == ["A", "B"]

    def test_empty_batch_returns_empty(self) -> None:
        assert taxonomy_detections_to_candidates([]) == []


class TestCombineCandidateSources:
    def test_union_preserves_order_and_unique_ids(self) -> None:
        rule = taxonomy_detections_to_candidates(
            [{"famille": "A"}, {"famille": "B"}], detector="rule_taxonomy"
        )
        ml = taxonomy_detections_to_candidates(
            [{"fallacy_type": "C"}], detector="ml_llm"
        )
        combined = combine_candidate_sources({"rule_taxonomy": rule, "ml_llm": ml})
        assert [c.candidate_id for c in combined] == [
            "rule_taxonomy_0",
            "rule_taxonomy_1",
            "ml_llm_0",
        ]
        assert {c.family for c in combined} == {"A", "B", "C"}

    def test_cross_source_id_collision_is_disambiguated(self) -> None:
        # Two sources craft ids that collide (same literal candidate_id) — the
        # combiner must prefix to guarantee global uniqueness.
        rule = [
            SophismCandidate(
                candidate_id="dup", family="A", span_id="s1", confidence=0.5
            )
        ]
        ml = [
            SophismCandidate(
                candidate_id="dup", family="B", span_id="s2", confidence=0.5
            )
        ]
        combined = combine_candidate_sources({"rule_taxonomy": rule, "ml_llm": ml})
        assert len(combined) == 2
        ids = {c.candidate_id for c in combined}
        assert "dup" in ids  # first occurrence kept verbatim
        assert len(ids) == 2  # second disambiguated, no loss

    def test_empty_sources_returns_empty(self) -> None:
        assert combine_candidate_sources({}) == []


class TestTargetArgumentAnchor:
    """#2920: a detection carrying ``target_argument`` anchors on the TARGET.

    Pre-#2920 the span anchor was always md5(detector::family), so two
    candidates shared a span only when they shared a family — and the rivalry
    policy skips same-family pairs, making the same-span channel dead for ANY
    input. These witnesses are born-red against that bridge: same target,
    different families must rival.
    """

    def test_same_target_different_families_share_span(self) -> None:
        a = taxonomy_detection_to_candidate(
            {"fallacy_type": "appeal_to_authority", "target_argument": "arg_3"},
            index=0,
            detector="hierarchical",
        )
        b = taxonomy_detection_to_candidate(
            {"fallacy_type": "hasty_generalization", "target_argument": "arg_3"},
            index=1,
            detector="hierarchical",
        )
        assert a.span_id == b.span_id
        assert a.family != b.family

    def test_anchorless_falls_back_to_family_hash(self) -> None:
        a = taxonomy_detection_to_candidate(
            {"fallacy_type": "appeal_to_authority"}, index=0, detector="hierarchical"
        )
        b = taxonomy_detection_to_candidate(
            {"fallacy_type": "hasty_generalization"}, index=1, detector="hierarchical"
        )
        # No target ⇒ the (detector, family) hash: different families never
        # share a span (the pre-#2920 behavior, unchanged for anchorless).
        assert a.span_id != b.span_id

    def test_cross_detector_same_target_shares_span(self) -> None:
        # The #1501 rule-vs-ML dimension: the target alone anchors, so a rule
        # detection and an ML detection of the SAME target are rivals.
        rule = taxonomy_detection_to_candidate(
            {"famille": "Ad Hominem", "target_argument": "arg_7"},
            index=0,
            detector="rule_taxonomy",
        )
        ml = taxonomy_detection_to_candidate(
            {"fallacy_type": "straw_man", "target_argument": "arg_7"},
            index=0,
            detector="hierarchical",
        )
        assert rule.span_id == ml.span_id

    def test_same_target_different_families_attack_through_stage(self) -> None:
        """DoD #2920 witness: the attack fires through the REAL bridge.

        Two different families grounded on the same argument, bridged by
        ``taxonomy_detections_to_candidates`` (not hand-built atoms), must
        produce a rivalry attack under the enabled arbitration stage — the
        more confident candidate eliminates the lesser.
        """
        from argumentation_analysis.agents.core.informal.dung_arbitration_stage import (
            arbitrate_detections,
        )

        detections = [
            {
                "fallacy_type": "appeal_to_authority",
                "target_argument": "arg_3",
                "confidence": 0.9,
            },
            {
                "fallacy_type": "hasty_generalization",
                "target_argument": "arg_3",
                "confidence": 0.5,
            },
        ]
        candidates = taxonomy_detections_to_candidates(
            detections, detector="hierarchical"
        )
        verdict = arbitrate_detections(candidates, dung_arbitration=True)
        assert verdict.honest_absent is False
        assert len(verdict.attacks) == 1
        survivor_id, eliminated_id = next(iter(verdict.attacks))
        eliminated = dict(verdict.eliminated_ids)
        assert eliminated_id in eliminated
        assert eliminated[eliminated_id] == "defeated_by_rival_candidate"
        assert verdict.surviving_count == 1
