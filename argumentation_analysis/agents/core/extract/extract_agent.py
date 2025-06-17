"""
Agent d'extraction pour l'analyse argumentative.

Ce module implémente `ExtractAgent`, un agent spécialisé dans l'extraction
d'informations pertinentes à partir de textes sources. Il utilise une combinaison
de fonctions sémantiques (via Semantic Kernel) et de fonctions natives pour
proposer, valider et gérer des extraits de texte. L'agent est conçu pour
interagir avec des définitions d'extraits et peut gérer des textes volumineux
grâce à des stratégies de découpage et de recherche contextuelle.

Fonctionnalités principales :
- Proposition de marqueurs (début/fin) pour un extrait basé sur son nom.
- Validation de la pertinence d'un extrait proposé.
- Réparation d'extraits existants dont les marqueurs sont invalides.
- Mise à jour et ajout de nouveaux extraits dans une structure de données.
- Utilisation d'un plugin natif (`ExtractAgentPlugin`) pour des opérations
  textuelles spécifiques (recherche dichotomique, extraction de blocs).
"""

import os
import re
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union, Callable, ClassVar

import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.prompt_template.prompt_template_config import PromptTemplateConfig

from ..abc.agent_bases import BaseAgent

# Import des définitions et prompts locaux
from .extract_definitions import ExtractAgentPlugin, ExtractResult
from .prompts import (
    EXTRACT_AGENT_INSTRUCTIONS,
    EXTRACT_FROM_NAME_PROMPT,
    VALIDATE_EXTRACT_PROMPT,
)

# Fonction d'importation paresseuse pour éviter les importations circulaires
def _lazy_imports() -> None:
    """
    Importe les modules de manière paresseuse pour éviter les importations circulaires.
    """
    global load_source_text, extract_text_with_markers, find_similar_text
    try:
        from ...ui.extract_utils import (
            load_source_text, extract_text_with_markers, find_similar_text,
        )
    except ImportError:
        from argumentation_analysis.ui.extract_utils import (
            load_source_text, extract_text_with_markers, find_similar_text,
        )

_lazy_imports()


class ExtractAgent(BaseAgent):
    """
    Agent spécialisé dans l'extraction d'informations pertinentes de textes sources.
    """
    
    EXTRACT_SEMANTIC_FUNCTION_NAME: ClassVar[str] = "extract_from_name_semantic"
    VALIDATE_SEMANTIC_FUNCTION_NAME: ClassVar[str] = "validate_extract_semantic"
    NATIVE_PLUGIN_NAME: ClassVar[str] = "ExtractNativePlugin"

    def __init__(
        self,
        kernel: sk.Kernel,
        agent_name: str = "ExtractAgent",
        find_similar_text_func: Optional[Callable] = None,
        extract_text_func: Optional[Callable] = None
    ):
        super().__init__(kernel, agent_name, EXTRACT_AGENT_INSTRUCTIONS)
        self._find_similar_text_func = find_similar_text_func or find_similar_text
        self._extract_text_func = extract_text_func or extract_text_with_markers

    def get_agent_capabilities(self) -> Dict[str, Any]:
        return {
            "extract_from_name": "Extrait un passage pertinent à partir de la dénomination de l'extrait.",
            "repair_extract": "Répare un extrait existant en utilisant sa dénomination.",
        }

    def setup_agent_components(self, llm_service_id: str) -> None:
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants pour {self.name} avec le service LLM ID: {llm_service_id}")
        self._native_extract_plugin = ExtractAgentPlugin()
        self._kernel.add_plugin(self._native_extract_plugin, plugin_name=self.NATIVE_PLUGIN_NAME)
        self.logger.info(f"Plugin natif '{self.NATIVE_PLUGIN_NAME}' enregistré.")
        extract_prompt_template_config = PromptTemplateConfig(
            template=EXTRACT_FROM_NAME_PROMPT,
            name=self.EXTRACT_SEMANTIC_FUNCTION_NAME,
            description="Propose des marqueurs de début et de fin pour un extrait basé sur son nom.",
            input_variables=[
                {"name": "extract_name", "description": "Nom de l'extrait à trouver", "is_required": True},
                {"name": "source_name", "description": "Nom de la source", "is_required": True},
                {"name": "extract_context", "description": "Texte source dans lequel chercher", "is_required": True}
            ],
            execution_settings=self._kernel.get_prompt_execution_settings_from_service_id(llm_service_id)
        )
        self._kernel.add_function(
            function_name=self.EXTRACT_SEMANTIC_FUNCTION_NAME,
            prompt_template_config=extract_prompt_template_config,
            plugin_name=self.name
        )
        self.logger.info(f"Fonction sémantique '{self.EXTRACT_SEMANTIC_FUNCTION_NAME}' enregistrée dans le plugin '{self.name}'.")
        validate_prompt_template_config = PromptTemplateConfig(
            template=VALIDATE_EXTRACT_PROMPT,
            name=self.VALIDATE_SEMANTIC_FUNCTION_NAME,
            description="Valide si un extrait de texte est pertinent par rapport à sa dénomination.",
            input_variables=[
                {"name": "extract_name", "description": "Nom de l'extrait", "is_required": True},
                {"name": "source_name", "description": "Nom de la source", "is_required": True},
                {"name": "start_marker", "description": "Marqueur de début", "is_required": True},
                {"name": "end_marker", "description": "Marqueur de fin", "is_required": True},
                {"name": "template_start", "description": "Modèle de début (optionnel)", "is_required": False},
                {"name": "extracted_text", "description": "Texte extrait", "is_required": True},
                {"name": "explanation", "description": "Explication de l'extraction LLM", "is_required": True}
            ],
            execution_settings=self._kernel.get_prompt_execution_settings_from_service_id(llm_service_id)
        )
        self._kernel.add_function(
            function_name=self.VALIDATE_SEMANTIC_FUNCTION_NAME,
            prompt_template_config=validate_prompt_template_config,
            plugin_name=self.name
        )
        self.logger.info(f"Fonction sémantique '{self.VALIDATE_SEMANTIC_FUNCTION_NAME}' enregistrée dans le plugin '{self.name}'.")

    @property
    def native_extract_plugin(self) -> ExtractAgentPlugin:
        if self._native_extract_plugin is None:
            raise RuntimeError("Plugin natif d'extraction non initialisé. Appelez setup_agent_components.")
        return self._native_extract_plugin

    async def extract_from_name(
        self,
        source_info: Dict[str, Any],
        extract_name: str,
        source_text: Optional[str] = None
    ) -> ExtractResult:
        source_name = source_info.get("source_name", "Source inconnue")
        self.logger.info(f"Extraction à partir du nom '{extract_name}' dans la source '{source_name}'...")
        
        if source_text is None:
            self.logger.debug("Aucun texte source direct fourni. Tentative de chargement depuis source_info.")
            source_text, url = load_source_text(source_info)
            if not source_text:
                return ExtractResult(source_name=source_name, extract_name=extract_name, status="error", message=f"Impossible de charger le texte source: {url}")
        
        arguments = KernelArguments(
            extract_name=extract_name,
            source_name=source_name,
            extract_context=source_text # On passe le texte complet
        )
        try:
            response = await self._kernel.invoke(
                plugin_name=self.name,
                function_name=self.EXTRACT_SEMANTIC_FUNCTION_NAME,
                arguments=arguments
            )
            extract_content_result = str(response)
        except Exception as e:
            return ExtractResult(source_name=source_name, extract_name=extract_name, status="error", message=f"Erreur LLM lors de la proposition de bornes: {str(e)}")
        
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', extract_content_result)
            extract_json = json.loads(json_match.group(1) if json_match else extract_content_result)
        except json.JSONDecodeError:
            self.logger.warning(f"Réponse non JSON de l'extraction pour '{extract_name}': {extract_content_result}")
            return ExtractResult(source_name=source_name, extract_name=extract_name, status="error", message="Réponse non-JSON de l'agent LLM.", explanation=extract_content_result)

        start_marker = extract_json.get("start_marker", "")
        end_marker = extract_json.get("end_marker", "")
        explanation = extract_json.get("explanation", "Aucune explication fournie.")

        if not start_marker or not end_marker:
            return ExtractResult(source_name=source_name, extract_name=extract_name, status="error", message="Bornes invalides ou manquantes proposées par l'agent.", explanation=explanation)

        extracted_text, status_msg, start_found, end_found = self._extract_text_func(source_text, start_marker, end_marker, "")
        if not start_found or not end_found:
            return ExtractResult(source_name=source_name, extract_name=extract_name, status="error", message=f"Bornes non trouvées dans le texte: {status_msg}", start_marker=start_marker, end_marker=end_marker, explanation=explanation)
        
        return ExtractResult(
            source_name=source_name,
            extract_name=extract_name,
            status="valid",
            message="Extraction réussie",
            start_marker=start_marker,
            end_marker=end_marker,
            explanation=explanation,
            extracted_text=extracted_text
        )

    async def get_response(self, kernel: "Kernel", arguments: Optional["KernelArguments"] = None) -> list[ChatMessageContent]:
        """Délègue l'invocation à la méthode invoke_single."""
        self.logger.debug(f"get_response appelé, délégation à invoke_single pour {self.name}.")
        return await self.invoke_single(kernel, arguments)

    async def invoke_single(self, kernel: "Kernel", arguments: Optional["KernelArguments"] = None) -> list[ChatMessageContent]:
        """
        Gère l'invocation de l'agent en extrayant le contenu pertinent de l'historique du chat.
        """
        self.logger.info(f"Invocation de {self.name} via invoke_single.")
        history = arguments.get("chat_history") if arguments else None

        if not history:
            error_msg = "L'historique du chat est vide, impossible d'extraire."
            self.logger.error(error_msg)
            return [ChatMessageContent(role="assistant", content=json.dumps({"error": error_msg}), name=self.name)]

        # Stratégie : prendre le premier message utilisateur comme source principale
        source_message = next((msg for msg in history if msg.role == "user"), history[0])
        source_text = source_message.content
        
        # Le nom de l'extrait est déterminé par le dernier message (instruction du PM)
        last_message = history[-1].content
        # Regex pour trouver une instruction comme extract(name="...")
        match = re.search(r'extract\s*\(\s*name="([^"]+)"', last_message)
        if match:
            extract_name = match.group(1)
            self.logger.info(f"Nom d'extrait trouvé dans l'instruction: '{extract_name}'")
        else:
            extract_name = "Le point principal de l'auteur" # Fallback
            self.logger.warning(f"Aucun nom d'extrait spécifique trouvé, utilisation du nom par défaut: '{extract_name}'")

        source_info = {"source_name": "Source Conversationnelle"}

        try:
            result = await self.extract_from_name(source_info, extract_name, source_text=str(source_text))
            response_content = result.to_json()
            response_message = ChatMessageContent(
                role="assistant",
                content=response_content,
                name=self.name,
                metadata={'task_name': 'extract_from_name', 'status': result.status}
            )
        except Exception as e:
            self.logger.error(f"Erreur dans invoke_single de ExtractAgent: {e}", exc_info=True)
            response_message = ChatMessageContent(
                role="assistant",
                content=json.dumps({"error": f"Erreur lors de l'extraction: {str(e)}"}),
                name=self.name
            )
        
        return [response_message]