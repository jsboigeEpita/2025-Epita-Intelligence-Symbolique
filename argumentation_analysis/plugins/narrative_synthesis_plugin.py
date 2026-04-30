"""Narrative Synthesis Plugin for Spectacular Analysis Pipeline (#351).

Produces 1-2 paragraphs of human-readable narrative weaving together
results from all analysis KBs (fallacies, JTMS, ATMS, Dung, quality,
counter-arguments). Reads from UnifiedAnalysisState and generates
prose without LLM calls — purely template-based for reliability.
"""

import logging
from typing import Any, Dict, List, Optional

try:
    from semantic_kernel.functions import kernel_function

    SK_AVAILABLE = True
except ImportError:

    def kernel_function(name=None, description=None):
        def decorator(func):
            func._sk_function_name = name or func.__name__
            func._sk_function_description = description or func.__doc__
            return func

        return decorator

    SK_AVAILABLE = False

logger = logging.getLogger(__name__)


def build_narrative(state: Any) -> str:
    """Build a narrative synthesis paragraph from UnifiedAnalysisState.

    Weaves together results from quality, fallacies, counter-arguments,
    JTMS beliefs, ATMS contexts, Dung extensions, and formal logic into
    1-2 readable paragraphs. Each referenced field is cited naturally.
    """
    parts: List[str] = []

    # ── Quality scores ─────────────────────────────────────────────
    quality = getattr(state, "argument_quality_scores", {})
    if quality:
        scores = [v.get("overall", 0) for v in quality.values() if isinstance(v, dict)]
        if scores:
            avg = sum(scores) / len(scores)
            quality_desc = (
                f"L'evaluation de la qualite argumentative couvre "
                f"{len(quality)} argument(s), avec une note moyenne de "
                f"{avg:.1f}/5."
            )
            weak = [k for k, v in quality.items() if isinstance(v, dict) and v.get("overall", 0) < 3]
            if weak:
                quality_desc += f" {len(weak)} argument(s) presentent des faiblesses significatives."
            parts.append(quality_desc)

    # ── Fallacies ──────────────────────────────────────────────────
    fallacies = getattr(state, "identified_fallacies", {})
    neural_fallacies = getattr(state, "neural_fallacy_scores", [])
    total_fallacies = len(fallacies) + len(neural_fallacies)
    if total_fallacies:
        types = [v.get("type", "inconnu") for v in fallacies.values() if isinstance(v, dict)]
        types_str = ", ".join(set(types)) if types else f"{total_fallacies} sophisme(s)"
        fallacy_text = (
            f"L'analyse a detecte {total_fallacies} sophisme(s) "
            f"({types_str}), ce qui fragilise la structure argumentative."
        )
        parts.append(fallacy_text)

    # ── Counter-arguments ──────────────────────────────────────────
    counters = getattr(state, "counter_arguments", [])
    if counters:
        strategies = set()
        for ca in counters:
            if isinstance(ca, dict):
                strategies.add(ca.get("strategy", "general"))
        strat_text = ", ".join(strategies) if strategies else "plusieurs approches"
        parts.append(
            f"Des contre-arguments ont ete generes via {strat_text}, "
            f"identifiant {len(counters)} point(s) de contestation."
        )

    # ── JTMS beliefs ───────────────────────────────────────────────
    jtms_beliefs = getattr(state, "jtms_beliefs", {})
    if jtms_beliefs:
        valid_count = sum(1 for v in jtms_beliefs.values() if isinstance(v, dict) and v.get("valid") is True)
        invalid_count = sum(1 for v in jtms_beliefs.values() if isinstance(v, dict) and v.get("valid") is False)
        jtms_text = (
            f"Le systeme JTMS maintient {len(jtms_beliefs)} croyance(s): "
            f"{valid_count} valide(s), {invalid_count} rejetee(s)."
        )
        retraction_chain = getattr(state, "jtms_retraction_chain", [])
        if retraction_chain:
            cascade_count = sum(len(r.get("cascaded", [])) for r in retraction_chain)
            jtms_text += (
                f" {len(retraction_chain)} retraction(s) en cascade ont ete observee(s), "
                f"affectant {cascade_count} croyance(s) dependante(s)."
            )
        parts.append(jtms_text)

    # ── ATMS multi-context ─────────────────────────────────────────
    atms_contexts = getattr(state, "atms_contexts", [])
    if atms_contexts:
        coherent = sum(1 for c in atms_contexts if isinstance(c, dict) and c.get("coherent"))
        incoherent = len(atms_contexts) - coherent
        parts.append(
            f"L'analyse ATMS multi-contextes a teste {len(atms_contexts)} hypothese(s): "
            f"{coherent} coherente(s), {incoherent} incoherente(s), "
            f"illustrant la sensibilite des conclusions aux hypotheses retenues."
        )

    # ── Dung frameworks ────────────────────────────────────────────
    dung = getattr(state, "dung_frameworks", {})
    if dung:
        ext_count = sum(
            len(v.get("extensions", [])) for v in dung.values() if isinstance(v, dict)
        )
        if ext_count:
            parts.append(
                f"L'argumentation abstraite (semantiques de Dung) a identifie "
                f"{ext_count} extension(s) parmi {len(dung)} cadre(s) d'attaque."
            )

    # ── Formal logic ───────────────────────────────────────────────
    fol = getattr(state, "fol_analysis_results", [])
    pl = getattr(state, "propositional_analysis_results", [])
    modal = getattr(state, "modal_analysis_results", [])
    formal_count = len(fol) + len(pl) + len(modal)
    if formal_count:
        formal_parts = []
        if fol:
            formal_parts.append(f"{len(fol)} en logique du premier ordre")
        if pl:
            formal_parts.append(f"{len(pl)} en logique propositionnelle")
        if modal:
            formal_parts.append(f"{len(modal)} en logique modale")
        formal_str = ", ".join(formal_parts)
        parts.append(
            f"L'analyse formelle a produit {formal_count} resultat(s) ({formal_str})."
        )

    if not parts:
        return (
            "L'analyse n'a pas produit suffisamment de donnees pour generer "
            "une synthese narrative. Seules des donnees partielles sont disponibles."
        )

    # ── Assemble into 1-2 paragraphs ───────────────────────────────
    paragraph_1 = " ".join(parts[: len(parts) // 2 + 1])
    paragraph_2 = " ".join(parts[len(parts) // 2 + 1 :]) if len(parts) > 3 else ""

    if paragraph_2:
        return f"{paragraph_1}\n\n{paragraph_2}"
    return paragraph_1


class NarrativeSynthesisPlugin:
    """Semantic Kernel plugin for narrative synthesis (#351).

    Produces human-readable analysis summaries by weaving together
    outputs from all pipeline phases.
    """

    @kernel_function(
        name="narrative_synthesis",
        description="Generate a narrative synthesis paragraph from all "
        "analysis results. Weaves quality scores, fallacy detection, "
        "counter-arguments, JTMS beliefs, ATMS contexts, and formal "
        "logic into readable prose.",
    )
    def synthesize(self, state_json: str = "{}") -> str:
        """Generate narrative synthesis from state JSON."""
        import json

        try:
            state_data = json.loads(state_json)
        except (json.JSONDecodeError, TypeError):
            state_data = {}

        # Build a simple namespace object from dict for build_narrative
        ns = type("State", (), state_data)()
        return build_narrative(ns)
