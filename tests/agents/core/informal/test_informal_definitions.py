#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module agents.core.informal.informal_definitions.
"""

import unittest
from unittest.mock import MagicMock, patch
import json

# La configuration du logging et les imports conditionnels (y compris pandas_mock)
# sont maintenant gérés globalement dans tests/conftest.py
# Les imports de sys et os ne semblent plus nécessaires ici.


# Import des fixtures
from .fixtures import (
    mock_semantic_kernel_instance, # patch_semantic_kernel est autouse
    setup_test_taxonomy_csv, # Crée le fichier CSV temporaire
    taxonomy_loader_patches, # Patche get_taxonomy_path et validate_taxonomy_file
    informal_analysis_plugin_instance # Utilise les patches de taxonomie
)

# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin, setup_informal_kernel
import pytest

# @pytest.mark.usefixtures("patch_semantic_kernel") # Déjà autouse dans fixtures.py
@pytest.mark.usefixtures("taxonomy_loader_patches") # Assure que les patches sont actifs pour la classe
class TestInformalDefinitions(unittest.TestCase):
    """Tests unitaires pour les définitions de l'agent informel."""
    
    # setUp et tearDown ne sont plus nécessaires pour la création du fichier CSV et les patches,
    # car gérés par les fixtures setup_test_taxonomy_csv et taxonomy_loader_patches.

    def test_initialization(self, informal_analysis_plugin_instance):
        plugin = informal_analysis_plugin_instance
        self.assertIsNotNone(plugin)
        self.assertIsNotNone(plugin._logger) # pylint: disable=protected-access
        self.assertIsNotNone(plugin.FALLACY_CSV_URL)
        self.assertIsNotNone(plugin.DATA_DIR)
        self.assertIsNotNone(plugin.FALLACY_CSV_LOCAL_PATH)
    
    # Le test_get_taxonomy_dataframe dépend maintenant de la fixture taxonomy_loader_patches
    # et indirectement de setup_test_taxonomy_csv.
    # Le logger n'est plus défini globalement ici, donc les logs de debug numpy sont retirés.
    def test_get_taxonomy_dataframe(self, informal_analysis_plugin_instance):
        plugin = informal_analysis_plugin_instance
        df = plugin._get_taxonomy_dataframe() # pylint: disable=protected-access
        self.assertIsNotNone(df)
        
        expected_columns_without_pk = ["Name", "Category", "Description", "Example", "Counter_Example"]
        
        # pandas_mock pourrait ne pas avoir 'columns' ou 'index' de la même manière que pandas réel.
        # Adaptez les assertions en fonction du comportement de votre mock.
        # Si pandas_mock simule bien un DataFrame pandas:
        if hasattr(df, 'columns'):
            self.assertEqual(len(df.columns), len(expected_columns_without_pk),
                           f"Attendu {len(expected_columns_without_pk)} colonnes, trouvé {len(df.columns)}: {df.columns}")
            for col in expected_columns_without_pk:
                self.assertIn(col, df.columns, f"Colonne manquante: {col}")
            
            # Vérifier que PK est bien l'index (si le mock le supporte)
            # if hasattr(df, 'index') and hasattr(df.index, 'name'):
            #     self.assertEqual(df.index.name, "PK")

            self.assertGreaterEqual(len(df), 3) # Basé sur le contenu de setup_test_taxonomy_csv
        else:
            # Fallback pour un mock plus simple
            self.assertTrue(hasattr(df, '_data')) # pylint: disable=protected-access
            self.assertGreater(len(df._data), 0) # pylint: disable=protected-access


    def test_explore_fallacy_hierarchy(self, informal_analysis_plugin_instance):
        plugin = informal_analysis_plugin_instance
        hierarchy_json = plugin.explore_fallacy_hierarchy("1") # PK "1" existe dans la fixture CSV
        self.assertIsInstance(hierarchy_json, str)
        hierarchy = json.loads(hierarchy_json)
        self.assertIsInstance(hierarchy, dict)
        self.assertIn("current_node", hierarchy)
        self.assertIn("children", hierarchy)
        self.assertEqual(hierarchy["current_node"]["name"], "Appel a l'autorite") # Vérifie le nom
    
    def test_get_fallacy_details(self, informal_analysis_plugin_instance):
        plugin = informal_analysis_plugin_instance
        # _internal_get_node_details est appelé par get_fallacy_details.
        # Le patch ici est pour s'assurer que la sortie est contrôlée pour le test.
        # Cependant, avec la fixture CSV, _internal_get_node_details devrait fonctionner.
        # Si on veut tester _internal_get_node_details lui-même, il faudrait un autre test.
        # Pour ce test, on peut soit patcher, soit s'attendre aux vraies données du CSV.
        # Allons avec les données du CSV via la fixture.
        
        details_json = plugin.get_fallacy_details("1") # PK "1"
        self.assertIsInstance(details_json, str)
        details = json.loads(details_json)
        self.assertIsInstance(details, dict)
        self.assertIn("pk", details)
        self.assertEqual(details["pk"], 1) # Doit être un entier
        self.assertEqual(details["name"], "Appel a l'autorite")
        self.assertIn("description", details)
    
    def test_setup_informal_kernel(self, mock_semantic_kernel_instance):
        kernel = mock_semantic_kernel_instance # Utilise la fixture pour le kernel mocké
        llm_service = MagicMock() # Mock simple pour le service LLM
        
        # La fixture patch_semantic_kernel (autouse) s'assure que semantic_kernel.Kernel est mocké.
        # setup_informal_kernel va instancier InformalAnalysisPlugin.
        # Les patches pour la taxonomie doivent être actifs si InformalAnalysisPlugin les utilise à l'init.
        # La fixture taxonomy_loader_patches (appliquée à la classe) devrait couvrir cela.
        
        setup_informal_kernel(kernel, llm_service)
        self.assertIn("InformalAnalyzer", kernel.plugins) # Vérifie que le plugin a été ajouté


if __name__ == "__main__":
    unittest.main()