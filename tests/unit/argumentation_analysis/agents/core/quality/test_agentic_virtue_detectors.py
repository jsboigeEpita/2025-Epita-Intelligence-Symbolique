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
    detect_clarte_agentic as detect_clarte,
    detect_pertinence_agentic as detect_pertinence,
    detect_structure_logique_agentic as detect_structure,
    detect_exhaustivite_agentic as detect_exhaust,
    detect_redondance_faible_agentic as detect_redond,
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
    """Identify which chain step a prompt is asking (by its signature marker).

    FB-29 step3 prompts open with "Score la qualité/pertinence"; FB-38 step3
    prompts open with "Score la clarté/...". The robust universal step3 signal:
    every step3 prompt embeds the ``"exhibit":`` JSON key, which no step1/step2
    does. (The step2 verdict tokens are underscore-form precisely so step3 can
    discriminate them from the rubric prose — see the detectors' module docstring.)
    """
    if (
        "Étape 3" in prompt
        or '"exhibit"' in prompt
        or "Score la qualité" in prompt
        or "Score la pertinence" in prompt
    ):
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
# FB-38 #1127 — the 5 remaining tractable virtues, agentic
#
# Same context-sensitive-stub pattern: step1/step2 classify the planted text;
# step3 keys off the verdict token carried from step2 (underscore-form, NOT in
# the rubric prose). Each negative control is a text where the LEXICAL detector
# gives a FALSE-POSITIVE high score (the agentic chain must REJECT) — that
# discrimination is the content-separation claim, not the score itself.
# ---------------------------------------------------------------------------


def _make_clarte_stub(jargon_keywords):
    """clarté stub: jargon (short words, unresolvable) must REJECT; clear text
    scores high. The lexical Flesch detector would score jargon HIGH on short
    words — the negative control."""
    def stub(prompt: str) -> str:
        step = _which_step(prompt)
        lower = prompt.lower()
        is_jargon = any(k.lower() in lower for k in jargon_keywords)
        if step == "step1":
            if is_jargon:
                return json.dumps({"has_clarity_obstacle": True, "obstacles": "jargon technique non défini (Q-GERT, TLN)"})
            return json.dumps({"has_clarity_obstacle": False, "obstacles": ""})
        if step == "step2":
            if is_jargon:
                return json.dumps({"obstacle_genuinely_opaque": True, "clarity_verdict": "opaque_réel", "reasoning": "jargon non résolvable"})
            return json.dumps({"obstacle_genuinely_opaque": False, "clarity_verdict": "aucun_obstacle", "reasoning": ""})
        if "opaque_réel" in lower:
            return json.dumps({"score": 0.0, "exhibit": "jargon opaque localisé"})
        if "résolvable_contexte" in lower:
            return json.dumps({"score": 0.5, "exhibit": "obstacle résolvable"})
        return json.dumps({"score": 1.0, "exhibit": "aucun obstacle"})

    return stub


def _make_pertinence_stub(digression_keywords):
    """pertinence stub: a digression (even with connectors) must REJECT; focused
    text scores high. The lexical connector-count would score a digressive text
    HIGH — the negative control."""
    def stub(prompt: str) -> str:
        step = _which_step(prompt)
        lower = prompt.lower()
        is_digression = any(k.lower() in lower for k in digression_keywords)
        if step == "step1":
            return json.dumps({
                "has_thesis": True,
                "thesis": "la thèse défendue",
                "digressions": "aparté sur le chat" if is_digression else "",
            })
        if step == "step2":
            if is_digression:
                return json.dumps({"has_digression": True, "relevance_verdict": "digression_localisée", "located_digression": "aparté hors-sujet"})
            return json.dumps({"has_digression": False, "relevance_verdict": "toutes_pertinentes", "located_digression": ""})
        if "digression_localisée" in lower:
            return json.dumps({"score": 0.0, "exhibit": "digression localisée"})
        if "toutes_pertinentes" in lower:
            return json.dumps({"score": 1.0, "exhibit": "toutes pertinentes"})
        return json.dumps({"score": 0.5, "exhibit": "pertinence partielle"})

    return stub


def _make_structure_stub(real_keywords, saut_keywords):
    """structure_logique stub: an enumeration with rhetorical 'donc' but no
    inference (saut logique) must REJECT; a real premise→conclusion scores high.
    The lexical connector-count would score the saut HIGH — the negative control."""
    def stub(prompt: str) -> str:
        step = _which_step(prompt)
        lower = prompt.lower()
        is_real = any(k.lower() in lower for k in real_keywords)
        is_saut = any(k.lower() in lower for k in saut_keywords)
        if step == "step1":
            return json.dumps({
                "has_chain": True,
                "premises": "prémisses identifiées",
                "conclusion": "conclusion",
            })
        if step == "step2":
            if is_real:
                return json.dumps({"chain_holds": True, "structure_verdict": "progression_logique", "reasoning": "inférence réelle"})
            if is_saut:
                return json.dumps({"chain_holds": False, "structure_verdict": "saut_logique", "reasoning": "la conclusion ne découle pas des prémisses"})
            return json.dumps({"chain_holds": False, "structure_verdict": "énumération_sans_lien", "reasoning": ""})
        if "progression_logique" in lower:
            return json.dumps({"score": 1.0, "exhibit": "chaîne prémisse→conclusion tenue"})
        if "saut_logique" in lower:
            return json.dumps({"score": 0.0, "exhibit": "saut logique rejeté"})
        if "énumération_sans_lien" in lower:
            return json.dumps({"score": 0.0, "exhibit": "énumération sans lien rejetée"})
        return json.dumps({"score": 0.5, "exhibit": "structure partielle"})

    return stub


def _make_exhaust_stub(broad_keywords, mono_keywords):
    """exhaustivité stub: a long but monodimensional text must REJECT; broad
    coverage scores high. The lexical sentence-count would score a long
    monodimensional text HIGH — the negative control."""
    def stub(prompt: str) -> str:
        step = _which_step(prompt)
        lower = prompt.lower()
        is_broad = any(k.lower() in lower for k in broad_keywords)
        is_mono = any(k.lower() in lower for k in mono_keywords)
        if step == "step1":
            return json.dumps({"subject": "le sujet", "expected_dimensions": "efficacité, coût, équité, faisabilité"})
        if step == "step2":
            if is_broad:
                return json.dumps({"covered_dimensions": "plusieurs dimensions", "missing_dimensions": "", "coverage_verdict": "couverture_large"})
            if is_mono:
                return json.dumps({"covered_dimensions": "efficacité seule", "missing_dimensions": "coût, équité, faisabilité absents", "coverage_verdict": "monodimensionnel_seul"})
            return json.dumps({"covered_dimensions": "", "missing_dimensions": "", "coverage_verdict": "couverture_partielle"})
        if "couverture_large" in lower:
            return json.dumps({"score": 1.0, "exhibit": "couverture large des dimensions"})
        if "monodimensionnel_seul" in lower:
            return json.dumps({"score": 0.0, "exhibit": "monodimensionnel rejeté"})
        if "couverture_partielle" in lower:
            return json.dumps({"score": 0.5, "exhibit": "couverture partielle"})
        return json.dumps({"score": 0.2, "exhibit": "couverture faible"})

    return stub


def _make_redond_stub(distinct_keywords, redundant_keywords):
    """redondance_faible stub: semantic restatement (same idea, varied words)
    must REJECT; genuinely distinct points score high. The lexical unique-word
    ratio would score a varied-word restatement HIGH (low redundancy) — the
    negative control."""
    def stub(prompt: str) -> str:
        step = _which_step(prompt)
        lower = prompt.lower()
        is_distinct = any(k.lower() in lower for k in distinct_keywords)
        is_redundant = any(k.lower() in lower for k in redundant_keywords)
        if step == "step1":
            return json.dumps({"distinct_points": "points identifiés"})
        if step == "step2":
            if is_distinct:
                return json.dumps({"has_semantic_redundancy": False, "redundancy_verdict": "points_distincts", "located_redundancy": ""})
            if is_redundant:
                return json.dumps({"has_semantic_redundancy": True, "redundancy_verdict": "redondance_sémantique", "located_redundancy": "même idée reformulée"})
            return json.dumps({"has_semantic_redundancy": False, "redundancy_verdict": "reformulation_utile", "located_redundancy": ""})
        if "points_distincts" in lower:
            return json.dumps({"score": 1.0, "exhibit": "points réellement distincts"})
        if "redondance_sémantique" in lower:
            return json.dumps({"score": 0.0, "exhibit": "redondance sémantique rejetée"})
        if "reformulation_utile" in lower:
            return json.dumps({"score": 0.5, "exhibit": "reformulation utile"})
        return json.dumps({"score": 0.2, "exhibit": "redondance notable"})

    return stub


# --- Planted texts (FB-38) ---

CLEAR_TEXT = (  # no clarity obstacle → measured 1.0
    "La photosynthèse convertit l'énergie solaire en énergie chimique. "
    "Les plantes utilisent ce processus pour produire leur propre nourriture."
)
JARGON_TEXT = (  # short words but unresolvable jargon → Flesch false-positive HIGH, agentic REJECT
    "Le Q-GERT module le TLN via le protocole X-47. C'est crucial pour le résultat final obtenu."
)
RELEVANT_TEXT = (  # focused argument, all propositions serve the thesis
    "La fiscalité écologique réduit les émissions carbone. En effet, taxer les "
    "pollueurs modifie les comportements industriels vers des pratiques plus propres, "
    "ce qui baisse durablement l'empreinte carbone du pays."
)
DIGRESSIVE_TEXT = (  # connectors + a clear digression → connector-count false-positive HIGH
    "Nous devons réduire la dette publique. En effet, la dette étouffe l'économie. "
    "Par ailleurs, mon chat est roux et dort beaucoup. Donc, la rigueur budgétaire s'impose."
)
CHAINED_TEXT = (  # real premise→conclusion inference
    "Tous les mammifères possèdent un cœur. La baleine est un mammifère. "
    "Donc, la baleine possède un cœur."
)
ENUMERATION_TEXT = (  # points + 'donc' but the conclusion doesn't follow → saut logique
    "Il pleut. La route est mouillée. Donc, la politique monétaire doit changer radicalement."
)
BROAD_TEXT = (  # covers multiple dimensions of the subject
    "Sur la réforme fiscale, il faut juger l'efficacité économique, le coût pour les "
    "ménages, l'équité sociale et la faisabilité politique."
)
MONODIM_TEXT = (  # long, many sentences, but ONE dimension only → sentence-count false-positive HIGH
    "Ce médicament est efficace. Son efficacité est prouvée par des essais cliniques. "
    "Les patients guérissent vite grâce à lui. Le taux de guérison est élevé. "
    "Son efficacité dépasse largement celle des alternatives disponibles."
)
DISTINCT_TEXT = (  # genuinely distinct points
    "Premièrement, la mesure réduit les inégalités. Deuxièmement, elle encourage "
    "l'innovation technique. Troisièmement, elle renforce la souveraineté du pays."
)
SEMANTIC_RESTATEMENT_TEXT = (  # same idea, varied words → unique-word-ratio false-positive HIGH
    "Il faut investir dans l'éducation. Nos écoles méritent davantage de moyens. "
    "L'enseignement doit rester une priorité budgétaire. Former notre jeunesse est un impératif national."
)


# --- FB-38 detector tests (positive + negative-control + fail-loud each) ---

class TestClarteAgentic:
    def test_clear_text_measured_high(self):
        stub = _make_clarte_stub(jargon_keywords=["q-gert"])
        score, comment = detect_clarte(CLEAR_TEXT, llm=stub)
        assert score == 1.0, f"clear text should score high, got {score}"
        assert "aucun obstacle" in comment.lower()

    def test_jargon_rejected_negative_control(self):
        """Negative control: unresolvable jargon (short words) must REJECT. A
        lexical Flesch detector would score it HIGH — the agentic chain locates
        the obstacle and rejects. Scoring it high = theatre (#1019)."""
        stub = _make_clarte_stub(jargon_keywords=["q-gert", "tln", "x-47"])
        score, comment = detect_clarte(JARGON_TEXT, llm=stub)
        assert score == 0.0, (
            f"NEGATIVE CONTROL FAILED: unresolvable jargon must REJECT (0.0), "
            f"got {score}. Flesch scores short-word jargon high — theatre."
        )
        assert "opaque_réel" in comment

    def test_no_llm_raises_fail_loud(self):
        with pytest.raises(AgenticDetectorError, match="no LLM callable"):
            detect_clarte(CLEAR_TEXT, llm=None)


class TestPertinenceAgentic:
    def test_relevant_text_matches_high(self):
        stub = _make_pertinence_stub(digression_keywords=["chat", "dort"])
        score, comment = detect_pertinence(RELEVANT_TEXT, llm=stub)
        assert score == 1.0, f"focused text should score high, got {score}"
        assert "toutes_pertinentes" in comment

    def test_digression_rejected_negative_control(self):
        """Negative control: connectors + a digression must REJECT. A lexical
        connector-count would score it HIGH (many connectors) — the agentic
        chain locates the digression."""
        stub = _make_pertinence_stub(digression_keywords=["chat", "dort"])
        score, comment = detect_pertinence(DIGRESSIVE_TEXT, llm=stub)
        assert score == 0.0, (
            f"NEGATIVE CONTROL FAILED: digression must REJECT (0.0), got {score}. "
            "Connector-count would score a digressive text high — theatre."
        )
        assert "digression_localisée" in comment

    def test_no_thesis_measured_zero(self):
        """No thesis identified → measured 0.0 (the gate short-circuits)."""
        def no_thesis_stub(prompt: str) -> str:
            if _which_step(prompt) == "step1":
                return json.dumps({"has_thesis": False, "thesis": "", "digressions": ""})
            return json.dumps({})

        score, comment = detect_pertinence(SOURCE_LIGHT_TEXT, llm=no_thesis_stub)
        assert score == 0.0
        assert "aucune thèse" in comment.lower()

    def test_no_llm_raises_fail_loud(self):
        with pytest.raises(AgenticDetectorError, match="no LLM callable"):
            detect_pertinence(RELEVANT_TEXT, llm=None)


class TestStructureLogiqueAgentic:
    def test_real_chain_matches_high(self):
        stub = _make_structure_stub(real_keywords=["mammifères", "baleine"], saut_keywords=["politique monétaire"])
        score, comment = detect_structure(CHAINED_TEXT, llm=stub)
        assert score == 1.0, f"real premise→conclusion should score high, got {score}"
        assert "progression_logique" in comment

    def test_enumeration_saut_rejected_negative_control(self):
        """Negative control: points + rhetorical 'donc' but no inference (saut
        logique) must REJECT. A lexical connector-count would score it HIGH —
        the agentic chain verifies the inference and rejects the gap."""
        stub = _make_structure_stub(real_keywords=["mammifères"], saut_keywords=["politique monétaire", "pleut"])
        score, comment = detect_structure(ENUMERATION_TEXT, llm=stub)
        assert score == 0.0, (
            f"NEGATIVE CONTROL FAILED: saut logique must REJECT (0.0), got {score}. "
            "Connector-count would score an enumeration with 'donc' high — theatre."
        )
        assert "saut_logique" in comment or "énumération_sans_lien" in comment

    def test_no_chain_measured_zero(self):
        def no_chain_stub(prompt: str) -> str:
            if _which_step(prompt) == "step1":
                return json.dumps({"has_chain": False, "premises": "", "conclusion": ""})
            return json.dumps({})

        score, comment = detect_structure(SOURCE_LIGHT_TEXT, llm=no_chain_stub)
        assert score == 0.0
        assert "aucune chaîne" in comment.lower()

    def test_no_llm_raises_fail_loud(self):
        with pytest.raises(AgenticDetectorError, match="no LLM callable"):
            detect_structure(CHAINED_TEXT, llm=None)


class TestExhaustiviteAgentic:
    def test_broad_coverage_matches_high(self):
        stub = _make_exhaust_stub(broad_keywords=["équité sociale", "faisabilité politique"], mono_keywords=["taux de guérison"])
        score, comment = detect_exhaust(BROAD_TEXT, llm=stub)
        assert score == 1.0, f"broad coverage should score high, got {score}"
        assert "couverture_large" in comment

    def test_monodimensional_rejected_negative_control(self):
        """Negative control: long but monodimensional text must REJECT. A
        lexical sentence-count would score it HIGH (many sentences) — the
        agentic chain identifies the missing dimensions."""
        stub = _make_exhaust_stub(broad_keywords=["équité sociale"], mono_keywords=["taux de guérison", "essais cliniques"])
        score, comment = detect_exhaust(MONODIM_TEXT, llm=stub)
        assert score == 0.0, (
            f"NEGATIVE CONTROL FAILED: monodimensional text must REJECT (0.0), "
            f"got {score}. Sentence-count rewards length, not coverage — theatre."
        )
        assert "monodimensionnel_seul" in comment

    def test_no_llm_raises_fail_loud(self):
        with pytest.raises(AgenticDetectorError, match="no LLM callable"):
            detect_exhaust(BROAD_TEXT, llm=None)


class TestRedondanceFaibleAgentic:
    def test_distinct_points_matches_high(self):
        stub = _make_redond_stub(distinct_keywords=["premièrement", "deuxièmement"], redundant_keywords=["écoles méritent"])
        score, comment = detect_redond(DISTINCT_TEXT, llm=stub)
        assert score == 1.0, f"distinct points should score high, got {score}"
        assert "points_distincts" in comment

    def test_semantic_restatement_rejected_negative_control(self):
        """Negative control: same idea in varied words must REJECT. A lexical
        unique-word ratio would score it HIGH (varied vocabulary = 'low
        redundancy') — the agentic chain locates the semantic restatement."""
        stub = _make_redond_stub(distinct_keywords=["premièrement"], redundant_keywords=["écoles méritent", "former notre jeunesse", "impératif national"])
        score, comment = detect_redond(SEMANTIC_RESTATEMENT_TEXT, llm=stub)
        assert score == 0.0, (
            f"NEGATIVE CONTROL FAILED: semantic restatement must REJECT (0.0), "
            f"got {score}. Unique-word-ratio rewards lexical variety, not "
            "semantic distinctness — theatre."
        )
        assert "redondance_sémantique" in comment

    def test_no_llm_raises_fail_loud(self):
        with pytest.raises(AgenticDetectorError, match="no LLM callable"):
            detect_redond(DISTINCT_TEXT, llm=None)


# ---------------------------------------------------------------------------
# Evaluator integration — agentic upgrade path + fail-loud propagation
# ---------------------------------------------------------------------------

class TestEvaluatorAgenticUpgrade:
    """The evaluator must: (a) use agentic detectors when an LLM is wired,
    (b) stay lexical without one (backwards-compat), (c) propagate
    AgenticDetectorError (fail-loud), (d) NOT swallow it into 0.0."""

    def test_agentic_llm_uses_agentic_detector(self, monkeypatch):
        """With agentic_llm wired, refutation_constructive routes to the
        agentic 3-step chain (not the lexical marker grep).

        FB-38 note: AGENTIC_DETECTORS now holds 7 virtues. The other 6 are
        stubbed to benign no-ops so evaluate() completes — only the refutation
        *routing* is under test here (not the other chains' behaviour)."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            ArgumentQualityEvaluator,
        )

        called = {"refut_chain": False}

        def stub_chain(text, llm=None):
            called["refut_chain"] = True
            return 0.5, "agentic chain ran"

        def benign_stub(text, llm=None):
            return 0.0, "stubbed (not under test)"

        monkeypatch.setitem(
            avd.AGENTIC_DETECTORS, "refutation_constructive", stub_chain
        )
        for v in list(avd.AGENTIC_DETECTORS):
            if v != "refutation_constructive":
                monkeypatch.setitem(avd.AGENTIC_DETECTORS, v, benign_stub)
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
