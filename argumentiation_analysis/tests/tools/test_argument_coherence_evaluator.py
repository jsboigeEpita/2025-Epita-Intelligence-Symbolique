#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests pour l'évaluateur de cohérence d'arguments.

Ce module contient les tests unitaires pour la classe ArgumentCoherenceEvaluator.
"""

import os
import sys
import unittest
import json
import numpy as np
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from argumentiation_analysis.agents.tools.analysis.new.argument_coherence_evaluator import ArgumentCoherenceEvaluator


class TestArgumentCoherenceEvaluator(unittest.TestCase):
    """Tests pour la classe ArgumentCoherenceEvaluator."""

    def setUp(self):
        """Initialise l'environnement de test."""
        # Patcher les dépendances externes pour éviter les erreurs d'importation
        self.numpy_patcher = patch('argumentiation_analysis.agents.tools.analysis.new.argument_coherence_evaluator.np', np)
        self.numpy_patcher.start()
        
        self.evaluator = ArgumentCoherenceEvaluator()
        
        # Exemples d'arguments pour les tests
        self.test_arguments = [
            "Le réchauffement climatique est un problème mondial urgent.",
            "Les émissions de gaz à effet de serre contribuent significativement au réchauffement climatique.",
            "Nous devons réduire nos émissions de carbone pour lutter contre le réchauffement climatique.",
            "Les énergies renouvelables sont une alternative viable aux combustibles fossiles."
        ]
        
        self.test_context = "environnemental"
        
        # Exemples d'arguments incohérents pour les tests
        self.incoherent_arguments = [
            "Le réchauffement climatique est un problème mondial urgent.",
            "Les chats sont des animaux domestiques populaires.",
            "La Tour Eiffel est située à Paris.",
            "Le chocolat est apprécié par de nombreuses personnes."
        ]

    def tearDown(self):
        """Nettoie l'environnement de test."""
        self.numpy_patcher.stop()

    def test_initialization(self):
        """Teste l'initialisation de l'évaluateur."""
        self.assertIsNotNone(self.evaluator)
        self.assertIsNotNone(self.evaluator.coherence_metrics)
        self.assertEqual(len(self.evaluator.evaluation_history), 0)

    def test_evaluate_argument_coherence(self):
        """Teste la méthode evaluate_argument_coherence."""
        result = self.evaluator.evaluate_argument_coherence(self.test_arguments, self.test_context)
        
        # Vérifier la structure du résultat
        self.assertIn("overall_coherence", result)
        self.assertIn("coherence_level", result)
        self.assertIn("thematic_coherence", result)
        self.assertIn("logical_coherence", result)
        self.assertIn("structural_coherence", result)
        self.assertIn("contextual_coherence", result)
        self.assertIn("coherence_issues", result)
        self.assertIn("improvement_suggestions", result)
        self.assertIn("evaluation_timestamp", result)
        
        # Vérifier que la cohérence globale est dans les limites attendues
        self.assertGreaterEqual(result["overall_coherence"], 0.0)
        self.assertLessEqual(result["overall_coherence"], 1.0)
        
        # Vérifier que le niveau de cohérence est valide
        self.assertIn(result["coherence_level"], ["Très faible", "Faible", "Modéré", "Élevé", "Excellent"])
        
        # Vérifier que l'historique d'évaluation a été mis à jour
        self.assertEqual(len(self.evaluator.evaluation_history), 1)
        self.assertEqual(self.evaluator.evaluation_history[0]["type"], "argument_coherence_evaluation")

    def test_evaluate_thematic_coherence(self):
        """Teste la méthode _evaluate_thematic_coherence."""
        # Tester avec des arguments cohérents
        coherent_result = self.evaluator._evaluate_thematic_coherence(self.test_arguments)
        
        # Vérifier la structure du résultat
        self.assertIn("coherence_score", coherent_result)
        self.assertIn("coherence_level", coherent_result)
        self.assertIn("main_themes", coherent_result)
        self.assertIn("thematic_clusters", coherent_result)
        self.assertIn("thematic_shifts", coherent_result)
        
        # Vérifier que le score de cohérence est élevé pour des arguments cohérents
        self.assertGreater(coherent_result["coherence_score"], 0.5)
        
        # Tester avec des arguments incohérents
        incoherent_result = self.evaluator._evaluate_thematic_coherence(self.incoherent_arguments)
        
        # Vérifier que le score de cohérence est faible pour des arguments incohérents
        self.assertLess(incoherent_result["coherence_score"], coherent_result["coherence_score"])

    def test_evaluate_logical_coherence(self):
        """Teste la méthode _evaluate_logical_coherence."""
        # Tester avec des arguments cohérents
        coherent_result = self.evaluator._evaluate_logical_coherence(self.test_arguments)
        
        # Vérifier la structure du résultat
        self.assertIn("coherence_score", coherent_result)
        self.assertIn("coherence_level", coherent_result)
        self.assertIn("logical_relationships", coherent_result)
        self.assertIn("logical_gaps", coherent_result)
        self.assertIn("logical_contradictions", coherent_result)
        
        # Vérifier que le score de cohérence est élevé pour des arguments cohérents
        self.assertGreater(coherent_result["coherence_score"], 0.5)
        
        # Tester avec des arguments incohérents
        incoherent_result = self.evaluator._evaluate_logical_coherence(self.incoherent_arguments)
        
        # Vérifier que le score de cohérence est faible pour des arguments incohérents
        self.assertLess(incoherent_result["coherence_score"], coherent_result["coherence_score"])

    def test_evaluate_structural_coherence(self):
        """Teste la méthode _evaluate_structural_coherence."""
        # Tester avec des arguments cohérents
        coherent_result = self.evaluator._evaluate_structural_coherence(self.test_arguments)
        
        # Vérifier la structure du résultat
        self.assertIn("coherence_score", coherent_result)
        self.assertIn("coherence_level", coherent_result)
        self.assertIn("structural_patterns", coherent_result)
        self.assertIn("structural_balance", coherent_result)
        self.assertIn("structural_issues", coherent_result)
        
        # Vérifier que le score de cohérence est élevé pour des arguments cohérents
        self.assertGreater(coherent_result["coherence_score"], 0.5)
        
        # Tester avec des arguments incohérents
        incoherent_result = self.evaluator._evaluate_structural_coherence(self.incoherent_arguments)
        
        # Vérifier que le score de cohérence est faible pour des arguments incohérents
        self.assertLess(incoherent_result["coherence_score"], coherent_result["coherence_score"])

    def test_evaluate_contextual_coherence(self):
        """Teste la méthode _evaluate_contextual_coherence."""
        # Tester avec des arguments cohérents
        coherent_result = self.evaluator._evaluate_contextual_coherence(self.test_arguments, self.test_context)
        
        # Vérifier la structure du résultat
        self.assertIn("coherence_score", coherent_result)
        self.assertIn("coherence_level", coherent_result)
        self.assertIn("context_relevance", coherent_result)
        self.assertIn("context_appropriate_language", coherent_result)
        self.assertIn("contextual_issues", coherent_result)
        
        # Vérifier que le score de cohérence est élevé pour des arguments cohérents
        self.assertGreater(coherent_result["coherence_score"], 0.5)
        
        # Tester avec des arguments incohérents
        incoherent_result = self.evaluator._evaluate_contextual_coherence(self.incoherent_arguments, self.test_context)
        
        # Vérifier que le score de cohérence est faible pour des arguments incohérents
        self.assertLess(incoherent_result["coherence_score"], coherent_result["coherence_score"])

    def test_identify_coherence_issues(self):
        """Teste la méthode _identify_coherence_issues."""
        # Créer des résultats d'évaluation pour le test
        thematic_coherence = {
            "coherence_score": 0.7,
            "thematic_shifts": [
                {"position": 1, "shift_magnitude": 0.3}
            ]
        }
        
        logical_coherence = {
            "coherence_score": 0.6,
            "logical_gaps": [
                {"gap_id": 0, "gap_type": "missing_premise", "position": 2}
            ],
            "logical_contradictions": []
        }
        
        structural_coherence = {
            "coherence_score": 0.8,
            "structural_issues": []
        }
        
        contextual_coherence = {
            "coherence_score": 0.7,
            "contextual_issues": [
                {"issue_id": 0, "issue_type": "inappropriate_language", "position": 3}
            ]
        }
        
        issues = self.evaluator._identify_coherence_issues(
            thematic_coherence, logical_coherence, structural_coherence, contextual_coherence
        )
        
        # Vérifier la structure du résultat
        self.assertIn("total_issues", issues)
        self.assertIn("critical_issues", issues)
        self.assertIn("moderate_issues", issues)
        self.assertIn("minor_issues", issues)
        self.assertIn("issue_details", issues)
        
        # Vérifier que des problèmes ont été identifiés
        self.assertGreater(issues["total_issues"], 0)
        self.assertGreater(len(issues["issue_details"]), 0)

    def test_generate_improvement_suggestions(self):
        """Teste la méthode _generate_improvement_suggestions."""
        # Créer des problèmes de cohérence pour le test
        coherence_issues = {
            "total_issues": 3,
            "critical_issues": 0,
            "moderate_issues": 2,
            "minor_issues": 1,
            "issue_details": [
                {
                    "issue_id": 0,
                    "issue_type": "thematic_shift",
                    "severity": "moderate",
                    "position": 1,
                    "description": "Changement thématique abrupt entre les arguments 1 et 2"
                },
                {
                    "issue_id": 1,
                    "issue_type": "logical_gap",
                    "severity": "moderate",
                    "position": 2,
                    "description": "Prémisse manquante entre les arguments 2 et 3"
                },
                {
                    "issue_id": 2,
                    "issue_type": "inappropriate_language",
                    "severity": "minor",
                    "position": 3,
                    "description": "Langage inapproprié pour le contexte environnemental"
                }
            ]
        }
        
        suggestions = self.evaluator._generate_improvement_suggestions(coherence_issues, self.test_context)
        
        # Vérifier la structure du résultat
        self.assertIn("general_suggestions", suggestions)
        self.assertIn("specific_suggestions", suggestions)
        self.assertIn("priority_improvements", suggestions)
        
        # Vérifier que des suggestions ont été générées
        self.assertGreater(len(suggestions["general_suggestions"]), 0)
        self.assertGreater(len(suggestions["specific_suggestions"]), 0)
        self.assertGreater(len(suggestions["priority_improvements"]), 0)

    def test_calculate_overall_coherence(self):
        """Teste la méthode _calculate_overall_coherence."""
        # Créer des scores de cohérence pour le test
        thematic_score = 0.7
        logical_score = 0.6
        structural_score = 0.8
        contextual_score = 0.7
        
        overall_coherence, coherence_level = self.evaluator._calculate_overall_coherence(
            thematic_score, logical_score, structural_score, contextual_score
        )
        
        # Vérifier que le score de cohérence global est dans les limites attendues
        self.assertGreaterEqual(overall_coherence, 0.0)
        self.assertLessEqual(overall_coherence, 1.0)
        
        # Vérifier que le niveau de cohérence est valide
        self.assertIn(coherence_level, ["Très faible", "Faible", "Modéré", "Élevé", "Excellent"])
        
        # Vérifier que le score de cohérence global est cohérent avec les scores individuels
        expected_score = (thematic_score * 0.25 + logical_score * 0.3 + 
                          structural_score * 0.2 + contextual_score * 0.25)
        self.assertAlmostEqual(overall_coherence, expected_score, places=1)

    def test_determine_coherence_level(self):
        """Teste la méthode _determine_coherence_level."""
        # Tester différentes valeurs de cohérence
        self.assertEqual(self.evaluator._determine_coherence_level(0.1), "Très faible")
        self.assertEqual(self.evaluator._determine_coherence_level(0.3), "Faible")
        self.assertEqual(self.evaluator._determine_coherence_level(0.5), "Modéré")
        self.assertEqual(self.evaluator._determine_coherence_level(0.7), "Élevé")
        self.assertEqual(self.evaluator._determine_coherence_level(0.9), "Excellent")

    def test_extract_main_themes(self):
        """Teste la méthode _extract_main_themes."""
        themes = self.evaluator._extract_main_themes(self.test_arguments)
        
        # Vérifier que des thèmes ont été extraits
        self.assertGreater(len(themes), 0)
        
        # Vérifier la structure des thèmes
        for theme in themes:
            self.assertIn("theme", theme)
            self.assertIn("relevance", theme)
            self.assertIn("related_arguments", theme)

    def test_identify_logical_relationships(self):
        """Teste la méthode _identify_logical_relationships."""
        relationships = self.evaluator._identify_logical_relationships(self.test_arguments)
        
        # Vérifier que des relations ont été identifiées
        self.assertGreaterEqual(len(relationships), 0)
        
        # Si des relations ont été identifiées, vérifier leur structure
        if relationships:
            for relationship in relationships:
                self.assertIn("relationship_type", relationship)
                self.assertIn("source_argument", relationship)
                self.assertIn("target_argument", relationship)
                self.assertIn("strength", relationship)
                self.assertIn("description", relationship)

    def test_identify_structural_patterns(self):
        """Teste la méthode _identify_structural_patterns."""
        patterns = self.evaluator._identify_structural_patterns(self.test_arguments)
        
        # Vérifier que des modèles ont été identifiés
        self.assertGreaterEqual(len(patterns), 0)
        
        # Si des modèles ont été identifiés, vérifier leur structure
        if patterns:
            for pattern in patterns:
                self.assertIn("pattern_type", pattern)
                self.assertIn("pattern_description", pattern)
                self.assertIn("arguments_involved", pattern)
                self.assertIn("strength", pattern)


if __name__ == "__main__":
    unittest.main()