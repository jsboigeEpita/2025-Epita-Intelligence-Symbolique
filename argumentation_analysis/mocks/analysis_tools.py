#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes Mock pour les outils d'analyse rhétorique.
Utilisées pour les tests et les exécutions en mode simulé.
"""

import random
import logging
from datetime import datetime
from typing import Dict, List, Any

# Configuration d'un logger pour ce module.
# Les applications utilisant ces mocks peuvent le reconfigurer.
logger = logging.getLogger(__name__)
if not logger.handlers:  # Évite d'ajouter plusieurs handlers si le module est rechargé
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class MockContextualFallacyDetector:
    """Simulation du détecteur de sophismes contextuels."""

    def __init__(self):
        self.fallacy_types = [
            "appel_inapproprié_autorité",
            "appel_inapproprié_émotion",
            "appel_inapproprié_tradition",
            "appel_inapproprié_nouveauté",
            "appel_inapproprié_popularité",
        ]
        logger.info("MockContextualFallacyDetector initialisé.")

    def detect_multiple_contextual_fallacies(
        self, arguments: List[str], context_description: str
    ) -> Dict[str, Any]:
        """Simule la détection de sophismes contextuels dans plusieurs arguments."""
        argument_results = []

        for i, argument in enumerate(arguments):
            detected_fallacies = []
            if random.random() < 0.3:  # 30% de chance de détecter un sophisme
                fallacy_type = random.choice(self.fallacy_types)
                detected_fallacies.append(
                    {
                        "fallacy_type": fallacy_type,
                        "description": f"Simulation de sophisme: {fallacy_type}",
                        "context_text": argument[:50] + "..."
                        if len(argument) > 50
                        else argument,
                        "severity": round(random.uniform(0.5, 0.9), 2),
                        "contextual_factors": {
                            "domain": random.choice(
                                ["scientifique", "politique", "juridique", "général"]
                            ),
                            "audience": random.choice(
                                ["expert", "généraliste", "académique"]
                            ),
                        },
                    }
                )

            argument_results.append(
                {
                    "argument_index": i,
                    "argument": argument,
                    "detected_fallacies": detected_fallacies,
                }
            )

        return {
            "argument_count": len(arguments),
            "context_description": context_description,
            "contextual_factors": {
                "domain": "général",
                "audience": "généraliste",
                "medium": "écrit",
                "purpose": "informer",
            },
            "argument_results": argument_results,
            "analysis_timestamp": datetime.now().isoformat(),
            "note": "Analyse simulée - résultats générés aléatoirement par MockContextualFallacyDetector",
        }


class MockArgumentCoherenceEvaluator:
    """Simulation de l'évaluateur de cohérence argumentative."""

    def __init__(self):
        self.coherence_types = [
            "logique",
            "thématique",
            "structurelle",
            "rhétorique",
            "épistémique",
        ]
        logger.info("MockArgumentCoherenceEvaluator initialisé.")

    def evaluate_coherence(
        self, arguments: List[str], context: str = None
    ) -> Dict[str, Any]:
        """Simule l'évaluation de la cohérence entre les arguments."""
        coherence_evaluations = {}

        for coherence_type in self.coherence_types:
            score = round(random.uniform(0.5, 0.9), 2)
            level = "Excellent" if score > 0.8 else "Bon" if score > 0.6 else "Moyen"

            coherence_evaluations[coherence_type] = {
                "score": score,
                "level": level,
                "criteria_scores": {
                    f"critère_{i+1}": round(random.uniform(0.4, 0.9), 2)
                    for i in range(4)
                },
                "specific_issues": [],
                "importance": round(random.uniform(0.1, 0.3), 2),
            }

        overall_score_numerator = sum(
            eval_data["score"] * eval_data["importance"]
            for eval_data in coherence_evaluations.values()
        )
        overall_score_denominator = sum(
            eval_data["importance"] for eval_data in coherence_evaluations.values()
        )
        overall_score = (
            round(overall_score_numerator / overall_score_denominator, 2)
            if overall_score_denominator
            else 0.0
        )

        if overall_score > 0.8:
            coherence_level = "Excellent"
        elif overall_score > 0.6:
            coherence_level = "Bon"
        elif overall_score > 0.4:
            coherence_level = "Moyen"
        else:
            coherence_level = "Faible"

        strengths = [
            f"Bonne cohérence {ct} ({ev['score']:.2f})"
            for ct, ev in coherence_evaluations.items()
            if ev["score"] > 0.7
        ]
        weaknesses = [
            f"Faible cohérence {ct} ({ev['score']:.2f})"
            for ct, ev in coherence_evaluations.items()
            if ev["score"] < 0.5
        ]

        recommendations = [
            f"La cohérence globale des arguments est {coherence_level.lower()}.",
            "Maintenir une structure logique claire entre les arguments.",
            "Assurer une progression thématique cohérente.",
        ]

        return {
            "overall_coherence": {
                "score": overall_score,
                "level": coherence_level,
                "strengths": strengths,
                "weaknesses": weaknesses,
            },
            "coherence_evaluations": coherence_evaluations,
            "recommendations": recommendations,
            "context": context or "Analyse d'arguments",
            "timestamp": datetime.now().isoformat(),
            "note": "Analyse simulée - résultats générés aléatoirement par MockArgumentCoherenceEvaluator",
        }


class MockSemanticArgumentAnalyzer:
    """Simulation de l'analyseur sémantique d'arguments."""

    def __init__(self):
        self.relation_types = [
            "support",
            "opposition",
            "elaboration",
            "condition",
            "causality",
        ]
        logger.info("MockSemanticArgumentAnalyzer initialisé.")

    def analyze_multiple_arguments(self, arguments: List[str]) -> Dict[str, Any]:
        """Simule l'analyse sémantique de plusieurs arguments."""
        argument_analyses = []

        for i, argument in enumerate(arguments):
            components = []
            if random.random() < 0.5:  # 50% de chance d'avoir une affirmation
                components.append(
                    {
                        "component_type": "claim",
                        "text": argument[:50] + "..."
                        if len(argument) > 50
                        else argument,
                        "confidence": round(random.uniform(0.6, 0.9), 2),
                    }
                )
            if random.random() < 0.3:  # 30% de chance d'avoir des données
                components.append(
                    {
                        "component_type": "data",
                        "text": argument[:30] + "..."
                        if len(argument) > 30
                        else argument,
                        "confidence": round(random.uniform(0.5, 0.8), 2),
                    }
                )
            if not components:
                components.append(
                    {"component_type": "claim", "text": argument, "confidence": 0.5}
                )

            argument_analyses.append(
                {
                    "argument_index": i,
                    "argument": argument,
                    "semantic_components": components,
                    "analysis_timestamp": datetime.now().isoformat(),
                }
            )

        semantic_relations = []
        if len(arguments) > 1:
            for i in range(len(arguments) - 1):
                if random.random() < 0.7:  # 70% de chance d'avoir une relation
                    relation_type = random.choice(self.relation_types)
                    semantic_relations.append(
                        {
                            "relation_type": relation_type,
                            "source_index": i,
                            "target_index": i + 1,
                            "confidence": round(random.uniform(0.5, 0.9), 2),
                        }
                    )

        return {
            "argument_count": len(arguments),
            "argument_analyses": argument_analyses,
            "semantic_relations": semantic_relations,
            "analysis_timestamp": datetime.now().isoformat(),
            "note": "Analyse simulée - résultats générés aléatoirement par MockSemanticArgumentAnalyzer",
        }
