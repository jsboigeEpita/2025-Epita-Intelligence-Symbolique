# core/llm_service.py
import logging
import os
from dotenv import load_dotenv
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion
from typing import Union # Pour type hint

logger = logging.getLogger("Orchestration.LLM")
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); logger.addHandler(handler); logger.setLevel(logging.INFO)


def create_llm_service(service_id: str = "global_llm_service") -> Union[OpenAIChatCompletion, AzureChatCompletion]:
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
    logger.info(f"--- Configuration du Service LLM ({service_id}) ---")
    load_dotenv(override=True) # Recharger au cas où

    api_key = os.getenv("OPENAI_API_KEY")
    model_id = os.getenv("OPENAI_CHAT_MODEL_ID")
    endpoint = os.getenv("OPENAI_ENDPOINT")
    org_id = os.getenv("OPENAI_ORG_ID")
    use_azure_openai = bool(endpoint)

    llm_instance = None
    try:
        if use_azure_openai:
            logger.info("Configuration Service: AzureChatCompletion...")
            if not all([api_key, model_id, endpoint]):
                raise ValueError("Configuration Azure OpenAI incomplète dans .env (OPENAI_API_KEY, OPENAI_CHAT_MODEL_ID, OPENAI_ENDPOINT requis).")
            llm_instance = AzureChatCompletion(
                service_id=service_id,
                deployment_name=model_id,
                endpoint=endpoint,
                api_key=api_key
            )
            logger.info(f"Service LLM Azure ({model_id}) créé avec ID '{service_id}'.")
        else:
            logger.info("Configuration Service: OpenAIChatCompletion...")
            if not all([api_key, model_id]):
                raise ValueError("Configuration OpenAI standard incomplète dans .env (OPENAI_API_KEY, OPENAI_CHAT_MODEL_ID requis).")
            llm_instance = OpenAIChatCompletion(
                service_id=service_id,
                ai_model_id=model_id,
                api_key=api_key,
                org_id=org_id # Peut être None
            )
            logger.info(f"Service LLM OpenAI ({model_id}) créé avec ID '{service_id}'.")

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

# Optionnel : Log de chargement
module_logger = logging.getLogger(__name__)
module_logger.debug("Module core.llm_service chargé.")