"""
Utilitaires pour l'extraction de texte et la gestion des marqueurs.

Ce module fournit des fonctions utilitaires pour l'extraction de texte à partir de sources,
la gestion des marqueurs, la recherche de texte similaire et la manipulation des définitions d'extraits.
"""

import re
import json
import logging
import gzip
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union

# Imports depuis les modules du projet
try:
    # Import relatif depuis le package ui
    from ..services.extract_service import ExtractService
    from ..services.fetch_service import FetchService
    from ..models.extract_definition import ExtractDefinitions
    from .config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON, CACHE_DIR
    from ..services.crypto_service import CryptoService
except ImportError:
    # Fallback pour les imports absolus
    from services.extract_service import ExtractService
    from services.fetch_service import FetchService
    from models.extract_definition import ExtractDefinitions
    from argumentation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON, CACHE_DIR
    from services.crypto_service import CryptoService

# Configuration du logging
logger = logging.getLogger("UI.ExtractUtils")

# Initialisation des services
extract_service = ExtractService()

# Le FetchService nécessite un CacheService avec un répertoire de cache
try:
    # Import relatif
    from ..services.cache_service import CacheService
    from ..ui.config import CACHE_DIR
    cache_service = CacheService(CACHE_DIR)
except ImportError:
    # Import absolu
    from services.cache_service import CacheService
    from argumentation_analysis.ui.config import CACHE_DIR
    cache_service = CacheService(CACHE_DIR)

fetch_service = FetchService(cache_service)
crypto_service = CryptoService()

def load_source_text(source_info: Dict[str, Any]) -> Tuple[str, str]:
    """
    Charge le texte source à partir des informations de la source en utilisant `FetchService`.

    :param source_info: Un dictionnaire contenant les informations nécessaires
                        pour reconstruire l'URL et déterminer la méthode de récupération.
    :type source_info: Dict[str, Any]
    :return: Un tuple contenant le texte source (str, ou None si échec) et
             l'URL traitée ou un message d'erreur (str).
    :rtype: Tuple[Optional[str], str]
    """
    try:
        # Utiliser le service de récupération pour charger le texte
        source_text, url = fetch_service.fetch_text(source_info)
        return source_text, url
    except Exception as e:
        logger.error(f"Erreur lors du chargement du texte source: {e}")
        return "", f"Erreur: {str(e)}"

def extract_text_with_markers(
    text: str, 
    start_marker: str, 
    end_marker: str, 
    template_start: Optional[str] = None
) -> Tuple[Optional[str], str, bool, bool]:
    """
    Extrait le texte situé entre des marqueurs de début et de fin spécifiés,
    en utilisant `ExtractService`.

    :param text: Le texte source complet à partir duquel extraire.
    :type text: str
    :param start_marker: La chaîne de caractères marquant le début de l'extrait.
    :type start_marker: str
    :param end_marker: La chaîne de caractères marquant la fin de l'extrait.
    :type end_marker: str
    :param template_start: Un template optionnel pour le marqueur de début.
    :type template_start: Optional[str]
    :return: Un tuple délégué par `ExtractService.extract_text_with_markers`:
             (texte_extrait, statut, start_found, end_found).
    :rtype: Tuple[Optional[str], str, bool, bool]
    """
    # Utiliser le service d'extraction pour extraire le texte
    return extract_service.extract_text_with_markers(text, start_marker, end_marker, template_start)

def find_similar_text(
    text: str, 
    marker: str, 
    context_size: int = 50, 
    max_results: int = 5
) -> List[Tuple[str, int, str]]:
    """
    Trouve des portions de texte similaires à un marqueur donné dans un texte source,
    en utilisant `ExtractService`.

    :param text: Le texte source complet dans lequel rechercher.
    :type text: str
    :param marker: Le marqueur (chaîne de caractères) à rechercher.
    :type marker: str
    :param context_size: Le nombre de caractères de contexte à inclure.
    :type context_size: int
    :param max_results: Le nombre maximum de résultats similaires à retourner.
    :type max_results: int
    :return: Une liste de tuples déléguée par `ExtractService.find_similar_text`:
             (contexte, position, texte_trouvé).
    :rtype: List[Tuple[str, int, str]]
    """
    # Utiliser le service d'extraction pour trouver du texte similaire
    return extract_service.find_similar_text(text, marker, context_size, max_results)

def highlight_text(
    text: str, 
    start_marker: str, 
    end_marker: str, 
    template_start: Optional[str] = None
) -> Tuple[str, bool, bool]:
    """
    Met en évidence les marqueurs de début et de fin dans un texte,
    en utilisant `ExtractService`.

    :param text: Le texte source complet.
    :type text: str
    :param start_marker: Le marqueur de début à mettre en évidence.
    :type start_marker: str
    :param end_marker: Le marqueur de fin à mettre en évidence.
    :type end_marker: str
    :param template_start: Un template optionnel pour le marqueur de début.
    :type template_start: Optional[str]
    :return: Un tuple délégué par `ExtractService.highlight_text`:
             (html_text, start_found, end_found).
    :rtype: Tuple[str, bool, bool]
    """
    # Utiliser le service d'extraction pour mettre en évidence le texte
    return extract_service.highlight_text(text, start_marker, end_marker, template_start)

def search_in_text(
    text: str, 
    search_term: str, 
    case_sensitive: bool = False
) -> List[re.Match]:
    """
    Recherche toutes les occurrences d'un terme dans un texte,
    en utilisant `ExtractService`.

    :param text: Le texte source complet dans lequel rechercher.
    :type text: str
    :param search_term: Le terme à rechercher.
    :type search_term: str
    :param case_sensitive: Si True, la recherche est sensible à la casse.
    :type case_sensitive: bool
    :return: Une liste d'objets `re.Match` déléguée par `ExtractService.search_in_text`.
    :rtype: List[re.Match]
    """
    # Utiliser le service d'extraction pour rechercher dans le texte
    return extract_service.search_in_text(text, search_term, case_sensitive)

def highlight_search_results(
    text: str, 
    search_term: str, 
    case_sensitive: bool = False, 
    context_size: int = 50
) -> Tuple[str, int]:
    """
    Met en évidence toutes les occurrences d'un terme de recherche dans un texte,
    en utilisant `ExtractService`.

    :param text: Le texte source complet.
    :type text: str
    :param search_term: Le terme à rechercher et à mettre en évidence.
    :type search_term: str
    :param case_sensitive: Si True, la recherche est sensible à la casse.
    :type case_sensitive: bool
    :param context_size: Le nombre de caractères de contexte à afficher.
    :type context_size: int
    :return: Un tuple délégué par `ExtractService.highlight_search_results`:
             (html_results, count).
    :rtype: Tuple[str, int]
    """
    # Utiliser le service d'extraction pour mettre en évidence les résultats de recherche
    return extract_service.highlight_search_results(text, search_term, case_sensitive, context_size)

def load_extract_definitions_safely(
    config_file: Union[str, Path], 
    encryption_key: Optional[str], 
    fallback_json_file: Optional[Union[str, Path]] = None
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Charge les définitions d'extraits de manière sécurisée, en essayant d'abord
    un fichier chiffré, puis un fichier JSON de secours.

    Utilise `CryptoService` pour le déchiffrement.

    :param config_file: Chemin vers le fichier de configuration principal (potentiellement chiffré).
    :type config_file: Union[str, Path]
    :param encryption_key: La clé de chiffrement binaire. Si None, le déchiffrement
                           du fichier principal n'est pas tenté.
    :type encryption_key: Optional[str]  # Devrait être Optional[bytes] pour CryptoService
    :param fallback_json_file: Chemin optionnel vers un fichier JSON non chiffré
                               de secours.
    :type fallback_json_file: Optional[Union[str, Path]]
    :return: Un tuple contenant la liste des définitions d'extraits (List[Dict[str, Any]])
             et un message de statut (str). Retourne une liste vide et un message d'erreur
             si tout échoue.
    :rtype: Tuple[List[Dict[str, Any]], str]
    """
    # TODO: L'encryption_key devrait être de type bytes pour CryptoService.
    #       Une conversion ou une adaptation de CryptoService pourrait être nécessaire.
    #       Pour l'instant, on suppose que CryptoService gère la conversion si besoin.
    try:
        # Essayer d'abord de charger depuis le fichier chiffré
        if encryption_key:
            try:
                config_path = Path(config_file)
                if config_path.exists():
                    # Déchiffrer le fichier
                    decrypted_data = crypto_service.decrypt_file(config_path, encryption_key)
                    if decrypted_data:
                        # Décompresser les données
                        json_data = gzip.decompress(decrypted_data).decode('utf-8')
                        extract_definitions = json.loads(json_data)
                        return extract_definitions, f"Définitions chargées depuis {config_path}"
            except Exception as e:
                logger.error(f"Erreur lors du déchiffrement: {e}")
                # Continuer avec le fallback
        
        # Si le déchiffrement échoue ou si pas de clé, essayer le fichier JSON
        if fallback_json_file:
            json_path = Path(fallback_json_file)
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    extract_definitions = json.load(f)
                return extract_definitions, f"Définitions chargées depuis {json_path}"
        
        # Si tout échoue, retourner une liste vide
        return [], "Aucun fichier de définitions trouvé"
    except Exception as e:
        logger.error(f"Erreur lors du chargement des définitions: {e}")
        return [], f"Erreur: {str(e)}"

def save_extract_definitions_safely(
    extract_definitions: List[Dict[str, Any]],
    config_file: Union[str, Path],
    encryption_key: Optional[str],
    fallback_json_file: Optional[Union[str, Path]] = None
) -> Tuple[bool, str]:
    """
    Sauvegarde les définitions d'extraits de manière sécurisée.

    Tente de chiffrer et compresser les données si `encryption_key` est fournie,
    et les sauvegarde dans `config_file`. Sauvegarde également en JSON brut dans
    `fallback_json_file` si spécifié.

    :param extract_definitions: La liste des définitions d'extraits à sauvegarder.
    :type extract_definitions: List[Dict[str, Any]]
    :param config_file: Chemin vers le fichier de configuration principal (pour la version chiffrée).
    :type config_file: Union[str, Path]
    :param encryption_key: La clé de chiffrement binaire. Si None, le chiffrement
                           n'est pas effectué pour `config_file`.
    :type encryption_key: Optional[str] # Devrait être Optional[bytes]
    :param fallback_json_file: Chemin optionnel vers un fichier JSON non chiffré
                               où sauvegarder les données en clair.
    :type fallback_json_file: Optional[Union[str, Path]]
    :return: Un tuple contenant un booléen indiquant le succès de l'opération
             et un message de statut.
    :rtype: Tuple[bool, str]
    """
    # TODO: L'encryption_key devrait être de type bytes.
    try:
        # Convertir en JSON
        json_data = json.dumps(extract_definitions, ensure_ascii=False, indent=2)
        
        # Sauvegarder dans le fichier JSON de secours si spécifié
        if fallback_json_file:
            json_path = Path(fallback_json_file)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(json_data)
            logger.info(f"Définitions sauvegardées dans {json_path}")
        
        # Sauvegarder dans le fichier chiffré si une clé est fournie
        if encryption_key:
            try:
                config_path = Path(config_file)
                config_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Compresser les données
                compressed_data = gzip.compress(json_data.encode('utf-8'))
                
                # Chiffrer les données
                crypto_service.encrypt_file(compressed_data, config_path, encryption_key)
                logger.info(f"Définitions chiffrées sauvegardées dans {config_path}")
                
                return True, f"Définitions sauvegardées avec succès"
            except Exception as e:
                logger.error(f"Erreur lors du chiffrement: {e}")
                if fallback_json_file:
                    return True, f"Définitions sauvegardées uniquement dans {fallback_json_file}"
                return False, f"Erreur lors du chiffrement: {str(e)}"
        
        # Si pas de clé mais JSON sauvegardé
        if fallback_json_file:
            return True, f"Définitions sauvegardées dans {fallback_json_file}"
        
        # Si ni clé ni JSON
        return False, "Aucun fichier de destination spécifié"
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde des définitions: {e}")
        return False, f"Erreur: {str(e)}"

def export_definitions_to_json(
    extract_definitions: List[Dict[str, Any]],
    output_path: Union[str, Path]
) -> Tuple[bool, str]:
    """
    Exporte les définitions d'extraits vers un fichier JSON non chiffré.

    :param extract_definitions: La liste des définitions d'extraits à exporter.
    :type extract_definitions: List[Dict[str, Any]]
    :param output_path: Le chemin du fichier de sortie JSON.
    :type output_path: Union[str, Path]
    :return: Un tuple contenant un booléen indiquant le succès de l'exportation
             et un message de statut.
    :rtype: Tuple[bool, str]
    """
    try:
        # Convertir en JSON
        json_data = json.dumps(extract_definitions, ensure_ascii=False, indent=2)
        
        # Sauvegarder dans le fichier
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_data)
        
        return True, f"✅ Définitions exportées avec succès vers {output_path}"
    except Exception as e:
        logger.error(f"Erreur lors de l'exportation des définitions: {e}")
        return False, f"❌ Erreur lors de l'exportation: {str(e)}"

def import_definitions_from_json(
    input_path: Union[str, Path]
) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
    """
    Importe les définitions d'extraits depuis un fichier JSON non chiffré.

    :param input_path: Le chemin du fichier d'entrée JSON.
    :type input_path: Union[str, Path]
    :return: Un tuple contenant un booléen indiquant le succès de l'importation
             et soit la liste des définitions d'extraits importées, soit un
             message d'erreur (str).
    :rtype: Tuple[bool, Union[List[Dict[str, Any]], str]]
    """
    try:
        # Charger depuis le fichier
        input_path = Path(input_path)
        if not input_path.exists():
            return False, f"❌ Fichier non trouvé: {input_path}"
        
        with open(input_path, 'r', encoding='utf-8') as f:
            extract_definitions = json.load(f)
        
        return True, extract_definitions
    except json.JSONDecodeError:
        logger.error(f"Erreur de format JSON dans le fichier {input_path}")
        return False, f"❌ Format JSON invalide dans {input_path}"
    except Exception as e:
        logger.error(f"Erreur lors de l'importation des définitions: {e}")
        return False, f"❌ Erreur lors de l'importation: {str(e)}"