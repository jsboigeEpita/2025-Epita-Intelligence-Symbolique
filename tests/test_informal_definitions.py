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

# Importer les mocks pour pandas
from tests.mocks.pandas_mock import *

# Patcher pandas avant d'importer le module à tester
sys.modules['pandas'] = sys.modules.get('pandas')

# Mock pour semantic_kernel
class MockSemanticKernel:
    """Mock pour semantic_kernel."""
    
    def __init__(self):
        self.plugins = {}
    
    def add_plugin(self, plugin, name):
        """Ajoute un plugin au kernel."""
        self.plugins[name] = plugin
    
    def create_semantic_function(self, prompt, function_name=None, plugin_name=None, description=None, max_tokens=None, temperature=None, top_p=None):
        """Crée une fonction sémantique."""
        return MagicMock()
    
    def register_semantic_function(self, function, plugin_name, function_name):
        """Enregistre une fonction sémantique."""
        if plugin_name not in self.plugins:
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
        self.assertEqual(len(df.columns), 6)  # PK, Name, Category, Description, Example, Counter_Example
        self.assertEqual(len(df._data[df.columns[0]]), 3)  # 3 lignes
    
    def test_get_fallacy_hierarchy(self):
        """Teste la méthode get_fallacy_hierarchy."""
        # Appeler la méthode get_fallacy_hierarchy
        hierarchy = self.plugin.get_fallacy_hierarchy()
        
        # Vérifier que la hiérarchie est correcte
        self.assertIsInstance(hierarchy, dict)
        self.assertIn("fallacies", hierarchy)
        self.assertIsInstance(hierarchy["fallacies"], list)
        self.assertEqual(len(hierarchy["fallacies"]), 3)  # 3 sophismes
    
    def test_get_fallacy_details(self):
        """Teste la méthode get_fallacy_details."""
        # Appeler la méthode get_fallacy_details pour un sophisme existant
        details = self.plugin.get_fallacy_details("Appel à l'autorité")
        
        # Vérifier que les détails sont corrects
        self.assertIsInstance(details, dict)
        self.assertIn("name", details)
        self.assertIn("category", details)
        self.assertIn("description", details)
        self.assertIn("example", details)
        self.assertIn("counter_example", details)
        self.assertEqual(details["name"], "Appel à l'autorité")
        
        # Appeler la méthode get_fallacy_details pour un sophisme inexistant
        details = self.plugin.get_fallacy_details("Sophisme inexistant")
        
        # Vérifier que les détails sont None
        self.assertIsNone(details)
    
    def test_get_fallacy_examples(self):
        """Teste la méthode get_fallacy_examples."""
        # Appeler la méthode get_fallacy_examples pour un sophisme existant
        examples = self.plugin.get_fallacy_examples("Appel à l'autorité")
        
        # Vérifier que les exemples sont corrects
        self.assertIsInstance(examples, dict)
        self.assertIn("example", examples)
        self.assertIn("counter_example", examples)
        self.assertIsInstance(examples["example"], str)
        self.assertIsInstance(examples["counter_example"], str)
        
        # Appeler la méthode get_fallacy_examples pour un sophisme inexistant
        examples = self.plugin.get_fallacy_examples("Sophisme inexistant")
        
        # Vérifier que les exemples sont None
        self.assertIsNone(examples)
    
    def test_search_fallacies(self):
        """Teste la méthode search_fallacies."""
        # Appeler la méthode search_fallacies avec un terme de recherche
        results = self.plugin.search_fallacies("autorité")
        
        # Vérifier que les résultats sont corrects
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Appel à l'autorité")
        
        # Appeler la méthode search_fallacies avec un terme de recherche qui ne correspond à aucun sophisme
        results = self.plugin.search_fallacies("terme inexistant")
        
        # Vérifier que les résultats sont vides
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)
    
    def test_setup_informal_kernel(self):
        """Teste la fonction setup_informal_kernel."""
        # Créer un kernel mock
        kernel = MockSemanticKernel()
        
        # Créer un service LLM mock
        llm_service = MagicMock()
        
        # Appeler la fonction setup_informal_kernel
        setup_informal_kernel(kernel, llm_service)
        
        # Vérifier que le plugin a été ajouté au kernel
        self.assertIn("InformalAnalysis", kernel.plugins)


if __name__ == "__main__":
    unittest.main()