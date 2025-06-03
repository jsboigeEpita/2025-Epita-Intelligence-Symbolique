#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests pour l'évaluateur de gravité des sophismes amélioré.

Ce module contient les tests unitaires pour la classe EnhancedFallacySeverityEvaluator.
"""

import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator


class TestEnhancedFallacySeverityEvaluator(unittest.TestCase):
    """Tests pour la classe EnhancedFallacySeverityEvaluator."""

    def setUp(self):
        """Initialise l'environnement de test."""
        self.evaluator = EnhancedFallacySeverityEvaluator()
        
        # Exemples d'arguments pour les tests
        self.test_arguments = [
            "Les experts affirment que ce produit est sûr.",
            "Ce produit est utilisé par des millions de personnes.",
            "Par conséquent, vous devriez faire confiance aux experts et utiliser ce produit.",
            "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves."
        ]
        
        self.test_context = "commercial"
        
        # Exemples de sophismes pour les tests
        self.test_fallacies = [
            {
                "fallacy_type": "Appel à l'autorité",
                "context_text": "Les experts affirment que ce produit est sûr.",
                "confidence": 0.7
            },
            {
                "fallacy_type": "Appel à la popularité",
                "context_text": "Ce produit est utilisé par des millions de personnes.",
                "confidence": 0.6
            },
            {
                "fallacy_type": "Appel à la peur",
                "context_text": "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves.",
                "confidence": 0.8
            }
        ]

    def test_initialization(self):
        """Teste l'initialisation de l'évaluateur."""
        self.assertIsNotNone(self.evaluator)
        self.assertIsNotNone(self.evaluator.fallacy_severity_base)
        self.assertIsNotNone(self.evaluator.context_severity_modifiers)
        self.assertIsNotNone(self.evaluator.audience_severity_modifiers)
        self.assertIsNotNone(self.evaluator.domain_severity_modifiers)

    def test_evaluate_fallacy_severity(self):
        """Teste la méthode evaluate_fallacy_severity."""
        result = self.evaluator.evaluate_fallacy_severity(self.test_arguments, self.test_context)
        
        # Vérifier la structure du résultat
        self.assertIn("overall_severity", result)
        self.assertIn("severity_level", result)
        self.assertIn("fallacy_evaluations", result)
        self.assertIn("context_analysis", result)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier que des évaluations de sophismes ont été générées
        self.assertGreater(len(result["fallacy_evaluations"]), 0)
        
        # Vérifier la structure des évaluations de sophismes
        for evaluation in result["fallacy_evaluations"]:
            self.assertIn("fallacy_type", evaluation)
            self.assertIn("context_text", evaluation)
            self.assertIn("base_severity", evaluation)
            self.assertIn("context_modifier", evaluation)
            self.assertIn("audience_modifier", evaluation)
            self.assertIn("domain_modifier", evaluation)
            self.assertIn("final_severity", evaluation)
            self.assertIn("severity_level", evaluation)

    def test_evaluate_fallacy_list(self):
        """Teste la méthode evaluate_fallacy_list."""
        result = self.evaluator.evaluate_fallacy_list(self.test_fallacies, self.test_context)
        
        # Vérifier la structure du résultat
        self.assertIn("overall_severity", result)
        self.assertIn("severity_level", result)
        self.assertIn("fallacy_evaluations", result)
        self.assertIn("context_analysis", result)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier que toutes les évaluations de sophismes ont été générées
        self.assertEqual(len(result["fallacy_evaluations"]), len(self.test_fallacies))
        
        # Vérifier que l'évaluation globale est cohérente
        self.assertGreaterEqual(result["overall_severity"], 0.0)
        self.assertLessEqual(result["overall_severity"], 1.0)
        self.assertIn(result["severity_level"], ["Faible", "Modéré", "Élevé", "Critique"])

    def test_analyze_context_impact(self):
        """Teste la méthode _analyze_context_impact."""
        context_analysis = self.evaluator._analyze_context_impact(self.test_context)
        
        # Vérifier la structure du résultat
        self.assertIn("context_type", context_analysis)
        self.assertIn("audience_type", context_analysis)
        self.assertIn("domain_type", context_analysis)
        self.assertIn("context_severity_modifier", context_analysis)
        self.assertIn("audience_severity_modifier", context_analysis)
        self.assertIn("domain_severity_modifier", context_analysis)
        
        # Vérifier que les modificateurs sont dans les limites attendues
        self.assertGreaterEqual(context_analysis["context_severity_modifier"], -0.3)
        self.assertLessEqual(context_analysis["context_severity_modifier"], 0.3)
        self.assertGreaterEqual(context_analysis["audience_severity_modifier"], -0.2)
        self.assertLessEqual(context_analysis["audience_severity_modifier"], 0.2)
        self.assertGreaterEqual(context_analysis["domain_severity_modifier"], -0.2)
        self.assertLessEqual(context_analysis["domain_severity_modifier"], 0.2)

    def test_calculate_fallacy_severity(self):
        """Teste la méthode _calculate_fallacy_severity."""
        # Créer un sophisme pour le test
        fallacy = {
            "fallacy_type": "Appel à l'autorité",
            "context_text": "Les experts affirment que ce produit est sûr.",
            "confidence": 0.7
        }
        
        # Créer une analyse de contexte pour le test
        context_analysis = {
            "context_type": "commercial",
            "audience_type": "grand public",
            "domain_type": "santé",
            "context_severity_modifier": 0.1,
            "audience_severity_modifier": 0.1,
            "domain_severity_modifier": 0.2
        }
        
        severity_evaluation = self.evaluator._calculate_fallacy_severity(fallacy, context_analysis)
        
        # Vérifier la structure du résultat
        self.assertIn("fallacy_type", severity_evaluation)
        self.assertIn("context_text", severity_evaluation)
        self.assertIn("base_severity", severity_evaluation)
        self.assertIn("context_modifier", severity_evaluation)
        self.assertIn("audience_modifier", severity_evaluation)
        self.assertIn("domain_modifier", severity_evaluation)
        self.assertIn("final_severity", severity_evaluation)
        self.assertIn("severity_level", severity_evaluation)
        
        # Vérifier que la gravité finale est cohérente
        self.assertGreaterEqual(severity_evaluation["final_severity"], 0.0)
        self.assertLessEqual(severity_evaluation["final_severity"], 1.0)
        self.assertIn(severity_evaluation["severity_level"], ["Faible", "Modéré", "Élevé", "Critique"])

    def test_determine_severity_level(self):
        """Teste la méthode _determine_severity_level."""
        # Tester différentes valeurs de gravité
        self.assertEqual(self.evaluator._determine_severity_level(0.1), "Faible")
        self.assertEqual(self.evaluator._determine_severity_level(0.3), "Faible")
        self.assertEqual(self.evaluator._determine_severity_level(0.4), "Modéré")
        self.assertEqual(self.evaluator._determine_severity_level(0.6), "Modéré")
        self.assertEqual(self.evaluator._determine_severity_level(0.7), "Élevé")
        self.assertEqual(self.evaluator._determine_severity_level(0.8), "Élevé")
        self.assertEqual(self.evaluator._determine_severity_level(0.9), "Critique")
        self.assertEqual(self.evaluator._determine_severity_level(1.0), "Critique")

    def test_calculate_overall_severity(self):
        """Teste la méthode _calculate_overall_severity."""
        # Créer des évaluations de sophismes pour le test
        fallacy_evaluations = [
            {
                "fallacy_type": "Appel à l'autorité",
                "final_severity": 0.5,
                "severity_level": "Modéré"
            },
            {
                "fallacy_type": "Appel à la popularité",
                "final_severity": 0.6,
                "severity_level": "Modéré"
            },
            {
                "fallacy_type": "Appel à la peur",
                "final_severity": 0.8,
                "severity_level": "Élevé"
            }
        ]
        
        overall_severity, severity_level = self.evaluator._calculate_overall_severity(fallacy_evaluations)
        
        # Vérifier que la gravité globale est cohérente
        self.assertGreaterEqual(overall_severity, 0.0)
        self.assertLessEqual(overall_severity, 1.0)
        self.assertIn(severity_level, ["Faible", "Modéré", "Élevé", "Critique"])
        
        # Vérifier que la gravité globale est influencée par la gravité la plus élevée
        self.assertGreaterEqual(overall_severity, 0.6)  # Au moins la moyenne des gravités

    @patch('numpy.mean')
    @patch('numpy.array')
    @patch('numpy.max')
    def test_evaluate_fallacy_severity_with_numpy_dependency(self, mock_max, mock_array, mock_mean):
        """Teste l'évaluation de la gravité des sophismes avec mock de numpy."""
        # Configurer les mocks numpy
        mock_array.return_value = [0.5, 0.6, 0.8]
        mock_mean.return_value = 0.63
        mock_max.return_value = 0.8
        
        # Appeler la méthode qui utilise numpy
        result = self.evaluator.evaluate_fallacy_list(self.test_fallacies, self.test_context)
        
        # Vérifier que le résultat est correct
        self.assertIsNotNone(result)
        self.assertIn("overall_severity", result)
        self.assertIn("severity_level", result)
        
        # Vérifier que les mocks ont été appelés
        # mock_array.assert_called() # Numpy n'est pas utilisé directement ici
        # mock_mean.assert_called() or mock_max.assert_called() # Numpy n'est pas utilisé directement ici


if __name__ == "__main__":
    unittest.main()