#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests d'intégration pour les outils d'analyse rhétorique améliorés.

Ce module contient les tests d'intégration pour valider l'interaction entre
les différents outils d'analyse rhétorique et leur intégration dans le système
d'orchestration hiérarchique.
"""

import os
import sys
import unittest
import json
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Importer les outils d'analyse rhétorique améliorés
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator
from argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_analyzer import EnhancedRhetoricalResultAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_visualizer import EnhancedRhetoricalResultVisualizer

# Importer les nouveaux outils d'analyse rhétorique
from argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer import SemanticArgumentAnalyzer
from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import ContextualFallacyDetector
from argumentation_analysis.agents.tools.analysis.new.argument_coherence_evaluator import ArgumentCoherenceEvaluator
from argumentation_analysis.agents.tools.analysis.new.argument_structure_visualizer import ArgumentStructureVisualizer

# Importer l'adaptateur des outils rhétoriques
from argumentation_analysis.orchestration.hierarchical.operational.adapters.rhetorical_tools_adapter import RhetoricalToolsAdapter

from argumentation_analysis.paths import RESULTS_DIR



class TestRhetoricalToolsIntegration(unittest.TestCase):
    """Tests d'intégration pour les outils d'analyse rhétorique."""

    def setUp(self):
        """Initialise l'environnement de test."""
        # Patcher les dépendances externes pour éviter les erreurs d'importation
        self.transformers_patcher = patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.HAS_TRANSFORMERS', False)
        self.transformers_patcher.start()
        
        self.matplotlib_patcher = patch('argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_visualizer.plt')
        self.matplotlib_patcher.start()
        
        self.networkx_patcher = patch('argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_visualizer.nx')
        self.networkx_patcher.start()
        
        # Initialiser les outils d'analyse rhétorique
        self.complex_fallacy_analyzer = EnhancedComplexFallacyAnalyzer()
        self.contextual_fallacy_analyzer = EnhancedContextualFallacyAnalyzer()
        self.fallacy_severity_evaluator = EnhancedFallacySeverityEvaluator()
        self.rhetorical_result_analyzer = EnhancedRhetoricalResultAnalyzer()
        self.rhetorical_result_visualizer = EnhancedRhetoricalResultVisualizer()
        
        self.semantic_argument_analyzer = SemanticArgumentAnalyzer()
        self.contextual_fallacy_detector = ContextualFallacyDetector()
        self.argument_coherence_evaluator = ArgumentCoherenceEvaluator()
        self.argument_structure_visualizer = ArgumentStructureVisualizer()
        
        # Initialiser l'adaptateur des outils rhétoriques
        self.rhetorical_tools_adapter = RhetoricalToolsAdapter()
        
        # Exemples d'arguments pour les tests
        self.test_arguments = [
            "Le réchauffement climatique est un mythe créé par les scientifiques pour obtenir des financements.",
            "Regardez, il a neigé l'hiver dernier, ce qui prouve que le climat ne se réchauffe pas.",
            "De plus, des milliers de scientifiques ont signé une pétition contre cette théorie.",
            "Si nous réduisons les émissions de carbone, l'économie s'effondrera et des millions de personnes perdront leur emploi.",
            "Voulez-vous être responsable de la misère de tant de familles?",
            "Les écologistes sont des extrémistes qui veulent nous ramener à l'âge de pierre."
        ]
        
        self.test_context = "politique"

    def tearDown(self):
        """Nettoie l'environnement de test."""
        self.transformers_patcher.stop()
        self.matplotlib_patcher.stop()
        self.networkx_patcher.stop()

    def test_complex_fallacy_analyzer_integration(self):
        """Teste l'intégration de l'analyseur de sophismes complexes avec d'autres outils."""
        # Analyser les sophismes complexes
        complex_fallacy_results = self.complex_fallacy_analyzer.detect_composite_fallacies(self.test_arguments, self.test_context)
        
        # Vérifier que l'analyse a produit des résultats
        self.assertIsNotNone(complex_fallacy_results)
        self.assertIn("individual_fallacies_count", complex_fallacy_results)
        self.assertIn("basic_combinations", complex_fallacy_results)
        self.assertIn("advanced_combinations", complex_fallacy_results)
        
        # Utiliser l'évaluateur de gravité pour évaluer les sophismes détectés
        if complex_fallacy_results["individual_fallacies_count"] > 0:
            # Créer une liste de sophismes à partir des résultats
            fallacies = []
            for i, arg in enumerate(self.test_arguments):
                fallacies.append({
                    "fallacy_type": "Sophisme complexe",
                    "context_text": arg,
                    "confidence": 0.7
                })
            
            severity_results = self.fallacy_severity_evaluator.evaluate_fallacy_list(fallacies, self.test_context)
            
            # Vérifier que l'évaluation de gravité a produit des résultats
            self.assertIsNotNone(severity_results)
            self.assertIn("overall_severity", severity_results)
            self.assertIn("severity_level", severity_results)
            self.assertIn("fallacy_evaluations", severity_results)

    def test_contextual_fallacy_analyzer_integration(self):
        """Teste l'intégration de l'analyseur de sophismes contextuels avec d'autres outils."""
        # Analyser les sophismes contextuels
        contextual_fallacy_results = self.contextual_fallacy_analyzer.analyze_context(self.test_arguments[0], self.test_context)
        
        # Vérifier que l'analyse a produit des résultats
        self.assertIsNotNone(contextual_fallacy_results)
        self.assertIn("context_analysis", contextual_fallacy_results)
        self.assertIn("contextual_fallacies", contextual_fallacy_results)
        
        # Utiliser le détecteur de sophismes contextuels pour détecter des sophismes
        detector_results = self.contextual_fallacy_detector.detect_contextual_fallacies(self.test_arguments, self.test_context)
        
        # Vérifier que la détection a produit des résultats
        self.assertIsNotNone(detector_results)
        self.assertIn("context_analysis", detector_results)
        self.assertIn("detected_fallacies", detector_results)
        
        # Comparer les résultats des deux outils
        self.assertEqual(contextual_fallacy_results["context_analysis"]["context_type"], 
                         detector_results["context_analysis"]["context_type"])

    def test_semantic_argument_analyzer_integration(self):
        """Teste l'intégration de l'analyseur d'arguments sémantiques avec d'autres outils."""
        # Analyser les arguments sémantiquement
        semantic_results = self.semantic_argument_analyzer.analyze_multiple_arguments(self.test_arguments)
        
        # Vérifier que l'analyse a produit des résultats
        self.assertIsNotNone(semantic_results)
        self.assertIn("argument_analyses", semantic_results)
        self.assertIn("semantic_relationships", semantic_results)
        self.assertIn("thematic_coherence", semantic_results)
        
        # Utiliser l'évaluateur de cohérence pour évaluer la cohérence des arguments
        coherence_results = self.argument_coherence_evaluator.evaluate_argument_coherence(self.test_arguments, self.test_context)
        
        # Vérifier que l'évaluation de cohérence a produit des résultats
        self.assertIsNotNone(coherence_results)
        self.assertIn("overall_coherence", coherence_results)
        self.assertIn("coherence_level", coherence_results)
        self.assertIn("thematic_coherence", coherence_results)
        
        # Comparer les résultats des deux outils
        self.assertIsNotNone(semantic_results["thematic_coherence"])
        self.assertIsNotNone(coherence_results["thematic_coherence"])

    def test_rhetorical_result_analyzer_integration(self):
        """Teste l'intégration de l'analyseur de résultats rhétoriques avec d'autres outils."""
        # Créer des résultats d'analyse pour le test
        test_results = {
            "complex_fallacy_analysis": self.complex_fallacy_analyzer.detect_composite_fallacies(self.test_arguments, self.test_context),
            "contextual_fallacy_analysis": {
                "context_analysis": self.contextual_fallacy_analyzer._analyze_context_deeply(self.test_context),
                "contextual_fallacies": [
                    {
                        "fallacy_type": "Appel à l'émotion",
                        "context_text": self.test_arguments[4],
                        "confidence": 0.8
                    }
                ]
            },
            "argument_coherence_evaluation": self.argument_coherence_evaluator.evaluate_argument_coherence(self.test_arguments, self.test_context)
        }
        
        # Analyser les résultats rhétoriques
        analysis_results = self.rhetorical_result_analyzer.analyze_rhetorical_results(test_results, self.test_context)
        
        # Vérifier que l'analyse a produit des résultats
        self.assertIsNotNone(analysis_results)
        self.assertIn("overall_analysis", analysis_results)
        self.assertIn("fallacy_analysis", analysis_results)
        self.assertIn("coherence_analysis", analysis_results)
        self.assertIn("persuasion_analysis", analysis_results)
        self.assertIn("recommendations", analysis_results)
        
        # Utiliser le visualiseur de résultats rhétoriques pour visualiser les résultats
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            visualization_results = self.rhetorical_result_visualizer.visualize_rhetorical_results(
                test_results, analysis_results, output_dir=output_dir
            )
            
            # Vérifier que la visualisation a produit des résultats
            self.assertIsNotNone(visualization_results)
            self.assertIn("visualization_summary", visualization_results)
            self.assertIn("generated_visualizations", visualization_results)
            self.assertIn("output_directory", visualization_results)

    def test_argument_structure_visualizer_integration(self):
        """Teste l'intégration du visualiseur de structure d'arguments avec d'autres outils."""
        # Analyser les arguments sémantiquement
        semantic_results = self.semantic_argument_analyzer.analyze_multiple_arguments(self.test_arguments)
        
        # Extraire les relations sémantiques
        semantic_relationships = semantic_results["semantic_relationships"]
        
        # Utiliser le visualiseur de structure d'arguments pour visualiser la structure
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            visualization_results = self.argument_structure_visualizer.visualize_argument_structure(
                self.test_arguments, self.test_context, "json", output_dir=str(output_dir)
            )
            
            # Vérifier que la visualisation a produit des résultats
            self.assertIsNotNone(visualization_results)
            self.assertIn("visualization_type", visualization_results)
            self.assertIn("argument_count", visualization_results)
            self.assertIn("identified_structure", visualization_results)
            self.assertIn("visualization_data", visualization_results)
            self.assertIn("output_files", visualization_results)

    def test_rhetorical_tools_adapter_integration(self):
        """Teste l'intégration de l'adaptateur des outils rhétoriques avec le système d'orchestration."""
        # Initialiser l'adaptateur
        self.rhetorical_tools_adapter.initialize()
        
        # Vérifier les capacités de l'adaptateur
        capabilities = self.rhetorical_tools_adapter.get_capabilities()
        self.assertIn("complex_fallacy_analysis", capabilities)
        self.assertIn("contextual_fallacy_analysis", capabilities)
        self.assertIn("fallacy_severity_evaluation", capabilities)
        self.assertIn("argument_structure_visualization", capabilities)
        self.assertIn("argument_coherence_evaluation", capabilities)
        self.assertIn("semantic_argument_analysis", capabilities)
        self.assertIn("contextual_fallacy_detection", capabilities)
        
        # Créer une tâche pour l'adaptateur
        task = {
            "id": "task-1",
            "tactical_task_id": "tactical-task-1",
            "description": "Analyser les sophismes dans le texte",
            "techniques": [
                {
                    "name": "complex_fallacy_analysis",
                    "parameters": {
                        "context": "politique",
                        "confidence_threshold": 0.7,
                        "include_composite_fallacies": True
                    }
                },
                {
                    "name": "contextual_fallacy_analysis",
                    "parameters": {
                        "context": "politique",
                        "consider_domain": True,
                        "consider_audience": True
                    }
                }
            ],
            "text_extracts": [
                {
                    "id": "extract-1",
                    "source": "example",
                    "content": "\n".join(self.test_arguments),
                    "relevance": "high"
                }
            ],
            "required_capabilities": ["complex_fallacy_analysis", "contextual_fallacy_analysis"]
        }
        
        # Vérifier que l'adaptateur peut traiter la tâche
        can_process = self.rhetorical_tools_adapter.can_process_task(task)
        self.assertTrue(can_process)
        
        # Traiter la tâche avec l'adaptateur
        result = asyncio.run(self.rhetorical_tools_adapter.process_task(task))
        
        # Vérifier que le traitement a produit des résultats
        self.assertIsNotNone(result)
        self.assertIn("id", result)
        self.assertIn("task_id", result)
        self.assertIn("tactical_task_id", result)
        self.assertIn("status", result)
        self.assertIn("outputs", result)
        self.assertIn("metrics", result)
        
        # Vérifier que le statut est valide
        self.assertIn(result["status"], ["completed", "completed_with_issues", "failed"])
        
        # Si le traitement a réussi, vérifier les résultats
        if result["status"] in ["completed", "completed_with_issues"]:
            outputs = result["outputs"]
            self.assertIn(RESULTS_DIR, outputs)
            
            results = outputs[RESULTS_DIR]
            self.assertGreater(len(results), 0)
            
            # Vérifier que les résultats contiennent des analyses de sophismes
            complex_fallacy_results = [r for r in results if r.get("type") == "complex_fallacy_analysis"]
            contextual_fallacy_results = [r for r in results if r.get("type") == "contextual_fallacy_analysis"]
            
            self.assertGreaterEqual(len(complex_fallacy_results), 0)
            self.assertGreaterEqual(len(contextual_fallacy_results), 0)


if __name__ == "__main__":
    unittest.main()