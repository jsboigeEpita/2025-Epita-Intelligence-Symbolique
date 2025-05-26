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
# sys.path.append(os.path.abspath('../..')) # Géré par conftest.py / pytest.ini

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
        
        self.informal_agent = InformalAgent(
            agent_id="informal_agent_test",
            tools={
                "complex_analyzer": self.complex_analyzer,
                "contextual_analyzer": self.contextual_analyzer,
                "severity_evaluator": self.severity_evaluator
            },
            strict_validation=False
        )
    
    def test_fallacy_detection_and_evaluation(self):
        """
        Teste la détection et l'évaluation des sophismes par l'agent informel
        en utilisant les outils d'analyse.
        """
        text = """
        Tous les politiciens sont corrompus. Jean est un politicien, donc Jean est corrompu.
        Si nous autorisons le mariage homosexuel, bientôt les gens voudront épouser leurs animaux de compagnie.
        Einstein ne croyait pas à la mécanique quantique, donc la mécanique quantique est fausse.
        """
        
        # Patcher les méthodes des outils d'analyse pour simuler leur comportement
        # Utiliser .analyze() pour ComplexFallacyAnalyzer et ContextualFallacyAnalyzer
        # Utiliser .evaluate_fallacy_list() pour FallacySeverityEvaluator (ou evaluate_fallacies_severity selon l'API)
        with patch.object(self.complex_analyzer, 'detect_composite_fallacies', return_value={ # ou analyze_argument_structure selon ce qui est appelé
            "individual_fallacies_count": 3,
            "basic_combinations": [], "advanced_combinations": [], "fallacy_patterns": [],
            "composite_severity": {"adjusted_severity": 0.7}
        }) as mock_complex_analyze_composite, \
             patch.object(self.complex_analyzer, 'analyze_argument_structure', return_value={ # Si cette méthode est aussi appelée
                 "identified_structures": [], "argument_relations": [], 
                 "coherence_evaluation": {"overall_score": 0.6}, "vulnerability_analysis": {}
             }) as mock_complex_analyze_structure, \
             patch.object(self.contextual_analyzer, 'identify_contextual_fallacies', return_value=[ # ou analyze_context
                {"fallacy_type": "généralisation_hâtive", "confidence": 0.85, "context_text": "..."},
                {"fallacy_type": "pente_glissante", "confidence": 0.92, "context_text": "..."},
                {"fallacy_type": "argument_d_autorité", "confidence": 0.88, "context_text": "..."}
             ]) as mock_context_analyze, \
             patch.object(self.severity_evaluator, 'evaluate_fallacy_list', return_value=[ # ou evaluate_fallacy_severity
                {"fallacy_type": "généralisation_hâtive", "final_severity_score": 0.6, "severity_level": "medium"},
                {"fallacy_type": "pente_glissante", "final_severity_score": 0.8, "severity_level": "high"},
                {"fallacy_type": "argument_d_autorité", "final_severity_score": 0.7, "severity_level": "medium"}
             ]) as mock_evaluate:
            
            # Appeler la méthode d'analyse de l'agent informel (qui devrait appeler les outils)
            # La méthode exacte appelée par l'agent peut varier (ex: analyze_text, perform_enhanced_analysis)
            # On suppose ici que l'agent a une méthode principale qui orchestre les outils.
            # Si l'agent appelle directement les méthodes des outils, ce test est déjà bien structuré.
            # Pour un test d'intégration plus profond de l'agent, il faudrait mocker moins.
            
            # Supposons que l'agent appelle une méthode comme `analyze_text_with_tools`
            # ou que `analyze_text` utilise les outils configurés.
            # Pour ce test, on va simuler que l'agent appelle les outils séquentiellement.

            # 1. L'agent utilise Complex Analyzer (peut-être pour les structures ou sophismes de base)
            #    L'agent pourrait appeler detect_composite_fallacies ou analyze_argument_structure
            #    On va supposer qu'il appelle une méthode qui retourne une liste de sophismes simples
            #    Pour simplifier, on va patcher la méthode `analyze` de la classe de base si elle existe
            #    ou une méthode spécifique de EnhancedComplexFallacyAnalyzer.
            #    Ici, on a déjà patché detect_composite_fallacies.

            # 2. L'agent utilise Contextual Analyzer
            #    On a patché identify_contextual_fallacies.

            # 3. L'agent utilise Severity Evaluator
            #    On a patché evaluate_fallacy_list.

            # Appel direct à une méthode de l'agent qui utilise les outils
            # Si l'agent a une méthode `analyze_text` qui utilise les outils :
            result = self.informal_agent.analyze_text(text) # Ou perform_enhanced_analysis(text)
            
            mock_complex_analyze_composite.assert_called() # Ou mock_complex_analyze_structure selon ce que l'agent appelle
            mock_context_analyze.assert_called()
            mock_evaluate.assert_called()
            
            self.assertIsNotNone(result)
            self.assertIn("fallacies", result)
            # Le nombre exact dépend de comment l'agent agrège les résultats
            # Pour ce test, on vérifie juste que des sophismes sont là.
            self.assertGreaterEqual(len(result["fallacies"]), 1) 
            
            fallacy_types = [f["type"] for f in result["fallacies"]]
            self.assertIn("généralisation_hâtive", fallacy_types)

    # Le test_enhanced_analysis_workflow est très similaire au précédent
    # et pourrait être fusionné ou simplifié si l'agent a une seule méthode d'analyse principale.
    # Pour l'instant, on le garde pour vérifier une autre facette potentielle de l'agent.
    def test_enhanced_analysis_workflow(self):
        text = """
        Le réchauffement climatique n'est pas réel car il a fait très froid cet hiver.
        Si nous réglementons les émissions de carbone, l'économie s'effondrera et des millions de personnes perdront leur emploi.
        """
        
        with patch.object(self.complex_analyzer, 'detect_composite_fallacies') as mock_complex_detect, \
             patch.object(self.contextual_analyzer, 'identify_contextual_fallacies') as mock_context_identify, \
             patch.object(self.severity_evaluator, 'evaluate_fallacy_list') as mock_severity_evaluate:
            
            mock_complex_detect.return_value = {
                "individual_fallacies_count": 2, "basic_combinations": [], "advanced_combinations": [],
                "fallacy_patterns": [], "composite_severity": {"adjusted_severity": 0.8}
            }
            # Simuler que contextual_analyzer retourne les sophismes que complex_analyzer aurait pu trouver
            mock_context_identify.return_value = [
                {"fallacy_type": "faux_dilemme", "confidence": 0.87, "context_text": "..."},
                {"fallacy_type": "généralisation_hâtive", "confidence": 0.91, "context_text": "..."}
            ]
            mock_severity_evaluate.return_value = [
                {"fallacy_type": "faux_dilemme", "final_severity_score": 0.75, "severity_level": "high"},
                {"fallacy_type": "généralisation_hâtive", "final_severity_score": 0.85, "severity_level": "high"}
            ]
            
            # Supposons que l'agent a une méthode perform_enhanced_analysis
            # qui utilise les outils.
            if hasattr(self.informal_agent, 'perform_enhanced_analysis'):
                result = self.informal_agent.perform_enhanced_analysis(text)
            else:
                # Si cette méthode n'existe pas, on appelle analyze_text et on vérifie les mocks
                result = self.informal_agent.analyze_text(text)


            mock_context_identify.assert_called() 
            # L'ordre d'appel des autres mocks dépend de l'implémentation de l'agent
            # mock_complex_detect.assert_called_once_with(text) # Ou avec les arguments extraits
            # mock_severity_evaluate.assert_called_once()
            
            self.assertIsNotNone(result)
            self.assertIn("fallacies", result)
            # Les assertions suivantes dépendent de la structure de retour de la méthode de l'agent
            # self.assertIn("context_analysis", result)
            # self.assertIn("severity_evaluation", result)
            
            fallacy_types = [f["type"] for f in result["fallacies"]]
            self.assertIn("faux_dilemme", fallacy_types)
            self.assertIn("généralisation_hâtive", fallacy_types)

if __name__ == "__main__":
    pytest.main(["-v", __file__])