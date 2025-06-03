# -*- coding: utf-8 -*-
"""
Utilitaires pour aider à la correction manuelle des données,
notamment pour les marqueurs d'extraits.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional # Ajout de Optional

logger = logging.getLogger(__name__)

def prepare_manual_correction_data(
    config_file_path: Path,
    target_source_id: str,
    target_extract_name: str,
    output_debug_file_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    Prépare et retourne les données nécessaires pour la correction manuelle d'un extrait spécifique.
    Optionnellement, écrit ces informations dans un fichier de débogage.

    Args:
        config_file_path (Path): Chemin vers le fichier de configuration JSON des sources.
        target_source_id (str): ID de la source contenant l'extrait.
        target_extract_name (str): Nom de l'extrait à corriger.
        output_debug_file_path (Optional[Path]): Chemin optionnel vers un fichier
                                                 où sauvegarder les informations de débogage.

    Returns:
        Optional[Dict[str, Any]]: Un dictionnaire contenant les informations de l'extrait
                                  (source_id, source_name, extract_name, current_start_marker,
                                  current_end_marker, source_full_text), ou None si l'extrait
                                  ou la source ne sont pas trouvés, ou en cas d'erreur de lecture.
    """
    logger.info(f"Préparation des données de correction manuelle pour source '{target_source_id}', extrait '{target_extract_name}'.")
    logger.debug(f"Chargement de la configuration depuis : {config_file_path}")

    if not config_file_path.exists() or not config_file_path.is_file():
        logger.error(f"Le fichier de configuration '{config_file_path}' n'existe pas ou n'est pas un fichier.")
        return None

    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            sources_data = json.load(f)
    except json.JSONDecodeError as e_json:
        logger.error(f"Impossible de décoder le JSON depuis '{config_file_path}': {e_json}", exc_info=True)
        return None
    except Exception as e_read:
        logger.error(f"Erreur de lecture du fichier '{config_file_path}': {e_read}", exc_info=True)
        return None

    if not isinstance(sources_data, list):
        logger.error(f"La structure racine du JSON dans '{config_file_path}' n'est pas une liste.")
        return None

    found_source_dict: Optional[Dict[str, Any]] = None
    for source in sources_data:
        if isinstance(source, dict) and source.get("id") == target_source_id:
            found_source_dict = source
            break
    
    if not found_source_dict:
        logger.error(f"Source ID '{target_source_id}' non trouvée.")
        available_ids = [s.get('id', 'ID_MANQUANT') for s in sources_data if isinstance(s, dict)]
        logger.info(f"IDs de source disponibles: {available_ids}")
        return None

    found_extract_dict: Optional[Dict[str, Any]] = None
    extracts_list = found_source_dict.get("extracts", [])
    if not isinstance(extracts_list, list):
        logger.error(f"Le champ 'extracts' pour la source ID '{target_source_id}' n'est pas une liste.")
        return None

    for extract in extracts_list:
        if isinstance(extract, dict) and extract.get("extract_name") == target_extract_name:
            found_extract_dict = extract
            break

    if not found_extract_dict:
        logger.error(f"Extrait nom '{target_extract_name}' non trouvé dans la source ID '{target_source_id}'.")
        available_extract_names = [e.get('extract_name', 'NOM_MANQUANT') for e in extracts_list if isinstance(e, dict)]
        logger.info(f"Noms d'extraits disponibles pour la source '{target_source_id}': {available_extract_names}")
        return None

    source_name = found_source_dict.get("source_name", "NomSourceInconnu")
    current_start_marker = found_extract_dict.get("start_marker", "N/A")
    current_end_marker = found_extract_dict.get("end_marker", "N/A")
    source_full_text = found_source_dict.get("full_text")

    correction_info: Dict[str, Any] = {
        "target_source_id": target_source_id,
        "source_name": source_name,
        "target_extract_name": target_extract_name,
        "current_start_marker": current_start_marker,
        "current_end_marker": current_end_marker,
        "source_full_text": source_full_text # Peut être None
    }

    if output_debug_file_path:
        debug_report_lines = [
            f"--- Informations pour Correction Manuelle ---",
            f"Source ID         : {target_source_id}",
            f"Nom de la Source  : {source_name}",
            f"Nom de l'Extrait  : {target_extract_name}",
            f"Marqueur Début Actuel : {repr(current_start_marker)}",
            f"Marqueur Fin Actuel   : {repr(current_end_marker)}"
        ]
        if source_full_text:
            debug_report_lines.append(f"Full_text de la source (longueur: {len(source_full_text)} caractères) :\n--- DEBUT FULL TEXT ---")
            debug_report_lines.append(source_full_text)
            debug_report_lines.append("--- FIN FULL TEXT ---")
        else:
            debug_report_lines.append("ATTENTION: Full_text de la source est ABSENT ou VIDE.")
        
        try:
            output_debug_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_debug_file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(debug_report_lines))
            logger.info(f"Les informations de débogage pour correction ont été écrites dans : {output_debug_file_path.resolve()}")
        except Exception as e_write_debug:
            logger.error(f"Impossible d'écrire le fichier de débogage '{output_debug_file_path}': {e_write_debug}", exc_info=True)
            
    if not source_full_text:
         logger.warning(f"Le full_text pour la source {target_source_id} est manquant. La correction manuelle des marqueurs sera difficile.")
         
    return correction_info