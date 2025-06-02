#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour la gestion des erreurs des agents informels.
"""

import unittest
from unittest.mock import MagicMock, patch
# import json # Semble inutilisé

# La configuration du logging et les imports conditionnels de numpy/pandas
# sont maintenant gérés globalement dans tests/conftest.py
# Les imports de sys et os ne semblent plus nécessaires ici.

# Import des fixtures
from .fixtures import (
    mock_fallacy_detector,
    mock_rhetorical_analyzer,
    mock_contextual_analyzer, # Ajouté pour test_handle_contextual_analyzer_exception
    informal_agent_instance,
    sample_test_text # patch_semantic_kernel est autouse
)

# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent


class TestInformalErrorHandling(unittest.TestCase):
    """Tests unitaires pour la gestion des erreurs des agents informels."""
    
    # setUp n'est plus nécessaire si les tests utilisent directement les fixtures

    def test_handle_empty_text(self, informal_agent_instance, mock_fallacy_detector):
        """Teste la gestion d'un texte vide."""
        agent = informal_agent_instance
        # S'assurer que le mock_fallacy_detector est celui utilisé par l'agent pour ce test
        agent.tools["fallacy_detector"] = mock_fallacy_detector

        result = agent.analyze_text("")
        
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Le texte est vide")
        self.assertIn("fallacies", result)
        self.assertEqual(result["fallacies"], [])
        mock_fallacy_detector.detect.assert_not_called()
    
    def test_handle_none_text(self, informal_agent_instance, mock_fallacy_detector):
        """Teste la gestion d'un texte None."""
        agent = informal_agent_instance
        agent.tools["fallacy_detector"] = mock_fallacy_detector

        result = agent.analyze_text(None)
        
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Le texte est vide")
        self.assertIn("fallacies", result)
        self.assertEqual(result["fallacies"], [])
        mock_fallacy_detector.detect.assert_not_called()
    
    def test_handle_fallacy_detector_exception(self, informal_agent_instance, mock_fallacy_detector, sample_test_text):
        """Teste la gestion d'une exception du détecteur de sophismes."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text
        
        mock_fallacy_detector.detect.side_effect = Exception("Erreur du détecteur de sophismes")
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        
        result = agent.analyze_text(text_to_analyze)
        
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Erreur lors de l'analyse", result["error"])
        self.assertIn("Erreur du détecteur de sophismes", result["error"])
        self.assertIn("fallacies", result)
        self.assertEqual(result["fallacies"], [])
    
    def test_handle_rhetorical_analyzer_exception(self, informal_agent_instance, mock_fallacy_detector, mock_rhetorical_analyzer, sample_test_text):
        """Teste la gestion d'une exception de l'analyseur rhétorique."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text

        mock_rhetorical_analyzer.analyze.side_effect = Exception("Erreur de l'analyseur rhétorique")
        # Assurer que l'agent utilise les mocks configurés pour ce test
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        agent.tools["rhetorical_analyzer"] = mock_rhetorical_analyzer
        
        # Réinitialiser le mock_fallacy_detector pour ce test spécifique si nécessaire
        mock_fallacy_detector.reset_mock()
        mock_fallacy_detector.detect = MagicMock(return_value=[{"fallacy_type": "Appel à l'autorité", "text": "...", "confidence": 0.7}])


        result = agent.analyze_argument(text_to_analyze)
        
        self.assertIsInstance(result, dict)
        self.assertIn("argument", result)
        self.assertEqual(result["argument"], text_to_analyze)
        
        mock_fallacy_detector.detect.assert_called_once_with(text_to_analyze)
        
        self.assertIn("fallacies", result)
        self.assertIsInstance(result["fallacies"], list)
        self.assertEqual(len(result["fallacies"]), 1) # S'attend à ce que les fallacies soient détectées
        
        self.assertNotIn("rhetoric", result) # L'analyse rhétorique a échoué
    
    def test_handle_contextual_analyzer_exception(self, informal_agent_instance, mock_fallacy_detector, mock_rhetorical_analyzer, mock_contextual_analyzer, sample_test_text):
        """Teste la gestion d'une exception de l'analyseur contextuel."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text

        mock_contextual_analyzer.analyze_context.side_effect = Exception("Erreur de l'analyseur contextuel")
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        agent.tools["rhetorical_analyzer"] = mock_rhetorical_analyzer
        agent.tools["contextual_analyzer"] = mock_contextual_analyzer # S'assurer que l'agent l'utilise
        agent.config["include_context"] = True # Activer l'analyse contextuelle

        # Réinitialiser les mocks pour ce test
        mock_fallacy_detector.reset_mock()
        mock_fallacy_detector.detect = MagicMock(return_value=[{"fallacy_type": "Appel à l'autorité", "text": "...", "confidence": 0.7}])
        mock_rhetorical_analyzer.reset_mock()
        mock_rhetorical_analyzer.analyze = MagicMock(return_value={"tone": "persuasif"})


        result = agent.analyze_argument(text_to_analyze) # analyze_argument peut appeler analyze_context
        
        self.assertIsInstance(result, dict)
        self.assertIn("argument", result)
        
        mock_fallacy_detector.detect.assert_called_once_with(text_to_analyze)
        mock_rhetorical_analyzer.analyze.assert_called_once_with(text_to_analyze)
        
        self.assertIn("fallacies", result)
        self.assertIn("rhetoric", result)
        
        self.assertNotIn("context", result) # L'analyse contextuelle a échoué
    
    def test_handle_invalid_fallacy_detector_result(self, informal_agent_instance, mock_fallacy_detector, sample_test_text):
        """Teste la gestion d'un résultat invalide du détecteur de sophismes."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text
        
        mock_fallacy_detector.detect.return_value = "résultat invalide"
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        
        result = agent.analyze_text(text_to_analyze)
        
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        self.assertEqual(result["fallacies"], []) # Devrait retourner une liste vide
        self.assertIn("analysis_timestamp", result)
    
    def test_handle_invalid_rhetorical_analyzer_result(self, informal_agent_instance, mock_fallacy_detector, mock_rhetorical_analyzer, sample_test_text):
        """Teste la gestion d'un résultat invalide de l'analyseur rhétorique."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text

        mock_rhetorical_analyzer.analyze.return_value = "résultat invalide"
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        agent.tools["rhetorical_analyzer"] = mock_rhetorical_analyzer
        
        # Configurer mock_fallacy_detector pour ce test
        mock_fallacy_detector.detect = MagicMock(return_value=[{"fallacy_type": "Appel à l'autorité", "text": "...", "confidence": 0.7}])


        result = agent.analyze_argument(text_to_analyze)
        
        self.assertIsInstance(result, dict)
        self.assertIn("argument", result)
        
        self.assertIn("fallacies", result)
        self.assertEqual(len(result["fallacies"]), 1)
        
        self.assertIn("rhetoric", result)
        self.assertEqual(result["rhetoric"], "résultat invalide") # Le résultat invalide est conservé
    
    def test_handle_missing_required_tool(self, mock_rhetorical_analyzer): # Pas besoin d'instance d'agent ici
        """Teste la gestion d'un outil requis manquant."""
        with self.assertRaises(ValueError) as context:
            agent = InformalAgent( # pylint: disable=unused-variable
                agent_id="missing_tool_agent",
                tools={"rhetorical_analyzer": mock_rhetorical_analyzer}
            )
        
        error_msg = str(context.exception)
        self.assertTrue(
            "détecteur de sophismes" in error_msg or "fallacy_detector" in error_msg,
            f"Message d'erreur inattendu: {error_msg}"
        )
    
    def test_handle_invalid_tool_type(self): # Pas besoin d'instance d'agent ici
        """Teste la gestion d'un type d'outil invalide."""
        with self.assertRaises(TypeError) as context:
            agent = InformalAgent( # pylint: disable=unused-variable
                agent_id="invalid_tool_agent",
                tools={"fallacy_detector": "not a tool"}
            )
        self.assertIn("fallacy_detector", str(context.exception))
    
    def test_handle_invalid_config(self, mock_fallacy_detector):
        """Teste la gestion d'une configuration invalide."""
        agent = InformalAgent(
            agent_id="invalid_config_agent",
            tools={"fallacy_detector": mock_fallacy_detector},
            config="not a dict"
        )
        self.assertEqual(agent.config, "not a dict")
    
    def test_handle_invalid_confidence_threshold(self, mock_fallacy_detector):
        """Teste la gestion d'un seuil de confiance invalide."""
        config = {"confidence_threshold": "not a number"}
        agent = InformalAgent(
            agent_id="invalid_threshold_agent",
            tools={"fallacy_detector": mock_fallacy_detector},
            config=config
        )
        self.assertEqual(agent.config["confidence_threshold"], "not a number")
    
    def test_handle_out_of_range_confidence_threshold(self, mock_fallacy_detector):
        """Teste la gestion d'un seuil de confiance hors limites."""
        config = {"confidence_threshold": 1.5}
        agent = InformalAgent(
            agent_id="out_of_range_threshold_agent",
            tools={"fallacy_detector": mock_fallacy_detector},
            config=config
        )
        self.assertEqual(agent.config["confidence_threshold"], 1.5)
    
    def test_handle_recovery_from_error(self, informal_agent_instance, mock_fallacy_detector, sample_test_text):
        """Teste la récupération après une erreur."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text
        
        mock_fallacy_detector.detect.side_effect = Exception("Erreur du détecteur de sophismes")
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        
        result1 = agent.analyze_text(text_to_analyze)
        self.assertIn("error", result1)
        
        # Réinitialiser le mock pour la récupération
        mock_fallacy_detector.detect.side_effect = None
        mock_fallacy_detector.detect.return_value = [
            {"fallacy_type": "Appel à l'autorité", "text": "...", "confidence": 0.7}
        ]
        # Pas besoin de réassigner à agent.tools si c'est le même objet mock qui est modifié

        result2 = agent.analyze_text(text_to_analyze)
        
        self.assertNotIn("error", result2)
        self.assertIn("fallacies", result2)
        self.assertEqual(len(result2["fallacies"]), 1)


if __name__ == "__main__":
    unittest.main()