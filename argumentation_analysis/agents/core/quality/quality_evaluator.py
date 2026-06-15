"""
Argument quality evaluator — 9 argumentative virtues.

Integrated from student project 2.3.5 (Argument Quality Evaluation).
Evaluates text against 9 quality dimensions ("vertus argumentatives")
and returns per-virtue scores + aggregated quality score.

Dependencies:
    - spacy (fr_core_news_sm model) — REQUIRED
    - textstat (Flesch readability) — REQUIRED

If spacy/textstat/model cannot load, the evaluator raises RuntimeError
instead of silently producing heuristic scores. The usual cause is a
missing dependency (`textstat` package or the `fr_core_news_sm` spaCy
model — see setup_project_env.ps1, FB-23 #1088); the torch DLL conflict
(WinError 182, #882) is the rarer fallback covered by dll_guard. Callers
must handle the exception or ensure the environment is correctly configured.
"""

import argumentation_analysis.core.dll_guard  # noqa: F401 — defense in depth (#1019)

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("ArgumentQualityEvaluator")

# --- Graceful dependency loading ---

_nlp = None
_flesch_reading_ease = None
_DEPS_AVAILABLE = False
_DEPS_ATTEMPTED = False
_TORCH_NEUTRALIZED = False


def _neutralize_faulty_torch() -> None:
    """Make spaCy's transitive optional ``torch`` import skippable when torch's
    Windows DLL faults (WinError 182 / fbgemm.dll, issue #882).

    Background (FB-25 #1093): on Windows envs where ``torch`` is installed but
    its native DLL faults (e.g. torch 2.2.2 in ``projet-is-roo-new``), spaCy's
    ``import spacy`` pulls thinc, which does an *optional* ``import torch``.
    thinc catches ``ImportError`` but NOT ``OSError`` — so the DLL fault
    propagates and blocks spaCy entirely, even though the ``fr_core_news_sm``
    model is rule-based (non-neural) and does not need torch at all.

    Fix (anti-pendule: remove the poisoning, do not add a counterweight):
    detect the faulty torch and plant a ``None`` sentinel in ``sys.modules``.
    A subsequent ``import torch`` then raises ``ImportError`` ("import of name
    halted; None in sys.modules"), which thinc catches gracefully and skips.

    This is a no-op when torch is genuinely absent (thinc already handles that)
    or when torch imports cleanly (neural path stays available — important so
    the wide-net / camembert path is unaffected in healthy-torch envs). It only
    fires when torch is installed-but-broken, in which case the neural path was
    never usable in this process anyway.
    """
    global _TORCH_NEUTRALIZED
    if _TORCH_NEUTRALIZED:
        return
    try:
        import torch  # noqa: F401
        return  # torch imports cleanly — nothing to do.
    except ImportError:
        return  # torch genuinely absent — thinc already handles this fine.
    except OSError as exc:
        # Broken torch (DLL fault). Block it so thinc skips its optional import.
        sys.modules["torch"] = None  # type: ignore[assignment]
        _TORCH_NEUTRALIZED = True
        logger.warning(
            "torch import faulted (%s); blocking it on the quality path so the "
            "rule-based fr_core_news_sm model loads. Neural path unavailable in "
            "this process. See issue #882, FB-25 #1093.",
            exc,
        )


def _load_deps():
    """Load required dependencies (spacy, textstat).

    Raises RuntimeError if spacy or textstat cannot be imported.
    This is the root-cause fix for #1019 subsystem 1: the previous
    code silently fell back to regex heuristics when torch/spacy
    failed due to DLL load order (WinError 182).  Now we fail loud
    so the problem is visible and the root cause (dll_guard not
    imported at entry point) must be fixed instead.
    """
    global _nlp, _flesch_reading_ease, _DEPS_AVAILABLE, _DEPS_ATTEMPTED
    if _DEPS_ATTEMPTED:
        if not _DEPS_AVAILABLE:
            raise RuntimeError(
                "spacy/textstat are not available. Ensure the conda environment "
                "is activated and dll_guard is imported before jpype. "
                "(Previous attempt failed — see logs above.)"
            )
        return True
    _DEPS_ATTEMPTED = True
    try:
        # FB-25 #1093: neutralise a faulty torch BEFORE importing spacy, so
        # thinc's optional torch import is skipped instead of poisoning spaCy.
        _neutralize_faulty_torch()
        import spacy
        from textstat import flesch_reading_ease

        _flesch_reading_ease = flesch_reading_ease
        try:
            _nlp = spacy.load("fr_core_news_sm")
        except OSError:
            logger.warning(
                "spacy model 'fr_core_news_sm' not found — "
                "some detectors will use simplified tokenisation."
            )
            _nlp = None
        _DEPS_AVAILABLE = True
        return True
    except (ImportError, OSError, RuntimeError) as exc:
        # ImportError: spacy/textstat not installed (most common cause — ensure
        #   `textstat` and `python -m spacy download fr_core_news_sm` are provisioned;
        #   see setup_project_env.ps1 and environment.yml, FB-23 #1088).
        # OSError [E050]: spaCy model `fr_core_news_sm` not downloaded.
        # OSError [WinError 182]: torch DLL conflict (#882) — rare on recent envs;
        #   dll_guard pre-loads torch before jpype as defense-in-depth.
        raise RuntimeError(
            f"Quality evaluation requires spacy, textstat and the fr_core_news_sm "
            f"model, but a dependency failed: {exc}. Most often this is a missing "
            f"package (textstat) or model (run `python -m spacy download "
            f"fr_core_news_sm`). See setup_project_env.ps1 and "
            f"docs/architecture/TORCH_DLL_REPAIR_RECIPE.md (WinError 182 fallback)."
        ) from exc


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

    def evaluate(
        self, text: str, agentic_llm: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Evaluate argument quality and return structured report.

        Raises RuntimeError if required dependencies (spacy/textstat) are
        unavailable.  This is the fail-loud contract from #1019: producing
        a dict full of zeros is functionally identical to the old silent
        fallback.  Callers must handle the exception or ensure the
        environment is correctly configured.

        FB-29 #1105: when ``agentic_llm`` is provided (an LLM callable wired by
        the caller, e.g. production's OpenRouter-toggle-aware client), the two
        joint-zero blindspot virtues (``refutation_constructive``,
        ``analogie_pertinente``) are upgraded to their multi-step agentic
        detectors (see ``agentic_virtue_detectors``). The other 7 virtues stay
        deterministic. Without ``agentic_llm`` the legacy lexical detectors are
        used for all 9 — backwards-compatible, no behavior change.
        """
        # Fail-loud gate (#1019 / NanoClaw review): if deps already failed,
        # raise immediately rather than looping through 9 detectors that
        # will each catch the RuntimeError and produce score 0.0 — which
        # is the exact "degraded theatre" the mandate forbids.
        if _DEPS_ATTEMPTED and not _DEPS_AVAILABLE:
            raise RuntimeError(
                "Cannot evaluate quality: spacy/textstat/model are not available. "
                "Ensure textstat is installed and the fr_core_news_sm model is "
                "downloaded (`python -m spacy download fr_core_news_sm`), and the "
                "conda environment is activated. See setup_project_env.ps1."
            )

        scores = {}
        details = {}

        # FB-29 #1105: upgrade the 2 joint-zero blindspot virtues to agentic
        # multi-step detectors when an LLM is wired. Lazy import avoids a hard
        # dependency on the agentic module for legacy callers.
        agentic_detectors: Dict[str, Callable[..., Tuple[float, str]]] = {}
        agentic_error_cls = None
        if agentic_llm is not None:
            try:
                from argumentation_analysis.agents.core.quality.agentic_virtue_detectors import (
                    AGENTIC_DETECTORS,
                    AgenticDetectorError,
                )

                agentic_detectors = AGENTIC_DETECTORS
                agentic_error_cls = AgenticDetectorError
            except ImportError as exc:
                logger.warning(
                    "agentic_virtue_detectors unavailable (%s); falling back to "
                    "lexical detectors for all 9 virtues.", exc,
                )

        for vertu, detector in self.detectors.items():
            try:
                # Use the agentic detector for the upgraded virtues when an LLM
                # is available; keep the lexical detector otherwise.
                if vertu in agentic_detectors and agentic_llm is not None:
                    note, comment = agentic_detectors[vertu](text, llm=agentic_llm)
                else:
                    note, comment = detector(text)
                scores[vertu] = note
                details[vertu] = comment
            except Exception as e:
                # FB-29 #1105: AgenticDetectorError is the agentic chain's
                # fail-loud contract (no LLM / unparseable step). It MUST
                # propagate — swallowing it would return a synthetic 0.0 "as if
                # measured", the exact degraded theatre #1019 forbids. Other
                # exceptions (detector-internal bugs) keep the legacy
                # 0.0+"Erreur" robustness (anti-pendule: don't widen the change).
                if agentic_error_cls is not None and isinstance(
                    e, agentic_error_cls
                ):
                    raise
                logger.warning("Detector '%s' failed: %s", vertu, e)
                scores[vertu] = 0.0
                details[vertu] = f"Erreur: {e}"

        note_finale = sum(scores.values())
        result = {
            "note_finale": note_finale,
            "note_moyenne": note_finale / len(scores) if scores else 0.0,
            "scores_par_vertu": scores,
            "rapport_detaille": details,
        }
        return result


def evaluer_argument(text: str) -> Dict[str, Any]:
    """Convenience function — evaluate a single argument text.

    Raises RuntimeError if required dependencies are unavailable (see
    ArgumentQualityEvaluator.evaluate).
    """
    evaluator = ArgumentQualityEvaluator()
    return evaluator.evaluate(text)
