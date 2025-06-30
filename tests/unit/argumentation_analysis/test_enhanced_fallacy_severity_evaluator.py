
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module EnhancedFallacySeverityEvaluator.
"""

import unittest

import json
from datetime import datetime
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator


class TestEnhancedFallacySeverityEvaluator(unittest.TestCase):
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

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

    
    
    
    def test_evaluate_fallacy_severity(self):
        """Teste l'évaluation de la gravité des sophismes dans une liste d'arguments."""
        # Appeler la méthode principale
        result = self.evaluator.evaluate_fallacy_severity(self.test_arguments, "commercial")
        
        # Vérifier les résultats
        self.assertIn("overall_severity", result)
        self.assertIn("severity_level", result)
        self.assertIn("fallacy_evaluations", result)
        self.assertIn("context_analysis", result)
        
        # La logique simulée trouve 4 sophismes (2x Appel à l'autorité)
        self.assertEqual(len(result["fallacy_evaluations"]), 4)
        fallacy_types = [eval["fallacy_type"] for eval in result["fallacy_evaluations"]]
        self.assertEqual(fallacy_types.count("Appel à l'autorité"), 2)
        self.assertIn("Appel à la popularité", fallacy_types)
        self.assertIn("Appel à la peur", fallacy_types)

        # Recalcul de la gravité globale pour ce cas
        # severities = [0.8, 0.7, 0.8, 1.0]
        # avg = 3.3 / 4 = 0.825
        # max = 1.0
        # overall = (0.825 * 0.7) + (1.0 * 0.3) = 0.5775 + 0.3 = 0.8775
        self.assertAlmostEqual(result["overall_severity"], 0.8775, places=4)
        self.assertEqual(result["severity_level"], "Élevé")

    
    
    
    def test_evaluate_fallacy_list(self):
        """Teste l'évaluation de la gravité d'une liste de sophismes."""
        # Appeler la méthode à tester
        result = self.evaluator.evaluate_fallacy_list(self.test_fallacies, "commercial")

        # Vérifier les résultats
        self.assertIn("overall_severity", result)
        self.assertIn("severity_level", result)
        self.assertIn("fallacy_evaluations", result)
        self.assertIn("context_analysis", result)

        # Vérifier que tous les sophismes ont été évalués
        self.assertEqual(len(result["fallacy_evaluations"]), len(self.test_fallacies))

        # Vérifier un exemple de calcul de gravité
        appeal_to_authority_eval = next(item for item in result["fallacy_evaluations"] if item["fallacy_type"] == "Appel à l'autorité")
        self.assertEqual(appeal_to_authority_eval["base_severity"], 0.6)
        self.assertEqual(appeal_to_authority_eval["context_modifier"], 0.1)  # commercial
        self.assertEqual(appeal_to_authority_eval["audience_modifier"], 0.0) # grand public
        self.assertEqual(appeal_to_authority_eval["domain_modifier"], 0.1)  # finance
        self.assertAlmostEqual(appeal_to_authority_eval["final_severity"], 0.8, places=7)
        self.assertEqual(appeal_to_authority_eval["severity_level"], "Élevé")
        
        # Vérifier le score global
        # Recalcul des valeurs attendues :
        # Appel à l'autorité: 0.6 + 0.1 (comm) + 0.0 (grand pub) + 0.1 (fin) = 0.8
        # Appel à la popularité: 0.5 + 0.2 = 0.7
        # Appel à la peur: 0.8 + 0.2 = 1.0
        # severities = [0.8, 0.7, 1.0]
        # avg = 2.5 / 3 = 0.8333
        # max = 1.0
        # overall = (0.8333 * 0.7) + (1.0 * 0.3) = 0.5833 + 0.3 = 0.8833
        self.assertAlmostEqual(result["overall_severity"], 0.8833, places=4)
        self.assertEqual(result["severity_level"], "Élevé")

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
        self.assertAlmostEqual(result["final_severity"], 0.8, places=7)
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