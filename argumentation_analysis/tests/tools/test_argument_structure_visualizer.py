#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests pour le visualiseur de structure d'arguments.

Ce module contient les tests unitaires pour la classe ArgumentStructureVisualizer.
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

from argumentation_analysis.agents.tools.analysis.new.argument_structure_visualizer import ArgumentStructureVisualizer


class TestArgumentStructureVisualizer(unittest.TestCase):
    """Tests pour la classe ArgumentStructureVisualizer."""

    def setUp(self):
        """Initialise l'environnement de test."""
        # Patcher les dépendances externes pour éviter les erreurs d'importation
        self.matplotlib_patcher = patch('argumentation_analysis.agents.tools.analysis.new.argument_structure_visualizer.plt')
        self.matplotlib_mock = self.matplotlib_patcher.start()
        
        self.networkx_patcher = patch('argumentation_analysis.agents.tools.analysis.new.argument_structure_visualizer.nx')
        self.networkx_mock = self.networkx_patcher.start()
        
        self.visualizer = ArgumentStructureVisualizer()
        
        # Exemples d'arguments pour les tests
        self.test_arguments = [
            "Le réchauffement climatique est un problème mondial urgent.",
            "Les émissions de gaz à effet de serre contribuent significativement au réchauffement climatique.",
            "Nous devons réduire nos émissions de carbone pour lutter contre le réchauffement climatique.",
            "Les énergies renouvelables sont une alternative viable aux combustibles fossiles."
        ]
        
        self.test_context = "environnemental"
        
        # Exemple de relations entre arguments pour les tests
        self.test_relationships = [
            {
                "relationship_type": "support",
                "source_argument": 1,
                "target_argument": 0,
                "strength": 0.8,
                "description": "Les émissions de gaz à effet de serre soutiennent l'affirmation du réchauffement climatique"
            },
            {
                "relationship_type": "conclusion",
                "source_argument": 0,
                "target_argument": 2,
                "strength": 0.7,
                "description": "Le problème du réchauffement climatique mène à la conclusion de réduire les émissions"
            },
            {
                "relationship_type": "support",
                "source_argument": 3,
                "target_argument": 2,
                "strength": 0.6,
                "description": "Les énergies renouvelables soutiennent la réduction des émissions de carbone"
            }
        ]

    def tearDown(self):
        """Nettoie l'environnement de test."""
        self.matplotlib_patcher.stop()
        self.networkx_patcher.stop()

    def test_initialization(self):
        """Teste l'initialisation du visualiseur."""
        self.assertIsNotNone(self.visualizer)
        self.assertIsNotNone(self.visualizer.visualization_options)
        self.assertEqual(len(self.visualizer.visualization_history), 0)

    def test_visualize_argument_structure(self):
        """Teste la méthode visualize_argument_structure."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Appeler la méthode avec le répertoire temporaire
            result = self.visualizer.visualize_argument_structure(
                self.test_arguments, 
                self.test_context, 
                "json",
                output_dir=str(output_dir)
            )
            
            # Vérifier la structure du résultat
            self.assertIn("visualization_type", result)
            self.assertIn("argument_count", result)
            self.assertIn("identified_structure", result)
            self.assertIn("visualization_data", result)
            self.assertIn("output_files", result)
            self.assertIn("visualization_timestamp", result)
            
            # Vérifier que l'historique de visualisation a été mis à jour
            self.assertEqual(len(self.visualizer.visualization_history), 1)
            self.assertEqual(self.visualizer.visualization_history[0]["type"], "argument_structure_visualization")

    def test_analyze_argument_structure(self):
        """Teste la méthode _analyze_argument_structure."""
        structure = self.visualizer._analyze_argument_structure(self.test_arguments, self.test_context)
        
        # Vérifier la structure du résultat
        self.assertIn("structure_type", structure)
        self.assertIn("main_claim", structure)
        self.assertIn("supporting_arguments", structure)
        self.assertIn("opposing_arguments", structure)
        self.assertIn("neutral_arguments", structure)
        self.assertIn("argument_relationships", structure)
        
        # Vérifier que le type de structure est valide
        self.assertIn(structure["structure_type"], ["linéaire", "arborescente", "convergente", "divergente", "complexe", "mixte"])
        
        # Vérifier que des relations entre arguments ont été identifiées
        self.assertGreaterEqual(len(structure["argument_relationships"]), 0)

    def test_identify_argument_roles(self):
        """Teste la méthode _identify_argument_roles."""
        roles = self.visualizer._identify_argument_roles(self.test_arguments)
        
        # Vérifier la structure du résultat
        self.assertIn("main_claim_index", roles)
        self.assertIn("supporting_indices", roles)
        self.assertIn("opposing_indices", roles)
        self.assertIn("neutral_indices", roles)
        self.assertIn("role_confidence", roles)
        
        # Vérifier que l'indice de l'affirmation principale est valide
        self.assertGreaterEqual(roles["main_claim_index"], 0)
        self.assertLess(roles["main_claim_index"], len(self.test_arguments))
        
        # Vérifier que les indices des arguments de soutien sont valides
        for idx in roles["supporting_indices"]:
            self.assertGreaterEqual(idx, 0)
            self.assertLess(idx, len(self.test_arguments))
        
        # Vérifier que la confiance des rôles est dans les limites attendues
        self.assertGreaterEqual(roles["role_confidence"], 0.0)
        self.assertLessEqual(roles["role_confidence"], 1.0)

    def test_infer_argument_relationships(self):
        """Teste la méthode _infer_argument_relationships."""
        relationships = self.visualizer._infer_argument_relationships(self.test_arguments)
        
        # Vérifier que des relations ont été inférées
        self.assertGreaterEqual(len(relationships), 0)
        
        # Si des relations ont été inférées, vérifier leur structure
        if relationships:
            for relationship in relationships:
                self.assertIn("relationship_type", relationship)
                self.assertIn("source_argument", relationship)
                self.assertIn("target_argument", relationship)
                self.assertIn("strength", relationship)
                self.assertIn("description", relationship)
                
                # Vérifier que les indices des arguments sont valides
                self.assertGreaterEqual(relationship["source_argument"], 0)
                self.assertLess(relationship["source_argument"], len(self.test_arguments))
                self.assertGreaterEqual(relationship["target_argument"], 0)
                self.assertLess(relationship["target_argument"], len(self.test_arguments))
                
                # Vérifier que la force de la relation est dans les limites attendues
                self.assertGreaterEqual(relationship["strength"], 0.0)
                self.assertLessEqual(relationship["strength"], 1.0)

    def test_determine_structure_type(self):
        """Teste la méthode _determine_structure_type."""
        # Créer des relations pour le test
        relationships = self.test_relationships
        
        structure_type = self.visualizer._determine_structure_type(relationships, len(self.test_arguments))
        
        # Vérifier que le type de structure est valide
        self.assertIn(structure_type, ["linéaire", "arborescente", "convergente", "divergente", "complexe", "mixte"])

    def test_create_graph_visualization(self):
        """Teste la méthode _create_graph_visualization."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_path = output_dir / "argument_structure.png"
            
            # Créer une structure d'arguments pour le test
            structure = {
                "structure_type": "convergente",
                "main_claim": {"index": 0, "text": self.test_arguments[0]},
                "supporting_arguments": [
                    {"index": 1, "text": self.test_arguments[1]},
                    {"index": 3, "text": self.test_arguments[3]}
                ],
                "opposing_arguments": [],
                "neutral_arguments": [
                    {"index": 2, "text": self.test_arguments[2]}
                ],
                "argument_relationships": self.test_relationships
            }
            
            # Appeler la méthode avec le répertoire temporaire
            visualization_files = self.visualizer._create_graph_visualization(
                structure, self.test_arguments, output_dir
            )
            
            # Vérifier que des fichiers de visualisation ont été créés
            self.assertGreater(len(visualization_files), 0)
            
            # Vérifier que networkx.draw a été appelé
            self.networkx_mock.draw_networkx.assert_called()
            
            # Vérifier que matplotlib.pyplot.savefig a été appelé
            self.matplotlib_mock.savefig.assert_called()

    def test_create_json_visualization(self):
        """Teste la méthode _create_json_visualization."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Créer une structure d'arguments pour le test
            structure = {
                "structure_type": "convergente",
                "main_claim": {"index": 0, "text": self.test_arguments[0]},
                "supporting_arguments": [
                    {"index": 1, "text": self.test_arguments[1]},
                    {"index": 3, "text": self.test_arguments[3]}
                ],
                "opposing_arguments": [],
                "neutral_arguments": [
                    {"index": 2, "text": self.test_arguments[2]}
                ],
                "argument_relationships": self.test_relationships
            }
            
            # Appeler la méthode avec le répertoire temporaire
            visualization_data, visualization_files = self.visualizer._create_json_visualization(
                structure, self.test_arguments, output_dir
            )
            
            # Vérifier que des données de visualisation ont été créées
            self.assertIsNotNone(visualization_data)
            
            # Vérifier que des fichiers de visualisation ont été créés
            self.assertGreater(len(visualization_files), 0)
            
            # Vérifier que le fichier JSON a été créé
            json_file = output_dir / "argument_structure.json"
            self.assertTrue(json_file.exists())
            
            # Vérifier que le contenu du fichier JSON est valide
            with open(json_file, "r", encoding="utf-8") as f:
                json_content = json.load(f)
                self.assertIn("structure_type", json_content)
                self.assertIn("arguments", json_content)
                self.assertIn("relationships", json_content)

    def test_create_html_visualization(self):
        """Teste la méthode _create_html_visualization."""
        # Créer un répertoire temporaire pour les visualisations
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Créer une structure d'arguments pour le test
            structure = {
                "structure_type": "convergente",
                "main_claim": {"index": 0, "text": self.test_arguments[0]},
                "supporting_arguments": [
                    {"index": 1, "text": self.test_arguments[1]},
                    {"index": 3, "text": self.test_arguments[3]}
                ],
                "opposing_arguments": [],
                "neutral_arguments": [
                    {"index": 2, "text": self.test_arguments[2]}
                ],
                "argument_relationships": self.test_relationships
            }
            
            # Appeler la méthode avec le répertoire temporaire
            visualization_data, visualization_files = self.visualizer._create_html_visualization(
                structure, self.test_arguments, output_dir
            )
            
            # Vérifier que des données de visualisation ont été créées
            self.assertIsNotNone(visualization_data)
            
            # Vérifier que des fichiers de visualisation ont été créés
            self.assertGreater(len(visualization_files), 0)
            
            # Vérifier que le fichier HTML a été créé
            html_file = output_dir / "argument_structure.html"
            self.assertTrue(html_file.exists())
            
            # Vérifier que le contenu du fichier HTML est valide
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()
                self.assertIn("<!DOCTYPE html>", html_content)
                self.assertIn("<html", html_content)
                self.assertIn("<body", html_content)
                self.assertIn("</html>", html_content)

    def test_generate_text_summary(self):
        """Teste la méthode _generate_text_summary."""
        # Créer une structure d'arguments pour le test
        structure = {
            "structure_type": "convergente",
            "main_claim": {"index": 0, "text": self.test_arguments[0]},
            "supporting_arguments": [
                {"index": 1, "text": self.test_arguments[1]},
                {"index": 3, "text": self.test_arguments[3]}
            ],
            "opposing_arguments": [],
            "neutral_arguments": [
                {"index": 2, "text": self.test_arguments[2]}
            ],
            "argument_relationships": self.test_relationships
        }
        
        summary = self.visualizer._generate_text_summary(structure, self.test_arguments)
        
        # Vérifier que le résumé n'est pas vide
        self.assertIsNotNone(summary)
        self.assertGreater(len(summary), 0)
        
        # Vérifier que le résumé contient des informations sur la structure
        self.assertIn("structure", summary.lower())
        self.assertIn("convergente", summary.lower())
        
        # Vérifier que le résumé mentionne l'affirmation principale
        self.assertIn(self.test_arguments[0][:20], summary)


if __name__ == "__main__":
    unittest.main()