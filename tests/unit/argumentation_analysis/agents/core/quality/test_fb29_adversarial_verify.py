"""FB-29 adversarial cross-verification (anti-self-confirmation) — po-2023 lane.

Companion to po-2025's ``test_agentic_virtue_detectors.py`` (PR #1106, #1105).
These tests were NOT written by the FB-29 author; they attack the specific
self-confirmation / theatre vector the R404b dispatch asked an independent eye
to check: **is the agentic chain tuned to score higher, or is it an honest
propagator of the LLM's verdict?**

The author's negative controls (strawman / surface ``comme X`` REJECT) prove the
detector refuses when the *LLM* says "no structure". They do NOT, by themselves,
prove the detector lacks an **upward bias** — i.e. that it would also faithfully
propagate a *low* score the LLM emits on a real-looking refutation. A detector
that floors low scores up, or inflates a 0.0 verdict, would still pass the
author's strawman test (which checks score==0.0) while being theatre on the
positive side.

These probes close that gap. They use a **call-order stub** (keys off the chain's
sequential step1→step2→step3 call sequence, NOT prompt-text markers) so they are
robust to prompt wording and genuinely independent of the author's fixtures.

DoD contract preserved: the LLM *dependency* is patched (the callable), not the
detector internals. The detector logic (chain, snap-to-scale, exhibit embedding)
is what runs and what is under test.

Findings recorded in ``docs/reports/FB29_ADVERSARIAL_VERIFY.md``.
"""

import json

from argumentation_analysis.agents.core.quality.agentic_virtue_detectors import (
    detect_analogie_pertinente_agentic as detect_analogy,
    detect_refutation_constructive_agentic as detect_refut,
)

# A text shaped like a real refutation — the stub ignores its content and
# returns a controlled chain, so any non-empty text works. We use a neutral
# stand-in (not the author's REAL_REFUTATION fixture) to stay fixture-independent.
_NEUTRAL_REFUTATION_TEXT = (
    "Certains soutiennent la thèse A. Nous contestons cette thèse pour des "
    "raisons précises, en adressant directement ses prémisses."
)
_NEUTRAL_ANALOGY_TEXT = (
    "Le mécanisme évoque un système connu : un domaine source éclaire un domaine "
    "cible par une correspondance structurelle."
)


def _refut_chain_stub(controlled_score: float):
    """Return a 'real refutation' chain (step1 real, step2 engagement_réel) but
    a CONTROLLED step3 score. Keys off call sequence (robust to prompt text)."""

    state = {"n": 0}

    def stub(prompt: str) -> str:
        state["n"] += 1
        if state["n"] == 1:  # step1 — claim an opposing claim IS present
            return json.dumps(
                {
                    "has_opposing_claim": True,
                    "opposing_claim": "la thèse adverse A",
                    "main_thesis": "la thèse adverse A est contestée",
                }
            )
        if state["n"] == 2:  # step2 — claim REAL engagement (not strawman)
            return json.dumps(
                {
                    "engages_real_claim": True,
                    "engagement_verdict": "engagement_réel",
                    "reasoning": "adresse la thèse adverse réelle",
                }
            )
        # step3 — CONTROLLED score (the variable under test)
        return json.dumps(
            {"score": controlled_score, "exhibit": "chaîne contrôlée (sondage d'inflation)"}
        )

    return stub


def _analogy_chain_stub(controlled_score: float):
    """Return a 'real analogy' chain (step1 domains, step2 structural mapping)
    but a CONTROLLED step3 score."""

    state = {"n": 0}

    def stub(prompt: str) -> str:
        state["n"] += 1
        if state["n"] == 1:
            return json.dumps(
                {
                    "has_analogy": True,
                    "source_domain": "domaine source",
                    "target_domain": "domaine cible",
                }
            )
        if state["n"] == 2:
            return json.dumps(
                {
                    "has_structural_mapping": True,
                    "mapping": "correspondance structurelle contrôlée",
                    "reasoning": "mapping non-surface",
                }
            )
        return json.dumps(
            {"score": controlled_score, "exhibit": "chaîne contrôlée (sondage d'inflation)"}
        )

    return stub


class TestNoUpwardInflation:
    """The detector MUST faithfully propagate a LOW / ZERO score the LLM emits,
    even when the upstream steps (step1/step2) report a fully-real refutation.
    A detector that inflates 0.0→higher or floors low scores up is theatre
    (the exact 'chain tuned to score higher' vector)."""

    def test_refut_zero_score_propagates_when_steps_say_real(self):
        """step1=real, step2=engagement_réel, but step3=0.0 → detector MUST
        return 0.0. Proves no upward override of a zero verdict."""
        score, comment = detect_refut(
            _NEUTRAL_REFUTATION_TEXT, llm=_refut_chain_stub(0.0)
        )
        assert score == 0.0, (
            f"INFLATION DETECTED: step1/step2 said 'real refutation' but step3 "
            f"scored 0.0 — detector returned {score} instead of honoring the 0.0. "
            "The chain would be theatre (upward override of a zero verdict)."
        )

    def test_refut_low_score_propagates_no_floor_up(self):
        """step3=0.2 (trace) → detector MUST return 0.2, NOT 1.0 or 0.5."""
        score, _ = detect_refut(_NEUTRAL_REFUTATION_TEXT, llm=_refut_chain_stub(0.2))
        assert score == 0.2, (
            f"INFLATION DETECTED: LLM step3 score was 0.2 but detector returned "
            f"{score} — the chain inflates a trace score upward (theatre)."
        )

    def test_refut_mid_score_propagates(self):
        """step3=0.5 → detector MUST return 0.5 (faithful mid propagation)."""
        score, _ = detect_refut(_NEUTRAL_REFUTATION_TEXT, llm=_refut_chain_stub(0.5))
        assert score == 0.5

    def test_analogy_zero_score_propagates_when_steps_say_real(self):
        """Analogous inflation probe for the analogy chain: step1=domains,
        step2=structural mapping, but step3=0.0 → MUST return 0.0."""
        score, _ = detect_analogy(
            _NEUTRAL_ANALOGY_TEXT, llm=_analogy_chain_stub(0.0)
        )
        assert score == 0.0, (
            f"INFLATION DETECTED (analogy): upstream said 'real analogy' but "
            f"step3=0.0 — detector returned {score} instead of 0.0."
        )

    def test_analogy_low_score_propagates_no_floor_up(self):
        score, _ = detect_analogy(_NEUTRAL_ANALOGY_TEXT, llm=_analogy_chain_stub(0.2))
        assert score == 0.2


class TestExhibitEmbedsControlledStructure:
    """The exhibit (demonstrated structure) must embed the step2 verdict + the
    controlled score, so a reviewer can audit what the chain actually located —
    not a generic 'refutation detected'. This is the content-separation
    artifact a 0-shot call does not emit."""

    def test_refut_exhibit_embeds_verdict_and_score(self):
        score, comment = detect_refut(
            _NEUTRAL_REFUTATION_TEXT, llm=_refut_chain_stub(0.5)
        )
        assert score == 0.5
        # The comment must carry the located opposing claim + verdict + score
        # so the exhibited structure is auditable, not a bare number.
        assert "engagement_réel" in comment
        assert "score=0.5" in comment
