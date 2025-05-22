"""
Tests unitaires pour le module EnhancedFallacySeverityEvaluator.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator


class TestEnhancedFallacySeverityEvaluator(unittest.TestCase):
    """Tests pour la classe EnhancedFallacySeverityEvaluator."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer une instance de l'évaluateur
        self.evaluator = EnhancedFallacySeverityEvaluator()
        
        # Données de test
        self.test_arguments = [
            "Les experts affirment que ce produit est sûr.",
            "Ce produit est utilisé par des millions de personnes.",
            "Par conséquent, vous devriez faire confiance aux experts et utiliser ce produit.",
            "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves."
        ]
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

    def test_init(self):
        """Teste l'initialisation de l'évaluateur."""
        # Vérifier que l'évaluateur est correctement initialisé
        self.assertIsNotNone(self.evaluator)
        self.assertIsNotNone(self.evaluator.fallacy_severity_base)
        self.assertIsNotNone(self.evaluator.context_severity_modifiers)
        self.assertIsNotNone(self.evaluator.audience_severity_modifiers)
        self.assertIsNotNone(self.evaluator.domain_severity_modifiers)
        
        # Vérifier que les dictionnaires de gravité sont correctement initialisés
        self.assertIn("Appel à l'autorité", self.evaluator.fallacy_severity_base)
        self.assertIn("académique", self.evaluator.context_severity_modifiers)
        self.assertIn("experts", self.evaluator.audience_severity_modifiers)
        self.assertIn("santé", self.evaluator.domain_severity_modifiers)

    @patch('argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator.EnhancedFallacySeverityEvaluator._analyze_context_impact')
    @patch('argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator.EnhancedFallacySeverityEvaluator._calculate_fallacy_severity')
    @patch('argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator.EnhancedFallacySeverityEvaluator._calculate_overall_severity')
    def test_evaluate_fallacy_severity(self, mock_overall_severity, mock_calculate_severity, mock_analyze_context):
        """Teste l'évaluation de la gravité des sophismes dans une liste d'arguments."""
        # Configurer les mocks
        mock_analyze_context.return_value = {
            "context_type": "commercial",
            "audience_type": "grand public",
            "domain_type": "finance"
        }
        mock_calculate_severity.return_value = {
            "fallacy_type": "Appel à l'autorité",
            "final_severity": 0.7,
            "severity_level": "Modéré"
        }
        mock_overall_severity.return_value = (0.75, "Élevé")
        
        # Appeler la méthode à tester
        result = self.evaluator.evaluate_fallacy_severity(self.test_arguments, "commercial")
        
        # Vérifier les résultats
        self.assertEqual(result["overall_severity"], 0.75)
        self.assertEqual(result["severity_level"], "Élevé")
        self.assertIn("fallacy_evaluations", result)
        self.assertIn("context_analysis", result)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier que les mocks ont été appelés correctement
        mock_analyze_context.assert_called_once_with("commercial")
        self.assertEqual(mock_calculate_severity.call_count, 3)  # 3 sophismes détectés
        mock_overall_severity.assert_called_once()

    @patch('argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator.EnhancedFallacySeverityEvaluator._analyze_context_impact')
    @patch('argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator.EnhancedFallacySeverityEvaluator._calculate_fallacy_severity')
    @patch('argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator.EnhancedFallacySeverityEvaluator._calculate_overall_severity')
    def test_evaluate_fallacy_list(self, mock_overall_severity, mock_calculate_severity, mock_analyze_context):
        """Teste l'évaluation de la gravité d'une liste de sophismes."""
        # Configurer les mocks
        mock_analyze_context.return_value = {
            "context_type": "commercial",
            "audience_type": "grand public",
            "domain_type": "finance"
        }
        mock_calculate_severity.side_effect = [
            {
                "fallacy_type": "Appel à l'autorité",
                "final_severity": 0.7,
                "severity_level": "Modéré"
            },
            {
                "fallacy_type": "Appel à la popularité",
                "final_severity": 0.6,
                "severity_level": "Modéré"
            },
            {
                "fallacy_type": "Appel à la peur",
                "final_severity": 0.9,
                "severity_level": "Critique"
            }
        ]
        mock_overall_severity.return_value = (0.8, "Élevé")
        
        # Appeler la méthode à tester
        result = self.evaluator.evaluate_fallacy_list(self.test_fallacies, "commercial")
        
        # Vérifier les résultats
        self.assertEqual(result["overall_severity"], 0.8)
        self.assertEqual(result["severity_level"], "Élevé")
        self.assertEqual(len(result["fallacy_evaluations"]), 3)
        self.assertIn("context_analysis", result)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier que les mocks ont été appelés correctement
        mock_analyze_context.assert_called_once_with("commercial")
        self.assertEqual(mock_calculate_severity.call_count, 3)
        mock_overall_severity.assert_called_once()

    def test_analyze_context_impact(self):
        """Teste l'analyse de l'impact du contexte sur la gravité des sophismes."""
        # Tester différents contextes
        contexts = ["académique", "politique", "commercial", "médical", "général", "contexte_inconnu"]
        
        for context in contexts:
            result = self.evaluator._analyze_context_impact(context)
            
            # Vérifier les résultats
            self.assertIn("context_type", result)
            self.assertIn("audience_type", result)
            self.assertIn("domain_type", result)
            self.assertIn("context_severity_modifier", result)
            self.assertIn("audience_severity_modifier", result)
            self.assertIn("domain_severity_modifier", result)
            
            # Vérifier que les types sont correctement déterminés
            if context in self.evaluator.context_severity_modifiers:
                self.assertEqual(result["context_type"], context)
            else:
                self.assertEqual(result["context_type"], "général")

    def test_calculate_fallacy_severity(self):
        """Teste le calcul de la gravité d'un sophisme."""
        # Données de test
        fallacy = {
            "fallacy_type": "Appel à l'autorité",
            "context_text": "Les experts affirment que ce produit est sûr.",
            "confidence": 0.7
        }
        context_analysis = {
            "context_type": "commercial",
            "audience_type": "grand public",
            "domain_type": "finance",
            "context_severity_modifier": 0.1,
            "audience_severity_modifier": 0.0,
            "domain_severity_modifier": 0.1
        }
        
        # Appeler la méthode à tester
        result = self.evaluator._calculate_fallacy_severity(fallacy, context_analysis)
        
        # Vérifier les résultats
        self.assertEqual(result["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(result["context_text"], "Les experts affirment que ce produit est sûr.")
        self.assertEqual(result["base_severity"], 0.6)
        self.assertEqual(result["context_modifier"], 0.1)
        self.assertEqual(result["audience_modifier"], 0.0)
        self.assertEqual(result["domain_modifier"], 0.1)
        self.assertEqual(result["final_severity"], 0.8)
        self.assertEqual(result["severity_level"], "Élevé")
        
        # Tester avec un sophisme inconnu
        fallacy_unknown = {
            "fallacy_type": "Sophisme inconnu",
            "context_text": "Texte quelconque",
            "confidence": 0.5
        }
        result_unknown = self.evaluator._calculate_fallacy_severity(fallacy_unknown, context_analysis)
        self.assertEqual(result_unknown["base_severity"], 0.5)  # Valeur par défaut

    def test_determine_severity_level(self):
        """Teste la détermination du niveau de gravité en fonction d'une valeur numérique."""
        # Tester différentes valeurs de gravité
        self.assertEqual(self.evaluator._determine_severity_level(0.0), "Faible")
        self.assertEqual(self.evaluator._determine_severity_level(0.3), "Faible")
        self.assertEqual(self.evaluator._determine_severity_level(0.4), "Modéré")
        self.assertEqual(self.evaluator._determine_severity_level(0.6), "Modéré")
        self.assertEqual(self.evaluator._determine_severity_level(0.7), "Élevé")
        self.assertEqual(self.evaluator._determine_severity_level(0.8), "Élevé")
        self.assertEqual(self.evaluator._determine_severity_level(0.9), "Critique")
        self.assertEqual(self.evaluator._determine_severity_level(1.0), "Critique")

    def test_calculate_overall_severity(self):
        """Teste le calcul de la gravité globale à partir d'une liste d'évaluations de sophismes."""
        # Données de test
        fallacy_evaluations = [
            {"final_severity": 0.6, "severity_level": "Modéré"},
            {"final_severity": 0.7, "severity_level": "Élevé"},
            {"final_severity": 0.8, "severity_level": "Élevé"}
        ]
        
        # Appeler la méthode à tester
        overall_severity, severity_level = self.evaluator._calculate_overall_severity(fallacy_evaluations)
        
        # Vérifier les résultats
        self.assertAlmostEqual(overall_severity, 0.73)  # (0.7 * (0.6 + 0.7 + 0.8) / 3) + (0.3 * 0.8)
        self.assertEqual(severity_level, "Élevé")
        
        # Tester avec une liste vide
        empty_severity, empty_level = self.evaluator._calculate_overall_severity([])
        self.assertEqual(empty_severity, 0.0)
        self.assertEqual(empty_level, "Faible")
        
        # Tester avec une liste contenant un seul élément
        single_severity, single_level = self.evaluator._calculate_overall_severity([{"final_severity": 0.9}])
        self.assertEqual(single_severity, 0.9)
        self.assertEqual(single_level, "Critique")

    def test_integration(self):
        """Teste l'intégration des différentes méthodes."""
        # Appeler la méthode principale
        result = self.evaluator.evaluate_fallacy_severity(self.test_arguments, "commercial")
        
        # Vérifier les résultats
        self.assertIn("overall_severity", result)
        self.assertIn("severity_level", result)
        self.assertIn("fallacy_evaluations", result)
        self.assertIn("context_analysis", result)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier que les sophismes ont été correctement détectés
        fallacy_types = [eval["fallacy_type"] for eval in result["fallacy_evaluations"]]
        self.assertIn("Appel à l'autorité", fallacy_types)
        self.assertIn("Appel à la popularité", fallacy_types)
        self.assertIn("Appel à la peur", fallacy_types)


if __name__ == '__main__':
    unittest.main()