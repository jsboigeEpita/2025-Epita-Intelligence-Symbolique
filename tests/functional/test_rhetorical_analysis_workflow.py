#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests fonctionnels pour le flux de travail d'analyse rhétorique.

Ce module teste le flux de travail complet d'analyse rhétorique,
de l'extraction du texte à la génération du rapport d'analyse.
"""

import unittest
import sys
import os
import pytest
from unittest.mock import MagicMock, patch
import logging
import json
from pathlib import Path

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestRhetoricalAnalysisWorkflow")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
# sys.path.append(os.path.abspath('../..')) # Géré par conftest.py / pytest.ini

# Import des modules à tester
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TacticalCoordinator as TaskCoordinator 
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer as ComplexFallacyAnalyzer
from argumentation_analysis.core.communication import MessageMiddleware # Corrigé
from argumentation_analysis.orchestration.analysis_runner import AnalysisRunner as RhetoricalAnalysisRunner # Corrigé et alias


class TestRhetoricalAnalysisWorkflow(unittest.TestCase):
    """Tests fonctionnels pour le flux de travail d'analyse rhétorique."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.middleware = MessageMiddleware()
        
        # Créer et enregistrer les canaux nécessaires
        from argumentation_analysis.core.communication.channel_interface import LocalChannel, ChannelType
        
        # Canal hiérarchique pour les communications tactiques
        self.hierarchical_channel = LocalChannel("hierarchical", self.middleware)
        self.hierarchical_channel.type = ChannelType.HIERARCHICAL
        self.middleware.register_channel(self.hierarchical_channel)
        
        # Autres canaux nécessaires
        self.data_channel = LocalChannel("data", self.middleware)
        self.data_channel.type = ChannelType.DATA
        self.middleware.register_channel(self.data_channel)
        
        self.tactical_state = TacticalState()
        self.coordinator = TaskCoordinator(tactical_state=self.tactical_state, middleware=self.middleware)
        
        self.extract_adapter = MagicMock(spec=ExtractAgentAdapter)
        self.extract_adapter.agent_id = "extract_agent" 
        
        self.complex_analyzer = ComplexFallacyAnalyzer()
        
        self.informal_agent = MagicMock(spec=InformalAgent)
        self.informal_agent.agent_id = "informal_agent"
        
        self.analysis_runner = RhetoricalAnalysisRunner()
        
        os.makedirs("results/test", exist_ok=True)
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # self.middleware.shutdown() # Si applicable

    @patch('argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.ExtractAgentAdapter') # Patcher la classe où elle est définie
    @patch('argumentation_analysis.agents.core.informal.informal_agent.InformalAgent') # Patcher la classe où elle est définie
    def test_complete_rhetorical_analysis_workflow(self, MockInformalAgent, MockExtractAgentAdapter):
        """
        Teste le flux de travail complet d'analyse rhétorique,
        de l'extraction du texte à la génération du rapport d'analyse.
        """
        mock_extract_adapter_instance = MockExtractAgentAdapter.return_value
        mock_informal_agent_instance = MockInformalAgent.return_value

        example_file = "examples/exemple_sophisme.txt"
        self.assertTrue(os.path.exists(example_file), f"Le fichier d'exemple {example_file} n'existe pas")
        
        example_content = """
        Le réchauffement climatique est un mythe car il a neigé cet hiver.
        Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.
        Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées.
        """
        
        mock_extract_adapter_instance.extract_text_from_file = MagicMock(return_value=example_content)
        
        mock_informal_agent_instance.analyze_text = MagicMock(return_value={
            "fallacies": [
                {"type": "généralisation_hâtive", "text": "Le réchauffement climatique est un mythe car il a neigé cet hiver", "confidence": 0.92},
                {"type": "faux_dilemme", "text": "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans", "confidence": 0.85},
                {"type": "ad_hominem", "text": "Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées", "confidence": 0.88}
            ],
            "analysis_metadata": {"timestamp": "2025-05-21T23:30:00", "agent_id": "informal_agent", "version": "1.0"}
        })
        
        with patch('argumentation_analysis.orchestration.analysis_runner.generate_report', return_value="rapport_test.json") as mock_generate:
            
            # Assurer que le runner utilise les instances mockées
            # Cela peut nécessiter de patcher comment le runner obtient ses agents
            # ou de passer les mocks au constructeur du runner si possible.
            # Pour ce test, on assume que le runner est configuré pour utiliser les instances mockées
            # ou que les patchs au niveau du module suffisent.
            # Si le runner crée ses propres instances, il faudrait patcher les constructeurs comme fait plus haut.
            
            # Si RhetoricalAnalysisRunner instancie ses propres agents, il faut s'assurer que ces instances sont nos mocks.
            # Une façon est de patcher les classes au niveau du module où RhetoricalAnalysisRunner les importe.
            # Par exemple, si RhetoricalAnalysisRunner fait:
            # from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
            # alors @patch('argumentation_analysis.orchestration.analysis_runner.InformalAgent') serait nécessaire.
            # Ici, on a déjà patché les classes au niveau du module de test, ce qui devrait fonctionner si le runner
            # les importe depuis le même scope.

            # Pour ce test, on va supposer que le runner est déjà configuré avec les mocks
            # ou que les patchs au niveau du module sont suffisants.
            # Si le runner crée ses propres instances, il faut patcher les constructeurs.
            # Ici, on a patché les classes elles-mêmes, donc les instances créées par le runner seront des mocks.

            # On doit s'assurer que le runner utilise les instances mockées.
            # Si le runner a des méthodes pour enregistrer des agents, on les utilise.
            # Sinon, on patche les méthodes de setup d'agent dans le runner.
            with patch.object(self.analysis_runner, '_get_agent_instance') as mock_get_agent:
                def side_effect_get_agent(agent_type, **kwargs):
                    if agent_type == "informal":
                        return mock_informal_agent_instance
                    elif agent_type == "extract": # Supposant un type "extract"
                        return mock_extract_adapter_instance
                    raise ValueError(f"Type d'agent non mocké: {agent_type}")
                mock_get_agent.side_effect = side_effect_get_agent

                result_file = self.analysis_runner.run_analysis(
                    input_file=example_file,
                    output_dir="results/test",
                    agent_type="informal", 
                    analysis_type="fallacy"
                )
            
            mock_extract_adapter_instance.extract_text_from_file.assert_called_once_with(example_file)
            mock_informal_agent_instance.analyze_text.assert_called_once()
            mock_generate.assert_called_once()
            
            self.assertIsNotNone(result_file)
            self.assertTrue(result_file.endswith(".json"))
    
    @patch('argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.ExtractAgentAdapter')
    @patch('argumentation_analysis.agents.core.informal.informal_agent.InformalAgent')
    def test_multi_document_analysis(self, MockInformalAgent, MockExtractAgentAdapter):
        mock_extract_adapter_instance = MockExtractAgentAdapter.return_value
        mock_informal_agent_instance = MockInformalAgent.return_value

        temp_dir = "examples/temp_multi_rhet" 
        os.makedirs(temp_dir, exist_ok=True)
        
        example_files = [os.path.join(temp_dir, f"exemple{i}.txt") for i in range(1,4)]
        example_contents = [
            "Texte 1 avec sophisme A.",
            "Texte 2 avec sophisme B.",
            "Texte 3 sans sophisme évident."
        ]
        
        for file, content in zip(example_files, example_contents):
            with open(file, 'w', encoding='utf-8') as f:
                f.write(content)
        
        try:
            mock_extract_adapter_instance.extract_text_from_file = MagicMock(side_effect=example_contents)
            mock_informal_agent_instance.analyze_text = MagicMock(return_value={
                "fallacies": [{"type": "sophisme_test", "text": "texte_test", "confidence": 0.8}],
                "analysis_metadata": {"timestamp": "2025-05-21T23:30:00"}
            })
            
            with patch('argumentation_analysis.orchestration.analysis_runner.generate_report', return_value="rapport_multi.json") as mock_generate, \
                 patch.object(self.analysis_runner, '_get_agent_instance') as mock_get_agent:
                
                def side_effect_get_agent(agent_type, **kwargs):
                    if agent_type == "informal": return mock_informal_agent_instance
                    elif agent_type == "extract": return mock_extract_adapter_instance
                    raise ValueError(f"Type d'agent non mocké: {agent_type}")
                mock_get_agent.side_effect = side_effect_get_agent
                
                result_file = self.analysis_runner.run_multi_document_analysis(
                    input_files=example_files,
                    output_dir="results/test",
                    agent_type="informal",
                    analysis_type="fallacy"
                )
                
                self.assertEqual(mock_extract_adapter_instance.extract_text_from_file.call_count, len(example_files))
                self.assertEqual(mock_informal_agent_instance.analyze_text.call_count, len(example_files))
                mock_generate.assert_called_once()
                
                self.assertIsNotNone(result_file)
                self.assertTrue(result_file.endswith(".json"))
        
        finally:
            for file in example_files:
                if os.path.exists(file): os.remove(file)
            if os.path.exists(temp_dir) and not os.listdir(temp_dir): os.rmdir(temp_dir)


if __name__ == "__main__":
    pytest.main(["-v", __file__])