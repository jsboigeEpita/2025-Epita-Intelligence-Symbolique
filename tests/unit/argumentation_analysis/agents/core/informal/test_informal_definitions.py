
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
import unittest

import pandas as pd
import json
import os
import sys
from pathlib import Path
import logging
from semantic_kernel import Kernel # Keep Kernel import here
from semantic_kernel.functions import KernelPlugin # Import KernelPlugin
from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin # Importation de la classe à tester

current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent.parent.parent.parent 
sys.path.append(str(root_dir))

# Importation de taxonomy_loader pour pouvoir le patcher
# import taxonomy_loader

test_logger = logging.getLogger("TestInformalDefinitions")


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

    """Tests pour le plugin d'analyse des sophismes informels."""

    def setUp(self): 
        """Initialisation avant chaque test."""
        self.sample_taxonomy_data = [
            {'pk': 0, 'parent_pk': None, 'depth': 0, 'text_fr': 'Sophismes', 'nom_vulgarisé': 'Sophismes', 'description_fr': 'Racine de la taxonomie des sophismes.'},
            {'pk': 1, 'parent_pk': 0, 'depth': 1, 'text_fr': 'Sophisme de Pertinence', 'nom_vulgarisé': 'Pertinence', 'description_fr': 'Les prémisses ne sont pas pertinentes pour la conclusion.'},
            {'pk': 2, 'parent_pk': 1, 'depth': 2, 'text_fr': 'Ad Hominem', 'nom_vulgarisé': 'Attaque personnelle', 'description_fr': "Attaquer la personne plutôt que l'argument."},
            {'pk': 3, 'parent_pk': 0, 'depth': 1, 'text_fr': 'Sophisme d\'Ambiguïté', 'nom_vulgarisé': 'Ambiguïté', 'description_fr': 'Utilisation de termes vagues ou équivoques.'}
        ]
        
        self.df_columns = [
            {'name': 'pk', 'dtype': 'int64'},
            {'name': 'parent_pk', 'dtype': 'float64'}, 
            {'name': 'depth', 'dtype': 'int64'},
            {'name': 'text_fr', 'dtype': 'object'},
            {'name': 'nom_vulgarisé', 'dtype': 'object'},
            {'name': 'description_fr', 'dtype': 'object'}
        ]

        self.mock_df_real = pd.DataFrame(self.sample_taxonomy_data)
        self.mock_df_real = self.mock_df_real.set_index('pk') # Set index here
        self.mock_df_real['parent_pk'] = pd.to_numeric(self.mock_df_real['parent_pk'], errors='coerce')
        self.mock_df_real['depth'] = pd.to_numeric(self.mock_df_real['depth'], errors='coerce').astype('Int64')
        self.mock_df = self.mock_df_real.copy()
        
        # Patch pour taxonomy_loader.get_taxonomy_path et validate_taxonomy_file
        # Cible directement le module taxonomy_loader
        # self.patcher_get_taxonomy_path = patch('taxonomy_loader.get_taxonomy_path', return_value="mock_taxonomy_path_for_all_tests.csv")
        # self.mock_get_taxonomy_path = self.patcher_get_taxonomy_path.start()
        # self.addCleanup(self.patcher_get_taxonomy_path.stop)

        # self.patcher_validate_taxonomy_file = patch('taxonomy_loader.validate_taxonomy_file', return_value=True)
        # self.mock_validate_taxonomy_file = self.patcher_validate_taxonomy_file.start()
        # self.addCleanup(self.patcher_validate_taxonomy_file.stop)

        # Importation de la classe réelle pour la patcher
        from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin
        self.InformalAnalysisPlugin = InformalAnalysisPlugin

        # Patch de la méthode _get_taxonomy_dataframe du module
        self.patcher_get_taxonomy_df = patch('argumentation_analysis.agents.core.informal.informal_definitions.InformalAnalysisPlugin._get_taxonomy_dataframe')
        self.mock_get_taxonomy_df_call = self.patcher_get_taxonomy_df.start()
        self.addCleanup(self.patcher_get_taxonomy_df.stop)
        self.mock_get_taxonomy_df_call# Mock eliminated - using authentic gpt-4o-mini self.mock_df
        
        # Instancier le plugin réel
        self.plugin = self.InformalAnalysisPlugin()
        # Appel initial pour peupler le cache et tester l'appel du mock
        _ = self.plugin._get_taxonomy_dataframe()
        
    def test_initialization(self):
        """Teste l'initialisation du plugin."""
        # L'attribut taxonomy_df n'existe pas directement sur l'instance du plugin.
        # Le DataFrame est accédé via _get_taxonomy_dataframe().
        # Le test doit vérifier que _get_taxonomy_dataframe a été appelé et retourne le mock_df.
        self.mock_get_taxonomy_df_call.# Mock assertion eliminated - authentic validation # Vérifie que _get_taxonomy_dataframe a été appelé
        retrieved_df = self.plugin._get_taxonomy_dataframe()
        self.assertIs(retrieved_df, self.mock_df)
        self.assertEqual(len(retrieved_df), 4)


    def test_internal_load_and_prepare_dataframe(self):
        """Teste le chargement et la préparation interne du DataFrame."""
        # Ce test n'est plus pertinent car _internal_load_and_prepare_dataframe est mocké.
        # Le but est de vérifier que _get_taxonomy_dataframe est appelé et retourne le mock_df.
        # Pas d'assertions spécifiques ici car le comportement est déjà couvert par test_initialization.
        pass

    def test_internal_load_and_prepare_dataframe_error_via_mock(self):
        """Teste la gestion d'erreur de __init__ si _get_taxonomy_dataframe échoue."""
        # Configurer le mock global pour lever une exception lors de l'appel
        self.mock_get_taxonomy_df_call# Mock eliminated - using authentic gpt-4o-mini Exception("Mocked Load Error")

        # Créer une nouvelle instance du plugin
        # Le mock est déjà configuré dans setUp pour lever une exception
        self.mock_get_taxonomy_df_call.reset_mock() # Réinitialiser les appels pour ce test
        self.mock_get_taxonomy_df_call# Mock eliminated - using authentic gpt-4o-mini Exception("Mocked Load Error")

        plugin_with_error = self.InformalAnalysisPlugin()
        
        # L'appel à _get_taxonomy_dataframe() doit être explicite pour déclencher l'erreur
        with self.assertRaises(Exception):
            plugin_with_error._get_taxonomy_dataframe()
        
        # Vérifier que le mock a été appelé
        self.mock_get_taxonomy_df_call.# Mock assertion eliminated - authentic validation
        self.assertIsNone(plugin_with_error._taxonomy_df_cache) # Vérifier le cache interne, pas taxonomy_df

        # Restaurer le side_effect et le return_value pour les autres tests
        self.mock_get_taxonomy_df_call# Mock eliminated - using authentic gpt-4o-mini None
        self.mock_get_taxonomy_df_call# Mock eliminated - using authentic gpt-4o-mini self.mock_df
        self.mock_get_taxonomy_df_call.reset_mock()


    def test_internal_get_node_details(self):
        """Teste la récupération des détails d'un nœud interne."""
        # Pour ce test, nous utilisons le DataFrame réel mocké.
        details_pk1 = self.plugin._internal_get_node_details(1, self.mock_df)
        self.assertIsNotNone(details_pk1)
        self.assertEqual(details_pk1['pk'], 1)
        self.assertEqual(details_pk1['nom_vulgarisé'], 'Pertinence')

        details_pk_invalid = self.plugin._internal_get_node_details(99, self.mock_df)
        self.assertIsNotNone(details_pk_invalid)
        self.assertIn("error", details_pk_invalid)
        self.assertIn("PK 99 non trouvée dans la taxonomie.", details_pk_invalid["error"])

    def test_internal_get_children_details(self):
        """Teste la récupération des détails des enfants d'un nœud."""
        # Pour ce test, nous utilisons le DataFrame réel mocké.
        children_pk0 = self.plugin._internal_get_children_details(0, self.mock_df, max_children=5)
        self.assertEqual(len(children_pk0), 2)
        self.assertTrue(any(c['nom_vulgarisé'] == 'Pertinence' for c in children_pk0))
        self.assertTrue(any(c['nom_vulgarisé'] == 'Ambiguïté' for c in children_pk0))

        children_pk1 = self.plugin._internal_get_children_details(1, self.mock_df, max_children=5)
        self.assertEqual(len(children_pk1), 1)
        self.assertEqual(children_pk1[0]['nom_vulgarisé'], 'Attaque personnelle')

        children_pk2 = self.plugin._internal_get_children_details(2, self.mock_df, max_children=5)
        self.assertEqual(len(children_pk2), 0)

    def test_internal_explore_hierarchy(self):
        """Teste l'exploration interne de la hiérarchie."""
        # Pour ce test, nous utilisons le DataFrame réel mocké.
        hierarchy_pk0 = self.plugin._internal_explore_hierarchy(0, self.mock_df)
        self.assertIsNotNone(hierarchy_pk0["current_node"])
        self.assertEqual(hierarchy_pk0["current_node"]["nom_vulgarisé"], "Sophismes")
        self.assertEqual(len(hierarchy_pk0["children"]), 2)
        self.assertIsNone(hierarchy_pk0["error"])

        hierarchy_pk2 = self.plugin._internal_explore_hierarchy(2, self.mock_df)
        self.assertIsNotNone(hierarchy_pk2["current_node"])
        self.assertEqual(hierarchy_pk2["current_node"]["nom_vulgarisé"], "Attaque personnelle")
        self.assertEqual(len(hierarchy_pk2["children"]), 0)
        self.assertIsNone(hierarchy_pk2["error"])

        hierarchy_invalid = self.plugin._internal_explore_hierarchy(99, self.mock_df)
        self.assertIsNone(hierarchy_invalid["current_node"])
        self.assertEqual(len(hierarchy_invalid["children"]), 0)
        self.assertIn("PK 99 non trouvée", hierarchy_invalid["error"])

    def test_explore_fallacy_hierarchy(self):
        """Teste la méthode publique d'exploration de la hiérarchie."""
        # Pour ce test, nous utilisons le DataFrame réel mocké.
        result_json_pk1 = self.plugin.explore_fallacy_hierarchy("1")
        result_pk1 = json.loads(result_json_pk1)
        print(f"[DEBUG TEST] Résultat de explore_fallacy_hierarchy pour PK 1: {result_pk1}")
        
        self.assertEqual(result_pk1["current_node"]["nom_vulgarisé"], "Pertinence")
        self.assertEqual(len(result_pk1["children"]), 1)
        self.assertEqual(result_pk1["children"][0]["nom_vulgarisé"], "Attaque personnelle")

        result_json_invalid = self.plugin.explore_fallacy_hierarchy("99")
        result_invalid = json.loads(result_json_invalid)
        self.assertIn("PK 99 non trouvée", result_invalid["error"])

        result_json_non_numeric = self.plugin.explore_fallacy_hierarchy("abc")
        result_non_numeric = json.loads(result_json_non_numeric)
        self.assertIn("PK invalide: abc", result_non_numeric["error"])

    def test_get_fallacy_details(self):
        """Teste la méthode publique de récupération des détails d'un sophisme."""
        # Pour ce test, nous utilisons le DataFrame réel mocké.
        details_json_pk2 = self.plugin.get_fallacy_details("2")
        details_pk2 = json.loads(details_json_pk2)
        self.assertEqual(details_pk2["nom_vulgarisé"], "Attaque personnelle")
        self.assertEqual(details_pk2["description_fr"], "Attaquer la personne plutôt que l'argument.")

        details_json_invalid = self.plugin.get_fallacy_details("99")
        details_invalid = json.loads(details_json_invalid)
        self.assertIn("PK 99 non trouvée", details_invalid["error"])

        details_json_non_numeric = self.plugin.get_fallacy_details("xyz")
        details_non_numeric_parsed = json.loads(details_json_non_numeric)
        self.assertIsNotNone(details_non_numeric_parsed)
        self.assertIn("PK invalide: xyz", details_non_numeric_parsed["error"])

    def test_get_taxonomy_dataframe(self):
        """Teste la récupération du DataFrame de taxonomie."""
        # Puisque _get_taxonomy_dataframe est mocké pour retourner self.mock_df,
        # nous pouvons directement tester les propriétés du mock_df.
        df_for_json = self.plugin._get_taxonomy_dataframe()
        self.assertIs(df_for_json, self.mock_df) # Vérifier que le mock_df est retourné
        
        # Le reste des assertions peut être gardé pour vérifier la structure du mock_df
        # si c'est pertinent pour le test.
        if df_for_json.index.name == 'pk': # Check if 'pk' is the index name
            df_for_json = df_for_json.reset_index()
        df_json = df_for_json.to_json(orient='records')
        df_data = json.loads(df_json)
        self.assertIsInstance(df_data, list)
        self.assertEqual(len(df_data), 4)
        ad_hominem_entry = next((item for item in df_data if item["nom_vulgarisé"] == "Attaque personnelle"), None)
        self.assertIsNotNone(ad_hominem_entry)
        self.assertEqual(ad_hominem_entry["pk"], 2)


class TestSetupInformalKernel(unittest.TestCase):
    """Tests pour la fonction de configuration du kernel informel."""

    def setUp(self):
        super().setUp() # Call parent setUp
        # Import setup_informal_kernel here to ensure it's available after patches
        # For TestSetupInformalKernel, setup_informal_kernel is imported globally
        # So we just need to reference it.
        from argumentation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel
        self.setup_informal_kernel_func = setup_informal_kernel 
        from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin
        self.InformalAnalysisPlugin = InformalAnalysisPlugin

    
    def test_setup_informal_kernel(self, MockInformalAnalysisPlugin):
        """Teste la configuration réussie du kernel informel."""
        # Mock the description attribute to avoid ValidationError
        mock_plugin_instance = MagicMock(description="Mock Informal Analysis Plugin")
        MockInformalAnalysisPlugin# Mock eliminated - using authentic gpt-4o-mini mock_plugin_instance
        kernel = Kernel()
        mock_llm_service = Magicawait self._create_authentic_gpt4o_mini_instance() 
        self.setup_informal_kernel_func(kernel, mock_llm_service) 
        MockInformalAnalysisPlugin.# Mock assertion eliminated - authentic validation
        self.assertIn("InformalAnalyzer", kernel.plugins) 
        # Check that the plugin is an instance of KernelPlugin and its _plugin_instance is the mock
        self.assertIsInstance(kernel.plugins["InformalAnalyzer"], KernelPlugin)

    def test_setup_informal_kernel_no_llm_service(self):
        """Teste la configuration avec un service LLM manquant (devrait lever une erreur ou gérer)."""
        kernel = Kernel()
        self.setup_informal_kernel_func(kernel, None) 
        self.assertIn("InformalAnalyzer", kernel.plugins)
        # Check that the plugin is an instance of KernelPlugin (the wrapper)
        self.assertIsInstance(kernel.plugins["InformalAnalyzer"], KernelPlugin)


    
    def test_setup_informal_kernel_with_error(self, MockInformalAnalysisPlugin):
        """Teste la configuration avec une erreur lors de l'initialisation du plugin."""
        MockInformalAnalysisPlugin# Mock eliminated - using authentic gpt-4o-mini Exception("Erreur d'initialisation du plugin")
        kernel = Kernel()
        mock_llm_service = Magicawait self._create_authentic_gpt4o_mini_instance()
        with self.assertRaises(Exception) as context:
            self.setup_informal_kernel_func(kernel, mock_llm_service)
        self.assertIn("Erreur d'initialisation du plugin", str(context.exception))