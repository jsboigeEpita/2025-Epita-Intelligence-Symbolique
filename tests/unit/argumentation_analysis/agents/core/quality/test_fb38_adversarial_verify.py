"""FB-38 adversarial cross-verify (po-2023, independent of po-2025's own tests).

Role (per #1127 / coordinator R417): adversarially verify po-2025's FB-38
quality-axis verdict BEFORE it weighs on Epic #947 closure. po-2025 produced
the measurement; this file independently stress-tests the **no-inflation**
property that makes the measurement trustworthy.

The load-bearing claim under test
---------------------------------
po-2025 reports `pertinence` separates +0.516 vs the same-model 0-shot baseline
(the strongest content-separation in the FB-28/29/38 arc). That number is only
honest IF the agentic detector faithfully propagates the step3 LLM verdict —
i.e. it must NOT floor a low step3 score up to a higher bucket, nor mask a high
step3 score. If a floor-up existed, the separation could be an artefact of the
detector code tuning scores higher, not the LLM locating genuine structure.

Method (mirrors test_fb29_adversarial_verify.py)
------------------------------------------------
Each detector runs a 3-step chain (step1 decompose → step2 verify → step3 score).
po-2025's own tests use prompt-content-keyed stubs that COUPLE step3's score to
step2's verdict (digression→0.0, toutes_pertinentes→1.0) — a coherent chain.
That tests positive/negative matching, but does NOT isolate the inflation vector.

These probes use **call-order stubs** that DECOUPLE step3's score from the
verdict: steps 1-2 always return "strong/real" structure (so no early-return
gate fires), while step3 returns a CONTROLLED score (0.0 / 0.2 / 0.5 / 1.0)
regardless of the verdict. We then assert the detector returns EXACTLY that
controlled score. A floor-up would surface here as a returned score higher than
the controlled one.

Anti-theatre is also checked: the `exhibit` (the located structure a 0-shot
cannot emit) must be non-vacant in the returned comment.
"""

import json
from typing import Callable

import pytest

from argumentation_analysis.agents.core.quality.agentic_virtue_detectors import (
    detect_clarte_agentic,
    detect_pertinence_agentic,
    detect_structure_logique_agentic,
    detect_exhaustivite_agentic,
    detect_redondance_faible_agentic,
    AgenticDetectorError,
)


# ── Call-order stub factory ──────────────────────────────────────────────────
# Each detector calls the LLM exactly 3 times in sequence (step1, step2, step3).
# We discriminate by invocation count, NOT prompt content — this is what lets us
# hand step3 a score that CONTRADICTS the step2 verdict, the inflation probe.


def _make_order_stub(step1: dict, step2: dict, step3: dict) -> Callable[[str], str]:
    """Return a stub that emits step1/step2/step3 JSON by call order.

    Reset per closure (fresh counter per detector invocation). The ``step3``
    dict carries the CONTROLLED score we want to test for faithful propagation.
    """
    seq = [step1, step2, step3]
    counter = {"n": 0}

    def stub(prompt: str) -> str:
        i = counter["n"]
        counter["n"] += 1
        return json.dumps(seq[i] if i < len(seq) else seq[-1])

    return stub


# Per-detector "strong structure" step1/step2 payloads (so no early-return gate
# fires) — step3 is supplied per-probe with the controlled score.

_PERT_STEP1_STRONG = {
    "has_thesis": True,
    "thesis": "la thèse défendue est solide",
    "digressions": "",
}
_PERT_STEP2_STRONG = {
    "has_digression": False,
    "relevance_verdict": "toutes_pertinentes",
    "located_digression": "",
}

_CLARTE_STEP1_OBSTACLE = {  # has_clarity_obstacle=True → does NOT early-return 1.0
    "has_clarity_obstacle": True,
    "obstacles": "anaphore non résolvable",
}
_CLARTE_STEP2 = {"clarity_verdict": "opaque_réel"}

_STRUCT_STEP1_STRONG = {
    "has_chain": True,
    "premises": "les prémisses énoncées",
    "conclusion": "la conclusion déduite",
}
_STRUCT_STEP2_STRONG = {
    "chain_holds": True,
    "structure_verdict": "progression_logique",
    "reasoning": "la conclusion suit des prémisses",
}

_EXHAUST_STEP1 = {
    "subject": "le sujet traité",
    "expected_dimensions": "dimensions attendues",
}
_EXHAUST_STEP2 = {
    "coverage_verdict": "couverture_large",
    "missing_dimensions": "",
}

_REDOND_STEP1 = {"distinct_points": "1. point A; 2. point B; 3. point C"}
_REDOND_STEP2 = {
    "has_semantic_redundancy": False,
    "redundancy_verdict": "points_distincts",
    "located_redundancy": "",
}


def _step3(score: float, exhibit: str = "structure démontrée localisée") -> dict:
    return {"score": score, "exhibit": exhibit}


# ── No-upward-inflation probes (the load-bearing tests) ──────────────────────


class TestNoUpwardInflation:
    """A controlled LOW step3 score (with steps 1-2 saying 'real/strong') must
    propagate faithfully — no code-level floor-up. If these fail high, the
    pertinence +0.516 separation could be an inflation artefact."""

    # --- pertinence (the reported +0.516 separator — highest priority) ---

    def test_pertinence_zero_propagates_when_steps_say_strong(self):
        stub = _make_order_stub(
            _PERT_STEP1_STRONG, _PERT_STEP2_STRONG, _step3(0.0)
        )
        score, _ = detect_pertinence_agentic("text", llm=stub)
        assert score == 0.0, (
            "pertinence floored a 0.0 step3 score up — potential inflation "
            "(steps 1-2 said 'toutes_pertinentes' but step3 said 0.0)"
        )

    def test_pertinence_low_score_no_floor_up(self):
        stub = _make_order_stub(
            _PERT_STEP1_STRONG, _PERT_STEP2_STRONG, _step3(0.2)
        )
        score, _ = detect_pertinence_agentic("text", llm=stub)
        assert score == 0.2

    def test_pertinence_mid_score_propagates(self):
        stub = _make_order_stub(
            _PERT_STEP1_STRONG, _PERT_STEP2_STRONG, _step3(0.5)
        )
        score, _ = detect_pertinence_agentic("text", llm=stub)
        assert score == 0.5

    # --- clarte ---

    def test_clarte_zero_propagates_when_obstacle_present(self):
        stub = _make_order_stub(
            _CLARTE_STEP1_OBSTACLE, _CLARTE_STEP2, _step3(0.0)
        )
        score, _ = detect_clarte_agentic("text", llm=stub)
        assert score == 0.0

    def test_clarte_low_score_no_floor_up(self):
        stub = _make_order_stub(
            _CLARTE_STEP1_OBSTACLE, _CLARTE_STEP2, _step3(0.2)
        )
        score, _ = detect_clarte_agentic("text", llm=stub)
        assert score == 0.2

    # --- structure_logique ---

    def test_structure_zero_propagates_when_chain_present(self):
        stub = _make_order_stub(
            _STRUCT_STEP1_STRONG, _STRUCT_STEP2_STRONG, _step3(0.0)
        )
        score, _ = detect_structure_logique_agentic("text", llm=stub)
        assert score == 0.0

    def test_structure_low_score_no_floor_up(self):
        stub = _make_order_stub(
            _STRUCT_STEP1_STRONG, _STRUCT_STEP2_STRONG, _step3(0.2)
        )
        score, _ = detect_structure_logique_agentic("text", llm=stub)
        assert score == 0.2

    # --- exhaustivite ---

    def test_exhaustivite_zero_propagates(self):
        stub = _make_order_stub(
            _EXHAUST_STEP1, _EXHAUST_STEP2, _step3(0.0)
        )
        score, _ = detect_exhaustivite_agentic("text", llm=stub)
        assert score == 0.0

    def test_exhaustivite_low_score_no_floor_up(self):
        stub = _make_order_stub(
            _EXHAUST_STEP1, _EXHAUST_STEP2, _step3(0.2)
        )
        score, _ = detect_exhaustivite_agentic("text", llm=stub)
        assert score == 0.2

    # --- redondance_faible ---

    def test_redondance_zero_propagates_when_points_distinct(self):
        stub = _make_order_stub(
            _REDOND_STEP1, _REDOND_STEP2, _step3(0.0)
        )
        score, _ = detect_redondance_faible_agentic("text", llm=stub)
        assert score == 0.0

    def test_redondance_low_score_no_floor_up(self):
        stub = _make_order_stub(
            _REDOND_STEP1, _REDOND_STEP2, _step3(0.2)
        )
        score, _ = detect_redondance_faible_agentic("text", llm=stub)
        assert score == 0.2


class TestBidirectionalFidelity:
    """The mirror check: a controlled HIGH step3 score must ALSO propagate
    faithfully (not masked down). Confirms the detector uses step3 verbatim in
    BOTH directions — it is a pure pass-through of the LLM verdict, not a
    one-directional correction."""

    def test_pertinence_high_score_propagates(self):
        stub = _make_order_stub(
            _PERT_STEP1_STRONG, _PERT_STEP2_STRONG, _step3(1.0)
        )
        score, _ = detect_pertinence_agentic("text", llm=stub)
        assert score == 1.0

    def test_structure_high_score_propagates(self):
        stub = _make_order_stub(
            _STRUCT_STEP1_STRONG, _STRUCT_STEP2_STRONG, _step3(1.0)
        )
        score, _ = detect_structure_logique_agentic("text", llm=stub)
        assert score == 1.0

    def test_redondance_high_score_propagates(self):
        stub = _make_order_stub(
            _REDOND_STEP1, _REDOND_STEP2, _step3(1.0)
        )
        score, _ = detect_redondance_faible_agentic("text", llm=stub)
        assert score == 1.0


class TestExhibitNonVacant:
    """Anti-theatre (#1019): the `exhibit` (located structure a 0-shot cannot
    emit) must be embedded and non-empty in the returned comment — the
    content-separation evidence is real, not a bare score."""

    @pytest.mark.parametrize(
        "detect, s1, s2",
        [
            (detect_pertinence_agentic, _PERT_STEP1_STRONG, _PERT_STEP2_STRONG),
            (detect_clarte_agentic, _CLARTE_STEP1_OBSTACLE, _CLARTE_STEP2),
            (detect_structure_logique_agentic, _STRUCT_STEP1_STRONG, _STRUCT_STEP2_STRONG),
            (detect_exhaustivite_agentic, _EXHAUST_STEP1, _EXHAUST_STEP2),
            (detect_redondance_faible_agentic, _REDOND_STEP1, _REDOND_STEP2),
        ],
    )
    def test_exhibit_embedded_non_empty(self, detect, s1, s2):
        marker = "LOCATED_STRUCTURE_MARKER_X"
        stub = _make_order_stub(s1, s2, _step3(0.5, exhibit=marker))
        _, comment = detect("text", llm=stub)
        assert marker in comment, (
            f"{detect.__name__}: exhibit not embedded in comment — content-"
            f"separation evidence is vacant (theatre risk #1019)"
        )

    def test_pertinence_comment_carries_verdict(self):
        """The step2 verdict token must surface in the comment — proves the
        chain's verify-step output is retained, not discarded."""
        stub = _make_order_stub(
            _PERT_STEP1_STRONG, _PERT_STEP2_STRONG, _step3(0.5)
        )
        _, comment = detect_pertinence_agentic("text", llm=stub)
        assert "toutes_pertinentes" in comment


class TestFailLoudOnCorruptedStep:
    """Bounds the measurement against a corrupted chain. Two distinct cases:

    1. Non-numeric score (string / None / bool) → ``AgenticDetectorError``
       (fail-loud). A corrupted chain cannot quietly inject a fabricated score.
    2. Numeric but off-scale (e.g. 0.7) → snapped to the nearest scale value
       (0.7→0.5), NOT raised. This is a deliberate tolerance: the LLM is asked
       for strict {0.0,0.2,0.5,1.0} and mostly complies; minor imprecision is
       snapped rather than failing the whole chain. It is NOT an inflation
       vector because the head-to-head script applies the SAME ``_snap_to_scale``
       to the 0-shot baseline side (symmetric) — snapping cannot bias the
       pipe-vs-base differential."""

    def test_pertinence_nonscale_string_raises(self):
        stub = _make_order_stub(
            _PERT_STEP1_STRONG,
            _PERT_STEP2_STRONG,
            {"score": "high", "exhibit": "x"},  # string, not coercible
        )
        with pytest.raises(AgenticDetectorError):
            detect_pertinence_agentic("text", llm=stub)

    def test_structure_string_score_raises(self):
        stub = _make_order_stub(
            _STRUCT_STEP1_STRONG,
            _STRUCT_STEP2_STRONG,
            {"score": "high", "exhibit": "x"},  # string, not float
        )
        with pytest.raises(AgenticDetectorError):
            detect_structure_logique_agentic("text", llm=stub)

    def test_pertinence_midscale_snaps_symmetric(self):
        """0.7 (off-scale numeric) snaps to 0.5 (nearest) — tolerance, not
        fail-loud. Symmetric with the baseline's _snap_to_scale, so it cannot
        bias the pipe-vs-base measurement."""
        stub = _make_order_stub(
            _PERT_STEP1_STRONG,
            _PERT_STEP2_STRONG,
            {"score": 0.7, "exhibit": "x"},
        )
        score, _ = detect_pertinence_agentic("text", llm=stub)
        assert score == 0.5, f"0.7 should snap to 0.5, got {score}"

    def test_structure_bool_score_raises(self):
        """bool is an int subclass but must be rejected (True==1 would snap to
        1.0) — _snap_to_scale explicitly returns None for bool."""
        stub = _make_order_stub(
            _STRUCT_STEP1_STRONG,
            _STRUCT_STEP2_STRONG,
            {"score": True, "exhibit": "x"},
        )
        with pytest.raises(AgenticDetectorError):
            detect_structure_logique_agentic("text", llm=stub)
