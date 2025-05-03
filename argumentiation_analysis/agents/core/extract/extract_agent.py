"""
Agent d'extraction pour l'analyse argumentative.

Ce module implémente un agent d'extraction capable de proposer des extraits pertinents
dans un texte source en se basant sur la dénomination de l'extrait et le contexte.
"""

import os
import re
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union, Callable

import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.functions.kernel_arguments import KernelArguments

# Imports depuis les modules du projet
try:
    # Import relatif depuis le package agents/core
    from ....ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
    from ....ui.utils import load_from_cache, reconstruct_url
    from ....ui.extract_utils import (
        load_source_text, extract_text_with_markers, find_similar_text,
        load_extract_definitions_safely, save_extract_definitions_safely
    )
    from ....core.llm_service import create_llm_service
    
    # Import des définitions et prompts
    from .extract_definitions import ExtractAgentPlugin, ExtractResult
    from .prompts import (
        EXTRACT_AGENT_INSTRUCTIONS, VALIDATION_AGENT_INSTRUCTIONS,
        EXTRACT_FROM_NAME_PROMPT, VALIDATE_EXTRACT_PROMPT, REPAIR_EXTRACT_PROMPT
    )
except ImportError:
    # Fallback pour les imports absolus
    from ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
    from ui.utils import load_from_cache, reconstruct_url
    from ui.extract_utils import (
        load_source_text, extract_text_with_markers, find_similar_text,
        load_extract_definitions_safely, save_extract_definitions_safely
    )
    from core.llm_service import create_llm_service
    
    # Import des définitions et prompts (chemin absolu)
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from extract_definitions import ExtractAgentPlugin, ExtractResult
    from prompts import (
        EXTRACT_AGENT_INSTRUCTIONS, VALIDATION_AGENT_INSTRUCTIONS,
        EXTRACT_FROM_NAME_PROMPT, VALIDATE_EXTRACT_PROMPT, REPAIR_EXTRACT_PROMPT
    )

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ExtractAgent")

# Création d'un handler pour écrire les logs dans un fichier
file_handler = logging.FileHandler("extract_agent.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(file_handler)


class ExtractAgent:
    """Agent d'extraction pour l'analyse argumentative."""
    
    def __init__(
        self,
        extract_agent: ChatCompletionAgent,
        validation_agent: ChatCompletionAgent,
        extract_plugin: ExtractAgentPlugin,
        find_similar_text_func: Optional[Callable] = None,
        extract_text_func: Optional[Callable] = None
    ):
        """
        Initialise l'agent d'extraction.
        
        Args:
            extract_agent: Agent d'extraction
            validation_agent: Agent de validation
            extract_plugin: Plugin d'extraction
            find_similar_text_func: Fonction pour trouver du texte similaire
            extract_text_func: Fonction pour extraire du texte avec des marqueurs
        """
        self.extract_agent = extract_agent
        self.validation_agent = validation_agent
        self.extract_plugin = extract_plugin
        self.find_similar_text_func = find_similar_text_func or find_similar_text
        self.extract_text_func = extract_text_func or extract_text_with_markers
    
    async def extract_from_name(
        self,
        source_info: Dict[str, Any],
        extract_name: str
    ) -> ExtractResult:
        """
        Extrait un passage pertinent à partir de la dénomination de l'extrait.
        
        Args:
            source_info: Informations sur la source
            extract_name: Nom de l'extrait à extraire
            
        Returns:
            Résultat de l'extraction
        """
        source_name = source_info.get("source_name", "Source inconnue")
        
        logger.info(f"Extraction à partir du nom '{extract_name}' dans la source '{source_name}'...")
        
        # Chargement du texte source
        source_text, url = load_source_text(source_info)
        if not source_text:
            logger.error(f"Impossible de charger le texte source pour '{source_name}': {url}")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="error",
                message=f"Impossible de charger le texte source: {url}"
            )
        
        # Préparation du contexte pour l'agent d'extraction
        is_large_text = len(source_text) > 10000
        
        # Pour les textes volumineux, utiliser une approche dichotomique
        if is_large_text:
            logger.info(f"Texte volumineux détecté. Utilisation d'une approche dichotomique...")
            
            # Extraire des blocs de texte pour l'analyse
            blocks = self.extract_plugin.extract_blocks(source_text, block_size=500, overlap=50)
            
            # Rechercher des termes clés de la dénomination dans le texte
            keywords = extract_name.lower().split()
            relevant_blocks = []
            
            for keyword in keywords:
                if len(keyword) > 3:  # Ignorer les mots trop courts
                    search_results = self.extract_plugin.search_text_dichotomically(source_text, keyword)
                    for result in search_results:
                        block_idx = result["block_start"] // 450  # 500 - 50 overlap
                        if block_idx < len(blocks):
                            relevant_blocks.append(blocks[block_idx])
            
            # Préparer un résumé du texte source avec les blocs pertinents
            extract_context = f"TEXTE SOURCE VOLUMINEUX ({len(source_text)} caractères).\n\n"
            extract_context += f"Dénomination de l'extrait: {extract_name}\n\n"
            
            if relevant_blocks:
                extract_context += "BLOCS PERTINENTS TROUVÉS:\n\n"
                for i, block in enumerate(relevant_blocks[:5]):  # Limiter à 5 blocs pour éviter de surcharger l'agent
                    extract_context += f"--- BLOC {i+1} (positions {block['start_pos']}-{block['end_pos']}) ---\n"
                    extract_context += block["block"] + "\n\n"
            else:
                # Si aucun bloc pertinent n'est trouvé, fournir le début et la fin du texte
                extract_context += f"Début du texte:\n{source_text[:2500]}...\n\n"
                extract_context += f"Fin du texte:\n...{source_text[-2500:]}"
        else:
            # Pour les textes plus courts, utiliser le texte complet
            extract_context = source_text
        
        # Demander à l'agent d'extraction de proposer des bornes
        extract_prompt = EXTRACT_FROM_NAME_PROMPT.format(
            extract_name=extract_name,
            source_name=source_name,
            extract_context=extract_context
        )
        
        # Créer un message de chat pour l'agent
        chat_message = ChatMessageContent(role=AuthorRole.USER, content=extract_prompt)
        
        # Utiliser invoke() avec le message comme argument
        extract_content = ""
        try:
            # Itérer sur le générateur asynchrone retourné par invoke
            async for chunk in self.extract_agent.invoke([chat_message]):
                if hasattr(chunk, 'content') and chunk.content:
                    extract_content = chunk.content
                    break  # Prendre seulement la première réponse complète
        except Exception as e:
            logger.error(f"Erreur lors de l'invocation de l'agent d'extraction: {e}")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="error",
                message=f"Erreur lors de l'invocation de l'agent d'extraction: {str(e)}"
            )
        
        # Extraire la réponse JSON de l'agent
        try:
            # Rechercher un bloc JSON dans la réponse
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', extract_content)
            if json_match:
                extract_json = json.loads(json_match.group(1))
            else:
                # Essayer de parser directement la réponse
                extract_json = json.loads(extract_content)
        except json.JSONDecodeError:
            # Si le JSON n'est pas valide, essayer d'extraire les informations avec des regex
            start_match = re.search(r'"start_marker"\s*:\s*"([^"]*)"', extract_content)
            end_match = re.search(r'"end_marker"\s*:\s*"([^"]*)"', extract_content)
            template_match = re.search(r'"template_start"\s*:\s*"([^"]*)"', extract_content)
            explanation_match = re.search(r'"explanation"\s*:\s*"([^"]*)"', extract_content)
            
            extract_json = {
                "start_marker": start_match.group(1) if start_match else "",
                "end_marker": end_match.group(1) if end_match else "",
                "template_start": template_match.group(1) if template_match else "",
                "explanation": explanation_match.group(1) if explanation_match else "Explication non disponible"
            }
        
        # Récupérer les bornes proposées
        start_marker = extract_json.get("start_marker", "")
        end_marker = extract_json.get("end_marker", "")
        template_start = extract_json.get("template_start", "")
        explanation = extract_json.get("explanation", "Aucune explication fournie")
        
        # Vérifier que les bornes sont valides
        if not start_marker or not end_marker:
            logger.warning(f"Bornes invalides proposées pour l'extrait '{extract_name}'.")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="error",
                message="Bornes invalides proposées par l'agent.",
                explanation=explanation
            )
        
        # Extraire le texte avec les bornes proposées
        extracted_text, status, start_found, end_found = self.extract_text_func(
            source_text, start_marker, end_marker, template_start
        )
        
        # Valider l'extrait proposé
        if not start_found or not end_found:
            logger.warning(f"Bornes non trouvées dans le texte pour l'extrait '{extract_name}'.")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="error",
                message=f"Bornes non trouvées dans le texte: {status}",
                start_marker=start_marker,
                end_marker=end_marker,
                template_start=template_start,
                explanation=explanation
            )
        
        # Demander à l'agent de validation de vérifier l'extrait
        validation_prompt = VALIDATE_EXTRACT_PROMPT.format(
            extract_name=extract_name,
            source_name=source_name,
            start_marker=start_marker,
            end_marker=end_marker,
            template_start=template_start,
            extracted_text=extracted_text if extracted_text else "Aucun texte extrait",
            explanation=explanation
        )
        
        # Créer un message de chat pour l'agent
        validation_chat_message = ChatMessageContent(role=AuthorRole.USER, content=validation_prompt)
        
        # Utiliser invoke() avec le message comme argument
        validation_content = ""
        try:
            # Itérer sur le générateur asynchrone retourné par invoke
            async for chunk in self.validation_agent.invoke([validation_chat_message]):
                if hasattr(chunk, 'content') and chunk.content:
                    validation_content = chunk.content
                    break  # Prendre seulement la première réponse complète
        except Exception as e:
            logger.error(f"Erreur lors de l'invocation de l'agent de validation: {e}")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="error",
                message=f"Erreur lors de l'invocation de l'agent de validation: {str(e)}",
                start_marker=start_marker,
                end_marker=end_marker,
                template_start=template_start,
                explanation=explanation
            )
        
        # Extraire la réponse JSON de l'agent
        try:
            # Rechercher un bloc JSON dans la réponse
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', validation_content)
            if json_match:
                validation_json = json.loads(json_match.group(1))
            else:
                # Essayer de parser directement la réponse
                validation_json = json.loads(validation_content)
        except json.JSONDecodeError:
            # Si le JSON n'est pas valide, essayer d'extraire les informations avec des regex
            valid_match = re.search(r'"valid"\s*:\s*(true|false)', validation_content)
            reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', validation_content)
            
            validation_json = {
                "valid": valid_match.group(1).lower() == "true" if valid_match else False,
                "reason": reason_match.group(1) if reason_match else "Raison non disponible"
            }
        
        # Récupérer la validation
        is_valid = validation_json.get("valid", False)
        validation_reason = validation_json.get("reason", "Aucune raison fournie")
        
        # Retourner les résultats
        if is_valid:
            logger.info(f"Extrait validé pour '{extract_name}'.")
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
            logger.warning(f"Extrait rejeté pour '{extract_name}': {validation_reason}")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="rejected",
                message=f"Extrait rejeté: {validation_reason}",
                start_marker=start_marker,
                end_marker=end_marker,
                template_start=template_start,
                explanation=explanation
            )
    
    async def repair_extract(
        self,
        extract_definitions: List[Dict[str, Any]],
        source_idx: int,
        extract_idx: int
    ) -> ExtractResult:
        """
        Répare un extrait existant en utilisant sa dénomination.
        
        Args:
            extract_definitions: Liste des définitions d'extraits
            source_idx: Index de la source
            extract_idx: Index de l'extrait
            
        Returns:
            Résultat de la réparation
        """
        source_info = extract_definitions[source_idx]
        source_name = source_info.get("source_name", f"Source #{source_idx}")
        
        extracts = source_info.get("extracts", [])
        extract_info = extracts[extract_idx]
        extract_name = extract_info.get("extract_name", f"Extrait #{extract_idx}")
        
        start_marker = extract_info.get("start_marker", "")
        end_marker = extract_info.get("end_marker", "")
        template_start = extract_info.get("template_start", "")
        
        logger.info(f"Réparation de l'extrait '{extract_name}' de la source '{source_name}'...")
        
        # Chargement du texte source
        source_text, url = load_source_text(source_info)
        if not source_text:
            logger.error(f"Impossible de charger le texte source pour '{source_name}': {url}")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="error",
                message=f"Impossible de charger le texte source: {url}"
            )
        
        # Extraction du texte avec les marqueurs actuels
        extracted_text, status, start_found, end_found = self.extract_text_func(
            source_text, start_marker, end_marker, template_start
        )
        
        # Si les deux marqueurs sont trouvés, l'extrait est valide
        if start_found and end_found:
            logger.info(f"Extrait '{extract_name}' valide. Aucune correction nécessaire.")
            return ExtractResult(
                source_name=source_name,
                extract_name=extract_name,
                status="valid",
                message="Extrait valide. Aucune correction nécessaire.",
                start_marker=start_marker,
                end_marker=end_marker,
                template_start=template_start,
                extracted_text=extracted_text
            )
        
        # Si au moins un marqueur est manquant, utiliser l'extraction à partir du nom
        logger.info(f"Extrait '{extract_name}' invalide. Tentative d'extraction à partir du nom...")
        
        # Utiliser l'extraction à partir du nom
        result = await self.extract_from_name(source_info, extract_name)
        
        # Si l'extraction est valide, retourner le résultat
        if result.status == "valid":
            logger.info(f"Extraction réussie pour l'extrait '{extract_name}'.")
            return result
        else:
            logger.warning(f"Échec de l'extraction pour l'extrait '{extract_name}'.")
            return result
    
    async def update_extract_markers(
        self,
        extract_definitions: List[Dict[str, Any]],
        source_idx: int,
        extract_idx: int,
        result: ExtractResult
    ) -> bool:
        """
        Met à jour les marqueurs d'un extrait avec les résultats d'une extraction.
        
        Args:
            extract_definitions: Liste des définitions d'extraits
            source_idx: Index de la source
            extract_idx: Index de l'extrait
            result: Résultat de l'extraction
            
        Returns:
            True si la mise à jour a réussi, False sinon
        """
        if result.status != "valid":
            logger.warning(f"Impossible de mettre à jour les marqueurs avec un résultat non valide: {result.status}")
            return False
        
        if 0 <= source_idx < len(extract_definitions):
            source_info = extract_definitions[source_idx]
            extracts = source_info.get("extracts", [])
            if 0 <= extract_idx < len(extracts):
                old_start = extracts[extract_idx].get("start_marker", "")
                old_end = extracts[extract_idx].get("end_marker", "")
                old_template = extracts[extract_idx].get("template_start", "")
                
                extracts[extract_idx]["start_marker"] = result.start_marker
                extracts[extract_idx]["end_marker"] = result.end_marker
                if result.template_start:
                    extracts[extract_idx]["template_start"] = result.template_start
                elif "template_start" in extracts[extract_idx] and not result.template_start:
                    del extracts[extract_idx]["template_start"]
                
                # Enregistrer les modifications
                self.extract_plugin.extract_results.append({
                    "source_name": source_info.get("source_name", f"Source #{source_idx}"),
                    "extract_name": extracts[extract_idx].get("extract_name", f"Extrait #{extract_idx}"),
                    "old_start_marker": old_start,
                    "new_start_marker": result.start_marker,
                    "old_end_marker": old_end,
                    "new_end_marker": result.end_marker,
                    "old_template_start": old_template,
                    "new_template_start": result.template_start
                })
                
                return True
        return False
    
    async def add_new_extract(
        self,
        extract_definitions: List[Dict[str, Any]],
        source_idx: int,
        extract_name: str,
        result: ExtractResult
    ) -> Tuple[bool, int]:
        """
        Ajoute un nouvel extrait à une source existante.
        
        Args:
            extract_definitions: Liste des définitions d'extraits
            source_idx: Index de la source
            extract_name: Nom du nouvel extrait
            result: Résultat de l'extraction
            
        Returns:
            Tuple contenant (success, extract_idx)
        """
        if result.status != "valid":
            logger.warning(f"Impossible d'ajouter un extrait avec un résultat non valide: {result.status}")
            return False, -1
        
        if 0 <= source_idx < len(extract_definitions):
            source_info = extract_definitions[source_idx]
            extracts = source_info.get("extracts", [])
            
            # Créer le nouvel extrait
            new_extract = {
                "extract_name": extract_name,
                "start_marker": result.start_marker,
                "end_marker": result.end_marker
            }
            
            if result.template_start:
                new_extract["template_start"] = result.template_start
            
            # Ajouter l'extrait à la liste
            extracts.append(new_extract)
            extract_idx = len(extracts) - 1
            
            # Mettre à jour la liste des extraits dans la source
            source_info["extracts"] = extracts
            
            # Enregistrer l'ajout
            self.extract_plugin.extract_results.append({
                "source_name": source_info.get("source_name", f"Source #{source_idx}"),
                "extract_name": extract_name,
                "action": "added",
                "start_marker": result.start_marker,
                "end_marker": result.end_marker,
                "template_start": result.template_start
            })
            
            return True, extract_idx
        
        return False, -1


async def setup_extract_agent(llm_service=None):
    """
    Configure l'agent d'extraction.
    
    Args:
        llm_service: Service LLM à utiliser (si None, un nouveau service sera créé)
        
    Returns:
        Tuple contenant (kernel, extract_agent)
    """
    logger.info("Configuration de l'agent d'extraction...")
    
    # Créer le service LLM si nécessaire
    if llm_service is None:
        llm_service = create_llm_service()
        if not llm_service:
            logger.error("Impossible de créer le service LLM.")
            return None, None
    
    # Créer le kernel et les agents
    kernel = sk.Kernel()
    kernel.add_service(llm_service)
    
    prompt_exec_settings = kernel.get_prompt_execution_settings_from_service_id(llm_service.service_id)
    
    extract_agent_instance = ChatCompletionAgent(
        kernel=kernel, 
        service=llm_service, 
        name="ExtractAgent",
        instructions=EXTRACT_AGENT_INSTRUCTIONS, 
        arguments=KernelArguments(settings=prompt_exec_settings)
    )
    
    validation_agent = ChatCompletionAgent(
        kernel=kernel, 
        service=llm_service, 
        name="ValidationAgent",
        instructions=VALIDATION_AGENT_INSTRUCTIONS, 
        arguments=KernelArguments(settings=prompt_exec_settings)
    )
    
    # Créer le plugin d'extraction
    extract_plugin = ExtractAgentPlugin()
    
    # Créer l'agent d'extraction
    agent = ExtractAgent(
        extract_agent=extract_agent_instance,
        validation_agent=validation_agent,
        extract_plugin=extract_plugin,
        find_similar_text_func=find_similar_text,
        extract_text_func=extract_text_with_markers
    )
    
    logger.info("Agent d'extraction configuré.")
    return kernel, agent