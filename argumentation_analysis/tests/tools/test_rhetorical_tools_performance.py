#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests de performance pour les outils d'analyse rhétorique améliorés.

Ce module contient les tests de performance pour évaluer l'efficacité des outils
d'analyse rhétorique améliorés par rapport aux outils originaux.
"""

import os
import sys
import unittest
import json
import time
import tempfile
import statistics
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Importer les outils d'analyse rhétorique originaux
from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator import FallacySeverityEvaluator
from argumentation_analysis.agents.tools.analysis.rhetorical_result_analyzer import RhetoricalResultAnalyzer
from argumentation_analysis.agents.tools.analysis.rhetorical_result_visualizer import RhetoricalResultVisualizer

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


class TestRhetoricalToolsPerformance(unittest.TestCase):
    """Tests de performance pour les outils d'analyse rhétorique."""

    def setUp(self):
        """Initialise l'environnement de test."""
        # Patcher les dépendances externes pour éviter les erreurs d'importation
        self.transformers_patcher = patch('argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer.HAS_TRANSFORMERS', False)
        self.transformers_patcher.start()
        
        self.matplotlib_patcher = patch('argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_visualizer.plt')
        self.matplotlib_patcher.start()
        
        self.networkx_patcher = patch('argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_visualizer.nx')
        self.networkx_patcher.start()
        
        # Initialiser les outils d'analyse rhétorique originaux
        self.complex_fallacy_analyzer = ComplexFallacyAnalyzer()
        self.contextual_fallacy_analyzer = ContextualFallacyAnalyzer()
        self.fallacy_severity_evaluator = FallacySeverityEvaluator()
        self.rhetorical_result_analyzer = RhetoricalResultAnalyzer()
        self.rhetorical_result_visualizer = RhetoricalResultVisualizer()
        
        # Initialiser les outils d'analyse rhétorique améliorés
        self.enhanced_complex_fallacy_analyzer = EnhancedComplexFallacyAnalyzer()
        self.enhanced_contextual_fallacy_analyzer = EnhancedContextualFallacyAnalyzer()
        self.enhanced_fallacy_severity_evaluator = EnhancedFallacySeverityEvaluator()
        self.enhanced_rhetorical_result_analyzer = EnhancedRhetoricalResultAnalyzer()
        self.enhanced_rhetorical_result_visualizer = EnhancedRhetoricalResultVisualizer()
        
        # Initialiser les nouveaux outils d'analyse rhétorique
        self.semantic_argument_analyzer = SemanticArgumentAnalyzer()
        self.contextual_fallacy_detector = ContextualFallacyDetector()
        self.argument_coherence_evaluator = ArgumentCoherenceEvaluator()
        self.argument_structure_visualizer = ArgumentStructureVisualizer()
        
        # Jeu de données de test
        self.test_datasets = {
            "simple": [
                "Le réchauffement climatique est un problème mondial urgent.",
                "Les émissions de gaz à effet de serre contribuent significativement au réchauffement climatique.",
                "Nous devons réduire nos émissions de carbone pour lutter contre le réchauffement climatique.",
                "Les énergies renouvelables sont une alternative viable aux combustibles fossiles."
            ],
            "complex": [
                "Le réchauffement climatique est un mythe créé par les scientifiques pour obtenir des financements.",
                "Regardez, il a neigé l'hiver dernier, ce qui prouve que le climat ne se réchauffe pas.",
                "De plus, des milliers de scientifiques ont signé une pétition contre cette théorie.",
                "Si nous réduisons les émissions de carbone, l'économie s'effondrera et des millions de personnes perdront leur emploi.",
                "Voulez-vous être responsable de la misère de tant de familles?",
                "Les écologistes sont des extrémistes qui veulent nous ramener à l'âge de pierre."
            ],
            "mixed": [
                "Le réchauffement climatique est un problème sérieux, mais certains scientifiques exagèrent ses effets.",
                "Les données montrent une augmentation de la température mondiale, mais les modèles climatiques ne sont pas parfaits.",
                "Nous devons réduire nos émissions de carbone, mais pas au détriment de l'économie.",
                "Les énergies renouvelables sont prometteuses, mais elles ne sont pas encore assez développées pour remplacer complètement les combustibles fossiles.",
                "Les politiques environnementales doivent être équilibrées et tenir compte des réalités économiques et sociales."
            ]
        }
        
        self.test_contexts = ["politique", "scientifique", "commercial", "général"]
        
        # Nombre d'exécutions pour les tests de performance
        self.num_runs = 3

    def tearDown(self):
        """Nettoie l'environnement de test."""
        self.transformers_patcher.stop()
        self.matplotlib_patcher.stop()
        self.networkx_patcher.stop()

    def test_complex_fallacy_analyzer_performance(self):
        """Teste la performance de l'analyseur de sophismes complexes amélioré par rapport à l'original."""
        results = {
            "original": {
                "execution_times": [],
                "fallacy_counts": [],
                "composite_fallacy_counts": []
            },
            "enhanced": {
                "execution_times": [],
                "fallacy_counts": [],
                "composite_fallacy_counts": []
            }
        }
        
        # Tester avec différents jeux de données et contextes
        for dataset_name, dataset in self.test_datasets.items():
            for context in self.test_contexts:
                print(f"Testing complex fallacy analyzer with dataset '{dataset_name}' in context '{context}'...")
                
                # Tester l'analyseur original
                for _ in range(self.num_runs):
                    start_time = time.time()
                    original_result = self.complex_fallacy_analyzer.detect_composite_fallacies(dataset, context)
                    execution_time = time.time() - start_time
                    
                    results["original"]["execution_times"].append(execution_time)
                    results["original"]["fallacy_counts"].append(original_result.get("individual_fallacies_count", 0))
                    results["original"]["composite_fallacy_counts"].append(len(original_result.get("composite_fallacies", [])))
                
                # Tester l'analyseur amélioré
                for _ in range(self.num_runs):
                    start_time = time.time()
                    enhanced_result = self.enhanced_complex_fallacy_analyzer.detect_composite_fallacies(dataset, context)
                    execution_time = time.time() - start_time
                    
                    results["enhanced"]["execution_times"].append(execution_time)
                    results["enhanced"]["fallacy_counts"].append(enhanced_result.get("individual_fallacies_count", 0))
                    results["enhanced"]["composite_fallacy_counts"].append(
                        len(enhanced_result.get("basic_combinations", [])) + 
                        len(enhanced_result.get("advanced_combinations", []))
                    )
        
        # Calculer les métriques de performance
        performance_metrics = {
            "original": {
                "avg_execution_time": statistics.mean(results["original"]["execution_times"]),
                "avg_fallacy_count": statistics.mean(results["original"]["fallacy_counts"]),
                "avg_composite_fallacy_count": statistics.mean(results["original"]["composite_fallacy_counts"])
            },
            "enhanced": {
                "avg_execution_time": statistics.mean(results["enhanced"]["execution_times"]),
                "avg_fallacy_count": statistics.mean(results["enhanced"]["fallacy_counts"]),
                "avg_composite_fallacy_count": statistics.mean(results["enhanced"]["composite_fallacy_counts"])
            }
        }
        
        # Calculer les améliorations
        improvements = {
            "execution_time_improvement": 1 - (performance_metrics["enhanced"]["avg_execution_time"] / 
                                             performance_metrics["original"]["avg_execution_time"]),
            "fallacy_detection_improvement": (performance_metrics["enhanced"]["avg_fallacy_count"] / 
                                            performance_metrics["original"]["avg_fallacy_count"]) - 1,
            "composite_fallacy_detection_improvement": (performance_metrics["enhanced"]["avg_composite_fallacy_count"] / 
                                                     performance_metrics["original"]["avg_composite_fallacy_count"]) - 1
        }
        
        # Afficher les résultats
        print("\nComplex Fallacy Analyzer Performance Results:")
        print(f"Original - Avg Execution Time: {performance_metrics['original']['avg_execution_time']:.4f}s")
        print(f"Enhanced - Avg Execution Time: {performance_metrics['enhanced']['avg_execution_time']:.4f}s")
        print(f"Execution Time Improvement: {improvements['execution_time_improvement']*100:.2f}%")
        print(f"Original - Avg Fallacy Count: {performance_metrics['original']['avg_fallacy_count']:.2f}")
        print(f"Enhanced - Avg Fallacy Count: {performance_metrics['enhanced']['avg_fallacy_count']:.2f}")
        print(f"Fallacy Detection Improvement: {improvements['fallacy_detection_improvement']*100:.2f}%")
        print(f"Original - Avg Composite Fallacy Count: {performance_metrics['original']['avg_composite_fallacy_count']:.2f}")
        print(f"Enhanced - Avg Composite Fallacy Count: {performance_metrics['enhanced']['avg_composite_fallacy_count']:.2f}")
        print(f"Composite Fallacy Detection Improvement: {improvements['composite_fallacy_detection_improvement']*100:.2f}%")
        
        # Vérifier que l'analyseur amélioré détecte plus de sophismes
        self.assertGreaterEqual(
            performance_metrics["enhanced"]["avg_fallacy_count"],
            performance_metrics["original"]["avg_fallacy_count"]
        )
        
        # Vérifier que l'analyseur amélioré détecte plus de sophismes composés
        self.assertGreaterEqual(
            performance_metrics["enhanced"]["avg_composite_fallacy_count"],
            performance_metrics["original"]["avg_composite_fallacy_count"]
        )

    def test_contextual_fallacy_analyzer_performance(self):
        """Teste la performance de l'analyseur de sophismes contextuels amélioré par rapport à l'original."""
        results = {
            "original": {
                "execution_times": [],
                "fallacy_counts": [],
                "context_relevance_scores": []
            },
            "enhanced": {
                "execution_times": [],
                "fallacy_counts": [],
                "context_relevance_scores": []
            }
        }
        
        # Tester avec différents jeux de données et contextes
        for dataset_name, dataset in self.test_datasets.items():
            for context in self.test_contexts:
                print(f"Testing contextual fallacy analyzer with dataset '{dataset_name}' in context '{context}'...")
                
                # Tester l'analyseur original avec chaque argument
                for argument in dataset:
                    # Tester l'analyseur original
                    for _ in range(self.num_runs):
                        start_time = time.time()
                        original_result = self.contextual_fallacy_analyzer.analyze_context(argument, context)
                        execution_time = time.time() - start_time
                        
                        results["original"]["execution_times"].append(execution_time)
                        results["original"]["fallacy_counts"].append(len(original_result.get("contextual_fallacies", [])))
                        results["original"]["context_relevance_scores"].append(
                            original_result.get("context_analysis", {}).get("confidence", 0.5)
                        )
                    
                    # Tester l'analyseur amélioré
                    for _ in range(self.num_runs):
                        start_time = time.time()
                        enhanced_result = self.enhanced_contextual_fallacy_analyzer.analyze_context(argument, context)
                        execution_time = time.time() - start_time
                        
                        results["enhanced"]["execution_times"].append(execution_time)
                        results["enhanced"]["fallacy_counts"].append(len(enhanced_result.get("contextual_fallacies", [])))
                        results["enhanced"]["context_relevance_scores"].append(
                            enhanced_result.get("context_analysis", {}).get("confidence", 0.5)
                        )
        
        # Calculer les métriques de performance
        performance_metrics = {
            "original": {
                "avg_execution_time": statistics.mean(results["original"]["execution_times"]),
                "avg_fallacy_count": statistics.mean(results["original"]["fallacy_counts"]),
                "avg_context_relevance": statistics.mean(results["original"]["context_relevance_scores"])
            },
            "enhanced": {
                "avg_execution_time": statistics.mean(results["enhanced"]["execution_times"]),
                "avg_fallacy_count": statistics.mean(results["enhanced"]["fallacy_counts"]),
                "avg_context_relevance": statistics.mean(results["enhanced"]["context_relevance_scores"])
            }
        }
        
        # Calculer les améliorations
        improvements = {
            "execution_time_improvement": 1 - (performance_metrics["enhanced"]["avg_execution_time"] / 
                                             performance_metrics["original"]["avg_execution_time"]),
            "fallacy_detection_improvement": (performance_metrics["enhanced"]["avg_fallacy_count"] / 
                                            max(1, performance_metrics["original"]["avg_fallacy_count"])) - 1,
            "context_relevance_improvement": (performance_metrics["enhanced"]["avg_context_relevance"] / 
                                           performance_metrics["original"]["avg_context_relevance"]) - 1
        }
        
        # Afficher les résultats
        print("\nContextual Fallacy Analyzer Performance Results:")
        print(f"Original - Avg Execution Time: {performance_metrics['original']['avg_execution_time']:.4f}s")
        print(f"Enhanced - Avg Execution Time: {performance_metrics['enhanced']['avg_execution_time']:.4f}s")
        print(f"Execution Time Improvement: {improvements['execution_time_improvement']*100:.2f}%")
        print(f"Original - Avg Fallacy Count: {performance_metrics['original']['avg_fallacy_count']:.2f}")
        print(f"Enhanced - Avg Fallacy Count: {performance_metrics['enhanced']['avg_fallacy_count']:.2f}")
        print(f"Fallacy Detection Improvement: {improvements['fallacy_detection_improvement']*100:.2f}%")
        print(f"Original - Avg Context Relevance: {performance_metrics['original']['avg_context_relevance']:.2f}")
        print(f"Enhanced - Avg Context Relevance: {performance_metrics['enhanced']['avg_context_relevance']:.2f}")
        print(f"Context Relevance Improvement: {improvements['context_relevance_improvement']*100:.2f}%")
        
        # Vérifier que l'analyseur amélioré a une meilleure pertinence contextuelle
        self.assertGreaterEqual(
            performance_metrics["enhanced"]["avg_context_relevance"],
            performance_metrics["original"]["avg_context_relevance"]
        )

    def test_fallacy_severity_evaluator_performance(self):
        """Teste la performance de l'évaluateur de gravité des sophismes amélioré par rapport à l'original."""
        results = {
            "original": {
                "execution_times": [],
                "severity_scores": [],
                "context_sensitivity_scores": []
            },
            "enhanced": {
                "execution_times": [],
                "severity_scores": [],
                "context_sensitivity_scores": []
            }
        }
        
        # Créer des sophismes pour le test
        test_fallacies = [
            {
                "fallacy_type": "Appel à l'autorité",
                "context_text": "Les experts affirment que ce produit est sûr.",
                "confidence": 0.7
            },
            {
                "fallacy_type": "Appel à la popularité",
                "context_text": "Des millions de personnes utilisent ce produit.",
                "confidence": 0.6
            },
            {
                "fallacy_type": "Appel à la peur",
                "context_text": "Si vous n'utilisez pas ce produit, vous risquez de graves problèmes.",
                "confidence": 0.8
            }
        ]
        
        # Tester avec différents contextes
        for context in self.test_contexts:
            print(f"Testing fallacy severity evaluator in context '{context}'...")
            
            # Tester l'évaluateur original
            for _ in range(self.num_runs):
                start_time = time.time()
                original_result = self.fallacy_severity_evaluator.evaluate_fallacy_list(test_fallacies, context)
                execution_time = time.time() - start_time
                
                results["original"]["execution_times"].append(execution_time)
                results["original"]["severity_scores"].append(original_result.get("overall_severity", 0.5))
                
                # Calculer la sensibilité au contexte (différence entre les évaluations de différents sophismes)
                severity_variations = []
                for eval in original_result.get("fallacy_evaluations", []):
                    severity_variations.append(eval.get("final_severity", 0.5))
                
                if severity_variations:
                    context_sensitivity = statistics.stdev(severity_variations)
                    results["original"]["context_sensitivity_scores"].append(context_sensitivity)
            
            # Tester l'évaluateur amélioré
            for _ in range(self.num_runs):
                start_time = time.time()
                enhanced_result = self.enhanced_fallacy_severity_evaluator.evaluate_fallacy_list(test_fallacies, context)
                execution_time = time.time() - start_time
                
                results["enhanced"]["execution_times"].append(execution_time)
                results["enhanced"]["severity_scores"].append(enhanced_result.get("overall_severity", 0.5))
                
                # Calculer la sensibilité au contexte (différence entre les évaluations de différents sophismes)
                severity_variations = []
                for eval in enhanced_result.get("fallacy_evaluations", []):
                    severity_variations.append(eval.get("final_severity", 0.5))
                
                if severity_variations:
                    context_sensitivity = statistics.stdev(severity_variations)
                    results["enhanced"]["context_sensitivity_scores"].append(context_sensitivity)
        
        # Calculer les métriques de performance
        performance_metrics = {
            "original": {
                "avg_execution_time": statistics.mean(results["original"]["execution_times"]),
                "avg_severity_score": statistics.mean(results["original"]["severity_scores"]),
                "avg_context_sensitivity": statistics.mean(results["original"]["context_sensitivity_scores"])
            },
            "enhanced": {
                "avg_execution_time": statistics.mean(results["enhanced"]["execution_times"]),
                "avg_severity_score": statistics.mean(results["enhanced"]["severity_scores"]),
                "avg_context_sensitivity": statistics.mean(results["enhanced"]["context_sensitivity_scores"])
            }
        }
        
        # Calculer les améliorations
        improvements = {
            "execution_time_improvement": 1 - (performance_metrics["enhanced"]["avg_execution_time"] / 
                                             performance_metrics["original"]["avg_execution_time"]),
            "severity_evaluation_improvement": (performance_metrics["enhanced"]["avg_severity_score"] / 
                                              performance_metrics["original"]["avg_severity_score"]) - 1,
            "context_sensitivity_improvement": (performance_metrics["enhanced"]["avg_context_sensitivity"] / 
                                              performance_metrics["original"]["avg_context_sensitivity"]) - 1
        }
        
        # Afficher les résultats
        print("\nFallacy Severity Evaluator Performance Results:")
        print(f"Original - Avg Execution Time: {performance_metrics['original']['avg_execution_time']:.4f}s")
        print(f"Enhanced - Avg Execution Time: {performance_metrics['enhanced']['avg_execution_time']:.4f}s")
        print(f"Execution Time Improvement: {improvements['execution_time_improvement']*100:.2f}%")
        print(f"Original - Avg Severity Score: {performance_metrics['original']['avg_severity_score']:.2f}")
        print(f"Enhanced - Avg Severity Score: {performance_metrics['enhanced']['avg_severity_score']:.2f}")
        print(f"Severity Evaluation Improvement: {improvements['severity_evaluation_improvement']*100:.2f}%")
        print(f"Original - Avg Context Sensitivity: {performance_metrics['original']['avg_context_sensitivity']:.2f}")
        print(f"Enhanced - Avg Context Sensitivity: {performance_metrics['enhanced']['avg_context_sensitivity']:.2f}")
        print(f"Context Sensitivity Improvement: {improvements['context_sensitivity_improvement']*100:.2f}%")
        
        # Vérifier que l'évaluateur amélioré a une meilleure sensibilité au contexte
        self.assertGreaterEqual(
            performance_metrics["enhanced"]["avg_context_sensitivity"],
            performance_metrics["original"]["avg_context_sensitivity"]
        )

    def test_new_tools_performance(self):
        """Teste la performance des nouveaux outils d'analyse rhétorique."""
        results = {
            "semantic_argument_analyzer": {
                "execution_times": [],
                "thematic_coherence_scores": []
            },
            "contextual_fallacy_detector": {
                "execution_times": [],
                "fallacy_counts": []
            },
            "argument_coherence_evaluator": {
                "execution_times": [],
                "coherence_scores": []
            },
            "argument_structure_visualizer": {
                "execution_times": []
            }
        }
        
        # Tester avec différents jeux de données et contextes
        for dataset_name, dataset in self.test_datasets.items():
            for context in self.test_contexts:
                print(f"Testing new tools with dataset '{dataset_name}' in context '{context}'...")
                
                # Tester l'analyseur d'arguments sémantiques
                for _ in range(self.num_runs):
                    start_time = time.time()
                    semantic_result = self.semantic_argument_analyzer.analyze_multiple_arguments(dataset)
                    execution_time = time.time() - start_time
                    
                    results["semantic_argument_analyzer"]["execution_times"].append(execution_time)
                    results["semantic_argument_analyzer"]["thematic_coherence_scores"].append(
                        semantic_result.get("thematic_coherence", {}).get("coherence_score", 0.5)
                    )
                
                # Tester le détecteur de sophismes contextuels
                for _ in range(self.num_runs):
                    start_time = time.time()
                    detector_result = self.contextual_fallacy_detector.detect_multiple_contextual_fallacies(dataset, context)
                    execution_time = time.time() - start_time
                    
                    results["contextual_fallacy_detector"]["execution_times"].append(execution_time)
                    # La structure de retour de detect_multiple_contextual_fallacies est différente
                    # Elle contient une liste "argument_results", chacun ayant "detected_fallacies"
                    total_fallacies_in_dataset = 0
                    if "argument_results" in detector_result:
                        for arg_res in detector_result["argument_results"]:
                            total_fallacies_in_dataset += len(arg_res.get("detected_fallacies", []))
                    results["contextual_fallacy_detector"]["fallacy_counts"].append(total_fallacies_in_dataset)
                
                # Tester l'évaluateur de cohérence d'arguments
                for _ in range(self.num_runs):
                    start_time = time.time()
                    coherence_result = self.argument_coherence_evaluator.evaluate_coherence(dataset, context)
                    execution_time = time.time() - start_time
    
                    results["argument_coherence_evaluator"]["execution_times"].append(execution_time)
                    results["argument_coherence_evaluator"]["coherence_scores"].append(
                        coherence_result.get("overall_coherence", 0.5)
                    )
                
                # Tester le visualiseur de structure d'arguments
                with tempfile.TemporaryDirectory() as temp_dir:
                    output_dir = Path(temp_dir)
                    
                    for _ in range(self.num_runs):
                        start_time = time.time()
                        self.argument_structure_visualizer.visualize_argument_structure(
                            dataset, context, "json", output_dir=str(output_dir)
                        )
                        execution_time = time.time() - start_time
                        
                        results["argument_structure_visualizer"]["execution_times"].append(execution_time)
        
        # Calculer les métriques de performance
        performance_metrics = {
            "semantic_argument_analyzer": {
                "avg_execution_time": statistics.mean(results["semantic_argument_analyzer"]["execution_times"]),
                "avg_thematic_coherence": statistics.mean(results["semantic_argument_analyzer"]["thematic_coherence_scores"])
            },
            "contextual_fallacy_detector": {
                "avg_execution_time": statistics.mean(results["contextual_fallacy_detector"]["execution_times"]),
                "avg_fallacy_count": statistics.mean(results["contextual_fallacy_detector"]["fallacy_counts"])
            },
            "argument_coherence_evaluator": {
                "avg_execution_time": statistics.mean(results["argument_coherence_evaluator"]["execution_times"]),
                "avg_coherence_score": statistics.mean(results["argument_coherence_evaluator"]["coherence_scores"])
            },
            "argument_structure_visualizer": {
                "avg_execution_time": statistics.mean(results["argument_structure_visualizer"]["execution_times"])
            }
        }
        
        # Afficher les résultats
        print("\nNew Tools Performance Results:")
        print(f"Semantic Argument Analyzer - Avg Execution Time: {performance_metrics['semantic_argument_analyzer']['avg_execution_time']:.4f}s")
        print(f"Semantic Argument Analyzer - Avg Thematic Coherence: {performance_metrics['semantic_argument_analyzer']['avg_thematic_coherence']:.2f}")
        print(f"Contextual Fallacy Detector - Avg Execution Time: {performance_metrics['contextual_fallacy_detector']['avg_execution_time']:.4f}s")
        print(f"Contextual Fallacy Detector - Avg Fallacy Count: {performance_metrics['contextual_fallacy_detector']['avg_fallacy_count']:.2f}")
        print(f"Argument Coherence Evaluator - Avg Execution Time: {performance_metrics['argument_coherence_evaluator']['avg_execution_time']:.4f}s")
        print(f"Argument Coherence Evaluator - Avg Coherence Score: {performance_metrics['argument_coherence_evaluator']['avg_coherence_score']:.2f}")
        print(f"Argument Structure Visualizer - Avg Execution Time: {performance_metrics['argument_structure_visualizer']['avg_execution_time']:.4f}s")
        
        # Vérifier que les nouveaux outils ont des temps d'exécution raisonnables
        self.assertLess(performance_metrics["semantic_argument_analyzer"]["avg_execution_time"], 5.0)
        self.assertLess(performance_metrics["contextual_fallacy_detector"]["avg_execution_time"], 5.0)
        self.assertLess(performance_metrics["argument_coherence_evaluator"]["avg_execution_time"], 5.0)
        self.assertLess(performance_metrics["argument_structure_visualizer"]["avg_execution_time"], 5.0)


if __name__ == "__main__":
    unittest.main()