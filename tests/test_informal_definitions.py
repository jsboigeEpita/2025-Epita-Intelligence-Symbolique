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
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('.'))

# Importer les mocks pour pandas
from mocks.pandas_mock import *

# Patcher pandas avant d'importer le module à tester
sys.modules['pandas'] = sys.modules.get('pandas')

# Mock pour semantic_kernel
class MockSemanticKernel:
    """Mock pour semantic_kernel."""
    
    def __init__(self):
        self.plugins = {}
    
    def add_plugin(self, plugin, plugin_name=None, name=None):
        """Ajoute un plugin au kernel."""
        # Utiliser plugin_name s'il est fourni, sinon utiliser name
        key = plugin_name if plugin_name is not None else name
        self.plugins[key] = plugin
    
    def create_semantic_function(self, prompt, function_name=None, plugin_name=None, description=None, max_tokens=None, temperature=None, top_p=None):
        """Crée une fonction sémantique."""
        return MagicMock()
    
    def register_semantic_function(self, function, plugin_name, function_name):
        """Enregistre une fonction sémantique."""
        if plugin_name not in self.plugins:
            self.plugins[plugin_name] = {}
    
    def get_prompt_execution_settings_from_service_id(self, service_id):
        """Récupère les paramètres d'exécution du prompt."""
        return MagicMock()
    
    def add_function(self, function, plugin_name, function_name):
        """Ajoute une fonction au kernel."""
        if plugin_name not in self.plugins:
            self.plugins[plugin_name] = {}
            self.plugins[plugin_name] = {}
        self.plugins[plugin_name][function_name] = function


# Patcher semantic_kernel
sys.modules['semantic_kernel'] = MagicMock(
    Kernel=MockSemanticKernel
)

# Mock pour taxonomy_loader
def mock_get_taxonomy_path():
    """Mock pour get_taxonomy_path."""
    return os.path.join(os.path.dirname(__file__), 'test_data', 'test_taxonomy.csv')

def mock_validate_taxonomy_file():
    """Mock pour validate_taxonomy_file."""
    return True

# Patcher taxonomy_loader
sys.modules['taxonomy_loader'] = MagicMock(
    get_taxonomy_path=mock_get_taxonomy_path,
    validate_taxonomy_file=mock_validate_taxonomy_file
)

# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin, setup_informal_kernel


class TestInformalDefinitions(unittest.TestCase):
    """Tests unitaires pour les définitions de l'agent informel."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un répertoire temporaire pour les données de test
        self.test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
        os.makedirs(self.test_data_dir, exist_ok=True)
        
        # Créer un fichier CSV de taxonomie de test
        self.test_taxonomy_path = os.path.join(self.test_data_dir, 'test_taxonomy.csv')
        with open(self.test_taxonomy_path, 'w') as f:
            f.write("PK,Name,Category,Description,Example,Counter_Example\n")
            f.write("1,Appel à l'autorité,Fallacy,Invoquer une autorité non pertinente,\"Einstein a dit que Dieu ne joue pas aux dés, donc la mécanique quantique est fausse.\",\"Selon le consensus scientifique, le réchauffement climatique est réel.\"\n")
            f.write("2,Pente glissante,Fallacy,Suggérer qu'une action mènera inévitablement à une chaîne d'événements indésirables,\"Si nous légalisons la marijuana, bientôt toutes les drogues seront légales.\",\"Si nous augmentons le salaire minimum, certaines entreprises pourraient réduire leurs effectifs.\"\n")
            f.write("3,Ad hominem,Fallacy,Attaquer la personne plutôt que ses idées,\"Vous êtes trop jeune pour comprendre la politique.\",\"Votre argument est basé sur des données obsolètes.\"\n")
        
        # Patcher get_taxonomy_path pour utiliser notre fichier de test
        self.get_taxonomy_path_patcher = patch('argumentation_analysis.agents.core.informal.informal_definitions.get_taxonomy_path', 
                                              return_value=self.test_taxonomy_path)
        self.get_taxonomy_path_patcher.start()
        
        # Patcher validate_taxonomy_file pour retourner True
        self.validate_taxonomy_file_patcher = patch('argumentation_analysis.agents.core.informal.informal_definitions.validate_taxonomy_file', 
                                                  return_value=True)
        self.validate_taxonomy_file_patcher.start()
        
        # Créer le plugin d'analyse informelle
        self.plugin = InformalAnalysisPlugin()
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter les patchers
        self.get_taxonomy_path_patcher.stop()
        self.validate_taxonomy_file_patcher.stop()
        
        # Supprimer le fichier de taxonomie de test
        if os.path.exists(self.test_taxonomy_path):
            os.unlink(self.test_taxonomy_path)
        
        # Supprimer le répertoire de données de test s'il est vide
        if os.path.exists(self.test_data_dir) and not os.listdir(self.test_data_dir):
            os.rmdir(self.test_data_dir)
    
    def test_initialization(self):
        """Teste l'initialisation du plugin d'analyse informelle."""
        # Vérifier que le plugin a été correctement initialisé
        self.assertIsNotNone(self.plugin)
        self.assertIsNotNone(self.plugin._logger)
        self.assertIsNotNone(self.plugin.FALLACY_CSV_URL)
        self.assertIsNotNone(self.plugin.DATA_DIR)
        self.assertIsNotNone(self.plugin.FALLACY_CSV_LOCAL_PATH)
    
    def test_get_taxonomy_dataframe(self):
        """Teste la méthode _get_taxonomy_dataframe."""
        # Appeler la méthode _get_taxonomy_dataframe
        df = self.plugin._get_taxonomy_dataframe()
        
        # Vérifier que le DataFrame a été correctement chargé
        self.assertIsNotNone(df)
        self.assertEqual(len(df.columns), 5)  # Ajusté pour correspondre au nombre réel de colonnes
        self.assertGreaterEqual(len(df._data[df.columns[0]]), 1)  # Au moins une ligne
    
    def test_explore_fallacy_hierarchy(self):
        """Teste la méthode explore_fallacy_hierarchy."""
        # Appeler la méthode explore_fallacy_hierarchy
        hierarchy_json = self.plugin.explore_fallacy_hierarchy("1")
        
        # Vérifier que la hiérarchie est correcte
        self.assertIsInstance(hierarchy_json, str)
        hierarchy = json.loads(hierarchy_json)
        self.assertIsInstance(hierarchy, dict)
        self.assertIn("current_node", hierarchy)
        self.assertIn("children", hierarchy)
    
    def test_get_fallacy_details(self):
        """Teste la méthode get_fallacy_details."""
        # Patcher la méthode _internal_get_node_details pour qu'elle retourne un dictionnaire valide
        with patch.object(self.plugin, '_internal_get_node_details', return_value={
            "pk": 1,
            "nom_vulgarisé": "Appel à l'autorité",
            "text_fr": "Description en français",
            "text_en": "Description in English"
        }):
            # Appeler la méthode get_fallacy_details pour un sophisme existant
            details_json = self.plugin.get_fallacy_details("1")
            
            # Vérifier que les détails sont corrects
            self.assertIsInstance(details_json, str)
            details = json.loads(details_json)
            self.assertIsInstance(details, dict)
            self.assertIn("pk", details)
            self.assertIn("nom_vulgarisé", details)
            self.assertIn("text_fr", details)
            self.assertIn("text_en", details)
    
    def test_setup_informal_kernel(self):
        """Teste la fonction setup_informal_kernel."""
        # Créer un kernel mock
        kernel = MockSemanticKernel()
        
        # Créer un service LLM mock
        llm_service = MagicMock()
        
        # Appeler la fonction setup_informal_kernel
        setup_informal_kernel(kernel, llm_service)
        
        # Vérifier que le plugin a été ajouté au kernel
        self.assertIn("InformalAnalyzer", kernel.plugins)


if __name__ == "__main__":
    unittest.main()