
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module llm_service.
"""

import unittest
from unittest.mock import MagicMock, patch

import os
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion
from argumentation_analysis.core.llm_service import create_llm_service
from openai import AsyncOpenAI


class TestLLMService(unittest.TestCase):
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

    """Tests pour la fonction create_llm_service."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Sauvegarder les variables d'environnement originales
        self.original_env = os.environ.copy()
        
        # Configurer les variables d'environnement pour les tests
        # Charger les variables d'environnement depuis le fichier .env
        from dotenv import load_dotenv
        load_dotenv(dotenv_path="../.env", override=True)
        
        # Stocker la clé API pour les assertions
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-4o-mini")

    def tearDown(self):
        """Nettoyage après chaque test."""
        # Restaurer les variables d'environnement originales
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch('argumentation_analysis.core.llm_service.OpenAIChatCompletion')
    def test_create_llm_service_openai(self, mock_openai_class):
        """Teste la création d'un service LLM OpenAI."""
        # Configurer le mock
        mock_service = MagicMock(spec=OpenAIChatCompletion)
        mock_openai_class.return_value = mock_service
        
        # Appeler la fonction à tester
        service = create_llm_service()
        
        # Vérifier que le service a été créé correctement
        self.assertIsNotNone(service)
        
        # Vérifier que le mock a été appelé une fois
        mock_openai_class.assert_called_once()
        
        # Vérifier que les arguments essentiels sont présents
        args, kwargs = mock_openai_class.call_args
        self.assertEqual(kwargs["service_id"], "global_llm_service")
        self.assertEqual(kwargs["ai_model_id"], "gpt-4o-mini")
        
        # Vérifier que async_client est fourni (nouvelle interface)
        self.assertIn("async_client", kwargs)
        self.assertIsNotNone(kwargs["async_client"])
        
        # Vérifier que api_key et org_id ne sont PAS fournis (ils sont dans async_client)
        self.assertNotIn("api_key", kwargs)
        self.assertNotIn("org_id", kwargs)

    @patch('argumentation_analysis.core.llm_service.OpenAIChatCompletion')
    def test_create_llm_service_custom_model(self, mock_openai_class):
        """Teste la création d'un service LLM avec un modèle personnalisé."""
        # Configurer le mock
        mock_service = MagicMock(spec=OpenAIChatCompletion)
        mock_openai_class.return_value = mock_service
        
        # Appeler la fonction à tester
        service = create_llm_service()
        
        # Vérifier que le service a été créé correctement
        self.assertIsNotNone(service)
        
        # Vérifier que le mock a été appelé une fois
        mock_openai_class.assert_called_once()
        
        # Vérifier que les arguments essentiels sont présents
        args, kwargs = mock_openai_class.call_args
        self.assertEqual(kwargs["service_id"], "global_llm_service")
        self.assertIsNotNone(kwargs["ai_model_id"])
        
        # Vérifier que async_client est fourni (nouvelle interface)
        self.assertIn("async_client", kwargs)
        self.assertIsNotNone(kwargs["async_client"])
        
        # Vérifier que api_key et org_id ne sont PAS fournis (ils sont dans async_client)
        self.assertNotIn("api_key", kwargs)
        self.assertNotIn("org_id", kwargs)

    @patch('argumentation_analysis.core.llm_service.OpenAIChatCompletion')
    def test_create_llm_service_missing_api_key(self, mock_openai_class):
        """Teste la création d'un service LLM avec une clé API manquante."""
        # Sauvegarder la clé API
        saved_api_key = os.environ.get("OPENAI_API_KEY", "")
        
        try:
            # Supprimer la clé API
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
            
            # Configurer le mock pour lever une exception ValueError
            mock_openai_class.side_effect = ValueError("Configuration OpenAI standard incomplète")
            
            # Appeler la fonction à tester et vérifier qu'elle lève une exception
            with self.assertRaises(ValueError):
                service = create_llm_service()
        finally:
            # Restaurer la clé API
            if saved_api_key:
                os.environ["OPENAI_API_KEY"] = saved_api_key

    @patch('argumentation_analysis.core.llm_service.OpenAIChatCompletion')
    def test_create_llm_service_exception(self, mock_openai_class):
        """Teste la création d'un service LLM avec une exception."""
        # Configurer le mock pour lever une exception
        mock_openai_class.side_effect = Exception("Test exception")
        
        # Appeler la fonction à tester et vérifier qu'elle lève une RuntimeError
        with self.assertRaises(RuntimeError):
            service = create_llm_service()
        
        # Vérifier que le mock a été appelé
        mock_openai_class.assert_called_once()

    @patch('argumentation_analysis.core.llm_service.AzureChatCompletion')
    def test_create_llm_service_azure(self, mock_azure_class):
        """Teste la création d'un service LLM Azure."""
        # Configurer les variables d'environnement
        os.environ["OPENAI_ENDPOINT"] = "https://example.azure.com"
        
        # Configurer le mock
        mock_service = MagicMock(spec=AzureChatCompletion)
        mock_azure_class.return_value = mock_service
        
        # Appeler la fonction à tester
        service = create_llm_service()
        
        # Vérifier que le service a été créé correctement
        self.assertIsNotNone(service)
        mock_azure_class.assert_called_once_with(
            service_id="global_llm_service",
            deployment_name="gpt-4o-mini",
            endpoint="https://example.azure.com",
            api_key=self.api_key
        )


if __name__ == '__main__':
    unittest.main()