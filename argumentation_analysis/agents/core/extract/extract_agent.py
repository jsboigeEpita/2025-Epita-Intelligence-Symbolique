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
from semantic_kernel.contents import ChatMessageContent # Potentiellement plus nécessaire directement
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.prompt_template.prompt_template_config import PromptTemplateConfig

# Import de la classe de base
from ..abc.agent_bases import BaseAgent

# Import des définitions et prompts locaux
from .extract_definitions import ExtractAgentPlugin, ExtractResult # ExtractAgentPlugin sera utilisé comme plugin natif
from .prompts import (
    EXTRACT_AGENT_INSTRUCTIONS, # Utilisé comme system_prompt
    # VALIDATION_AGENT_INSTRUCTIONS, # Plus nécessaire si validation_agent est supprimé
    EXTRACT_FROM_NAME_PROMPT,
    VALIDATE_EXTRACT_PROMPT,
    # REPAIR_EXTRACT_PROMPT # Non utilisé actuellement
)

# Fonction d'importation paresseuse pour éviter les importations circulaires
def _lazy_imports() -> None:
    """
    Importe les modules de manière paresseuse pour éviter les importations circulaires.

    Cette fonction est appelée une fois au chargement du module `extract_agent`.
    Elle peuple les variables globales nécessaires à partir d'autres modules,
    principalement `argumentation_analysis.ui.config`,
    `argumentation_analysis.ui.utils`, et `argumentation_analysis.ui.extract_utils`.
    Cela permet à `ExtractAgent` d'accéder à des configurations et des utilitaires
    sans créer de dépendances d'importation directes au niveau supérieur du module,
    ce qui pourrait causer des problèmes si ces modules importent eux-mêmes `ExtractAgent`.

    Les variables globales peuplées incluent `ENCRYPTION_KEY`, `CONFIG_FILE`,
    `CONFIG_FILE_JSON`, `load_from_cache`, `reconstruct_url`, `load_source_text`,
    `extract_text_with_markers`, `find_similar_text`,
    `load_extract_definitions_safely`, et `save_extract_definitions_safely`.
    """
    global ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
    global load_from_cache, reconstruct_url
    global load_source_text, extract_text_with_markers, find_similar_text
    global load_extract_definitions_safely, save_extract_definitions_safely
    # global create_llm_service # create_llm_service ne sera plus appelé ici

    try:
        # Import relatif depuis le package agents/core
        # Corrigé de '....' à '...' car ui est un sous-répertoire de argumentation_analysis
        from ...ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
        from ...ui.utils import load_from_cache, reconstruct_url
        from ...ui.extract_utils import (
            load_source_text, extract_text_with_markers, find_similar_text,
            load_extract_definitions_safely, save_extract_definitions_safely
        )
        # from ...core.llm_service import create_llm_service # Déplacé
    except ImportError:
        # Fallback pour les imports absolus
        from argumentation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
        from argumentation_analysis.ui.utils import load_from_cache, reconstruct_url
        from argumentation_analysis.ui.extract_utils import (
            load_source_text, extract_text_with_markers, find_similar_text,
            load_extract_definitions_safely, save_extract_definitions_safely
        )
        # from argumentation_analysis.core.llm_service import create_llm_service # Déplacé

# Appeler la fonction d'importation paresseuse
_lazy_imports()

# Configuration du logging - BaseAgent s'en charge, mais on peut garder le handler spécifique
# logger = logging.getLogger(__name__) # Sera initialisé par BaseAgent

# Création d'un handler pour écrire les logs dans un fichier
# file_handler = logging.FileHandler("extract_agent.log") # Peut être configuré au niveau du projet
# file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'))
# logger.addHandler(file_handler) # Le logger de BaseAgent peut être utilisé


class ExtractAgent(BaseAgent):
    """
    Agent spécialisé dans l'extraction d'informations pertinentes de textes sources.

    Hérite de `BaseAgent` et implémente des fonctionnalités pour proposer,
    valider, réparer et gérer des extraits de texte. Utilise des fonctions
    sémantiques pour l'interaction avec les LLMs et un plugin natif pour
    des opérations textuelles spécifiques.

    Attributes:
        EXTRACT_SEMANTIC_FUNCTION_NAME (str): Nom de la fonction sémantique pour la proposition d'extraits.
        VALIDATE_SEMANTIC_FUNCTION_NAME (str): Nom de la fonction sémantique pour la validation d'extraits.
        NATIVE_PLUGIN_NAME (str): Nom du plugin natif contenant les fonctions d'aide à l'extraction.
        find_similar_text_func (Callable): Fonction pour trouver du texte similaire.
        extract_text_func (Callable): Fonction pour extraire du texte basé sur des marqueurs.
        _native_extract_plugin (Optional[ExtractAgentPlugin]): Instance du plugin natif.
    """
    
    # Noms pour les fonctions sémantiques
    EXTRACT_SEMANTIC_FUNCTION_NAME: ClassVar[str] = "extract_from_name_semantic"
    VALIDATE_SEMANTIC_FUNCTION_NAME: ClassVar[str] = "validate_extract_semantic"
    NATIVE_PLUGIN_NAME: ClassVar[str] = "ExtractNativePlugin"

    find_similar_text_func: Optional[Callable] = None
    extract_text_func: Optional[Callable] = None
    _native_extract_plugin: Optional[ExtractAgentPlugin] = None

    def __init__(
        self,
        kernel: sk.Kernel,
        agent_name: str = "ExtractAgent",
        find_similar_text_func: Optional[Callable] = None,
        extract_text_func: Optional[Callable] = None
    ):
        """
        Initialise l'agent d'extraction.

        :param kernel: Le kernel Semantic Kernel à utiliser par l'agent.
        :type kernel: sk.Kernel
        :param agent_name: Nom de cet agent. Par défaut "ExtractAgent".
        :type agent_name: str
        :param find_similar_text_func: Fonction optionnelle pour trouver du texte similaire.
                                       Si None, utilise `find_similar_text` de `ui.utils`.
        :type find_similar_text_func: Optional[Callable]
        :param extract_text_func: Fonction optionnelle pour extraire du texte avec des marqueurs.
                                  Si None, utilise `extract_text_with_markers` de `ui.utils`.
        :type extract_text_func: Optional[Callable]
        """
        super().__init__(kernel, agent_name, EXTRACT_AGENT_INSTRUCTIONS)
        
        # Fonctions helper spécifiques à cet agent
        self.find_similar_text_func = find_similar_text_func or find_similar_text
        self.extract_text_func = extract_text_func or extract_text_with_markers

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Décrit les capacités principales de l'agent d'extraction.

        :return: Un dictionnaire mappant les noms des capacités à leurs descriptions.
        :rtype: Dict[str, Any]
        """
        return {
            "extract_from_name": "Extrait un passage pertinent à partir de la dénomination de l'extrait.",
            "repair_extract": "Répare un extrait existant en utilisant sa dénomination.",
            "update_extract_markers": "Met à jour les marqueurs d'un extrait avec les résultats d'une extraction.",
            "add_new_extract": "Ajoute un nouvel extrait à une source existante.",
            # Les fonctions du plugin natif pourraient aussi être listées ici si elles sont exposées publiquement
            "find_similar_markers_native": "Trouve des marqueurs similaires dans le texte source (fonction native).",
            "search_text_dichotomically_native": "Recherche un terme dans le texte en utilisant une approche dichotomique (fonction native).",
            "extract_blocks_native": "Extrait des blocs de texte avec chevauchement pour l'analyse (fonction native)."
        }

    def setup_agent_components(self, llm_service_id: str) -> None:
        """Configure les composants spécifiques de l'agent d'extraction dans le kernel Semantic Kernel.

        Enregistre le plugin natif `ExtractAgentPlugin` et les fonctions sémantiques
        pour l'extraction et la validation des extraits.

        :param llm_service_id: L'ID du service LLM à utiliser pour les fonctions sémantiques.
        :type llm_service_id: str
        :return: None
        :rtype: None
        """
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants pour {self.name} avec le service LLM ID: {llm_service_id}")

        # 1. Initialiser et enregistrer le plugin natif
        self._native_extract_plugin = ExtractAgentPlugin()
        self.sk_kernel.add_plugin(self._native_extract_plugin, plugin_name=self.NATIVE_PLUGIN_NAME)
        self.logger.info(f"Plugin natif '{self.NATIVE_PLUGIN_NAME}' enregistré.")

        # 2. Enregistrer les fonctions sémantiques
        # Fonction sémantique pour l'extraction
        extract_prompt_template_config = PromptTemplateConfig(
            template=EXTRACT_FROM_NAME_PROMPT,
            name=self.EXTRACT_SEMANTIC_FUNCTION_NAME,
            description="Propose des bornes (marqueurs de début et de fin) pour un extrait.",
            input_variables=[
                {"name": "extract_name", "description": "Dénomination de l'extrait", "is_required": True},
                {"name": "source_name", "description": "Nom de la source", "is_required": True},
                {"name": "extract_context", "description": "Contexte d'extraction (texte source ou résumé)", "is_required": True},
            ],
            execution_settings=self.sk_kernel.get_prompt_execution_settings_from_service_id(llm_service_id)
        )
        self.sk_kernel.add_function(
            function_name=self.EXTRACT_SEMANTIC_FUNCTION_NAME, # Ajout explicite
            prompt_template_config=extract_prompt_template_config,
            plugin_name=self.name
        )
        self.logger.info(f"Fonction sémantique '{self.EXTRACT_SEMANTIC_FUNCTION_NAME}' enregistrée dans le plugin '{self.name}'.")

        # Fonction sémantique pour la validation
        validate_prompt_template_config = PromptTemplateConfig(
            template=VALIDATE_EXTRACT_PROMPT,
            name=self.VALIDATE_SEMANTIC_FUNCTION_NAME,
            description="Valide un extrait proposé.",
            input_variables=[
                {"name": "extract_name", "description": "Dénomination de l'extrait", "is_required": True},
                {"name": "source_name", "description": "Nom de la source", "is_required": True},
                {"name": "start_marker", "description": "Marqueur de début proposé", "is_required": True},
                {"name": "end_marker", "description": "Marqueur de fin proposé", "is_required": True},
                {"name": "template_start", "description": "Template de début (optionnel)", "is_required": False, "default_value": ""},
                {"name": "extracted_text", "description": "Texte extrait", "is_required": True},
                {"name": "explanation", "description": "Explication de l'agent d'extraction", "is_required": True},
            ],
            execution_settings=self.sk_kernel.get_prompt_execution_settings_from_service_id(llm_service_id)
        )
        self.sk_kernel.add_function(
            function_name=self.VALIDATE_SEMANTIC_FUNCTION_NAME, # Ajout explicite
            prompt_template_config=validate_prompt_template_config,
            plugin_name=self.name
        )
        self.logger.info(f"Fonction sémantique '{self.VALIDATE_SEMANTIC_FUNCTION_NAME}' enregistrée dans le plugin '{self.name}'.")

    @property
    def native_extract_plugin(self) -> ExtractAgentPlugin:
        """Retourne l'instance du plugin natif d'extraction.

        :return: L'instance de `ExtractAgentPlugin`.
        :rtype: ExtractAgentPlugin
        :raises RuntimeError: Si le plugin natif n'a pas été initialisé (c'est-à-dire
                              si `setup_agent_components` n'a pas été appelé).
        """
        if self._native_extract_plugin is None:
            raise RuntimeError("Plugin natif d'extraction non initialisé. Appelez setup_agent_components.")
        return self._native_extract_plugin

    async def extract_from_name(
        self,
        source_info: Dict[str, Any],
        extract_name: str
    ) -> ExtractResult:
        """
        Propose et valide des marqueurs pour un extrait basé sur son nom et le texte source.

        Utilise une fonction sémantique pour proposer des marqueurs (`start_marker`, `end_marker`,
        `template_start`) et une autre pour valider la pertinence du texte extrait.
        Gère les textes volumineux en utilisant une approche dichotomique pour le contexte.

        :param source_info: Dictionnaire contenant les informations de la source
                            (nom, chemin, etc.).
        :type source_info: Dict[str, Any]
        :param extract_name: Le nom ou la description de l'extrait à trouver.
        :type extract_name: str
        :return: Un objet `ExtractResult` contenant les marqueurs proposés, le texte extrait,
                 le statut de l'extraction ("valid", "rejected", "error"), un message
                 et une explication.
        :rtype: ExtractResult
        """
        source_name = source_info.get("source_name", "Source inconnue")
        
        self.logger.info(f"Extraction à partir du nom '{extract_name}' dans la source '{source_info.get('source_name', 'Source inconnue')}'...")
        
        source_name = source_info.get("source_name", "Source inconnue")
        source_text, url = load_source_text(source_info)
        if not source_text:
            self.logger.error(f"Impossible de charger le texte source pour '{source_name}': {url}")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="error",
                message=f"Impossible de charger le texte source: {url}"
            )
        
        is_large_text = len(source_text) > 10000
        extract_context_for_llm = ""

        if is_large_text:
            self.logger.info(f"Texte volumineux détecté. Utilisation d'une approche dichotomique...")
            blocks = self.native_extract_plugin.extract_blocks(source_text, block_size=500, overlap=50)
            keywords = extract_name.lower().split()
            relevant_blocks_data = []
            
            for keyword in keywords:
                if len(keyword) > 3:
                    search_results = self.native_extract_plugin.search_text_dichotomically(source_text, keyword)
                    for result in search_results:
                        block_idx = result["block_start"] // 450
                        if block_idx < len(blocks):
                            relevant_blocks_data.append(blocks[block_idx])
            
            extract_context_for_llm = f"TEXTE SOURCE VOLUMINEUX ({len(source_text)} caractères).\n\n"
            extract_context_for_llm += f"Dénomination de l'extrait: {extract_name}\n\n"
            
            if relevant_blocks_data:
                extract_context_for_llm += "BLOCS PERTINENTS TROUVÉS:\n\n"
                for i, block_data in enumerate(relevant_blocks_data[:5]):
                    extract_context_for_llm += f"--- BLOC {i+1} (positions {block_data['start_pos']}-{block_data['end_pos']}) ---\n"
                    extract_context_for_llm += block_data["block"] + "\n\n"
            else:
                extract_context_for_llm += f"Début du texte:\n{source_text[:2500]}...\n\n"
                extract_context_for_llm += f"Fin du texte:\n...{source_text[-2500:]}"
        else:
            extract_context_for_llm = source_text
        
        arguments = KernelArguments(
            extract_name=extract_name,
            source_name=source_name,
            extract_context=extract_context_for_llm
        )
        
        extract_content_result = ""
        try:
            # Utilisation de self.sk_kernel.invoke pour appeler la fonction sémantique
            response = await self.sk_kernel.invoke(
                plugin_name=self.name,
                function_name=self.EXTRACT_SEMANTIC_FUNCTION_NAME,
                arguments=arguments
            )
            extract_content_result = str(response) # La réponse est un KernelContent ou similaire
        except Exception as e:
            self.logger.error(f"Erreur lors de l'invocation de la fonction sémantique '{self.EXTRACT_SEMANTIC_FUNCTION_NAME}': {e}")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="error",
                message=f"Erreur LLM lors de la proposition de bornes: {str(e)}"
            )
        
        # Extraire la réponse JSON de l'agent
        extract_content = extract_content_result
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', extract_content)
            if json_match:
                extract_json = json.loads(json_match.group(1))
            else:
                extract_json = json.loads(extract_content)
        except json.JSONDecodeError:
            self.logger.warning(f"Réponse non JSON de l'extraction pour '{extract_name}': {extract_content}")
            start_match = re.search(r'"start_marker"\s*:\s*"([^"]*)"', extract_content)
            end_match = re.search(r'"end_marker"\s*:\s*"([^"]*)"', extract_content)
            template_match = re.search(r'"template_start"\s*:\s*"([^"]*)"', extract_content)
            explanation_match = re.search(r'"explanation"\s*:\s*"([^"]*)"', extract_content)
            extract_json = {
                "start_marker": start_match.group(1) if start_match else "",
                "end_marker": end_match.group(1) if end_match else "",
                "template_start": template_match.group(1) if template_match else "",
                "explanation": explanation_match.group(1) if explanation_match else "Explication non disponible due à une réponse malformée."
            }

        start_marker = extract_json.get("start_marker", "")
        end_marker = extract_json.get("end_marker", "")
        template_start = extract_json.get("template_start", "")
        explanation = extract_json.get("explanation", "Aucune explication fournie par l'agent d'extraction.")

        if not start_marker or not end_marker:
            self.logger.warning(f"Bornes invalides ou manquantes proposées pour l'extrait '{extract_name}'. Start: '{start_marker}', End: '{end_marker}'")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="error",
                message="Bornes invalides ou manquantes proposées par l'agent.",
                explanation=explanation
            )

        extracted_text, status_msg, start_found, end_found = self.extract_text_func(
            source_text, start_marker, end_marker, template_start
        )

        if not start_found or not end_found:
            self.logger.warning(f"Bornes non trouvées dans le texte pour l'extrait '{extract_name}'. Status: {status_msg}")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="error",
                message=f"Bornes non trouvées dans le texte: {status_msg}",
                start_marker=start_marker,
                end_marker=end_marker,
                template_start=template_start,
                explanation=explanation
            )
        
        # Appel de la fonction sémantique de validation
        validation_args = KernelArguments(
            extract_name=extract_name,
            source_name=source_name,
            start_marker=start_marker,
            end_marker=end_marker,
            template_start=template_start,
            extracted_text=extracted_text if extracted_text else "Aucun texte extrait",
            explanation=explanation
        )
        
        validation_content_result = ""
        try:
            response = await self.sk_kernel.invoke(
                plugin_name=self.name,
                function_name=self.VALIDATE_SEMANTIC_FUNCTION_NAME,
                arguments=validation_args
            )
            validation_content_result = str(response)
        except Exception as e:
            self.logger.error(f"Erreur lors de l'invocation de la fonction sémantique '{self.VALIDATE_SEMANTIC_FUNCTION_NAME}': {e}")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="error",
                message=f"Erreur LLM lors de la validation: {str(e)}",
                start_marker=start_marker,
                end_marker=end_marker,
                template_start=template_start,
                explanation=explanation
            )
            
        validation_content = validation_content_result
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', validation_content)
            if json_match:
                validation_json = json.loads(json_match.group(1))
            else:
                validation_json = json.loads(validation_content)
        except json.JSONDecodeError:
            self.logger.warning(f"Réponse non JSON de la validation pour '{extract_name}': {validation_content}")
            valid_match = re.search(r'"valid"\s*:\s*(true|false)', validation_content, re.IGNORECASE)
            reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', validation_content)
            validation_json = {
                "valid": valid_match.group(1).lower() == "true" if valid_match else False,
                "reason": reason_match.group(1) if reason_match else "Raison non disponible due à une réponse malformée."
            }

        is_valid = validation_json.get("valid", False)
        validation_reason = validation_json.get("reason", "Aucune raison de validation fournie.")

        if is_valid:
            self.logger.info(f"Extrait validé pour '{extract_name}'. Raison: {validation_reason}")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="valid",
                message=f"Extrait validé: {validation_reason}",
                start_marker=start_marker,
                end_marker=end_marker,
                template_start=template_start,
                explanation=explanation,
                extracted_text=extracted_text
            )
        else:
            self.logger.warning(f"Extrait rejeté pour '{extract_name}'. Raison: {validation_reason}")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="rejected",
                message=f"Extrait rejeté: {validation_reason}",
                start_marker=start_marker,
                end_marker=end_marker,
                template_start=template_start,
                explanation=explanation,
                extracted_text=extracted_text # Inclure le texte même si rejeté pour analyse
            )

    async def repair_extract(
        self,
        extract_definitions: List[Dict[str, Any]],
        source_idx: int,
        extract_idx: int
    ) -> ExtractResult:
        """
        Tente de réparer les marqueurs d'un extrait existant si ceux-ci sont invalides.

        Si les marqueurs actuels de l'extrait ne permettent pas une extraction valide,
        cette méthode appelle `extract_from_name` pour tenter de trouver de meilleurs
        marqueurs basés sur le nom de l'extrait.

        :param extract_definitions: La liste complète des définitions d'extraits.
        :type extract_definitions: List[Dict[str, Any]]
        :param source_idx: L'index de la source contenant l'extrait à réparer.
        :type source_idx: int
        :param extract_idx: L'index de l'extrait à réparer au sein de la source.
        :type extract_idx: int
        :return: Un objet `ExtractResult` indiquant le résultat de la tentative de réparation.
                 Si l'extrait original était déjà valide, le statut sera "valid" avec un message.
                 Si la réparation réussit, le résultat de la nouvelle extraction est retourné.
                 Si la réparation échoue, le résultat de l'échec de la nouvelle extraction est retourné.
        :rtype: ExtractResult
        """
        source_info = extract_definitions[source_idx]
        source_name = source_info.get("source_name", f"Source #{source_idx}")
        
        extracts = source_info.get("extracts", [])
        extract_info = extracts[extract_idx]
        extract_name = extract_info.get("extract_name", f"Extrait #{extract_idx}")
        
        start_marker = extract_info.get("start_marker", "")
        end_marker = extract_info.get("end_marker", "")
        template_start = extract_info.get("template_start", "")
        
        self.logger.info(f"Réparation de l'extrait '{extract_name}' de la source '{source_name}'...")
        
        source_text, url = load_source_text(source_info)
        if not source_text:
            self.logger.error(f"Impossible de charger le texte source pour '{source_name}': {url}")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="error",
                message=f"Impossible de charger le texte source: {url}"
            )
        
        extracted_text, status_msg, start_found, end_found = self.extract_text_func(
            source_text, start_marker, end_marker, template_start
        )
        
        if start_found and end_found:
            self.logger.info(f"Extrait '{extract_name}' déjà valide. Aucune correction nécessaire.")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="valid",
                message="Extrait déjà valide. Aucune correction nécessaire.",
                start_marker=start_marker,
                end_marker=end_marker,
                template_start=template_start,
                extracted_text=extracted_text
            )
        
        self.logger.info(f"Extrait '{extract_name}' invalide (start_found: {start_found}, end_found: {end_found}). Tentative d'extraction à partir du nom...")
        
        # Réutiliser la logique d'extraction principale
        new_extract_result = await self.extract_from_name(source_info, extract_name)
        
        if new_extract_result.status == "valid":
            self.logger.info(f"Réparation réussie pour l'extrait '{extract_name}' via nouvelle extraction.")
            return new_extract_result
        else:
            self.logger.warning(f"Échec de la réparation pour l'extrait '{extract_name}'. L'extraction à partir du nom a échoué avec le statut: {new_extract_result.status}")
            # Retourner le résultat de la tentative de réparation, même si c'est une erreur, pour informer l'appelant
            return new_extract_result
    
    async def update_extract_markers(
        self,
        extract_definitions: List[Dict[str, Any]],
        source_idx: int,
        extract_idx: int,
        result: ExtractResult
    ) -> bool:
        """
        Met à jour les marqueurs d'un extrait spécifique dans la liste des définitions
        avec les marqueurs d'un `ExtractResult` validé.

        Enregistre également l'action de mise à jour dans le plugin natif si disponible.

        :param extract_definitions: La liste complète des définitions d'extraits (sera modifiée en place).
        :type extract_definitions: List[Dict[str, Any]]
        :param source_idx: L'index de la source de l'extrait.
        :type source_idx: int
        :param extract_idx: L'index de l'extrait à mettre à jour.
        :type extract_idx: int
        :param result: L'objet `ExtractResult` contenant les nouveaux marqueurs validés.
        :type result: ExtractResult
        :return: True si la mise à jour a été effectuée, False si le résultat n'était pas valide
                 ou si les index étaient invalides.
        :rtype: bool
        """
        if result.status != "valid":
            self.logger.warning(f"Impossible de mettre à jour les marqueurs avec un résultat non valide: {result.status}")
            return False
        
        if not (0 <= source_idx < len(extract_definitions)):
            self.logger.error(f"Index de source invalide: {source_idx}")
            return False

        source_info = extract_definitions[source_idx]
        extracts = source_info.get("extracts", [])

        if not (0 <= extract_idx < len(extracts)):
            self.logger.error(f"Index d'extrait invalide: {extract_idx} pour la source '{source_info.get('source_name', '')}'")
            return False
            
        current_extract = extracts[extract_idx]
        old_start = current_extract.get("start_marker", "")
        old_end = current_extract.get("end_marker", "")
        old_template = current_extract.get("template_start", "")
        
        current_extract["start_marker"] = result.start_marker
        current_extract["end_marker"] = result.end_marker
        if result.template_start:
            current_extract["template_start"] = result.template_start
        elif "template_start" in current_extract and not result.template_start:
            del current_extract["template_start"] # Supprimer si vide et existait
        
        # Enregistrer les modifications dans le plugin natif (si nécessaire pour le suivi)
        # Note: self.extract_plugin n'existe plus, utiliser self.native_extract_plugin
        if self.native_extract_plugin:
            self.native_extract_plugin.extract_results.append({
                "source_name": source_info.get("source_name", f"Source #{source_idx}"),
                "extract_name": current_extract.get("extract_name", f"Extrait #{extract_idx}"),
                "action": "updated_markers",
                "old_start_marker": old_start,
                "new_start_marker": result.start_marker,
                "old_end_marker": old_end,
                "new_end_marker": result.end_marker,
                "old_template_start": old_template,
                "new_template_start": result.template_start or ""
            })
        
        self.logger.info(f"Marqueurs mis à jour pour l'extrait '{current_extract.get('extract_name', '')}' dans '{source_info.get('source_name', '')}'.")
        return True

    async def add_new_extract(
        self,
        extract_definitions: List[Dict[str, Any]],
        source_idx: int,
        extract_name: str,
        result: ExtractResult
    ) -> Tuple[bool, int]:
        """
        Ajoute un nouvel extrait à une source existante dans la liste des définitions.

        Utilise les marqueurs d'un `ExtractResult` validé pour créer le nouvel extrait.
        Enregistre également l'action d'ajout dans le plugin natif si disponible.

        :param extract_definitions: La liste complète des définitions d'extraits (sera modifiée en place).
        :type extract_definitions: List[Dict[str, Any]]
        :param source_idx: L'index de la source à laquelle ajouter l'extrait.
        :type source_idx: int
        :param extract_name: Le nom à donner au nouvel extrait.
        :type extract_name: str
        :param result: L'objet `ExtractResult` contenant les marqueurs validés pour le nouvel extrait.
        :type result: ExtractResult
        :return: Un tuple contenant un booléen indiquant le succès de l'ajout et l'index
                 du nouvel extrait (-1 en cas d'échec).
        :rtype: Tuple[bool, int]
        """
        if result.status != "valid":
            self.logger.warning(f"Impossible d'ajouter un extrait avec un résultat non valide: {result.status}")
            return False, -1
        
        if not (0 <= source_idx < len(extract_definitions)):
            self.logger.error(f"Index de source invalide: {source_idx}")
            return False, -1

        source_info = extract_definitions[source_idx]
        extracts = source_info.get("extracts", [])
            
        new_extract_data = {
            "extract_name": extract_name,
            "start_marker": result.start_marker,
            "end_marker": result.end_marker
        }
        if result.template_start:
            new_extract_data["template_start"] = result.template_start
            
        extracts.append(new_extract_data)
        new_extract_idx = len(extracts) - 1
        source_info["extracts"] = extracts # Mettre à jour la liste dans le dictionnaire source_info
            
        # Enregistrer l'ajout dans le plugin natif (si nécessaire pour le suivi)
        if self.native_extract_plugin:
            self.native_extract_plugin.extract_results.append({
                "source_name": source_info.get("source_name", f"Source #{source_idx}"),
                "extract_name": extract_name,
                "action": "added_extract",
                "start_marker": result.start_marker,
                "end_marker": result.end_marker,
                "template_start": result.template_start or ""
            })
        
        self.logger.info(f"Nouvel extrait '{extract_name}' ajouté à '{source_info.get('source_name', '')}' à l'index {new_extract_idx}.")
        return True, new_extract_idx

    async def get_response(self, message: str, **kwargs) -> str:
        """
        Méthode implémentée pour satisfaire l'interface BaseAgent.
        
        Retourne une réponse basée sur les capacités d'extraction de l'agent.
        
        :param message: Le message/texte à traiter
        :param kwargs: Arguments supplémentaires
        :return: Réponse de l'agent
        """
        # Pour un agent d'extraction, on peut retourner une description des capacités
        # ou traiter le message selon le contexte
        capabilities = self.get_agent_capabilities()
        return f"ExtractAgent '{self.name}' prêt. Capacités: {', '.join(capabilities.keys())}"

    async def invoke(self, action: str = "extract_from_name", **kwargs) -> Any:
        """
        Méthode d'invocation principale pour l'agent d'extraction.
        
        :param action: L'action à effectuer ('extract_from_name', 'repair_extract', etc.)
        :param kwargs: Arguments spécifiques à l'action
        :return: Résultat de l'action
        """
        if action == "extract_from_name":
            source_info = kwargs.get("source_info")
            extract_name = kwargs.get("extract_name")
            if source_info and extract_name:
                return await self.extract_from_name(source_info, extract_name)
            else:
                raise ValueError("extract_from_name requires 'source_info' and 'extract_name' parameters")
        
        elif action == "repair_extract":
            extract_definitions = kwargs.get("extract_definitions")
            source_idx = kwargs.get("source_idx")
            extract_idx = kwargs.get("extract_idx")
            if extract_definitions is not None and source_idx is not None and extract_idx is not None:
                return await self.repair_extract(extract_definitions, source_idx, extract_idx)
            else:
                raise ValueError("repair_extract requires 'extract_definitions', 'source_idx', and 'extract_idx' parameters")
        
        else:
            raise ValueError(f"Unknown action: {action}. Available actions: extract_from_name, repair_extract")

# La fonction setup_extract_agent n'est plus nécessaire ici,
# car l'initialisation du kernel et du service LLM se fait à l'extérieur
# et l'agent est initialisé avec un kernel existant.
# Les fonctions sémantiques sont maintenant configurées dans setup_agent_components.

# Exemple de méthodes natives qui pourraient être appelées directement ou via le kernel si enregistrées
# Ces méthodes sont maintenant dans ExtractAgentPlugin et accessibles via self.native_extract_plugin

# async def find_similar_markers_wrapper(self, text: str, marker: str, max_results: int = 5):
#     # Wrapper si on veut l'exposer comme une capacité de l'agent directement
#     if not self.native_extract_plugin:
#         self.logger.error("Plugin natif non initialisé pour find_similar_markers_wrapper.")
#         return []
#     return self.native_extract_plugin.find_similar_markers(
#         text, marker, max_results, self.find_similar_text_func
#     )

# async def search_text_dichotomically_wrapper(self, text: str, search_term: str, block_size: int = 500, overlap: int = 50):
#     if not self.native_extract_plugin:
#         self.logger.error("Plugin natif non initialisé pour search_text_dichotomically_wrapper.")
#         return []
#     return self.native_extract_plugin.search_text_dichotomically(text, search_term, block_size, overlap)

# async def extract_blocks_wrapper(self, text: str, block_size: int = 500, overlap: int = 50):
#     if not self.native_extract_plugin:
#         self.logger.error("Plugin natif non initialisé pour extract_blocks_wrapper.")
#         return []
#     return self.native_extract_plugin.extract_blocks(text, block_size, overlap)