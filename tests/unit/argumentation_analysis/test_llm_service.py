
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
import pytest
import asyncio
import logging
from unittest.mock import MagicMock, patch

import os
import semantic_kernel as sk
from pathlib import Path
from semantic_kernel.functions import KernelArguments
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from argumentation_analysis.core.llm_service import create_llm_service
from openai import AsyncOpenAI, AuthenticationError


class TestLLMService:
    """Tests pour la fonction create_llm_service avec de vrais appels API."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Initialisation et nettoyage pour chaque test."""
        self.original_env = os.environ.copy()
        from dotenv import load_dotenv
        dotenv_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'
        load_dotenv(dotenv_path=dotenv_path, override=True)
        
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-4o-mini")

        yield  # C'est ici que le test s'exécute

        os.environ.clear()
        os.environ.update(self.original_env)

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY non disponible")
    def test_create_llm_service_openai_authentic(self):
        """Teste la création d'un vrai service LLM OpenAI."""
        if not self.api_key:
            pytest.skip("La variable d'environnement OPENAI_API_KEY est requise pour ce test.")

        service = create_llm_service(service_id="test_service", model_id=self.model_id, force_authentic=True)
        
        assert service is not None, "Le service LLM ne devrait pas être None."
        assert isinstance(service, OpenAIChatCompletion), "Le service devrait être une instance de OpenAIChatCompletion."
        assert service.ai_model_id == self.model_id, f"L'ID du modèle du service ({service.ai_model_id}) ne correspond pas à celui de l'environnement ({self.model_id})."

    def test_create_llm_service_missing_api_key(self):
        """Teste que la création du service échoue sans clé API."""
        # Supprimer temporairement la clé API de l'environnement
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        with pytest.raises(ValueError) as excinfo:
            create_llm_service(service_id="test_service", model_id=self.model_id, force_authentic=True)
        
        assert "Configuration OpenAI standard incomplète" in str(excinfo.value)

        assert "OPENAI_API_KEY" in str(excinfo.value)

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY non disponible")
    def test_authentic_llm_call(self):
        """Teste un appel authentique à gpt-4o-mini pour valider la connectivité."""
        async def _run_async_test():
            try:
                kernel = sk.Kernel()
                llm_service = create_llm_service(service_id="test_service", model_id=self.model_id)
                kernel.add_service(llm_service)
                
                # Création d'une fonction de prompt simple
                prompt_template = "{{$input}}"
                prompt_function = kernel.add_function(
                    function_name="echo",
                    plugin_name="test",
                    prompt=prompt_template
                )

                prompt = "Bonjour, es-tu là ?"
                result = await kernel.invoke(prompt_function, KernelArguments(input=prompt))
                
                response_str = str(result).strip()
                assert isinstance(response_str, str)
                assert len(response_str) > 0, "La réponse du LLM ne devrait pas être vide."
                logging.info(f"Réponse authentique du LLM reçue : '{response_str[:50]}...'")

            except Exception as e:
                pytest.fail(f"L'appel LLM authentique a échoué avec l'exception: {e}")
        
        asyncio.run(_run_async_test())

# Le bloc if __name__ == '__main__': est retiré car pytest et pytest-asyncio
# gèrent l'exécution des tests, y compris les tests asynchrones.