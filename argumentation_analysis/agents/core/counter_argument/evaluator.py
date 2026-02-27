"""
Counter-argument quality evaluator.

Evaluates counter-arguments on 5 weighted criteria: relevance (0.25),
logical strength (0.25), persuasiveness (0.20), originality (0.15),
and clarity (0.15). Uses French-language NLP heuristics (no LLM required).

Adapted from 2.3.3-generation-contre-argument/counter_agent/evaluation/evaluator.py.
"""

import re
import logging
from typing import List, Set

from .definitions import (
    Argument,
    CounterArgument,
    CounterArgumentType,
    ArgumentStrength,
    EvaluationResult,
)

logger = logging.getLogger(__name__)


class CounterArgumentEvaluator:
    """Evaluate counter-argument quality on 5 criteria."""

    def __init__(self):
        self.evaluation_criteria = {
            "relevance": 0.25,
            "logical_strength": 0.25,
            "persuasiveness": 0.20,
            "originality": 0.15,
            "clarity": 0.15,
        }
        self.persuasive_elements = [
            "exemple",
            "preuve",
            "étude",
            "données",
            "expert",
            "recherche",
            "statistique",
            "évidence",
            "démontré",
            "prouvé",
            "consensus",
            "observation",
            "expérience",
            "analyse",
            "résultat",
        ]
        self.logical_markers = [
            "parce que",
            "car",
            "donc",
            "ainsi",
            "par conséquent",
            "puisque",
            "en raison de",
            "il s'ensuit que",
            "implique",
            "prouve",
            "démontre",
            "conduit à",
        ]

    def evaluate(
        self, original_argument: Argument, counter_argument: CounterArgument
    ) -> EvaluationResult:
        """Evaluate a counter-argument's quality."""
        relevance = self._evaluate_relevance(original_argument, counter_argument)
        logical_strength = self._evaluate_logical_strength(counter_argument)
        persuasiveness = self._evaluate_persuasiveness(counter_argument)
        originality = self._evaluate_originality(counter_argument)
        clarity = self._evaluate_clarity(counter_argument)

        overall_score = sum(
            score * weight
            for score, weight in zip(
                [relevance, logical_strength, persuasiveness, originality, clarity],
                self.evaluation_criteria.values(),
            )
        )

        recommendations = self._generate_recommendations(
            original_argument,
            counter_argument,
            relevance,
            logical_strength,
            persuasiveness,
            originality,
            clarity,
        )

        return EvaluationResult(
            relevance=relevance,
            logical_strength=logical_strength,
            persuasiveness=persuasiveness,
            originality=originality,
            clarity=clarity,
            overall_score=overall_score,
            recommendations=recommendations,
        )

    def _evaluate_relevance(
        self, original_argument: Argument, counter_argument: CounterArgument
    ) -> float:
        """Evaluate relevance via keyword overlap and targeting."""
        original_keywords = self._extract_keywords(original_argument.content)
        counter_keywords = self._extract_keywords(counter_argument.counter_content)

        keyword_overlap = (
            len(original_keywords.intersection(counter_keywords))
            / len(original_keywords)
            if original_keywords
            else 0
        )

        target_match = 0.0
        if counter_argument.counter_type == CounterArgumentType.PREMISE_CHALLENGE:
            premise_kw = set()
            for premise in original_argument.premises:
                premise_kw.update(self._extract_keywords(premise))
            target_match = (
                len(premise_kw.intersection(counter_keywords)) / len(premise_kw)
                if premise_kw
                else 0
            )
        elif counter_argument.counter_type == CounterArgumentType.DIRECT_REFUTATION:
            conclusion_kw = self._extract_keywords(original_argument.conclusion)
            target_match = (
                len(conclusion_kw.intersection(counter_keywords)) / len(conclusion_kw)
                if conclusion_kw
                else 0
            )

        mentions = (
            1.0 if "argument" in counter_argument.counter_content.lower() else 0.0
        )

        relevance = 0.4 * keyword_overlap + 0.5 * target_match + 0.1 * mentions

        # Strategy bonus
        if (
            counter_argument.counter_type == CounterArgumentType.COUNTER_EXAMPLE
            and "analogical" in counter_argument.rhetorical_strategy
        ):
            relevance += 0.1
        elif (
            counter_argument.counter_type == CounterArgumentType.PREMISE_CHALLENGE
            and "socratic" in counter_argument.rhetorical_strategy
        ):
            relevance += 0.1

        return min(relevance, 1.0)

    def _evaluate_logical_strength(self, counter_argument: CounterArgument) -> float:
        """Evaluate logical strength via type, markers, and structure."""
        type_strengths = {
            CounterArgumentType.DIRECT_REFUTATION: 0.7,
            CounterArgumentType.COUNTER_EXAMPLE: 0.8,
            CounterArgumentType.ALTERNATIVE_EXPLANATION: 0.6,
            CounterArgumentType.PREMISE_CHALLENGE: 0.7,
            CounterArgumentType.REDUCTIO_AD_ABSURDUM: 0.8,
        }
        base = type_strengths.get(counter_argument.counter_type, 0.5)

        content_lower = counter_argument.counter_content.lower()
        logical_score = (
            0.1 if any(m in content_lower for m in self.logical_markers) else 0.0
        )

        has_premise = any(m in content_lower for m in ["car", "parce que", "puisque"])
        has_conclusion = any(
            m in content_lower for m in ["donc", "ainsi", "par conséquent"]
        )
        structure = (0.1 if has_premise else 0.0) + (0.1 if has_conclusion else 0.0)

        evidence = (
            0.1
            if any(w in content_lower for w in ["preuve", "exemple", "cas", "étude"])
            else 0.0
        )

        fallacies = [
            "ad hominem",
            "homme de paille",
            "faux dilemme",
            "pente glissante",
            "ad populum",
        ]
        fallacy_free = 0.1 if not any(f in content_lower for f in fallacies) else 0.0

        strength_adj = {
            ArgumentStrength.WEAK: -0.1,
            ArgumentStrength.MODERATE: 0.0,
            ArgumentStrength.STRONG: 0.1,
            ArgumentStrength.DECISIVE: 0.2,
        }

        total = (
            base
            + logical_score
            + structure
            + evidence
            + fallacy_free
            + strength_adj.get(counter_argument.strength, 0.0)
        )
        return min(total, 1.0)

    def _evaluate_persuasiveness(self, counter_argument: CounterArgument) -> float:
        """Evaluate persuasiveness via elements, rhetoric, tone, length."""
        content_lower = counter_argument.counter_content.lower()

        persuasive_count = sum(
            1 for e in self.persuasive_elements if e in content_lower
        )
        persuasive_score = min(persuasive_count * 0.1, 0.5)

        rhetoric_scores = {
            "socratic_questioning": 0.8,
            "reductio_ad_absurdum": 0.7,
            "analogical_counter": 0.6,
            "authority_appeal": 0.5,
            "statistical_evidence": 0.8,
        }
        rhetoric_score = 0.2
        for name, score in rhetoric_scores.items():
            if name in counter_argument.rhetorical_strategy:
                rhetoric_score = score * 0.3
                break

        affirm = ["clairement", "certainement", "évidemment", "sans doute"]
        dubious = ["peut-être", "probablement", "possiblement", "il se pourrait"]
        tone = 0.1 * (
            sum(1 for w in affirm if w in content_lower)
            - sum(1 for w in dubious if w in content_lower) * 0.5
        )
        tone = max(min(tone, 0.2), 0.0)

        word_count = len(content_lower.split())
        length_score = (
            0.1 if 30 <= word_count <= 100 else (0.05 if word_count > 100 else 0.0)
        )

        return min(persuasive_score + rhetoric_score + tone + length_score, 1.0)

    def _evaluate_originality(self, counter_argument: CounterArgument) -> float:
        """Evaluate originality via vocabulary and strategy combination."""
        content = counter_argument.counter_content

        common_phrases = [
            "tout le monde sait que",
            "comme on dit souvent",
            "il est bien connu que",
            "évidemment",
            "bien entendu",
        ]
        penalty = min(sum(1 for p in common_phrases if p in content.lower()) * 0.1, 0.3)

        strategy_orig = 0.2
        if (
            counter_argument.counter_type == CounterArgumentType.DIRECT_REFUTATION
            and "socratic" in counter_argument.rhetorical_strategy
        ):
            strategy_orig = 0.4
        elif (
            counter_argument.counter_type == CounterArgumentType.PREMISE_CHALLENGE
            and "analogical" in counter_argument.rhetorical_strategy
        ):
            strategy_orig = 0.4

        unique = set(re.findall(r"\b\w{4,}\b", content.lower()))
        words = len(content.split())
        vocab_score = min((len(unique) / words * 2) if words else 0, 0.3)

        unexpected = [
            "contrairement à ce qu'on pourrait penser",
            "sous un angle différent",
            "perspective alternative",
        ]
        unexpected_score = 0.2 if any(u in content.lower() for u in unexpected) else 0.0

        originality = 0.5 + strategy_orig + vocab_score + unexpected_score - penalty
        return min(max(originality, 0.1), 1.0)

    def _evaluate_clarity(self, counter_argument: CounterArgument) -> float:
        """Evaluate clarity via sentence length, structure, connectors."""
        content = counter_argument.counter_content
        avg_len = self._average_sentence_length(content)

        sentence_score = 0.3 if avg_len < 25 else (0.2 if avg_len < 35 else 0.1)
        structure_score = 0.2 if self._has_structure(content) else 0.0

        connectors = [
            "car",
            "parce que",
            "puisque",
            "donc",
            "ainsi",
            "en effet",
            "cependant",
            "toutefois",
            "néanmoins",
            "de plus",
            "ensuite",
        ]
        connector_score = 0.2 if any(c in content.lower() for c in connectors) else 0.0

        ambiguity = ["peut-être", "possiblement", "il se pourrait", "plus ou moins"]
        ambiguity_penalty = min(
            sum(1 for m in ambiguity if m in content.lower()) * 0.05, 0.2
        )

        complexity = self._vocabulary_complexity(content)
        vocab_score = 0.2 if complexity < 0.3 else 0.1

        total = (
            sentence_score
            + structure_score
            + connector_score
            + vocab_score
            - ambiguity_penalty
        )
        return min(max(total, 0.1), 1.0)

    def _generate_recommendations(
        self,
        original: Argument,
        counter: CounterArgument,
        relevance: float,
        logic: float,
        persuasion: float,
        originality: float,
        clarity: float,
    ) -> List[str]:
        """Generate improvement recommendations for weak criteria."""
        recs = []
        threshold = 0.6

        if relevance < threshold:
            recs.append("Improve relevance to the original argument")
        if logic < threshold:
            recs.append("Strengthen logical structure with connectors")
        if persuasion < threshold:
            recs.append("Add persuasive elements (examples, evidence)")
        if originality < threshold:
            recs.append("Develop a more original angle")
        if clarity < threshold:
            recs.append("Simplify formulation with shorter sentences")
        if all(
            s >= threshold for s in [relevance, logic, persuasion, originality, clarity]
        ):
            recs.append("Counter-argument is of good quality")

        return recs

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract non-stopword keywords."""
        text = re.sub(r"[^\w\s]", "", text.lower())
        stops = {
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "et",
            "ou",
            "mais",
            "car",
            "donc",
            "si",
            "que",
            "qui",
            "est",
            "sont",
            "a",
            "ont",
            "pour",
            "dans",
            "par",
            "sur",
            "avec",
            "sans",
            "ce",
            "cette",
            "de",
            "du",
            "au",
            "aux",
            "en",
            "y",
        }
        return {w for w in text.split() if w not in stops and len(w) > 3}

    def _average_sentence_length(self, text: str) -> float:
        """Average sentence length in words."""
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        if not sentences:
            return 0.0
        return sum(len(s.split()) for s in sentences) / len(sentences)

    def _has_structure(self, text: str) -> bool:
        """Check for structural markers."""
        markers = [
            "premièrement",
            "tout d'abord",
            "ensuite",
            "de plus",
            "en conclusion",
            "pour conclure",
            "ainsi",
            "donc",
        ]
        return any(m in text.lower() for m in markers)

    def _vocabulary_complexity(self, text: str) -> float:
        """Assess vocabulary complexity (0=simple, 1=complex)."""
        complex_words = [
            "paradigme",
            "ontologie",
            "épistémologie",
            "herméneutique",
            "heuristique",
            "axiomatique",
            "syllogisme",
            "dialectique",
        ]
        words = text.lower().split()
        if not words:
            return 0.0
        count = sum(1 for w in words if w in complex_words)
        long = sum(1 for w in words if len(w) > 8)
        return min((count + long * 0.5) / len(words), 1.0)
