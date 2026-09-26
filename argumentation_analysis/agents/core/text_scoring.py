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
  (en) or pyphen (fr/de) dictionary load (#2398 pattern).
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
    """
    global _WARMED
    with _LOCK:
        if _WARMED:
            return
        for lang in sorted(SUPPORTED_LANGUAGES):
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
    """
    if lang is None:
        lang = detect_language(text)
    if lang not in SUPPORTED_LANGUAGES:
        return None, lang
    score = _flesch_instance(lang).flesch_reading_ease(text)
    return float(score), lang
