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
    from argumentiation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON, CACHE_DIR
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
    from argumentiation_analysis.ui.config import CACHE_DIR
    cache_service = CacheService(CACHE_DIR)

fetch_service = FetchService(cache_service)
crypto_service = CryptoService()

def load_source_text(source_info: Dict[str, Any]) -> Tuple[str, str]:
    """
    Charge le texte source à partir des informations de la source.
    
    Args:
        source_info: Informations sur la source
        
    Returns:
        Tuple contenant (texte_source, url_ou_message_erreur)
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
    Extrait le texte entre les marqueurs de début et de fin.
    
    Args:
        text: Texte source complet
        start_marker: Marqueur de début
        end_marker: Marqueur de fin
        template_start: Template pour le marqueur de début (optionnel)
        
    Returns:
        Tuple contenant (texte_extrait, statut, start_found, end_found)
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
    Trouve des textes similaires au marqueur dans le texte source.
    
    Args:
        text: Texte source complet
        marker: Marqueur à rechercher
        context_size: Nombre de caractères de contexte à inclure
        max_results: Nombre maximum de résultats à retourner
        
    Returns:
        Liste de tuples (contexte, position, texte_trouvé)
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
    Met en évidence les marqueurs dans le texte.
    
    Args:
        text: Texte source complet
        start_marker: Marqueur de début
        end_marker: Marqueur de fin
        template_start: Template pour le marqueur de début (optionnel)
        
    Returns:
        Tuple contenant (html_text, start_found, end_found)
    """
    # Utiliser le service d'extraction pour mettre en évidence le texte
    return extract_service.highlight_text(text, start_marker, end_marker, template_start)

def search_in_text(
    text: str, 
    search_term: str, 
    case_sensitive: bool = False
) -> List[re.Match]:
    """
    Recherche un terme dans le texte et retourne les positions trouvées.
    
    Args:
        text: Texte source complet
        search_term: Terme à rechercher
        case_sensitive: Si True, la recherche est sensible à la casse
        
    Returns:
        Liste des correspondances trouvées
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
    Met en évidence les résultats de recherche dans le texte.
    
    Args:
        text: Texte source complet
        search_term: Terme à rechercher
        case_sensitive: Si True, la recherche est sensible à la casse
        context_size: Nombre de caractères de contexte à inclure
        
    Returns:
        Tuple contenant (html_results, count)
    """
    # Utiliser le service d'extraction pour mettre en évidence les résultats de recherche
    return extract_service.highlight_search_results(text, search_term, case_sensitive, context_size)

def load_extract_definitions_safely(
    config_file: Union[str, Path], 
    encryption_key: Optional[str], 
    fallback_json_file: Optional[Union[str, Path]] = None
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Charge les définitions d'extraits de manière sécurisée.
    
    Args:
        config_file: Chemin vers le fichier de configuration chiffré
        encryption_key: Clé de chiffrement (peut être None)
        fallback_json_file: Chemin vers un fichier JSON de secours (peut être None)
        
    Returns:
        Tuple contenant (définitions_extraits, message)
    """
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
    
    Args:
        extract_definitions: Définitions d'extraits à sauvegarder
        config_file: Chemin vers le fichier de configuration chiffré
        encryption_key: Clé de chiffrement (peut être None)
        fallback_json_file: Chemin vers un fichier JSON de secours (peut être None)
        
    Returns:
        Tuple contenant (succès, message)
    """
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
    Exporte les définitions d'extraits vers un fichier JSON.
    
    Args:
        extract_definitions: Définitions d'extraits à exporter
        output_path: Chemin vers le fichier de sortie
        
    Returns:
        Tuple contenant (succès, message)
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
    Importe les définitions d'extraits depuis un fichier JSON.
    
    Args:
        input_path: Chemin vers le fichier d'entrée
        
    Returns:
        Tuple contenant (succès, définitions_ou_message_erreur)
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