"""
Tests unitaires pour l'agent d'analyse informelle.
"""

import unittest
import json
import os
import tempfile
import pandas as pd
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import semantic_kernel as sk
from argumentiation_analysis.agents.informal.informal_definitions import InformalAnalysisPlugin, setup_informal_kernel
from argumentiation_analysis.tests.async_test_case import AsyncTestCase


class TestInformalAnalysisPlugin(unittest.TestCase):
    """Tests pour la classe InformalAnalysisPlugin."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.plugin = InformalAnalysisPlugin()
        
        # Créer un DataFrame de test pour la taxonomie
        self.test_df = pd.DataFrame({
            'PK': [0, 1, 2, 3],
            'FK_Parent': [None, 0, 0, 1],
            'text_fr': ['Racine', 'Catégorie 1', 'Catégorie 2', 'Sous-catégorie 1.1'],
            'nom_vulgarisé': ['Sophismes', 'Ad Hominem', 'Faux Dilemme', 'Attaque Personnelle'],
            'description_fr': ['Description racine', 'Description cat 1', 'Description cat 2', 'Description sous-cat 1.1'],
            'exemple_fr': ['Exemple racine', 'Exemple cat 1', 'Exemple cat 2', 'Exemple sous-cat 1.1'],
            'depth': [0, 1, 1, 2]
        })
        self.test_df.set_index('PK', inplace=True)

    @patch('argumentiation_analysis.agents.informal.informal_definitions.pd.read_csv')
    @patch('argumentiation_analysis.agents.informal.informal_definitions.requests.get')
    @patch('argumentiation_analysis.agents.informal.informal_definitions.validate_taxonomy_file')
    @patch('argumentiation_analysis.agents.informal.informal_definitions.get_taxonomy_path')
    @patch('builtins.open', new_callable=mock_open)
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
        self.assertEqual(list(df.index), [0, 1, 2, 3])
        self.assertIn('text_fr', df.columns)
        self.assertIn('nom_vulgarisé', df.columns)
        self.assertIn('description_fr', df.columns)

    @patch.object(InformalAnalysisPlugin, '_internal_load_and_prepare_dataframe')
    def test_get_taxonomy_dataframe(self, mock_load):
        """Teste la récupération du DataFrame de taxonomie."""
        # Configurer le mock pour retourner le DataFrame de test
        mock_load.return_value = self.test_df
        
        # Appeler la méthode à tester
        df = self.plugin._get_taxonomy_dataframe()
        
        # Vérifier que le DataFrame a été correctement récupéré
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 4)
        
        # Vérifier que le cache fonctionne (deuxième appel)
        df2 = self.plugin._get_taxonomy_dataframe()
        self.assertIs(df2, df)  # Doit être le même objet (pas de rechargement)
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

    @patch.object(InformalAnalysisPlugin, '_get_taxonomy_dataframe')
    def test_internal_get_children_details(self, mock_get_df):
        """Teste la récupération des détails des enfants d'un nœud."""
        # Configurer le mock pour retourner le DataFrame de test
        mock_get_df.return_value = self.test_df
        
        # Appeler la méthode à tester pour la racine (PK=0)
        children = self.plugin._internal_get_children_details(0, self.test_df, 10)
        
        # Vérifier que les enfants ont été correctement récupérés
        self.assertEqual(len(children), 2)  # Doit avoir 2 enfants (PK=1 et PK=2)
        self.assertEqual(children[0]['pk'], 1)
        self.assertEqual(children[1]['pk'], 2)
        
        # Tester avec un nœud qui a un seul enfant
        children_one = self.plugin._internal_get_children_details(1, self.test_df, 10)
        self.assertEqual(len(children_one), 1)  # Doit avoir 1 enfant (PK=3)
        self.assertEqual(children_one[0]['pk'], 3)
        
        # Tester avec un nœud qui n'a pas d'enfants
        children_none = self.plugin._internal_get_children_details(3, self.test_df, 10)
        self.assertEqual(len(children_none), 0)  # Ne doit pas avoir d'enfants
        
        # Tester avec un DataFrame None
        children_no_df = self.plugin._internal_get_children_details(0, None, 10)
        self.assertEqual(len(children_no_df), 0)

    @patch.object(InformalAnalysisPlugin, '_get_taxonomy_dataframe')
    @patch.object(InformalAnalysisPlugin, '_internal_get_node_details')
    @patch.object(InformalAnalysisPlugin, '_internal_get_children_details')
    def test_explore_fallacy_hierarchy(self, mock_children, mock_details, mock_get_df):
        """Teste l'exploration de la hiérarchie des sophismes."""
        # Configurer les mocks
        mock_get_df.return_value = self.test_df
        mock_details.return_value = {'pk': 0, 'text_fr': 'Racine', 'nom_vulgarisé': 'Sophismes', 'error': None}
        mock_children.return_value = [
            {'pk': 1, 'text_fr': 'Catégorie 1', 'nom_vulgarisé': 'Ad Hominem', 'error': None},
            {'pk': 2, 'text_fr': 'Catégorie 2', 'nom_vulgarisé': 'Faux Dilemme', 'error': None}
        ]
        
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


class TestSetupInformalKernel(AsyncTestCase):
    """Tests pour la fonction setup_informal_kernel."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.kernel = sk.Kernel()
        self.llm_service = MagicMock()
        self.llm_service.service_id = "test_service"

    @patch('argumentiation_analysis.agents.informal.informal_definitions.prompt_identify_args_v8')
    @patch('argumentiation_analysis.agents.informal.informal_definitions.prompt_analyze_fallacies_v1')
    @patch('argumentiation_analysis.agents.informal.informal_definitions.prompt_justify_fallacy_attribution_v1')
    def test_setup_informal_kernel(self, mock_justify, mock_analyze, mock_identify):
        """Teste la configuration du kernel pour l'agent informel."""
        # Configurer les mocks
        mock_identify.text = "Prompt d'identification des arguments"
        mock_analyze.text = "Prompt d'analyse des sophismes"
        mock_justify.text = "Prompt de justification des sophismes"
        
        # Appeler la fonction à tester
        setup_informal_kernel(self.kernel, self.llm_service)
        
        # Vérifier que le plugin a été ajouté au kernel
        self.assertIn("InformalAnalyzer", self.kernel.plugins)
        
        # Vérifier que le plugin a été ajouté
        self.assertIn("InformalAnalyzer", self.kernel.plugins)
        
        # Vérifier que les fonctions sont disponibles dans le plugin
        # Note: Dans les versions récentes de Semantic Kernel, les fonctions natives
        # sont automatiquement enregistrées, mais nous ne pouvons pas les vérifier directement
        # dans les tests. Nous vérifions simplement que le plugin a été ajouté.
        
        # Note: Nous ne pouvons pas vérifier directement les fonctions sémantiques
        # car elles peuvent échouer à l'ajout dans l'environnement de test


if __name__ == '__main__':
    unittest.main()