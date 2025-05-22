#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module agents.tools.analysis.enhanced.fallacy_severity_evaluator.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch
import json
import logging
from datetime import datetime

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestEnhancedFallacySeverityEvaluator")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Import du module à tester
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator


class TestEnhancedFallacySeverityEvaluator(unittest.TestCase):
    """Tests unitaires pour l'évaluateur de gravité des sophismes amélioré."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer l'évaluateur de gravité des sophismes amélioré
        self.evaluator = EnhancedFallacySeverityEvaluator()
        
        # Créer des arguments pour les tests
        self.arguments = [
            "Les experts affirment que ce produit est sûr.",
            "Ce produit est utilisé par des millions de personnes.",
            "Par conséquent, vous devriez faire confiance aux experts et utiliser ce produit.",
            "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves."
        ]
        
        # Créer des sophismes pour les tests
        self.fallacies = [
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
        """Teste l'initialisation de l'évaluateur de gravité des sophismes amélioré."""
        # Vérifier que l'évaluateur a été correctement initialisé
        self.assertIsNotNone(self.evaluator)
        self.assertIsNotNone(self.evaluator.logger)
        
        # Vérifier que les bases de gravité ont été définies
        self.assertIsNotNone(self.evaluator.fallacy_severity_base)
        self.assertIn("Appel à l'autorité", self.evaluator.fallacy_severity_base)
        self.assertIn("Appel à la popularité", self.evaluator.fallacy_severity_base)
        self.assertIn("Appel à la peur", self.evaluator.fallacy_severity_base)
        
        # Vérifier que les modificateurs de contexte ont été définis
        self.assertIsNotNone(self.evaluator.context_severity_modifiers)
        self.assertIn("académique", self.evaluator.context_severity_modifiers)
        self.assertIn("scientifique", self.evaluator.context_severity_modifiers)
        self.assertIn("politique", self.evaluator.context_severity_modifiers)
        
        # Vérifier que les modificateurs d'audience ont été définis
        self.assertIsNotNone(self.evaluator.audience_severity_modifiers)
        self.assertIn("experts", self.evaluator.audience_severity_modifiers)
        self.assertIn("grand public", self.evaluator.audience_severity_modifiers)
        
        # Vérifier que les modificateurs de domaine ont été définis
        self.assertIsNotNone(self.evaluator.domain_severity_modifiers)
        self.assertIn("santé", self.evaluator.domain_severity_modifiers)
        self.assertIn("politique", self.evaluator.domain_severity_modifiers)
    
    def test_evaluate_fallacy_severity(self):
        """Teste la méthode evaluate_fallacy_severity."""
        # Appeler la méthode evaluate_fallacy_severity
        result = self.evaluator.evaluate_fallacy_severity(self.arguments, "commercial")
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("overall_severity", result)
        self.assertIn("severity_level", result)
        self.assertIn("fallacy_evaluations", result)
        self.assertIn("context_analysis", result)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier les évaluations de sophismes
        self.assertIsInstance(result["fallacy_evaluations"], list)
        self.assertGreaterEqual(len(result["fallacy_evaluations"]), 1)
        
        # Vérifier l'analyse du contexte
        self.assertIsInstance(result["context_analysis"], dict)
        self.assertIn("context_type", result["context_analysis"])
        self.assertIn("audience_type", result["context_analysis"])
        self.assertIn("domain_type", result["context_analysis"])
        self.assertEqual(result["context_analysis"]["context_type"], "commercial")
    
    def test_evaluate_fallacy_list(self):
        """Teste la méthode evaluate_fallacy_list."""
        # Appeler la méthode evaluate_fallacy_list
        result = self.evaluator.evaluate_fallacy_list(self.fallacies, "scientifique")
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("overall_severity", result)
        self.assertIn("severity_level", result)
        self.assertIn("fallacy_evaluations", result)
        self.assertIn("context_analysis", result)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier les évaluations de sophismes
        self.assertIsInstance(result["fallacy_evaluations"], list)
        self.assertEqual(len(result["fallacy_evaluations"]), 3)
        
        # Vérifier l'analyse du contexte
        self.assertIsInstance(result["context_analysis"], dict)
        self.assertIn("context_type", result["context_analysis"])
        self.assertIn("audience_type", result["context_analysis"])
        self.assertIn("domain_type", result["context_analysis"])
        self.assertEqual(result["context_analysis"]["context_type"], "scientifique")
        
        # Vérifier que la gravité globale est correcte
        self.assertGreaterEqual(result["overall_severity"], 0.0)
        self.assertLessEqual(result["overall_severity"], 1.0)
        self.assertIn(result["severity_level"], ["Faible", "Modéré", "Élevé", "Critique"])
    
    def test_analyze_context_impact(self):
        """Teste la méthode _analyze_context_impact."""
        # Appeler la méthode _analyze_context_impact
        context_analysis = self.evaluator._analyze_context_impact("scientifique")
        
        # Vérifier le résultat
        self.assertIsInstance(context_analysis, dict)
        self.assertIn("context_type", context_analysis)
        self.assertIn("audience_type", context_analysis)
        self.assertIn("domain_type", context_analysis)
        self.assertIn("context_severity_modifier", context_analysis)
        self.assertIn("audience_severity_modifier", context_analysis)
        self.assertIn("domain_severity_modifier", context_analysis)
        
        # Vérifier les valeurs
        self.assertEqual(context_analysis["context_type"], "scientifique")
        self.assertEqual(context_analysis["audience_type"], "experts")
        self.assertEqual(context_analysis["domain_type"], "sciences")
        self.assertEqual(context_analysis["context_severity_modifier"], 0.3)
        self.assertEqual(context_analysis["audience_severity_modifier"], 0.2)
        self.assertEqual(context_analysis["domain_severity_modifier"], 0.2)
    
    def test_calculate_fallacy_severity(self):
        """Teste la méthode _calculate_fallacy_severity."""
        # Créer un sophisme
        fallacy = {
            "fallacy_type": "Appel à l'autorité",
            "context_text": "Les experts affirment que ce produit est sûr.",
            "confidence": 0.7
        }
        
        # Créer une analyse de contexte
        context_analysis = {
            "context_type": "scientifique",
            "audience_type": "experts",
            "domain_type": "sciences",
            "context_severity_modifier": 0.3,
            "audience_severity_modifier": 0.2,
            "domain_severity_modifier": 0.2
        }
        
        # Appeler la méthode _calculate_fallacy_severity
        severity_evaluation = self.evaluator._calculate_fallacy_severity(fallacy, context_analysis)
        
        # Vérifier le résultat
        self.assertIsInstance(severity_evaluation, dict)
        self.assertIn("fallacy_type", severity_evaluation)
        self.assertIn("context_text", severity_evaluation)
        self.assertIn("base_severity", severity_evaluation)
        self.assertIn("context_modifier", severity_evaluation)
        self.assertIn("audience_modifier", severity_evaluation)
        self.assertIn("domain_modifier", severity_evaluation)
        self.assertIn("final_severity", severity_evaluation)
        self.assertIn("severity_level", severity_evaluation)
        
        # Vérifier les valeurs
        self.assertEqual(severity_evaluation["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(severity_evaluation["context_text"], "Les experts affirment que ce produit est sûr.")
        self.assertEqual(severity_evaluation["base_severity"], 0.6)
        self.assertEqual(severity_evaluation["context_modifier"], 0.3)
        self.assertEqual(severity_evaluation["audience_modifier"], 0.2)
        self.assertEqual(severity_evaluation["domain_modifier"], 0.2)
        
        # Vérifier que la gravité finale est correcte
        expected_severity = min(1.0, 0.6 + 0.3 + 0.2 + 0.2)
        self.assertEqual(severity_evaluation["final_severity"], expected_severity)
        
        # Vérifier que le niveau de gravité est correct
        self.assertIn(severity_evaluation["severity_level"], ["Faible", "Modéré", "Élevé", "Critique"])
    
    def test_determine_severity_level(self):
        """Teste la méthode _determine_severity_level."""
        # Tester différentes valeurs de gravité
        self.assertEqual(self.evaluator._determine_severity_level(0.3), "Faible")
        self.assertEqual(self.evaluator._determine_severity_level(0.5), "Modéré")
        self.assertEqual(self.evaluator._determine_severity_level(0.8), "Élevé")
        self.assertEqual(self.evaluator._determine_severity_level(0.95), "Critique")
    
    def test_calculate_overall_severity(self):
        """Teste la méthode _calculate_overall_severity."""
        # Créer des évaluations de sophismes
        fallacy_evaluations = [
            {
                "fallacy_type": "Appel à l'autorité",
                "context_text": "Les experts affirment que ce produit est sûr.",
                "base_severity": 0.6,
                "context_modifier": 0.3,
                "audience_modifier": 0.2,
                "domain_modifier": 0.2,
                "final_severity": 1.0,
                "severity_level": "Critique"
            },
            {
                "fallacy_type": "Appel à la popularité",
                "context_text": "Ce produit est utilisé par des millions de personnes.",
                "base_severity": 0.5,
                "context_modifier": 0.1,
                "audience_modifier": 0.0,
                "domain_modifier": 0.1,
                "final_severity": 0.7,
                "severity_level": "Élevé"
            },
            {
                "fallacy_type": "Appel à la peur",
                "context_text": "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves.",
                "base_severity": 0.8,
                "context_modifier": 0.1,
                "audience_modifier": 0.1,
                "domain_modifier": 0.2,
                "final_severity": 1.0,
                "severity_level": "Critique"
            }
        ]
        
        # Appeler la méthode _calculate_overall_severity
        overall_severity, severity_level = self.evaluator._calculate_overall_severity(fallacy_evaluations)
        
        # Vérifier le résultat
        self.assertIsInstance(overall_severity, float)
        self.assertIsInstance(severity_level, str)
        
        # Vérifier que la gravité globale est correcte
        # (0.7 * moyenne) + (0.3 * max)
        # moyenne = (1.0 + 0.7 + 1.0) / 3 = 0.9
        # max = 1.0
        # overall_severity = (0.7 * 0.9) + (0.3 * 1.0) = 0.63 + 0.3 = 0.93
        expected_severity = (0.7 * ((1.0 + 0.7 + 1.0) / 3)) + (0.3 * 1.0)
        self.assertAlmostEqual(overall_severity, expected_severity, places=2)
        
        # Vérifier que le niveau de gravité est correct
        self.assertEqual(severity_level, "Critique")
    
    def test_calculate_overall_severity_empty_list(self):
        """Teste la méthode _calculate_overall_severity avec une liste vide."""
        # Appeler la méthode _calculate_overall_severity avec une liste vide
        overall_severity, severity_level = self.evaluator._calculate_overall_severity([])
        
        # Vérifier le résultat
        self.assertEqual(overall_severity, 0.0)
        self.assertEqual(severity_level, "Faible")
    
    def test_evaluate_fallacy_severity_with_different_contexts(self):
        """Teste la méthode evaluate_fallacy_severity avec différents contextes."""
        # Tester différents contextes
        contexts = ["académique", "politique", "commercial", "juridique", "médical"]
        
        for context in contexts:
            # Appeler la méthode evaluate_fallacy_severity
            result = self.evaluator.evaluate_fallacy_severity(self.arguments, context)
            
            # Vérifier le résultat
            self.assertIsInstance(result, dict)
            self.assertIn("overall_severity", result)
            self.assertIn("severity_level", result)
            self.assertIn("fallacy_evaluations", result)
            self.assertIn("context_analysis", result)
            
            # Vérifier l'analyse du contexte
            self.assertEqual(result["context_analysis"]["context_type"], context)


if __name__ == "__main__":
    unittest.main()