# -*- coding: utf-8 -*-
"""
Utilitaires pour la génération de rapports et de résumés spécifiques
à l'analyse d'argumentation.
"""

import logging
from typing import List, Dict, Any, Optional # Ajout d'Optional

logger = logging.getLogger(__name__)

def summarize_extract_definitions(extract_definitions: List[Dict[str, Any]], max_marker_len: int = 50) -> None:
    """
    Affiche via le logger un résumé des sources et extraits disponibles
    à partir des définitions d'extraits.

    Args:
        extract_definitions (List[Dict[str, Any]]): Une liste de dictionnaires,
            où chaque dictionnaire représente une source et contient des informations
            sur la source et une liste de ses extraits.
        max_marker_len (int): Longueur maximale pour l'affichage des marqueurs.
    """
    if not extract_definitions:
        logger.warning("Aucune définition d'extrait fournie pour le résumé.")
        return
    
    logger.info(f"--- Résumé des Définitions d'Extraits ---")
    logger.info(f"Nombre total de sources: {len(extract_definitions)}")
    
    total_extracts_count = 0
    for i, source_def in enumerate(extract_definitions, 1):
        if not isinstance(source_def, dict):
            logger.warning(f"Source {i} n'est pas un dictionnaire, ignorée.")
            continue

        source_name = source_def.get("source_name", "Source Inconnue")
        source_type = source_def.get("source_type", "Type Inconnu")
        source_url = source_def.get("source_url", source_def.get("path", "URL/Path Inconnu")) # Utiliser path comme fallback
        extracts_list = source_def.get("extracts", [])
        
        logger.info(f"\nSource {i}: {source_name}")
        logger.info(f"  Type: {source_type}")
        logger.info(f"  URL/Path: {source_url}")
        
        if not isinstance(extracts_list, list):
            logger.warning(f"  Les extraits pour la source '{source_name}' ne sont pas une liste, ignorés.")
            extracts_list = [] # Traiter comme vide pour éviter erreur plus loin

        logger.info(f"  Nombre d'extraits: {len(extracts_list)}")
        
        for j, extract_def in enumerate(extracts_list, 1):
            if not isinstance(extract_def, dict):
                logger.warning(f"    Extrait {j} pour la source '{source_name}' n'est pas un dictionnaire, ignoré.")
                continue

            extract_name = extract_def.get("extract_name", "Extrait Inconnu")
            start_marker = extract_def.get("start_marker", "")
            end_marker = extract_def.get("end_marker", "")
            
            # Tronquer les marqueurs s'ils sont trop longs pour l'affichage
            display_start_marker = start_marker[:max_marker_len] + "..." if len(start_marker) > max_marker_len else start_marker
            display_end_marker = end_marker[:max_marker_len] + "..." if len(end_marker) > max_marker_len else end_marker
            
            logger.info(f"    Extrait {j}: {extract_name}")
            logger.info(f"      Début: '{display_start_marker}'")
            logger.info(f"      Fin:   '{display_end_marker}'")
        
        total_extracts_count += len(extracts_list)
    
    logger.info(f"\nNombre total d'extraits sur toutes les sources: {total_extracts_count}")
    logger.info(f"--- Fin du Résumé des Définitions d'Extraits ---")

# D'autres fonctions de reporting spécifiques à l'analyse d'argumentation pourraient être ajoutées ici.
# Par exemple, formater des résultats d'analyse spécifiques, etc.