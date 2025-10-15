"""
Évaluation de la qualité des contre-arguments.

Ce module fournit des fonctionnalités pour évaluer la qualité
des contre-arguments selon différents critères.
"""

import re
import logging
from typing import Dict, List, Any, Tuple, Optional, Set

from ..agent.definitions import (
    Argument,
    CounterArgument,
    CounterArgumentType,
    ArgumentStrength,
    RhetoricalStrategy,
    EvaluationResult,
)

logger = logging.getLogger(__name__)


class CounterArgumentEvaluator:
    """
    Classe pour évaluer la qualité des contre-arguments.
    """

    def __init__(self):
        """Initialise l'évaluateur de contre-arguments."""
        # Définir les poids pour les différents critères d'évaluation
        self.evaluation_criteria = {
            "relevance": 0.25,
            "logical_strength": 0.25,
            "persuasiveness": 0.20,
            "originality": 0.15,
            "clarity": 0.15,
        }

        # Listes de mots pour l'évaluation
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
            "si...alors",
            "implique",
            "prouve",
            "démontre",
            "conduit à",
        ]

        # Caractéristiques de clarté
        self.clarity_features = {
            "short_sentences": lambda text: self._average_sentence_length(text) < 25,
            "common_vocab": lambda text: self._assess_vocabulary_complexity(text) < 0.3,
            "structured": lambda text: self._has_clear_structure(text),
            "connects_ideas": lambda text: self._has_connectors(text),
        }

        logger.info("CounterArgumentEvaluator initialisé")

    def evaluate(
        self, original_argument: Argument, counter_argument: CounterArgument
    ) -> EvaluationResult:
        """
        Évalue la qualité d'un contre-argument.

        Args:
            original_argument: L'argument original
            counter_argument: Le contre-argument à évaluer

        Returns:
            Un objet EvaluationResult contenant l'évaluation
        """
        logger.info(
            f"Évaluation d'un contre-argument de type {counter_argument.counter_type.value}"
        )

        # Calculer les scores individuels
        relevance = self._evaluate_relevance(original_argument, counter_argument)
        logical_strength = self._evaluate_logical_strength(counter_argument)
        persuasiveness = self._evaluate_persuasiveness(counter_argument)
        originality = self._evaluate_originality(counter_argument)
        clarity = self._evaluate_clarity(counter_argument)

        # Calculer le score global
        overall_score = sum(
            score * weight
            for score, weight in zip(
                [relevance, logical_strength, persuasiveness, originality, clarity],
                self.evaluation_criteria.values(),
            )
        )

        # Générer des recommandations
        recommendations = self._generate_recommendations(
            original_argument,
            counter_argument,
            relevance,
            logical_strength,
            persuasiveness,
            originality,
            clarity,
        )

        # Créer l'objet de résultat
        result = EvaluationResult(
            relevance=relevance,
            logical_strength=logical_strength,
            persuasiveness=persuasiveness,
            originality=originality,
            clarity=clarity,
            overall_score=overall_score,
            recommendations=recommendations,
        )

        logger.debug(f"Évaluation terminée, score global: {overall_score:.2f}")

        return result

    def _evaluate_relevance(
        self, original_argument: Argument, counter_argument: CounterArgument
    ) -> float:
        """
        Évalue la pertinence du contre-argument par rapport à l'argument original.

        Args:
            original_argument: L'argument original
            counter_argument: Le contre-argument à évaluer

        Returns:
            Un score entre 0 et 1
        """
        # Vérifier si le contre-argument cible effectivement l'argument original
        # 1. Chevauchement de mots clés
        original_keywords = self._extract_keywords(original_argument.content)
        counter_keywords = self._extract_keywords(counter_argument.counter_content)

        keyword_overlap_ratio = (
            len(original_keywords.intersection(counter_keywords))
            / len(original_keywords)
            if original_keywords
            else 0
        )

        # 2. Vérifier si le contre-argument cible spécifiquement les prémisses ou la conclusion
        target_match = 0.0
        if counter_argument.counter_type == CounterArgumentType.PREMISE_CHALLENGE:
            # Vérifier si le contre-argument mentionne les prémisses
            premise_keywords = set()
            for premise in original_argument.premises:
                premise_keywords.update(self._extract_keywords(premise))

            premise_match = (
                len(premise_keywords.intersection(counter_keywords))
                / len(premise_keywords)
                if premise_keywords
                else 0
            )
            target_match = premise_match

        elif counter_argument.counter_type == CounterArgumentType.DIRECT_REFUTATION:
            # Vérifier si le contre-argument mentionne la conclusion
            conclusion_keywords = self._extract_keywords(original_argument.conclusion)
            conclusion_match = (
                len(conclusion_keywords.intersection(counter_keywords))
                / len(conclusion_keywords)
                if conclusion_keywords
                else 0
            )
            target_match = conclusion_match

        # 3. Autres facteurs de pertinence
        mentions_argument = (
            1.0 if "argument" in counter_argument.counter_content.lower() else 0.0
        )

        # Combiner les facteurs
        relevance = (
            (0.4 * keyword_overlap_ratio)
            + (0.5 * target_match)
            + (0.1 * mentions_argument)
        )

        # Bonus pour les stratégies rhétoriques pertinentes
        strategy_bonus = 0.0
        if (
            counter_argument.counter_type == CounterArgumentType.COUNTER_EXAMPLE
            and "analogical" in counter_argument.rhetorical_strategy
        ):
            strategy_bonus = 0.1
        elif (
            counter_argument.counter_type == CounterArgumentType.PREMISE_CHALLENGE
            and "socratic" in counter_argument.rhetorical_strategy
        ):
            strategy_bonus = 0.1

        relevance = min(relevance + strategy_bonus, 1.0)

        return relevance

    def _evaluate_logical_strength(self, counter_argument: CounterArgument) -> float:
        """
        Évalue la force logique du contre-argument.

        Args:
            counter_argument: Le contre-argument à évaluer

        Returns:
            Un score entre 0 et 1
        """
        # 1. Force intrinsèque du type de contre-argument
        type_strengths = {
            CounterArgumentType.DIRECT_REFUTATION: 0.7,
            CounterArgumentType.COUNTER_EXAMPLE: 0.8,
            CounterArgumentType.ALTERNATIVE_EXPLANATION: 0.6,
            CounterArgumentType.PREMISE_CHALLENGE: 0.7,
            CounterArgumentType.REDUCTIO_AD_ABSURDUM: 0.8,
        }

        base_strength = type_strengths.get(counter_argument.counter_type, 0.5)

        # 2. Présence de marqueurs logiques
        logical_score = 0.0
        content_lower = counter_argument.counter_content.lower()
        for marker in self.logical_markers:
            if marker in content_lower:
                logical_score += 0.1
                break

        # 3. Structure logique (prémisses -> conclusion)
        has_premise_marker = any(
            marker in content_lower for marker in ["car", "parce que", "puisque"]
        )
        has_conclusion_marker = any(
            marker in content_lower for marker in ["donc", "ainsi", "par conséquent"]
        )

        structure_score = 0.1 if has_premise_marker else 0.0
        structure_score += 0.1 if has_conclusion_marker else 0.0

        # 4. Présence de preuves ou exemples
        evidence_score = (
            0.1
            if any(
                word in content_lower for word in ["preuve", "exemple", "cas", "étude"]
            )
            else 0.0
        )

        # 5. Absence de sophismes communs
        fallacies = [
            "ad hominem",
            "homme de paille",
            "appel à l'autorité",
            "faux dilemme",
            "pente glissante",
            "ad populum",
        ]

        fallacy_free = (
            0.1 if not any(fallacy in content_lower for fallacy in fallacies) else 0.0
        )

        # Combiner les scores
        logical_strength = (
            base_strength
            + logical_score
            + structure_score
            + evidence_score
            + fallacy_free
        )

        # Ajustement en fonction de la force déclarée du contre-argument
        strength_adjustment = {
            ArgumentStrength.WEAK: -0.1,
            ArgumentStrength.MODERATE: 0.0,
            ArgumentStrength.STRONG: 0.1,
            ArgumentStrength.DECISIVE: 0.2,
        }

        logical_strength += strength_adjustment.get(counter_argument.strength, 0.0)

        return min(logical_strength, 1.0)

    def _evaluate_persuasiveness(self, counter_argument: CounterArgument) -> float:
        """
        Évalue le pouvoir de persuasion du contre-argument.

        Args:
            counter_argument: Le contre-argument à évaluer

        Returns:
            Un score entre 0 et 1
        """
        content_lower = counter_argument.counter_content.lower()

        # 1. Présence d'éléments persuasifs
        persuasive_count = sum(
            1 for element in self.persuasive_elements if element in content_lower
        )
        persuasive_score = min(persuasive_count * 0.1, 0.5)

        # 2. Qualité rhétorique
        rhetoric_scores = {
            "socratic_questioning": 0.8,  # Efficace pour engager la réflexion
            "reductio_ad_absurdum": 0.7,  # Puissant mais peut sembler artificiel
            "analogical_counter": 0.6,  # Dépend de la pertinence de l'analogie
            "authority_appeal": 0.5,  # Dépend de l'autorité citée
            "statistical_evidence": 0.8,  # Persuasif si statistiques pertinentes
        }

        rhetoric_score = 0.2
        for strat_name, score in rhetoric_scores.items():
            if strat_name in counter_argument.rhetorical_strategy:
                rhetoric_score = score * 0.3
                break

        # 3. Ton affirmatif vs dubitatif
        tone_words = {
            "affirmatif": [
                "clairement",
                "certainement",
                "évidemment",
                "sans doute",
                "absolument",
            ],
            "dubitatif": [
                "peut-être",
                "probablement",
                "possiblement",
                "il se pourrait",
                "on pourrait penser",
            ],
        }

        affirmatif_count = sum(
            1 for word in tone_words["affirmatif"] if word in content_lower
        )
        dubitatif_count = sum(
            1 for word in tone_words["dubitatif"] if word in content_lower
        )

        tone_score = 0.1 * (affirmatif_count - dubitatif_count * 0.5)
        tone_score = max(min(tone_score, 0.2), 0.0)  # Limiter entre 0 et 0.2

        # 4. Longueur et complexité
        word_count = len(content_lower.split())
        if 30 <= word_count <= 100:
            length_score = 0.1
        elif word_count > 100:
            length_score = 0.05
        else:
            length_score = 0.0

        # Combiner les scores
        persuasiveness = persuasive_score + rhetoric_score + tone_score + length_score

        return min(persuasiveness, 1.0)

    def _evaluate_originality(self, counter_argument: CounterArgument) -> float:
        """
        Évalue l'originalité du contre-argument.

        Args:
            counter_argument: Le contre-argument à évaluer

        Returns:
            Un score entre 0 et 1
        """
        content = counter_argument.counter_content

        # 1. Présence de formulations communes vs originales
        common_phrases = [
            "tout le monde sait que",
            "comme on dit souvent",
            "il est bien connu que",
            "évidemment",
            "bien entendu",
        ]

        common_phrase_count = sum(
            1 for phrase in common_phrases if phrase in content.lower()
        )
        common_phrase_penalty = min(common_phrase_count * 0.1, 0.3)

        # 2. Originalité de la stratégie pour le type d'argument
        strategy_originality = 0.2
        if (
            counter_argument.counter_type == CounterArgumentType.DIRECT_REFUTATION
            and "socratic" in counter_argument.rhetorical_strategy
        ):
            strategy_originality = 0.4  # Combinaison moins commune
        elif (
            counter_argument.counter_type == CounterArgumentType.PREMISE_CHALLENGE
            and "analogical" in counter_argument.rhetorical_strategy
        ):
            strategy_originality = 0.4  # Combinaison moins commune

        # 3. Complexité et richesse du vocabulaire
        unique_words = set(
            re.findall(r"\b\w{4,}\b", content.lower())
        )  # Mots de 4 lettres ou plus
        word_count = len(content.split())

        if word_count > 0:
            vocabulary_ratio = len(unique_words) / word_count
            vocabulary_score = min(vocabulary_ratio * 2, 0.3)
        else:
            vocabulary_score = 0.0

        # 4. Présence de perspectives inattendues
        unexpected_perspectives = [
            "contrairement à ce qu'on pourrait penser",
            "sous un angle différent",
            "perspective alternative",
            "vision moins connue",
            "approche inhabituelle",
        ]

        unexpected_score = 0.0
        for perspective in unexpected_perspectives:
            if perspective in content.lower():
                unexpected_score = 0.2
                break

        # Combiner les scores
        originality = (
            0.5
            + strategy_originality
            + vocabulary_score
            + unexpected_score
            - common_phrase_penalty
        )

        return min(max(originality, 0.1), 1.0)  # Garantir un score entre 0.1 et 1.0

    def _evaluate_clarity(self, counter_argument: CounterArgument) -> float:
        """
        Évalue la clarté du contre-argument.

        Args:
            counter_argument: Le contre-argument à évaluer

        Returns:
            Un score entre 0 et 1
        """
        content = counter_argument.counter_content

        # 1. Longueur moyenne des phrases
        avg_sentence_length = self._average_sentence_length(content)
        sentence_length_score = (
            0.3
            if avg_sentence_length < 25
            else (0.2 if avg_sentence_length < 35 else 0.1)
        )

        # 2. Structure claire (début, développement, conclusion)
        structure_score = 0.2 if self._has_clear_structure(content) else 0.0

        # 3. Utilisation de connecteurs logiques
        connectors_score = 0.2 if self._has_connectors(content) else 0.0

        # 4. Absence d'ambiguïtés
        ambiguity_markers = [
            "peut-être",
            "possiblement",
            "il se pourrait",
            "d'une certaine façon",
            "en quelque sorte",
            "plus ou moins",
            "relativement",
            "assez",
        ]

        ambiguity_count = sum(
            1 for marker in ambiguity_markers if marker in content.lower()
        )
        ambiguity_penalty = min(ambiguity_count * 0.05, 0.2)

        # 5. Vocabulaire accessible
        complexity_score = (
            0.2 if self._assess_vocabulary_complexity(content) < 0.3 else 0.1
        )

        # Combiner les scores
        clarity = (
            sentence_length_score
            + structure_score
            + connectors_score
            + complexity_score
            - ambiguity_penalty
        )

        return min(max(clarity, 0.1), 1.0)  # Garantir un score entre 0.1 et 1.0

    def _generate_recommendations(
        self,
        original_argument: Argument,
        counter_argument: CounterArgument,
        relevance: float,
        logical_strength: float,
        persuasiveness: float,
        originality: float,
        clarity: float,
    ) -> List[str]:
        """
        Génère des recommandations pour améliorer le contre-argument.

        Args:
            original_argument: L'argument original
            counter_argument: Le contre-argument évalué
            relevance: Score de pertinence
            logical_strength: Score de force logique
            persuasiveness: Score de persuasion
            originality: Score d'originalité
            clarity: Score de clarté

        Returns:
            Liste de recommandations
        """
        recommendations = []

        # Seuil pour considérer qu'un critère nécessite une amélioration
        threshold = 0.6

        if relevance < threshold:
            if counter_argument.counter_type == CounterArgumentType.PREMISE_CHALLENGE:
                recommendations.append(
                    "Cibler plus spécifiquement les prémisses de l'argument original"
                )
            elif counter_argument.counter_type == CounterArgumentType.DIRECT_REFUTATION:
                recommendations.append(
                    "Adresser plus directement la conclusion de l'argument original"
                )
            else:
                recommendations.append(
                    "Améliorer la pertinence par rapport à l'argument original"
                )

        if logical_strength < threshold:
            if not any(
                marker in counter_argument.counter_content.lower()
                for marker in self.logical_markers
            ):
                recommendations.append(
                    "Renforcer la structure logique en utilisant des connecteurs comme 'car', 'donc', 'par conséquent'"
                )
            else:
                recommendations.append(
                    "Renforcer le raisonnement logique du contre-argument"
                )

        if persuasiveness < threshold:
            if not any(
                element in counter_argument.counter_content.lower()
                for element in self.persuasive_elements
            ):
                recommendations.append(
                    "Ajouter des éléments persuasifs comme des exemples concrets ou des preuves"
                )
            else:
                recommendations.append(
                    "Renforcer le pouvoir de persuasion du contre-argument"
                )

        if originality < threshold:
            recommendations.append("Développer un angle plus original ou inattendu")

        if clarity < threshold:
            if self._average_sentence_length(counter_argument.counter_content) > 30:
                recommendations.append(
                    "Simplifier la formulation en utilisant des phrases plus courtes"
                )
            else:
                recommendations.append(
                    "Améliorer la clarté et la structure du contre-argument"
                )

        # Si tous les scores sont bons
        if all(
            score >= threshold
            for score in [
                relevance,
                logical_strength,
                persuasiveness,
                originality,
                clarity,
            ]
        ):
            recommendations.append("Le contre-argument est de bonne qualité")

        return recommendations

    def _extract_keywords(self, text: str) -> Set[str]:
        """
        Extrait les mots-clés d'un texte.

        Args:
            text: Le texte à analyser

        Returns:
            Ensemble de mots-clés
        """
        import re

        # Supprimer la ponctuation et convertir en minuscules
        text = re.sub(r"[^\w\s]", "", text.lower())

        # Liste de mots vides en français
        stop_words = [
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
            "quoi",
            "comment",
            "quand",
            "où",
            "est",
            "sont",
            "a",
            "ont",
            "être",
            "avoir",
            "pour",
            "dans",
            "par",
            "sur",
            "avec",
            "sans",
            "ce",
            "cette",
            "ces",
            "mon",
            "ma",
            "mes",
            "ton",
            "ta",
            "tes",
            "son",
            "sa",
            "ses",
            "notre",
            "nos",
            "votre",
            "vos",
            "leur",
            "leurs",
            "de",
            "du",
            "au",
            "aux",
            "en",
            "y",
        ]

        # Filtrer les mots vides et les mots courts
        return {
            word for word in text.split() if word not in stop_words and len(word) > 3
        }

    def _average_sentence_length(self, text: str) -> float:
        """
        Calcule la longueur moyenne des phrases d'un texte.

        Args:
            text: Le texte à analyser

        Returns:
            Longueur moyenne en mots
        """
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 0.0

        total_words = sum(len(s.split()) for s in sentences)
        return total_words / len(sentences)

    def _has_clear_structure(self, text: str) -> bool:
        """
        Vérifie si le texte a une structure claire.

        Args:
            text: Le texte à analyser

        Returns:
            True si le texte a une structure claire, False sinon
        """
        # Vérifier la présence d'éléments structurants
        intro_markers = ["premièrement", "tout d'abord", "en premier lieu"]
        development_markers = ["ensuite", "de plus", "par ailleurs", "en outre"]
        conclusion_markers = ["en conclusion", "pour conclure", "ainsi", "donc"]

        has_intro = any(marker in text.lower() for marker in intro_markers)
        has_development = any(marker in text.lower() for marker in development_markers)
        has_conclusion = any(marker in text.lower() for marker in conclusion_markers)

        # Structure minimale : introduction et conclusion
        return has_intro or has_conclusion

    def _has_connectors(self, text: str) -> bool:
        """
        Vérifie si le texte utilise des connecteurs logiques.

        Args:
            text: Le texte à analyser

        Returns:
            True si le texte utilise des connecteurs, False sinon
        """
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
            "malgré",
            "bien que",
            "même si",
            "en revanche",
            "par ailleurs",
            "de plus",
            "ensuite",
        ]

        return any(connector in text.lower() for connector in connectors)

    def _assess_vocabulary_complexity(self, text: str) -> float:
        """
        Évalue la complexité du vocabulaire d'un texte.

        Args:
            text: Le texte à analyser

        Returns:
            Un score entre 0 (simple) et 1 (complexe)
        """
        # Liste de mots considérés comme complexes
        complex_words = [
            "paradigme",
            "ontologie",
            "épistémologie",
            "herméneutique",
            "heuristique",
            "axiomatique",
            "syllogisme",
            "dialectique",
            "dichotomie",
            "holisme",
            "transcendantal",
            "immanent",
            "phénoménologie",
            "métaphysique",
            "tautologie",
            "fallacieux",
        ]

        words = text.lower().split()

        if not words:
            return 0.0

        # Compter les mots complexes et les mots longs
        complex_count = sum(1 for word in words if word in complex_words)
        long_words = sum(1 for word in words if len(word) > 8)

        # Calculer un score de complexité
        complexity = (complex_count + (long_words * 0.5)) / len(words)

        return min(complexity, 1.0)
