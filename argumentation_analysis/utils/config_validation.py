# -*- coding: utf-8 -*-
"""
Utilitaires pour la validation de la configuration des extraits et sources
d'analyse d'argumentation.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple  # Ajout de Tuple pour le type de retour

logger = logging.getLogger(__name__)


def identify_missing_full_text_segments(
    config_file_path: Path,
) -> Tuple[int, int, List[Dict[str, Any]]]:
    """
    Identifie les extraits dans un fichier de configuration JSON qui n'ont pas
    de champ 'full_text_segment' ou dont ce champ est vide.

    Args:
        config_file_path (Path): Chemin vers le fichier de configuration JSON.
                                 Le JSON doit être une liste de sources, chaque source
                                 contenant une liste d'extraits.

    Returns:
        Tuple[int, int, List[Dict[str, Any]]]: Un tuple contenant:
            - Le nombre total d'extraits avec 'full_text_segment' manquant ou vide.
            - Le nombre total d'extraits analysés.
            - Une liste de dictionnaires, chaque dictionnaire détaillant un extrait manquant
              (incluant source_id, source_name, extract_name, start_marker, end_marker,
               et si le full_text de la source est présent).
    """
    logger.info(
        f"Analyse du fichier de configuration pour les segments manquants: {config_file_path}"
    )

    if not config_file_path.exists() or not config_file_path.is_file():
        logger.error(
            f"Le fichier de configuration '{config_file_path}' n'existe pas ou n'est pas un fichier."
        )
        return 0, 0, []

    try:
        with open(config_file_path, "r", encoding="utf-8") as f:
            sources_data = json.load(f)
    except json.JSONDecodeError as e_json:
        logger.error(
            f"Impossible de décoder le JSON depuis '{config_file_path}': {e_json}",
            exc_info=True,
        )
        return 0, 0, []
    except Exception as e_read:
        logger.error(
            f"Erreur de lecture du fichier '{config_file_path}': {e_read}",
            exc_info=True,
        )
        return 0, 0, []

    if not isinstance(sources_data, list):
        logger.error(
            f"La structure racine du JSON dans '{config_file_path}' n'est pas une liste."
        )
        return 0, 0, []

    missing_segments_details: List[Dict[str, Any]] = []
    missing_segments_count = 0
    total_extracts_count = 0

    logger.info("--- Rapport des Segments d'Extraits Manquants ou Vides ---")
    for i, source in enumerate(sources_data):
        if not isinstance(source, dict):
            logger.warning(f"Source à l'index {i} n'est pas un dictionnaire, ignorée.")
            continue

        source_id = source.get("id", f"SourceInconnue_{i+1}")
        source_name = source.get("source_name", "NomSourceInconnu")
        extracts = source.get("extracts", [])

        if not isinstance(extracts, list):
            logger.warning(
                f"La source '{source_name}' (ID: {source_id}) a un champ 'extracts' qui n'est pas une liste. Ignorée."
            )
            continue

        for j, extract in enumerate(extracts):
            total_extracts_count += 1
            if not isinstance(extract, dict):
                logger.warning(
                    f"Extrait {j+1} de la source '{source_name}' n'est pas un dictionnaire, ignoré."
                )
                continue

            extract_name = extract.get("extract_name", f"ExtraitInconnu_{j+1}")
            segment = extract.get("full_text_segment")

            if segment is None or segment == "":
                missing_segments_count += 1
                start_marker = extract.get("start_marker", "N/A")
                end_marker = extract.get("end_marker", "N/A")
                has_full_text_in_source = (
                    "PRÉSENT" if source.get("full_text") else "ABSENT"
                )

                detail = {
                    "source_id": source_id,
                    "source_name": source_name,
                    "extract_name": extract_name,
                    "start_marker": start_marker,
                    "end_marker": end_marker,
                    "source_has_full_text": has_full_text_in_source,
                }
                missing_segments_details.append(detail)

                logger.info(f"  - Source: '{source_name}' (ID: {source_id})")
                logger.info(f"    Extrait: '{extract_name}' - SEGMENT MANQUANT/VIDE")
                logger.info(f"      Marqueur Début: {repr(start_marker)}")
                logger.info(f"      Marqueur Fin: {repr(end_marker)}")
                logger.info(f"      Full_text de la source: {has_full_text_in_source}")

    logger.info("\n--- Résumé de l'identification des segments manquants ---")
    if missing_segments_count == 0:
        logger.info("Tous les extraits ont un segment 'full_text_segment' renseigné.")
    else:
        logger.info(
            f"Nombre total d'extraits avec segment manquant ou vide : {missing_segments_count}"
        )
    logger.info(f"Nombre total d'extraits analysés : {total_extracts_count}")

    return missing_segments_count, total_extracts_count, missing_segments_details
