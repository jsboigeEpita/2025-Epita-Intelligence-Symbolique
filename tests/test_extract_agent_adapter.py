#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module orchestration.hierarchical.operational.adapters.extract_agent_adapter.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestExtractAgentAdapter")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Import des modules à tester
from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState


# Mock pour ExtractAgent
class MockExtractAgent:
    """Mock pour la classe ExtractAgent."""
    
    def __init__(self):
        self.extract_text = AsyncMock(return_value={
            "status": "success",
            "extracts": [
                {
                    "id": "extract-1",
                    "text": "Ceci est un extrait de test",
                    "source": "test-source",
                    "confidence": 0.9
                }
            ]
        })
        
        self.validate_extracts = AsyncMock(return_value={
            "status": "success",
            "valid_extracts": [
                {
                    "id": "extract-1",
                    "text": "Ceci est un extrait de test",
                    "source": "test-source",
                    "confidence": 0.9,
                    "validation_score": 0.95
                }
            ]
        })
        
        self.preprocess_text = AsyncMock(return_value={
            "status": "success",
            "preprocessed_text": "Ceci est un texte prétraité",
            "metadata": {
                "word_count": 5,
                "language": "fr"
            }
        })


# Mock pour setup_extract_agent
async def mock_setup_extract_agent():
    """Mock pour la fonction setup_extract_agent."""
    kernel = MagicMock()
    extract_agent = MockExtractAgent()
    return kernel, extract_agent


class TestExtractAgentAdapter(unittest.TestCase):
    """Tests unitaires pour l'adaptateur d'agent d'extraction."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un état opérationnel mock
        self.operational_state = OperationalState()
        
        # Patcher les imports pour utiliser nos mocks
        self.patches = []
        
        # Patcher setup_extract_agent
        setup_extract_agent_patch = patch('argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.setup_extract_agent', 
                                         side_effect=mock_setup_extract_agent)
        self.patches.append(setup_extract_agent_patch)
        setup_extract_agent_patch.start()
        
        # Créer l'adaptateur d'agent d'extraction
        self.adapter = ExtractAgentAdapter(name="TestExtractAgent", operational_state=self.operational_state)
        
        # Exécuter initialize() de manière synchrone
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.adapter.initialize())
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter tous les patchers
        for patcher in self.patches:
            patcher.stop()
    
    def test_initialization(self):
        """Teste l'initialisation de l'adaptateur d'agent d'extraction."""
        # Vérifier que l'adaptateur a été correctement initialisé
        self.assertIsNotNone(self.adapter)
        self.assertEqual(self.adapter.name, "TestExtractAgent")
        self.assertEqual(self.adapter.state, self.operational_state)
        self.assertIsNotNone(self.adapter.extract_agent)
        self.assertIsNotNone(self.adapter.kernel)
        self.assertTrue(self.adapter.initialized)
    
    def test_get_capabilities(self):
        """Teste la méthode get_capabilities."""
        # Appeler la méthode get_capabilities
        capabilities = self.adapter.get_capabilities()
        
        # Vérifier que les capacités sont correctes
        self.assertIsInstance(capabilities, list)
        self.assertIn("text_extraction", capabilities)
        self.assertIn("preprocessing", capabilities)
        self.assertIn("extract_validation", capabilities)
    
    def test_can_process_task(self):
        """Teste la méthode can_process_task."""
        # Créer une tâche que l'adaptateur peut traiter
        task = {
            "id": "task-1",
            "description": "Extraire le texte",
            "required_capabilities": ["text_extraction"]
        }
        
        # Appeler la méthode can_process_task
        can_process = self.adapter.can_process_task(task)
        
        # Vérifier que l'adaptateur peut traiter la tâche
        self.assertTrue(can_process)
        
        # Créer une tâche que l'adaptateur ne peut pas traiter
        task = {
            "id": "task-2",
            "description": "Analyser les sophismes",
            "required_capabilities": ["fallacy_detection"]
        }
        
        # Appeler la méthode can_process_task
        can_process = self.adapter.can_process_task(task)
        
        # Vérifier que l'adaptateur ne peut pas traiter la tâche
        self.assertFalse(can_process)
    
    def test_process_task_extract_text(self):
        """Teste la méthode process_task pour l'extraction de texte."""
        # Créer une tâche d'extraction de texte
        task = {
            "id": "task-1",
            "description": "Extraire le texte",
            "required_capabilities": ["text_extraction"],
            "parameters": {
                "text": "Ceci est un texte à extraire",
                "source": "test-source"
            }
        }
        
        # Exécuter process_task de manière synchrone
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.adapter.process_task(task))
        
        # Vérifier que le résultat est correct
        self.assertEqual(result["status"], "success")
        self.assertIn("extracts", result)
        self.assertEqual(len(result["extracts"]), 1)
        self.assertEqual(result["extracts"][0]["id"], "extract-1")
        
        # Vérifier que la méthode extract_text de l'agent d'extraction a été appelée
        self.adapter.extract_agent.extract_text.assert_called_once()
    
    def test_process_task_validate_extracts(self):
        """Teste la méthode process_task pour la validation d'extraits."""
        # Créer une tâche de validation d'extraits
        task = {
            "id": "task-2",
            "description": "Valider les extraits",
            "required_capabilities": ["extract_validation"],
            "parameters": {
                "extracts": [
                    {
                        "id": "extract-1",
                        "text": "Ceci est un extrait à valider",
                        "source": "test-source"
                    }
                ]
            }
        }
        
        # Exécuter process_task de manière synchrone
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.adapter.process_task(task))
        
        # Vérifier que le résultat est correct
        self.assertEqual(result["status"], "success")
        self.assertIn("valid_extracts", result)
        self.assertEqual(len(result["valid_extracts"]), 1)
        self.assertEqual(result["valid_extracts"][0]["id"], "extract-1")
        
        # Vérifier que la méthode validate_extracts de l'agent d'extraction a été appelée
        self.adapter.extract_agent.validate_extracts.assert_called_once()
    
    def test_process_task_preprocess_text(self):
        """Teste la méthode process_task pour le prétraitement de texte."""
        # Créer une tâche de prétraitement de texte
        task = {
            "id": "task-3",
            "description": "Prétraiter le texte",
            "required_capabilities": ["preprocessing"],
            "parameters": {
                "text": "Ceci est un texte à prétraiter"
            }
        }
        
        # Exécuter process_task de manière synchrone
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.adapter.process_task(task))
        
        # Vérifier que le résultat est correct
        self.assertEqual(result["status"], "success")
        self.assertIn("preprocessed_text", result)
        self.assertEqual(result["preprocessed_text"], "Ceci est un texte prétraité")
        
        # Vérifier que la méthode preprocess_text de l'agent d'extraction a été appelée
        self.adapter.extract_agent.preprocess_text.assert_called_once()
    
    def test_process_task_unknown_capability(self):
        """Teste la méthode process_task pour une capacité inconnue."""
        # Créer une tâche avec une capacité inconnue
        task = {
            "id": "task-4",
            "description": "Tâche inconnue",
            "required_capabilities": ["unknown_capability"],
            "parameters": {}
        }
        
        # Exécuter process_task de manière synchrone
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.adapter.process_task(task))
        
        # Vérifier que le résultat indique une erreur
        self.assertEqual(result["status"], "error")
        self.assertIn("message", result)
        self.assertIn("unknown_capability", result["message"])
    
    def test_process_task_missing_parameters(self):
        """Teste la méthode process_task avec des paramètres manquants."""
        # Créer une tâche d'extraction de texte sans paramètres
        task = {
            "id": "task-5",
            "description": "Extraire le texte",
            "required_capabilities": ["text_extraction"],
            "parameters": {}  # Paramètres manquants
        }
        
        # Exécuter process_task de manière synchrone
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.adapter.process_task(task))
        
        # Vérifier que le résultat indique une erreur
        self.assertEqual(result["status"], "error")
        self.assertIn("message", result)
        self.assertIn("paramètres requis", result["message"].lower())
    
    def test_shutdown(self):
        """Teste la méthode shutdown."""
        # Exécuter shutdown de manière synchrone
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.adapter.shutdown())
        
        # Vérifier que le résultat est correct
        self.assertTrue(result)
        self.assertFalse(self.adapter.initialized)
        self.assertIsNone(self.adapter.extract_agent)
        self.assertIsNone(self.adapter.kernel)


if __name__ == "__main__":
    unittest.main()