#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module agents.core.informal.informal_definitions.
"""

# import unittest # Supprimé
from unittest.mock import MagicMock, patch
import json
import pytest # Déjà présent, gardé

# La configuration du logging et les imports conditionnels (y compris pandas_mock)
# sont maintenant gérés globalement dans tests/conftest.py

# Import des fixtures
from .fixtures_authentic import (
    authentic_semantic_kernel,
    setup_authentic_taxonomy_csv,
    authentic_informal_analysis_plugin
)

# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin, setup_informal_kernel


@pytest.mark.use_real_numpy # Ajout pour utiliser le vrai NumPy/Pandas
class TestInformalDefinitions: # Suppression de l'héritage unittest.TestCase
    """Tests unitaires pour les définitions de l'agent informel."""

    def test_initialization(self, authentic_informal_analysis_plugin):
        plugin = authentic_informal_analysis_plugin
        assert plugin is not None
        assert plugin._logger is not None # pylint: disable=protected-access
        # Vérifier que le chemin du fichier de taxonomie est défini et que le DataFrame est chargé
        assert hasattr(plugin, '_current_taxonomy_path') # pylint: disable=protected-access
        assert plugin._current_taxonomy_path is not None # pylint: disable=protected-access
        assert plugin._get_taxonomy_dataframe() is not None # pylint: disable=protected-access
    
    def test_get_taxonomy_dataframe(self, authentic_informal_analysis_plugin):
        plugin = authentic_informal_analysis_plugin
        df = plugin._get_taxonomy_dataframe() # pylint: disable=protected-access
        assert df is not None
        
        expected_columns_without_pk = ["Name", "Category", "Description", "Example", "Counter_Example"]
        
        if hasattr(df, 'columns'):
            assert len(df.columns) == len(expected_columns_without_pk), \
                   f"Attendu {len(expected_columns_without_pk)} colonnes, trouvé {len(df.columns)}: {df.columns}"
            for col in expected_columns_without_pk:
                assert col in df.columns, f"Colonne manquante: {col}"
            
            assert len(df) >= 3 
        else:
            assert hasattr(df, '_data') # pylint: disable=protected-access
            assert len(df._data) > 0 # pylint: disable=protected-access

    def test_explore_fallacy_hierarchy(self, authentic_informal_analysis_plugin):
        plugin = authentic_informal_analysis_plugin
        hierarchy_json = plugin.explore_fallacy_hierarchy("1") 
        assert isinstance(hierarchy_json, str)
        hierarchy = json.loads(hierarchy_json)
        assert isinstance(hierarchy, dict)
        assert "current_node" in hierarchy
        assert "children" in hierarchy
        assert hierarchy["current_node"]["Name"] == "Appel à l'autorité"
    
    def test_get_fallacy_details(self, authentic_informal_analysis_plugin):
        plugin = authentic_informal_analysis_plugin
        details_json = plugin.get_fallacy_details("1")
        assert isinstance(details_json, str)
        details = json.loads(details_json)
        assert isinstance(details, dict)
        assert "pk" in details
        assert details["pk"] == 1
        assert details["Name"] == "Appel à l'autorité"
        assert "Description" in details
    
    def test_setup_informal_kernel(self, authentic_semantic_kernel, setup_authentic_taxonomy_csv): # Ajout de setup_authentic_taxonomy_csv
        kernel = authentic_semantic_kernel.get_kernel()  # Correction: utiliser get_kernel()
        llm_service = MagicMock()
        test_taxonomy_path = str(setup_authentic_taxonomy_csv) # Utiliser le chemin de la fixture

        setup_informal_kernel(kernel, llm_service, taxonomy_file_path=test_taxonomy_path) # Utiliser test_taxonomy_path
        assert "InformalAnalyzer" in kernel.plugins

# if __name__ == "__main__": # Supprimé
#     unittest.main()