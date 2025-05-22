#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module agents.tools.analysis.enhanced.contextual_fallacy_analyzer.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch
import json
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestEnhancedContextualFallacyAnalyzer")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('.'))

# Importer les mocks pour numpy et pandas
from mocks.numpy_mock import *
from mocks.pandas_mock import *

# Patcher numpy et pandas avant d'importer le module à tester
sys.modules['numpy'] = sys.modules.get('numpy')
sys.modules['pandas'] = sys.modules.get('pandas')

# Import des bibliothèques réelles si disponibles, sinon utiliser des mocks
try:
    import torch
    import transformers
    HAS_REAL_LIBS = True
except ImportError:
    HAS_REAL_LIBS = False
    
    # Mock pour torch si non disponible
    class MockTorch:
        """Mock pour torch."""
        def __init__(self):
            pass
        
        @staticmethod
        def tensor(data):
            return data
        
        @staticmethod
        def no_grad():
            class NoGrad:
                def __enter__(self):
                    return None
                def __exit__(self, *args):
                    pass
            return NoGrad()
    
    # Mock pour transformers si non disponible
    class MockTransformers:
        """Mock pour transformers."""
        class AutoTokenizer:
            @staticmethod
            def from_pretrained(model_name):
                tokenizer = MagicMock()
                tokenizer.encode = lambda text, return_tensors: [0, 1, 2, 3]
                tokenizer.decode = lambda tokens: "Texte décodé"
                return tokenizer
        
        class AutoModelForSequenceClassification:
            @staticmethod
            def from_pretrained(model_name):
                model = MagicMock()
                model.forward = lambda input_ids: MagicMock(logits=[[0.1, 0.9]])
                return model
        
        class pipeline:
            def __init__(self, task, model=None):
                self.task = task
                self.model = model
            
            def __call__(self, text):
                if self.task == "sentiment-analysis":
                    return [{"label": "POSITIVE", "score": 0.9}]
                elif self.task == "text-generation":
                    return [{"generated_text": "Texte généré"}]
                elif self.task == "ner":
                    return [{"entity": "B-PER", "word": "Einstein", "score": 0.9}]
                return []
    
    # Patcher torch et transformers si non disponibles
    sys.modules['torch'] = MagicMock(spec=MockTorch)
    sys.modules['transformers'] = MagicMock(spec=MockTransformers)

# Import du module à tester
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer


class TestEnhancedContextualFallacyAnalyzer(unittest.TestCase):
    """Tests unitaires pour l'analyseur contextuel de sophismes amélioré."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Patcher les imports pour utiliser nos mocks seulement si les vraies bibliothèques ne sont pas disponibles
        self.patches = []
        
        if not HAS_REAL_LIBS:
            # Patcher torch
            torch_patch = patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.torch', MockTorch())
            self.patches.append(torch_patch)
            torch_patch.start()
            
            # Patcher transformers
            transformers_patch = patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.transformers', MockTransformers())
            self.patches.append(transformers_patch)
            transformers_patch.start()
            
            # Patcher HAS_TRANSFORMERS
            has_transformers_patch = patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.HAS_TRANSFORMERS', True)
            self.patches.append(has_transformers_patch)
            has_transformers_patch.start()
        
        # Créer l'analyseur contextuel de sophismes amélioré
        # Utiliser un modèle plus léger pour les tests
        self.analyzer = EnhancedContextualFallacyAnalyzer(model_name="distilbert-base-uncased")
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter tous les patchers
        for patcher in self.patches:
            patcher.stop()
    
    def test_initialization(self):
        """Teste l'initialisation de l'analyseur contextuel de sophismes amélioré."""
        # Vérifier que l'analyseur a été correctement initialisé
        self.assertIsNotNone(self.analyzer)
        self.assertIsNotNone(self.analyzer.logger)
        self.assertIsNotNone(self.analyzer.model_name)
        self.assertIsNotNone(self.analyzer.feedback_history)
        self.assertIsNotNone(self.analyzer.context_embeddings_cache)
        self.assertIsNotNone(self.analyzer.last_analysis_fallacies)
        self.assertIsNotNone(self.analyzer.nlp_models)
        self.assertIsNotNone(self.analyzer.learning_data)
    
    def test_analyze_context(self):
        """Teste la méthode analyze_context."""
        # Appeler la méthode analyze_context
        text = "Les experts affirment que ce produit est sûr et efficace."
        context = "Discours commercial pour un produit controversé"
        
        # Patcher les méthodes appelées par analyze_context
        with patch.object(self.analyzer, '_analyze_context_deeply', return_value={
            "context_type": "commercial",
            "context_subtypes": ["publicitaire"],
            "audience_characteristics": ["grand public"],
            "formality_level": "moyen",
            "confidence": 0.8
        }) as mock_analyze_context, \
             patch.object(self.analyzer, '_identify_potential_fallacies_with_nlp', return_value=[
                 {
                     "fallacy_type": "Appel à l'autorité",
                     "keyword": "experts",
                     "context_text": "Les experts affirment que ce produit est sûr et efficace.",
                     "confidence": 0.7,
                     "detection_method": "keyword_matching"
                 }
             ]) as mock_identify_fallacies, \
             patch.object(self.analyzer, '_filter_by_context_semantic', return_value=[
                 {
                     "fallacy_type": "Appel à l'autorité",
                     "keyword": "experts",
                     "context_text": "Les experts affirment que ce produit est sûr et efficace.",
                     "confidence": 0.8,
                     "detection_method": "keyword_matching",
                     "contextual_relevance": "Élevée",
                     "context_adjustment": 0.1
                 }
             ]) as mock_filter_context, \
             patch.object(self.analyzer, '_analyze_fallacy_relations', return_value=[]) as mock_analyze_relations:
            
            # Appeler la méthode analyze_context
            result = self.analyzer.analyze_context(text, context)
            
            # Vérifier que les méthodes ont été appelées
            mock_analyze_context.assert_called_once_with(context)
            mock_identify_fallacies.assert_called_once_with(text)
            mock_filter_context.assert_called_once()
            mock_analyze_relations.assert_called_once()
            
            # Vérifier le résultat
            self.assertIsInstance(result, dict)
            self.assertIn("context_analysis", result)
            self.assertIn("potential_fallacies_count", result)
            self.assertIn("contextual_fallacies_count", result)
            self.assertIn("contextual_fallacies", result)
            self.assertIn("fallacy_relations", result)
            self.assertIn("analysis_timestamp", result)
            
            # Vérifier les valeurs
            self.assertEqual(result["context_analysis"]["context_type"], "commercial")
            self.assertEqual(result["potential_fallacies_count"], 1)
            self.assertEqual(result["contextual_fallacies_count"], 1)
            self.assertEqual(len(result["contextual_fallacies"]), 1)
            self.assertEqual(result["contextual_fallacies"][0]["fallacy_type"], "Appel à l'autorité")
    
    def test_analyze_context_deeply(self):
        """Teste la méthode _analyze_context_deeply."""
        # Appeler la méthode _analyze_context_deeply
        context = "Discours politique lors d'une campagne électorale"
        
        # Patcher les méthodes appelées par _analyze_context_deeply
        with patch.object(self.analyzer, '_determine_context_type', return_value="politique") as mock_determine_context:
            
            # Appeler la méthode _analyze_context_deeply
            result = self.analyzer._analyze_context_deeply(context)
            
            # Vérifier que les méthodes ont été appelées
            mock_determine_context.assert_called_once_with(context)
            
            # Vérifier le résultat
            self.assertIsInstance(result, dict)
            self.assertIn("context_type", result)
            self.assertIn("context_subtypes", result)
            self.assertIn("audience_characteristics", result)
            self.assertIn("formality_level", result)
            self.assertIn("confidence", result)
            
            # Vérifier les valeurs
            self.assertEqual(result["context_type"], "politique")
            self.assertIsInstance(result["context_subtypes"], list)
            self.assertIsInstance(result["audience_characteristics"], list)
            self.assertIn(result["formality_level"], ["élevé", "moyen", "faible"])
            self.assertGreaterEqual(result["confidence"], 0.0)
            self.assertLessEqual(result["confidence"], 1.0)
    
    def test_identify_potential_fallacies_with_nlp(self):
        """Teste la méthode _identify_potential_fallacies_with_nlp."""
        # Appeler la méthode _identify_potential_fallacies_with_nlp
        text = "Les experts affirment que ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà."
        
        # Patcher les méthodes appelées par _identify_potential_fallacies_with_nlp
        with patch.object(self.analyzer, '_identify_potential_fallacies', return_value=[
            {
                "fallacy_type": "Appel à l'autorité",
                "keyword": "experts",
                "context_text": "Les experts affirment que ce produit est sûr et efficace.",
                "confidence": 0.7,
                "detection_method": "keyword_matching"
            },
            {
                "fallacy_type": "Appel à la popularité",
                "keyword": "millions",
                "context_text": "Des millions de personnes l'utilisent déjà.",
                "confidence": 0.6,
                "detection_method": "keyword_matching"
            }
        ]) as mock_identify_fallacies:
            
            # Appeler la méthode _identify_potential_fallacies_with_nlp
            result = self.analyzer._identify_potential_fallacies_with_nlp(text)
            
            # Vérifier que les méthodes ont été appelées
            mock_identify_fallacies.assert_called_once_with(text)
            
            # Vérifier le résultat
            self.assertIsInstance(result, list)
            self.assertGreaterEqual(len(result), 1)
            
            # Vérifier les valeurs
            self.assertEqual(result[0]["fallacy_type"], "Appel à l'autorité")
            self.assertEqual(result[0]["keyword"], "experts")
            self.assertEqual(result[0]["detection_method"], "keyword_matching")
            
            # Vérifier qu'un appel à la popularité a été détecté
            popularity_fallacy = next((f for f in result if f["fallacy_type"] == "Appel à la popularité"), None)
            self.assertIsNotNone(popularity_fallacy)
            self.assertIn("millions", popularity_fallacy["keyword"].lower())
    
    def test_filter_by_context_semantic(self):
        """Teste la méthode _filter_by_context_semantic."""
        # Créer des sophismes potentiels
        potential_fallacies = [
            {
                "fallacy_type": "Appel à l'autorité",
                "keyword": "experts",
                "context_text": "Les experts affirment que ce produit est sûr et efficace.",
                "confidence": 0.7,
                "detection_method": "keyword_matching"
            },
            {
                "fallacy_type": "Appel à la popularité",
                "keyword": "millions",
                "context_text": "Des millions de personnes l'utilisent déjà.",
                "confidence": 0.6,
                "detection_method": "keyword_matching"
            }
        ]
        
        # Créer une analyse de contexte
        context_analysis = {
            "context_type": "commercial",
            "context_subtypes": ["publicitaire"],
            "audience_characteristics": ["grand public"],
            "formality_level": "moyen",
            "confidence": 0.8
        }
        
        # Appeler la méthode _filter_by_context_semantic
        result = self.analyzer._filter_by_context_semantic(potential_fallacies, context_analysis)
        
        # Vérifier le résultat
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        
        # Vérifier les valeurs - sans se soucier de l'ordre
        fallacy_types = [f["fallacy_type"] for f in result]
        self.assertIn("Appel à l'autorité", fallacy_types)
        self.assertIn("Appel à la popularité", fallacy_types)
        
        # Vérifier les ajustements de contexte
        self.assertIn("contextual_relevance", result[0])
        self.assertIn("context_adjustment", result[0])
        self.assertIn("context_analysis", result[0])
        
        # Vérifier que les sophismes sont triés par confiance décroissante
        self.assertGreaterEqual(result[0]["confidence"], result[1]["confidence"])
    
    def test_analyze_fallacy_relations(self):
        """Teste la méthode _analyze_fallacy_relations."""
        # Créer des sophismes
        fallacies = [
            {
                "fallacy_type": "Appel à l'autorité",
                "keyword": "experts",
                "context_text": "Les experts affirment que ce produit est sûr et efficace.",
                "confidence": 0.7,
                "detection_method": "keyword_matching"
            },
            {
                "fallacy_type": "Appel à la popularité",
                "keyword": "millions",
                "context_text": "Des millions de personnes l'utilisent déjà.",
                "confidence": 0.6,
                "detection_method": "keyword_matching"
            },
            {
                "fallacy_type": "Appel à la peur",
                "keyword": "risque",
                "context_text": "Si vous n'utilisez pas ce produit, vous risquez de souffrir.",
                "confidence": 0.8,
                "detection_method": "keyword_matching"
            }
        ]
        
        # Appeler la méthode _analyze_fallacy_relations
        result = self.analyzer._analyze_fallacy_relations(fallacies)
        
        # Vérifier le résultat
        self.assertIsInstance(result, list)
        
        # Vérifier les relations
        if len(result) > 0:
            relation = result[0]
            self.assertIn("relation_type", relation)
            self.assertIn("fallacy1_type", relation)
            self.assertIn("fallacy2_type", relation)
            self.assertIn("strength", relation)
    
    def test_are_complementary_fallacies(self):
        """Teste la méthode _are_complementary_fallacies."""
        # Tester des paires de sophismes complémentaires
        self.assertTrue(self.analyzer._are_complementary_fallacies("Appel à l'autorité", "Appel à la popularité"))
        self.assertTrue(self.analyzer._are_complementary_fallacies("Faux dilemme", "Appel à l'émotion"))
        self.assertTrue(self.analyzer._are_complementary_fallacies("Pente glissante", "Appel à la peur"))
        self.assertTrue(self.analyzer._are_complementary_fallacies("Homme de paille", "Ad hominem"))
        self.assertTrue(self.analyzer._are_complementary_fallacies("Appel à la tradition", "Appel à l'autorité"))
        
        # Tester des paires de sophismes non complémentaires
        self.assertFalse(self.analyzer._are_complementary_fallacies("Appel à l'autorité", "Pente glissante"))
        self.assertFalse(self.analyzer._are_complementary_fallacies("Faux dilemme", "Ad hominem"))
    
    def test_identify_contextual_fallacies(self):
        """Teste la méthode identify_contextual_fallacies."""
        # Appeler la méthode identify_contextual_fallacies
        argument = "Les experts affirment que ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà."
        context = "Discours commercial pour un produit controversé"
        
        # Patcher la méthode analyze_context
        with patch.object(self.analyzer, 'analyze_context', return_value={
            "context_analysis": {
                "context_type": "commercial",
                "context_subtypes": ["publicitaire"],
                "audience_characteristics": ["grand public"],
                "formality_level": "moyen",
                "confidence": 0.8
            },
            "potential_fallacies_count": 2,
            "contextual_fallacies_count": 2,
            "contextual_fallacies": [
                {
                    "fallacy_type": "Appel à l'autorité",
                    "keyword": "experts",
                    "context_text": "Les experts affirment que ce produit est sûr et efficace.",
                    "confidence": 0.7,
                    "detection_method": "keyword_matching",
                    "contextual_relevance": "Élevée",
                    "context_adjustment": 0.1
                },
                {
                    "fallacy_type": "Appel à la popularité",
                    "keyword": "millions",
                    "context_text": "Des millions de personnes l'utilisent déjà.",
                    "confidence": 0.6,
                    "detection_method": "keyword_matching",
                    "contextual_relevance": "Élevée",
                    "context_adjustment": 0.1
                }
            ],
            "fallacy_relations": [],
            "analysis_timestamp": "2025-05-22T00:00:00.000000"
        }) as mock_analyze_context:
            
            # Appeler la méthode identify_contextual_fallacies
            result = self.analyzer.identify_contextual_fallacies(argument, context)
            
            # Vérifier que les méthodes ont été appelées
            mock_analyze_context.assert_called_once_with(argument, context)
            
            # Vérifier le résultat
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)
            
            # Vérifier les valeurs
            self.assertEqual(result[0]["fallacy_type"], "Appel à l'autorité")
            self.assertEqual(result[1]["fallacy_type"], "Appel à la popularité")
    
    def test_provide_feedback(self):
        """Teste la méthode provide_feedback."""
        # Configurer l'état pour le test
        self.analyzer.last_analysis_fallacies = {
            "fallacy_1": {
                "fallacy_type": "Appel à l'autorité",
                "keyword": "experts",
                "context_text": "Les experts affirment que ce produit est sûr et efficace.",
                "confidence": 0.7,
                "detection_method": "keyword_matching"
            }
        }
        
        # Réinitialiser l'historique de feedback et les ajustements de confiance
        self.analyzer.feedback_history = []
        self.analyzer.learning_data["feedback_history"] = []
        self.analyzer.learning_data["confidence_adjustments"] = {}
        
        # Patcher la méthode _save_learning_data
        with patch.object(self.analyzer, '_save_learning_data') as mock_save_learning_data:
            
            # Appeler la méthode provide_feedback
            self.analyzer.provide_feedback("fallacy_1", True, "Bonne détection")
            
            # Vérifier que les méthodes ont été appelées
            mock_save_learning_data.assert_called_once()
            
            # Vérifier que le feedback a été enregistré
            self.assertEqual(len(self.analyzer.feedback_history), 1)
            self.assertEqual(len(self.analyzer.learning_data["feedback_history"]), 1)
            
            # Vérifier les valeurs
            feedback = self.analyzer.feedback_history[0]
            self.assertEqual(feedback["fallacy_id"], "fallacy_1")
            self.assertTrue(feedback["is_correct"])
            self.assertEqual(feedback["feedback_text"], "Bonne détection")
            
            # Vérifier que les ajustements de confiance ont été mis à jour
            self.assertIn("Appel à l'autorité", self.analyzer.learning_data["confidence_adjustments"])
            self.assertEqual(self.analyzer.learning_data["confidence_adjustments"]["Appel à l'autorité"], 0.05)
    
    def test_get_contextual_fallacy_examples(self):
        """Teste la méthode get_contextual_fallacy_examples."""
        # Patcher la méthode parent get_contextual_fallacy_examples
        with patch.object(self.analyzer.__class__.__bases__[0], 'get_contextual_fallacy_examples', return_value=[
            "Les experts affirment que ce produit est sûr, donc il l'est forcément.",
            "Le Dr. Smith recommande ce médicament, donc il doit être efficace."
        ]) as mock_parent_method, \
             patch.object(self.analyzer, '_generate_fallacy_explanation', return_value="Explication du sophisme") as mock_generate_explanation, \
             patch.object(self.analyzer, '_generate_correction_suggestion', return_value="Suggestion de correction") as mock_generate_correction:
            
            # Appeler la méthode get_contextual_fallacy_examples
            result = self.analyzer.get_contextual_fallacy_examples("Appel à l'autorité", "commercial")
            
            # Vérifier que les méthodes ont été appelées
            mock_parent_method.assert_called_once_with("Appel à l'autorité", "commercial")
            self.assertEqual(mock_generate_explanation.call_count, 2)
            self.assertEqual(mock_generate_correction.call_count, 2)
            
            # Vérifier le résultat
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)
            
            # Vérifier les valeurs
            self.assertIsInstance(result[0], dict)
            self.assertIn("text", result[0])
            self.assertIn("explanation", result[0])
            self.assertIn("correction_suggestion", result[0])
            self.assertIn("context_type", result[0])
            self.assertIn("fallacy_type", result[0])
            
            self.assertEqual(result[0]["text"], "Les experts affirment que ce produit est sûr, donc il l'est forcément.")
            self.assertEqual(result[0]["explanation"], "Explication du sophisme")
            self.assertEqual(result[0]["correction_suggestion"], "Suggestion de correction")
            self.assertEqual(result[0]["context_type"], "commercial")
            self.assertEqual(result[0]["fallacy_type"], "Appel à l'autorité")


if __name__ == "__main__":
    unittest.main()