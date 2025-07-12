# core/llm_service.py
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
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

# Charger les variables d'environnement depuis le fichier .env
load_dotenv(override=True)

# Logger pour ce module
logger = logging.getLogger("Orchestration.LLM")
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
logger.info("<<<<< MODULE llm_service.py LOADED >>>>>")

# Petit classes pour simuler la structure de la réponse de SK
class MockFunctionCall:
    def __init__(self, name: str, arguments: dict):
        self.name = name
        self._arguments = arguments

    def parse_arguments(self) -> dict:
        return self._arguments

class MockToolCall:
    def __init__(self, function_name: str, arguments: dict):
        self.function = MockFunctionCall(name=function_name, arguments=arguments)

class MockChatCompletion(ChatCompletionClientBase):
    """
    Service de complétion de chat mocké qui retourne des réponses prédéfinies
    et simule une réponse de type 'tool_call' attendue par l'agent.
    """
    async def get_chat_message_contents(
        self,
        chat_history: ChatHistory,
        **kwargs,
    ) -> list[ChatMessageContent]:
        """
        Retourne une réponse mockée simulant un appel d'outil (tool_call)
        avec une analyse de sophisme valide et sans sophisme.
        """
        logger.warning(f"--- ADVANCED MOCK LLM SERVICE USED (service_id: {self.service_id}, simulating tool_call) ---")
        
        # 1. Définir le payload de la réponse que l'outil est censé retourner
        #    Ceci correspond à la structure du modèle Pydantic `FallacyAnalysisResult`
        mock_tool_arguments = {
            "analysis_id": "mock-analysis-123",
            "fallacies": [],  # La clé du succès du test !
            "is_argument_valid": True,
            "overall_assessment": "L'argument est valide, clair et bien structuré.",
            "confidence_score": 0.99
        }

        # 2. Simuler la structure de 'tool_call' que le LLM renverrait
        #    On utilise nos classes de simulation pour imiter la structure de Semantic Kernel
        mock_tool_call = MockToolCall(
            function_name="submit_fallacy_analysis",
            arguments=mock_tool_arguments
        )

        # 3. Créer le message de contenu de chat qui encapsule le 'tool_call'
        #    Le `content` peut être vide, car l'agent va chercher `tool_calls`
        response_message = ChatMessageContent(
            role="assistant",
            content=None,  # Le contenu textuel n'est pas nécessaire quand il y a un tool_call
            tool_calls=[mock_tool_call]
        )
        
        # Simuler une latence réseau
        await asyncio.sleep(0.05)
        
        return [response_message]

# La signature de la fonction est conservée pour la compatibilité, mais on utilise create_llm_service
# pour la logique principale.
@staticmethod
def create_llm_service(
    service_id: str,
    model_id: str,
    service_type: str = "OpenAIChatCompletion",
    **kwargs,
) -> "LLMService":
    """
    Factory pour créer et configurer une instance de service de complétion de chat.

    Cette fonction lit la configuration à partir des variables d'environnement
    pour déterminer quel service instancier (OpenAI standard ou Azure OpenAI).
    Elle peut également forcer la création d'un service mocké pour les tests.

    Args:
        service_id (str): L'ID de service à utiliser pour l'instance dans
                          le kernel Semantic Kernel.
        model_id (str): L'ID du modèle à utiliser (ex: "gpt-4-turbo").
        service_type (str): Le type de service à créer. Actuellement, seul
                            "OpenAIChatCompletion" est entièrement géré
                            pour la connexion à l'API OpenAI officielle.
        force_mock (bool): Si True, retourne une instance de `MockChatCompletion`
                           ignorant la configuration.
        force_authentic (bool): Si True, force la création d'un service authentique
                                même dans un environnement de test.

    Returns:
        Union[OpenAIChatCompletion, AzureChatCompletion, MockChatCompletion]:
            Une instance configurée du service de chat.

    Raises:
        ValueError: Si la configuration requise (ex: OPENAI_API_KEY) est manquante.
        RuntimeError: Si la création du service échoue.
    """
    logger.critical("<<<<< create_llm_service FUNCTION CALLED >>>>>")
    logger.info(f"--- Configuration du Service LLM ({service_id}) ---")

    # Logique de mock pour les tests
    is_test_environment = 'PYTEST_CURRENT_TEST' in os.environ
    force_real_llm_in_test = os.environ.get("FORCE_REAL_LLM_IN_TEST", "false").lower() == "true"
    
    if is_test_environment and not force_real_llm_in_test and kwargs.get('force_mock', False):
        logger.warning("Environnement de test détecté. Création d'un service LLM mocké.")
        return MockChatCompletion(service_id=service_id, ai_model_id="mock_model")

    # Récupération directe depuis l'environnement
    api_key = os.environ.get("OPENAI_API_KEY")
    org_id = os.environ.get("OPENAI_ORG_ID")

    if not api_key:
        raise ValueError("La variable d'environnement OPENAI_API_KEY n'est pas définie.")

    resilient_client = get_resilient_async_client()
    llm_instance = None

    try:
        if service_type == "OpenAIChatCompletion":
            logger.info("Configuration Service: OpenAIChatCompletion pour l'API OpenAI officielle...")
            
            client_kwargs = {
                "api_key": api_key,
                "http_client": resilient_client
            }
            if org_id:
                client_kwargs["organization"] = org_id
            
            async_client = AsyncOpenAI(**client_kwargs)
            
            llm_instance = OpenAIChatCompletion(
                service_id=service_id,
                ai_model_id=model_id,
                async_client=async_client
            )
            logger.info(f"Service LLM OpenAI ({model_id}) créé avec succès.")
        
        # NOTE: La logique pour Azure est conservée mais non utilisée si service_type est OpenAIChatCompletion
        elif service_type == "AzureChatCompletion":
            endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
            if not endpoint:
                raise ValueError("La variable d'environnement AZURE_OPENAI_ENDPOINT est requise pour Azure.")
            
            logger.info("Configuration Service: AzureChatCompletion...")
            llm_instance = AzureChatCompletion(
                service_id=service_id,
                deployment_name=model_id,
                endpoint=endpoint,
                api_key=api_key
            )
            logger.info(f"Service LLM Azure ({model_id}) créé.")
        else:
            raise ValueError(f"Type de service LLM non supporté: {service_type}")

    except ValueError as ve:
        logger.critical(f"Erreur de configuration LLM: {ve}")
        raise
    except Exception as e:
        logger.critical(f"Erreur critique lors de la création du service LLM: {e}", exc_info=True)
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
