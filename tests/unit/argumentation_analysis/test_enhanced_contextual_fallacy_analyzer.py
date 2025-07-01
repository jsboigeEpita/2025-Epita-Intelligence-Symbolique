# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module EnhancedContextualFallacyAnalyzer.
"""

import unittest
from unittest.mock import MagicMock, patch

import json
import os
from pathlib import Path
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer, BaseAnalyzer


class TestEnhancedContextualFallacyAnalyzer(unittest.TestCase):
    """Tests pour la classe EnhancedContextualFallacyAnalyzer."""

    @classmethod
    def setUpClass(cls):
        """Initialisation unique pour toute la classe de test."""
        # Patcher les dépendances externes avant même l'instanciation
        cls.patcher_transformers = patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.HAS_TRANSFORMERS', True)
        cls.mock_has_transformers = cls.patcher_transformers.start()

        # Mocker les modèles NLP pour éviter les téléchargements et les chargements longs et coûteux
        cls.patcher_pipeline = patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.pipeline', return_value=MagicMock())
        cls.mock_pipeline = cls.patcher_pipeline.start()
        
        # Créer une instance unique de l'analyseur pour tous les tests
        cls.analyzer = EnhancedContextualFallacyAnalyzer()

    @classmethod
    def tearDownClass(cls):
        """Nettoyage unique après tous les tests de la classe."""
        cls.patcher_transformers.stop()
        cls.patcher_pipeline.stop()

    def setUp(self):
        """Réinitialisation avant chaque test."""
        # Réinitialiser l'état de l'analyseur partagé
        self.analyzer.feedback_history = []
        self.analyzer.context_embeddings_cache = {}
        self.analyzer.last_analysis_fallacies = {}
        self.analyzer.learning_data = self.analyzer._load_learning_data() # Recharger les données vierges

        # Données de test
        self.test_text = "Les experts sont unanimes : ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà."
        self.test_context = "commercial"

    def tearDown(self):
        """Pas de nettoyage individuel nécessaire car géré par setUp."""
        pass

    def test_init(self):
        """Teste l'initialisation de l'analyseur."""
        # Vérifier que l'analyseur est correctement initialisé
        self.assertIsNotNone(self.analyzer)
        self.assertEqual(self.analyzer.model_name, "distilbert-base-uncased-finetuned-sst-2-english")
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

    def test_analyze_context(self):
        """Teste l'analyse du contexte avec l'instance partagée."""
        # Simuler un retour des modèles NLP mockés (même si désactivés globalement)
        self.analyzer.nlp_models = {
            'sentiment': MagicMock(return_value=[{'label': 'POSITIVE', 'score': 0.9}]),
            'ner': MagicMock(return_value=[])
        }

        result = self.analyzer.analyze_context(self.test_text, self.test_context)
        
        self.assertIn("context_analysis", result)
        self.assertIn("contextual_fallacies", result)
        self.assertEqual(result['context_analysis']['context_type'], 'commercial')
        self.assertIsInstance(result['contextual_fallacies'], list)

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

    def test_identify_potential_fallacies_with_nlp(self):
        """Teste l'identification des sophismes potentiels avec NLP en mode dégradé."""
        # Les modèles NLP étant désactivés, cette méthode doit se replier sur la méthode de base.
        expected_result = [{"fallacy_type": "Appel à l'autorité"}]
        with patch.object(self.analyzer, '_identify_potential_fallacies', return_value=expected_result) as mock_base_call:
            result = self.analyzer._identify_potential_fallacies_with_nlp(self.test_text)
            mock_base_call.assert_called_once_with(self.test_text)
            self.assertEqual(result, expected_result)

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

    def test_identify_contextual_fallacies(self):
        """Teste l'identification des sophismes contextuels en mode dégradé."""
        # Mocker l'appel à analyze_context pour retourner un résultat contrôlé
        mock_analysis_result = {
            "contextual_fallacies": [
                {"fallacy_type": "Appel à l'autorité", "confidence": 0.8},
                {"fallacy_type": "Appel à la popularité", "confidence": 0.4}
            ]
        }
        with patch.object(self.analyzer, 'analyze_context', return_value=mock_analysis_result):
            result = self.analyzer.identify_contextual_fallacies("some text", "some context")
            # Le filtrage se fait à 0.5 de confiance.
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['fallacy_type'], "Appel à l'autorité")

    def test_provide_feedback(self):
        """Teste la fourniture de feedback pour l'apprentissage continu."""
        fallacy_id = "fallacy_0"
        self.analyzer.last_analysis_fallacies = {
            fallacy_id: {"fallacy_type": "Appel à l'autorité"}
        }
        
        # Simuler un feedback positif
        self.analyzer.provide_feedback(fallacy_id, True, "Bonne détection.")
        
        # Vérifier que le feedback a été enregistré
        self.assertEqual(len(self.analyzer.feedback_history), 1)
        self.assertEqual(self.analyzer.feedback_history[0]["fallacy_id"], fallacy_id)
        
        # Vérifier que l'ajustement de confiance a été modifié
        self.assertIn("Appel à l'autorité", self.analyzer.learning_data["confidence_adjustments"])
        self.assertGreater(self.analyzer.learning_data["confidence_adjustments"]["Appel à l'autorité"], 0)

    def test_get_contextual_fallacy_examples(self):
        """Teste l'obtention d'exemples enrichis de sophismes contextuels."""
        # Mocker la méthode de base de laquelle elle hérite
        base_examples = ["Les experts disent que c'est bien."]
        # La bonne façon de patcher super() est de patcher la méthode sur la classe BaseAnalyzer
        with patch.object(BaseAnalyzer, 'get_contextual_fallacy_examples', return_value=base_examples):
            enriched_examples = self.analyzer.get_contextual_fallacy_examples("Appel à l'autorité", "commercial")
            
            self.assertEqual(len(enriched_examples), 1)
            example = enriched_examples[0]
            self.assertIn("text", example)
            self.assertIn("explanation", example)
            self.assertIn("correction_suggestion", example)
            self.assertEqual(example["text"], base_examples[0])

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
        self.assertIn("populaire", explanation2.lower()) # Corrigé: "popularité" en "populaire"
        
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