"""Language-aware text measuring instruments (#2588).

Scoring instruments that judge a text's wording — fact-check word lists,
evidence/emotional indicators, Flesch readability — are language-bound.
Applied to French or German text, the English instruments produced
constants reported as measurements: every French text scored fact-check
0.6 (hedging and absolutes matched nothing), and Flesch ran English
syllable counting on French words.

Centralized here:

- language detection, reusing the tested word-marker heuristic of the
  conversational orchestrator (lazy import: ``orchestration`` already
  imports agents at module level);
- one dedicated ``textstatistics`` instance per language — calling
  ``set_lang`` on the default instance is process-wide state shared with
  every other textstat caller;
- a one-time warm-up so the first timed call does not pay the CMUdict
  (en) or pyphen (fr/de) dictionary load (#2398 pattern);
- a no-network guard on the English instrument (#3093): textstat's lazy
  CMUdict loader DOWNLOADS the corpus on a missing resource (``quiet=True``),
  which made a CONSTRUCTOR a network dependency — a failed fetch raised from
  ``DebatePlugin()`` on a corpus that never touched English. When the corpus
  is not provisioned, the English Flesch degrades to ``None`` with its cause
  named (:func:`degraded_reason`); it is never fetched at run time.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = frozenset({"en", "fr", "de"})

_LOCK = threading.Lock()
_FLESCH_BY_LANG: Dict[str, Any] = {}
_WARMED = False
#: #3093 — language -> named reason when an instrument is degraded because an
#: environment dependency is not provisioned. Populated by the no-network
#: guard, read through :func:`degraded_reason`.
_DEGRADED: Dict[str, str] = {}
_CMUDICT_PRESENT: Optional[bool] = None


def cmudict_available() -> bool:
    """True when NLTK's CMUdict corpus is ALREADY provisioned (#3093).

    Reads the NLTK data search path only — this function never downloads.
    The result is cached for the process: the corpus is provisioned by the
    environment (``setup_project_env.ps1``), not conjured mid-run.
    """
    global _CMUDICT_PRESENT
    if _CMUDICT_PRESENT is None:
        try:
            import nltk

            nltk.data.find("corpora/cmudict")
            _CMUDICT_PRESENT = True
        except LookupError:
            _CMUDICT_PRESENT = False
    return _CMUDICT_PRESENT


def degraded_reason(lang: str) -> Optional[str]:
    """The named reason ``lang``'s Flesch is degraded, or None (#3093).

    ``"cmudict-missing"`` for English when the corpus is not provisioned —
    the metric then honestly returns ``None`` instead of fetching the
    corpus at run time. Other languages are unaffected (their syllable
    dictionaries ship with pyphen).
    """
    if lang == "en" and not cmudict_available():
        return "cmudict-missing"
    return _DEGRADED.get(lang)


def detect_language(text: str) -> str:
    """'de' / 'fr' / 'en' / 'unknown', via the orchestrator heuristic."""
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        _detect_language,
    )

    return _detect_language(text)


def _flesch_instance(lang: str) -> Any:
    """The dedicated textstatistics instance for ``lang`` (cached)."""
    instance = _FLESCH_BY_LANG.get(lang)
    if instance is None:
        from textstat.textstat import textstatistics

        instance = textstatistics()
        instance.set_lang(lang)
        _FLESCH_BY_LANG[lang] = instance
    return instance


def warm_up() -> None:
    """Pay textstat's first-use cost once, outside any timed path.

    One Flesch call per supported language performs the lazy dictionary
    load (CMUdict for 'en', pyphen for 'fr'/'de') under the lock, so no
    timed measurement absorbs it later.

    #3093: the English call is the one textstat would turn into a NETWORK
    FETCH when the corpus is not provisioned (its lazy loader downloads
    'cmudict' with ``quiet=True`` on a LookupError). When it is not
    provisioned the call is skipped — the constructor that calls this
    warm-up never touches the network, and the English metric degrades
    with its cause named (:func:`degraded_reason`) instead of raising.
    """
    global _WARMED
    with _LOCK:
        if _WARMED:
            return
        for lang in sorted(SUPPORTED_LANGUAGES):
            reason = degraded_reason(lang)
            if reason:
                _DEGRADED[lang] = reason
                logger.warning(
                    "Flesch %r dégradé (%s) : corpus NLTK non provisionné — "
                    "aucun téléchargement au run (#3093) ; la métrique "
                    "retourne None avec sa cause. Provisionner via "
                    "setup_project_env.ps1 pour la rétablir.",
                    lang,
                    reason,
                )
                continue
            _flesch_instance(lang).flesch_reading_ease(
                "Une phrase de mise en route. Puis une autre."
            )
        _WARMED = True


def flesch_reading_ease_for(
    text: str, lang: Optional[str] = None
) -> Tuple[Optional[float], str]:
    """Flesch reading ease computed with ``lang``'s formula.

    Returns ``(score, lang)``. When ``lang`` is None the language is
    detected from the text. A language without Flesch support here yields
    ``(None, lang)`` — no English-scale number for a non-English text.
    #3093: English yields ``(None, "en")`` when CMUdict is not provisioned
    — the corpus is NOT fetched at run time; :func:`degraded_reason` names
    the cause.

    #2588 review: the first Flesch call per language performs textstat's
    lazy dictionary load (CMUdict for 'en', pyphen for 'fr'/'de'), which
    is not thread-safe on first use (#2353). It therefore runs under the
    lock: whichever caller arrives first pays it once, and only for the
    language it scores — a French first call does not load CMUdict.
    """
    if lang is None:
        lang = detect_language(text)
    if lang not in SUPPORTED_LANGUAGES:
        return None, lang
    if lang == "en" and degraded_reason(lang):
        # #3093 — the guard, not the network: reaching textstat here with
        # the corpus absent would download it (quiet=True) from inside a
        # measurement path, or a constructor.
        _DEGRADED["en"] = degraded_reason(lang) or "cmudict-missing"
        return None, lang
    with _LOCK:
        score = _flesch_instance(lang).flesch_reading_ease(text)
    return float(score), lang
