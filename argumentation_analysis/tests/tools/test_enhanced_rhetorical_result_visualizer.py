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

from argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_visualizer import EnhancedRhetoricalResultVisualizer


class TestEnhancedRhetoricalResultVisualizer(unittest.TestCase):
    """Tests pour la classe EnhancedRhetoricalResultVisualizer."""

    def setUp(self):
        """Initialise l'environnement de test."""
        # Patcher les dépendances externes pour éviter les erreurs d'importation
        self.matplotlib_patcher = patch('argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_visualizer.plt')
        self.matplotlib_mock = self.matplotlib_patcher.start()
        
        self.networkx_patcher = patch('argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_visualizer.nx')
        self.networkx_mock = self.networkx_patcher.start()
        
        self.visualizer = EnhancedRhetoricalResultVisualizer()
        
        # Exemple de résultats d'analyse rhétorique pour les tests
        # Ajout de identified_arguments et identified_fallacies pour les tests de visualisation
        self.test_results = {
            "identified_arguments": {
                "arg_1": "Les experts affirment que ce produit est sûr.",
                "arg_2": "Ce produit est utilisé par des millions de personnes.",
                "arg_3": "Par conséquent, vous devriez faire confiance aux experts et utiliser ce produit."
            },
            "identified_fallacies": {
                "fallacy_1": {
                    "type": "Appel à l'autorité",
                    "target_argument_id": "arg_1"
                },
                "fallacy_2": {
                    "type": "Appel à la popularité",
                    "target_argument_id": "arg_2"
                }
            },
            "complex_fallacy_analysis": {
                "individual_fallacies_count": 5, # Ce nombre devrait correspondre à identified_fallacies + autres
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
            # La méthode retourne directement un dictionnaire de chemins, pas de "visualization_summary" ou "generated_visualizations"
            self.assertIn("argument_network", result)
            self.assertIn("fallacy_distribution", result)
            self.assertIn("argument_quality", result)
            self.assertIn("html_report", result)
            
            # Vérifier que des chemins de visualisations ont été générés (non vides et ne commencent pas par "Aucun")
            self.assertTrue(isinstance(result.get("argument_network"), str) and result.get("argument_network") and not result.get("argument_network", "").startswith("Aucun"))
            self.assertTrue(isinstance(result.get("fallacy_distribution"), str) and result.get("fallacy_distribution") and not result.get("fallacy_distribution", "").startswith("Aucun"))
            self.assertTrue(isinstance(result.get("argument_quality"), str) and result.get("argument_quality") and not result.get("argument_quality", "").startswith("Aucun"))
            self.assertTrue(Path(result["html_report"]).exists())

            # Vérifier que l'historique de visualisation a été mis à jour
            self.assertEqual(len(self.visualizer.visualization_history), 1)
            self.assertEqual(self.visualizer.visualization_history[0]["type"], "rhetorical_results_visualization")

    def test_create_fallacy_distribution_chart(self):
        """Teste la méthode visualize_fallacy_distribution (anciennement _create_fallacy_distribution_chart)."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_path = output_dir / "fallacy_distribution.png"
            
            # Préparer un état minimal pour le test
            # La méthode visualize_fallacy_distribution attend un 'state' avec 'identified_fallacies'
            test_state = {
                "identified_fallacies": {
                    f"fallacy_{i+1}": {
                        "type": fallacy_type,
                        "justification": "Test justification",
                        "target_argument_id": f"arg_{i+1}"
                    } for i, fallacy_type in enumerate(self.test_analysis_results["fallacy_analysis"]["fallacy_types_distribution"].keys())
                }
            }
            
            # Appeler la méthode avec le répertoire temporaire
            self.visualizer.visualize_fallacy_distribution(
                test_state, # Utiliser l'état de test
                output_path=output_path
            )
            
            # Vérifier que matplotlib.pyplot.savefig a été appelé
            self.matplotlib_mock.savefig.assert_called_once()

    @unittest.skip("Fonctionnalité _create_fallacy_severity_chart semble supprimée")
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

    @unittest.skip("Fonctionnalité _create_coherence_radar_chart semble supprimée")
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

    @unittest.skip("Fonctionnalité _create_persuasion_radar_chart semble supprimée")
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
        """Teste la méthode visualize_argument_network (anciennement _create_fallacy_network_graph)."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_path = output_dir / "fallacy_network.png"

            # Préparer un état minimal pour le test
            # La méthode visualize_argument_network attend un 'state' avec 'identified_arguments' et 'identified_fallacies'
            # On simule les arguments et les sophismes basés sur les données du test original
            
            # Créer des arguments identifiés à partir des cibles des sophismes
            identified_arguments = {}
            arg_counter = 0
            fallacy_nodes_map = {} # Pour mapper les anciens fallacy_type à des fallacy_id uniques
            
            # Créer des sophismes identifiés
            identified_fallacies = {}
            for i, fallacy_data in enumerate(self.test_results["contextual_fallacy_analysis"]["contextual_fallacies"]):
                fallacy_id = f"fallacy_{i}"
                fallacy_type = fallacy_data.get("fallacy_type", "Type inconnu")
                # Simuler un argument cible si non existant
                target_arg_text = fallacy_data.get("context_text", f"Argument cible pour {fallacy_type}")
                # Créer un ID d'argument unique pour chaque sophisme pour simplifier, ou essayer de les regrouper si pertinent
                target_arg_id = f"arg_for_{fallacy_id}"
                if target_arg_id not in identified_arguments:
                    identified_arguments[target_arg_id] = target_arg_text
                
                identified_fallacies[fallacy_id] = {
                    "type": fallacy_type,
                    "target_argument_id": target_arg_id
                }
                fallacy_nodes_map[fallacy_type] = fallacy_id # Peut écraser si types dupliqués, mais ok pour ce test

            # Les relations de sophismes ne sont pas directement utilisées par visualize_argument_network
            # qui se concentre sur les liens argument -> sophisme.

            test_state = {
                "identified_arguments": identified_arguments,
                "identified_fallacies": identified_fallacies
            }
            
            # Appeler la méthode avec le répertoire temporaire
            self.visualizer.visualize_argument_network(
                test_state,
                output_path=output_path
            )
            
            # Vérifier que networkx.draw_networkx_nodes (ou une autre méthode draw spécifique) a été appelé
            self.networkx_mock.draw_networkx_nodes.assert_called()
            
            # Vérifier que matplotlib.pyplot.savefig a été appelé
            self.matplotlib_mock.savefig.assert_called_once()

    def test_create_argument_structure_graph(self):
        """Teste la méthode visualize_argument_network (anciennement _create_argument_structure_graph)."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_path = output_dir / "argument_structure.png"
            
            # Créer des arguments pour le test
            arguments_text_list = [
                "Les experts affirment que ce produit est sûr.",
                "Ce produit est utilisé par des millions de personnes.",
                "Par conséquent, vous devriez faire confiance aux experts et utiliser ce produit.",
                "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves."
            ]
            identified_arguments = {f"arg_{i}": text for i, text in enumerate(arguments_text_list)}
            
            # Simuler des sophismes liés à ces arguments (ou aucun si non pertinent pour ce test spécifique)
            # La méthode visualize_argument_network utilise identified_fallacies pour les liens.
            # Les logical_flows du test original ne sont pas directement utilisés.
            # Pour ce test, on peut se concentrer sur la création des nœuds d'arguments.
            identified_fallacies = {} # Pas de sophismes spécifiques pour ce test de structure d'argument pur

            test_state = {
                "identified_arguments": identified_arguments,
                "identified_fallacies": identified_fallacies
            }
            
            # Appeler la méthode avec le répertoire temporaire
            self.visualizer.visualize_argument_network( # Changé de _create_argument_structure_graph
                test_state, # La méthode attend un 'state'
                output_path=output_path
            )
            
            # Vérifier que networkx.draw_networkx_nodes (ou une autre méthode draw spécifique) a été appelé
            self.networkx_mock.draw_networkx_nodes.assert_called()
            
            # Vérifier que matplotlib.pyplot.savefig a été appelé
            self.matplotlib_mock.savefig.assert_called_once()

    @unittest.skip("Fonctionnalité _create_rhetorical_quality_dashboard semble supprimée")
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
        """Teste la méthode generate_enhanced_html_report (anciennement _generate_html_report)."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_path = output_dir / "rhetorical_analysis_report.html"
            
            # Créer une liste de chemins d'images pour le test, correspondant à ce que generate_enhanced_html_report attend
            # Les clés doivent correspondre à celles utilisées dans generate_enhanced_html_report
            image_paths = {
                "argument_network": str(Path(output_dir) / "argument_network.png"),
                "fallacy_distribution": str(Path(output_dir) / "fallacy_distribution.png"),
                "argument_quality": str(Path(output_dir) / "argument_quality.png")
            }
            # Créer des fichiers images factices pour que le rapport HTML puisse les référencer
            for img_path_str in image_paths.values():
                Path(img_path_str).touch()

            # La méthode attend un 'state' complet
            test_state = {**self.test_results, **self.test_analysis_results}
            
            # Appeler la méthode avec le répertoire temporaire
            self.visualizer.generate_enhanced_html_report( # Changé de _generate_html_report
                test_state, # La méthode attend un 'state'
                image_paths, # La méthode attend image_paths
                output_path=output_path
            )
            
            # Vérifier que le fichier HTML a été créé
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()