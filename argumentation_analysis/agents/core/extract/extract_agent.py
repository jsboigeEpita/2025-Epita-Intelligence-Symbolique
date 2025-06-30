"""
Implémentation de l'agent spécialisé dans l'extraction de texte.

Ce module définit `ExtractAgent`, un agent dont la mission est de localiser
et d'extraire avec précision des passages de texte pertinents à partir de
documents sources volumineux.

L'architecture de l'agent repose sur une collaboration entre :
-   **Fonctions Sémantiques** : Utilisent un LLM pour proposer de manière
    intelligente des marqueurs de début et de fin pour un extrait de texte,
    en se basant sur une description sémantique (son "nom").
-   **Plugin Natif (`ExtractAgentPlugin`)** : Fournit des outils déterministes
    pour manipuler le texte, comme l'extraction effective du contenu entre
    deux marqueurs.
-   **Fonctions Utilitaires** : Offrent des services de support comme le
    chargement de texte à partir de diverses sources.

Cette approche hybride permet de combiner la compréhension contextuelle du LLM
avec la précision et la fiabilité du code natif.
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
from semantic_kernel.functions import KernelArguments
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
    # Correction de l'import pour utiliser un chemin absolu et robuste
    from argumentation_analysis.ui.extract_utils import (
        load_source_text, extract_text_with_markers, find_similar_text,
    )

_lazy_imports()


class ExtractAgent(BaseAgent):
    """
    Agent spécialisé dans l'extraction de passages de texte sémantiquement pertinents.

    Cet agent orchestre un processus en plusieurs étapes pour extraire un passage
    de texte (un "extrait") à partir d'un document source plus large. Il ne se
    contente pas d'une simple recherche par mot-clé, mais utilise un LLM pour
    localiser un passage basé sur sa signification.

    Le flux de travail typique est le suivant :
    1.  Le LLM propose des marqueurs de début et de fin pour l'extrait (`extract_from_name`).
    2.  Une fonction native extrait le texte entre ces marqueurs.
    3.  (Optionnel) Le LLM valide si le texte extrait correspond bien à la demande initiale.

    Attributes:
        EXTRACT_SEMANTIC_FUNCTION_NAME (ClassVar[str]): Nom de la fonction sémantique
            utilisée pour proposer les marqueurs d'un extrait.
        VALIDATE_SEMANTIC_FUNCTION_NAME (ClassVar[str]): Nom de la fonction sémantique
            utilisée pour valider la pertinence d'un extrait.
        NATIVE_PLUGIN_NAME (ClassVar[str]): Nom sous lequel le plugin natif
            (`ExtractAgentPlugin`) est enregistré dans le kernel.
        _find_similar_text_func (Callable): Dépendance injectée pour la recherche de texte.
        _extract_text_func (Callable): Dépendance injectée pour l'extraction de texte.
        _native_extract_plugin (Optional[ExtractAgentPlugin]): Instance du plugin natif.
    """
    
    EXTRACT_SEMANTIC_FUNCTION_NAME: ClassVar[str] = "extract_from_name_semantic"
    VALIDATE_SEMANTIC_FUNCTION_NAME: ClassVar[str] = "validate_extract_semantic"
    NATIVE_PLUGIN_NAME: ClassVar[str] = "ExtractNativePlugin"

    def __init__(
        self,
        kernel: sk.Kernel,
        agent_name: str = "ExtractAgent",
        llm_service_id: str = None,
        plugins: list = None,
        find_similar_text_func: Optional[Callable] = None,
        extract_text_func: Optional[Callable] = None,
    ):
        """
        Initialise l'agent d'extraction.
        """
        if plugins is None:
            plugins = [ExtractAgentPlugin()]

        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            system_prompt=EXTRACT_AGENT_INSTRUCTIONS,
            llm_service_id=llm_service_id,
            plugins=plugins
        )
        
        self._find_similar_text_func = find_similar_text_func or find_similar_text
        self._extract_text_func = extract_text_func or extract_text_with_markers
        self._native_extract_plugin = next((p for p in plugins if isinstance(p, ExtractAgentPlugin)), None)

        if not llm_service_id:
            self.logger.warning(f"Aucun llm_service_id fourni pour {self.name}. Les fonctions sémantiques ne seront pas initialisées.")
            return

        self._register_semantic_functions(llm_service_id)

    def _register_semantic_functions(self, llm_service_id: str):
        """Enregistre les fonctions sémantiques dans le kernel."""
        self.logger.info(f"Enregistrement des fonctions sémantiques pour {self.name} avec le service LLM ID: {llm_service_id}")

        execution_settings = self._kernel.get_prompt_execution_settings_from_service_id(llm_service_id)
        
        # Fonction d'extraction
        extract_prompt_template_config = PromptTemplateConfig(
            template=EXTRACT_FROM_NAME_PROMPT,
            name=self.EXTRACT_SEMANTIC_FUNCTION_NAME,
            description="Propose des marqueurs de début et de fin pour un extrait basé sur son nom.",
            input_variables=[
                {"name": "extract_name", "description": "Nom de l'extrait à trouver", "is_required": True},
                {"name": "source_name", "description": "Nom de la source", "is_required": True},
                {"name": "extract_context", "description": "Texte source dans lequel chercher", "is_required": True}
            ],
            execution_settings=execution_settings
        )
        self._kernel.add_function(self.EXTRACT_SEMANTIC_FUNCTION_NAME, extract_prompt_template_config, plugin_name=self.name)
        self.logger.info(f"Fonction sémantique '{self.EXTRACT_SEMANTIC_FUNCTION_NAME}' enregistrée dans le plugin '{self.name}'.")

        # Fonction de validation
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
            execution_settings=execution_settings
        )
        self._kernel.add_function(self.VALIDATE_SEMANTIC_FUNCTION_NAME, validate_prompt_template_config, plugin_name=self.name)
        self.logger.info(f"Fonction sémantique '{self.VALIDATE_SEMANTIC_FUNCTION_NAME}' enregistrée dans le plugin '{self.name}'.")

    def get_agent_capabilities(self) -> Dict[str, Any]:
        return {
            "extract_from_name": "Extrait un passage pertinent à partir de la dénomination de l'extrait.",
            "repair_extract": "Répare un extrait existant en utilisant sa dénomination.",
        }

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
        """
        Coordonne le processus complet d'extraction d'un passage à partir de son nom.

        Ce workflow implique plusieurs étapes :
        1.  Charge le texte source si non fourni.
        2.  Appelle la fonction sémantique `extract_from_name_semantic` pour obtenir une
            proposition de marqueurs de début et de fin.
        3.  Parse la réponse JSON du LLM.
        4.  Utilise la fonction native `_extract_text_func` pour extraire physiquement le
            texte entre les marqueurs proposés.
        5.  Retourne un objet `ExtractResult` encapsulant le succès ou l'échec de
            chaque étape.

        Args:
            source_info (Dict[str, Any]): Dictionnaire contenant des informations sur
                le texte source (par exemple, le chemin du fichier).
            extract_name (str): Le nom ou la description sémantique de l'extrait à trouver.
            source_text (Optional[str]): Le texte source complet. S'il est `None`, il est
                chargé dynamiquement en utilisant `source_info`.

        Returns:
            ExtractResult: Un objet de résultat détaillé contenant le statut, les marqueurs,
            le texte extrait et les messages d'erreur éventuels.
        """
        source_name = source_info.get("source_name", "Source inconnue")
        self.logger.info(f"Extraction pour '{extract_name}' dans la source '{source_name}'.")

        if source_text is None:
            source_text, url = load_source_text(source_info)
            if not source_text:
                msg = f"Impossible de charger le texte source depuis {url}"
                return ExtractResult(source_name=source_name, extract_name=extract_name, status="error", message=msg)

        arguments = KernelArguments(
            extract_name=extract_name,
            source_name=source_name,
            extract_context=source_text,
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
        Point d'entrée principal pour l'invocation de l'agent dans un scénario de chat.

        Cette méthode est conçue pour être appelée par un planificateur ou un orchestrateur.
        Elle analyse l'historique de la conversation pour extraire deux informations clés :
        1.  Le **texte source** : typiquement le premier message de l'utilisateur.
        2.  Le **nom de l'extrait** : recherché dans la dernière instruction, souvent
            fournie par un agent planificateur.

        Elle délègue ensuite le travail à la méthode `extract_from_name` et formate
        le résultat en `ChatMessageContent`.
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