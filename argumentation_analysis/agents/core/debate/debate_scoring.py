"""
Argument analysis and scoring — 8-metric evaluation system.

Extracted from enhanced_argumentation_main.py ArgumentAnalyzer class.
"""

import logging
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

from ..text_scoring import (
    SUPPORTED_LANGUAGES,
    detect_language,
    flesch_reading_ease_for,
    warm_up,
)
from .debate_definitions import ArgumentMetrics, EnhancedArgument

logger = logging.getLogger(__name__)

# #2344: function words carried the overlap. Two unrelated French sentences
# scored 0.27 relevance on "la", "le", "de", "est" alone, and ``str.split``
# kept punctuation, so "Non." never matched "non". Content words only.
_FUNCTION_WORDS_TEXT = """
    a au aux avec c ce ces cet cette d dans de des du elle elles en est et il
    ils j je l la le les leur leurs lui m mais me même n ne nous on ont ou par
    pas pour qu que qui s sa se ses son sont sur t ta te tes ton tu un une vos
    votre vous y à été être
    an and are as at be been but by can do does for from had has have he her
    his i if in is it its me my no not of on or our she so than that the their
    them then there these they this those to was we were what when which who
    will with would you your
"""
_FUNCTION_WORDS = frozenset(_FUNCTION_WORDS_TEXT.split())

# Weights of the persuasiveness combination; a metric left at None drops out.
_PERSUASIVENESS_WEIGHTS = (
    ("logical_coherence", 0.25),
    ("evidence_quality", 0.25),
    ("relevance_score", 0.15),
    ("readability_score", 0.15),
    ("fact_check_score", 0.10),
    ("novelty_score", 0.10),
)


def _content_words(text: str) -> Set[str]:
    return {w for w in re.findall(r"\w+", text.lower()) if w not in _FUNCTION_WORDS}


def _overlap(words: Set[str], other: Set[str]) -> float:
    return len(words & other) / max(len(words), len(other))


_PATTERN_CACHE: Dict[str, re.Pattern[str]] = {}


def _indicator_pattern(indicator: str) -> re.Pattern[str]:
    pattern = _PATTERN_CACHE.get(indicator)
    if pattern is None:
        pattern = re.compile(rf"\b{re.escape(indicator)}\b", re.IGNORECASE)
        _PATTERN_CACHE[indicator] = pattern
    return pattern


def _count_indicators(content: str, indicators: Iterable[str]) -> int:
    """Count indicators present at word boundaries (#2588).

    Substring matching counted "none" inside "nonetheless", and would
    count "tous" inside "toujours" once French absolutes were listed.
    """
    return sum(
        1 for indicator in indicators if _indicator_pattern(indicator).search(content)
    )


def _union(per_language: Dict[str, Tuple[str, ...]]) -> Tuple[str, ...]:
    """Deduplicated union of the per-language word lists (#2588 review).

    The evidence/emotion lists share five words across languages with the
    same meaning; the dedup keeps each counted once.
    """
    return tuple(dict.fromkeys(w for words in per_language.values() for w in words))


class ArgumentAnalyzer:
    """Multi-dimensional argument quality analyzer.

    Evaluates arguments on 8 metrics: logical coherence, evidence quality,
    relevance, emotional appeal, readability, fact-check score, novelty,
    and overall persuasiveness.
    """

    def __init__(self):
        self.logical_indicators = [
            # English connectors
            "therefore",
            "because",
            "since",
            "thus",
            "hence",
            "consequently",
            "as a result",
            "it follows that",
            "given that",
            "due to",
            # French connectors (#967)
            "donc",
            "parce que",
            "car",
            "ainsi",
            "par conséquent",
            "puisque",
            "c'est pourquoi",
            "en effet",
            "cependant",
            "néanmoins",
        ]
        # #2588: word lists are language-bound. Unaccented variants are
        # listed alongside accented ones — corpus texts are often typed
        # without diacritics.
        self.hedging_indicators = {
            "en": (
                "might",
                "could",
                "possibly",
                "perhaps",
                "likely",
                "probably",
            ),
            "fr": (
                "peut-être",
                "peut etre",
                "pourrait",
                "pourraient",
                "probablement",
                "possiblement",
                "sans doute",
                "éventuellement",
                "eventuellement",
                "il est possible",
                "il se peut",
            ),
            "de": (
                "vielleicht",
                "könnte",
                "koennte",
                "könnten",
                "koennten",
                "möglicherweise",
                "moeglicherweise",
                "wahrscheinlich",
                "eventuell",
                "scheint",
            ),
        }
        self.absolute_indicators = {
            "en": (
                "always",
                "never",
                "all",
                "none",
                "definitely",
                "certainly",
            ),
            "fr": (
                "toujours",
                "jamais",
                "tous",
                "toutes",
                "aucun",
                "aucune",
                "absolument",
                "certainement",
                "nécessairement",
                "necessairement",
                "indéniablement",
                "indeniablement",
                "totalement",
            ),
            "de": (
                "immer",
                "nie",
                "niemals",
                "alle",
                "kein",
                "keine",
                "bestimmt",
                "sicherlich",
                "absolut",
                "gewiss",
                "unbestreitbar",
            ),
        }
        self.evidence_indicators = {
            "en": (
                "studies show",
                "research indicates",
                "data suggests",
                "according to",
                "evidence",
                "statistics",
                "findings",
                "survey",
                "analysis",
                "report",
            ),
            "fr": (
                "études montrent",
                "etudes montrent",
                "recherche indique",
                "données suggèrent",
                "donnees suggerent",
                "données montrent",
                "donnees montrent",
                "données",
                "donnees",
                "selon",
                "preuves",
                "statistiques",
                "constats",
                "enquête",
                "enquete",
                "sondage",
                "analyse",
                "rapport",
                "résultats",
                "resultats",
            ),
            "de": (
                "studien zeigen",
                "untersuchungen zeigen",
                "daten legen nahe",
                "daten zeigen",
                "laut",
                "belege",
                "belegt",
                "beweise",
                "statistiken",
                "ergebnisse",
                "umfrage",
                "analyse",
                "bericht",
            ),
        }
        self.study_words = {
            "en": ("study", "university", "journal", "published"),
            "fr": (
                "étude",
                "etude",
                "université",
                "universite",
                "revue",
                "publié",
                "publie",
            ),
            "de": (
                "studie",
                "universität",
                "universitaet",
                "zeitschrift",
                "veröffentlicht",
                "veroeffentlicht",
            ),
        }
        self.emotional_indicators = {
            "en": (
                "feel",
                "feels",
                "feeling",
                "believe",
                "believes",
                "think",
                "thinks",
                "important",
                "crucial",
                "vital",
                "devastating",
                "wonderful",
                "terrible",
                "amazing",
            ),
            "fr": (
                "ressens",
                "ressentir",
                "croire",
                "crois",
                "pense que",
                "penser que",
                "important",
                "crucial",
                "vital",
                "dévastateur",
                "devastateur",
                "merveilleux",
                "terrible",
                "extraordinaire",
                "catastrophe",
                "gravissime",
                "peur",
                "espoir",
            ),
            "de": (
                "fühle",
                "fuehle",
                "fühlen",
                "glaube",
                "denke",
                "wichtig",
                "entscheidend",
                "verheerend",
                "wunderbar",
                "schrecklich",
                "katastrophe",
            ),
        }
        # #2588: textstat's first-use cost (CMUdict/pyphen load) is paid
        # here, once per process, so no timed measurement absorbs it later.
        # Measured construction cost: ~1.55 s and ~590 modules on the first
        # construction in a process (coordinator review of PR #2666).
        warm_up()
        # #2588 review: when no context decides the language and the detector
        # cannot either (below 3 function-word hits), the word instruments
        # run on the union of the three languages — the hedging/absolute
        # lists are disjoint, the evidence/emotion lists share five words
        # with the same meaning in both, so a deduplicated union counts
        # each once. "might" is hedging whichever list recognises it, and
        # no language is ever guessed.
        self._hedging_union = _union(self.hedging_indicators)
        self._absolute_union = _union(self.absolute_indicators)
        self._evidence_union = _union(self.evidence_indicators)
        self._study_union = _union(self.study_words)
        self._emotional_union = _union(self.emotional_indicators)

    def analyze_argument(
        self,
        argument: EnhancedArgument,
        context: List[EnhancedArgument],
        lang: Optional[str] = None,
    ) -> ArgumentMetrics:
        """Comprehensive argument analysis across all 8 metrics.

        #2588 review: ``lang`` is the language decided where there is
        enough text to decide one — the document or debate context the
        caller holds. ``None`` detects on the argument's own content and,
        failing that, falls back to the lexicon union for the word lists
        (readability stays ``None``: no formula is picked by guessing).
        """
        content = argument.content
        metrics = ArgumentMetrics()
        metrics.logical_coherence = self._assess_logical_coherence(content)
        metrics.evidence_quality = self._assess_evidence_quality(content, lang)
        metrics.relevance_score = self._assess_relevance(argument, context)
        metrics.emotional_appeal = self._assess_emotional_appeal(content, lang)
        metrics.readability_score = self._assess_readability(content, lang)
        metrics.fact_check_score = self._basic_fact_check(content, lang)
        metrics.novelty_score = self._assess_novelty(argument, context)
        metrics.persuasiveness = self._calculate_persuasiveness(metrics)
        return metrics

    def _assess_logical_coherence(self, content: str) -> float:
        """Assess logical structure via connector detection."""
        score = 0.5
        logical_count = sum(
            1
            for indicator in self.logical_indicators
            if indicator.lower() in content.lower()
        )
        score += min(logical_count * 0.1, 0.3)
        if "first" in content.lower() and "second" in content.lower():
            score += 0.1
        if "premièrement" in content.lower() and "deuxièmement" in content.lower():
            score += 0.1
        if any(
            word in content.lower()
            for word in [
                "premise",
                "conclusion",
                "assumption",
                "prémisse",
                "conclusion",
                "hypothèse",  # FR structural (#967)
            ]
        ):
            score += 0.1
        return min(score, 1.0)

    def _assess_evidence_quality(
        self, content: str, lang: Optional[str] = None
    ) -> float:
        """Assess presence of evidence (citations, numbers, references).

        #2588: indicators and study words match in the text's language;
        numbers are language-independent and always count. With no
        decidable language and no ``lang``, the union of the three
        lexicons runs (#2588 review).
        """
        lang = lang or detect_language(content)
        score = 0.3
        evidence_count = _count_indicators(
            content, self.evidence_indicators.get(lang, self._evidence_union)
        )
        score += min(evidence_count * 0.15, 0.4)
        numbers = re.findall(r"\d+(?:\.\d+)?%?", content)
        if numbers:
            score += min(len(numbers) * 0.05, 0.2)
        if _count_indicators(content, self.study_words.get(lang, self._study_union)):
            score += 0.1
        return min(score, 1.0)

    def _assess_relevance(
        self, argument: EnhancedArgument, context: List[EnhancedArgument]
    ) -> Optional[float]:
        """Assess relevance via content-word overlap with recent arguments.

        #2344: ``None`` when there is nothing to compare with: no context, or no
        content word on either side. It used to return a constant 0.8 there,
        and ``DebatePlugin.analyze_argument_quality`` always passes no context.
        """
        arg_words = _content_words(argument.content)
        scores = [
            _overlap(arg_words, prev_words)
            for prev_words in (_content_words(a.content) for a in context[-3:])
            if arg_words and prev_words
        ]
        return max(scores) if scores else None

    def _assess_emotional_appeal(
        self, content: str, lang: Optional[str] = None
    ) -> float:
        """Detect emotional language and rhetorical devices.

        #2588: indicators match in the text's language; exclamation marks
        and all-caps words are language-independent and always count. With
        no decidable language and no ``lang``, the union of the three
        lexicons runs (#2588 review).
        """
        lang = lang or detect_language(content)
        words = self.emotional_indicators.get(lang, self._emotional_union)
        emotional_count = _count_indicators(content, words)
        exclamations = content.count("!")
        caps_words = sum(
            1 for word in content.split() if word.isupper() and len(word) > 2
        )
        return min(
            (emotional_count * 0.1) + (exclamations * 0.05) + (caps_words * 0.05), 1.0
        )

    def _assess_readability(
        self, content: str, lang: Optional[str] = None
    ) -> Optional[float]:
        """Assess readability via Flesch, with the text language's formula.

        #2588: ``None`` when no language can be picked — an English-scale
        number on a non-English text is not a measurement. The detector
        rarely decides below ~20 words, so callers holding a longer text
        (the document, the debate context) should pass ``lang`` (#2588
        review); Flesch on a handful of words is not a measure in any
        language. textstat is a required dependency: an import failure
        propagates.
        """
        score, _lang = flesch_reading_ease_for(content, lang)
        if score is None:
            return None
        return max(0.0, min(1.0, score / 100.0))

    def _basic_fact_check(self, content: str, lang: Optional[str] = None) -> float:
        """Heuristic fact-check: hedging vs absolute language.

        #2588: the word lists are language-bound — the English lists on a
        French text returned the neutral 0.6 constant on every input. With
        no decidable language and no ``lang``, the union of the three
        languages' lists runs instead of guessing one (review): the lists
        are disjoint, so the counts stay meaningful.
        """
        lang = lang or detect_language(content)
        hedging_words = self.hedging_indicators.get(lang, self._hedging_union)
        absolute_words = self.absolute_indicators.get(lang, self._absolute_union)
        hedging_count = _count_indicators(content, hedging_words)
        absolute_count = _count_indicators(content, absolute_words)
        if hedging_count > absolute_count:
            return 0.7
        elif absolute_count > hedging_count:
            return 0.4
        else:
            return 0.6

    def _assess_novelty(
        self, argument: EnhancedArgument, context: List[EnhancedArgument]
    ) -> Optional[float]:
        """Assess originality by comparing with opponent arguments.

        #2344: ``None`` when no opponent argument with content words exists to
        compare with. It used to return 0.8 without context, and 1.0 when every
        earlier argument was the agent's own.
        """
        arg_words = _content_words(argument.content)
        similarities = [
            _overlap(arg_words, prev_words)
            for prev_words in (
                _content_words(a.content)
                for a in context
                if a.agent_name != argument.agent_name
            )
            if arg_words and prev_words
        ]
        if not similarities:
            return None
        return max(0.0, 1 - sum(similarities) / len(similarities))

    def _calculate_persuasiveness(self, metrics: ArgumentMetrics) -> float:
        """Weighted mean of the metrics that were computed.

        #2344: a metric left at ``None`` (relevance, novelty) drops out and the
        remaining weights are renormalized, instead of a constant counting in
        its place.
        """
        computed = [
            (value, weight)
            for value, weight in (
                (getattr(metrics, name), weight)
                for name, weight in _PERSUASIVENESS_WEIGHTS
            )
            if value is not None
        ]
        total = sum(weight for _, weight in computed)
        return min(sum(value * weight for value, weight in computed) / total, 1.0)
