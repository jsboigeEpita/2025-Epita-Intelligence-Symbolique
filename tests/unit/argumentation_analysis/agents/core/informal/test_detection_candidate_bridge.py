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
