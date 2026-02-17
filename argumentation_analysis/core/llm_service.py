# core/llm_service.py
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    AzureChatCompletion,
)
from typing import Union, AsyncGenerator, List
import httpx
from openai import AsyncOpenAI
import json
import asyncio
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

# Tentative de correction en supprimant l'import qui échoue
# from semantic_kernel.contents.tool_call_content import ToolCallContent
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from argumentation_analysis.core.utils.network_utils import get_resilient_async_client
from argumentation_analysis.config.settings import settings
from tests.mocks.llm_service_mocks import MockChatCompletion

# Logger pour ce module
logger = logging.getLogger("Orchestration.LLM")
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
logger.info("<<<<< MODULE llm_service.py LOADED >>>>>")


# La signature de la fonction est conservée pour la compatibilité, mais on utilise create_llm_service
# pour la logique principale.
def create_llm_service(
    service_id: str,
    model_id: str = None,
    service_type: str = "OpenAIChatCompletion",
    force_mock: bool = False,
    force_authentic: bool = False,
) -> Union[OpenAIChatCompletion, AzureChatCompletion, MockChatCompletion]:
    """
    Factory pour créer et configurer une instance de service de complétion de chat.

    Cette fonction lit la configuration à partir des variables d'environnement
    pour déterminer quel service instancier (OpenAI standard ou Azure OpenAI).
    Elle peut également forcer la création d'un service mocké ou authentique
    pour les tests.

    Args:
        service_id (str): L'ID de service à utiliser pour l'instance dans
                          le kernel Semantic Kernel.
        model_id (str, optionnel): L'ID du modèle. Si non fourni, il est lu
                                 depuis la variable d'environnement OPENAI_CHAT_MODEL_ID.
        service_type (str): Le type de service à créer (par ex., "OpenAIChatCompletion").
        force_mock (bool): Si True, retourne une instance de MockChatCompletion.
        force_authentic (bool): Si True, force la création d'un service authentique
                                même dans un environnement de test.

    Returns:
        Instance configurée du service de chat.

    Raises:
        ValueError: Si la configuration requise est manquante.
        RuntimeError: Si la création du service échoue.
    """
    logger.critical("<<<<< create_llm_service FUNCTION CALLED >>>>>")
    logger.info(f"--- Configuration du Service LLM ({service_id}) ---")

    # Gestion des mocks pour les tests
    # force_authentic overrides force_mock and test environment detection
    is_test_environment = "PYTEST_CURRENT_TEST" in os.environ
    if not force_authentic and (force_mock or is_test_environment):
        if force_mock:
            logger.warning(
                f"Création forcée d'un service LLM MOCKÉ pour '{service_id}'."
            )
        else:
            logger.warning(
                f"Environnement de test détecté. Création d'un service LLM MOCKÉ pour '{service_id}'."
            )
        return MockChatCompletion(service_id=service_id, ai_model_id="mock_model")

    logger.info("Tentative de création d'un service LLM AUTHENTIQUE...")

    # Si on n'est pas en mode mock, on cherche le model_id s'il n'est pas fourni
    if not model_id:
        model_id = os.getenv("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
        logger.info(
            f"model_id non fourni, utilisation de la valeur de .env: {model_id}"
        )

    # Correction automatique pour les modèles obsolètes
    if model_id == "gpt-4-32k":
        new_model_id = "gpt-5-mini"
        logger.warning(
            f"Le modèle '{model_id}' est obsolète ou inaccessible. "
            f"Substitution automatique par '{new_model_id}'. "
            f"Veuillez mettre à jour votre fichier .env avec OPENAI_CHAT_MODEL_ID={new_model_id}"
        )
        model_id = new_model_id
    # Récupération directe depuis l'environnement
    api_key = os.environ.get("OPENAI_API_KEY")
    org_id = os.environ.get("OPENAI_ORG_ID")

    if not api_key:
        raise ValueError(
            "La variable d'environnement OPENAI_API_KEY n'est pas définie."
        )

    resilient_client = get_resilient_async_client()
    llm_instance = None

    try:
        if service_type == "OpenAIChatCompletion":
            logger.info(
                "Configuration Service: OpenAIChatCompletion pour l'API OpenAI officielle..."
            )

            client_kwargs = {"api_key": api_key, "http_client": resilient_client}
            if org_id:
                client_kwargs["organization"] = org_id

            async_client = AsyncOpenAI(**client_kwargs)

            llm_instance = OpenAIChatCompletion(
                service_id=service_id, ai_model_id=model_id, async_client=async_client
            )
            logger.info(f"Service LLM OpenAI ({model_id}) créé avec succès.")

        # NOTE: La logique pour Azure est conservée mais non utilisée si service_type est OpenAIChatCompletion
        elif service_type == "AzureChatCompletion":
            endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
            if not endpoint:
                raise ValueError(
                    "La variable d'environnement AZURE_OPENAI_ENDPOINT est requise pour Azure."
                )

            logger.info("Configuration Service: AzureChatCompletion...")
            llm_instance = AzureChatCompletion(
                service_id=service_id,
                deployment_name=model_id,
                endpoint=endpoint,
                api_key=api_key,
            )
            logger.info(f"Service LLM Azure ({model_id}) créé.")
        else:
            raise ValueError(f"Type de service LLM non supporté: {service_type}")

    except ValueError as ve:
        logger.critical(f"Erreur de configuration LLM: {ve}")
        raise
    except Exception as e:
        logger.critical(
            f"Erreur critique lors de la création du service LLM: {e}", exc_info=True
        )
        raise RuntimeError(f"Impossible de configurer le service LLM: {e}")

    if not llm_instance:
        raise RuntimeError("La configuration du service LLM a échoué silencieusement.")

    return llm_instance


# Conserver la classe LLMService pour la compatibilité, bien que la logique principale
# soit maintenant dans la factory `create_llm_service`.
class LLMService:
    def __init__(self, llm_instance: ChatCompletionClientBase):
        self._llm_instance = llm_instance

    @property
    def llm(self) -> ChatCompletionClientBase:
        return self._llm_instance

    # La méthode `create_llm_service` est maintenant statique et à l'extérieur
    # pour une meilleure séparation des préoccupations.


# Optionnel : Log de chargement
module_logger = logging.getLogger(__name__)
module_logger.debug("Module core.llm_service chargé.")
