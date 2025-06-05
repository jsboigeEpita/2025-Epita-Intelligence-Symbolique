# core/llm_service.py
import logging
import os
from dotenv import load_dotenv
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion
from typing import Union # Pour type hint
import httpx # Ajout pour le client HTTP personnalisé
from openai import AsyncOpenAI # Ajout pour instancier le client OpenAI
import json # Ajout de l'import manquant

# Logger pour ce module
logger = logging.getLogger("Orchestration.LLM")
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); logger.addHandler(handler); logger.setLevel(logging.INFO)
logger.info("<<<<< MODULE llm_service.py LOADED >>>>>")


def create_llm_service(service_id: str = "global_llm_service", force_mock: bool = False) -> Union[OpenAIChatCompletion, AzureChatCompletion]:
    """
    Charge la configuration depuis .env et crée une instance du service LLM
    (OpenAI ou Azure OpenAI).

    Args:
        service_id (str): ID à assigner au service dans Semantic Kernel.

    Returns:
        Union[OpenAIChatCompletion, AzureChatCompletion]: L'instance du service LLM configurée.

    Raises:
        ValueError: Si la configuration .env est incomplète ou invalide.
        RuntimeError: Si la création de l'instance échoue pour une autre raison.
    """
    logger.critical("<<<<< get_llm_service FUNCTION CALLED >>>>>")
    logger.info(f"--- Configuration du Service LLM ({service_id}) ---")
    cwd = os.getcwd()
    logger.info(f"Current working directory for dotenv: {cwd}")
    dotenv_path = os.path.join(cwd, '.env')
    logger.info(f"Attempting to load .env from explicit path: {dotenv_path}")
    success = load_dotenv(dotenv_path=dotenv_path, override=True, verbose=True) # Ajout de verbose=True
    logger.info(f"load_dotenv success with explicit path '{dotenv_path}': {success}")

    api_key = os.getenv("OPENAI_API_KEY")
    logger.info(f"Value of api_key directly from os.getenv: '{api_key}'")
    # AJOUT POUR DEBUGGING
    if api_key and len(api_key) > 10: # Vérifier que la clé existe et est assez longue
        logger.info(f"OpenAI API Key (first 5, last 5): {api_key[:5]}...{api_key[-5:]}")
    elif api_key:
        logger.info(f"OpenAI API Key loaded (short key): {api_key}")
    else:
        logger.warning("OpenAI API Key is None or empty after os.getenv.")
    # FIN AJOUT
    model_id = os.getenv("OPENAI_CHAT_MODEL_ID")
    endpoint = os.getenv("OPENAI_ENDPOINT")
    org_id = os.getenv("OPENAI_ORG_ID")
    use_azure_openai = bool(endpoint)

    llm_instance = None
    try:
        if force_mock:
            logger.info("Forçage de l'utilisation du service LLM factice (Mock).")
            # Vous devez avoir une classe MockLLMService définie quelque part
            # Pour l'exemple, je vais la définir ici, mais elle devrait être dans un module de mocks.
            class MockLLMService(OpenAIChatCompletion):
                def __init__(self, service_id: str):
                    # Initialisation minimale pour satisfaire les besoins de base
                    super().__init__(ai_model_id="mock_model", service_id=service_id, api_key="mock_key")
                
                async def _inner_get_chat_message_contents(self, *args, **kwargs):
                    # Simuler une réponse simple
                    from semantic_kernel.contents.chat_message_content import ChatMessageContent
                    from openai.types.chat import ChatCompletion, ChatCompletionMessage
                    from openai.types.chat.chat_completion import Choice
                    from semantic_kernel.contents.utils.author_role import AuthorRole
                    
                    mock_choice = Choice(
                        finish_reason='stop',
                        index=0,
                        message=ChatCompletionMessage(role='assistant', content='{"sophismes": []}')
                    )
                    
                    mock_completion = ChatCompletion(
                        id='chatcmpl-mock',
                        choices=[mock_choice],
                        created=1677652288,
                        model=self.ai_model_id,
                        object='chat.completion',
                    )
                    
                    return [ChatMessageContent(
                        inner_content=mock_completion,
                        ai_model_id=self.ai_model_id,
                        role=AuthorRole.ASSISTANT,
                        content=mock_choice.message.content
                    )]

            return MockLLMService(service_id=service_id)

        if use_azure_openai:
            logger.info("Configuration Service: AzureChatCompletion...")
            if not all([api_key, model_id, endpoint]):
                raise ValueError("Configuration Azure OpenAI incomplète dans .env (OPENAI_API_KEY, OPENAI_CHAT_MODEL_ID, OPENAI_ENDPOINT requis).")
            
            # Pour Azure, nous pourrions aussi vouloir injecter un client httpx personnalisé si nécessaire,
            # mais la complexité est plus grande à cause de la gestion des credentials Azure.
            # Pour l'instant, on se concentre sur OpenAI standard.
            azure_async_client = httpx.AsyncClient() # Client standard pour l'instant
            # TODO: Rechercher comment injecter un transport personnalisé pour AzureOpenAI si besoin de logs bruts.
            # Pour l'instant, on utilise le client par défaut pour Azure.
            # Si on voulait un client personnalisé pour Azure, il faudrait probablement passer un `AzureOpenAI` client
            # à `AzureChatCompletion` de la même manière qu'on passe `AsyncOpenAI` à `OpenAIChatCompletion`.

            llm_instance = AzureChatCompletion(
                service_id=service_id,
                deployment_name=model_id,
                endpoint=endpoint,
                api_key=api_key
                # azure_ad_token_provider=... , # si auth Azure AD
                # http_client=azure_async_client # Exemple si supporté
            )
            logger.info(f"Service LLM Azure ({model_id}) créé avec ID '{service_id}'.")
        else:
            logger.info("Configuration Service: OpenAIChatCompletion...")
            if not all([api_key, model_id]):
                raise ValueError("Configuration OpenAI standard incomplète dans .env (OPENAI_API_KEY, OPENAI_CHAT_MODEL_ID requis).")

            # Création du transport et du client httpx personnalisés
            logging_http_transport = LoggingHttpTransport(logger=logger)
            custom_httpx_client = httpx.AsyncClient(transport=logging_http_transport)

            # Création du client AsyncOpenAI avec le client httpx personnalisé
            # Création du client AsyncOpenAI avec le client httpx personnalisé
            client_args = {
                "api_key": api_key,
                "http_client": custom_httpx_client
            }
            if org_id and "your_openai_org_id_here" not in org_id:
                client_args["organization"] = org_id
            
            openai_custom_async_client = AsyncOpenAI(**client_args)
            
            llm_instance = OpenAIChatCompletion(
                service_id=service_id,
                ai_model_id=model_id,
                async_client=openai_custom_async_client # Utilisation du client OpenAI personnalisé
                # api_key et org_id ne sont plus passés directement ici, car gérés par openai_custom_async_client
            )
            logger.info(f"Service LLM OpenAI ({model_id}) créé avec ID '{service_id}' et HTTP client personnalisé.")

    except ValueError as ve: # Attraper specific ValueError de la validation
        logger.critical(f"Erreur de configuration LLM: {ve}")
        raise # Renvoyer l'erreur de configuration
    except Exception as e:
        logger.critical(f"Erreur critique lors de la création du service LLM: {e}", exc_info=True)
        raise RuntimeError(f"Impossible de configurer le service LLM: {e}")

    if not llm_instance:
        # Ne devrait pas arriver si les exceptions sont bien gérées
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