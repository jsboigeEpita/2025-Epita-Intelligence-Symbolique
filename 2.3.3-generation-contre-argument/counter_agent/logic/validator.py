"""
Validation logique des arguments et contre-arguments.

Ce module fournit des fonctionnalités pour valider la cohérence
logique des arguments et des contre-arguments.
"""

import logging
from typing import Dict, List, Any, Optional

from ..agent.definitions import (
    Argument,
    CounterArgument,
    CounterArgumentType,
    ArgumentStrength,
    ValidationResult,
)
from .tweety_bridge import TweetyBridge

logger = logging.getLogger(__name__)


class CounterArgumentValidator:
    """
    Classe pour valider la cohérence logique des contre-arguments.
    """

    def __init__(self, tweety_jar_path: Optional[str] = None):
        """
        Initialise le validateur de contre-arguments.

        Args:
            tweety_jar_path: Chemin vers le fichier JAR de TweetyProject
        """
        self.tweety_bridge = TweetyBridge(tweety_jar_path)
        logger.info("CounterArgumentValidator initialisé")

    def validate(
        self, original_argument: Argument, counter_argument: CounterArgument
    ) -> ValidationResult:
        """
        Valide la cohérence logique d'un contre-argument.

        Args:
            original_argument: L'argument original
            counter_argument: Le contre-argument à valider

        Returns:
            Un objet ValidationResult contenant les résultats de la validation
        """
        logger.info(
            f"Validation du contre-argument de type {counter_argument.counter_type.value}"
        )

        # Utiliser TweetyProject pour la validation formelle
        validation_result = self.tweety_bridge.validate_counter_argument(
            original_argument, counter_argument
        )

        return ValidationResult(
            is_valid_attack=validation_result["is_valid_attack"],
            original_survives=validation_result["original_survives"],
            counter_succeeds=validation_result["counter_succeeds"],
            logical_consistency=validation_result["logical_consistency"],
            formal_representation=validation_result.get("formal_representation"),
        )

    def assess_strength(
        self, original_argument: Argument, counter_arguments: List[CounterArgument]
    ) -> float:
        """
        Évalue la force d'un argument après application de contre-arguments.

        Args:
            original_argument: L'argument original
            counter_arguments: Liste des contre-arguments

        Returns:
            Un score entre 0 et 1 représentant la force de l'argument
        """
        logger.info(
            f"Évaluation de la force de l'argument face à {len(counter_arguments)} contre-arguments"
        )

        return self.tweety_bridge.assess_argument_strength(
            original_argument, counter_arguments
        )

    def generate_attack_graph(
        self, original_argument: Argument, counter_arguments: List[CounterArgument]
    ) -> str:
        """
        Génère une représentation textuelle du graphe d'attaque.

        Args:
            original_argument: L'argument original
            counter_arguments: Liste des contre-arguments

        Returns:
            Une représentation textuelle du graphe d'attaque
        """
        logger.info(
            f"Génération du graphe d'attaque pour {len(counter_arguments)} contre-arguments"
        )

        return self.tweety_bridge.generate_attack_graph(
            original_argument, counter_arguments
        )

    def check_logical_coherence(self, premise_set: List[str], conclusion: str) -> bool:
        """
        Vérifie la cohérence logique entre un ensemble de prémisses et une conclusion.

        Args:
            premise_set: Liste des prémisses
            conclusion: La conclusion à vérifier

        Returns:
            True si l'argument est logiquement cohérent, False sinon
        """
        logger.info(
            f"Vérification de la cohérence logique entre {len(premise_set)} prémisses et une conclusion"
        )

        # Cette méthode pourrait être développée pour utiliser des
        # outils de vérification logique plus avancés

        # Pour l'instant, implémentation simplifiée
        if not premise_set or not conclusion:
            return False

        # Vérifier si des mots clés des prémisses apparaissent dans la conclusion
        premise_words = set()
        for premise in premise_set:
            premise_words.update(self._extract_key_words(premise))

        conclusion_words = set(self._extract_key_words(conclusion))

        # S'il y a au moins quelques mots en commun, considérer comme cohérent
        common_words = premise_words.intersection(conclusion_words)
        return len(common_words) > 0

    def _extract_key_words(self, text: str) -> List[str]:
        """
        Extrait les mots clés d'un texte.

        Args:
            text: Le texte à analyser

        Returns:
            Liste des mots clés
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

        # Filtrer les mots vides
        return [
            word for word in text.split() if word not in stop_words and len(word) > 2
        ]
