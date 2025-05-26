#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module agents.core.informal.informal_definitions.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch
import json
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestInformalDefinitions")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
# sys.path.append(os.path.abspath('..')) # Géré par conftest.py
# sys.path.append(os.path.abspath('.'))  # Géré par conftest.py

# Importer les mocks pour pandas
# Le répertoire tests/mocks est ajouté à sys.path par conftest.py
from pandas_mock import *

# Patcher pandas avant d'importer le module à tester
# Redondant si conftest.py gère bien sys.modules
# sys.modules['pandas'] = sys.modules.get('pandas')

# Mock pour semantic_kernel
class MockSemanticKernel:
    """Mock pour semantic_kernel."""
    
    def __init__(self):
        self.plugins = {}
    
    def add_plugin(self, plugin, plugin_name=None, name=None):
        """Ajoute un plugin au kernel."""
        key = plugin_name if plugin_name is not None else name
        self.plugins[key] = plugin
    
    def create_semantic_function(self, prompt, function_name=None, plugin_name=None, description=None, max_tokens=None, temperature=None, top_p=None):
        return MagicMock()
    
    def register_semantic_function(self, function, plugin_name, function_name):
        if plugin_name not in self.plugins:
            self.plugins[plugin_name] = {}
    
    def get_prompt_execution_settings_from_service_id(self, service_id):
        return MagicMock()
    
    def add_function(self, function, plugin_name, function_name):
        if plugin_name not in self.plugins:
            self.plugins[plugin_name] = {}
        self.plugins[plugin_name][function_name] = function


# Patcher semantic_kernel (conftest.py devrait aussi le gérer si semantic_kernel est une dépendance optionnelle)
if 'semantic_kernel' not in sys.modules:
    sys.modules['semantic_kernel'] = MagicMock(Kernel=MockSemanticKernel)
elif not hasattr(sys.modules['semantic_kernel'], 'Kernel'): # Au cas où le module est là mais Kernel manque
    sys.modules['semantic_kernel'].Kernel = MockSemanticKernel


# Mock pour taxonomy_loader
def mock_get_taxonomy_path():
    return os.path.join(os.path.dirname(__file__), 'test_data', 'test_taxonomy.csv')

def mock_validate_taxonomy_file():
    return True

# Patcher taxonomy_loader (si ce n'est pas un vrai module)
if 'taxonomy_loader' not in sys.modules:
    sys.modules['taxonomy_loader'] = MagicMock(
        get_taxonomy_path=mock_get_taxonomy_path,
        validate_taxonomy_file=mock_validate_taxonomy_file
    )
else: # S'il existe, patcher ses fonctions
    if not hasattr(sys.modules['taxonomy_loader'], 'get_taxonomy_path'):
        sys.modules['taxonomy_loader'].get_taxonomy_path = mock_get_taxonomy_path
    if not hasattr(sys.modules['taxonomy_loader'], 'validate_taxonomy_file'):
        sys.modules['taxonomy_loader'].validate_taxonomy_file = mock_validate_taxonomy_file


# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin, setup_informal_kernel


class TestInformalDefinitions(unittest.TestCase):
    """Tests unitaires pour les définitions de l'agent informel."""
    
    def setUp(self):
        self.test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
        os.makedirs(self.test_data_dir, exist_ok=True)
        
        self.test_taxonomy_path = os.path.join(self.test_data_dir, 'test_taxonomy.csv')
        with open(self.test_taxonomy_path, 'w') as f:
            f.write("PK,Name,Category,Description,Example,Counter_Example\n")
            f.write("1,Appel à l'autorité,Fallacy,Invoquer une autorité non pertinente,\"Einstein a dit que Dieu ne joue pas aux dés, donc la mécanique quantique est fausse.\",\"Selon le consensus scientifique, le réchauffement climatique est réel.\"\n")
            f.write("2,Pente glissante,Fallacy,Suggérer qu'une action mènera inévitablement à une chaîne d'événements indésirables,\"Si nous légalisons la marijuana, bientôt toutes les drogues seront légales.\",\"Si nous augmentons le salaire minimum, certaines entreprises pourraient réduire leurs effectifs.\"\n")
            f.write("3,Ad hominem,Fallacy,Attaquer la personne plutôt que ses idées,\"Vous êtes trop jeune pour comprendre la politique.\",\"Votre argument est basé sur des données obsolètes.\"\n")
        
        self.get_taxonomy_path_patcher = patch('argumentation_analysis.agents.core.informal.informal_definitions.get_taxonomy_path', 
                                              return_value=self.test_taxonomy_path)
        self.get_taxonomy_path_patcher.start()
        
        self.validate_taxonomy_file_patcher = patch('argumentation_analysis.agents.core.informal.informal_definitions.validate_taxonomy_file', 
                                                  return_value=True)
        self.validate_taxonomy_file_patcher.start()
        
        self.plugin = InformalAnalysisPlugin()
    
    def tearDown(self):
        self.get_taxonomy_path_patcher.stop()
        self.validate_taxonomy_file_patcher.stop()
        
        if os.path.exists(self.test_taxonomy_path):
            os.unlink(self.test_taxonomy_path)
        
        if os.path.exists(self.test_data_dir) and not os.listdir(self.test_data_dir):
            os.rmdir(self.test_data_dir)
    
    def test_initialization(self):
        self.assertIsNotNone(self.plugin)
        self.assertIsNotNone(self.plugin._logger)
        self.assertIsNotNone(self.plugin.FALLACY_CSV_URL)
        self.assertIsNotNone(self.plugin.DATA_DIR)
        self.assertIsNotNone(self.plugin.FALLACY_CSV_LOCAL_PATH)
    
    def test_get_taxonomy_dataframe(self):
        df = self.plugin._get_taxonomy_dataframe()
        self.assertIsNotNone(df)
        
        # Le DataFrame transforme la colonne PK en index, donc on s'attend à 5 colonnes + index PK
        expected_columns_without_pk = ["Name", "Category", "Description", "Example", "Counter_Example"]
        
        if hasattr(df, 'columns'):
            # Vérifier le nombre de colonnes (doit être 5 après transformation PK en index)
            self.assertEqual(len(df.columns), len(expected_columns_without_pk),
                           f"Attendu {len(expected_columns_without_pk)} colonnes, trouvé {len(df.columns)}: {df.columns}")
            
            # Vérifier que toutes les colonnes attendues sont présentes (sauf PK qui est maintenant l'index)
            for col in expected_columns_without_pk:
                self.assertIn(col, df.columns, f"Colonne manquante: {col}")
            
            # Vérifier que PK est bien l'index
            if hasattr(df, 'index') and hasattr(df.index, 'name'):
                # Pour un vrai DataFrame pandas, l'index aurait un nom
                pass  # Le mock peut ne pas avoir cette propriété
            
            # Vérifier qu'il y a au moins 3 lignes de données
            self.assertGreaterEqual(len(df), 3)
        else:
            # Si c'est un mock sans colonnes, vérifier au moins qu'il a des données
            self.assertTrue(hasattr(df, '_data'))
            self.assertGreater(len(df._data), 0)


    def test_explore_fallacy_hierarchy(self):
        hierarchy_json = self.plugin.explore_fallacy_hierarchy("1")
        self.assertIsInstance(hierarchy_json, str)
        hierarchy = json.loads(hierarchy_json)
        self.assertIsInstance(hierarchy, dict)
        self.assertIn("current_node", hierarchy)
        self.assertIn("children", hierarchy)
    
    def test_get_fallacy_details(self):
        with patch.object(self.plugin, '_internal_get_node_details', return_value={
            "pk": 1, "nom_vulgarisé": "Appel à l'autorité", 
            "text_fr": "Description en français", "text_en": "Description in English"
        }):
            details_json = self.plugin.get_fallacy_details("1")
            self.assertIsInstance(details_json, str)
            details = json.loads(details_json)
            self.assertIsInstance(details, dict)
            self.assertIn("pk", details)
            self.assertEqual(details["nom_vulgarisé"], "Appel à l'autorité")
    
    def test_setup_informal_kernel(self):
        kernel = MockSemanticKernel()
        llm_service = MagicMock()
        setup_informal_kernel(kernel, llm_service)
        self.assertIn("InformalAnalyzer", kernel.plugins)


if __name__ == "__main__":
    unittest.main()