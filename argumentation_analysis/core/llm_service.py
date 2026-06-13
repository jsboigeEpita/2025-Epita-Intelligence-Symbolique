# core/llm_service.py
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    AzureChatCompletion,
)
from typing import Union, AsyncGenerator, List, Tuple
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


def resolve_chat_endpoint(default_model: str = "gpt-5-mini") -> Tuple[str, str, str]:
    """Resolve the chat endpoint honoring the OpenRouter toggle.

    Single canonical source of truth for routing raw-SDK (non-kernel) LLM
    chat calls. Mirrors the toggle embedded in :func:`create_llm_service`
    (this module) and ``orchestration.invoke_callables._get_openai_client``.
    Anti-pendule (#1019 / anti-théâtre): consults ``OPENROUTER_BASE_URL`` +
    ``OPENROUTER_API_KEY`` first and falls back to ``OPENAI_*``. Do NOT add a
    new knob — every raw-SDK caller must go through this so they no longer hit
    the official OpenAI quota (→ 429 → silent fallback) when OpenRouter is on.

    Args:
        default_model: model id used when neither ``OPENROUTER_CHAT_MODEL_ID``
            nor ``OPENAI_CHAT_MODEL_ID`` is set.

    Returns:
        ``(api_key, base_url, model_id)``. ``api_key`` is ``""`` when no key
        is configured (callers treat this as "no LLM available"). When the
        OpenRouter toggle is on, ``base_url`` is the OpenRouter endpoint and
        ``model_id`` is the provider-prefixed ``OPENROUTER_CHAT_MODEL_ID``.
    """
    openrouter_base_url = os.environ.get("OPENROUTER_BASE_URL")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_base_url and openrouter_api_key:
        api_key = openrouter_api_key
        base_url = openrouter_base_url
        model_id = os.environ.get(
            "OPENROUTER_CHAT_MODEL_ID",
            os.environ.get("OPENAI_CHAT_MODEL_ID", default_model),
        )
    else:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", default_model)
    return api_key, base_url, model_id


# La signature de la fonction est conservée pour la compatibilité, mais on utilise create_llm_service
# pour la logique principale.
def create_llm_service(
    service_id: str,
    model_id: str = None,
    service_type: str = "OpenAIChatCompletion",
    force_mock: bool = False,
    force_authentic: bool = False,
) -> Union[OpenAIChatCompletion, AzureChatCompletion, "ChatCompletionClientBase"]:
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
        # Lazy import to avoid requiring test modules in production code
        from tests.mocks.llm_service_mocks import MockChatCompletion

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
    # --- Sélection du provider : bascule OpenRouter si configurée ---
    # Si OPENROUTER_BASE_URL est défini (+ OPENROUTER_API_KEY), les appels sont
    # routés vers OpenRouter (API compatible OpenAI). Sinon, le comportement
    # OpenAI officiel reste inchangé. Toggle réversible : retirer
    # OPENROUTER_BASE_URL du .env pour revenir à OpenAI.
    openrouter_base_url = os.environ.get("OPENROUTER_BASE_URL")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    use_openrouter = bool(openrouter_base_url and openrouter_api_key)

    if use_openrouter:
        api_key = openrouter_api_key
        # OpenRouter exige des slugs préfixés par le provider (ex. "openai/gpt-5-mini")
        model_id = os.getenv("OPENROUTER_CHAT_MODEL_ID", model_id)
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
    org_id = os.environ.get("OPENAI_ORG_ID")

    if not api_key:
        raise ValueError(
            "Aucune clé API LLM définie. Définissez OPENAI_API_KEY, ou "
            "OPENROUTER_API_KEY + OPENROUTER_BASE_URL pour router via OpenRouter."
        )

    resilient_client = get_resilient_async_client()
    llm_instance = None

    try:
        if service_type == "OpenAIChatCompletion":
            provider_label = (
                "OpenRouter" if use_openrouter else "l'API OpenAI officielle"
            )
            logger.info(
                f"Configuration Service: OpenAIChatCompletion pour {provider_label}..."
            )

            client_kwargs = {"api_key": api_key, "http_client": resilient_client}
            if use_openrouter:
                client_kwargs["base_url"] = openrouter_base_url
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
