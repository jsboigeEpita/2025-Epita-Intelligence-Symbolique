"""
Argument quality evaluator — 9 argumentative virtues.

Integrated from student project 2.3.5 (Argument Quality Evaluation).
Evaluates text against 9 quality dimensions ("vertus argumentatives")
and returns per-virtue scores + aggregated quality score.

Dependencies:
    - spacy (fr_core_news_sm model)
    - textstat (Flesch readability)
    Both optional — graceful degradation if missing.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("ArgumentQualityEvaluator")

# --- Graceful dependency loading ---

_nlp = None
_flesch_reading_ease = None
_DEPS_AVAILABLE = False


def _load_deps():
    """Load optional dependencies (spacy, textstat) once."""
    global _nlp, _flesch_reading_ease, _DEPS_AVAILABLE
    if _DEPS_AVAILABLE:
        return True
    try:
        import spacy
        from textstat import flesch_reading_ease

        _flesch_reading_ease = flesch_reading_ease
        try:
            _nlp = spacy.load("fr_core_news_sm")
        except OSError:
            logger.warning(
                "spacy model 'fr_core_news_sm' not found. "
                "Quality evaluation will use fallback heuristics."
            )
            _nlp = None
        _DEPS_AVAILABLE = True
        return True
    except ImportError:
        logger.warning(
            "spacy or textstat not installed. "
            "Quality evaluation will use fallback heuristics."
        )
        return False


# --- Linguistic resources ---

_RESOURCES_PATH = Path(__file__).parent / "ressources_argumentatives.json"
_FALLBACK_RESOURCES = {
    "connecteurs_pertinence": [
        "parce que",
        "car",
        "donc",
        "ainsi",
        "puisque",
        "cependant",
        "néanmoins",
        "en effet",
        "en conséquence",
        "par conséquent",
    ],
    "citation_patterns": [
        r"\(.*?\d{4}\)",
        r"\[\d+\]",
        r"selon .*?\b",
        r"d'après .*?\b",
    ],
    "marqueurs_refutation": [
        "certains pensent que",
        "on pourrait objecter",
        "il est vrai que",
        "cependant",
        "néanmoins",
        "toutefois",
    ],
    "connecteurs_structure_logique": [
        "car",
        "donc",
        "ainsi",
        "en conséquence",
        "par conséquent",
        "puisque",
        "en effet",
        "parce que",
        "cependant",
        "mais",
    ],
    "patterns_analogies": [
        "comme si",
        "tel que",
        "à l'instar de",
        "similaire à",
        "comparable à",
        "comme",
        "tout comme",
    ],
    "credible_sources": [
        "OMS",
        "INSEE",
        "UNESCO",
        "ONU",
        "CNRS",
        "INSERM",
        ".gouv.fr",
        ".gov",
        ".org",
        "nature.com",
    ],
}


def _load_resources() -> Dict[str, Any]:
    """Load linguistic resources from JSON file or fallback."""
    if _RESOURCES_PATH.exists():
        try:
            with open(_RESOURCES_PATH, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load resources JSON: %s", e)
    return _FALLBACK_RESOURCES


RESOURCES = _load_resources()

# Taxonomie des 9 vertus argumentatives
VERTUES = [
    "clarte",
    "pertinence",
    "presence_sources",
    "refutation_constructive",
    "structure_logique",
    "analogie_pertinente",
    "fiabilite_sources",
    "exhaustivite",
    "redondance_faible",
]


# --- Individual virtue detectors ---


def detect_clarte(text: str) -> Tuple[float, str]:
    """Evaluate clarity via Flesch readability."""
    _load_deps()
    if _flesch_reading_ease is not None:
        score = _flesch_reading_ease(text)
        comment = f"Lisibilité (Flesch) : {score:.2f}. "
        if score >= 60:
            return 1.0, comment + "Texte clair."
        elif score >= 30:
            return 0.5, comment + "Texte moyennement clair."
        else:
            return 0.2, comment + "Texte difficile à comprendre."
    # Fallback: word length heuristic
    words = text.split()
    avg_len = sum(len(w) for w in words) / max(len(words), 1)
    if avg_len < 6:
        return 1.0, "Texte clair (heuristique: mots courts)."
    elif avg_len < 8:
        return 0.5, "Clarté moyenne (heuristique)."
    return 0.2, "Texte potentiellement complexe (heuristique)."


def detect_pertinence(text: str) -> Tuple[float, str]:
    """Evaluate relevance via logical connector count."""
    connecteurs = RESOURCES.get("connecteurs_pertinence", [])
    text_lower = text.lower()
    _load_deps()
    if _nlp is not None:
        doc = _nlp(text)
        count = sum(1 for token in doc if token.text.lower() in connecteurs)
    else:
        count = sum(1 for c in connecteurs if c in text_lower)
    if count >= 3:
        return 1.0, f"Connecteurs logiques détectés ({count}). Bien structuré."
    elif count >= 1:
        return 0.5, f"Quelques connecteurs logiques ({count}). Structure partielle."
    return 0.2, "Peu ou pas de connecteurs logiques. Structure faible."


def detect_presence_sources(text: str) -> Tuple[float, str]:
    """Evaluate source citation presence."""
    patterns = RESOURCES.get("citation_patterns", [])
    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, text, re.IGNORECASE))
    if count >= 2:
        return 1.0, f"{count} sources détectées."
    elif count == 1:
        return 0.5, "Une source détectée."
    return 0.0, "Aucune source détectée."


def detect_refutation_constructive(text: str) -> Tuple[float, str]:
    """Evaluate presence of constructive refutation markers."""
    marqueurs = RESOURCES.get("marqueurs_refutation", [])
    found = [m for m in marqueurs if m in text.lower()]
    if found:
        return 1.0, f"Réfutation détectée avec : {found[:3]}."
    return 0.0, "Aucune réfutation constructive détectée."


def detect_structure_logique(text: str) -> Tuple[float, str]:
    """Evaluate logical structure via connector count."""
    connecteurs = RESOURCES.get("connecteurs_structure_logique", [])
    found = [c for c in connecteurs if c in text.lower()]
    if len(found) >= 2:
        return 1.0, f"Structure logique ({len(found)} connecteurs)."
    elif len(found) == 1:
        return 0.5, "Structure partiellement logique."
    return 0.0, "Structure logique faible."


def detect_analogie_pertinente(text: str) -> Tuple[float, str]:
    """Evaluate presence of pertinent analogies."""
    patterns = RESOURCES.get("patterns_analogies", [])
    found = [p for p in patterns if p in text.lower()]
    if found:
        return 1.0, f"Analogie détectée : {found[:2]}."
    return 0.0, "Aucune analogie détectée."


def detect_fiabilite_sources(text: str) -> Tuple[float, str]:
    """Evaluate source credibility via known source list."""
    sources = RESOURCES.get("credible_sources", [])
    found = [src for src in sources if src.lower() in text.lower()]
    if found:
        return 1.0, f"Sources crédibles : {found[:3]}."
    return 0.0, "Pas de source crédible identifiable."


def detect_exhaustivite(text: str) -> Tuple[float, str]:
    """Evaluate text comprehensiveness via sentence count."""
    _load_deps()
    if _nlp is not None:
        sentences = list(_nlp(text).sents)
        count = len(sentences)
    else:
        count = text.count(".") + text.count("!") + text.count("?")
    if count >= 5:
        return 1.0, f"{count} phrases. Couverture raisonnable."
    elif count >= 3:
        return 0.5, "Couverture partielle du sujet."
    return 0.0, "Texte trop court pour juger de l'exhaustivité."


def detect_redondance_faible(text: str) -> Tuple[float, str]:
    """Evaluate low redundancy via unique word ratio."""
    _load_deps()
    if _nlp is not None:
        words = [t.text.lower() for t in _nlp(text) if t.is_alpha]
    else:
        words = [w.lower().strip(".,!?;:") for w in text.split() if w.strip(".,!?;:")]
    if not words:
        return 0.0, "Texte vide."
    unique = set(words)
    ratio = len(unique) / len(words)
    if ratio > 0.7:
        return 1.0, "Peu de redondance détectée."
    elif ratio > 0.5:
        return 0.5, "Redondance modérée."
    return 0.0, "Forte redondance lexicale."


# --- Detector registry ---

DETECTORS: Dict[str, Callable[[str], Tuple[float, str]]] = {
    "clarte": detect_clarte,
    "pertinence": detect_pertinence,
    "presence_sources": detect_presence_sources,
    "refutation_constructive": detect_refutation_constructive,
    "structure_logique": detect_structure_logique,
    "analogie_pertinente": detect_analogie_pertinente,
    "fiabilite_sources": detect_fiabilite_sources,
    "exhaustivite": detect_exhaustivite,
    "redondance_faible": detect_redondance_faible,
}


# --- Main evaluator ---


class ArgumentQualityEvaluator:
    """
    Evaluates argument quality across 9 virtues.

    Can be used standalone or registered in CapabilityRegistry.

    Usage:
        evaluator = ArgumentQualityEvaluator()
        result = evaluator.evaluate("Selon l'OMS, ...")
        # result = {"note_finale": 7.5, "note_moyenne": 0.83, "scores_par_vertu": {...}, ...}
    """

    def __init__(self, detectors: Optional[Dict] = None):
        self.detectors = detectors or DETECTORS

    def evaluate(self, text: str) -> Dict[str, Any]:
        """Evaluate argument quality and return structured report."""
        scores = {}
        details = {}
        for vertu, detector in self.detectors.items():
            try:
                note, comment = detector(text)
                scores[vertu] = note
                details[vertu] = comment
            except Exception as e:
                logger.warning("Detector '%s' failed: %s", vertu, e)
                scores[vertu] = 0.0
                details[vertu] = f"Erreur: {e}"

        note_finale = sum(scores.values())
        return {
            "note_finale": note_finale,
            "note_moyenne": note_finale / len(scores) if scores else 0.0,
            "scores_par_vertu": scores,
            "rapport_detaille": details,
        }


def evaluer_argument(text: str) -> Dict[str, Any]:
    """Convenience function — evaluate a single argument text."""
    evaluator = ArgumentQualityEvaluator()
    return evaluator.evaluate(text)
