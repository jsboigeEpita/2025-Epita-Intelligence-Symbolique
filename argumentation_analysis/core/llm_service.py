# core/llm_service.py
import logging
import os
from pathlib import Path
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion
from typing import Union # Pour type hint
import httpx # Ajout pour le client HTTP personnalisé
from openai import AsyncOpenAI  # Ajout pour instancier le client OpenAI
import json  # Ajout de l'import manquant
import asyncio
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from argumentation_analysis.core.utils.network_utils import get_resilient_async_client
from argumentation_analysis.config.settings import settings

# Logger pour ce module
logger = logging.getLogger("Orchestration.LLM")
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
logger.info("<<<<< MODULE llm_service.py LOADED >>>>>")

class MockChatCompletion(ChatCompletionClientBase):
    """
    Service de complétion de chat mocké qui retourne des réponses prédéfinies.
    Simule le comportement de OpenAIChatCompletion pour les tests E2E.
    """
    async def get_chat_message_contents(
        self,
        chat_history: ChatHistory,
        **kwargs,
    ) -> list[ChatMessageContent]:
        """Retourne une réponse mockée basée sur le contenu de l'historique."""
        logger.warning(f"--- MOCK LLM SERVICE USED (service_id: {self.service_id}) ---")
        
        # Simuler une réponse JSON valide pour une analyse d'argument
        mock_response_content = {
            "analysis_id": "mock-12345",
            "argument_summary": {
                "main_conclusion": "Socrate est mortel.",
                "premises": ["Tous les hommes sont mortels.", "Socrate est un homme."],
                "structure": "Deductif"
            },
            "quality_assessment": {
                "clarity": 85,
                "relevance": 95,
                "coherence": 90,
                "overall_score": 91
            },
            "fallacies": [],
            "suggestions": "Aucune suggestion, l'argument est valide."
        }
        
        # Créer un ChatMessageContent avec la réponse mockée
        response_message = ChatMessageContent(
            role="assistant",
            content=json.dumps(mock_response_content, indent=2, ensure_ascii=False)
        )
        
        # Simuler une latence réseau
        await asyncio.sleep(0.1)
        
        return [response_message]

    async def complete_chat(self, *args, **kwargs):
        """Dummy implementation for backward compatibility."""
        return await self.get_chat_message_contents(*args, **kwargs)

    async def complete_chat_stream(self, *args, **kwargs):
        """Dummy implementation for backward compatibility."""
        # This is a simplified stream simulation.
        # A real implementation would yield content chunks.
        results = await self.get_chat_message_contents(*args, **kwargs)
        for result in results:
            yield [result]

def create_llm_service(service_id: str = "global_llm_service", force_mock: bool = False, force_authentic: bool = False) -> Union[OpenAIChatCompletion, AzureChatCompletion, MockChatCompletion]:
    """
    Factory pour créer et configurer une instance de service de complétion de chat.

    Cette fonction lit la configuration à partir d'un fichier .env pour déterminer
    quel service instancier (OpenAI standard ou Azure OpenAI). Elle peut également
    forcer la création d'un service mocké pour les tests.

    Args:
        service_id (str): L'ID de service à utiliser pour l'instance dans
                          le kernel Semantic Kernel.
        force_mock (bool): Si True, retourne une instance de `MockChatCompletion`
                           ignorant la configuration du .env.
        force_authentic (bool): Si True, force la création d'un service authentique
                                même dans un environnement de test.

    Returns:
        Union[OpenAIChatCompletion, AzureChatCompletion, MockChatCompletion]:
            Une instance configurée du service de chat.

    Raises:
        ValueError: Si la configuration requise pour le service choisi (OpenAI ou Azure)
                    est manquante dans le fichier .env.
        RuntimeError: Si la création du service échoue pour une raison inattendue.
    """
    logger.critical("<<<<< create_llm_service FUNCTION CALLED >>>>>")
    logger.info(f"--- Configuration du Service LLM ({service_id}) ---")

    # Mocking automatique en environnement de test (détecté via variable pytest)
    is_test_environment = 'PYTEST_CURRENT_TEST' in os.environ
    if is_test_environment and not force_authentic:
        logger.warning("Environnement de test détecté et `force_authentic` est False. Forçage du service LLM mocké.")
        force_mock = True

    logger.info(f"--- Force Mock: {force_mock} ---")

    if force_mock:
        logger.warning("Création d'un service LLM mocké (MockChatCompletion).")
        return MockChatCompletion(service_id=service_id, ai_model_id="mock_model")

    api_key = settings.openai.api_key.get_secret_value() if settings.openai.api_key else None
    model_id = settings.openai.chat_model_id
    # Pour la compatibilité avec Azure, on vérifie si base_url est une instance Azure
    # Pydantic HttpUrl ne peut pas être None, on vérifie la valeur de l'url
    base_url_str = str(settings.openai.base_url) if settings.openai.base_url else None
    endpoint = None
    base_url = None
    org_id = None # org_id n'est pas dans notre modèle de settings pour l'instant

    if base_url_str and "azure" in base_url_str:
        endpoint = base_url_str
    elif base_url_str:
        # On ne passe la base_url que si elle est explicitement définie et n'est pas une URL Azure
        base_url = base_url_str
        if "localhost" in base_url or "127.0.0.1" in base_url:
             logger.warning(f"Une base_url locale ('{base_url}') est utilisée pour le client OpenAI. Assurez-vous qu'un proxy compatible OpenAI est en cours d'exécution.")

    logger.info(f"Configuration LLM finale - base_url: {base_url}, endpoint Azure: {endpoint}")
    use_azure_openai = bool(endpoint)

    llm_instance = None
    try:
        if use_azure_openai:
            logger.info("Configuration Service: AzureChatCompletion...")
            if not all([api_key, model_id, endpoint]):
                raise ValueError("Configuration Azure OpenAI incomplète (.env).")
            
            llm_instance = AzureChatCompletion(
                service_id=service_id,
                deployment_name=model_id,
                endpoint=endpoint,
                api_key=api_key
            )
            logger.info(f"Service LLM Azure ({model_id}) créé.")
        else:
            logger.info("Configuration Service: OpenAIChatCompletion...")
            if not all([api_key, model_id]):
                raise ValueError("Configuration OpenAI standard incomplète (.env).")

            resilient_client = get_resilient_async_client()
            
            # --- AJOUT DE LOG POUR DEBUG ---
            logger.critical(f"DEBUG: Valeur de settings.openai.base_url au moment de l'utilisation: {settings.openai.base_url}")
            logger.critical(f"DEBUG: Valeur de la variable 'base_url' dérivée: {base_url}")
            # --- FIN DE L'AJOUT DE LOG ---

            client_kwargs = {"api_key": api_key, "http_client": resilient_client}
            if base_url:
                client_kwargs["base_url"] = base_url
            if org_id and "your_openai_org_id_here" not in org_id:
                client_kwargs["organization"] = org_id
                
            openai_custom_async_client = AsyncOpenAI(**client_kwargs)
            
            llm_instance = OpenAIChatCompletion(
                service_id=service_id,
                ai_model_id=model_id,
                async_client=openai_custom_async_client
            )
            logger.info(f"Service LLM OpenAI ({model_id}) créé avec HTTP client personnalisé.")

    except ValueError as ve:
        logger.critical(f"Erreur de configuration LLM: {ve}")
        raise
    except Exception as e:
        logger.critical(f"Erreur critique lors de la création du service LLM: {e}", exc_info=True)
        raise RuntimeError(f"Impossible de configurer le service LLM: {e}")

    if not llm_instance:
        raise RuntimeError("Configuration du service LLM a échoué silencieusement.")

    return llm_instance

# La classe LoggingHttpTransport a été déplacée dans core/utils/network_utils.py

# Optionnel : Log de chargement
module_logger = logging.getLogger(__name__)
module_logger.debug("Module core.llm_service chargé.")
