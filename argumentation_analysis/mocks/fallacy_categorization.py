# -*- coding: utf-8 -*-
"""Mock pour un catégorisateur de sophismes."""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class MockFallacyCategorizer:
    """
    Mock d'un catégorisateur de sophismes.
    Simule la classification de sophismes détectés dans des catégories prédéfinies.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config if config else {}
        # Catégories de sophismes et les types de sophismes qu'elles incluent (simplifié)
        self.fallacy_categories: Dict[str, List[str]] = self.config.get(
            "fallacy_categories",
            {
                "Sophismes de Pertinence (Mock)": [
                    "Ad Hominem (Mock)",
                    "Homme de Paille (Mock)",
                    "Appel à l'Ignorance (Mock)",
                    "Ad Populum (Mock)",
                ],
                "Sophismes d'Ambiguïté (Mock)": [
                    "Équivocation (Mock)",
                    "Amphibologie (Mock)",
                ],
                "Sophismes de Présomption (Mock)": [
                    "Pétition de Principe (Mock)",
                    "Faux Dilemme (Mock)",
                    "Généralisation Hâtive (Mock)",
                ],
                "Sophismes Formels (Mock)": [  # Bien que les mocks soient informels, pour la structure
                    "Affirmation du Conséquent (Mock)",
                    "Négation de l'Antécédent (Mock)",
                ],
            },
        )
        # Mapping inversé pour trouver rapidement la catégorie d'un type de sophisme
        self.type_to_category_map: Dict[str, str] = {}
        for category, types in self.fallacy_categories.items():
            for f_type in types:
                self.type_to_category_map[f_type.lower()] = (
                    category  # Stocker en minuscules pour la recherche insensible à la casse
                )

        logger.info(
            "MockFallacyCategorizer initialisé avec config: %s (catégories: %d)",
            self.config,
            len(self.fallacy_categories),
        )

    def categorize_fallacies(
        self, fallacies: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Simule la catégorisation d'une liste de sophismes détectés.

        Args:
            fallacies: Une liste de dictionnaires, où chaque dictionnaire représente un sophisme
                       détecté et doit contenir au moins une clé "fallacy_type".

        Returns:
            Un dictionnaire où les clés sont les noms des catégories de sophismes et
            les valeurs sont des listes des types de sophismes appartenant à cette catégorie.
        """
        if not isinstance(fallacies, list):
            logger.warning(
                "MockFallacyCategorizer.categorize_fallacies a reçu une entrée non-liste."
            )
            return {"error": "Entrée non-liste"}

        logger.info(f"MockFallacyCategorizer catégorise {len(fallacies)} sophismes...")

        categorized_results: Dict[str, List[str]] = {
            category: [] for category in self.fallacy_categories
        }
        categorized_results["Autres Sophismes (Mock)"] = []  # Pour ceux non mappés

        for fallacy in fallacies:
            if not isinstance(fallacy, dict) or "fallacy_type" not in fallacy:
                logger.warning(f"Sophisme invalide ou sans 'fallacy_type': {fallacy}")
                continue

            fallacy_type_str = str(
                fallacy["fallacy_type"]
            ).lower()  # Recherche insensible à la casse

            category = self.type_to_category_map.get(fallacy_type_str)

            if category:
                # Récupérer le type de sophisme avec la casse d'origine de la configuration
                original_case_type = fallacy["fallacy_type"]  # Valeur par défaut
                for type_in_config in self.fallacy_categories.get(category, []):
                    if type_in_config.lower() == fallacy_type_str:
                        original_case_type = type_in_config
                        break

                # Éviter les doublons de type dans une même catégorie pour ce résultat
                if original_case_type not in categorized_results[category]:
                    categorized_results[category].append(original_case_type)
            else:
                logger.debug(
                    f"Type de sophisme '{fallacy['fallacy_type']}' non trouvé dans les catégories mappées, classé comme 'Autres'."
                )
                # Pour "Autres Sophismes", on conserve la casse d'entrée car il n'y a pas de casse canonique.
                if (
                    fallacy["fallacy_type"]
                    not in categorized_results["Autres Sophismes (Mock)"]
                ):
                    categorized_results["Autres Sophismes (Mock)"].append(
                        fallacy["fallacy_type"]
                    )

        # Nettoyer les catégories vides (sauf "Autres" si elle a du contenu)
        final_categories = {
            cat: types for cat, types in categorized_results.items() if types
        }
        if (
            not final_categories
            and "Autres Sophismes (Mock)" in categorized_results
            and not categorized_results["Autres Sophismes (Mock)"]
        ):
            # Si tout est vide, on peut retourner un dict vide ou avec "Autres" vide.
            # Pour la cohérence, si "Autres" est la seule clé et est vide, on la retire.
            pass

        logger.info(f"Catégorisation terminée: {final_categories}")
        return final_categories

    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle du catégorisateur de sophismes."""
        return self.config
