# -*- coding: utf-8 -*-
"""Mock pour une analyse d'engagement."""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class MockEngagementAnalyzer:
    """
    Mock d'un analyseur d'engagement.
    Simule l'évaluation du niveau d'engagement d'un texte basé sur certains indicateurs.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config if config else {}
        self.engagement_signals: Dict[str, float] = self.config.get(
            "engagement_signals",
            {
                "questions_directes": 0.2,  # ex: "Qu'en pensez-vous ?"
                "appels_action": 0.3,  # ex: "Cliquez ici", "Rejoignez-nous"
                "pronoms_inclusifs": 0.1,  # ex: "nous", "notre", "ensemble"
                "vocabulaire_positif_fort": 0.15,  # ex: "incroyable", "fantastique", "révolutionnaire"
                "vocabulaire_negatif_fort": -0.1,  # ex: "terrible", "désastreux" (peut désengager)
                "longueur_texte_bonus": 0.05,  # Petit bonus pour les textes plus longs (plus d'opportunités)
            },
        )
        self.positive_keywords = [
            "incroyable",
            "fantastique",
            "révolutionnaire",
            "excellent",
            "merveilleux",
        ]
        self.negative_keywords = ["terrible", "désastreux", "horrible", "décevant"]
        self.action_keywords = [
            "cliquez",
            "rejoignez",
            "participez",
            "inscrivez-vous",
            "achetez",
        ]
        self.question_patterns = [r"\?", r"qu'en pensez-vous", r"n'est-ce pas"]
        self.inclusive_pronouns = [
            "nous",
            "notre",
            "nos",
            "ensemble",
            "votre",
            "vos",
        ]  # "vous" peut être engageant

        logger.info(
            "MockEngagementAnalyzer initialisé avec config: %s (signals: %d)",
            self.config,
            len(self.engagement_signals),
        )

    def analyze_engagement(self, text: str) -> Dict[str, Any]:
        """
        Simule l'analyse de l'engagement du texte.

        Args:
            text: Le texte à analyser.

        Returns:
            Un dictionnaire contenant le score d'engagement simulé et les signaux détectés.
        """
        if not isinstance(text, str):
            logger.warning(
                "MockEngagementAnalyzer.analyze_engagement a reçu une entrée non textuelle."
            )
            return {
                "error": "Entrée non textuelle",
                "engagement_score": 0.0,
                "signals_detected": {},
            }

        logger.info("MockEngagementAnalyzer analyse le texte : %s...", text[:100])

        engagement_score: float = 0.0
        signals_detected: Dict[str, int] = {
            signal: 0 for signal in self.engagement_signals
        }
        text_lower = text.lower()

        # Questions directes
        for pattern in self.question_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                signals_detected["questions_directes"] += len(
                    re.findall(pattern, text_lower, re.IGNORECASE)
                )
        if signals_detected["questions_directes"] > 0:
            engagement_score += self.engagement_signals["questions_directes"] * min(
                signals_detected["questions_directes"], 3
            )  # Plafonner l'effet

        # Appels à l'action
        for keyword in self.action_keywords:
            if keyword in text_lower:
                signals_detected["appels_action"] += text_lower.count(keyword)
        if signals_detected["appels_action"] > 0:
            engagement_score += (
                self.engagement_signals["appels_action"]
                * signals_detected["appels_action"]
            )

        # Pronoms inclusifs
        for pronoun in self.inclusive_pronouns:
            matches = re.findall(rf"\b{pronoun}\b", text_lower, re.IGNORECASE)
            if matches:
                signals_detected["pronoms_inclusifs"] += len(matches)
        if signals_detected["pronoms_inclusifs"] > 0:
            engagement_score += self.engagement_signals["pronoms_inclusifs"] * min(
                signals_detected["pronoms_inclusifs"], 5
            )

        # Vocabulaire positif fort
        for keyword in self.positive_keywords:
            if keyword in text_lower:
                signals_detected["vocabulaire_positif_fort"] += text_lower.count(
                    keyword
                )
        if signals_detected["vocabulaire_positif_fort"] > 0:
            engagement_score += (
                self.engagement_signals["vocabulaire_positif_fort"]
                * signals_detected["vocabulaire_positif_fort"]
            )

        # Vocabulaire négatif fort
        for keyword in self.negative_keywords:
            if keyword in text_lower:
                signals_detected["vocabulaire_negatif_fort"] += text_lower.count(
                    keyword
                )
        if signals_detected["vocabulaire_negatif_fort"] > 0:
            engagement_score += (
                self.engagement_signals["vocabulaire_negatif_fort"]
                * signals_detected["vocabulaire_negatif_fort"]
            )

        # Bonus longueur texte
        if len(text) > 200:  # Arbitraire
            engagement_score += self.engagement_signals["longueur_texte_bonus"]
            signals_detected["longueur_texte_bonus"] = 1

        # Normaliser le score entre 0 et 1
        final_score = min(max(engagement_score, 0.0), 1.0)

        logger.info(
            f"MockEngagementAnalyzer score calculé: {final_score:.2f}, signaux: {signals_detected}"
        )
        return {
            "engagement_score": final_score,
            "signals_detected": signals_detected,
            "interpretation": self._interpret_score(final_score),
        }

    def _interpret_score(self, score: float) -> str:
        if score >= 0.75:
            return "Très engageant (Mock)"
        elif score >= 0.5:
            return "Engageant (Mock)"
        elif score >= 0.25:
            return "Peu engageant (Mock)"
        else:
            return "Pas du tout engageant (Mock)"

    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle de l'analyseur d'engagement."""
        return self.config
