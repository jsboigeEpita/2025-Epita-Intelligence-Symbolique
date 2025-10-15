#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Détecteur de sophismes contextuels basé sur un système de règles.

Ce module fournit `ContextualFallacyDetector`, une classe qui identifie les
sophismes dont la nature fallacieuse dépend fortement du contexte. Contrairement
aux approches basées sur des modèles NLP lourds, ce détecteur utilise un système
expert léger et explicite fondé sur des règles prédéfinies.

La détection repose sur :
- L'inférence de facteurs contextuels (domaine, audience, etc.) par mots-clés.
- La recherche de marqueurs textuels spécifiques à chaque type de sophisme.
- L'application de règles contextuelles pour déterminer si le sophisme est
  suffisamment "grave" pour être signalé dans le contexte donné.
"""

import os
import sys
import json
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ContextualFallacyDetector")


class ContextualFallacyDetector:
    """
    Détecte les sophismes en appliquant des règles basées sur le contexte.

    Cette classe utilise une approche "top-down" : elle analyse d'abord le
    contexte de l'argumentation, puis recherche des marqueurs de sophismes.
    Un sophisme n'est signalé que si sa gravité, telle que définie dans les
    règles pour le contexte identifié, dépasse un certain seuil.
    """

    def __init__(self):
        """
        Initialise le détecteur de sophismes contextuels.
        """
        self.logger = logger

        # Définir les facteurs contextuels
        self.contextual_factors = self._define_contextual_factors()

        # Définir les sophismes contextuels
        self.contextual_fallacies = self._define_contextual_fallacies()
        self.detection_history = []

        self.logger.info("Détecteur de sophismes contextuels initialisé.")

    def _define_contextual_factors(self) -> Dict[str, Dict[str, Any]]:
        """
        Définit les axes et les valeurs possibles pour l'analyse contextuelle.

        Cette méthode agit comme une base de connaissances des dimensions
        contextuelles pertinentes pour l'analyse des sophismes (domaine,
        audience, support, objectif).

        Returns:
            Dict[str, Dict[str, Any]]: Un dictionnaire des facteurs contextuels.
        """
        factors = {
            "domain": {
                "description": "Domaine de l'argument",
                "values": [
                    "scientifique",
                    "politique",
                    "juridique",
                    "médical",
                    "commercial",
                    "éducatif",
                    "religieux",
                    "philosophique",
                    "éthique",
                    "technique",
                ],
            },
            "audience": {
                "description": "Public cible de l'argument",
                "values": [
                    "expert",
                    "généraliste",
                    "académique",
                    "professionnel",
                    "jeune",
                    "âgé",
                    "conservateur",
                    "progressiste",
                    "traditionaliste",
                    "moderniste",
                ],
            },
            "medium": {
                "description": "Support de l'argument",
                "values": [
                    "écrit",
                    "oral",
                    "visuel",
                    "académique",
                    "journalistique",
                    "réseaux sociaux",
                    "publicité",
                    "débat",
                    "conversation",
                    "discours",
                ],
            },
            "purpose": {
                "description": "Objectif de l'argument",
                "values": [
                    "informer",
                    "persuader",
                    "divertir",
                    "éduquer",
                    "critiquer",
                    "défendre",
                    "attaquer",
                    "clarifier",
                    "questionner",
                    "réfuter",
                ],
            },
        }

        return factors

    def _define_contextual_fallacies(self) -> Dict[str, Dict[str, Any]]:
        """
        Définit la base de règles pour la détection de sophismes contextuels.

        Cette méthode retourne un dictionnaire qui est la principale base de
        connaissances du détecteur. Pour chaque sophisme, elle définit :
        - `markers` : Les mots-clés qui peuvent indiquer sa présence.
        - `contextual_rules`: Des règles qui spécifient la gravité du sophisme
          dans un domaine particulier.

        Returns:
            Dict[str, Dict[str, Any]]: Un dictionnaire des règles de sophismes.
        """
        fallacies = {
            "appel_inapproprié_autorité": {
                "description": "Appel à une autorité qui n'est pas pertinente dans le contexte",
                "markers": ["expert", "autorité", "spécialiste", "selon", "d'après"],
                "contextual_rules": {
                    "domain": {
                        "scientifique": {"severity": 0.9},
                        "médical": {"severity": 0.9},
                        "juridique": {"severity": 0.8},
                        "commercial": {"severity": 0.6},
                    }
                },
            },
            "appel_inapproprié_émotion": {
                "description": "Appel aux émotions inapproprié dans le contexte",
                "markers": [
                    "peur",
                    "crainte",
                    "inquiétude",
                    "terreur",
                    "anxiété",
                    "horreur",
                ],
                "contextual_rules": {
                    "domain": {
                        "scientifique": {"severity": 0.9},
                        "juridique": {"severity": 0.8},
                        "commercial": {"severity": 0.5},
                        "politique": {"severity": 0.6},
                    }
                },
            },
            "appel_inapproprié_tradition": {
                "description": "Appel à la tradition inapproprié dans le contexte",
                "markers": [
                    "tradition",
                    "toujours",
                    "depuis longtemps",
                    "historiquement",
                    "de tout temps",
                ],
                "contextual_rules": {
                    "domain": {
                        "scientifique": {"severity": 0.8},
                        "technique": {"severity": 0.8},
                        "médical": {"severity": 0.7},
                        "religieux": {"severity": 0.3},
                    }
                },
            },
            "appel_inapproprié_nouveauté": {
                "description": "Appel à la nouveauté inapproprié dans le contexte",
                "markers": [
                    "nouveau",
                    "récent",
                    "moderne",
                    "innovant",
                    "dernier",
                    "tendance",
                ],
                "contextual_rules": {
                    "domain": {
                        "juridique": {"severity": 0.7},
                        "éthique": {"severity": 0.7},
                        "religieux": {"severity": 0.6},
                        "technique": {"severity": 0.3},
                    }
                },
            },
            "appel_inapproprié_popularité": {
                "description": "Appel à la popularité inapproprié dans le contexte",
                "markers": [
                    "populaire",
                    "tout le monde",
                    "majorité",
                    "beaucoup",
                    "nombreux",
                    "la plupart",
                ],
                "contextual_rules": {
                    "domain": {
                        "scientifique": {"severity": 0.9},
                        "médical": {"severity": 0.8},
                        "juridique": {"severity": 0.7},
                        "commercial": {"severity": 0.4},
                    }
                },
            },
        }

        return fallacies

    def detect_contextual_fallacies(
        self,
        argument: str,
        context_description: str,
        contextual_factors: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Détecte les sophismes contextuels pour un seul argument.

        L'algorithme de détection est le suivant :
        1. Inférer les facteurs contextuels à partir de la `context_description` si
           ils ne sont pas fournis.
        2. Pour chaque sophisme dans la base de règles, rechercher ses marqueurs
           dans le texte de l'argument.
        3. Si un marqueur est trouvé, calculer la gravité du sophisme en utilisant
           les règles contextuelles.
        4. Si la gravité calculée est supérieure à 0.5, signaler le sophisme.

        Args:
            argument (str): L'argument à analyser.
            context_description (str): Une description textuelle du contexte.
            contextual_factors (Optional[Dict[str, str]], optional): Facteurs
                contextuels pré-analysés. Si None, ils sont inférés.

        Returns:
            Dict[str, Any]: Un dictionnaire de résultats contenant la liste des
            sophismes détectés pour cet argument.
        """
        self.logger.info(f"Détection de sophismes contextuels dans: {argument[:50]}...")

        # Si les facteurs contextuels ne sont pas spécifiés, les inférer à partir de la description
        if not contextual_factors:
            contextual_factors = self._infer_contextual_factors(context_description)

        # Détecter les sophismes contextuels (simulation)
        detected_fallacies = []

        # Vérifier chaque type de sophisme contextuel
        for fallacy_type, fallacy_info in self.contextual_fallacies.items():
            # Vérifier si les marqueurs du sophisme sont présents dans l'argument
            markers = fallacy_info.get("markers", [])
            for marker in markers:
                if marker.lower() in argument.lower():
                    # Calculer la gravité du sophisme en fonction du contexte
                    severity = self._calculate_contextual_severity(
                        fallacy_type, contextual_factors
                    )

                    # Si la gravité est suffisamment élevée, ajouter le sophisme à la liste
                    if severity > 0.5:
                        detected_fallacies.append(
                            {
                                "fallacy_type": fallacy_type,
                                "description": fallacy_info.get("description", ""),
                                "context_text": argument,
                                "marker": marker,
                                "severity": severity,
                                "contextual_factors": contextual_factors,
                            }
                        )

                    # Ne détecter qu'une seule instance de chaque type de sophisme
                    break

        # Préparer les résultats
        results = {
            "argument": argument,
            "context_description": context_description,
            "contextual_factors": contextual_factors,
            "detected_fallacies": detected_fallacies,
            "analysis_timestamp": datetime.now().isoformat(),
        }

        return results

    def detect_multiple_contextual_fallacies(
        self,
        arguments: List[str],
        context_description: str,
        contextual_factors: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Détecte les sophismes contextuels dans plusieurs arguments.

        Args:
            arguments (List[str]): Liste d'arguments à analyser
            context_description (str): Description du contexte
            contextual_factors (Optional[Dict[str, str]]): Facteurs contextuels spécifiques

        Returns:
            Dict[str, Any]: Résultats de la détection
        """
        self.logger.info(
            f"Détection de sophismes contextuels dans {len(arguments)} arguments"
        )

        # Détecter les sophismes dans chaque argument
        argument_results = []
        for i, argument in enumerate(arguments):
            result = self.detect_contextual_fallacies(
                argument, context_description, contextual_factors
            )
            result["argument_index"] = i
            argument_results.append(result)

        # Préparer les résultats
        results = {
            "argument_count": len(arguments),
            "context_description": context_description,
            "contextual_factors": contextual_factors,
            "argument_results": argument_results,
            "analysis_timestamp": datetime.now().isoformat(),
        }

        self.detection_history.append(
            {
                "type": "multiple_contextual_fallacy_detection",
                "timestamp": results["analysis_timestamp"],
                "input_arguments_count": len(arguments),
                "input_context": context_description,
                "detected_fallacies_count": sum(
                    len(arg_res.get("detected_fallacies", []))
                    for arg_res in argument_results
                ),
            }
        )

        return results

    def _infer_contextual_factors(self, context_description: str) -> Dict[str, str]:
        """
        Infère les facteurs contextuels à partir d'une description.

        Args:
            context_description (str): Description du contexte

        Returns:
            Dict[str, str]: Facteurs contextuels inférés
        """
        # Simuler l'inférence des facteurs contextuels
        contextual_factors = {}

        # Inférer le domaine
        if (
            "science" in context_description.lower()
            or "recherche" in context_description.lower()
        ):
            contextual_factors["domain"] = "scientifique"
        elif (
            "politique" in context_description.lower()
            or "gouvernement" in context_description.lower()
        ):
            contextual_factors["domain"] = "politique"
        elif (
            "juridique" in context_description.lower()
            or "légal" in context_description.lower()
        ):
            contextual_factors["domain"] = "juridique"
        elif (
            "médical" in context_description.lower()
            or "santé" in context_description.lower()
        ):
            contextual_factors["domain"] = "médical"
        elif (
            "commercial" in context_description.lower()
            or "marketing" in context_description.lower()
        ):
            contextual_factors["domain"] = "commercial"
        else:
            contextual_factors["domain"] = "général"

        # Inférer le public cible
        if (
            "expert" in context_description.lower()
            or "spécialiste" in context_description.lower()
        ):
            contextual_factors["audience"] = "expert"
        elif (
            "académique" in context_description.lower()
            or "universitaire" in context_description.lower()
        ):
            contextual_factors["audience"] = "académique"
        elif "professionnel" in context_description.lower():
            contextual_factors["audience"] = "professionnel"
        elif (
            "jeune" in context_description.lower()
            or "enfant" in context_description.lower()
        ):
            contextual_factors["audience"] = "jeune"
        else:
            contextual_factors["audience"] = "généraliste"

        # Inférer le support
        if (
            "écrit" in context_description.lower()
            or "article" in context_description.lower()
        ):
            contextual_factors["medium"] = "écrit"
        elif (
            "oral" in context_description.lower()
            or "discours" in context_description.lower()
        ):
            contextual_factors["medium"] = "oral"
        elif (
            "visuel" in context_description.lower()
            or "image" in context_description.lower()
        ):
            contextual_factors["medium"] = "visuel"
        elif "réseaux sociaux" in context_description.lower():
            contextual_factors["medium"] = "réseaux sociaux"
        else:
            contextual_factors["medium"] = "général"

        # Inférer l'objectif
        if (
            "informer" in context_description.lower()
            or "expliquer" in context_description.lower()
        ):
            contextual_factors["purpose"] = "informer"
        elif (
            "persuader" in context_description.lower()
            or "convaincre" in context_description.lower()
        ):
            contextual_factors["purpose"] = "persuader"
        elif (
            "divertir" in context_description.lower()
            or "amuser" in context_description.lower()
        ):
            contextual_factors["purpose"] = "divertir"
        elif (
            "éduquer" in context_description.lower()
            or "enseigner" in context_description.lower()
        ):
            contextual_factors["purpose"] = "éduquer"
        else:
            contextual_factors["purpose"] = "général"

        return contextual_factors

    def _calculate_contextual_severity(
        self, fallacy_type: str, contextual_factors: Dict[str, str]
    ) -> float:
        """
        Calcule la gravité d'un sophisme en fonction du contexte.

        Args:
            fallacy_type (str): Type de sophisme
            contextual_factors (Dict[str, str]): Facteurs contextuels

        Returns:
            float: Gravité du sophisme (entre 0.0 et 1.0)
        """
        # Obtenir les règles contextuelles pour ce type de sophisme
        fallacy_info = self.contextual_fallacies.get(fallacy_type, {})
        contextual_rules = fallacy_info.get("contextual_rules", {})

        # Calculer la gravité de base
        base_severity = 0.5

        # Ajuster la gravité en fonction des facteurs contextuels
        for factor_name, factor_value in contextual_factors.items():
            if factor_name in contextual_rules:
                factor_rules = contextual_rules[factor_name]
                if factor_value in factor_rules:
                    rule = factor_rules[factor_value]
                    base_severity = rule.get("severity", base_severity)

        return base_severity


# Test de la classe si exécutée directement
if __name__ == "__main__":
    # Exemple d'arguments
    arguments = [
        "Les experts affirment que ce produit est sûr.",
        "Tout le monde utilise ce produit, donc il doit être bon.",
        "Ce produit est utilisé depuis des décennies, donc il est fiable.",
        "Ce produit est le plus récent sur le marché, donc il est meilleur.",
    ]

    # Créer le détecteur
    detector = ContextualFallacyDetector()

    # Détecter les sophismes contextuels
    results = detector.detect_multiple_contextual_fallacies(arguments, "commercial")

    # Afficher les résultats
    print(json.dumps(results, indent=2, ensure_ascii=False))
