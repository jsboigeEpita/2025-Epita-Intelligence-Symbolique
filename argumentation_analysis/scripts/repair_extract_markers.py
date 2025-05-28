#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de réparation des bornes défectueuses dans les extraits

Ce script identifie et corrige automatiquement les bornes défectueuses dans les extraits
définis dans extract_sources.json, en se concentrant particulièrement sur le corpus
de discours d'Hitler qui est volumineux.

Il utilise une approche basée sur des agents pour analyser les textes sources,
détecter les problèmes de bornes et proposer des corrections automatiques.

Fonctionnalités:
- Analyse des extraits existants pour détecter les bornes défectueuses
- Correction automatique des bornes avec des algorithmes de correspondance approximative
- Traitement spécifique pour le corpus de discours d'Hitler
- Validation et sauvegarde des corrections
- Génération d'un rapport détaillé des modifications
"""

import os
import re
import json
import logging
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RepairExtractMarkers")

# Création d'un handler pour écrire les logs dans un fichier
file_handler = logging.FileHandler("repair_extract_markers.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(file_handler)

# Imports depuis les modules du projet
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent, AuthorRole # Peut-être plus nécessaire ici si setup_agents est déplacé
from semantic_kernel.agents import ChatCompletionAgent # Peut-être plus nécessaire ici
from semantic_kernel.functions.kernel_arguments import KernelArguments # Peut-être plus nécessaire ici

# Imports des services et modèles
from ..models.extract_definition import ExtractDefinitions, SourceDefinition, Extract
# from ..models.extract_result import ExtractResult # Non utilisé directement dans ce fichier après refactor
from ..services.cache_service import CacheService
from ..services.crypto_service import CryptoService
from ..services.definition_service import DefinitionService
from ..services.extract_service import ExtractService
from ..services.fetch_service import FetchService
from ..core.llm_service import create_llm_service

# Import de la logique métier déplacée
from ..utils.extract_repair.marker_repair_logic import (
    ExtractRepairPlugin,
    REPAIR_AGENT_INSTRUCTIONS,
    VALIDATION_AGENT_INSTRUCTIONS,
    generate_report as generate_marker_repair_report # Renommer pour clarté
)


async def setup_agents(llm_service, kernel_instance): # kernel_instance est maintenant passé en argument
    """
    Configure les agents de réparation et de validation.
    
    Args:
        llm_service: Service LLM
        
    Returns:
        Tuple contenant (kernel, repair_agent, validation_agent)
    """
    logger.info("Configuration des agents...")
    
    # kernel = sk.Kernel() # Le kernel est maintenant créé dans main et passé ici
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
    return repair_agent, validation_agent # Ne retourne plus le kernel


async def repair_extract_markers(
    extract_definitions: ExtractDefinitions,
    llm_service,
    fetch_service: FetchService,
    extract_service: ExtractService
) -> Tuple[ExtractDefinitions, List[Dict[str, Any]]]:
    """
    Répare les bornes défectueuses dans les extraits.
    
    Args:
        extract_definitions: Définitions d'extraits
        llm_service: Service LLM
        fetch_service: Service de récupération
        extract_service: Service d'extraction
        
    Returns:
        Tuple contenant (extract_definitions, results)
    """
    logger.info("Initialisation de la réparation des bornes défectueuses...")
    
    # Créer le plugin de réparation
    repair_plugin = ExtractRepairPlugin(extract_service)
    
    # Liste pour stocker les résultats
    results = []
    
    # Parcourir toutes les sources et leurs extraits
    for source_idx, source_info in enumerate(extract_definitions.sources):
        source_name = source_info.source_name
        logger.info(f"Analyse de la source '{source_name}'...")
        
        extracts = source_info.extracts
        for extract_idx, extract_info in enumerate(extracts):
            extract_name = extract_info.extract_name
            start_marker = extract_info.start_marker
            end_marker = extract_info.end_marker
            template_start = extract_info.template_start
            
            logger.info(f"Analyse de l'extrait '{extract_name}'...")
            logger.debug(f"  - start_marker: '{start_marker}'")
            logger.debug(f"  - end_marker: '{end_marker}'")
            logger.debug(f"  - template_start: '{template_start}'")
            
            # Vérifier si l'extrait a un template_start
            if template_start and "{0}" in template_start:
                # Extraire la lettre du template
                first_letter = template_start.replace("{0}", "")
                
                # Vérifier si le start_marker ne commence pas déjà par cette lettre
                if start_marker and not start_marker.startswith(first_letter):
                    # Corriger le start_marker en ajoutant la première lettre
                    old_marker = start_marker
                    new_marker = first_letter + start_marker
                    
                    logger.info(f"Correction de l'extrait '{extract_name}':")
                    logger.info(f"  - Ancien marqueur: '{old_marker}'")
                    logger.info(f"  - Nouveau marqueur: '{new_marker}'")
                    
                    # Mettre à jour le marqueur
                    repair_plugin.update_extract_markers(
                        extract_definitions, source_idx, extract_idx,
                        new_marker, end_marker, template_start
                    )
                    
                    # Ajouter le résultat
                    results.append({
                        "source_name": source_name,
                        "extract_name": extract_name,
                        "status": "repaired",
                        "message": f"Marqueur de début corrigé: '{old_marker}' -> '{new_marker}'",
                        "old_start_marker": old_marker,
                        "new_start_marker": new_marker,
                        "old_end_marker": end_marker,
                        "new_end_marker": end_marker,
                        "old_template_start": template_start,
                        "new_template_start": template_start,
                        "explanation": f"Première lettre manquante ajoutée selon le template '{template_start}'"
                    })
                else:
                    logger.info(f"Extrait '{extract_name}' valide. Aucune correction nécessaire.")
                    results.append({
                        "source_name": source_name,
                        "extract_name": extract_name,
                        "status": "valid",
                        "message": "Extrait valide. Aucune correction nécessaire."
                    })
            else:
                # Pour les extraits sans template_start, on pourrait utiliser l'agent
                # mais pour simplifier, on les considère comme valides
                logger.info(f"Extrait '{extract_name}' sans template_start. Aucune correction nécessaire.")
                results.append({
                    "source_name": source_name,
                    "extract_name": extract_name,
                    "status": "valid",
                    "message": "Extrait sans template_start. Aucune correction nécessaire."
                })
    
    # Récupérer les modifications effectuées
    repair_results = repair_plugin.get_repair_results()
    logger.info(f"{len(repair_results)} extraits corrigés.")
    
    return extract_definitions, results


# La fonction generate_report a été déplacée vers marker_repair_logic.py
# Elle est importée sous le nom generate_marker_repair_report


async def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Réparation des bornes défectueuses dans les extraits")
    parser.add_argument("--output", "-o", default="repair_report.html", help="Fichier de sortie pour le rapport HTML")
    parser.add_argument("--save", "-s", action="store_true", help="Sauvegarder les modifications")
    parser.add_argument("--hitler-only", action="store_true", help="Traiter uniquement le corpus de discours d'Hitler")
    parser.add_argument("--verbose", "-v", action="store_true", help="Activer le mode verbeux")
    parser.add_argument("--input", "-i", default=None, help="Fichier d'entrée personnalisé")
    parser.add_argument("--output-json", default="extract_sources_updated.json", help="Fichier de sortie JSON pour vérification")
    args = parser.parse_args()
    
    # Configurer le niveau de journalisation
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé.")
    
    logger.info("Démarrage du script de réparation des bornes défectueuses...")
    logger.info(f"Répertoire de travail actuel: {os.getcwd()}")
    logger.info(f"Chemin du script: {os.path.abspath(__file__)}")
    
    # Initialiser les services
    try:
        # Créer le service LLM
        llm_service = create_llm_service()
        if not llm_service:
            logger.error("Impossible de créer le service LLM.")
            return

        # Créer une instance du Kernel ici
        kernel = sk.Kernel()
        
        # Configurer les agents en passant le kernel
        # repair_agent, validation_agent = await setup_agents(llm_service, kernel) # Décommenter si setup_agents est utilisé ici
        # Note: setup_agents n'est pas directement appelé par repair_extract_markers,
        # mais par une logique d'agent qui serait dans marker_repair_logic.py si on suivait ce pattern.
        # Pour l'instant, repair_extract_markers ne semble pas utiliser les agents directement.

        # Créer le service de cache
        cache_dir = Path("./text_cache")
        cache_service = CacheService(cache_dir)
        
        # Créer le service de chiffrement
        from ..ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
        crypto_service = CryptoService(ENCRYPTION_KEY)
        
        # Créer le service d'extraction
        extract_service = ExtractService()
        
        # Créer le service de récupération
        temp_download_dir = Path("./temp_downloads")
        fetch_service = FetchService(
            cache_service=cache_service,
            temp_download_dir=temp_download_dir
        )
        
        # Créer le service de définition
        input_file = Path(args.input) if args.input else Path(CONFIG_FILE)
        fallback_file = Path(CONFIG_FILE_JSON) if Path(CONFIG_FILE_JSON).exists() else None
        definition_service = DefinitionService(
            crypto_service=crypto_service,
            config_file=input_file,
            fallback_file=fallback_file
        )
        
        # Charger les définitions d'extraits
        extract_definitions, error_message = definition_service.load_definitions()
        if error_message:
            logger.warning(f"Avertissement lors du chargement des définitions: {error_message}")
        
        logger.info(f"{len(extract_definitions.sources)} sources chargées.")
        
        # Filtrer les sources si l'option --hitler-only est activée
        if args.hitler_only:
            original_count = len(extract_definitions.sources)
            extract_definitions.sources = [
                source for source in extract_definitions.sources
                if "hitler" in source.source_name.lower()
            ]
            logger.info(f"Filtrage des sources: {len(extract_definitions.sources)}/{original_count} sources retenues (corpus Hitler).")
        
        # Réparer les bornes défectueuses
        logger.info("Démarrage de la réparation des bornes défectueuses...")
        updated_definitions, results = await repair_extract_markers(
            extract_definitions, llm_service, fetch_service, extract_service
        )
        logger.info(f"Réparation terminée. {len(results)} résultats obtenus.")
        
        # Générer le rapport
        logger.info(f"Génération du rapport dans {args.output}...")
        generate_marker_repair_report(results, args.output) # Utiliser la fonction importée
        logger.info(f"Rapport généré dans {args.output}")
        
        # Sauvegarder les modifications si demandé
        if args.save:
            logger.info(f"Sauvegarde des modifications...")
            success, error_message = definition_service.save_definitions(updated_definitions)
            if success:
                logger.info("✅ Modifications sauvegardées avec succès.")
            else:
                logger.error(f"❌ Erreur lors de la sauvegarde: {error_message}")
        
        # Exporter les définitions mises à jour au format JSON pour vérification
        if args.output_json:
            logger.info(f"Exportation des définitions mises à jour dans {args.output_json}...")
            success, message = definition_service.export_definitions_to_json(
                updated_definitions, Path(args.output_json)
            )
            logger.info(message)
    
    except Exception as e:
        logger.error(f"Exception non gérée: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(main())