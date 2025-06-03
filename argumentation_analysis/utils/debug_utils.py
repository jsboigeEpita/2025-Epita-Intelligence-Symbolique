# -*- coding: utf-8 -*-
"""
Utilitaires pour le débogage et l'inspection des données et configurations
spécifiques à l'analyse d'argumentation.
"""

import logging
import json
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def display_extract_sources_details(
    extract_sources_data: List[Dict[str, Any]],
    source_id_to_inspect: Optional[str] = None,
    show_all_french: bool = False,
    show_all: bool = False,
    output_json_path: Optional[str] = None
) -> None:
    """
    Affiche de manière structurée les détails des sources et extraits
    à partir des données déchiffrées.

    Permet de filtrer par ID de source, d'afficher toutes les sources françaises,
    ou toutes les sources. Peut également sauvegarder les données en JSON.

    Args:
        extract_sources_data (List[Dict[str, Any]]): La liste des données de sources
                                                     et extraits (typiquement déchiffrée).
        source_id_to_inspect (Optional[str]): ID de la source spécifique à inspecter.
        show_all_french (bool): Si True, affiche toutes les sources françaises et leurs extraits.
        show_all (bool): Si True, affiche toutes les sources et leurs extraits.
                         Prend le pas sur show_all_french si les deux sont True.
        output_json_path (Optional[str]): Chemin optionnel pour sauvegarder les données
                                          complètes en JSON.
    """
    if not isinstance(extract_sources_data, list):
        logger.error("Les données fournies ne sont pas une liste. Impossible d'afficher les détails.")
        return

    logger.info(f"Début de l'affichage des détails pour {len(extract_sources_data)} sources.")

    if source_id_to_inspect:
        found_source = False
        for item in extract_sources_data:
            if isinstance(item, dict) and item.get("id") == source_id_to_inspect:
                logger.info(f"\n--- Détails pour la source ID: {source_id_to_inspect} ---")
                logger.info(json.dumps(item, indent=2, ensure_ascii=False))
                if "full_text" in item:
                    logger.info(f"\n--- Full Text pour source ID: {source_id_to_inspect} ---")
                    logger.info(item["full_text"] if item["full_text"] else "[VIDE]")
                    logger.info(f"--- Fin Full Text pour source ID: {source_id_to_inspect} ---")
                else:
                    logger.info(f"Pas de champ 'full_text' pour la source ID: {source_id_to_inspect}")
                found_source = True
                break
        if not found_source:
            logger.warning(f"Source avec ID '{source_id_to_inspect}' non trouvée.")
    elif show_all or show_all_french:
        logger.info(f"\n--- Inspection de {'toutes les sources françaises (filtrées)' if show_all_french and not show_all else 'toutes les sources'} ---")
        keywords_fr = ["lemonde", "assemblee-nationale", "vie-publique", "conseil-constitutionnel", "elysee", ".fr/"]
        
        displayed_count = 0
        for i, item in enumerate(extract_sources_data):
            if not isinstance(item, dict):
                logger.warning(f"Élément {i} n'est pas un dictionnaire, ignoré.")
                continue

            source_name = item.get("source_name", "").lower()
            source_path = item.get("path", "").lower()
            source_id_val = item.get("id", f"N/A_{i}")
            host_parts = item.get("host_parts", [])
            domain_str = ".".join(host_parts).lower()

            is_french_by_keyword = any(keyword in source_name for keyword in keywords_fr) or \
                               any(keyword in source_path for keyword in keywords_fr) or \
                               any(keyword in domain_str for keyword in keywords_fr)

            if show_all or (show_all_french and is_french_by_keyword):
                displayed_count += 1
                logger.info(f"\n--- Source {i+1}/{len(extract_sources_data)} (ID: {source_id_val}, Nom: {item.get('source_name', 'N/A')}) {'[FRANÇAISE]' if is_french_by_keyword else ''} ---")
                logger.info(f"  Path: {item.get('path', 'N/A')}")
                logger.info(f"  Host Parts: {host_parts}")
                logger.info(f"  Type: {item.get('source_type', 'N/A')}, Fetch: {item.get('fetch_method', 'N/A')}")
                
                extracts = item.get("extracts", [])
                if extracts:
                    logger.info(f"  Extraits ({len(extracts)}):")
                    for j, extract in enumerate(extracts):
                        logger.info(f"    {j+1}. Nom: {extract.get('extract_name', 'N/A')}")
                        logger.info(f"       Start: {extract.get('start_marker', 'N/A')}")
                        logger.info(f"       End:   {extract.get('end_marker', 'N/A')}")
                else:
                    logger.info("  Aucun extrait défini pour cette source.")
                
                if "full_text" in item:
                    full_text_preview = item['full_text'][:200] + "..." if item['full_text'] and len(item['full_text']) > 200 else (item['full_text'] if item['full_text'] else "[VIDE]")
                    logger.info(f"  Aperçu Full Text (200 premiers caractères): {full_text_preview}")
                else:
                    logger.info("  Pas de champ 'full_text' pour cette source.")
        
        if displayed_count == 0:
            if show_all_french and not show_all:
                logger.info("Aucune source française identifiée par les mots-clés actuels.")
            else:
                logger.info("Aucune source à afficher (la liste est peut-être vide ou les filtres n'ont rien retourné).")

    else:
        # Comportement par défaut si aucun filtre spécifique: afficher les N premiers
        logger.info("Affichage des 2 premiers éléments par défaut (aucun filtre spécifique appliqué).")
        for i, item in enumerate(extract_sources_data[:2]):
            logger.info(f"\n--- Structure de l'élément {i+1} ---")
            logger.info(json.dumps(item, indent=2, ensure_ascii=False))
            if isinstance(item, dict):
                logger.info(f"Champs présents: {list(item.keys())}")
                if "full_text" in item and item["full_text"]:
                     logger.info(f"Aperçu Full Text (500 premiers caractères): {item['full_text'][:500]}")
            logger.info(f"--- Fin de la structure de l'élément {i+1} ---\n")
        if not extract_sources_data:
             logger.info("Aucune donnée de source d'extrait à afficher.")


    if output_json_path:
        from pathlib import Path as PlPath # Pour éviter conflit avec import pathlib
        output_file = PlPath(output_json_path)
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(extract_sources_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Données complètes sauvegardées dans : {output_file.resolve()}")
        except Exception as e_write:
            logger.error(f"Erreur lors de la sauvegarde du JSON dans {output_file}: {e_write}", exc_info=True)