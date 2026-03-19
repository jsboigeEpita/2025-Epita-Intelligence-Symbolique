# -*- coding: utf-8 -*-
"""
Module contenant la classe NarrativeAgent pour interagir avec le Semantic Kernel.
"""
import os
import httpx
import semantic_kernel as sk
from openai import AsyncOpenAI
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatCompletion
from semantic_kernel.functions import KernelArguments
from pathlib import Path
from dotenv import load_dotenv
import logging
import tiktoken

# Initialisation de l'encodeur de tokens
ENCODER = tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    """Compte le nombre de tokens dans une chaîne de caractères."""
    return len(ENCODER.encode(text))

class NarrativeAgent:
    """
    Agent chargé de la génération de chapitres narratifs via le Semantic Kernel.
    """

    def __init__(self, kernel_settings):
        """
        Initialise le NarrativeAgent.
        Args:
            kernel_settings (dict): Paramètres pour le Semantic Kernel.
        """
        self.kernel = sk.Kernel()

        # Charger les variables d'environnement depuis le fichier .env à la racine
        dotenv_path = Path(__file__).parent.parent.parent / '.env'
        load_dotenv(dotenv_path=dotenv_path)

        # Configuration du service OpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        org_id = os.environ.get("OPENAI_ORG_ID")

        if not api_key:
            raise ValueError("La variable d'environnement OPENAI_API_KEY est requise.")

        # Configuration du client HTTP avec un timeout personnalisé
        client_timeout = httpx.Timeout(120.0)
        custom_httpx_client = httpx.AsyncClient(timeout=client_timeout)

        # Création du client OpenAI avec le client HTTP personnalisé
        async_openai_client = AsyncOpenAI(
            api_key=api_key,
            organization=org_id,
            http_client=custom_httpx_client
        )

        self.kernel.add_service(
            OpenAIChatCompletion(
                service_id="chat-gpt",
                ai_model_id="gpt-4-turbo-preview",
                async_client=async_openai_client,
            )
        )
        self.narrative_plugin = None
        # Le nom de la fonction doit correspondre au nom du répertoire contenant skprompt.txt
        self.function_name = kernel_settings.get("function_name", "ChapterGenerator")
        
        self._load_plugin(kernel_settings)

    def _load_plugin(self, kernel_settings):
        """Charge le plugin sémantique depuis le système de fichiers."""
        plugin_name = kernel_settings["plugin_name"]
        
        # Le chemin vers les plugins doit être relatif au projet
        plugins_directory = Path(__file__).parent.parent.parent.parent / "plugins"
        
        logging.info(f"Chargement du plugin '{plugin_name}' depuis '{plugins_directory}'")
        
        try:
            self.narrative_plugin = self.kernel.add_plugin(
                parent_directory=str(plugins_directory), plugin_name=plugin_name
            )
            logging.info(f"Plugin '{plugin_name}' chargé avec succès.")
        except Exception as e:
            logging.error(f"Erreur lors du chargement du plugin '{plugin_name}': {e}", exc_info=True)
            raise

    async def generate_narrative(self, context, commit_range=""):
        """
        Invoque le plugin pour générer un nouveau chapitre narratif.

        Args:
            context (dict): Le contexte technique et narratif combiné.
            commit_range (str): La chaîne de caractères représentant la plage des commits.

        Returns:
            str: Le chapitre narratif généré par le LLM.
        """
        if not self.narrative_plugin:
            error_msg = "Le plugin de narration n'est pas chargé."
            logging.error(error_msg)
            return error_msg

        try:
            # Le prompt attend maintenant 5 arguments, y compris commit_range
            
            # Log de la taille des contextes
            tech_context = str(context.get("technical_context", ""))
            narr_context = str(context.get("narrative_context", ""))
            hist_context = str(context.get("historical_context", ""))
            strat_preamble = str(context.get("strategic_preamble", ""))

            logging.info(f"Taille du contexte technique: {count_tokens(tech_context)} tokens")
            logging.info(f"Taille du contexte narratif: {count_tokens(narr_context)} tokens")
            logging.info(f"Taille du contexte historique: {count_tokens(hist_context)} tokens")
            logging.info(f"Taille du préambule stratégique: {count_tokens(strat_preamble)} tokens")
            
            total_tokens = count_tokens(tech_context) + count_tokens(narr_context) + count_tokens(hist_context) + count_tokens(strat_preamble)
            logging.info(f"Taille totale estimée des tokens: {total_tokens}")

            kernel_args = KernelArguments(
                technical_context=tech_context,
                narrative_context=narr_context,
                historical_context=hist_context,
                strategic_preamble=strat_preamble,
                commit_range=commit_range,
            )
            
            # Utilisation du nom correct du plugin et de la fonction
            plugin_function = self.narrative_plugin[self.function_name]

            result = await self.kernel.invoke(
                plugin_function,
                kernel_args
            )
            
            result_str = str(result).strip()
            if not result_str:
                raise ValueError("La génération du chapitre a retourné un résultat vide.")
            return result_str
        except Exception as e:
            logging.error(f"Erreur critique lors de l'invocation du kernel : {e}", exc_info=True)
            raise  # Relancer l'exception pour arrêter le script principal
