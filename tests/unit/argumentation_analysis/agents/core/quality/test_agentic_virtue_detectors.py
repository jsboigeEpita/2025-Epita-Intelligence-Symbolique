"""Load-bearing tests for agentic multi-step virtue detectors (FB-29 #1105).

Target: argumentation_analysis/agents/core/quality/agentic_virtue_detectors.py
        + the agentic upgrade path in quality_evaluator.evaluate(agentic_llm=...).

DoD contract (FB-29 #1105): the LLM dependency is patched (NOT the detector
internals), and a **negative control is mandatory** — a planted
pseudo-refutation / surface ``comme X`` non-analogy MUST be rejected. A
detector that scores everything high is theatre (FB-28 §4 stricter≠better).

The stub LLM is **context-sensitive**: it inspects the planted text embedded in
each chain-step prompt and returns the structurally-correct verdict. This
mirrors what a real LLM does, and makes the test load-bearing rather than
tautological (cf. the #1100 modal-gate bug where the test patched the function
itself). The discrimination lives in the LLM verdict; the detector's job is to
propagate it faithfully into a score + exhibit.
"""

import json

import pytest

from argumentation_analysis.agents.core.quality.agentic_virtue_detectors import (
    AgenticDetectorError,
    detect_analogie_pertinente_agentic,
    detect_refutation_constructive_agentic,
    detect_refutation_constructive_agentic as detect_refut,
    detect_analogie_pertinente_agentic as detect_analogy,
)
from argumentation_analysis.agents.core.quality import agentic_virtue_detectors as avd


# ---------------------------------------------------------------------------
# Context-sensitive stub LLMs
#
# Each stub reads the planted text from the prompt and returns the verdict a
# competent analyst would. Steps are distinguished by their prompt signature
# (step1 = "Étape 1", step2 = "Étape 2", step3 = the scoring prompt).
# ---------------------------------------------------------------------------

def _which_step(prompt: str) -> str:
    """Identify which chain step a prompt is asking (by its signature marker)."""
    if "Étape 3" in prompt or "Score la qualité" in prompt or "Score la pertinence" in prompt:
        return "step3"
    if "Étape 2" in prompt:
        return "step2"
    return "step1"


def _make_refut_stub(real_keywords, pseudo_keywords):
    """Build a context-sensitive stub for the refutation chain.

    The stub classifies the planted text: if it contains a real opposing claim
    (engages it genuinely) it returns a high-score chain; if it contains a
    strawman/pseudo-refutation it returns a reject chain. This is the
    discrimination the negative control demands.

    NB on step3: the scoring prompt embeds the step2 verdict ({prev_step2}) but
    NOT the raw {arg_text} — that is by design (step3 scores from the verdict,
    not by re-reading the argument). So step3 keys off the verdict text present
    in its prompt, faithfully testing that step3 maps verdict→score.
    """

    def stub(prompt: str) -> str:
        step = _which_step(prompt)
        lower = prompt.lower()
        is_real = any(k.lower() in lower for k in real_keywords)
        is_pseudo = any(k.lower() in lower for k in pseudo_keywords)
        if step == "step1":
            if is_real:
                return json.dumps({
                    "has_opposing_claim": True,
                    "opposing_claim": "la thèse adverse que X suffit",
                    "main_thesis": "X ne suffit pas",
                })
            if is_pseudo:
                return json.dumps({
                    "has_opposing_claim": True,
                    "opposing_claim": "prétention absurde que personne ne défend",
                    "main_thesis": "notre position",
                })
            return json.dumps({"has_opposing_claim": False, "opposing_claim": "", "main_thesis": ""})
        if step == "step2":
            if is_real:
                return json.dumps({
                    "engages_real_claim": True,
                    "engagement_verdict": "engagement_réel",
                    "reasoning": "adresse la thèse adverse réelle",
                })
            if is_pseudo:
                return json.dumps({
                    "engages_real_claim": False,
                    "engagement_verdict": "homme_de_paille",
                    "reasoning": "attaque une position déformée",
                })
            return json.dumps({"engages_real_claim": False, "engagement_verdict": "non_sequitur", "reasoning": ""})
        # step3 — key off the verdict carried from step2 (no raw arg_text here).
        # Use the UNDERSCORE form only: the rubric prose contains the space-form
        # ("engagement réel", "homme de paille") in its scoring description, so
        # the space-form would match the rubric for EVERY input. The underscore
        # verdict token ("engagement_réel" / "homme_de_paille") is the actual
        # step2 output value and is NOT in the rubric — it discriminates.
        if "engagement_réel" in lower:
            return json.dumps({"score": 1.0, "exhibit": "position adverse identifiée + engagement réel"})
        if "homme_de_paille" in lower:
            return json.dumps({"score": 0.0, "exhibit": "homme de paille rejeté"})
        return json.dumps({"score": 0.0, "exhibit": "pas de réfutation"})

    return stub


def _make_analogy_stub(real_keywords, surface_keywords):
    """Build a context-sensitive stub for the analogy chain.

    step3 keys off the mapping verdict carried from step2 (no raw arg_text in
    the scoring prompt) — see _make_refut_stub NB.
    """

    def stub(prompt: str) -> str:
        step = _which_step(prompt)
        lower = prompt.lower()
        is_real = any(k.lower() in lower for k in real_keywords)
        is_surface = any(k.lower() in lower for k in surface_keywords)
        if step == "step1":
            if is_real or is_surface:
                return json.dumps({
                    "has_analogy": True,
                    "source_domain": "le vivant",
                    "target_domain": "la société",
                })
            return json.dumps({"has_analogy": False, "source_domain": "", "target_domain": ""})
        if step == "step2":
            if is_real:
                return json.dumps({
                    "has_structural_mapping": True,
                    "mapping": "interdépendance des organes ↔ interdépendance des groupes",
                    "reasoning": "correspondance structurelle",
                })
            if is_surface:
                return json.dumps({
                    "has_structural_mapping": False,
                    "mapping": "surface_seule",
                    "reasoning": "comparaison sans profondeur",
                })
            return json.dumps({"has_structural_mapping": False, "mapping": "surface_seule", "reasoning": ""})
        # step3 — key off the mapping carried from step2. "interdépendance" is
        # the distinctive step2 real-mapping token (the rubric says
        # "correspondance structurelle", which would match every input). The
        # underscore "surface_seule" is the step2 surface verdict (rubric uses
        # the space-form "surface seule").
        if "interdépendance" in lower:
            return json.dumps({"score": 1.0, "exhibit": "domaines + mapping structurel"})
        if "surface_seule" in lower:
            return json.dumps({"score": 0.0, "exhibit": "surface seule rejetée"})
        return json.dumps({"score": 0.0, "exhibit": "pas d'analogie"})

    return stub


# ---------------------------------------------------------------------------
# Planted texts
# ---------------------------------------------------------------------------

REAL_REFUTATION = (
    "Certains affirment que la croissance économique suffit à résoudre le chômage. "
    "Cependant, cette thèse ignore que sans formation, les créations d'emplois ne "
    "profitent pas aux non-qualifiés : l'engagement porte bien sur la causalité "
    'croissance-emploi, et non sur un effet marginal.'
)

PSEUDO_REFUTATION = (  # strawman — attacks a distorted claim, must REJECT
    "Les partisans de la réglementation veulent interdire toute liberté. "
    "C'est absurde : personne ne soutient cela. Nous défendons le bon sens "
    "contre cette prétention ridicule d'interdiction totale."
)

REAL_ANALOGY = (
    "La société fonctionne comme un organisme vivant : de même que les organes "
    "sont interdépendants et que chacun remplit une fonction nécessaire au tout, "
    "les groupes sociaux se sustentent mutuellement par la division du travail."
)

SURFACE_ANALOGY = (  # surface "comme X" with no structural mapping — must REJECT
    "C'est comme une voiture. La politique, c'est comme conduire, en quelque sorte."
)

SOURCE_LIGHT_TEXT = (  # neither refutation nor analogy — should score 0.0 measured
    "La météo d'aujourd'hui est clémente. Les oiseaux chantent dans les arbres."
)


# ---------------------------------------------------------------------------
# Refutation detector — positive + negative control
# ---------------------------------------------------------------------------

class TestRefutationConstructiveAgentic:
    """Positive control (real refutation MATCHes) + negative control (strawman
    REJECTs). Both are mandatory per FB-29 DoD."""

    def test_real_refutation_matches_high_score(self):
        stub = _make_refut_stub(
            real_keywords=["croissance économique suffit", "cependant, cette thèse"],
            pseudo_keywords=["interdire toute liberté"],
        )
        score, comment = detect_refut(REAL_REFUTATION, llm=stub)
        assert score == 1.0, f"real refutation should MATCH (high), got {score}"
        # exhibit embeds the LOCATED opposing claim — the demonstrated structure
        # a 0-shot call does not surface. That exhibit is the content-separation.
        assert "croissance économique suffit" in comment.lower() or "position adverse" in comment.lower()
        assert "engagement_réel" in comment

    def test_strawman_refutation_rejected_negative_control(self):
        """Negative control (mandatory): a strawman MUST be rejected, not
        scored high. A detector that scores a strawman as 1.0 is theatre."""
        stub = _make_refut_stub(
            real_keywords=["croissance économique suffit"],
            pseudo_keywords=["interdire toute liberté", "prétention ridicule"],
        )
        score, comment = detect_refut(PSEUDO_REFUTATION, llm=stub)
        assert score == 0.0, (
            f"NEGATIVE CONTROL FAILED: strawman must REJECT (0.0), got {score}. "
            "Detector scored a pseudo-refutation as if real — theatre (#1019)."
        )
        assert "homme_de_paille" in comment

    def test_no_refutation_measured_zero(self):
        """Text with no opposing claim → measured 0.0 (not a synthetic fallback).
        The comment must say 'Aucune position adverse' (step1 ran, found nothing)."""
        stub = _make_refut_stub(real_keywords=[], pseudo_keywords=[])
        score, comment = detect_refut(SOURCE_LIGHT_TEXT, llm=stub)
        assert score == 0.0
        assert "aucune position adverse" in comment.lower()

    def test_no_llm_raises_fail_loud(self):
        """No LLM callable wired → AgenticDetectorError (fail-loud per DoD),
        NEVER a synthetic 0.0 'as if measured'."""
        with pytest.raises(AgenticDetectorError, match="no LLM callable"):
            detect_refut(REAL_REFUTATION, llm=None)

    def test_unparseable_llm_output_raises(self):
        """Garbage LLM output → AgenticDetectorError (fail-loud), not a silent 0.0."""
        def garbage_stub(prompt: str) -> str:
            return "this is not json at all, sorry"

        with pytest.raises(AgenticDetectorError, match="unparseable"):
            detect_refut(REAL_REFUTATION, llm=garbage_stub)

    def test_llm_transport_error_raises(self):
        """LLM callable raising → AgenticDetectorError (fail-loud)."""
        def raising_stub(prompt: str) -> str:
            raise ConnectionError("429 rate limited")

        with pytest.raises(AgenticDetectorError, match="LLM callable raised"):
            detect_refut(REAL_REFUTATION, llm=raising_stub)


# ---------------------------------------------------------------------------
# Analogy detector — positive + negative control
# ---------------------------------------------------------------------------

class TestAnalogiePertinenteAgentic:
    def test_real_analogy_matches_high_score(self):
        stub = _make_analogy_stub(
            real_keywords=["organisme vivant", "interdépendants", "division du travail"],
            surface_keywords=["comme une voiture"],
        )
        score, comment = detect_analogy(REAL_ANALOGY, llm=stub)
        assert score == 1.0, f"real analogy should MATCH (high), got {score}"
        assert "source=" in comment and "target=" in comment
        assert "mapping" in comment.lower()

    def test_surface_analogy_rejected_negative_control(self):
        """Negative control (mandatory): a surface 'comme X' with NO structural
        mapping MUST be rejected. Scoring it high = the FB-28 §4 blindspot."""
        stub = _make_analogy_stub(
            real_keywords=["organisme vivant"],
            surface_keywords=["comme une voiture", "comme conduire"],
        )
        score, comment = detect_analogy(SURFACE_ANALOGY, llm=stub)
        assert score == 0.0, (
            f"NEGATIVE CONTROL FAILED: surface 'comme X' must REJECT (0.0), "
            f"got {score}. Detector scored a non-analogy as if pertinent — "
            "theatre (#1019)."
        )
        assert "surface_seule" in comment or "surface seule" in comment.lower()

    def test_no_analogy_measured_zero(self):
        stub = _make_analogy_stub(real_keywords=[], surface_keywords=[])
        score, comment = detect_analogy(SOURCE_LIGHT_TEXT, llm=stub)
        assert score == 0.0
        assert "aucune analogie" in comment.lower()

    def test_no_llm_raises_fail_loud(self):
        with pytest.raises(AgenticDetectorError, match="no LLM callable"):
            detect_analogy(REAL_ANALOGY, llm=None)


# ---------------------------------------------------------------------------
# Evaluator integration — agentic upgrade path + fail-loud propagation
# ---------------------------------------------------------------------------

class TestEvaluatorAgenticUpgrade:
    """The evaluator must: (a) use agentic detectors when an LLM is wired,
    (b) stay lexical without one (backwards-compat), (c) propagate
    AgenticDetectorError (fail-loud), (d) NOT swallow it into 0.0."""

    def test_agentic_llm_uses_agentic_detector(self, monkeypatch):
        """With agentic_llm wired, refutation_constructive routes to the
        agentic 3-step chain (not the lexical marker grep)."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            ArgumentQualityEvaluator,
        )

        called = {"refut_chain": False}

        def stub_chain(text, llm=None):
            called["refut_chain"] = True
            return 0.5, "agentic chain ran"

        monkeypatch.setitem(
            avd.AGENTIC_DETECTORS, "refutation_constructive", stub_chain
        )
        # Avoid the spacy/textstat hard dependency for this unit test: bypass
        # the deps gate by marking them available. The 7 lexical detectors are
        # not under test here; only the routing is.
        import argumentation_analysis.agents.core.quality.quality_evaluator as qe

        monkeypatch.setattr(qe, "_DEPS_ATTEMPTED", True)
        monkeypatch.setattr(qe, "_DEPS_AVAILABLE", True)

        ev = ArgumentQualityEvaluator()
        result = ev.evaluate(REAL_REFUTATION, agentic_llm=lambda p: "{}")
        assert called["refut_chain"] is True
        assert result["scores_par_vertu"]["refutation_constructive"] == 0.5

    def test_no_agentic_llm_stays_lexical(self, monkeypatch):
        """Without agentic_llm, the lexical detector runs (backwards-compat)."""
        import argumentation_analysis.agents.core.quality.quality_evaluator as qe

        monkeypatch.setattr(qe, "_DEPS_ATTEMPTED", True)
        monkeypatch.setattr(qe, "_DEPS_AVAILABLE", True)

        called = {"lexical": False}
        original = qe.detect_refutation_constructive

        def spy(text):
            called["lexical"] = True
            return original(text)

        monkeypatch.setattr(qe, "detect_refutation_constructive", spy)
        # Also patch the registry entry the evaluator iterates, since it holds
        # the original function reference.
        monkeypatch.setitem(
            qe.DETECTORS, "refutation_constructive", spy
        )

        ev = qe.ArgumentQualityEvaluator()
        ev.evaluate(REAL_REFUTATION)  # no agentic_llm
        assert called["lexical"] is True

    def test_agentic_error_propagates_fail_loud(self, monkeypatch):
        """AgenticDetectorError raised by the chain MUST propagate (not be
        swallowed into 0.0+'Erreur'). This is the DoD fail-loud contract."""
        import argumentation_analysis.agents.core.quality.quality_evaluator as qe

        monkeypatch.setattr(qe, "_DEPS_ATTEMPTED", True)
        monkeypatch.setattr(qe, "_DEPS_AVAILABLE", True)

        def raising_chain(text, llm=None):
            raise AgenticDetectorError("simulated chain failure")

        monkeypatch.setitem(
            avd.AGENTIC_DETECTORS, "refutation_constructive", raising_chain
        )

        ev = qe.ArgumentQualityEvaluator()
        with pytest.raises(AgenticDetectorError, match="simulated chain failure"):
            ev.evaluate(REAL_REFUTATION, agentic_llm=lambda p: "{}")
