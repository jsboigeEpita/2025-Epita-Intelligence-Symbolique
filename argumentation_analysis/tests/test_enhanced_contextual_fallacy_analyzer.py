"""
Tests unitaires pour le module EnhancedContextualFallacyAnalyzer.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import os
from pathlib import Path
from tests.async_test_case import AsyncTestCase
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer


class TestEnhancedContextualFallacyAnalyzer(unittest.TestCase):
    """Tests pour la classe EnhancedContextualFallacyAnalyzer."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Patcher les dépendances externes
        self.patcher_transformers = patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.HAS_TRANSFORMERS', False)
        self.mock_transformers = self.patcher_transformers.start()
        
        # Créer une instance de l'analyseur
        self.analyzer = EnhancedContextualFallacyAnalyzer()
        
        # Données de test
        self.test_text = "Les experts sont unanimes : ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà."
        self.test_context = "commercial"

    def tearDown(self):
        """Nettoyage après chaque test."""
        self.patcher_transformers.stop()

    def test_init(self):
        """Teste l'initialisation de l'analyseur."""
        # Vérifier que l'analyseur est correctement initialisé
        self.assertIsNotNone(self.analyzer)
        self.assertEqual(self.analyzer.model_name, "distilbert-base-uncased")
        self.assertEqual(len(self.analyzer.feedback_history), 0)
        self.assertEqual(len(self.analyzer.context_embeddings_cache), 0)
        self.assertEqual(len(self.analyzer.last_analysis_fallacies), 0)
        self.assertIsNotNone(self.analyzer.learning_data)

    def test_determine_context_type(self):
        """Teste la détermination du type de contexte."""
        # Tester différents types de contexte
        self.assertEqual(self.analyzer._determine_context_type("discours politique"), "politique")
        self.assertEqual(self.analyzer._determine_context_type("article scientifique"), "scientifique")
        self.assertEqual(self.analyzer._determine_context_type("publicité commerciale"), "commercial")
        self.assertEqual(self.analyzer._determine_context_type("débat juridique"), "juridique")
        self.assertEqual(self.analyzer._determine_context_type("cours académique"), "académique")
        self.assertEqual(self.analyzer._determine_context_type("conversation générale"), "général")
        self.assertEqual(self.analyzer._determine_context_type("contexte inconnu"), "général")

    @patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.EnhancedContextualFallacyAnalyzer._analyze_context_deeply')
    @patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.EnhancedContextualFallacyAnalyzer._identify_potential_fallacies_with_nlp')
    @patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.EnhancedContextualFallacyAnalyzer._filter_by_context_semantic')
    @patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.EnhancedContextualFallacyAnalyzer._analyze_fallacy_relations')
    def test_analyze_context(self, mock_analyze_relations, mock_filter_context, mock_identify_fallacies, mock_analyze_context):
        """Teste l'analyse du contexte."""
        # Configurer les mocks
        mock_analyze_context.return_value = {
            "context_type": "commercial",
            "context_subtypes": ["publicitaire"],
            "audience_characteristics": ["généraliste"],
            "formality_level": "moyen",
            "confidence": 0.8
        }
        mock_identify_fallacies.return_value = [
            {"fallacy_type": "Appel à l'autorité", "confidence": 0.7},
            {"fallacy_type": "Appel à la popularité", "confidence": 0.6}
        ]
        mock_filter_context.return_value = [
            {"fallacy_type": "Appel à l'autorité", "confidence": 0.8, "contextual_relevance": "Élevée"},
            {"fallacy_type": "Appel à la popularité", "confidence": 0.7, "contextual_relevance": "Élevée"}
        ]
        mock_analyze_relations.return_value = [
            {"relation_type": "complementary", "fallacy1_type": "Appel à l'autorité", "fallacy2_type": "Appel à la popularité"}
        ]
        
        # Appeler la méthode à tester
        result = self.analyzer.analyze_context(self.test_text, self.test_context)
        
        # Vérifier les résultats
        self.assertEqual(result["context_analysis"]["context_type"], "commercial")
        self.assertEqual(result["potential_fallacies_count"], 2)
        self.assertEqual(result["contextual_fallacies_count"], 2)
        self.assertEqual(len(result["contextual_fallacies"]), 2)
        self.assertEqual(len(result["fallacy_relations"]), 1)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier que les mocks ont été appelés correctement
        mock_analyze_context.assert_called_once_with(self.test_context)
        mock_identify_fallacies.assert_called_once_with(self.test_text)
        mock_filter_context.assert_called_once()
        mock_analyze_relations.assert_called_once()
        
        # Vérifier que les sophismes ont été stockés pour l'apprentissage
        self.assertEqual(len(self.analyzer.last_analysis_fallacies), 2)

    def test_analyze_context_deeply(self):
        """Teste l'analyse approfondie du contexte."""
        # Tester l'analyse d'un contexte commercial
        result = self.analyzer._analyze_context_deeply("discours commercial pour un produit de santé")
        
        # Vérifier les résultats
        self.assertEqual(result["context_type"], "commercial")
        self.assertIsInstance(result["context_subtypes"], list)
        self.assertIsInstance(result["audience_characteristics"], list)
        self.assertIsInstance(result["formality_level"], str)
        self.assertIsInstance(result["confidence"], float)
        
        # Vérifier que le résultat est mis en cache
        context_key = "discours commercial pour un produit de santé".lower()[:100]
        self.assertIn(context_key, self.analyzer.context_embeddings_cache)
        self.assertEqual(self.analyzer.context_embeddings_cache[context_key], result)
        
        # Tester l'utilisation du cache
        cached_result = self.analyzer._analyze_context_deeply("discours commercial pour un produit de santé")
        self.assertEqual(cached_result, result)

    @patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.EnhancedContextualFallacyAnalyzer._identify_potential_fallacies')
    def test_identify_potential_fallacies_with_nlp(self, mock_identify_potential):
        """Teste l'identification des sophismes potentiels avec NLP."""
        # Configurer le mock
        mock_identify_potential.return_value = [
            {"fallacy_type": "Appel à l'autorité", "confidence": 0.7, "context_text": "Les experts sont unanimes"},
            {"fallacy_type": "Appel à la popularité", "confidence": 0.6, "context_text": "Des millions de personnes l'utilisent déjà"}
        ]
        
        # Appeler la méthode à tester
        result = self.analyzer._identify_potential_fallacies_with_nlp(self.test_text)
        
        # Vérifier les résultats
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(result[1]["fallacy_type"], "Appel à la popularité")
        
        # Vérifier que le mock a été appelé correctement
        mock_identify_potential.assert_called_once_with(self.test_text)

    def test_filter_by_context_semantic(self):
        """Teste le filtrage des sophismes par contexte sémantique."""
        # Données de test
        potential_fallacies = [
            {"fallacy_type": "Appel à l'autorité", "confidence": 0.7, "context_text": "Les experts sont unanimes"},
            {"fallacy_type": "Appel à la popularité", "confidence": 0.6, "context_text": "Des millions de personnes l'utilisent déjà"}
        ]
        context_analysis = {
            "context_type": "commercial",
            "context_subtypes": [],
            "audience_characteristics": [],
            "formality_level": "moyen"
        }
        
        # Appeler la méthode à tester
        result = self.analyzer._filter_by_context_semantic(potential_fallacies, context_analysis)
        
        # Vérifier les résultats
        self.assertEqual(len(result), 2)
        self.assertGreaterEqual(result[0]["confidence"], potential_fallacies[0]["confidence"])
        self.assertIn("contextual_relevance", result[0])
        self.assertIn("context_adjustment", result[0])
        self.assertIn("context_analysis", result[0])

    def test_are_complementary_fallacies(self):
        """Teste la détermination de sophismes complémentaires."""
        # Tester des paires complémentaires
        self.assertTrue(self.analyzer._are_complementary_fallacies("Appel à l'autorité", "Appel à la popularité"))
        self.assertTrue(self.analyzer._are_complementary_fallacies("Faux dilemme", "Appel à l'émotion"))
        self.assertTrue(self.analyzer._are_complementary_fallacies("Pente glissante", "Appel à la peur"))
        self.assertTrue(self.analyzer._are_complementary_fallacies("Homme de paille", "Ad hominem"))
        self.assertTrue(self.analyzer._are_complementary_fallacies("Appel à la tradition", "Appel à l'autorité"))
        
        # Tester des paires non complémentaires
        self.assertFalse(self.analyzer._are_complementary_fallacies("Appel à l'autorité", "Faux dilemme"))
        self.assertFalse(self.analyzer._are_complementary_fallacies("Pente glissante", "Homme de paille"))

    @patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.EnhancedContextualFallacyAnalyzer.analyze_context')
    def test_identify_contextual_fallacies(self, mock_analyze_context):
        """Teste l'identification des sophismes contextuels."""
        # Configurer le mock
        mock_analyze_context.return_value = {
            "contextual_fallacies": [
                {"fallacy_type": "Appel à l'autorité", "confidence": 0.8},
                {"fallacy_type": "Appel à la popularité", "confidence": 0.6},
                {"fallacy_type": "Faux dilemme", "confidence": 0.4}
            ]
        }
        
        # Appeler la méthode à tester
        result = self.analyzer.identify_contextual_fallacies(self.test_text, self.test_context)
        
        # Vérifier les résultats
        self.assertEqual(len(result), 2)  # Seulement les sophismes avec confiance >= 0.5
        self.assertEqual(result[0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(result[1]["fallacy_type"], "Appel à la popularité")
        
        # Vérifier que le mock a été appelé correctement
        mock_analyze_context.assert_called_once_with(self.test_text, self.test_context)

    @patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.EnhancedContextualFallacyAnalyzer._save_learning_data')
    def test_provide_feedback(self, mock_save_learning):
        """Teste la fourniture de feedback pour l'apprentissage continu."""
        # Configurer l'analyseur avec des sophismes identifiés
        self.analyzer.last_analysis_fallacies = {
            "fallacy_1": {"fallacy_type": "Appel à l'autorité", "confidence": 0.7},
            "fallacy_2": {"fallacy_type": "Appel à la popularité", "confidence": 0.6}
        }
        
        # Appeler la méthode à tester avec un feedback positif
        self.analyzer.provide_feedback("fallacy_1", True, "Bon travail")
        
        # Vérifier les résultats
        self.assertEqual(len(self.analyzer.feedback_history), 1)
        self.assertEqual(len(self.analyzer.learning_data["feedback_history"]), 1)
        self.assertIn("Appel à l'autorité", self.analyzer.learning_data["confidence_adjustments"])
        self.assertGreater(self.analyzer.learning_data["confidence_adjustments"]["Appel à l'autorité"], 0)
        
        # Appeler la méthode à tester avec un feedback négatif
        self.analyzer.provide_feedback("fallacy_2", False, "Mauvaise identification")
        
        # Vérifier les résultats
        self.assertEqual(len(self.analyzer.feedback_history), 2)
        self.assertEqual(len(self.analyzer.learning_data["feedback_history"]), 2)
        self.assertIn("Appel à la popularité", self.analyzer.learning_data["confidence_adjustments"])
        self.assertLess(self.analyzer.learning_data["confidence_adjustments"]["Appel à la popularité"], 0)
        
        # Vérifier que la sauvegarde a été appelée
        self.assertEqual(mock_save_learning.call_count, 2)

    @patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.BaseAnalyzer.get_contextual_fallacy_examples')
    @patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.EnhancedContextualFallacyAnalyzer._generate_fallacy_explanation')
    @patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.EnhancedContextualFallacyAnalyzer._generate_correction_suggestion')
    def test_get_contextual_fallacy_examples(self, mock_correction, mock_explanation, mock_base_examples):
        """Teste l'obtention d'exemples enrichis de sophismes contextuels."""
        # Configurer les mocks
        mock_base_examples.return_value = [
            "Les experts disent que ce produit est sûr, donc vous devriez l'acheter.",
            "Ce produit est recommandé par le Dr. Smith, un célèbre dentiste."
        ]
        mock_explanation.side_effect = [
            "Explication pour l'exemple 1",
            "Explication pour l'exemple 2"
        ]
        mock_correction.side_effect = [
            "Suggestion de correction pour l'exemple 1",
            "Suggestion de correction pour l'exemple 2"
        ]
        
        # Appeler la méthode à tester
        result = self.analyzer.get_contextual_fallacy_examples("Appel à l'autorité", "commercial")
        
        # Vérifier les résultats
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["text"], "Les experts disent que ce produit est sûr, donc vous devriez l'acheter.")
        self.assertEqual(result[0]["explanation"], "Explication pour l'exemple 1")
        self.assertEqual(result[0]["correction_suggestion"], "Suggestion de correction pour l'exemple 1")
        self.assertEqual(result[0]["context_type"], "commercial")
        self.assertEqual(result[0]["fallacy_type"], "Appel à l'autorité")
        
        # Vérifier que les mocks ont été appelés correctement
        mock_base_examples.assert_called_once_with("Appel à l'autorité", "commercial")
        self.assertEqual(mock_explanation.call_count, 2)
        self.assertEqual(mock_correction.call_count, 2)

    def test_generate_fallacy_explanation(self):
        """Teste la génération d'explications détaillées pour les sophismes."""
        # Tester des explications spécifiques
        explanation1 = self.analyzer._generate_fallacy_explanation(
            "Appel à l'autorité", 
            "politique", 
            "Le Dr. Smith, un célèbre économiste, soutient cette politique"
        )
        self.assertIn("politique", explanation1)
        self.assertIn("autorité", explanation1.lower())
        
        explanation2 = self.analyzer._generate_fallacy_explanation(
            "Appel à la popularité", 
            "scientifique", 
            "La plupart des gens croient que cette théorie est vraie"
        )
        self.assertIn("scientifique", explanation2)
        self.assertIn("popularité", explanation2.lower())
        
        # Tester une explication générique
        explanation3 = self.analyzer._generate_fallacy_explanation(
            "Faux dilemme", 
            "général", 
            "Soit vous êtes avec nous, soit vous êtes contre nous"
        )
        self.assertIn("Faux dilemme", explanation3)
        self.assertIn("général", explanation3)

    def test_generate_correction_suggestion(self):
        """Teste la génération de suggestions de correction pour les sophismes."""
        # Tester des suggestions spécifiques
        suggestion1 = self.analyzer._generate_correction_suggestion(
            "Appel à l'autorité", 
            "Le Dr. Smith, un célèbre économiste, soutient cette politique"
        )
        self.assertIn("preuves", suggestion1.lower())
        
        suggestion2 = self.analyzer._generate_correction_suggestion(
            "Faux dilemme", 
            "Soit vous êtes avec nous, soit vous êtes contre nous"
        )
        self.assertIn("options", suggestion2.lower())
        
        # Tester une suggestion générique
        suggestion3 = self.analyzer._generate_correction_suggestion(
            "Sophisme inconnu", 
            "Exemple de sophisme inconnu"
        )
        self.assertIn("corriger", suggestion3.lower())


if __name__ == '__main__':
    unittest.main()