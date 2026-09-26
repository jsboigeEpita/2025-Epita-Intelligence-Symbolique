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
import threading
from functools import partial
from pathlib import Path
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("ArgumentQualityEvaluator")

# --- Graceful dependency loading ---

_nlp = None
_DEPS_AVAILABLE = False
_DEPS_ATTEMPTED = False
# #2320: the FIRST load failure raises with its cause; every later call hits a
# gate message that used to repeat only generic advice — the original cause was
# lost (swallowed by callers' broad excepts), leaving CI diagnostics blind. The
# gates re-embed it so the first failure stays visible from any later traceback.
_LAST_LOAD_ERROR: Optional[str] = None
_TORCH_NEUTRALIZED = False
# The flags above are set in two steps around a load that takes seconds cold
# (spaCy import), and the quality phase evaluates units in concurrent threads
# (#2331). Unlocked, a sibling unit read "attempted, not available" mid-load
# and raised "cause not recorded" — a load in progress reported as a failed
# one (measured by the #2353 render). The load runs under this lock, and every
# read of the pair goes through it, so a reader waits for the load to finish.
_DEPS_LOCK = threading.Lock()


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
    """Load required dependencies (spacy, textstat), once, under ``_DEPS_LOCK``.

    A caller arriving while another thread loads waits for that load and
    shares its outcome — success, or the recorded failure.
    """
    with _DEPS_LOCK:
        return _load_deps_locked()


def _deps_failed() -> bool:
    """True once a load has been attempted and failed; waits for one in flight."""
    with _DEPS_LOCK:
        return _DEPS_ATTEMPTED and not _DEPS_AVAILABLE


def _load_deps_locked():
    """Load required dependencies (spacy, textstat). Caller holds ``_DEPS_LOCK``.

    Raises RuntimeError if spacy or textstat cannot be imported, or if the
    ``fr_core_news_sm`` model cannot be loaded (#2675).
    This is the root-cause fix for #1019 subsystem 1: the previous
    code silently fell back to regex heuristics when torch/spacy
    failed due to DLL load order (WinError 182).  Now we fail loud
    so the problem is visible and the root cause (dll_guard not
    imported at entry point) must be fixed instead.
    """
    global _nlp, _DEPS_AVAILABLE, _DEPS_ATTEMPTED, _LAST_LOAD_ERROR
    if _DEPS_ATTEMPTED:
        if not _DEPS_AVAILABLE:
            raise RuntimeError(
                "spacy/textstat are not available. Ensure the conda environment "
                "is activated and dll_guard is imported before jpype. "
                f"(Previous attempt failed: {_LAST_LOAD_ERROR or 'cause not recorded'})"
            )
        return True
    _DEPS_ATTEMPTED = True
    try:
        # FB-25 #1093: neutralise a faulty torch BEFORE importing spacy, so
        # thinc's optional torch import is skipped instead of poisoning spaCy.
        _neutralize_faulty_torch()
        import spacy
        from textstat import flesch_reading_ease  # noqa: F401 — presence check

        # textstat reaches NLTK's cmudict through a LazyCorpusLoader, which is
        # not thread-safe on first use: concurrent units raced it and recorded
        # 'clarte' UNAVAILABLE ("'CMUDictCorpusReader' object has no attribute
        # '_LazyCorpusLoader__reader_cls'", #2353 render). #2588 review: that
        # first use now happens under text_scoring's own lock, per language
        # (a French first call does not load CMUdict), so no warm-up runs
        # here — warming all three languages added ~1.2 s to the first
        # quality call without preventing the race.
        # #2675: a missing model is a load failure like any other. It used to
        # be caught here and degraded to "simplified tokenisation" with a
        # warning — the scores changed without the result saying so (the
        # #2320 replay-key drift, and a #2353 render that differed by seat).
        _nlp = spacy.load("fr_core_news_sm")
        _DEPS_AVAILABLE = True
        return True
    except Exception as exc:
        # Record EVERY escape (#2320): the load can die with exception types this
        # clause historically did not list — e.g. srsly's msgpack deserializer
        # raising ValueError("int is not allowed for map key...") — and those
        # escaped unrecorded, leaving the later gates with "cause not recorded"
        # and the diagnosis blind (run 35451228603: 54 gate hits, zero causes).
        _LAST_LOAD_ERROR = f"{type(exc).__name__}: {exc}"
        # ImportError: spacy/textstat not installed (most common cause — ensure
        #   `textstat` and `python -m spacy download fr_core_news_sm` are provisioned;
        #   see setup_project_env.ps1 and environment.yml, FB-23 #1088).
        # OSError [E050]: spaCy model `fr_core_news_sm` not downloaded.
        # OSError [WinError 182]: torch DLL conflict (#882) — rare on recent envs;
        #   dll_guard pre-loads torch before jpype as defense-in-depth.
        if not isinstance(exc, (ImportError, OSError, RuntimeError)):
            raise  # unfamiliar failure class — propagate it RAW, fail loud
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


# --- Context taxonomy (#1907) ---


class ContextLevel(IntEnum):
    """How much material a virtue needs before it can be judged at all.

    Ordered: a unit at level N carries every property judgeable at levels <= N.
    """

    CLAIM = 1
    """A single extracted claim, stripped of its surroundings."""

    LOCAL_CONTEXT = 2
    """The claim plus the passage it sits in (a few sentences)."""

    DOCUMENT = 3
    """The whole document, with its citations and its rebuttal moves."""

    @property
    def label(self) -> str:
        return {
            ContextLevel.CLAIM: "revendication isolee",
            ContextLevel.LOCAL_CONTEXT: "passage local",
            ContextLevel.DOCUMENT: "document complet",
        }[self]


class VirtueStatus(str, Enum):
    """Outcome of asking one virtue about one unit (#1907)."""

    EVALUATED = "evaluated"
    """The detector ran on adequate material; ``scores_par_vertu`` holds a value."""

    NOT_APPLICABLE = "not_applicable"
    """The unit cannot carry this property. Honestly absent — NOT a zero."""

    UNAVAILABLE = "unavailable"
    """The detector or one of its dependencies failed. Also NOT a zero."""


VIRTUE_CONTEXT_REQUIREMENTS: Dict[str, ContextLevel] = {
    # Judgeable on the claim itself: readability, and whether the claim links
    # its own parts. Measured on 142 real records, these are the only two
    # dimensions that actually varied on isolated claims.
    "clarte": ContextLevel.CLAIM,
    "pertinence": ContextLevel.CLAIM,
    # Need the surrounding passage. A multi-step structure spans clauses; an
    # analogy is a passage-level device; a lexical-diversity ratio over a
    # 94-character claim is ~1.0 for any input (it scored exactly 1.00 on
    # 142/142 records, adding a flat +1.0 to every score while ranking nothing).
    "structure_logique": ContextLevel.LOCAL_CONTEXT,
    "analogie_pertinente": ContextLevel.LOCAL_CONTEXT,
    "redondance_faible": ContextLevel.LOCAL_CONTEXT,
    # Stating an opposing thesis and rebutting it fits in a passage, not a
    # document: the ``REAL_REFUTATION`` fixture of FB-29 does it in two
    # sentences, and ``REAL_ANALOGY`` carries a full structural mapping in one
    # long sentence. Those fixtures refuted an earlier draft that filed
    # refutation as DOCUMENT-level.
    "refutation_constructive": ContextLevel.LOCAL_CONTEXT,
    # Need the whole document. Extraction strips citations, and essay-level
    # coverage is by definition a whole-text property. ``detect_exhaustivite``
    # already says so in its own comment ("Texte trop court pour juger") and
    # then returned 0.0 anyway — that is the inference #1907 removes.
    "presence_sources": ContextLevel.DOCUMENT,
    "fiabilite_sources": ContextLevel.DOCUMENT,
    "exhaustivite": ContextLevel.DOCUMENT,
}

VIRTUE_DEPENDENCIES: Dict[str, str] = {
    # The reliability of sources is undefined when no source is present at all.
    # Scoring it 0.0 asserts "the sources are unreliable" about a text that
    # cites none.
    "fiabilite_sources": "presence_sources",
}

# Derived from the detectors' own scoring bands, not invented: detect_exhaustivite
# reaches its top band at >= 5 sentences, so a unit that long is document-shaped;
# below 2 sentences nothing multi-sentence can be exhibited.
_DOCUMENT_MIN_SENTENCES = 5
_LOCAL_MIN_SENTENCES = 2
# A single long sentence can still be a passage: a multi-clause sentence carries
# an analogy or a rebuttal. Calibrated against the observed corpus unit (median
# 94 characters, ~15 words) and against ``detect_redondance_faible``, whose
# unique-word ratio is mechanically ~1.0 below roughly this many tokens — it
# scored exactly 1.00 on 142/142 real records. ``TestPopulationBand`` is the
# guard that keeps this from drifting back into a degenerate band.
_LOCAL_MIN_WORDS = 30

# R2 clause-aware admission (#1907, coordinator arbitration R950). The word
# gate above is the only discriminator for single-sentence units, and the
# measured sub-30-word region still holds structure: 12/47 units carry a
# refutation, an analogy or a causal chain (9 of the 12 in the 20-29 word
# band). Rule R2 admits a CLAIM-band unit for the *structural* virtues when
# it carries clause structure. Exactly these three virtues — never
# ``redondance_faible``, whose sub-30-word band is degenerate (a flat 1.00 on
# 47/47 measured units: admitting it reopens the +1.0 band the tri-state
# closed), and never as a third gate of ``infer_context_level`` (which would
# lift every LOCAL-level virtue at once).
_CLAUSE_AWARE_VIRTUES = frozenset(
    {"refutation_constructive", "analogie_pertinente", "structure_logique"}
)


def is_multi_clause(text: str) -> bool:
    """R2 clause-structure test for a short single-sentence unit (#1907).

    True when the unit carries at least one strong separator — ``;``, ``:``
    or a connector from the existing ``connecteurs_structure_logique``
    resource, reusing the detectors' own list and substring semantics (no
    second taxonomy) — or at least two commas.

    Calibration (measured 2026-09-08 on the 47-unit sub-30-word region,
    #1907): admits 11/12 structure-bearing units. The 12th is a 15-word
    adversative refutation carrying no separator of any kind — recognized
    by its content, not its punctuation — and stays honestly
    NOT_APPLICABLE. **Family bound**: any punctuation-based admission rule
    leaves at least one such residual false negative; do not tighten the
    rule to catch it (that admits arbitrarily elsewhere).

    Accepted noise on the comma branch (re-measured 2026-09-20): of the
    non-bearing units admitted only by commas, a majority carry
    enumeration or discourse-marker commas (one via a thousands
    separator), not clause commas — yet the branch also admits genuinely
    multi-clause units (2 of 6 in the measured set), which is why R2 was
    preferred over R1. Admitted non-bearers produce evaluated zeros, not
    fabricated scores.
    """
    lowered = (text or "").lower()
    if ";" in lowered or ":" in lowered:
        return True
    if any(c in lowered for c in RESOURCES.get("connecteurs_structure_logique", [])):
        return True
    return lowered.count(",") >= 2


def infer_context_level(text: str) -> ContextLevel:
    """Infer the unit shape when the caller did not declare one.

    The ~40 legacy call sites pass text only. Defaulting them to DOCUMENT is
    what produced seven fabricated zeros per record; defaulting to CLAIM would
    silently discard real document evaluations. So we read the text.
    """
    sentences = len([s for s in re.split(r"[.!?]+", text or "") if s.strip()])
    words = len((text or "").split())
    if sentences >= _DOCUMENT_MIN_SENTENCES:
        return ContextLevel.DOCUMENT
    if sentences >= _LOCAL_MIN_SENTENCES or words >= _LOCAL_MIN_WORDS:
        return ContextLevel.LOCAL_CONTEXT
    return ContextLevel.CLAIM


# --- Individual virtue detectors ---


# Flesch bands per language (#2588). First calibration, n = 8 repo samples
# (5 fr, 2 de, 1 en anchor), measured 2026-09-26: under fr rules the same
# text scores ~+20 vs en rules (mid-range sentence 21.4→43.6, simple
# 98.3→112.0) — bands shift up; under de rules ~-12 (67.3→55.3) with no
# band crossing on the graded set — bands kept. Translation anchor: the en
# control (59.2, "medium") and its French counterparts (43.6–69.1) land in
# the same band. A thin calibration — re-derive before trusting the edges.
_CLARTE_BANDS = {
    "en": (60.0, 30.0),
    "fr": (80.0, 40.0),
    "de": (60.0, 30.0),
}


def detect_clarte(text: str, lang: Optional[str] = None) -> Tuple[float, str]:
    """Evaluate clarity via Flesch readability, in the text's language (#2588).

    ``lang`` is a decision taken on a LONGER text than ``text`` — the document
    the caller holds (a pipeline phase's ``input_text``, a debate topic). That
    is the only case where the comment's "langue du document" is true. Passing
    a language detected on ``text`` itself is not merely redundant (``None``
    runs the same detection): the comment would name a document that decided
    nothing. Callers holding no longer text leave it ``None``, and the comment
    then names the detected language (#2588 review-2).
    """
    _load_deps()
    from argumentation_analysis.agents.core import text_scoring

    score, used_lang = text_scoring.flesch_reading_ease_for(text, lang)
    if score is not None:
        clear_threshold, medium_threshold = _CLARTE_BANDS[used_lang]
        origin = "langue détectée" if lang is None else "langue du document"
        comment = f"Lisibilité (Flesch {used_lang}, {origin}) : {score:.2f}. "
        if score >= clear_threshold:
            return 1.0, comment + "Texte clair."
        elif score >= medium_threshold:
            return 0.5, comment + "Texte moyennement clair."
        else:
            return 0.2, comment + "Texte difficile à comprendre."
    # No Flesch constants for the detected language: named fallback heuristic.
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

# #2331: sentinel distinguishing "evaluate() was not asked" (inherit the
# constructor wiring) from "evaluate() was explicitly asked for lexical"
# (``agentic_llm=None``). Without it, a per-call None could not force the
# lexical layer on an evaluator constructed with wiring.
_UNSET: Any = object()


class ArgumentQualityEvaluator:
    """
    Evaluates argument quality across 9 virtues.

    Can be used standalone or registered in CapabilityRegistry.

    Usage:
        evaluator = ArgumentQualityEvaluator()
        result = evaluator.evaluate("Selon l'OMS, ...")
        # result = {"note_finale": 7.5, "note_moyenne": 0.83, "scores_par_vertu": {...}, ...}
    """

    def __init__(
        self,
        detectors: Optional[Dict] = None,
        agentic_llm: Optional[Any] = None,
    ):
        self.detectors = detectors or DETECTORS
        # #2331: the evaluator can be CONSTRUCTED with its agentic wiring —
        # the production quality phase does this, so the construction site
        # (not each call site) is where the wiring lives and is asserted.
        # ``evaluate`` still accepts a per-call ``agentic_llm``; an explicitly
        # passed value (including None) always wins over this one, so the
        # degraded re-run of a failed unit can force the lexical layer.
        self.agentic_llm = agentic_llm

    def evaluate(
        self,
        text: str,
        agentic_llm: Any = _UNSET,
        context_level: Optional[ContextLevel] = None,
        lang: Optional[str] = None,
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

        #2331: omitted (the sentinel default) inherits ``self.agentic_llm``
        (the constructor wiring the production phase asserts at its
        construction site); explicitly passed — including ``None`` — always
        overrides it.

        #1907: every virtue declares the context level it needs
        (``VIRTUE_CONTEXT_REQUIREMENTS``). A virtue that needs more material
        than ``context_level`` provides is reported NOT_APPLICABLE and carries
        no score at all — it is not scored 0.0 and it does not enter the
        denominator. ``context_level`` defaults to ``infer_context_level(text)``
        so legacy single-argument callers stop receiving fabricated zeros.
        The returned dict gains ``statuts_par_vertu`` (all 9 virtues),
        ``note_max_applicable`` (the ceiling actually reachable on this unit)
        and ``contexte_evalue``.

        #1907 R2 (arbitration R950): within the CLAIM band, a unit that
        carries clause structure (``is_multi_clause``) remains applicable to
        the three structural virtues — a per-virtue admission, never a third
        gate of ``infer_context_level``.
        """
        # Fail-loud gate (#1019 / NanoClaw review): if deps already failed,
        # raise immediately rather than looping through 9 detectors that
        # will each catch the RuntimeError and produce score 0.0 — which
        # is the exact "degraded theatre" the mandate forbids.
        if _deps_failed():
            raise RuntimeError(
                "Cannot evaluate quality: spacy/textstat/model are not available. "
                "Ensure textstat is installed and the fr_core_news_sm model is "
                "downloaded (`python -m spacy download fr_core_news_sm`), and the "
                "conda environment is activated. See setup_project_env.ps1. "
                f"(First load failure: {_LAST_LOAD_ERROR or 'cause not recorded'})"
            )

        # #2331: no per-call ask → inherit the constructor wiring. An explicit
        # value (including None, the forced-lexical degraded re-run) wins.
        if agentic_llm is _UNSET:
            agentic_llm = self.agentic_llm

        if context_level is None:
            context_level = infer_context_level(text)
        context_level = ContextLevel(context_level)

        # #2588 review: ``lang`` is the language decided on the document the
        # caller holds; bound into the clarte detector so a short argument
        # inherits the document's Flesch scale instead of losing it.
        detectors = self.detectors
        if lang is not None and "clarte" in detectors:
            detectors = {**detectors, "clarte": partial(detect_clarte, lang=lang)}

        scores: Dict[str, float] = {}
        details: Dict[str, str] = {}
        statuses: Dict[str, VirtueStatus] = {}

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
                    "lexical detectors for all 9 virtues.",
                    exc,
                )

        for vertu, detector in detectors.items():
            # #1907 — applicability is decided by the input unit, never by the
            # score that came out. A virtue whose required context exceeds what
            # we were handed is honestly absent: no value, no denominator slot.
            # (Custom/injected detectors are unknown to the taxonomy and default
            # to CLAIM, i.e. always applicable — no behaviour change for them.)
            required = VIRTUE_CONTEXT_REQUIREMENTS.get(vertu, ContextLevel.CLAIM)
            # #1907 R2 (arbitration R950): a CLAIM-band unit that carries
            # clause structure stays judgeable by the structural virtues —
            # the measured false negatives (12/47 sub-30-word units) sit
            # exactly there. Per virtue only, so redondance_faible keeps its
            # >= 30-word floor; inferred and declared levels are treated the
            # same because applicability is a property of the unit.
            if (
                vertu in _CLAUSE_AWARE_VIRTUES
                and context_level == ContextLevel.CLAIM
                and is_multi_clause(text)
            ):
                required = ContextLevel.CLAIM
            if required > context_level:
                statuses[vertu] = VirtueStatus.NOT_APPLICABLE
                details[vertu] = (
                    f"Non applicable : cette vertu requiert un {required.label}, "
                    f"l'unite evaluee est une {context_level.label}. Absence "
                    "honnete, aucune note attribuee (#1907)."
                )
                continue

            dep = VIRTUE_DEPENDENCIES.get(vertu)
            if dep is not None and scores.get(dep) == 0.0:
                statuses[vertu] = VirtueStatus.NOT_APPLICABLE
                details[vertu] = (
                    f"Non applicable : depend de « {dep} », qui n'a rien releve. "
                    "Juger la fiabilite de sources absentes n'a pas de sens "
                    "(#1907)."
                )
                continue

            try:
                # Use the agentic detector for the upgraded virtues when an LLM
                # is available; keep the lexical detector otherwise.
                if vertu in agentic_detectors and agentic_llm is not None:
                    note, comment = agentic_detectors[vertu](text, llm=agentic_llm)
                else:
                    note, comment = detector(text)
                scores[vertu] = note
                details[vertu] = comment
                statuses[vertu] = VirtueStatus.EVALUATED
            except Exception as e:
                # FB-29 #1105: AgenticDetectorError is the agentic chain's
                # fail-loud contract (no LLM / unparseable step). It MUST
                # propagate — swallowing it would return a synthetic 0.0 "as if
                # measured", the exact degraded theatre #1019 forbids. Other
                # exceptions (detector-internal bugs) keep the legacy
                # 0.0+"Erreur" robustness (anti-pendule: don't widen the change).
                if agentic_error_cls is not None and isinstance(e, agentic_error_cls):
                    raise
                # #1907: an outage is the third state. Recording 0.0 made a
                # crashed detector indistinguishable from a measured verdict.
                logger.warning("Detector '%s' failed: %s", vertu, e)
                statuses[vertu] = VirtueStatus.UNAVAILABLE
                details[vertu] = f"Indisponible : {e}"

        # #1907 — the denominator is the number of dimensions actually
        # evaluated, not a fixed 9. Averaging over inapplicable dimensions is
        # what pinned every real-corpus argument into a 1.4-2.5 band on a
        # surface labelled "/10".
        note_finale = sum(scores.values())
        evaluees = len(scores)
        result = {
            "note_finale": note_finale,
            "note_moyenne": note_finale / evaluees if evaluees else 0.0,
            "note_max_applicable": float(evaluees),
            "scores_par_vertu": scores,
            "statuts_par_vertu": statuses,
            "contexte_evalue": context_level,
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
