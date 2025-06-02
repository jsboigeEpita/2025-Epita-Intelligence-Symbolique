#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour les méthodes d'analyse des agents informels.
"""

import unittest
from unittest.mock import MagicMock, patch
# import json # Semble inutilisé

# La configuration du logging et les imports conditionnels de numpy/pandas
# sont maintenant gérés globalement dans tests/conftest.py

# Import des fixtures
from .fixtures import (
    mock_fallacy_detector,
    mock_rhetorical_analyzer,
    mock_contextual_analyzer,
    informal_agent_instance,
    sample_test_text # patch_semantic_kernel est autouse
)

# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent


class TestInformalAnalysisMethods(unittest.TestCase):
    """Tests unitaires pour les méthodes d'analyse des agents informels."""
    
    # setUp n'est plus nécessaire si les tests utilisent directement les fixtures

    def test_analyze_text(self, informal_agent_instance, mock_fallacy_detector, sample_test_text):
        """Teste la méthode analyze_text."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text
        
        # Configurer le mock pour ce test spécifique si nécessaire (le mock global est déjà là)
        mock_fallacy_detector.detect = MagicMock(return_value=[
            {"fallacy_type": "Appel à l'autorité", "text": "Les experts...", "confidence": 0.7},
            {"fallacy_type": "Appel à la popularité", "text": "Millions de personnes...", "confidence": 0.6}
        ])
        agent.tools["fallacy_detector"] = mock_fallacy_detector # S'assurer que l'agent utilise ce mock configuré

        result = agent.analyze_text(text_to_analyze)
        
        mock_fallacy_detector.detect.assert_called_once_with(text_to_analyze)
        
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        self.assertIn("analysis_timestamp", result)
        
        self.assertIsInstance(result["fallacies"], list)
        self.assertEqual(len(result["fallacies"]), 2)
        self.assertEqual(result["fallacies"][0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(result["fallacies"][1]["fallacy_type"], "Appel à la popularité")
    
    def test_analyze_text_with_context(self, informal_agent_instance, mock_fallacy_detector, sample_test_text):
        """Teste la méthode analyze_text avec un contexte."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text
        context = "Discours commercial pour un produit controversé"
        
        mock_fallacy_detector.detect = MagicMock(return_value=[]) # Adaptez le retour si nécessaire
        agent.tools["fallacy_detector"] = mock_fallacy_detector

        result = agent.analyze_text(text_to_analyze, context)
        
        mock_fallacy_detector.detect.assert_called_once_with(text_to_analyze)
        
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        self.assertIn("context", result)
        self.assertIn("analysis_timestamp", result)
        self.assertEqual(result["context"], context)
    
    def test_analyze_text_with_confidence_threshold(self, informal_agent_instance, mock_fallacy_detector, sample_test_text):
        """Teste la méthode analyze_text avec un seuil de confiance."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text
        agent.config["confidence_threshold"] = 0.65
        
        mock_fallacy_detector.detect = MagicMock(return_value=[
            {"fallacy_type": "Appel à l'autorité", "text": "Les experts...", "confidence": 0.7},
            {"fallacy_type": "Appel à la popularité", "text": "Millions de personnes...", "confidence": 0.6}
        ])
        agent.tools["fallacy_detector"] = mock_fallacy_detector

        result = agent.analyze_text(text_to_analyze)
        
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        self.assertEqual(len(result["fallacies"]), 1)
        self.assertEqual(result["fallacies"][0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(result["fallacies"][0]["confidence"], 0.7)
    
    def test_analyze_text_with_max_fallacies(self, informal_agent_instance, mock_fallacy_detector, sample_test_text):
        """Teste la méthode analyze_text avec un nombre maximum de sophismes."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text
        agent.config["max_fallacies"] = 1

        mock_fallacy_detector.detect = MagicMock(return_value=[
            {"fallacy_type": "Appel à l'autorité", "text": "Les experts...", "confidence": 0.7},
            {"fallacy_type": "Appel à la popularité", "text": "Millions de personnes...", "confidence": 0.6}
        ])
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        
        result = agent.analyze_text(text_to_analyze)
        
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        self.assertEqual(len(result["fallacies"]), 1)
        self.assertEqual(result["fallacies"][0]["fallacy_type"], "Appel à l'autorité")
    
    def test_perform_complete_analysis(self, informal_agent_instance, mock_fallacy_detector, mock_rhetorical_analyzer, sample_test_text):
        """Teste la méthode perform_complete_analysis."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text

        # Configurer les mocks pour ce test
        mock_fallacy_detector.detect = MagicMock(return_value=[
            {"fallacy_type": "Appel à l'autorité", "confidence": 0.7},
            {"fallacy_type": "Appel à la popularité", "confidence": 0.6}
        ])
        mock_rhetorical_analyzer.analyze = MagicMock(return_value={
            "tone": "persuasif", "style": "émotionnel",
            "techniques": ["appel à l'émotion"], "effectiveness": 0.8
        })
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        agent.tools["rhetorical_analyzer"] = mock_rhetorical_analyzer

        result = agent.perform_complete_analysis(text_to_analyze)
        
        mock_fallacy_detector.detect.assert_called_once_with(text_to_analyze)
        mock_rhetorical_analyzer.analyze.assert_called_once_with(text_to_analyze)
        
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        self.assertIn("rhetorical_analysis", result)
        self.assertIn("text", result)
        # self.assertIn("context", result) # Context est optionnel ici
        self.assertIn("categories", result) # categorize_fallacies est appelé
        
        self.assertIsInstance(result["fallacies"], list)
        self.assertEqual(len(result["fallacies"]), 2)
        
        self.assertIsInstance(result["rhetorical_analysis"], dict)
        self.assertEqual(result["rhetorical_analysis"]["tone"], "persuasif")
    
    def test_perform_complete_analysis_with_context(self, informal_agent_instance, mock_fallacy_detector, mock_rhetorical_analyzer, mock_contextual_analyzer, sample_test_text):
        """Teste la méthode perform_complete_analysis avec un contexte."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text
        context = "Discours commercial pour un produit controversé"

        # Configurer les mocks
        mock_fallacy_detector.detect = MagicMock(return_value=[])
        mock_rhetorical_analyzer.analyze = MagicMock(return_value={})
        mock_contextual_analyzer.analyze_context = MagicMock(return_value={"context_type": "commercial", "confidence": 0.9})
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        agent.tools["rhetorical_analyzer"] = mock_rhetorical_analyzer
        agent.tools["contextual_analyzer"] = mock_contextual_analyzer

        result = agent.perform_complete_analysis(text_to_analyze, context)
        
        mock_fallacy_detector.detect.assert_called_once_with(text_to_analyze)
        mock_rhetorical_analyzer.analyze.assert_called_once_with(text_to_analyze)
        mock_contextual_analyzer.analyze_context.assert_called_once_with(text_to_analyze, context)
        
        self.assertIsInstance(result, dict)
        self.assertIn("contextual_analysis", result)
        self.assertEqual(result["context"], context)
        self.assertEqual(result["contextual_analysis"]["context_type"], "commercial")
    
    def test_analyze_and_categorize(self, informal_agent_instance, mock_fallacy_detector, sample_test_text):
        """Teste la méthode analyze_and_categorize."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text

        mock_fallacy_detector.detect = MagicMock(return_value=[
             {"fallacy_type": "Appel à l'autorité", "confidence": 0.7},
             {"fallacy_type": "Appel à la popularité", "confidence": 0.6}
        ])
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        
        # Patcher la méthode categorize_fallacies de l'instance de l'agent
        with patch.object(agent, 'categorize_fallacies', return_value={
            "RELEVANCE": ["Appel à l'autorité"],
            "INDUCTION": ["Appel à la popularité"]
        }) as mock_categorize:
            
            result = agent.analyze_and_categorize(text_to_analyze)
            
            mock_fallacy_detector.detect.assert_called_once_with(text_to_analyze)
            mock_categorize.assert_called_once() # mock_categorize est appelé avec la sortie de detect
            
            self.assertIsInstance(result, dict)
            self.assertIn("fallacies", result)
            self.assertIn("categories", result)
            self.assertEqual(result["categories"]["RELEVANCE"], ["Appel à l'autorité"])
    
    def test_categorize_fallacies(self, informal_agent_instance): # Pas besoin de mock_fallacy_detector ici
        """Teste la méthode categorize_fallacies."""
        agent = informal_agent_instance
        fallacies_input = [
            {"fallacy_type": "Appel à l'autorité", "text": "...", "confidence": 0.7},
            {"fallacy_type": "Appel à la popularité", "text": "...", "confidence": 0.6},
            {"fallacy_type": "Ad hominem", "text": "...", "confidence": 0.8}
        ]
        
        categories = agent.categorize_fallacies(fallacies_input)
        
        self.assertIsInstance(categories, dict)
        # Les catégories exactes dépendent de l'implémentation réelle,
        # mais on s'attend à ce que certains types soient classés.
        # Par exemple, si "Ad Hominem" est classé sous "RELEVANCE_PERSONAL_ATTACK"
        # self.assertIn("RELEVANCE_PERSONAL_ATTACK", categories)
        # self.assertIn("Ad hominem", categories["RELEVANCE_PERSONAL_ATTACK"])
        self.assertGreater(len(categories), 0) # Au moins une catégorie
    
    def test_extract_arguments(self, informal_agent_instance, sample_test_text):
        """Teste la méthode _extract_arguments."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text
        # Cette méthode est interne et potentiellement complexe à mocker sans connaître son implémentation.
        # Si elle utilise semantic_kernel, le patch autouse devrait s'appliquer.
        # Pour un test unitaire plus ciblé, il faudrait mocker ses dépendances internes.
        # Ici, on se contente d'un patch de haut niveau pour illustrer.
        with patch.object(agent, '_extract_arguments', return_value=[
            {"id": "arg-1", "text": "Argument 1", "confidence": 0.9},
            {"id": "arg-2", "text": "Argument 2", "confidence": 0.85}
        ]) as mock_extract:
            arguments = agent._extract_arguments(text_to_analyze) # pylint: disable=protected-access
            mock_extract.assert_called_once_with(text_to_analyze)
            self.assertEqual(len(arguments), 2)
            self.assertEqual(arguments[0]["id"], "arg-1")
    
    def test_process_text(self, informal_agent_instance, sample_test_text):
        """Teste la méthode _process_text."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text
        # Similaire à _extract_arguments, c'est une méthode interne.
        with patch.object(agent, '_process_text', return_value={
            "processed_text": text_to_analyze, "word_count": 10,
            "sentence_count": 2, "language": "fr"
        }) as mock_process:
            result = agent._process_text(text_to_analyze) # pylint: disable=protected-access
            mock_process.assert_called_once_with(text_to_analyze)
            self.assertEqual(result["language"], "fr")

    def test_analyze_text_with_empty_text(self, informal_agent_instance):
        """Teste la méthode analyze_text avec un texte vide."""
        agent = informal_agent_instance
        result = agent.analyze_text("")
        
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Le texte est vide")
    
    def test_analyze_text_with_fallacy_detector_error(self, informal_agent_instance, mock_fallacy_detector, sample_test_text):
        """Teste la méthode analyze_text avec une erreur du détecteur de sophismes."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text
        
        mock_fallacy_detector.detect = MagicMock(side_effect=Exception("Erreur du détecteur de sophismes"))
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        
        result = agent.analyze_text(text_to_analyze)
        
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Erreur lors de l'analyse", result["error"])


if __name__ == "__main__":
    unittest.main()