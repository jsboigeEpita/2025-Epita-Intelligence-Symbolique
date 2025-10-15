# -*- coding: utf-8 -*-
# tests/integration/test_notebooks_structure.py
"""
Tests d'intégration pour vérifier que les notebooks ont une structure valide.
"""

import unittest
import os
import json


class TestNotebooksStructure(unittest.TestCase):
    """Tests d'intégration pour la structure des notebooks."""

    def _verify_notebook_structure(self, notebook_relative_path):
        """
        Méthode d'aide pour vérifier la structure d'un notebook.
        Prend le chemin relatif du notebook depuis la racine du projet.
        """
        # Construire le chemin absolu basé sur l'emplacement de ce fichier de test
        # tests/integration/test_notebooks_structure.py -> remonter de deux niveaux pour la racine
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        notebook_path = os.path.join(project_root, notebook_relative_path)

        self.assertTrue(
            os.path.exists(notebook_path),
            f"Le notebook {notebook_path} (chemin relatif: {notebook_relative_path}) n'existe pas. Vérifié depuis {os.getcwd()}",
        )

        try:
            with open(notebook_path, "r", encoding="utf-8") as f:
                notebook_content = json.load(f)

            # Vérifier que le notebook a les attributs requis
            self.assertIn(
                "cells", notebook_content, "Le notebook ne contient pas de cellules"
            )
            self.assertIn(
                "metadata",
                notebook_content,
                "Le notebook ne contient pas de métadonnées",
            )
            self.assertIn(
                "nbformat", notebook_content, "Le notebook ne contient pas de format"
            )

            # Vérifier que le notebook contient au moins une cellule
            self.assertTrue(
                isinstance(notebook_content["cells"], list),
                "L'attribut 'cells' n'est pas une liste.",
            )
            self.assertGreater(
                len(notebook_content["cells"]),
                0,
                "Le notebook ne contient aucune cellule",
            )

            # Vérifier que les cellules ont une structure valide
            for i, cell in enumerate(notebook_content["cells"]):
                self.assertIn(
                    "cell_type", cell, f"La cellule {i} ne contient pas de type"
                )
                self.assertIn(
                    "source", cell, f"La cellule {i} ne contient pas de source"
                )

        except json.JSONDecodeError as e:
            self.fail(
                f"Le notebook {notebook_path} n'a pas une structure JSON valide: {str(e)}"
            )
        except Exception as e:
            self.fail(
                f"Erreur lors de la vérification du notebook {notebook_path}: {str(e)}"
            )

    def test_logic_agents_tutorial_notebook(self):
        """Test de la structure du notebook tutoriel sur les agents logiques."""
        self._verify_notebook_structure(
            os.path.join("examples", "notebooks", "logic_agents_tutorial.ipynb")
        )

    def test_api_logic_tutorial_notebook(self):
        """Test de la structure du notebook tutoriel sur l'API Web pour les opérations logiques."""
        self._verify_notebook_structure(
            os.path.join("examples", "notebooks", "api_logic_tutorial.ipynb")
        )


if __name__ == "__main__":
    # Pour exécuter spécifiquement ce fichier de test avec unittest
    # Cela nécessite que le PYTHONPATH soit correctement configuré si exécuté directement
    # ou que le script soit lancé depuis la racine du projet avec python -m tests.integration.test_notebooks_structure
    unittest.main()
