# Fichier: argumentation_analysis/kernel/kernel_builder.py

import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatCompletion,
)
from argumentation_analysis.config.settings import AppSettings


class KernelBuilder:
    """
    Classe responsable de la construction et de la configuration du Kernel
    à partir d'un objet de configuration centralisé.
    """

    @staticmethod
    def create_kernel(settings: AppSettings) -> sk.Kernel:
        """Crée et configure une instance du Kernel."""
        kernel = sk.Kernel()

        llm_service_name = settings.service_manager.default_llm_service_id

        if llm_service_name == "openai":
            if settings.openai.api_key:
                service = OpenAIChatCompletion(
                    service_id="openai",
                    ai_model_id=settings.openai.chat_model_id,
                    api_key=settings.openai.api_key.get_secret_value(),
                )
            else:
                raise ValueError("La clé API OpenAI n'est pas configurée.")
        elif llm_service_name == "azure":
            if settings.azure_openai.api_key and settings.azure_openai.endpoint:
                service = AzureChatCompletion(
                    service_id="azure",
                    deployment_name=settings.azure_openai.deployment_name,
                    endpoint=str(settings.azure_openai.endpoint),
                    api_key=settings.azure_openai.api_key.get_secret_value(),
                )
            else:
                raise ValueError(
                    "La clé API ou l'endpoint Azure ne sont pas configurés."
                )
        else:
            raise ValueError(f"Service LLM global inconnu: {llm_service_name}")

        kernel.add_service(service)
        return kernel
