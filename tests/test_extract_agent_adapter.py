#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module orchestration.hierarchical.operational.adapters.extract_agent_adapter.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
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
    def __init__(self, extract_agent=None, validation_agent=None, extract_plugin=None):
        self.extract_agent = extract_agent or Mock()
        self.validation_agent = validation_agent or Mock()
        self.extract_plugin = extract_plugin or Mock()
        self.state = Mock()
        self.state.task_dependencies = {}
        self.state.tasks = {}
        
        # Configuration des méthodes pour retourner les bons statuts
        # Ces mocks directs (extract_text, validate_extracts, preprocess_text)
        # ne sont plus directement utilisés par la nouvelle logique de process_task de l'adaptateur,
        # qui se base sur des "techniques" et appelle _process_extract (utilisant extract_from_name)
        # ou _normalize_text.
        # Nous les gardons pour l'instant au cas où d'autres parties du mock en dépendraient,
        # mais le mock crucial pour les tests actuels sera extract_from_name.
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

        # Mock pour extract_from_name, utilisé par _process_extract
        # ExtractResult est attendu. On utilise MagicMock pour simuler ses attributs.
        self.extract_from_name = AsyncMock(return_value=MagicMock(
            status="valid",
            message="Extraction réussie simulée par extract_from_name",
            explanation="Mock explanation",
            start_marker="<MOCK_START>",
            end_marker="<MOCK_END>",
            template_start="<MOCK_TEMPLATE_START>",
            extracted_text="Texte extrait simulé via extract_from_name"
        ))
        
    def process_extract(self, *args, **kwargs):
        return {"status": "success", "data": []}
    
    def validate_extract(self, *args, **kwargs):
        return True


class MockValidationAgent:
    """Mock pour ValidationAgent."""
    
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
    extract_agent = MockExtractAgent(
        extract_agent=Mock(),
        validation_agent=Mock(),
        extract_plugin=Mock()
    )
    return kernel, extract_agent


class TestExtractAgentAdapter(unittest.TestCase):
    """Tests unitaires pour l'adaptateur d'agent d'extraction."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer les mocks
        self.mock_extract_agent = Mock()
        self.mock_validation_agent = Mock()
        self.mock_extract_plugin = Mock()
        
        # Configuration des mocks pour les tests
        self.mock_extract_agent.process_extract.return_value = {"status": "success"}
        self.mock_validation_agent.validate.return_value = True
        self.mock_extract_plugin.extract.return_value = []
        self.mock_extract_plugin.process_text.return_value = {"status": "success", "data": []}
        self.mock_extract_plugin.get_supported_formats.return_value = ["txt", "pdf", "docx"]
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
        self.assertEqual(self.adapter.operational_state, self.operational_state)
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
            "required_capabilities": ["text_extraction"], # Cette clé n'est plus directement utilisée pour router
            "text_extracts": [{
                "id": "input-extract-1",
                "content": "Ceci est un texte à extraire",
                "source": "test-source"
            }],
            "techniques": [{
                "name": "relevant_segment_extraction",
                "parameters": {}
            }]
        }
        
        # Exécuter process_task de manière synchrone
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.adapter.process_task(task))
        
        # Vérifier que le résultat est correct
        self.assertEqual(result["status"], "completed") # Statut attendu par format_result
        self.assertIn("outputs", result)
        outputs = result["outputs"]
        self.assertIn("extracted_segments", outputs)
        self.assertEqual(len(outputs["extracted_segments"]), 1)
        
        extracted_segment = outputs["extracted_segments"][0]
        self.assertEqual(extracted_segment["extract_id"], "input-extract-1")
        self.assertEqual(extracted_segment["extracted_text"], "Texte extrait simulé via extract_from_name")
        
        # Vérifier que la méthode extract_from_name de l'agent d'extraction a été appelée
        self.adapter.extract_agent.extract_from_name.assert_called_once_with(
            {"source_name": "test-source", "source_text": "Ceci est un texte à extraire"}, # source_info
            "input-extract-1"  # extract_name
        )
    
    def test_process_task_validate_extracts(self):
        """Teste la méthode process_task pour la validation d'extraits."""
        # Créer une tâche de validation d'extraits
        task = {
            "id": "task-2",
            "description": "Valider les extraits",
            "required_capabilities": ["extract_validation"], # Non utilisé directement par la logique de process_task
            "text_extracts": [{ # Fournir text_extracts pour éviter l'erreur initiale
                "id": "extract-to-validate-1",
                "content": "Ceci est un extrait à valider",
                "source": "test-source"
            }],
            "techniques": [{ # Fournir une technique, même si elle ne correspond pas à la validation
                "name": "non_existent_validation_technique",
                "parameters": {}
            }]
        }
        
        # Exécuter process_task de manière synchrone
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.adapter.process_task(task))
        
        # La logique actuelle de process_task ne gère pas "extract_validation" via une technique.
        # Elle devrait donc retourner "completed_with_issues" avec une issue "unsupported_technique".
        self.assertEqual(result["status"], "completed_with_issues")
        self.assertIn("issues", result)
        self.assertTrue(len(result["issues"]) > 0)
        issue = result["issues"][0]
        self.assertEqual(issue["type"], "unsupported_technique")
        self.assertIn("non_existent_validation_technique", issue["description"])
        
        # La méthode validate_extracts du mock ne sera PAS appelée car la logique a changé.
        self.adapter.extract_agent.validate_extracts.assert_not_called()
    
    def test_process_task_preprocess_text(self):
        """Teste la méthode process_task pour le prétraitement de texte."""
        # Créer une tâche de prétraitement de texte
        task = {
            "id": "task-3",
            "description": "Prétraiter le texte",
            "required_capabilities": ["preprocessing"], # Non utilisé directement
            "text_extracts": [{
                "id": "input-text-preprocess-1",
                "content": "Ceci est un texte à prétraiter avec des mots comme le et la",
                "source": "test-source-preprocess"
            }],
            "techniques": [{
                "name": "text_normalization",
                "parameters": {"remove_stopwords": True} # Exemple de paramètre pour _normalize_text
            }]
        }
        
        # Exécuter process_task de manière synchrone
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.adapter.process_task(task))
        
        # Vérifier que le résultat est correct
        self.assertEqual(result["status"], "completed")
        self.assertIn("outputs", result)
        outputs = result["outputs"]
        self.assertIn("normalized_text", outputs) # _format_outputs devrait créer cette clé
        self.assertEqual(len(outputs["normalized_text"]), 1)
        
        normalized_output = outputs["normalized_text"][0]
        self.assertEqual(normalized_output["extract_id"], "input-text-preprocess-1")
        # S'attendre au résultat de _normalize_text (qui supprime les stopwords simples)
        self.assertEqual(normalized_output["normalized_text"], "Ceci texte à prétraiter avec mots comme") # "le" et "la" sont supprimés
        
        # La méthode preprocess_text du mock ne sera PAS appelée. _normalize_text est appelée directement.
        self.adapter.extract_agent.preprocess_text.assert_not_called()
    
    def test_process_task_unknown_capability(self):
        """Teste la méthode process_task pour une capacité inconnue."""
        # Créer une tâche avec une capacité inconnue
        task = {
            "id": "task-4",
            "description": "Tâche inconnue",
            "required_capabilities": ["unknown_capability"], # Non utilisé directement
            "text_extracts": [{ # Fournir pour éviter l'erreur initiale
                "id": "input-unknown-1",
                "content": "Texte pour capacité inconnue",
                "source": "test-source-unknown"
            }],
            "techniques": [{
                "name": "very_unknown_technique", # Technique non supportée
                "parameters": {}
            }]
        }
        
        # Exécuter process_task de manière synchrone
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.adapter.process_task(task))
        
        # Devrait retourner "completed_with_issues" avec une issue "unsupported_technique"
        self.assertEqual(result["status"], "completed_with_issues")
        self.assertIn("issues", result)
        self.assertTrue(len(result["issues"]) > 0)
        issue = result["issues"][0]
        self.assertEqual(issue["type"], "unsupported_technique")
        self.assertIn("very_unknown_technique", issue["description"])
    
    def test_process_task_missing_parameters(self):
        """Teste la méthode process_task avec des paramètres manquants."""
        # Créer une tâche d'extraction de texte sans paramètres
        task = {
            "id": "task-5",
            "description": "Extraire le texte avec paramètres manquants pour la technique",
            "required_capabilities": ["text_extraction"], # Non utilisé directement
            "text_extracts": [], # Fournir text_extracts (peut être vide si aucune donnée à traiter)
                                 # pour éviter l'erreur initiale "Aucun extrait de texte fourni".
                                 # Si text_extracts est vide, la boucle sur les extracts ne s'exécute pas.
            "techniques": [{
                "name": "relevant_segment_extraction"
                # "parameters" est optionnel pour la technique elle-même,
                # et _process_extract prend technique_params qui sera {} par défaut.
                # Donc, cela ne devrait pas causer d'erreur de "paramètres manquants" au niveau de process_task.
            }]
        }
        
        # Exécuter process_task de manière synchrone
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.adapter.process_task(task))
        
        # Si text_extracts est vide, l'adaptateur lève une ValueError "Aucun extrait de texte fourni".
        # Le statut du résultat devrait donc être "failed".
        self.assertEqual(result["status"], "failed")
        self.assertIn("issues", result)
        self.assertTrue(len(result["issues"]) > 0)
        issue = result["issues"][0]
        self.assertEqual(issue["type"], "execution_error") # L'exception est capturée et formatée en issue
        self.assertIn("Aucun extrait de texte fourni dans la tâche.", issue["description"])
        
        # Les outputs devraient être vides ou absents dans ce cas d'échec.
        self.assertIn("outputs", result)
        # En cas d'échec avant la production de `results` (liste vide passée à _format_outputs),
        # `_format_outputs` initialisera les listes vides.
        # Si l'échec se produit dans le bloc try principal et que `format_result` n'est pas appelé avec la liste `results`
        # mais que le bloc except retourne directement un dictionnaire, alors "outputs" pourrait être {}.
        # Le bloc except dans process_task retourne "outputs": {}
        self.assertEqual(result["outputs"], {})
    
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