#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour la gestion des erreurs des agents informels.
"""

# import unittest # Supprimé
import pytest # Ajouté
from unittest.mock import MagicMock, patch

# La configuration du logging et les imports conditionnels de numpy/pandas
# sont maintenant gérés globalement dans tests/conftest.py

# Import des fixtures
from .fixtures import (
    mock_fallacy_detector,
    mock_rhetorical_analyzer,
    mock_contextual_analyzer, 
    informal_agent_instance,
    sample_test_text 
)

# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent


class TestInformalErrorHandling: # Suppression de l'héritage unittest.TestCase
    """Tests unitaires pour la gestion des erreurs des agents informels."""

    def test_handle_empty_text(self, informal_agent_instance, mock_fallacy_detector):
        """Teste la gestion d'un texte vide."""
        agent = informal_agent_instance
        agent.tools["fallacy_detector"] = mock_fallacy_detector

        result = agent.analyze_text("")
        
        assert isinstance(result, dict)
        assert "error" in result
        assert result["error"] == "Le texte est vide"
        assert "fallacies" in result
        assert result["fallacies"] == []
        mock_fallacy_detector.detect.assert_not_called()
    
    def test_handle_none_text(self, informal_agent_instance, mock_fallacy_detector):
        """Teste la gestion d'un texte None."""
        agent = informal_agent_instance
        agent.tools["fallacy_detector"] = mock_fallacy_detector

        result = agent.analyze_text(None)
        
        assert isinstance(result, dict)
        assert "error" in result
        assert result["error"] == "Le texte est vide"
        assert "fallacies" in result
        assert result["fallacies"] == []
        mock_fallacy_detector.detect.assert_not_called()
    
    def test_handle_fallacy_detector_exception(self, informal_agent_instance, mock_fallacy_detector, sample_test_text):
        """Teste la gestion d'une exception du détecteur de sophismes."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text
        
        mock_fallacy_detector.detect.side_effect = Exception("Erreur du détecteur de sophismes")
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        
        result = agent.analyze_text(text_to_analyze)
        
        assert isinstance(result, dict)
        assert "error" in result
        assert "Erreur lors de l'analyse" in result["error"]
        assert "Erreur du détecteur de sophismes" in result["error"]
        assert "fallacies" in result
        assert result["fallacies"] == []
    
    def test_handle_rhetorical_analyzer_exception(self, informal_agent_instance, mock_fallacy_detector, mock_rhetorical_analyzer, sample_test_text):
        """Teste la gestion d'une exception de l'analyseur rhétorique."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text

        mock_rhetorical_analyzer.analyze.side_effect = Exception("Erreur de l'analyseur rhétorique")
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        agent.tools["rhetorical_analyzer"] = mock_rhetorical_analyzer
        
        mock_fallacy_detector.reset_mock()
        mock_fallacy_detector.detect = MagicMock(return_value=[{"fallacy_type": "Appel à l'autorité", "text": "...", "confidence": 0.7}])

        result = agent.analyze_argument(text_to_analyze)
        
        assert isinstance(result, dict)
        assert "argument" in result
        assert result["argument"] == text_to_analyze
        
        mock_fallacy_detector.detect.assert_called_once_with(text_to_analyze)
        
        assert "fallacies" in result
        assert isinstance(result["fallacies"], list)
        assert len(result["fallacies"]) == 1
        
        assert "rhetoric" not in result
    
    def test_handle_contextual_analyzer_exception(self, informal_agent_instance, mock_fallacy_detector, mock_rhetorical_analyzer, mock_contextual_analyzer, sample_test_text):
        """Teste la gestion d'une exception de l'analyseur contextuel."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text

        mock_contextual_analyzer.analyze_context.side_effect = Exception("Erreur de l'analyseur contextuel")
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        agent.tools["rhetorical_analyzer"] = mock_rhetorical_analyzer
        agent.tools["contextual_analyzer"] = mock_contextual_analyzer
        agent.config["include_context"] = True

        mock_fallacy_detector.reset_mock()
        mock_fallacy_detector.detect = MagicMock(return_value=[{"fallacy_type": "Appel à l'autorité", "text": "...", "confidence": 0.7}])
        mock_rhetorical_analyzer.reset_mock()
        mock_rhetorical_analyzer.analyze = MagicMock(return_value={"tone": "persuasif"})

        result = agent.analyze_argument(text_to_analyze)
        
        assert isinstance(result, dict)
        assert "argument" in result
        
        mock_fallacy_detector.detect.assert_called_once_with(text_to_analyze)
        mock_rhetorical_analyzer.analyze.assert_called_once_with(text_to_analyze)
        
        assert "fallacies" in result
        assert "rhetoric" in result
        
        assert "context" not in result
    
    def test_handle_invalid_fallacy_detector_result(self, informal_agent_instance, mock_fallacy_detector, sample_test_text):
        """Teste la gestion d'un résultat invalide du détecteur de sophismes."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text
        
        mock_fallacy_detector.detect.return_value = "résultat invalide"
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        
        result = agent.analyze_text(text_to_analyze)
        
        assert isinstance(result, dict)
        assert "fallacies" in result
        assert result["fallacies"] == []
        assert "analysis_timestamp" in result
    
    def test_handle_invalid_rhetorical_analyzer_result(self, informal_agent_instance, mock_fallacy_detector, mock_rhetorical_analyzer, sample_test_text):
        """Teste la gestion d'un résultat invalide de l'analyseur rhétorique."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text

        mock_rhetorical_analyzer.analyze.return_value = "résultat invalide"
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        agent.tools["rhetorical_analyzer"] = mock_rhetorical_analyzer
        
        mock_fallacy_detector.detect = MagicMock(return_value=[{"fallacy_type": "Appel à l'autorité", "text": "...", "confidence": 0.7}])

        result = agent.analyze_argument(text_to_analyze)
        
        assert isinstance(result, dict)
        assert "argument" in result
        
        assert "fallacies" in result
        assert len(result["fallacies"]) == 1
        
        assert "rhetoric" in result
        assert result["rhetoric"] == "résultat invalide"
    
    def test_handle_missing_required_tool(self, mock_rhetorical_analyzer):
        """Teste la gestion d'un outil requis manquant."""
        with pytest.raises(ValueError) as excinfo:
            agent = InformalAgent( # pylint: disable=unused-variable
                agent_id="missing_tool_agent",
                tools={"rhetorical_analyzer": mock_rhetorical_analyzer}
            )
        
        error_msg = str(excinfo.value)
        assert "détecteur de sophismes" in error_msg or "fallacy_detector" in error_msg, \
               f"Message d'erreur inattendu: {error_msg}"
    
    def test_handle_invalid_tool_type(self):
        """Teste la gestion d'un type d'outil invalide."""
        with pytest.raises(TypeError) as excinfo:
            agent = InformalAgent( # pylint: disable=unused-variable
                agent_id="invalid_tool_agent",
                tools={"fallacy_detector": "not a tool"}
            )
        assert "fallacy_detector" in str(excinfo.value)
    
    def test_handle_invalid_config(self, mock_fallacy_detector):
        """Teste la gestion d'une configuration invalide."""
        agent = InformalAgent(
            agent_id="invalid_config_agent",
            tools={"fallacy_detector": mock_fallacy_detector},
            config="not a dict"
        )
        assert agent.config == "not a dict"
    
    def test_handle_invalid_confidence_threshold(self, mock_fallacy_detector):
        """Teste la gestion d'un seuil de confiance invalide."""
        config = {"confidence_threshold": "not a number"}
        agent = InformalAgent(
            agent_id="invalid_threshold_agent",
            tools={"fallacy_detector": mock_fallacy_detector},
            config=config
        )
        assert agent.config["confidence_threshold"] == "not a number"
    
    def test_handle_out_of_range_confidence_threshold(self, mock_fallacy_detector):
        """Teste la gestion d'un seuil de confiance hors limites."""
        config = {"confidence_threshold": 1.5}
        agent = InformalAgent(
            agent_id="out_of_range_threshold_agent",
            tools={"fallacy_detector": mock_fallacy_detector},
            config=config
        )
        assert agent.config["confidence_threshold"] == 1.5
    
    def test_handle_recovery_from_error(self, informal_agent_instance, mock_fallacy_detector, sample_test_text):
        """Teste la récupération après une erreur."""
        agent = informal_agent_instance
        text_to_analyze = sample_test_text
        
        mock_fallacy_detector.detect.side_effect = Exception("Erreur du détecteur de sophismes")
        agent.tools["fallacy_detector"] = mock_fallacy_detector
        
        result1 = agent.analyze_text(text_to_analyze)
        assert "error" in result1
        
        mock_fallacy_detector.detect.side_effect = None
        mock_fallacy_detector.detect.return_value = [
            {"fallacy_type": "Appel à l'autorité", "text": "...", "confidence": 0.7}
        ]

        result2 = agent.analyze_text(text_to_analyze)
        
        assert "error" not in result2
        assert "fallacies" in result2
        assert len(result2["fallacies"]) == 1

# if __name__ == "__main__": # Supprimé
#     unittest.main()