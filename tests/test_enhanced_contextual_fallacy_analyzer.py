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
import pytest # Ajout de l'import pytest

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestEnhancedContextualFallacyAnalyzer")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
# sys.path.append(os.path.abspath('..')) # Géré par conftest.py
# sys.path.append(os.path.abspath('.'))  # Géré par conftest.py

# Importer les mocks pour numpy et pandas
# Le répertoire tests/mocks est ajouté à sys.path par conftest.py
# from numpy_mock import * # Commenté pour tester
# from pandas_mock import * # Commenté pour tester si cela résout l'erreur pandas.__spec__

# Patcher numpy et pandas avant d'importer le module à tester
# Redondant si conftest.py gère bien sys.modules
# sys.modules['numpy'] = sys.modules.get('numpy')
# sys.modules['pandas'] = sys.modules.get('pandas')

# Import des bibliothèques réelles si disponibles, sinon utiliser des mocks
try:
    import torch
    import transformers
    HAS_REAL_LIBS = True
except ImportError:
    HAS_REAL_LIBS = False
    
    class MockTorch:
        def __init__(self): pass
        @staticmethod
        def tensor(data): return data
        @staticmethod
        def no_grad():
            class NoGrad:
                def __enter__(self): return None
                def __exit__(self, *args): pass
            return NoGrad()
    
    class MockTransformers:
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
                if self.task == "sentiment-analysis": return [{"label": "POSITIVE", "score": 0.9}]
                elif self.task == "text-generation": return [{"generated_text": "Texte généré"}]
                elif self.task == "ner": return [{"entity": "B-PER", "word": "Einstein", "score": 0.9}]
                return []
    
    # Mocker torch et transformers si non disponibles (conftest.py devrait aussi les gérer)
    if 'torch' not in sys.modules: # Vérifier avant de potentiellement écraser un mock de conftest
        sys.modules['torch'] = MagicMock(spec=MockTorch)
    if 'transformers' not in sys.modules:
        sys.modules['transformers'] = MagicMock(spec=MockTransformers)

# Import du module à tester
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer


@pytest.mark.use_real_numpy
@pytest.mark.xfail(reason="NumPy 2.x _NoValueType issue with ndarray.max/min, see numpy/numpy#27857 and pandas-dev/pandas#60421")
class TestEnhancedContextualFallacyAnalyzer(unittest.TestCase):
    """Tests unitaires pour l'analyseur contextuel de sophismes amélioré."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.patches = []
        
        # Importer percentile depuis le mock numpy pour le patch
        try:
            from tests.mocks.numpy_mock import percentile as numpy_mock_percentile
        except ImportError:
            logger.error("Impossible d'importer percentile depuis tests.mocks.numpy_mock pour le patch.")
            numpy_mock_percentile = MagicMock()

        # Vérifier si numpy est mocké (par exemple, par conftest.py)
        # Une façon simple est de vérifier si la version est celle du mock.
        numpy_module = sys.modules.get('numpy')
        is_numpy_mocked = hasattr(numpy_module, '__version__') and numpy_module.__version__ == '1.24.3' # Version du mock dans conftest

        if is_numpy_mocked:
            # Patcher numpy.percentile si numpy est mocké et que percentile n'est pas déjà là ou est incorrect
            if not hasattr(numpy_module, 'percentile') or getattr(numpy_module, 'percentile') is not numpy_mock_percentile:
                percentile_patch = patch('numpy.percentile', numpy_mock_percentile)
                self.patches.append(percentile_patch)
                percentile_patch.start()
                logger.info("Patch appliqué pour numpy.percentile dans setUp.")

        # Si les vraies bibliothèques ne sont pas là, ET que les mocks de conftest n'ont pas suffi,
        # on pourrait avoir besoin de patcher spécifiquement pour ce module.
        # Cependant, conftest.py devrait rendre cela moins nécessaire.
        if not HAS_REAL_LIBS:
            if 'torch' not in sys.modules or not isinstance(sys.modules['torch'], MockTorch):
                 torch_patch = patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.torch', MagicMock(spec=MockTorch))
                 self.patches.append(torch_patch)
                 torch_patch.start()
            
            if 'transformers' not in sys.modules or not isinstance(sys.modules['transformers'], MockTransformers):
                 transformers_patch = patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.transformers', MagicMock(spec=MockTransformers))
                 self.patches.append(transformers_patch)
                 transformers_patch.start()
            
            # Assurer que HAS_TRANSFORMERS est True pour que le code interne s'exécute
            has_transformers_patch = patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.HAS_TRANSFORMERS', True)
            self.patches.append(has_transformers_patch)
            has_transformers_patch.start()
        
        self.analyzer = EnhancedContextualFallacyAnalyzer(model_name="distilbert-base-uncased") # Modèle léger
    
    def tearDown(self):
        for patcher in self.patches:
            patcher.stop()
    
    def test_initialization(self):
        self.assertIsNotNone(self.analyzer)
        self.assertIsNotNone(self.analyzer.logger)
        self.assertIsNotNone(self.analyzer.model_name)
        self.assertIsNotNone(self.analyzer.feedback_history)
        self.assertIsNotNone(self.analyzer.context_embeddings_cache)
        self.assertIsNotNone(self.analyzer.last_analysis_fallacies)
        self.assertIsNotNone(self.analyzer.nlp_models)
        self.assertIsNotNone(self.analyzer.learning_data)
    
    def test_analyze_context(self):
        text = "Les experts affirment que ce produit est sûr et efficace."
        context = "Discours commercial pour un produit controversé"
        
        with patch.object(self.analyzer, '_analyze_context_deeply', return_value={
            "context_type": "commercial", "context_subtypes": ["publicitaire"],
            "audience_characteristics": ["grand public"], "formality_level": "moyen", "confidence": 0.8
        }) as mock_analyze_context, \
             patch.object(self.analyzer, '_identify_potential_fallacies_with_nlp', return_value=[
                 {"fallacy_type": "Appel à l'autorité", "keyword": "experts", 
                  "context_text": text, "confidence": 0.7, "detection_method": "keyword_matching"}
             ]) as mock_identify_fallacies, \
             patch.object(self.analyzer, '_filter_by_context_semantic', return_value=[
                 {"fallacy_type": "Appel à l'autorité", "keyword": "experts", 
                  "context_text": text, "confidence": 0.8, "detection_method": "keyword_matching",
                  "contextual_relevance": "Élevée", "context_adjustment": 0.1}
             ]) as mock_filter_context, \
             patch.object(self.analyzer, '_analyze_fallacy_relations', return_value=[]) as mock_analyze_relations:
            
            result = self.analyzer.analyze_context(text, context)
            
            mock_analyze_context.assert_called_once_with(context)
            mock_identify_fallacies.assert_called_once_with(text)
            mock_filter_context.assert_called_once()
            mock_analyze_relations.assert_called_once()
            
            self.assertIsInstance(result, dict)
            self.assertIn("context_analysis", result)
            self.assertEqual(result["context_analysis"]["context_type"], "commercial")
            self.assertEqual(result["potential_fallacies_count"], 1)
            self.assertEqual(result["contextual_fallacies_count"], 1)
            self.assertEqual(len(result["contextual_fallacies"]), 1)
            self.assertEqual(result["contextual_fallacies"][0]["fallacy_type"], "Appel à l'autorité")
    
    def test_analyze_context_deeply(self):
        context = "Discours politique lors d'une campagne électorale"
        with patch.object(self.analyzer, '_determine_context_type', return_value="politique") as mock_determine_context:
            result = self.analyzer._analyze_context_deeply(context)
            mock_determine_context.assert_called_once_with(context)
            self.assertIsInstance(result, dict)
            self.assertEqual(result["context_type"], "politique")
            self.assertIn(result["formality_level"], ["élevé", "moyen", "faible"])
    
    def test_identify_potential_fallacies_with_nlp(self):
        text = "Les experts affirment que ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà."
        with patch.object(self.analyzer, '_identify_potential_fallacies', return_value=[
            {"fallacy_type": "Appel à l'autorité", "keyword": "experts", "context_text": text[:50], "confidence": 0.7, "detection_method": "keyword_matching"},
            {"fallacy_type": "Appel à la popularité", "keyword": "millions", "context_text": text[50:], "confidence": 0.6, "detection_method": "keyword_matching"}
        ]) as mock_identify_fallacies:
            result = self.analyzer._identify_potential_fallacies_with_nlp(text)
            mock_identify_fallacies.assert_called_once_with(text)
            self.assertIsInstance(result, list)
            self.assertGreaterEqual(len(result), 1)
            self.assertEqual(result[0]["fallacy_type"], "Appel à l'autorité")
            popularity_fallacy = next((f for f in result if f["fallacy_type"] == "Appel à la popularité"), None)
            self.assertIsNotNone(popularity_fallacy)
    
    def test_filter_by_context_semantic(self):
        potential_fallacies = [
            {"fallacy_type": "Appel à l'autorité", "keyword": "experts", "context_text": "Les experts...", "confidence": 0.7, "detection_method": "keyword_matching"},
            {"fallacy_type": "Appel à la popularité", "keyword": "millions", "context_text": "Des millions...", "confidence": 0.6, "detection_method": "keyword_matching"}
        ]
        context_analysis = {
            "context_type": "commercial",
            "context_subtypes": ["publicitaire"],
            "audience_characteristics": ["généraliste"],
            "formality_level": "informel",
            "confidence": 0.8
        }
        result = self.analyzer._filter_by_context_semantic(potential_fallacies, context_analysis)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        fallacy_types = [f["fallacy_type"] for f in result]
        self.assertIn("Appel à l'autorité", fallacy_types)
        self.assertIn("Appel à la popularité", fallacy_types)
        self.assertIn("contextual_relevance", result[0])
        self.assertGreaterEqual(result[0]["confidence"], result[1]["confidence"])
    
    def test_analyze_fallacy_relations(self):
        fallacies = [
            {"fallacy_type": "Appel à l'autorité", "confidence": 0.7, "context_text": "Les experts affirment..."},
            {"fallacy_type": "Appel à la popularité", "confidence": 0.6, "context_text": "Des millions de personnes..."},
            {"fallacy_type": "Appel à la peur", "confidence": 0.8, "context_text": "Si nous ne faisons rien..."}
        ]
        result = self.analyzer._analyze_fallacy_relations(fallacies)
        self.assertIsInstance(result, list)
        if len(result) > 0:
            relation = result[0]
            self.assertIn("relation_type", relation)
            self.assertIn("strength", relation)
    
    def test_are_complementary_fallacies(self):
        self.assertTrue(self.analyzer._are_complementary_fallacies("Appel à l'autorité", "Appel à la popularité"))
        self.assertFalse(self.analyzer._are_complementary_fallacies("Appel à l'autorité", "Pente glissante"))
    
    def test_identify_contextual_fallacies(self):
        argument = "Les experts affirment que ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà."
        context = "Discours commercial pour un produit controversé"
        mock_analysis_result = {
            "context_analysis": {"context_type": "commercial", "confidence": 0.8},
            "potential_fallacies_count": 2, "contextual_fallacies_count": 2,
            "contextual_fallacies": [
                {"fallacy_type": "Appel à l'autorité", "confidence": 0.7},
                {"fallacy_type": "Appel à la popularité", "confidence": 0.6}
            ], "fallacy_relations": [], "analysis_timestamp": "..."
        }
        with patch.object(self.analyzer, 'analyze_context', return_value=mock_analysis_result) as mock_analyze_context:
            result = self.analyzer.identify_contextual_fallacies(argument, context)
            mock_analyze_context.assert_called_once_with(argument, context)
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["fallacy_type"], "Appel à l'autorité")
    
    def test_provide_feedback(self):
        self.analyzer.last_analysis_fallacies = {
            "fallacy_1": {"fallacy_type": "Appel à l'autorité", "confidence": 0.7}
        }
        self.analyzer.feedback_history = []
        self.analyzer.learning_data["feedback_history"] = []
        self.analyzer.learning_data["confidence_adjustments"] = {}
        with patch.object(self.analyzer, '_save_learning_data') as mock_save:
            self.analyzer.provide_feedback("fallacy_1", True, "Bonne détection")
            mock_save.assert_called_once()
            self.assertEqual(len(self.analyzer.feedback_history), 1)
            feedback = self.analyzer.feedback_history[0]
            self.assertEqual(feedback["fallacy_id"], "fallacy_1")
            self.assertTrue(feedback["is_correct"])
            self.assertIn("Appel à l'autorité", self.analyzer.learning_data["confidence_adjustments"])
    
    def test_get_contextual_fallacy_examples(self):
        with patch.object(self.analyzer.__class__.__bases__[0], 'get_contextual_fallacy_examples', return_value=[
            "Exemple 1.", "Exemple 2."
        ]) as mock_parent, \
             patch.object(self.analyzer, '_generate_fallacy_explanation', return_value="Expl.") as mock_expl, \
             patch.object(self.analyzer, '_generate_correction_suggestion', return_value="Corr.") as mock_corr:
            
            result = self.analyzer.get_contextual_fallacy_examples("Appel à l'autorité", "commercial")
            
            mock_parent.assert_called_once_with("Appel à l'autorité", "commercial")
            self.assertEqual(mock_expl.call_count, 2)
            self.assertEqual(mock_corr.call_count, 2)
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["explanation"], "Expl.")

if __name__ == "__main__":
    unittest.main()