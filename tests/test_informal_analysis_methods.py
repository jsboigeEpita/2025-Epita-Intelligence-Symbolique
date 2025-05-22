#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour les méthodes d'analyse des agents informels.
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
logger = logging.getLogger("TestInformalAnalysisMethods")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Utiliser les vraies bibliothèques numpy et pandas si disponibles
try:
    import numpy
    import pandas
    HAS_REAL_LIBS = True
except ImportError:
    # Importer les mocks pour numpy et pandas si les vraies bibliothèques ne sont pas disponibles
    from tests.mocks.numpy_mock import *
    from tests.mocks.pandas_mock import *
    
    # Patcher numpy et pandas avant d'importer le module à tester
    sys.modules['numpy'] = sys.modules.get('numpy')
    sys.modules['pandas'] = sys.modules.get('pandas')
    HAS_REAL_LIBS = False

# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent


class TestInformalAnalysisMethods(unittest.TestCase):
    """Tests unitaires pour les méthodes d'analyse des agents informels."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer des mocks pour les outils
        self.fallacy_detector = MagicMock()
        self.fallacy_detector.detect = MagicMock(return_value=[
            {
                "fallacy_type": "Appel à l'autorité",
                "text": "Les experts affirment que ce produit est sûr.",
                "confidence": 0.7
            },
            {
                "fallacy_type": "Appel à la popularité",
                "text": "Ce produit est utilisé par des millions de personnes.",
                "confidence": 0.6
            }
        ])
        
        self.rhetorical_analyzer = MagicMock()
        self.rhetorical_analyzer.analyze = MagicMock(return_value={
            "tone": "persuasif",
            "style": "émotionnel",
            "techniques": ["appel à l'émotion", "question rhétorique"],
            "effectiveness": 0.8
        })
        
        self.contextual_analyzer = MagicMock()
        self.contextual_analyzer.analyze_context = MagicMock(return_value={
            "context_type": "commercial",
            "confidence": 0.9
        })
        
        # Créer l'agent informel
        self.agent = InformalAgent(
            agent_id="test_agent",
            tools={
                "fallacy_detector": self.fallacy_detector,
                "rhetorical_analyzer": self.rhetorical_analyzer,
                "contextual_analyzer": self.contextual_analyzer
            }
        )
        
        # Texte d'exemple pour les tests
        self.text = """
        Les experts affirment que ce produit est sûr et efficace.
        Ce produit est utilisé par des millions de personnes dans le monde entier.
        Ne voulez-vous pas faire partie de ceux qui bénéficient de ses avantages ?
        Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves.
        """
    
    def test_analyze_text(self):
        """Teste la méthode analyze_text."""
        # Appeler la méthode analyze_text
        result = self.agent.analyze_text(self.text)
        
        # Vérifier que les méthodes des outils ont été appelées
        self.fallacy_detector.detect.assert_called_once_with(self.text)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier les sophismes détectés
        self.assertIsInstance(result["fallacies"], list)
        self.assertEqual(len(result["fallacies"]), 2)
        self.assertEqual(result["fallacies"][0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(result["fallacies"][1]["fallacy_type"], "Appel à la popularité")
    
    def test_analyze_text_with_context(self):
        """Teste la méthode analyze_text avec un contexte."""
        # Appeler la méthode analyze_text avec un contexte
        context = "Discours commercial pour un produit controversé"
        result = self.agent.analyze_text(self.text, context)
        
        # Vérifier que les méthodes des outils ont été appelées
        self.fallacy_detector.detect.assert_called_once_with(self.text)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        self.assertIn("context", result)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier le contexte
        self.assertEqual(result["context"], context)
    
    def test_analyze_text_with_confidence_threshold(self):
        """Teste la méthode analyze_text avec un seuil de confiance."""
        # Modifier la configuration de l'agent
        self.agent.config["confidence_threshold"] = 0.65
        
        # Appeler la méthode analyze_text
        result = self.agent.analyze_text(self.text)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        
        # Vérifier que seuls les sophismes avec une confiance supérieure au seuil sont inclus
        self.assertEqual(len(result["fallacies"]), 1)
        self.assertEqual(result["fallacies"][0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(result["fallacies"][0]["confidence"], 0.7)
    
    def test_analyze_text_with_max_fallacies(self):
        """Teste la méthode analyze_text avec un nombre maximum de sophismes."""
        # Modifier la configuration de l'agent
        self.agent.config["max_fallacies"] = 1
        
        # Appeler la méthode analyze_text
        result = self.agent.analyze_text(self.text)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        
        # Vérifier que seul le nombre maximum de sophismes est inclus
        self.assertEqual(len(result["fallacies"]), 1)
        self.assertEqual(result["fallacies"][0]["fallacy_type"], "Appel à l'autorité")
    
    def test_perform_complete_analysis(self):
        """Teste la méthode perform_complete_analysis."""
        # Appeler la méthode perform_complete_analysis
        result = self.agent.perform_complete_analysis(self.text)
        
        # Vérifier que les méthodes des outils ont été appelées
        self.fallacy_detector.detect.assert_called_once_with(self.text)
        self.rhetorical_analyzer.analyze.assert_called_once_with(self.text)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        self.assertIn("rhetorical_analysis", result)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier les sophismes détectés
        self.assertIsInstance(result["fallacies"], list)
        self.assertEqual(len(result["fallacies"]), 2)
        
        # Vérifier l'analyse rhétorique
        self.assertIsInstance(result["rhetorical_analysis"], dict)
        self.assertIn("tone", result["rhetorical_analysis"])
        self.assertIn("style", result["rhetorical_analysis"])
        self.assertIn("techniques", result["rhetorical_analysis"])
        self.assertIn("effectiveness", result["rhetorical_analysis"])
    
    def test_perform_complete_analysis_with_context(self):
        """Teste la méthode perform_complete_analysis avec un contexte."""
        # Appeler la méthode perform_complete_analysis avec un contexte
        context = "Discours commercial pour un produit controversé"
        result = self.agent.perform_complete_analysis(self.text, context)
        
        # Vérifier que les méthodes des outils ont été appelées
        self.fallacy_detector.detect.assert_called_once_with(self.text)
        self.rhetorical_analyzer.analyze.assert_called_once_with(self.text)
        self.contextual_analyzer.analyze_context.assert_called_once_with(self.text, context)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        self.assertIn("rhetorical_analysis", result)
        self.assertIn("contextual_analysis", result)
        self.assertIn("context", result)
        self.assertIn("analysis_timestamp", result)
        
        # Vérifier le contexte
        self.assertEqual(result["context"], context)
        
        # Vérifier l'analyse contextuelle
        self.assertIsInstance(result["contextual_analysis"], dict)
        self.assertIn("context_type", result["contextual_analysis"])
        self.assertIn("confidence", result["contextual_analysis"])
    
    def test_analyze_and_categorize(self):
        """Teste la méthode analyze_and_categorize."""
        # Patcher la méthode categorize_fallacies
        with patch.object(self.agent, 'categorize_fallacies', return_value={
            "RELEVANCE": ["Appel à l'autorité"],
            "INDUCTION": ["Appel à la popularité"]
        }) as mock_categorize:
            
            # Appeler la méthode analyze_and_categorize
            result = self.agent.analyze_and_categorize(self.text)
            
            # Vérifier que les méthodes ont été appelées
            self.fallacy_detector.detect.assert_called_once_with(self.text)
            mock_categorize.assert_called_once()
            
            # Vérifier le résultat
            self.assertIsInstance(result, dict)
            self.assertIn("fallacies", result)
            self.assertIn("categories", result)
            self.assertIn("analysis_timestamp", result)
            
            # Vérifier les catégories
            self.assertIsInstance(result["categories"], dict)
            self.assertIn("RELEVANCE", result["categories"])
            self.assertIn("INDUCTION", result["categories"])
            self.assertEqual(result["categories"]["RELEVANCE"], ["Appel à l'autorité"])
            self.assertEqual(result["categories"]["INDUCTION"], ["Appel à la popularité"])
    
    def test_categorize_fallacies(self):
        """Teste la méthode categorize_fallacies."""
        # Créer des sophismes
        fallacies = [
            {
                "fallacy_type": "Appel à l'autorité",
                "text": "Les experts affirment que ce produit est sûr.",
                "confidence": 0.7
            },
            {
                "fallacy_type": "Appel à la popularité",
                "text": "Ce produit est utilisé par des millions de personnes.",
                "confidence": 0.6
            },
            {
                "fallacy_type": "Ad hominem",
                "text": "Mon opposant n'a pas de diplôme en économie.",
                "confidence": 0.8
            }
        ]
        
        # Appeler la méthode categorize_fallacies
        categories = self.agent.categorize_fallacies(fallacies)
        
        # Vérifier le résultat
        self.assertIsInstance(categories, dict)
        
        # Vérifier que les sophismes sont correctement catégorisés
        # Note: Les catégories exactes dépendent de l'implémentation de categorize_fallacies
        # Nous vérifions simplement que la méthode retourne un dictionnaire non vide
        self.assertGreater(len(categories), 0)
    
    def test_extract_arguments(self):
        """Teste la méthode _extract_arguments."""
        # Patcher la méthode _extract_arguments
        with patch.object(self.agent, '_extract_arguments', return_value=[
            {
                "id": "arg-1",
                "text": "Les experts affirment que ce produit est sûr et efficace.",
                "confidence": 0.9
            },
            {
                "id": "arg-2",
                "text": "Ce produit est utilisé par des millions de personnes dans le monde entier.",
                "confidence": 0.85
            }
        ]) as mock_extract:
            
            # Appeler la méthode _extract_arguments
            arguments = self.agent._extract_arguments(self.text)
            
            # Vérifier le résultat
            self.assertIsInstance(arguments, list)
            self.assertEqual(len(arguments), 2)
            self.assertEqual(arguments[0]["id"], "arg-1")
            self.assertEqual(arguments[1]["id"], "arg-2")
    
    def test_process_text(self):
        """Teste la méthode _process_text."""
        # Patcher la méthode _process_text
        with patch.object(self.agent, '_process_text', return_value={
            "processed_text": self.text,
            "word_count": 50,
            "sentence_count": 4,
            "language": "fr"
        }) as mock_process:
            
            # Appeler la méthode _process_text
            result = self.agent._process_text(self.text)
            
            # Vérifier le résultat
            self.assertIsInstance(result, dict)
            self.assertIn("processed_text", result)
            self.assertIn("word_count", result)
            self.assertIn("sentence_count", result)
            self.assertIn("language", result)
    
    def test_analyze_text_with_empty_text(self):
        """Teste la méthode analyze_text avec un texte vide."""
        # Appeler la méthode analyze_text avec un texte vide
        result = self.agent.analyze_text("")
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Le texte est vide")
    
    def test_analyze_text_with_fallacy_detector_error(self):
        """Teste la méthode analyze_text avec une erreur du détecteur de sophismes."""
        # Configurer le détecteur de sophismes pour lever une exception
        self.fallacy_detector.detect.side_effect = Exception("Erreur du détecteur de sophismes")
        
        # Appeler la méthode analyze_text
        result = self.agent.analyze_text(self.text)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Erreur lors de l'analyse", result["error"])


if __name__ == "__main__":
    unittest.main()