# -*- coding: utf-8 -*-
# tests/integration/test_notebooks_execution.py
"""
Tests d'intégration pour vérifier que les notebooks ont une structure valide.
"""

import unittest
import os
import json


class TestNotebooksStructure(unittest.TestCase):
    """Tests d'intégration pour la structure des notebooks."""
    
    def test_logic_agents_tutorial_notebook(self):
        """Test de la structure du notebook tutoriel sur les agents logiques."""
        # Chemin du notebook
        notebook_path = os.path.join('examples', 'notebooks', 'logic_agents_tutorial.ipynb')
        
        # Vérifier que le notebook existe
        self.assertTrue(os.path.exists(notebook_path), f"Le notebook {notebook_path} n'existe pas")
        
        # Vérifier que le notebook a une structure JSON valide
        try:
            with open(notebook_path, 'r', encoding='utf-8') as f:
                notebook_content = json.load(f)
            
            # Vérifier que le notebook a les attributs requis
            self.assertIn('cells', notebook_content, "Le notebook ne contient pas de cellules")
            self.assertIn('metadata', notebook_content, "Le notebook ne contient pas de métadonnées")
            self.assertIn('nbformat', notebook_content, "Le notebook ne contient pas de format")
            
            # Vérifier que le notebook contient au moins une cellule
            self.assertGreater(len(notebook_content['cells']), 0, "Le notebook ne contient aucune cellule")
            
            # Vérifier que les cellules ont une structure valide
            for cell in notebook_content['cells']:
                self.assertIn('cell_type', cell, "Une cellule ne contient pas de type")
                self.assertIn('source', cell, "Une cellule ne contient pas de source")
            
            # Le test réussit si aucune exception n'est levée
            self.assertTrue(True)
        
        except json.JSONDecodeError as e:
            self.fail(f"Le notebook {notebook_path} n'a pas une structure JSON valide: {str(e)}")
        except Exception as e:
            self.fail(f"Erreur lors de la vérification du notebook {notebook_path}: {str(e)}")
    
    def test_api_logic_tutorial_notebook(self):
        """Test de la structure du notebook tutoriel sur l'API Web pour les opérations logiques."""
        # Chemin du notebook
        notebook_path = os.path.join('examples', 'notebooks', 'api_logic_tutorial.ipynb')
        
        # Vérifier que le notebook existe
        self.assertTrue(os.path.exists(notebook_path), f"Le notebook {notebook_path} n'existe pas")
        
        # Vérifier que le notebook a une structure JSON valide
        try:
            with open(notebook_path, 'r', encoding='utf-8') as f:
                notebook_content = json.load(f)
            
            # Vérifier que le notebook a les attributs requis
            self.assertIn('cells', notebook_content, "Le notebook ne contient pas de cellules")
            self.assertIn('metadata', notebook_content, "Le notebook ne contient pas de métadonnées")
            self.assertIn('nbformat', notebook_content, "Le notebook ne contient pas de format")
            
            # Vérifier que le notebook contient au moins une cellule
            self.assertGreater(len(notebook_content['cells']), 0, "Le notebook ne contient aucune cellule")
            
            # Vérifier que les cellules ont une structure valide
            for cell in notebook_content['cells']:
                self.assertIn('cell_type', cell, "Une cellule ne contient pas de type")
                self.assertIn('source', cell, "Une cellule ne contient pas de source")
            
            # Le test réussit si aucune exception n'est levée
            self.assertTrue(True)
        
        except json.JSONDecodeError as e:
            self.fail(f"Le notebook {notebook_path} n'a pas une structure JSON valide: {str(e)}")
        except Exception as e:
            self.fail(f"Erreur lors de la vérification du notebook {notebook_path}: {str(e)}")


if __name__ == "__main__":
    unittest.main()