
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests unitaires pour l'agent d'analyse informelle.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import os
import tempfile
import pandas as pd
import numpy as np

from pathlib import Path
import semantic_kernel as sk
from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin, setup_informal_kernel
import pytest
import logging

# Configuration du logging pour les tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="function")
def informal_plugin_with_test_df():
    """
    Fixture Pytest pour fournir une instance de InformalAnalysisPlugin
    avec un DataFrame de taxonomie de test pré-configuré.
    La portée "function" garantit une nouvelle instance pour chaque test.
    """
    plugin = InformalAnalysisPlugin()
    
    # Créer et assigner le DataFrame de test directement
    test_df = pd.DataFrame({
        'PK': [0, 1, 2, 3],
        'FK_Parent': [pd.NA, 0, 0, 1],
        'text_fr': ['Racine', 'Catégorie 1', 'Catégorie 2', 'Sous-catégorie 1.1'],
        'nom_vulgarise': ['Sophismes', 'Ad Hominem', 'Faux Dilemme', 'Attaque Personnelle'],
        'description_fr': ['Description racine', 'Description cat 1', 'Description cat 2', 'Description sous-cat 1.1'],
        'exemple_fr': ['Exemple racine', 'Exemple cat 1', 'Exemple cat 2', 'Exemple sous-cat 1.1'],
        'depth': [0, 1, 1, 2]
    }).astype({
        'PK': int,
        'FK_Parent': 'Int64', # Utiliser 'Int64' pour entiers avec potentiels NA
        'depth': int
    })
    test_df.set_index('PK', inplace=True)
    
    # Remplacer la méthode de chargement par un mock qui retourne le DataFrame de test
    with patch.object(plugin, '_internal_load_and_prepare_dataframe', return_value=test_df):
        yield plugin, test_df

@pytest.mark.usefixtures("informal_plugin_with_test_df")
class TestInformalAnalysisPlugin:
    """
    Classe de tests pour InformalAnalysisPlugin, utilisant des fixtures pytest
    pour garantir l'isolation complète des tests.
    """

    @patch('pandas.read_csv')
    @patch('requests.get')
    @patch('argumentation_analysis.utils.taxonomy_loader.validate_taxonomy_file')
    @patch('argumentation_analysis.utils.taxonomy_loader.get_taxonomy_path')
    @patch('builtins.open')
    def test_internal_load_and_prepare_dataframe(self, mock_open, mock_get_path, mock_validate, mock_requests, mock_read_csv, informal_plugin_with_test_df):
        """Teste le chargement et la préparation du DataFrame."""
        plugin, test_df = informal_plugin_with_test_df
        
        # Configurer les mocks
        mock_read_csv.return_value = test_df.reset_index()
        mock_requests.return_value.status_code = 200
        mock_validate.return_value = True
        mock_get_path.return_value = Path("mock_taxonomy_path.csv")
        
        # Appeler la méthode à tester
        # Note: on teste la méthode interne, pas celle qui utilise le cache
        df = plugin._internal_load_and_prepare_dataframe()
        
        # Vérifications
        assert df is not None
        assert len(df) == 4
        pd.testing.assert_frame_equal(df, test_df)

    def test_get_taxonomy_dataframe(self, informal_plugin_with_test_df):
        """Teste la récupération du DataFrame de taxonomie et la mise en cache."""
        plugin, test_df = informal_plugin_with_test_df

        # Appeler la méthode une première fois
        df = plugin._get_taxonomy_dataframe()
        
        # Vérifier que le DataFrame est correct
        assert df is not None
        pd.testing.assert_frame_equal(df, test_df)
        
        # Appeler une seconde fois pour vérifier l'utilisation du cache
        df2 = plugin._get_taxonomy_dataframe()
        pd.testing.assert_frame_equal(df2, df)
        
        # Vérifier que la méthode de chargement n'a été appelée qu'une fois
        # Le mock est déjà configuré dans la fixture
        plugin._internal_load_and_prepare_dataframe.assert_called_once()

    def test_internal_get_node_details(self, informal_plugin_with_test_df):
        """Teste la récupération des détails d'un nœud."""
        plugin, test_df = informal_plugin_with_test_df
        
        # === Cas 1: Nœud existant ===
        details = plugin._internal_get_node_details(1, test_df)
        assert details['pk'] == 1
        assert details['text_fr'] == 'Catégorie 1'
        assert details['nom_vulgarise'] == 'Ad Hominem'
        assert details['error'] is None
        
        # === Cas 2: PK Inexistante ===
        details_invalid = plugin._internal_get_node_details(999, test_df)
        assert details_invalid['pk'] == 999
        assert details_invalid['error'] is not None
        
        # === Cas 3: DataFrame None ===
        details_no_df = plugin._internal_get_node_details(1, None)
        assert details_no_df['pk'] == 1
        assert details_no_df['error'] is not None

    # Ce test est obsolète car la méthode '_internal_get_children_details' a été supprimée
    # et sa logique intégrée dans '_internal_explore_hierarchy'.

    @patch.object(InformalAnalysisPlugin, '_get_taxonomy_dataframe')
    @patch.object(InformalAnalysisPlugin, '_internal_explore_hierarchy', autospec=True)
    def test_explore_fallacy_hierarchy(self, mock_explore, informal_plugin_with_test_df):
        """Teste l'exploration de la hiérarchie des sophismes."""
        plugin, test_df = informal_plugin_with_test_df
        
        # === Cas 1: Appel Nominal ===
        mock_explore.return_value = {
            "current_node": {'pk': 0, 'text_fr': 'Racine', 'nom_vulgarise': 'Sophismes', 'error': None},
            "children": [
                {'pk': 1, 'text_fr': 'Catégorie 1', 'nom_vulgarise': 'Ad Hominem'},
                {'pk': 2, 'text_fr': 'Catégorie 2', 'nom_vulgarise': 'Faux Dilemme'}
            ]
        }
        
        result_json = plugin.explore_fallacy_hierarchy("0")
        result = json.loads(result_json)
        
        assert 'current_node' in result
        assert 'children' in result
        assert result['current_node']['pk'] == 0
        assert len(result['children']) == 2
        mock_explore.assert_called_once_with(plugin, 0, test_df, 15)
        
        # === Cas 2: PK Invalide ===
        result_invalid_json = plugin.explore_fallacy_hierarchy("invalid")
        result_invalid = json.loads(result_invalid_json)
        assert 'error' in result_invalid

        # === Cas 3: DataFrame non disponible (simulé en patchant _get_taxonomy_dataframe) ===
        with patch.object(plugin, '_get_taxonomy_dataframe', return_value=None):
            result_no_df_json = plugin.explore_fallacy_hierarchy("0")
            result_no_df = json.loads(result_no_df_json)
            assert 'error' in result_no_df

    @patch.object(InformalAnalysisPlugin, '_get_taxonomy_dataframe')
    @patch.object(InformalAnalysisPlugin, '_internal_get_node_details', autospec=True)
    def test_get_fallacy_details(self, mock_details, informal_plugin_with_test_df):
        """Teste la récupération des détails d'un sophisme."""
        plugin, test_df = informal_plugin_with_test_df
        
        # === Cas 1: Appel Nominal ===
        mock_details.return_value = {
            'pk': 1,
            'text_fr': 'Catégorie 1',
            'nom_vulgarise': 'Ad Hominem',
            'description_fr': 'Description cat 1',
            'exemple_fr': 'Exemple cat 1',
            'error': None
        }
        
        result_json = plugin.get_fallacy_details("1")
        result = json.loads(result_json)

        assert result['pk'] == 1
        assert result['text_fr'] == 'Catégorie 1'
        assert result['nom_vulgarise'] == 'Ad Hominem'
        assert 'error' not in result or result['error'] is None
        mock_details.assert_called_once_with(plugin, 1, test_df)

        # === Cas 2: PK Invalide ===
        result_invalid_json = plugin.get_fallacy_details("invalid")
        result_invalid = json.loads(result_invalid_json)
        assert 'error' in result_invalid

        # === Cas 3: DataFrame non disponible (simulé) ===
        with patch.object(plugin, '_get_taxonomy_dataframe', return_value=None):
            result_no_df_json = plugin.get_fallacy_details("1")
            result_no_df = json.loads(result_no_df_json)
            assert 'error' in result_no_df


class TestSetupInformalKernel(unittest.TestCase):
    """Tests pour la fonction setup_informal_kernel."""

    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()

    def setUp(self):
        """Initialisation avant chaque test."""
        import asyncio
        async def async_setup():
            self.kernel = sk.Kernel()
            # _create_authentic_gpt4o_mini_instance retourne un Kernel configuré
            # Nous extrayons le service llm de ce kernel pour le passer à setup_informal_kernel
            kernel_with_service = await self._create_authentic_gpt4o_mini_instance()
            self.llm_service = kernel_with_service.get_service()
        asyncio.run(async_setup())

    
    
    
    @patch('semantic_kernel.Kernel.add_function')
    @patch('semantic_kernel.Kernel.add_plugin')
    def test_setup_informal_kernel(self, mock_add_plugin, mock_add_function):
        """Teste la configuration du kernel pour l'agent informel."""
        # Appeler la fonction à tester
        setup_informal_kernel(self.kernel, self.llm_service)

        # Vérifier que le plugin natif a été ajouté une fois
        mock_add_plugin.assert_called_once()
        # Vérifier le type de l'instance du plugin
        plugin_instance = mock_add_plugin.call_args[0][0]
        self.assertIsInstance(plugin_instance, InformalAnalysisPlugin)
        
        # Vérifier que les fonctions sémantiques ont été ajoutées
        # Il y a 3 fonctions sémantiques dans setup_informal_kernel
        self.assertGreaterEqual(mock_add_function.call_count, 3)
        
        # On peut optionnellement vérifier les noms des fonctions ajoutées
        added_functions = [call.kwargs['function_name'] for call in mock_add_function.call_args_list]
        self.assertIn("semantic_IdentifyArguments", added_functions)
        self.assertIn("semantic_AnalyzeFallacies", added_functions)
        self.assertIn("semantic_JustifyFallacyAttribution", added_functions)


if __name__ == '__main__':
    unittest.main()