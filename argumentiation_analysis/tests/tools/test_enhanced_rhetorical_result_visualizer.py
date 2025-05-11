#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests pour le visualiseur de résultats rhétoriques amélioré.

Ce module contient les tests unitaires pour la classe EnhancedRhetoricalResultVisualizer.
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

from argumentiation_analysis.agents.tools.analysis.enhanced.rhetorical_result_visualizer import EnhancedRhetoricalResultVisualizer


class TestEnhancedRhetoricalResultVisualizer(unittest.TestCase):
    """Tests pour la classe EnhancedRhetoricalResultVisualizer."""

    def setUp(self):
        """Initialise l'environnement de test."""
        # Patcher les dépendances externes pour éviter les erreurs d'importation
        self.matplotlib_patcher = patch('argumentiation_analysis.agents.tools.analysis.enhanced.rhetorical_result_visualizer.plt')
        self.matplotlib_mock = self.matplotlib_patcher.start()
        
        self.networkx_patcher = patch('argumentiation_analysis.agents.tools.analysis.enhanced.rhetorical_result_visualizer.nx')
        self.networkx_mock = self.networkx_patcher.start()
        
        self.visualizer = EnhancedRhetoricalResultVisualizer()
        
        # Exemple de résultats d'analyse rhétorique pour les tests
        self.test_results = {
            "complex_fallacy_analysis": {
                "individual_fallacies_count": 5,
                "basic_combinations": [
                    {
                        "combination_name": "Appel à l'autorité + Appel à la popularité",
                        "description": "Combinaison d'appel à l'autorité et d'appel à la popularité",
                        "severity": 0.7,
                        "severity_level": "Élevé"
                    }
                ],
                "advanced_combinations": [
                    {
                        "combination_name": "cascade_émotionnelle",
                        "description": "Combinaison d'appels à l'émotion qui s'intensifient progressivement",
                        "components": ["Appel à l'émotion", "Appel à la peur", "Appel à la pitié"],
                        "pattern": "escalation",
                        "pattern_match_score": 0.8,
                        "severity": 0.8,
                        "severity_level": "Élevé"
                    }
                ],
                "fallacy_patterns": [
                    {
                        "pattern_name": "escalade_émotionnelle",
                        "description": "Escalade progressive d'appels à l'émotion",
                        "confidence": 0.7,
                        "severity": 0.7
                    }
                ],
                "composite_severity": {
                    "basic_severity": 0.6,
                    "advanced_severity": 0.8,
                    "pattern_severity": 0.7,
                    "composite_severity": 0.7,
                    "context_modifier": 0.1,
                    "adjusted_severity": 0.8,
                    "severity_level": "Élevé"
                },
                "context": "politique",
                "analysis_timestamp": datetime.now().isoformat()
            },
            "contextual_fallacy_analysis": {
                "context_analysis": {
                    "context_type": "politique",
                    "context_subtypes": ["électoral"],
                    "audience_characteristics": ["généraliste"],
                    "formality_level": "moyen",
                    "confidence": 0.8
                },
                "potential_fallacies_count": 8,
                "contextual_fallacies_count": 5,
                "contextual_fallacies": [
                    {
                        "fallacy_type": "Appel à l'émotion",
                        "keyword": "peur",
                        "context_text": "Si nous ne faisons pas ce choix, nous risquons de graves conséquences.",
                        "confidence": 0.8,
                        "contextual_relevance": "Élevée",
                        "context_adjustment": 0.2
                    },
                    {
                        "fallacy_type": "Ad hominem",
                        "keyword": "attaque personnelle",
                        "context_text": "Mon adversaire n'a pas l'expérience nécessaire pour diriger.",
                        "confidence": 0.7,
                        "contextual_relevance": "Élevée",
                        "context_adjustment": 0.3
                    }
                ],
                "fallacy_relations": [
                    {
                        "relation_type": "complementary",
                        "fallacy1_type": "Appel à l'émotion",
                        "fallacy2_type": "Appel à la peur",
                        "explanation": "Les sophismes 'Appel à l'émotion' et 'Appel à la peur' se renforcent mutuellement",
                        "strength": 0.7
                    }
                ],
                "analysis_timestamp": datetime.now().isoformat()
            },
            "argument_coherence_evaluation": {
                "coherence_score": 0.6,
                "coherence_level": "Modéré",
                "thematic_clusters": [
                    {
                        "cluster_id": 0,
                        "arguments": [0, 1, 2]
                    },
                    {
                        "cluster_id": 1,
                        "arguments": [3, 4]
                    }
                ],
                "logical_flows": [
                    {
                        "flow_id": 0,
                        "source_argument": 0,
                        "target_argument": 1,
                        "relation_type": "support",
                        "confidence": 0.8
                    }
                ],
                "analysis_timestamp": datetime.now().isoformat()
            }
        }
        
        # Exemple de résultats d'analyse rhétorique globale pour les tests
        self.test_analysis_results = {
            "overall_analysis": {
                "rhetorical_quality": 0.6,
                "rhetorical_quality_level": "Modéré",
                "main_strengths": ["Appel émotionnel fort", "Structure thématique cohérente"],
                "main_weaknesses": ["Utilisation excessive de sophismes", "Manque de support logique"],
                "context_relevance": "Élevée"
            },
            "fallacy_analysis": {
                "total_fallacies": 5,
                "fallacy_types_distribution": {
                    "Appel à l'émotion": 2,
                    "Ad hominem": 1,
                    "Appel à la peur": 1,
                    "Appel à l'autorité": 1
                },
                "most_common_fallacies": ["Appel à l'émotion"],
                "most_severe_fallacies": ["Appel à la peur"],
                "composite_fallacies": 2,
                "overall_severity": 0.7,
                "severity_level": "Élevé"
            },
            "coherence_analysis": {
                "overall_coherence": 0.6,
                "coherence_level": "Modéré",
                "thematic_coherence": 0.7,
                "logical_coherence": 0.5,
                "structure_quality": 0.6,
                "main_coherence_issues": ["Transitions thématiques abruptes", "Lacunes logiques"]
            },
            "persuasion_analysis": {
                "persuasion_score": 0.65,
                "persuasion_level": "Modéré",
                "emotional_appeal": 0.8,
                "logical_appeal": 0.5,
                "credibility_appeal": 0.6,
                "context_appropriateness": 0.7,
                "audience_alignment": 0.7
            },
            "recommendations": {
                "general_recommendations": [
                    "Réduire l'utilisation de sophismes, en particulier les appels à l'émotion",
                    "Renforcer le support logique des arguments"
                ],
                "fallacy_recommendations": [
                    "Éviter les attaques ad hominem",
                    "Remplacer les appels à la peur par des arguments basés sur des faits"
                ],
                "coherence_recommendations": [
                    "Améliorer les transitions entre les thèmes",
                    "Combler les lacunes logiques entre les arguments"
                ],
                "persuasion_recommendations": [
                    "Équilibrer les appels émotionnels et logiques",
                    "Renforcer la crédibilité par des sources fiables"
                ],
                "context_specific_recommendations": [
                    "Adapter le discours au contexte politique électoral",
                    "Considérer les attentes de l'audience généraliste"
                ]
            },
            "analysis_timestamp": datetime.now().isoformat()
        }

    def tearDown(self):
        """Nettoie l'environnement de test."""
        self.matplotlib_patcher.stop()
        self.networkx_patcher.stop()

    def test_initialization(self):
        """Teste l'initialisation du visualiseur."""
        self.assertIsNotNone(self.visualizer)
        self.assertEqual(len(self.visualizer.visualization_history), 0)

    def test_visualize_rhetorical_results(self):
        """Teste la méthode visualize_rhetorical_results."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Appeler la méthode avec le répertoire temporaire
            result = self.visualizer.visualize_rhetorical_results(
                self.test_results,
                self.test_analysis_results,
                output_dir=output_dir
            )
            
            # Vérifier la structure du résultat
            self.assertIn("visualization_summary", result)
            self.assertIn("generated_visualizations", result)
            self.assertIn("output_directory", result)
            
            # Vérifier que des visualisations ont été générées
            self.assertGreater(len(result["generated_visualizations"]), 0)
            
            # Vérifier que l'historique de visualisation a été mis à jour
            self.assertEqual(len(self.visualizer.visualization_history), 1)
            self.assertEqual(self.visualizer.visualization_history[0]["type"], "rhetorical_results_visualization")

    def test_create_fallacy_distribution_chart(self):
        """Teste la méthode _create_fallacy_distribution_chart."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_path = output_dir / "fallacy_distribution.png"
            
            # Appeler la méthode avec le répertoire temporaire
            self.visualizer._create_fallacy_distribution_chart(
                self.test_analysis_results["fallacy_analysis"],
                output_path
            )
            
            # Vérifier que matplotlib.pyplot.savefig a été appelé
            self.matplotlib_mock.savefig.assert_called_once()

    def test_create_fallacy_severity_chart(self):
        """Teste la méthode _create_fallacy_severity_chart."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_path = output_dir / "fallacy_severity.png"
            
            # Appeler la méthode avec le répertoire temporaire
            self.visualizer._create_fallacy_severity_chart(
                self.test_analysis_results["fallacy_analysis"],
                output_path
            )
            
            # Vérifier que matplotlib.pyplot.savefig a été appelé
            self.matplotlib_mock.savefig.assert_called_once()

    def test_create_coherence_radar_chart(self):
        """Teste la méthode _create_coherence_radar_chart."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_path = output_dir / "coherence_radar.png"
            
            # Appeler la méthode avec le répertoire temporaire
            self.visualizer._create_coherence_radar_chart(
                self.test_analysis_results["coherence_analysis"],
                output_path
            )
            
            # Vérifier que matplotlib.pyplot.savefig a été appelé
            self.matplotlib_mock.savefig.assert_called_once()

    def test_create_persuasion_radar_chart(self):
        """Teste la méthode _create_persuasion_radar_chart."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_path = output_dir / "persuasion_radar.png"
            
            # Appeler la méthode avec le répertoire temporaire
            self.visualizer._create_persuasion_radar_chart(
                self.test_analysis_results["persuasion_analysis"],
                output_path
            )
            
            # Vérifier que matplotlib.pyplot.savefig a été appelé
            self.matplotlib_mock.savefig.assert_called_once()

    def test_create_fallacy_network_graph(self):
        """Teste la méthode _create_fallacy_network_graph."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_path = output_dir / "fallacy_network.png"
            
            # Appeler la méthode avec le répertoire temporaire
            self.visualizer._create_fallacy_network_graph(
                self.test_results["contextual_fallacy_analysis"]["contextual_fallacies"],
                self.test_results["contextual_fallacy_analysis"]["fallacy_relations"],
                output_path
            )
            
            # Vérifier que networkx.draw a été appelé
            self.networkx_mock.draw_networkx.assert_called()
            
            # Vérifier que matplotlib.pyplot.savefig a été appelé
            self.matplotlib_mock.savefig.assert_called_once()

    def test_create_argument_structure_graph(self):
        """Teste la méthode _create_argument_structure_graph."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_path = output_dir / "argument_structure.png"
            
            # Créer des arguments pour le test
            arguments = [
                "Les experts affirment que ce produit est sûr.",
                "Ce produit est utilisé par des millions de personnes.",
                "Par conséquent, vous devriez faire confiance aux experts et utiliser ce produit.",
                "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves."
            ]
            
            # Appeler la méthode avec le répertoire temporaire
            self.visualizer._create_argument_structure_graph(
                arguments,
                self.test_results["argument_coherence_evaluation"]["logical_flows"],
                output_path
            )
            
            # Vérifier que networkx.draw a été appelé
            self.networkx_mock.draw_networkx.assert_called()
            
            # Vérifier que matplotlib.pyplot.savefig a été appelé
            self.matplotlib_mock.savefig.assert_called_once()

    def test_create_rhetorical_quality_dashboard(self):
        """Teste la méthode _create_rhetorical_quality_dashboard."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_path = output_dir / "rhetorical_quality_dashboard.png"
            
            # Appeler la méthode avec le répertoire temporaire
            self.visualizer._create_rhetorical_quality_dashboard(
                self.test_analysis_results,
                output_path
            )
            
            # Vérifier que matplotlib.pyplot.savefig a été appelé
            self.matplotlib_mock.savefig.assert_called_once()

    def test_generate_html_report(self):
        """Teste la méthode _generate_html_report."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_path = output_dir / "rhetorical_analysis_report.html"
            
            # Créer une liste de visualisations pour le test
            visualizations = [
                {"type": "fallacy_distribution", "path": "fallacy_distribution.png", "title": "Distribution des sophismes"},
                {"type": "fallacy_severity", "path": "fallacy_severity.png", "title": "Gravité des sophismes"},
                {"type": "coherence_radar", "path": "coherence_radar.png", "title": "Cohérence argumentative"},
                {"type": "persuasion_radar", "path": "persuasion_radar.png", "title": "Efficacité persuasive"}
            ]
            
            # Appeler la méthode avec le répertoire temporaire
            self.visualizer._generate_html_report(
                self.test_analysis_results,
                visualizations,
                output_path
            )
            
            # Vérifier que le fichier HTML a été créé
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()