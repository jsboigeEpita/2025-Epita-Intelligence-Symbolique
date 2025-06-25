
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

from pathlib import Path
import semantic_kernel as sk
from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin, setup_informal_kernel
import pytest

@pytest.mark.use_real_numpy
class TestInformalAnalysisPlugin(unittest.TestCase):
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests pour la classe InformalAnalysisPlugin."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.plugin = InformalAnalysisPlugin()
        
        # Créer un DataFrame de test pour la taxonomie
        self.test_df = pd.DataFrame({
            'PK': pd.array([0, 1, 2, 3], dtype='Int64'),
            'FK_Parent': pd.array([pd.NA, 0, 0, 1], dtype='Int64'),
            'text_fr': ['Racine', 'Catégorie 1', 'Catégorie 2', 'Sous-catégorie 1.1'],
            'nom_vulgarisé': ['Sophismes', 'Ad Hominem', 'Faux Dilemme', 'Attaque Personnelle'],
            'description_fr': ['Description racine', 'Description cat 1', 'Description cat 2', 'Description sous-cat 1.1'],
            'exemple_fr': ['Exemple racine', 'Exemple cat 1', 'Exemple cat 2', 'Exemple sous-cat 1.1'],
            'depth': [0, 1, 1, 2]
        })
        self.test_df.set_index('PK', inplace=True)

    
    
    
    
    
    @patch('pandas.read_csv')
    @patch('requests.get')
    @patch('argumentation_analysis.utils.taxonomy_loader.validate_taxonomy_file')
    @patch('argumentation_analysis.utils.taxonomy_loader.get_taxonomy_path')
    @patch('builtins.open')
    def test_internal_load_and_prepare_dataframe(self, mock_file, mock_get_path, mock_validate, mock_requests, mock_read_csv):
        """Teste le chargement et la préparation du DataFrame."""
        # Configurer les mocks
        mock_read_csv.return_value = self.test_df.reset_index()
        mock_requests.return_value.status_code = 200
        mock_validate.return_value = True  # Simuler que le fichier de taxonomie est valide
        mock_get_path.return_value = Path("mock_taxonomy_path.csv")  # Simuler un chemin de fichier valide
        
        # Appeler la méthode à tester
        df = self.plugin._internal_load_and_prepare_dataframe()
        
        # Vérifier que le DataFrame a été correctement chargé et préparé
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 4)
        pd.testing.assert_frame_equal(df, self.test_df)

    @patch.object(InformalAnalysisPlugin, '_internal_load_and_prepare_dataframe')
    def test_get_taxonomy_dataframe(self, mock_load):
        """Teste la récupération du DataFrame de taxonomie."""
        # Configurer le mock pour retourner le DataFrame de test
        mock_load.return_value = self.test_df
        
        # Appeler la méthode à tester
        df = self.plugin._get_taxonomy_dataframe()
        
        # Vérifier que le DataFrame a été correctement récupéré
        self.assertIsNotNone(df)
        pd.testing.assert_frame_equal(df, self.test_df)
        
        # Vérifier que le cache fonctionne (deuxième appel)
        df2 = self.plugin._get_taxonomy_dataframe()
        pd.testing.assert_frame_equal(df2, df) # Doit être le même objet (pas de rechargement)
        mock_load.assert_called_once()  # Le chargement ne doit être appelé qu'une fois

    @patch.object(InformalAnalysisPlugin, '_get_taxonomy_dataframe')
    def test_internal_get_node_details(self, mock_get_df):
        """Teste la récupération des détails d'un nœud."""
        # Configurer le mock pour retourner le DataFrame de test
        mock_get_df.return_value = self.test_df
        
        # Appeler la méthode à tester pour un nœud existant
        details = self.plugin._internal_get_node_details(1, self.test_df)
        
        # Vérifier que les détails ont été correctement récupérés
        self.assertEqual(details['pk'], 1)
        self.assertEqual(details['text_fr'], 'Catégorie 1')
        self.assertEqual(details['nom_vulgarisé'], 'Ad Hominem')
        self.assertIsNone(details['error'])
        
        # Tester avec un PK inexistant
        details_invalid = self.plugin._internal_get_node_details(999, self.test_df)
        self.assertEqual(details_invalid['pk'], 999)
        self.assertIsNotNone(details_invalid['error'])
        
        # Tester avec un DataFrame None
        details_no_df = self.plugin._internal_get_node_details(1, None)
        self.assertEqual(details_no_df['pk'], 1)
        self.assertIsNotNone(details_no_df['error'])

    # Ce test est obsolète car la méthode '_internal_get_children_details' a été supprimée
    # et sa logique intégrée dans '_internal_explore_hierarchy'.

    @patch.object(InformalAnalysisPlugin, '_get_taxonomy_dataframe')
    @patch.object(InformalAnalysisPlugin, '_internal_explore_hierarchy')
    def test_explore_fallacy_hierarchy(self, mock_explore, mock_get_df):
        """Teste l'exploration de la hiérarchie des sophismes."""
        # Configurer les mocks
        mock_get_df.return_value = self.test_df
        mock_explore.return_value = {
            "current_node": {'pk': 0, 'text_fr': 'Racine', 'nom_vulgarisé': 'Sophismes', 'error': None},
            "children": [
                {'pk': 1, 'text_fr': 'Catégorie 1', 'nom_vulgarisé': 'Ad Hominem'},
                {'pk': 2, 'text_fr': 'Catégorie 2', 'nom_vulgarisé': 'Faux Dilemme'}
            ]
        }
        
        # Appeler la méthode à tester
        result_json = self.plugin.explore_fallacy_hierarchy("0")
        result = json.loads(result_json)
        
        # Vérifier que le résultat est correct
        self.assertIn('current_node', result)
        self.assertIn('children', result)
        self.assertEqual(result['current_node']['pk'], 0)
        self.assertEqual(len(result['children']), 2)
        
        # Tester avec un PK invalide
        mock_get_df.return_value = self.test_df
        result_invalid_json = self.plugin.explore_fallacy_hierarchy("invalid")
        result_invalid = json.loads(result_invalid_json)
        self.assertIn('error', result_invalid)
        
        # Tester avec un DataFrame None
        mock_get_df.return_value = None
        result_no_df_json = self.plugin.explore_fallacy_hierarchy("0")
        result_no_df = json.loads(result_no_df_json)
        self.assertIn('error', result_no_df)

    @patch.object(InformalAnalysisPlugin, '_get_taxonomy_dataframe')
    @patch.object(InformalAnalysisPlugin, '_internal_get_node_details')
    def test_get_fallacy_details(self, mock_details, mock_get_df):
        """Teste la récupération des détails d'un sophisme."""
        # Configurer les mocks
        mock_get_df.return_value = self.test_df
        mock_details.return_value = {
            'pk': 1,
            'text_fr': 'Catégorie 1',
            'nom_vulgarisé': 'Ad Hominem',
            'description_fr': 'Description cat 1',
            'exemple_fr': 'Exemple cat 1',
            'error': None
        }
        
        # Appeler la méthode à tester
        result_json = self.plugin.get_fallacy_details("1")
        result = json.loads(result_json)
        
        # Vérifier que le résultat est correct
        self.assertEqual(result['pk'], 1)
        self.assertEqual(result['text_fr'], 'Catégorie 1')
        self.assertEqual(result['nom_vulgarisé'], 'Ad Hominem')
        self.assertIsNone(result.get('error'))
        
        # Tester avec un PK invalide
        result_invalid_json = self.plugin.get_fallacy_details("invalid")
        result_invalid = json.loads(result_invalid_json)
        self.assertIn('error', result_invalid)
        
        # Tester avec un DataFrame None
        mock_get_df.return_value = None
        result_no_df_json = self.plugin.get_fallacy_details("1")
        result_no_df = json.loads(result_no_df_json)
        self.assertIn('error', result_no_df)


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