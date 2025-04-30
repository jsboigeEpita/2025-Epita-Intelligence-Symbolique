"""
Tests unitaires pour le module llm_service.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from core.llm_service import create_llm_service


class TestLLMService(unittest.TestCase):
    """Tests pour la fonction create_llm_service."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Sauvegarder les variables d'environnement originales
        self.original_env = os.environ.copy()
        
        # Configurer les variables d'environnement pour les tests
        os.environ["GLOBAL_LLM_SERVICE"] = "OpenAI"
        os.environ["OPENAI_API_KEY"] = "test_api_key"
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-4o-mini"

    def tearDown(self):
        """Nettoyage après chaque test."""
        # Restaurer les variables d'environnement originales
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch('core.llm_service.OpenAIChatCompletion')
    def test_create_llm_service_openai(self, mock_openai_class):
        """Teste la création d'un service LLM OpenAI."""
        # Configurer le mock
        mock_service = MagicMock(spec=OpenAIChatCompletion)
        mock_openai_class.return_value = mock_service
        
        # Appeler la fonction à tester
        service = create_llm_service()
        
        # Vérifier que le service a été créé correctement
        self.assertIsNotNone(service)
        mock_openai_class.assert_called_once_with(
            service_id="global_llm_service",
            ai_model_id="gpt-4o-mini",
            api_key="test_api_key",
            org_id=None
        )

    @patch('core.llm_service.OpenAIChatCompletion')
    def test_create_llm_service_custom_model(self, mock_openai_class):
        """Teste la création d'un service LLM avec un modèle personnalisé."""
        # Configurer les variables d'environnement
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-4"
        
        # Configurer le mock
        mock_service = MagicMock(spec=OpenAIChatCompletion)
        mock_openai_class.return_value = mock_service
        
        # Appeler la fonction à tester
        service = create_llm_service()
        
        # Vérifier que le service a été créé correctement
        self.assertIsNotNone(service)
        mock_openai_class.assert_called_once_with(
            service_id="global_llm_service",
            ai_model_id="gpt-4",
            api_key="test_api_key",
            org_id=None
        )

    @patch('core.llm_service.OpenAIChatCompletion')
    def test_create_llm_service_missing_api_key(self, mock_openai_class):
        """Teste la création d'un service LLM avec une clé API manquante."""
        # Supprimer la clé API
        del os.environ["OPENAI_API_KEY"]
        
        # Appeler la fonction à tester et vérifier qu'elle retourne None
        service = create_llm_service()
        self.assertIsNone(service)
        
        # Vérifier que le service n'a pas été créé
        mock_openai_class.assert_not_called()

    @patch('core.llm_service.OpenAIChatCompletion')
    def test_create_llm_service_exception(self, mock_openai_class):
        """Teste la création d'un service LLM avec une exception."""
        # Configurer le mock pour lever une exception
        mock_openai_class.side_effect = Exception("Test exception")
        
        # Appeler la fonction à tester et vérifier qu'elle retourne None
        service = create_llm_service()
        self.assertIsNone(service)
        
        # Vérifier que le mock a été appelé
        mock_openai_class.assert_called_once()

    @patch('core.llm_service.AzureChatCompletion')
    def test_create_llm_service_azure(self, mock_azure_class):
        """Teste la création d'un service LLM Azure."""
        # Configurer les variables d'environnement
        os.environ["OPENAI_ENDPOINT"] = "https://example.azure.com"
        
        # Configurer le mock
        mock_service = MagicMock()
        mock_azure_class.return_value = mock_service
        
        # Appeler la fonction à tester
        service = create_llm_service()
        
        # Vérifier que le service a été créé correctement
        self.assertIsNotNone(service)
        mock_azure_class.assert_called_once_with(
            service_id="global_llm_service",
            deployment_name="gpt-4o-mini",
            endpoint="https://example.azure.com",
            api_key="test_api_key"
        )


if __name__ == '__main__':
    unittest.main()