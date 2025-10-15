# -*- coding: utf-8 -*-
"""Mock pour un analyseur rhétorique de base."""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class MockRhetoricalAnalyzer:
    """
    Mock d'un analyseur rhétorique de base.
    Simule l'identification de figures de style et de tonalités.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config if config else {}
        logger.info(
            "MockRhetoricalAnalyzer initialisé avec la config : %s", self.config
        )

    def analyze(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Simule une analyse rhétorique sur le texte donné.

        Args:
            text: Le texte à analyser.
            context: Contexte supplémentaire pour l'analyse (non utilisé dans ce mock).

        Returns:
            Un dictionnaire contenant les résultats simulés de l'analyse.
        """
        if not isinstance(text, str):
            logger.warning(
                "MockRhetoricalAnalyzer.analyze a reçu une entrée non textuelle."
            )
            return {
                "error": "Entrée non textuelle",
                "figures_de_style": [],
                "tonalite": "Neutre (Erreur)",
            }

        logger.info("MockRhetoricalAnalyzer analyse le texte : %s...", text[:100])

        figures_de_style: List[Dict[str, Any]] = []
        tonalite_globale = "Neutre"
        score_engagement = 0.0

        if "exemple de métaphore" in text.lower():
            figures_de_style.append(
                {
                    "type": "Métaphore (Mock)",
                    "description": "Comparaison implicite simulée.",
                    "extrait": text[
                        text.lower()
                        .find("exemple de métaphore") : text.lower()
                        .find("exemple de métaphore")
                        + 30
                    ],
                    "impact_persuasif": 0.6,
                }
            )
            tonalite_globale = "Imagée"
            score_engagement += 0.3

        if "question rhétorique" in text.lower():
            figures_de_style.append(
                {
                    "type": "Question Rhétorique (Mock)",
                    "description": "Question n'attendant pas de réponse, simulée.",
                    "extrait": text[
                        text.lower()
                        .find("question rhétorique") : text.lower()
                        .find("question rhétorique")
                        + 30
                    ],
                    "impact_persuasif": 0.7,
                }
            )
            tonalite_globale = "Interrogative / Persuasive"
            score_engagement += 0.4

        if "tonalité ironique" in text.lower():
            tonalite_globale = "Ironique (Mock)"
            score_engagement -= 0.2  # L'ironie peut parfois désengager si mal comprise

        if not figures_de_style and tonalite_globale == "Neutre":
            # Cas par défaut si rien de spécifique n'est trouvé
            figures_de_style.append(
                {
                    "type": "Style Direct (Mock)",
                    "description": "Discours simple et direct simulé.",
                    "extrait": text[:50],
                    "impact_persuasif": 0.3,
                }
            )
            score_engagement += 0.1

        return {
            "figures_de_style": figures_de_style,
            "tonalite_globale": tonalite_globale,
            "score_engagement_simule": min(
                max(score_engagement, 0), 1
            ),  # clamp entre 0 et 1
            "longueur_texte": len(text),
        }

    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle de l'analyseur."""
        return self.config
