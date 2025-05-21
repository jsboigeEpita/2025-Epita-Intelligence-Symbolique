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
sys.path.append(os.path.abspath('../..'))

# Import des modules à tester
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import ComplexFallacyAnalyzer
from argumentation_analysis.orchestration.message_middleware import MessageMiddleware
from argumentation_analysis.orchestration.analysis_runner import RhetoricalAnalysisRunner


class TestRhetoricalAnalysisWorkflow(unittest.TestCase):
    """Tests fonctionnels pour le flux de travail d'analyse rhétorique."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un middleware
        self.middleware = MessageMiddleware()
        
        # Créer un état tactique
        self.tactical_state = TacticalState()
        
        # Créer le coordinateur tactique
        self.coordinator = TaskCoordinator(tactical_state=self.tactical_state, middleware=self.middleware)
        
        # Créer l'adaptateur d'extraction
        self.extract_adapter = ExtractAgentAdapter(agent_id="extract_agent", middleware=self.middleware)
        
        # Créer l'analyseur de sophismes complexes
        self.complex_analyzer = ComplexFallacyAnalyzer()
        
        # Créer l'agent informel
        self.informal_agent = InformalAgent(
            agent_id="informal_agent",
            tools={"complex_analyzer": self.complex_analyzer}
        )
        
        # Créer le runner d'analyse rhétorique
        self.analysis_runner = RhetoricalAnalysisRunner(middleware=self.middleware)
        
        # Initialiser les protocoles de communication
        self.middleware.initialize_protocols()
        
        # Créer le répertoire de résultats si nécessaire
        os.makedirs("results/test", exist_ok=True)
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter le middleware
        self.middleware.shutdown()
    
    def test_complete_rhetorical_analysis_workflow(self):
        """
        Teste le flux de travail complet d'analyse rhétorique,
        de l'extraction du texte à la génération du rapport d'analyse.
        """
        # Chemin du fichier d'exemple
        example_file = "examples/exemple_sophisme.txt"
        
        # Vérifier que le fichier existe
        self.assertTrue(os.path.exists(example_file), f"Le fichier d'exemple {example_file} n'existe pas")
        
        # Contenu d'exemple pour le fichier
        example_content = """
        Le réchauffement climatique est un mythe car il a neigé cet hiver.
        Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.
        Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées.
        """
        
        # Patcher la méthode d'extraction pour simuler la lecture du fichier
        with patch.object(self.extract_adapter, 'extract_text_from_file', return_value=example_content) as mock_extract:
            # Patcher la méthode d'analyse de l'agent informel
            with patch.object(self.informal_agent, 'analyze_text', return_value={
                "fallacies": [
                    {"type": "généralisation_hâtive", "text": "Le réchauffement climatique est un mythe car il a neigé cet hiver", "confidence": 0.92},
                    {"type": "faux_dilemme", "text": "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans", "confidence": 0.85},
                    {"type": "ad_hominem", "text": "Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées", "confidence": 0.88}
                ],
                "analysis_metadata": {
                    "timestamp": "2025-05-21T23:30:00",
                    "agent_id": "informal_agent",
                    "version": "1.0"
                }
            }) as mock_analyze:
                # Patcher la méthode de génération de rapport
                with patch('argumentation_analysis.orchestration.analysis_runner.generate_report', return_value="rapport_test.json") as mock_generate:
                    
                    # Exécuter le flux de travail d'analyse rhétorique
                    result_file = self.analysis_runner.run_analysis(
                        input_file=example_file,
                        output_dir="results/test",
                        agent_type="informal",
                        analysis_type="fallacy"
                    )
                    
                    # Vérifier que les méthodes ont été appelées
                    mock_extract.assert_called_once_with(example_file)
                    mock_analyze.assert_called_once()
                    mock_generate.assert_called_once()
                    
                    # Vérifier le résultat
                    self.assertIsNotNone(result_file)
                    self.assertTrue(result_file.endswith(".json"))
    
    def test_rhetorical_analysis_with_real_dependencies(self):
        """
        Teste le flux de travail d'analyse rhétorique avec les dépendances réelles
        (sans mocks pour les bibliothèques numpy, pandas, jpype).
        
        Note: Ce test nécessite que les dépendances soient correctement installées
        selon les instructions dans README_RESOLUTION_DEPENDANCES.md.
        """
        # Vérifier si les dépendances sont disponibles
        try:
            import numpy
            import pandas
            has_dependencies = True
        except ImportError:
            has_dependencies = False
            logger.warning("Les dépendances numpy et pandas ne sont pas disponibles. Le test sera ignoré.")
        
        if has_dependencies:
            # Chemin du fichier d'exemple
            example_file = "examples/exemple_sophisme.txt"
            
            # Vérifier que le fichier existe
            self.assertTrue(os.path.exists(example_file), f"Le fichier d'exemple {example_file} n'existe pas")
            
            # Créer un contenu d'exemple si le fichier n'existe pas ou est vide
            if not os.path.exists(example_file) or os.path.getsize(example_file) == 0:
                example_content = """
                Le réchauffement climatique est un mythe car il a neigé cet hiver.
                Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.
                Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées.
                """
                with open(example_file, 'w', encoding='utf-8') as f:
                    f.write(example_content)
            
            # Exécuter le flux de travail d'analyse rhétorique avec les dépendances réelles
            try:
                # Patcher uniquement la méthode de génération de rapport pour éviter d'écrire des fichiers
                with patch('argumentation_analysis.orchestration.analysis_runner.generate_report', return_value="rapport_test.json"):
                    
                    result_file = self.analysis_runner.run_analysis(
                        input_file=example_file,
                        output_dir="results/test",
                        agent_type="informal",
                        analysis_type="fallacy"
                    )
                    
                    # Vérifier le résultat
                    self.assertIsNotNone(result_file)
                    self.assertTrue(result_file.endswith(".json"))
            
            except Exception as e:
                logger.error(f"Erreur lors de l'exécution du test avec dépendances réelles: {e}")
                self.fail(f"Le test a échoué avec l'erreur: {e}")
        else:
            # Ignorer le test si les dépendances ne sont pas disponibles
            self.skipTest("Les dépendances numpy et pandas ne sont pas disponibles")
    
    def test_multi_document_analysis(self):
        """
        Teste l'analyse rhétorique sur plusieurs documents.
        """
        # Créer des fichiers d'exemple temporaires
        temp_dir = "examples/temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        example_files = [
            os.path.join(temp_dir, "exemple1.txt"),
            os.path.join(temp_dir, "exemple2.txt"),
            os.path.join(temp_dir, "exemple3.txt")
        ]
        
        example_contents = [
            "Le réchauffement climatique est un mythe car il a neigé cet hiver.",
            "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.",
            "Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées."
        ]
        
        # Créer les fichiers temporaires
        for file, content in zip(example_files, example_contents):
            with open(file, 'w', encoding='utf-8') as f:
                f.write(content)
        
        try:
            # Patcher les méthodes nécessaires
            with patch.object(self.extract_adapter, 'extract_text_from_file', side_effect=example_contents) as mock_extract:
                with patch.object(self.informal_agent, 'analyze_text', return_value={
                    "fallacies": [{"type": "sophisme", "text": "texte", "confidence": 0.8}],
                    "analysis_metadata": {"timestamp": "2025-05-21T23:30:00"}
                }) as mock_analyze:
                    with patch('argumentation_analysis.orchestration.analysis_runner.generate_report', return_value="rapport_multi.json") as mock_generate:
                        
                        # Exécuter l'analyse sur plusieurs documents
                        result_file = self.analysis_runner.run_multi_document_analysis(
                            input_files=example_files,
                            output_dir="results/test",
                            agent_type="informal",
                            analysis_type="fallacy"
                        )
                        
                        # Vérifier que les méthodes ont été appelées pour chaque fichier
                        self.assertEqual(mock_extract.call_count, len(example_files))
                        self.assertEqual(mock_analyze.call_count, len(example_files))
                        mock_generate.assert_called_once()
                        
                        # Vérifier le résultat
                        self.assertIsNotNone(result_file)
                        self.assertTrue(result_file.endswith(".json"))
        
        finally:
            # Nettoyer les fichiers temporaires
            for file in example_files:
                if os.path.exists(file):
                    os.remove(file)
            
            # Supprimer le répertoire temporaire s'il est vide
            if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                os.rmdir(temp_dir)


if __name__ == "__main__":
    pytest.main(["-v", __file__])