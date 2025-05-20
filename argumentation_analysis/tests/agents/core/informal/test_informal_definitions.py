"""
Tests unitaires pour le module informal_definitions.

Ce module contient les tests unitaires pour les classes et fonctions définies dans le module
agents.core.informal.informal_definitions.
"""

import unittest
import json
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from argumentation_analysis.agents.core.informal.informal_definitions import (
    InformalAnalysisPlugin, setup_informal_kernel
)


class TestInformalAnalysisPlugin(unittest.TestCase):
    """Tests pour la classe InformalAnalysisPlugin."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Patch pour éviter le chargement réel de la taxonomie
        self.taxonomy_path_patcher = patch('argumentation_analysis.agents.core.informal.informal_definitions.get_taxonomy_path')
        self.mock_get_taxonomy_path = self.taxonomy_path_patcher.start()
        self.mock_get_taxonomy_path.return_value = "mock_taxonomy_path.csv"
        
        self.validate_taxonomy_patcher = patch('argumentation_analysis.agents.core.informal.informal_definitions.validate_taxonomy_file')
        self.mock_validate_taxonomy = self.validate_taxonomy_patcher.start()
        self.mock_validate_taxonomy.return_value = True
        
        # Patch pour pd.read_csv et DataFrame
        self.pandas_patcher = patch('argumentation_analysis.agents.core.informal.informal_definitions.pd')
        self.mock_pandas = self.pandas_patcher.start()
        
        # Créer un mock pour le DataFrame
        self.test_df = MagicMock()
        self.test_df.__len__.return_value = 4
        self.test_df.index = [0, 1, 2, 3]
        self.test_df.columns = ['FK_Parent', 'depth', 'path', 'nom_vulgarisé', 'text_fr', 'description_fr', 'exemple_fr']
        
        # Configurer le comportement du DataFrame pour les accès aux données
        def mock_loc_getitem(key):
            if key == [0]:
                row = MagicMock()
                row.name = 0
                row.get.side_effect = lambda k, default=None: {
                    'path': '0', 'depth': 0, 'nom_vulgarisé': 'Racine',
                    'text_fr': 'Racine des sophismes', 'description_fr': 'Description racine'
                }.get(k, default)
                return [row]
            elif key == [1]:
                row = MagicMock()
                row.name = 1
                row.get.side_effect = lambda k, default=None: {
                    'path': '0.1', 'depth': 1, 'nom_vulgarisé': 'Sophisme 1',
                    'text_fr': 'Description sophisme 1', 'description_fr': 'Description détaillée 1'
                }.get(k, default)
                return [row]
            elif key == [2]:
                row = MagicMock()
                row.name = 2
                row.get.side_effect = lambda k, default=None: {
                    'path': '0.2', 'depth': 1, 'nom_vulgarisé': 'Sophisme 2',
                    'text_fr': 'Description sophisme 2', 'description_fr': 'Description détaillée 2'
                }.get(k, default)
                return [row]
            elif key == [3]:
                row = MagicMock()
                row.name = 3
                row.get.side_effect = lambda k, default=None: {
                    'path': '0.1.3', 'depth': 2, 'nom_vulgarisé': 'Sophisme 3',
                    'text_fr': 'Description sophisme 3', 'description_fr': 'Description détaillée 3'
                }.get(k, default)
                return [row]
            else:
                return MagicMock(__len__=lambda: 0)
        
        self.test_df.loc.__getitem__.side_effect = mock_loc_getitem
        
        # Configurer le comportement pour les filtres
        filtered_df = MagicMock()
        filtered_df.__len__.return_value = 2
        filtered_df.iterrows.return_value = [
            (1, MagicMock(name=1, get=lambda k, default=None: 'Sophisme 1' if k == 'nom_vulgarisé' else 'Description sophisme 1' if k == 'text_fr' else default)),
            (2, MagicMock(name=2, get=lambda k, default=None: 'Sophisme 2' if k == 'nom_vulgarisé' else 'Description sophisme 2' if k == 'text_fr' else default))
        ]
        self.test_df.__getitem__.return_value = filtered_df
        
        self.mock_pandas.read_csv.return_value = self.test_df
        
        # Créer l'instance à tester
        self.plugin = InformalAnalysisPlugin()

    def tearDown(self):
        """Nettoyage après chaque test."""
        self.taxonomy_path_patcher.stop()
        self.validate_taxonomy_patcher.stop()
        self.pandas_patcher.stop()

    def test_init(self):
        """Teste l'initialisation de la classe."""
        self.assertIsNotNone(self.plugin)
        self.assertEqual(self.plugin.FALLACY_CSV_URL, 
                         "https://raw.githubusercontent.com/ArgumentumGames/Argumentum/master/Cards/Fallacies/Argumentum%20Fallacies%20-%20Taxonomy.csv")
        self.assertIsNone(self.plugin._taxonomy_df_cache)

    def test_get_taxonomy_dataframe(self):
        """Teste la récupération du DataFrame de taxonomie."""
        # Premier appel - devrait charger le DataFrame
        df = self.plugin._get_taxonomy_dataframe()
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 4)
        self.mock_pandas.read_csv.assert_called_once()
        
        # Deuxième appel - devrait utiliser le cache
        df2 = self.plugin._get_taxonomy_dataframe()
        self.assertIs(df, df2)
        self.mock_pandas.read_csv.assert_called_once()  # Toujours appelé une seule fois

    def test_internal_load_and_prepare_dataframe(self):
        """Teste le chargement et la préparation du DataFrame."""
        df = self.plugin._internal_load_and_prepare_dataframe()
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 4)
        self.mock_get_taxonomy_path.assert_called_once()
        self.mock_validate_taxonomy.assert_called_once()
        self.mock_pandas.read_csv.assert_called_once_with("mock_taxonomy_path.csv", encoding='utf-8')

    def test_internal_load_and_prepare_dataframe_error(self):
        """Teste le chargement du DataFrame avec une erreur."""
        self.mock_validate_taxonomy.return_value = False
        
        with self.assertRaises(Exception):
            self.plugin._internal_load_and_prepare_dataframe()

    def test_internal_explore_hierarchy(self):
        """Teste l'exploration de la hiérarchie des sophismes."""
        # Tester avec un nœud existant (racine)
        result = self.plugin._internal_explore_hierarchy(0, self.test_df)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result["current_node"])
        self.assertEqual(result["current_node"]["pk"], 0)
        self.assertEqual(result["current_node"]["nom_vulgarisé"], "Racine")
        self.assertEqual(len(result["children"]), 2)  # Deux enfants directs (PK 1 et 2)
        
        # Tester avec un nœud existant (avec enfants)
        result = self.plugin._internal_explore_hierarchy(1, self.test_df)
        self.assertIsNotNone(result)
        self.assertEqual(result["current_node"]["pk"], 1)
        self.assertEqual(result["current_node"]["nom_vulgarisé"], "Sophisme 1")
        self.assertEqual(len(result["children"]), 1)  # Un enfant direct (PK 3)
        
        # Tester avec un nœud existant (sans enfants)
        result = self.plugin._internal_explore_hierarchy(3, self.test_df)
        self.assertIsNotNone(result)
        self.assertEqual(result["current_node"]["pk"], 3)
        self.assertEqual(result["current_node"]["nom_vulgarisé"], "Sophisme 3")
        self.assertEqual(len(result["children"]), 0)  # Pas d'enfants
        
        # Tester avec un nœud inexistant
        result = self.plugin._internal_explore_hierarchy(99, self.test_df)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result["error"])
        self.assertIn("PK 99 non trouvée", result["error"])

    def test_internal_get_node_details(self):
        """Teste la récupération des détails d'un nœud."""
        # Tester avec un nœud existant
        result = self.plugin._internal_get_node_details(1, self.test_df)
        self.assertIsNotNone(result)
        self.assertEqual(result["pk"], 1)
        self.assertEqual(result["nom_vulgarisé"], "Sophisme 1")
        self.assertEqual(result["text_fr"], "Description sophisme 1")
        self.assertEqual(result["description_fr"], "Description détaillée 1")
        self.assertEqual(result["exemple_fr"], "Exemple 1")
        
        # Tester avec un nœud inexistant
        result = self.plugin._internal_get_node_details(99, self.test_df)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result["error"])
        self.assertIn("PK 99 non trouvée", result["error"])

    def test_explore_fallacy_hierarchy(self):
        """Teste la méthode publique d'exploration de la hiérarchie."""
        # Tester avec un nœud existant
        result_json = self.plugin.explore_fallacy_hierarchy("1")
        result = json.loads(result_json)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result["current_node"])
        self.assertEqual(result["current_node"]["pk"], 1)
        self.assertEqual(result["current_node"]["nom_vulgarisé"], "Sophisme 1")
        
        # Tester avec un nœud inexistant
        result_json = self.plugin.explore_fallacy_hierarchy("99")
        result = json.loads(result_json)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result["error"])
        
        # Tester avec une PK invalide
        result_json = self.plugin.explore_fallacy_hierarchy("invalid")
        result = json.loads(result_json)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result["error"])
        self.assertIn("PK invalide", result["error"])

    def test_get_fallacy_details(self):
        """Teste la méthode publique de récupération des détails d'un sophisme."""
        # Tester avec un nœud existant
        result_json = self.plugin.get_fallacy_details("1")
        result = json.loads(result_json)
        self.assertIsNotNone(result)
        self.assertEqual(result["pk"], 1)
        self.assertEqual(result["nom_vulgarisé"], "Sophisme 1")
        
        # Tester avec un nœud inexistant
        result_json = self.plugin.get_fallacy_details("99")
        result = json.loads(result_json)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result["error"])
        
        # Tester avec une PK invalide
        result_json = self.plugin.get_fallacy_details("invalid")
        result = json.loads(result_json)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result["error"])
        self.assertIn("PK invalide", result["error"])


class TestSetupInformalKernel(unittest.TestCase):
    """Tests pour la fonction setup_informal_kernel."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.mock_kernel = MagicMock()
        self.mock_llm_service = MagicMock()
        self.mock_llm_service.service_id = "test_service_id"

    def test_setup_informal_kernel(self):
        """Teste la configuration du kernel pour l'agent informel."""
        # Configurer les mocks
        self.mock_kernel.get_prompt_execution_settings_from_service_id.return_value = {"temperature": 0.7}
        
        # Appeler la fonction à tester
        setup_informal_kernel(self.mock_kernel, self.mock_llm_service)
        
        # Vérifier que le plugin a été ajouté au kernel
        self.mock_kernel.add_plugin.assert_called_once()
        
        # Vérifier que les fonctions sémantiques ont été ajoutées
        self.assertEqual(self.mock_kernel.add_function.call_count, 3)
        
        # Vérifier que les settings LLM ont été récupérés
        self.mock_kernel.get_prompt_execution_settings_from_service_id.assert_called_once_with("test_service_id")

    def test_setup_informal_kernel_no_llm_service(self):
        """Teste la configuration du kernel sans service LLM."""
        # Appeler la fonction à tester
        setup_informal_kernel(self.mock_kernel, None)
        
        # Vérifier que le plugin a été ajouté au kernel
        self.mock_kernel.add_plugin.assert_called_once()
        
        # Vérifier que les fonctions sémantiques ont été ajoutées
        self.assertEqual(self.mock_kernel.add_function.call_count, 3)
        
        # Vérifier que les settings LLM n'ont pas été récupérés
        self.mock_kernel.get_prompt_execution_settings_from_service_id.assert_not_called()

    def test_setup_informal_kernel_with_error(self):
        """Teste la configuration du kernel avec une erreur lors de l'ajout des fonctions."""
        # Configurer les mocks pour lever une exception
        self.mock_kernel.add_function.side_effect = ValueError("Erreur test")
        
        # Appeler la fonction à tester
        setup_informal_kernel(self.mock_kernel, self.mock_llm_service)
        
        # Vérifier que le plugin a été ajouté au kernel
        self.mock_kernel.add_plugin.assert_called_once()
        
        # Vérifier que la fonction add_function a été appelée
        self.mock_kernel.add_function.assert_called()


if __name__ == "__main__":
    unittest.main()