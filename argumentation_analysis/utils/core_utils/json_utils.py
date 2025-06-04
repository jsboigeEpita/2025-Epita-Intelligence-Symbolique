# -*- coding: utf-8 -*-
"""
Utilitaires pour la manipulation de données et de fichiers JSON.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Union, Optional, Callable # Ajout de Union, Optional, Callable

logger = logging.getLogger(__name__)

def load_json_from_file(file_path: Path) -> Optional[Union[List[Any], Dict[str, Any]]]:
    """
    Charge des données JSON depuis un fichier.

    Args:
        file_path (Path): Chemin vers le fichier JSON.

    Returns:
        Optional[Union[List[Any], Dict[str, Any]]]: Les données JSON chargées
                                                    (liste ou dictionnaire),
                                                    ou None en cas d'erreur.
    """
    if not file_path.exists() or not file_path.is_file():
        logger.error(f"Fichier JSON non trouvé ou n'est pas un fichier: {file_path}")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Données JSON chargées avec succès depuis {file_path}")
        return data
    except json.JSONDecodeError as e_json:
        logger.error(f"Erreur de décodage JSON dans {file_path}: {e_json}", exc_info=True)
        return None
    except Exception as e_read:
        logger.error(f"Erreur de lecture du fichier JSON {file_path}: {e_read}", exc_info=True)
        return None

def save_json_to_file(
    data: Union[List[Any], Dict[str, Any]],
    file_path: Path,
    indent: int = 2,
    ensure_ascii: bool = False
) -> bool:
    """
    Sauvegarde des données Python dans un fichier JSON.

    Args:
        data: Les données à sauvegarder (liste ou dictionnaire).
        file_path (Path): Chemin du fichier de sortie JSON.
        indent (int): Niveau d'indentation pour le JSON.
        ensure_ascii (bool): Si True, la sortie est garantie d'avoir tous les
                             caractères non-ASCII échappés. Si False (défaut),
                             ces caractères sont sortis tels quels.
    Returns:
        bool: True si la sauvegarde a réussi, False sinon.
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        logger.info(f"Données JSON sauvegardées avec succès dans : {file_path.resolve()}")
        return True
    except TypeError as e_type:
        logger.error(f"Erreur de type lors de la sérialisation JSON pour {file_path}: {e_type}", exc_info=True)
        return False
    except IOError as e_io:
        logger.error(f"Erreur d'E/S lors de la sauvegarde JSON dans {file_path}: {e_io}", exc_info=True)
        return False
    except Exception as e_gen:
        logger.error(f"Erreur inattendue lors de la sauvegarde JSON dans {file_path}: {e_gen}", exc_info=True)
        return False

def filter_list_in_json_data(
    json_data: Union[List[Dict[str, Any]], Dict[str, Any]],
    filter_key: str,
    filter_value_to_remove: Any,
    list_path_key: Optional[str] = None
) -> Tuple[Union[List[Dict[str, Any]], Dict[str, Any]], int]:
    """
    Filtre une liste d'objets (dictionnaires) dans des données JSON chargées,
    en supprimant les éléments où une clé spécifiée a une certaine valeur.

    Args:
        json_data (Union[List[Dict[str, Any]], Dict[str, Any]]): 
            Les données JSON chargées. Peut être une liste d'objets directement,
            ou un dictionnaire contenant une liste d'objets sous la clé `list_path_key`.
        filter_key (str): La clé dans chaque objet de la liste à vérifier.
        filter_value_to_remove (Any): La valeur qui, si trouvée pour `filter_key`,
                                      entraînera la suppression de l'objet de la liste.
        list_path_key (Optional[str]): Si `json_data` est un dictionnaire, cette clé
                                       indique où trouver la liste à filtrer.
                                       Si None, `json_data` est supposé être la liste elle-même.
    Returns:
        Tuple[Union[List[Dict[str, Any]], Dict[str, Any]], int]: 
            Un tuple contenant:
            - Les données JSON modifiées (avec la liste filtrée).
            - Le nombre d'éléments supprimés.
            Si `json_data` n'est pas du type attendu ou si `list_path_key` est invalide,
            les données originales et 0 sont retournés.
    """
    items_removed_count = 0
    
    if isinstance(json_data, list) and list_path_key is None:
        original_list = json_data
        filtered_list = [
            item for item in original_list
            if not (isinstance(item, dict) and item.get(filter_key) == filter_value_to_remove)
        ]
        items_removed_count = len(original_list) - len(filtered_list)
        logger.info(f"{items_removed_count} éléments retirés de la liste racine.")
        return filtered_list, items_removed_count
        
    elif isinstance(json_data, dict) and list_path_key and list_path_key in json_data:
        if isinstance(json_data[list_path_key], list):
            original_list_in_dict = json_data[list_path_key]
            filtered_list_in_dict = [
                item for item in original_list_in_dict
                if not (isinstance(item, dict) and item.get(filter_key) == filter_value_to_remove)
            ]
            items_removed_count = len(original_list_in_dict) - len(filtered_list_in_dict)
            json_data[list_path_key] = filtered_list_in_dict # Modifier la copie
            logger.info(f"{items_removed_count} éléments retirés de la liste sous la clé '{list_path_key}'.")
            return json_data, items_removed_count
        else:
            logger.warning(f"La clé '{list_path_key}' dans les données JSON ne contient pas une liste. Aucun filtrage effectué.")
            return json_data, 0
            
    else:
        logger.warning(f"Structure de données JSON non prise en charge pour le filtrage (type: {type(json_data)}, list_path_key: {list_path_key}). Aucun filtrage effectué.")
        return json_data, 0