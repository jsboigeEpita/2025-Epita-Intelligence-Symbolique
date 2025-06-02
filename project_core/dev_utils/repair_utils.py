# -*- coding: utf-8 -*-
"""
Utilitaires pour la réparation et la maintenance des données d'extraits.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple # Ajout des types nécessaires

# Imports pour les fonctions déplacées
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.functions.kernel_arguments import KernelArguments

from argumentation_analysis.models import ExtractDefinitions, SourceDefinition, Extract # Ajustement du chemin
from argumentation_analysis.core.llm_service import create_llm_service # Conservé pour le pipeline
from project_core.service_setup.core_services import initialize_core_services # Conservé pour le pipeline

# Services passés en argument à repair_extract_markers, pas besoin d'importer FetchService/ExtractService ici
# from argumentation_analysis.services.fetch_service import FetchService
# from argumentation_analysis.services.extract_service import ExtractService

from argumentation_analysis.utils.extract_repair.marker_repair_logic import (
    ExtractRepairPlugin,
    REPAIR_AGENT_INSTRUCTIONS, # Pour setup_agents
    VALIDATION_AGENT_INSTRUCTIONS, # Pour setup_agents
    generate_report as generate_marker_repair_report # Renommé pour clarté
)


logger = logging.getLogger(__name__)

# --- Fonctions déplacées depuis argumentation_analysis/scripts/repair_extract_markers.py ---

async def setup_agents(llm_service, kernel_instance: sk.Kernel) -> Tuple[ChatCompletionAgent, ChatCompletionAgent]:
    """
    Configure les agents de réparation et de validation.
    
    Args:
        llm_service: Service LLM.
        kernel_instance: Instance du Kernel Semantic Kernel.
        
    Returns:
        Tuple contenant (repair_agent, validation_agent).
    """
    logger.info("Configuration des agents...")
    
    kernel_instance.add_service(llm_service)
    
    try:
        prompt_exec_settings = kernel_instance.get_prompt_execution_settings_from_service_id(llm_service.service_id)
        logger.info("Paramètres d'exécution de prompt obtenus")
    except Exception as e:
        logger.warning(f"Erreur lors de l'obtention des paramètres d'exécution de prompt: {e}")
        logger.info("Utilisation de paramètres d'exécution de prompt vides")
        prompt_exec_settings = {} # type: ignore
    
    try:
        repair_agent = ChatCompletionAgent(
            kernel=kernel_instance,
            service=llm_service,
            name="RepairAgent",
            instructions=REPAIR_AGENT_INSTRUCTIONS,
            arguments=KernelArguments(settings=prompt_exec_settings)
        )
        logger.info("Agent de réparation créé")
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'agent de réparation: {e}")
        raise
    
    try:
        validation_agent = ChatCompletionAgent(
            kernel=kernel_instance,
            service=llm_service,
            name="ValidationAgent",
            instructions=VALIDATION_AGENT_INSTRUCTIONS,
            arguments=KernelArguments(settings=prompt_exec_settings)
        )
        logger.info("Agent de validation créé")
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'agent de validation: {e}")
        raise
    
    logger.info("Agents configurés.")
    return repair_agent, validation_agent


async def repair_extract_markers(
    extract_definitions: ExtractDefinitions,
    llm_service: Any, # Type Any car create_llm_service peut retourner None, et le type exact de llm_service peut varier
    fetch_service: Any, # Type Any pour FetchService mockable/réel
    extract_service: Any # Type Any pour ExtractService mockable/réel
) -> Tuple[ExtractDefinitions, List[Dict[str, Any]]]:
    """
    Répare les bornes défectueuses dans les extraits.
    (Fonction déplacée depuis argumentation_analysis/scripts/repair_extract_markers.py)
    """
    logger.info("Initialisation de la réparation des bornes défectueuses (dans repair_utils)...")
    
    repair_plugin = ExtractRepairPlugin(extract_service)
    results: List[Dict[str, Any]] = []
    
    for source_idx, source_info in enumerate(extract_definitions.sources):
        source_name = source_info.source_name
        logger.info(f"Analyse de la source '{source_name}'...")
        
        for extract_idx, extract_info in enumerate(source_info.extracts):
            extract_name = extract_info.extract_name
            start_marker = extract_info.start_marker
            end_marker = extract_info.end_marker
            template_start = extract_info.template_start
            
            logger.debug(f"Analyse de l'extrait '{extract_name}'...")
            logger.debug(f"  - start_marker: '{start_marker}'")
            logger.debug(f"  - end_marker: '{end_marker}'")
            logger.debug(f"  - template_start: '{template_start}'")
            
            current_status = "valid"
            message = "Extrait valide. Aucune correction nécessaire."
            old_start = start_marker
            new_start = start_marker

            if template_start and "{0}" in template_start:
                first_letter = template_start.replace("{0}", "")
                if start_marker and not start_marker.startswith(first_letter):
                    old_start = start_marker
                    new_start = first_letter + start_marker
                    logger.info(f"Correction de l'extrait '{extract_name}': '{old_start}' -> '{new_start}'")
                    
                    # La mise à jour de extract_definitions se fait via l'instance de ExtractRepairPlugin
                    # qui modifie l'objet extract_definitions passé par référence.
                    # Ou, si ExtractDefinitions est immuable, repair_plugin devrait retourner la nouvelle instance.
                    # En supposant que ExtractRepairPlugin modifie l'objet en place :
                    source_info.extracts[extract_idx].start_marker = new_start # Modification directe
                    
                    current_status = "repaired"
                    message = f"Marqueur de début corrigé: '{old_start}' -> '{new_start}'"
            elif not template_start:
                 message = "Extrait sans template_start. Aucune correction basée sur template appliquée."


            results.append({
                "source_name": source_name,
                "extract_name": extract_name,
                "status": current_status,
                "message": message,
                "old_start_marker": old_start, # old_start et non start_marker pour refléter la valeur avant modif
                "new_start_marker": new_start,
                "old_end_marker": end_marker, # end_marker n'est pas modifié dans cette logique
                "new_end_marker": end_marker,
                "old_template_start": template_start, # template_start n'est pas modifié
                "new_template_start": template_start,
                "explanation": (f"Première lettre manquante ajoutée selon le template '{template_start}'" 
                                if current_status == "repaired" else "Aucune correction appliquée.")
            })
            
    # La logique de repair_plugin.get_repair_results() n'est plus nécessaire si on modifie directement
    # et qu'on construit les `results` au fur et à mesure.
    # Si ExtractRepairPlugin était responsable de stocker les changements, alors on l'utiliserait.
    # Pour ce refactoring, on assume que la modification directe de extract_definitions.sources[...].extracts[...].start_marker
    # est suffisante et que `results` capture les détails.
    logger.info(f"{sum(1 for r in results if r['status'] == 'repaired')} extraits corrigés (logique simplifiée).")
    return extract_definitions, results


# --- Pipeline (précédemment défini ici) ---

async def run_extract_repair_pipeline(
    project_root_dir: Path,
    output_report_path_str: str,
    save_changes: bool,
    hitler_only: bool,
    custom_input_path_str: Optional[str],
    output_json_path_str: Optional[str]
):
    """
    Exécute le pipeline de réparation des bornes d'extraits.
    """
    logger.info("Démarrage du pipeline de réparation des bornes défectueuses...")
    logger.info(f"Racine du projet utilisée pour le pipeline: {project_root_dir}")

    try:
        llm_service = create_llm_service()
        if not llm_service:
            logger.error("Impossible de créer le service LLM dans le pipeline.")
            return

        config_file_to_use = Path(custom_input_path_str) if custom_input_path_str else None
        
        core_services = initialize_core_services(
            project_root_dir=project_root_dir,
            config_file_path=config_file_to_use
        )
        
        extract_service = core_services["extract_service"]
        fetch_service = core_services["fetch_service"]
        definition_service = core_services["definition_service"]
        
        extract_definitions, error_message = definition_service.load_definitions()
        if error_message:
            logger.warning(f"Avertissement lors du chargement des définitions (pipeline): {error_message}")
        
        if not extract_definitions or not extract_definitions.sources:
            logger.error("Aucune définition d'extrait chargée ou sources vides. Arrêt du pipeline.")
            return

        logger.info(f"{len(extract_definitions.sources)} sources chargées dans le pipeline.")
        
        if hitler_only:
            original_count = len(extract_definitions.sources)
            extract_definitions.sources = [
                source for source in extract_definitions.sources
                if "hitler" in source.source_name.lower()
            ]
            logger.info(f"Filtrage des sources (pipeline): {len(extract_definitions.sources)}/{original_count} sources retenues.")

        if not extract_definitions.sources:
            logger.warning("Aucune source restante après filtrage. Arrêt du pipeline de réparation.")
            return

        logger.info("Démarrage de la réparation des bornes (pipeline)...")
        # Appel à la fonction repair_extract_markers maintenant locale à ce module
        updated_definitions, results = await repair_extract_markers(
            extract_definitions, llm_service, fetch_service, extract_service
        )
        logger.info(f"Réparation terminée (pipeline). {len(results)} résultats obtenus.")
        
        output_report_file = Path(output_report_path_str)
        output_report_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Génération du rapport dans {output_report_file} (pipeline)...")
        # Utiliser generate_marker_repair_report importé depuis marker_repair_logic
        generate_marker_repair_report(results, str(output_report_file))
        logger.info(f"Rapport généré dans {output_report_file} (pipeline)")
        
        if save_changes:
            logger.info("Sauvegarde des modifications (pipeline)...")
            success, error_msg_save = definition_service.save_definitions(updated_definitions)
            if success:
                logger.info("✅ Modifications sauvegardées avec succès (pipeline).")
            else:
                logger.error(f"❌ Erreur lors de la sauvegarde (pipeline): {error_msg_save}")
        
        if output_json_path_str:
            output_json_file = Path(output_json_path_str)
            output_json_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Exportation des définitions JSON mises à jour vers {output_json_file} (pipeline)...")
            success_export, msg_export = definition_service.export_definitions_to_json(
                updated_definitions, output_json_file
            )
            logger.info(msg_export)

    except Exception as e:
        logger.error(f"Exception non gérée dans le pipeline de réparation: {e}", exc_info=True)