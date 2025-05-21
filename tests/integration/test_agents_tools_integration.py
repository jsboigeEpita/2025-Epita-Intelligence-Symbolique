#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests d'intégration entre les agents et les outils d'analyse.

Ce module teste l'interaction entre les agents et les outils d'analyse
pour la détection et l'évaluation des sophismes.
"""

import unittest
import sys
import os
import pytest
from unittest.mock import MagicMock, patch
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestAgentsToolsIntegration")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('../..'))

# Import des modules à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import ComplexFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import FallacySeverityEvaluator


class TestAgentsToolsIntegration(unittest.TestCase):
    """Tests d'intégration entre les agents et les outils d'analyse."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer les outils d'analyse
        self.complex_analyzer = ComplexFallacyAnalyzer()
        self.contextual_analyzer = ContextualFallacyAnalyzer()
        self.severity_evaluator = FallacySeverityEvaluator()
        
        # Créer l'agent informel avec les outils d'analyse
        self.informal_agent = InformalAgent(
            agent_id="informal_agent_test",
            tools={
                "complex_analyzer": self.complex_analyzer,
                "contextual_analyzer": self.contextual_analyzer,
                "severity_evaluator": self.severity_evaluator
            }
        )
    
    def test_fallacy_detection_and_evaluation(self):
        """
        Teste la détection et l'évaluation des sophismes par l'agent informel
        en utilisant les outils d'analyse.
        """
        # Texte d'exemple contenant des sophismes
        text = """
        Tous les politiciens sont corrompus. Jean est un politicien, donc Jean est corrompu.
        Si nous autorisons le mariage homosexuel, bientôt les gens voudront épouser leurs animaux de compagnie.
        Einstein ne croyait pas à la mécanique quantique, donc la mécanique quantique est fausse.
        """
        
        # Patcher les méthodes des outils d'analyse pour simuler leur comportement
        with patch.object(self.complex_analyzer, 'analyze', return_value=[
            {"type": "généralisation_hâtive", "text": "Tous les politiciens sont corrompus", "confidence": 0.85},
            {"type": "pente_glissante", "text": "Si nous autorisons le mariage homosexuel, bientôt les gens voudront épouser leurs animaux de compagnie", "confidence": 0.92},
            {"type": "argument_d_autorité", "text": "Einstein ne croyait pas à la mécanique quantique, donc la mécanique quantique est fausse", "confidence": 0.88}
        ]) as mock_complex_analyze:
            
            with patch.object(self.contextual_analyzer, 'analyze_context', return_value={
                "généralisation_hâtive": {"context_relevance": 0.7, "cultural_factors": ["politique", "éthique"]},
                "pente_glissante": {"context_relevance": 0.9, "cultural_factors": ["mariage", "droits"]},
                "argument_d_autorité": {"context_relevance": 0.8, "cultural_factors": ["science", "physique"]}
            }) as mock_context_analyze:
                
                with patch.object(self.severity_evaluator, 'evaluate_severity', return_value=[
                    {"type": "généralisation_hâtive", "severity": 0.6, "impact": "medium"},
                    {"type": "pente_glissante", "severity": 0.8, "impact": "high"},
                    {"type": "argument_d_autorité", "severity": 0.7, "impact": "medium"}
                ]) as mock_evaluate:
                    
                    # Appeler la méthode d'analyse de l'agent informel
                    result = self.informal_agent.analyze_text(text)
                    
                    # Vérifier que les méthodes des outils d'analyse ont été appelées
                    mock_complex_analyze.assert_called_once_with(text)
                    mock_context_analyze.assert_called()
                    mock_evaluate.assert_called()
                    
                    # Vérifier le résultat
                    self.assertIsNotNone(result)
                    self.assertIn("fallacies", result)
                    self.assertEqual(len(result["fallacies"]), 3)
                    
                    # Vérifier que les sophismes détectés sont présents dans le résultat
                    fallacy_types = [f["type"] for f in result["fallacies"]]
                    self.assertIn("généralisation_hâtive", fallacy_types)
                    self.assertIn("pente_glissante", fallacy_types)
                    self.assertIn("argument_d_autorité", fallacy_types)
    
    def test_enhanced_analysis_workflow(self):
        """
        Teste le flux de travail complet d'analyse améliorée avec les outils d'analyse.
        """
        # Texte d'exemple
        text = """
        Le réchauffement climatique n'est pas réel car il a fait très froid cet hiver.
        Si nous réglementons les émissions de carbone, l'économie s'effondrera et des millions de personnes perdront leur emploi.
        """
        
        # Patcher les méthodes des outils d'analyse
        with patch.object(self.complex_analyzer, 'analyze') as mock_complex_analyze:
            with patch.object(self.contextual_analyzer, 'analyze_context') as mock_context_analyze:
                with patch.object(self.severity_evaluator, 'evaluate_severity') as mock_evaluate:
                    
                    # Configurer les retours des mocks
                    mock_complex_analyze.return_value = [
                        {"type": "faux_dilemme", "text": "Si nous réglementons les émissions de carbone, l'économie s'effondrera", "confidence": 0.87},
                        {"type": "généralisation_hâtive", "text": "Le réchauffement climatique n'est pas réel car il a fait très froid cet hiver", "confidence": 0.91}
                    ]
                    
                    mock_context_analyze.return_value = {
                        "faux_dilemme": {"context_relevance": 0.8, "cultural_factors": ["économie", "environnement"]},
                        "généralisation_hâtive": {"context_relevance": 0.9, "cultural_factors": ["climat", "science"]}
                    }
                    
                    mock_evaluate.return_value = [
                        {"type": "faux_dilemme", "severity": 0.75, "impact": "high"},
                        {"type": "généralisation_hâtive", "severity": 0.85, "impact": "high"}
                    ]
                    
                    # Appeler la méthode d'analyse améliorée de l'agent informel
                    result = self.informal_agent.perform_enhanced_analysis(text)
                    
                    # Vérifier que les méthodes des outils d'analyse ont été appelées dans le bon ordre
                    mock_complex_analyze.assert_called_once_with(text)
                    mock_context_analyze.assert_called_once()
                    mock_evaluate.assert_called_once()
                    
                    # Vérifier le résultat
                    self.assertIsNotNone(result)
                    self.assertIn("fallacies", result)
                    self.assertIn("context_analysis", result)
                    self.assertIn("severity_evaluation", result)
                    
                    # Vérifier que les sophismes détectés sont présents dans le résultat
                    fallacy_types = [f["type"] for f in result["fallacies"]]
                    self.assertIn("faux_dilemme", fallacy_types)
                    self.assertIn("généralisation_hâtive", fallacy_types)
                    
                    # Vérifier que l'analyse contextuelle est présente
                    self.assertIn("faux_dilemme", result["context_analysis"])
                    self.assertIn("généralisation_hâtive", result["context_analysis"])
                    
                    # Vérifier que l'évaluation de la sévérité est présente
                    severity_types = [f["type"] for f in result["severity_evaluation"]]
                    self.assertIn("faux_dilemme", severity_types)
                    self.assertIn("généralisation_hâtive", severity_types)


if __name__ == "__main__":
    pytest.main(["-v", __file__])