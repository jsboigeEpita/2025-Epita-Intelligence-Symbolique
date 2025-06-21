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

def create_llm_service(service_id: str = "global_llm_service", force_mock: bool = False) -> Union[OpenAIChatCompletion, AzureChatCompletion, MockChatCompletion]:
    """
    Charge la configuration depuis .env et crée une instance du service LLM.
    Supporte maintenant un mode mock pour les tests.

    Args:
        service_id (str): ID à assigner au service dans Semantic Kernel.
        force_mock (bool): Si True, force la création d'un service mocké.

    Returns:
        Instance du service LLM (réel ou mocké).
    """
    logger.critical("<<<<< create_llm_service FUNCTION CALLED >>>>>")
    logger.info(f"--- Configuration du Service LLM ({service_id}) ---")
    logger.info(f"--- Force Mock: {force_mock} ---")

    if force_mock:
        logger.warning("Création d'un service LLM mocké (MockChatCompletion).")
        return MockChatCompletion(service_id=service_id)

    project_root = Path(__file__).resolve().parent.parent.parent
    dotenv_path = project_root / '.env'
    logger.info(f"Project root determined from __file__: {project_root}")
    logger.info(f"Attempting to load .env from absolute path: {dotenv_path}")
    
    success = load_dotenv(dotenv_path=dotenv_path, override=True, verbose=True)
    logger.info(f"load_dotenv success with absolute path '{dotenv_path}': {success}")

    api_key = os.getenv("OPENAI_API_KEY")
    model_id = os.getenv("OPENAI_CHAT_MODEL_ID")
    endpoint = os.getenv("OPENAI_ENDPOINT")
    base_url = os.getenv("OPENAI_BASE_URL")
    org_id = os.getenv("OPENAI_ORG_ID")

    logger.info(f"Configuration détectée - base_url: {base_url}, endpoint: {endpoint}")
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

            logging_http_transport = LoggingHttpTransport(logger=logger)
            custom_httpx_client = httpx.AsyncClient(transport=logging_http_transport)
            
            client_kwargs = {"api_key": api_key, "http_client": custom_httpx_client}
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

# Classe pour le transport HTTP personnalisé avec logging
class LoggingHttpTransport(httpx.AsyncBaseTransport):
    def __init__(self, logger: logging.Logger, wrapped_transport: httpx.AsyncBaseTransport = None):
        self.logger = logger
        # Si aucun transport n'est fourni, utiliser un transport HTTP standard
        self._wrapped_transport = wrapped_transport if wrapped_transport else httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.logger.info(f"--- RAW HTTP REQUEST (LLM Service) ---")
        self.logger.info(f"  Method: {request.method}")
        self.logger.info(f"  URL: {request.url}")
        # Log des headers (attention aux informations sensibles comme les clés API si elles sont dans les headers)
        # self.logger.info(f"  Headers: {request.headers}")
        if request.content:
            try:
                # Tenter de décoder et logger le contenu si c'est du JSON
                content_bytes = await request.aread() # Lire le contenu asynchrone du corps
                request.stream._buffer = [content_bytes] # Remettre le contenu dans le buffer pour la requête réelle
                
                json_content = json.loads(content_bytes.decode('utf-8'))
                pretty_json_content = json.dumps(json_content, indent=2, ensure_ascii=False)
                self.logger.info(f"  Body (JSON):\n{pretty_json_content}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Si ce n'est pas du JSON ou si l'encodage échoue, logger en brut (tronqué)
                # Il faut être prudent avec le logging du contenu brut, surtout pour les grosses requêtes
                # content_preview = content_bytes[:500].decode('utf-8', errors='replace') + ('...' if len(content_bytes) > 500 else '')
                # self.logger.info(f"  Body (Raw Preview): {content_preview}")
                self.logger.info(f"  Body: (Contenu binaire ou non-JSON, taille: {len(content_bytes)} bytes)")
            except Exception as e_req:
                 self.logger.error(f"  Erreur lors du logging du corps de la requête: {e_req}")
        else:
            self.logger.info("  Body: (Vide)")
        self.logger.info(f"--- END RAW HTTP REQUEST (LLM Service) ---")

        response = await self._wrapped_transport.handle_async_request(request)

        self.logger.info(f"--- RAW HTTP RESPONSE (LLM Service) ---")
        self.logger.info(f"  Status Code: {response.status_code}")
        # self.logger.info(f"  Headers: {response.headers}")
        
        # Lire le contenu de la réponse pour le logging
        # IMPORTANT: lire le contenu ici le consomme. Il faut le remettre dans le stream
        # pour que Semantic Kernel puisse le lire ensuite.
        response_content_bytes = await response.aread()
        response.stream._buffer = [response_content_bytes] # Remettre le contenu dans le buffer

        try:
            json_response_content = json.loads(response_content_bytes.decode('utf-8'))
            pretty_json_response_content = json.dumps(json_response_content, indent=2, ensure_ascii=False)
            self.logger.info(f"  Body (JSON):\n{pretty_json_response_content}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            # response_content_preview = response_content_bytes[:1500].decode('utf-8', errors='replace') + ('...' if len(response_content_bytes) > 1500 else '')
            # self.logger.info(f"  Body (Raw Preview): {response_content_preview}")
            self.logger.info(f"  Body: (Contenu binaire ou non-JSON, taille: {len(response_content_bytes)} bytes)")
        except Exception as e_resp:
            self.logger.error(f"  Erreur lors du logging du corps de la réponse: {e_resp}")
        self.logger.info(f"--- END RAW HTTP RESPONSE (LLM Service) ---")
        
        return response

    async def aclose(self) -> None:
        await self._wrapped_transport.aclose()

# Optionnel : Log de chargement
module_logger = logging.getLogger(__name__)
module_logger.debug("Module core.llm_service chargé.")
