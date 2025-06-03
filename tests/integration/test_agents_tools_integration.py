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
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# L'installation du package via `pip install -e .` devrait gérer l'accessibilité,
# mais cette modification assure le fonctionnement même sans installation en mode édition.
# conftest.py et pytest.ini devraient également aider, mais ajout explicite pour robustesse.

# Import des modules à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer as ComplexFallacyAnalyzer # Alias
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer as ContextualFallacyAnalyzer # Alias
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator as FallacySeverityEvaluator # Alias


class TestAgentsToolsIntegration(unittest.TestCase):
    """Tests d'intégration entre les agents et les outils d'analyse."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.complex_analyzer = ComplexFallacyAnalyzer()
        self.contextual_analyzer = ContextualFallacyAnalyzer()
        self.severity_evaluator = FallacySeverityEvaluator()
        
        # Créer un mock fallacy_detector qui sera utilisé par l'agent
        self.fallacy_detector = MagicMock()
        self.fallacy_detector.detect.return_value = [
            {"fallacy_type": "généralisation_hâtive", "confidence": 0.85, "context_text": "..."},
            {"fallacy_type": "pente_glissante", "confidence": 0.92, "context_text": "..."},
            {"fallacy_type": "argument_d_autorité", "confidence": 0.88, "context_text": "..."}
        ]
        
        self.informal_agent = InformalAgent(
            agent_id="informal_agent_test",
            tools={
                "fallacy_detector": self.fallacy_detector,
                "complex_analyzer": self.complex_analyzer,
                "contextual_analyzer": self.contextual_analyzer,
                "severity_evaluator": self.severity_evaluator
            },
            strict_validation=False
        )
    
    def test_fallacy_detection_and_evaluation(self):
        """
        Teste la détection et l'évaluation des sophismes par l'agent informel
        en utilisant le détecteur de sophismes.
        """
        text = """
        Tous les politiciens sont corrompus. Jean est un politicien, donc Jean est corrompu.
        Si nous autorisons le mariage homosexuel, bientôt les gens voudront épouser leurs animaux de compagnie.
        Einstein ne croyait pas à la mécanique quantique, donc la mécanique quantique est fausse.
        """
        
        # Configurer le mock du détecteur de sophismes
        expected_fallacies = [
            {"fallacy_type": "généralisation_hâtive", "confidence": 0.85, "context_text": "..."},
            {"fallacy_type": "pente_glissante", "confidence": 0.92, "context_text": "..."},
            {"fallacy_type": "argument_d_autorité", "confidence": 0.88, "context_text": "..."}
        ]
        self.fallacy_detector.detect.return_value = expected_fallacies
        
        # Appeler la méthode d'analyse de l'agent informel
        result = self.informal_agent.analyze_text(text)
        
        # Vérifier que le détecteur de sophismes a été appelé
        self.fallacy_detector.detect.assert_called_once_with(text)
        
        # Vérifier le résultat
        self.assertIsNotNone(result)
        self.assertIn("fallacies", result)
        self.assertGreaterEqual(len(result["fallacies"]), 1)
        
        # Vérifier que les sophismes attendus sont présents
        fallacy_types = [f.get("fallacy_type") for f in result["fallacies"]]
        self.assertIn("généralisation_hâtive", fallacy_types)
        self.assertIn("pente_glissante", fallacy_types)
        self.assertIn("argument_d_autorité", fallacy_types)

    # Le test_enhanced_analysis_workflow est très similaire au précédent
    # et pourrait être fusionné ou simplifié si l'agent a une seule méthode d'analyse principale.
    # Pour l'instant, on le garde pour vérifier une autre facette potentielle de l'agent.
    def test_enhanced_analysis_workflow(self):
        """
        Teste le workflow d'analyse améliorée avec l'agent informel.
        """
        text = """
        Le réchauffement climatique n'est pas réel car il a fait très froid cet hiver.
        Si nous réglementons les émissions de carbone, l'économie s'effondrera et des millions de personnes perdront leur emploi.
        """
        
        # Configurer le mock du détecteur de sophismes pour ce test
        expected_fallacies = [
            {"fallacy_type": "faux_dilemme", "confidence": 0.87, "context_text": "..."},
            {"fallacy_type": "généralisation_hâtive", "confidence": 0.91, "context_text": "..."}
        ]
        self.fallacy_detector.detect.return_value = expected_fallacies
        
        # Tester la méthode perform_complete_analysis si elle existe, sinon analyze_text
        if hasattr(self.informal_agent, 'perform_complete_analysis'):
            result = self.informal_agent.perform_complete_analysis(text)
        else:
            result = self.informal_agent.analyze_text(text)
        
        # Vérifier que le détecteur de sophismes a été appelé
        self.fallacy_detector.detect.assert_called_once_with(text)
        
        # Vérifier le résultat
        self.assertIsNotNone(result)
        self.assertIn("fallacies", result)
        self.assertGreaterEqual(len(result["fallacies"]), 1)
        
        # Vérifier que les sophismes attendus sont présents
        fallacy_types = [f.get("fallacy_type") for f in result["fallacies"]]
        self.assertIn("faux_dilemme", fallacy_types)
        self.assertIn("généralisation_hâtive", fallacy_types)

    def test_agent_tool_configuration_validation(self):
        """
        Teste la validation de la configuration des outils de l'agent.
        """
        # Test avec configuration valide
        valid_tools = {
            "fallacy_detector": self.fallacy_detector,
            "contextual_analyzer": self.contextual_analyzer
        }
        
        agent = InformalAgent(
            agent_id="test_validation",
            tools=valid_tools,
            strict_validation=False
        )
        
        # Vérifier que l'agent est correctement configuré
        self.assertEqual(agent.agent_id, "test_validation")
        self.assertEqual(len(agent.get_available_tools()), 2)
        self.assertIn("fallacy_detector", agent.get_available_tools())
        self.assertIn("contextual_analyzer", agent.get_available_tools())
        
        # Vérifier les capacités de l'agent
        capabilities = agent.get_agent_capabilities()
        self.assertTrue(capabilities["fallacy_detection"])
        self.assertTrue(capabilities["contextual_analysis"])
        self.assertFalse(capabilities["rhetorical_analysis"])
        
        # Test avec configuration invalide (outils vides)
        with self.assertRaises(ValueError) as context:
            InformalAgent(
                agent_id="test_invalid",
                tools={},
                strict_validation=True
            )
        self.assertIn("Aucun outil fourni", str(context.exception))

    def test_multi_tool_analysis_workflow(self):
        """
        Teste un workflow d'analyse utilisant plusieurs outils de manière coordonnée.
        """
        text = """
        Les vaccins causent l'autisme car mon voisin m'a dit que son enfant est devenu autiste après vaccination.
        Tous les scientifiques sont payés par les compagnies pharmaceutiques, donc on ne peut pas leur faire confiance.
        """
        
        # Configurer les mocks pour simuler un workflow complet
        expected_fallacies = [
            {"fallacy_type": "anecdote_personnelle", "confidence": 0.89, "context_text": "mon voisin m'a dit"},
            {"fallacy_type": "généralisation_hâtive", "confidence": 0.92, "context_text": "Tous les scientifiques"},
            {"fallacy_type": "ad_hominem", "confidence": 0.85, "context_text": "payés par les compagnies"}
        ]
        self.fallacy_detector.detect.return_value = expected_fallacies
        
        # Configurer l'analyseur contextuel pour simuler une analyse contextuelle
        self.contextual_analyzer.analyze_context = MagicMock(return_value={
            "context_type": "medical_misinformation",
            "confidence": 0.94,
            "risk_level": "high",
            "related_topics": ["vaccination", "autism", "conspiracy_theory"]
        })
        
        # Effectuer une analyse complète avec contexte pour déclencher l'analyse contextuelle
        context = "Discussion sur la vaccination et l'autisme"
        result = self.informal_agent.perform_complete_analysis(text, context=context)
        
        # Vérifier que le détecteur de sophismes a été appelé
        self.fallacy_detector.detect.assert_called_once_with(text)
        
        # Vérifier le résultat de l'analyse
        self.assertIsNotNone(result)
        self.assertIn("fallacies", result)
        self.assertIn("contextual_analysis", result)
        
        # Vérifier les sophismes détectés
        fallacies = result["fallacies"]
        self.assertEqual(len(fallacies), 3)
        
        fallacy_types = [f.get("fallacy_type") for f in fallacies]
        self.assertIn("anecdote_personnelle", fallacy_types)
        self.assertIn("généralisation_hâtive", fallacy_types)
        self.assertIn("ad_hominem", fallacy_types)
        
        # Vérifier la catégorisation des sophismes
        if "categories" in result:
            categories = result["categories"]
            self.assertIsInstance(categories, dict)
            # Au moins une catégorie devrait contenir des sophismes
            total_categorized = sum(len(v) for v in categories.values())
            self.assertGreater(total_categorized, 0)
        
        # Vérifier l'analyse contextuelle (elle devrait être appelée avec un contexte)
        contextual_analysis = result["contextual_analysis"]
        if contextual_analysis:  # Si l'analyse contextuelle a été effectuée
            self.assertIn("context_type", contextual_analysis)
            self.assertEqual(contextual_analysis["context_type"], "medical_misinformation")
            self.assertIn("risk_level", contextual_analysis)
            self.assertEqual(contextual_analysis["risk_level"], "high")
        else:
            # Si l'analyse contextuelle n'a pas été effectuée, vérifier qu'elle est vide
            self.assertEqual(contextual_analysis, {})


if __name__ == "__main__":
    pytest.main(["-v", __file__])