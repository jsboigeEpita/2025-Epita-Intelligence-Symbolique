"""
Argument analysis and scoring — 8-metric evaluation system.

Extracted from enhanced_argumentation_main.py ArgumentAnalyzer class.
"""

import logging
import re
from typing import List

from .debate_definitions import ArgumentMetrics, EnhancedArgument

logger = logging.getLogger(__name__)


class ArgumentAnalyzer:
    """Multi-dimensional argument quality analyzer.

    Evaluates arguments on 8 metrics: logical coherence, evidence quality,
    relevance, emotional appeal, readability, fact-check score, novelty,
    and overall persuasiveness.
    """

    def __init__(self):
        self.logical_indicators = [
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
        ]
        self.evidence_indicators = [
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
        ]
        self.emotional_indicators = [
            "feel",
            "believe",
            "think",
            "important",
            "crucial",
            "vital",
            "devastating",
            "wonderful",
            "terrible",
            "amazing",
        ]

    def analyze_argument(
        self, argument: EnhancedArgument, context: List[EnhancedArgument]
    ) -> ArgumentMetrics:
        """Comprehensive argument analysis across all 8 metrics."""
        metrics = ArgumentMetrics()
        metrics.logical_coherence = self._assess_logical_coherence(argument.content)
        metrics.evidence_quality = self._assess_evidence_quality(argument.content)
        metrics.relevance_score = self._assess_relevance(argument, context)
        metrics.emotional_appeal = self._assess_emotional_appeal(argument.content)
        metrics.readability_score = self._assess_readability(argument.content)
        metrics.fact_check_score = self._basic_fact_check(argument.content)
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
        if any(
            word in content.lower() for word in ["premise", "conclusion", "assumption"]
        ):
            score += 0.1
        return min(score, 1.0)

    def _assess_evidence_quality(self, content: str) -> float:
        """Assess presence of evidence (citations, numbers, references)."""
        score = 0.3
        evidence_count = sum(
            1
            for indicator in self.evidence_indicators
            if indicator.lower() in content.lower()
        )
        score += min(evidence_count * 0.15, 0.4)
        numbers = re.findall(r"\d+(?:\.\d+)?%?", content)
        if numbers:
            score += min(len(numbers) * 0.05, 0.2)
        if any(
            word in content.lower()
            for word in ["study", "university", "journal", "published"]
        ):
            score += 0.1
        return min(score, 1.0)

    def _assess_relevance(
        self, argument: EnhancedArgument, context: List[EnhancedArgument]
    ) -> float:
        """Assess relevance via keyword overlap with recent arguments."""
        if not context:
            return 0.8
        recent_args = context[-3:] if len(context) >= 3 else context
        arg_words = set(argument.content.lower().split())
        relevance_scores = []
        for prev_arg in recent_args:
            prev_words = set(prev_arg.content.lower().split())
            overlap = len(arg_words.intersection(prev_words))
            relevance_scores.append(overlap / max(len(arg_words), len(prev_words)))
        return max(relevance_scores) if relevance_scores else 0.5

    def _assess_emotional_appeal(self, content: str) -> float:
        """Detect emotional language and rhetorical devices."""
        emotional_count = sum(
            1
            for indicator in self.emotional_indicators
            if indicator.lower() in content.lower()
        )
        exclamations = content.count("!")
        caps_words = sum(
            1 for word in content.split() if word.isupper() and len(word) > 2
        )
        return min(
            (emotional_count * 0.1) + (exclamations * 0.05) + (caps_words * 0.05), 1.0
        )

    def _assess_readability(self, content: str) -> float:
        """Assess readability using textstat or fallback heuristic."""
        try:
            from textstat import flesch_reading_ease

            flesch_score = flesch_reading_ease(content)
            return max(0, min(1, flesch_score / 100))
        except (ImportError, Exception):
            sentences = content.split(".")
            if not sentences:
                return 0.5
            avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
            return max(0, min(1, 1 - (avg_length - 15) / 20))

    def _basic_fact_check(self, content: str) -> float:
        """Heuristic fact-check: hedging vs absolute language."""
        hedging = ["might", "could", "possibly", "perhaps", "likely", "probably"]
        absolute = ["always", "never", "all", "none", "definitely", "certainly"]
        hedging_count = sum(1 for w in hedging if w in content.lower())
        absolute_count = sum(1 for w in absolute if w in content.lower())
        if hedging_count > absolute_count:
            return 0.7
        elif absolute_count > hedging_count:
            return 0.4
        else:
            return 0.6

    def _assess_novelty(
        self, argument: EnhancedArgument, context: List[EnhancedArgument]
    ) -> float:
        """Assess originality by comparing with opponent arguments."""
        if not context:
            return 0.8
        arg_phrases = set(argument.content.lower().split())
        similarity_scores = []
        for prev_arg in context:
            if prev_arg.agent_name != argument.agent_name:
                prev_phrases = set(prev_arg.content.lower().split())
                overlap = len(arg_phrases.intersection(prev_phrases))
                similarity = overlap / max(len(arg_phrases), len(prev_phrases))
                similarity_scores.append(similarity)
        avg_similarity = (
            sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0
        )
        return max(0, 1 - avg_similarity)

    def _calculate_persuasiveness(self, metrics: ArgumentMetrics) -> float:
        """Weighted combination of all metrics."""
        return min(
            metrics.logical_coherence * 0.25
            + metrics.evidence_quality * 0.25
            + metrics.relevance_score * 0.15
            + metrics.readability_score * 0.15
            + metrics.fact_check_score * 0.10
            + metrics.novelty_score * 0.10,
            1.0,
        )
