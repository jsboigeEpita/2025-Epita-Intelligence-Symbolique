# Fichier: argumentation_analysis/kernel/kernel_builder.py

import os
from typing import List, Dict, Any

import semantic_kernel as sk
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    AzureTextEmbedding,
)


# 1. Modèles Pydantic pour une configuration typée
class AIServiceSettings(BaseModel):
    """Définit la configuration pour un service IA."""
    service_id: str = Field(..., alias="service_id")
    model_id: str = Field(..., alias="model_id")
    env_api_key: str = Field(..., alias="env_api_key")
    env_endpoint: str = Field(..., alias="env_endpoint")


class KernelSettings(BaseModel):
    """Modèle racine pour la configuration du kernel."""
    ai_services: Dict[str, AIServiceSettings]


# 2. Classe de construction du Kernel
class KernelBuilder:
    """
    Classe responsable de la construction et configuration du Kernel
    à partir de fichiers de configuration.
    """

    @staticmethod
    def load_settings(config_path: str, env_path: str) -> KernelSettings:
        """Charge la configuration depuis les fichiers YAML et .env."""
        load_dotenv(dotenv_path=env_path)
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return KernelSettings(**config)

    @staticmethod
    def create_kernel(settings: KernelSettings) -> sk.Kernel:
        """Crée et configure une instance du Kernel."""
        kernel = sk.Kernel()

        service_map = {
            "azure_openai_embedding": AzureTextEmbedding,
            "azure_openai_chat_gpt4": AzureChatCompletion,
        }

        for service_name, service_settings in settings.ai_services.items():
            service_class = service_map.get(service_name)
            if not service_class:
                raise ValueError(f"Service IA inconnu: {service_name}")

            api_key = os.getenv(service_settings.env_api_key)
            endpoint = os.getenv(service_settings.env_endpoint)

            if not api_key or not endpoint:
                raise ValueError(f"Clé API ou endpoint manquant pour {service_name}")

            service_instance = service_class(
                service_id=service_settings.service_id,
                model_id=service_settings.model_id,
                api_key=api_key,
                endpoint=endpoint,
            )
            kernel.add_service(service_instance)

        return kernel