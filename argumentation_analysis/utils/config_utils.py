# -*- coding: utf-8 -*-
"""
Utilitaires pour la manipulation et l'inspection des fichiers de configuration
spécifiques à l'analyse d'argumentation (par exemple, extract_sources.json).
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Union, Tuple # Ajout de Set, Union, et Tuple

logger = logging.getLogger(__name__)

def find_sources_in_config_by_ids(
    config_data: Union[List[Dict[str, Any]], Dict[str, Any]],
    ids_to_find: List[str]
) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """
    Recherche et retourne les configurations de sources spécifiques par leurs IDs
    à partir d'une structure de configuration JSON chargée (liste ou dictionnaire).

    Args:
        config_data (Union[List[Dict[str, Any]], Dict[str, Any]]): 
            Les données de configuration chargées (peut être une liste de sources
            ou un dictionnaire contenant potentiellement une liste de sources).
        ids_to_find (List[str]): Une liste d'IDs de source à rechercher.

    Returns:
        Tuple[List[Dict[str, Any]], Set[str]]: 
            Un tuple contenant:
            - Une liste des dictionnaires de configuration des sources trouvées.
            - Un ensemble des IDs qui ont été effectivement trouvés.
    """
    found_sources_list: List[Dict[str, Any]] = []
    found_ids_set: Set[str] = set()
    
    if not ids_to_find:
        logger.debug("Aucun ID fourni pour la recherche.")
        return [], set()

    ids_to_inspect_set = set(ids_to_find) # Pour une recherche plus efficace

    def process_source_item(source_item: Any) -> None:
        if isinstance(source_item, dict):
            source_id = source_item.get("id")
            if source_id in ids_to_inspect_set and source_id not in found_ids_set:
                logger.info(f"Source trouvée par ID: {source_id}")
                found_sources_list.append(source_item)
                found_ids_set.add(source_id)

    if isinstance(config_data, list):
        logger.debug("Configuration fournie sous forme de liste. Itération directe.")
        for item in config_data:
            process_source_item(item)
    elif isinstance(config_data, dict):
        logger.debug("Configuration fournie sous forme de dictionnaire. Tentative de localisation de la liste des sources.")
        # Cas 1: L'ID est une clé directe du dictionnaire principal
        for id_to_check in ids_to_inspect_set:
            if id_to_check in config_data and id_to_check not in found_ids_set:
                # Supposer que la valeur est la configuration de la source
                source_config = config_data[id_to_check]
                if isinstance(source_config, dict):
                     # Ajouter l'ID à la configuration de la source si elle n'y est pas, pour la cohérence
                    if "id" not in source_config:
                        source_config_copy = source_config.copy()
                        source_config_copy["id"] = id_to_check
                        logger.info(f"Source trouvée par clé ID: {id_to_check}")
                        found_sources_list.append(source_config_copy)
                    else: # L'ID est déjà dans le dict
                        logger.info(f"Source trouvée par clé ID (ID aussi dans le dict): {id_to_check}")
                        found_sources_list.append(source_config)
                    found_ids_set.add(id_to_check)
                else:
                    logger.warning(f"La clé ID '{id_to_check}' trouvée dans le dictionnaire de config, mais sa valeur n'est pas un dictionnaire de source.")


        # Cas 2: La liste des sources est sous une clé commune
        possible_list_keys = ["sources", "items", "data", "records"]
        source_list_found_in_dict = False
        for key in possible_list_keys:
            if key in config_data and isinstance(config_data[key], list):
                logger.debug(f"Liste de sources trouvée sous la clé '{key}'.")
                for item in config_data[key]:
                    process_source_item(item)
                source_list_found_in_dict = True
                break # Supposer qu'il n'y a qu'une seule liste de sources principale
        
        # Cas 3: Le dictionnaire lui-même est une seule source (moins courant pour une config de "sources")
        if not source_list_found_in_dict and not found_sources_list: # Si rien n'a été trouvé par les méthodes précédentes
            process_source_item(config_data) # Traiter le dictionnaire racine comme une source potentielle

    else:
        logger.warning(f"Format de configuration non supporté (type: {type(config_data)}). Attendu: liste ou dictionnaire.")

    if len(found_ids_set) < len(ids_to_inspect_set):
        missing_ids = ids_to_inspect_set - found_ids_set
        logger.warning(f"Certains IDs n'ont pas été trouvés: {missing_ids}")
        
    logger.info(f"{len(found_sources_list)} sources trouvées pour les IDs demandés.")
    return found_sources_list, found_ids_set

# D'autres utilitaires de configuration peuvent être ajoutés ici,
# par exemple, pour valider la structure d'une configuration de source,
# mettre à jour des entrées, etc.