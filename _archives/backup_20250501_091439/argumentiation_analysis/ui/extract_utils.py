"""
Module d'utilitaires pour la manipulation des extraits de texte.

Ce module fournit des fonctions spécialisées pour :
- Extraire du texte à partir de marqueurs
- Rechercher et suggérer des marqueurs similaires
- Mettre en évidence des marqueurs dans le texte
- Rechercher du texte dans les documents sources
"""

import re
import difflib
import logging
import json
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any, Union

# Import depuis le même package ui
from . import config as ui_config
from .utils import (
    load_extract_definitions, save_extract_definitions, 
    reconstruct_url, load_from_cache, get_cache_filepath
)

# Configuration du logging
extract_utils_logger = logging.getLogger("App.UI.ExtractUtils")
if not extract_utils_logger.handlers and not extract_utils_logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    extract_utils_logger.addHandler(handler)
    extract_utils_logger.setLevel(logging.INFO)

def load_source_text(source_info: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """
    Charge le texte source depuis le cache.
    
    Args:
        source_info: Dictionnaire contenant les informations de la source
        
    Returns:
        Tuple contenant (texte_source, message_ou_url)
    """
    try:
        reconstructed_url = reconstruct_url(
            source_info.get("schema"), source_info.get("host_parts", []), source_info.get("path")
        )
        if not reconstructed_url:
            return None, "URL invalide"
        
        cached_text = load_from_cache(reconstructed_url)
        if cached_text is None:
            return None, "Texte non trouvé dans le cache"
        
        return cached_text, reconstructed_url
    except Exception as e:
        extract_utils_logger.error(f"Erreur lors du chargement du texte source: {e}")
        return None, f"Erreur: {str(e)}"

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
    if not text:
        return None, "Texte source vide", False, False
    
    start_index = 0
    end_index = len(text)
    start_found = False
    end_found = False
    complete_start_marker = start_marker
    
    # Recherche du marqueur de début
    if start_marker:
        try:
            # Essayer d'abord avec le marqueur tel quel
            found_start = text.index(start_marker)
            start_index = found_start + len(start_marker)
            start_found = True
        except ValueError:
            # Si échec et template disponible, essayer avec le template
            if template_start:
                try:
                    # Remplacer {0} dans le template par le marqueur original
                    complete_start_marker = template_start.replace("{0}", start_marker)
                    found_start = text.index(complete_start_marker)
                    start_index = found_start + len(complete_start_marker)
                    start_found = True
                except ValueError:
                    pass
    
    # Recherche du marqueur de fin
    if end_marker:
        try:
            found_end = text.index(end_marker, start_index)
            end_index = found_end
            end_found = True
        except ValueError:
            pass
    
    # Extraction du texte
    if start_index < end_index:
        extracted_text = text[start_index:end_index].strip()
        status = ""
        if not start_found:
            status += "⚠️ Marqueur début non trouvé. "
        if not end_found:
            status += "⚠️ Marqueur fin non trouvé. "
        if start_found and end_found:
            status = "✅ Extraction réussie"
        return extracted_text, status, start_found, end_found
    else:
        return None, "❌ Conflit de marqueurs ou texte vide", start_found, end_found

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
    if not text or not marker:
        return []
    
    # Utiliser difflib pour trouver des séquences similaires
    results = []
    
    # Si le marqueur est court, chercher des correspondances exactes de sous-chaînes
    if len(marker) < 20:
        pattern = re.escape(marker[:10]) if len(marker) > 10 else re.escape(marker)
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in matches[:max_results]:
            start_pos = max(0, match.start() - context_size)
            end_pos = min(len(text), match.end() + context_size)
            context = text[start_pos:end_pos]
            results.append((context, match.start(), match.group()))
    else:
        # Pour les marqueurs plus longs, utiliser difflib
        text_chunks = [text[i:i+len(marker)*2] for i in range(0, len(text), len(marker)//2)]
        for i, chunk in enumerate(text_chunks):
            ratio = difflib.SequenceMatcher(None, marker, chunk).ratio()
            if ratio > 0.6:  # Seuil de similarité
                pos = i * (len(marker)//2)
                start_pos = max(0, pos - context_size)
                end_pos = min(len(text), pos + len(marker) + context_size)
                context = text[start_pos:end_pos]
                results.append((context, pos, chunk[:len(marker)]))
                if len(results) >= max_results:
                    break
    
    return results

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
    if not text:
        return "<p>Texte vide</p>", False, False
    
    html_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    
    # Recherche et mise en évidence du marqueur de début
    start_found = False
    if start_marker and start_marker in text:
        html_text = html_text.replace(start_marker, f"<span style='background-color: #FFFF00; font-weight: bold;'>{start_marker}</span>")
        start_found = True
    elif template_start and start_marker:
        complete_start_marker = template_start.replace("{0}", start_marker)
        if complete_start_marker in text:
            html_text = html_text.replace(complete_start_marker, f"<span style='background-color: #FFFF00; font-weight: bold;'>{complete_start_marker}</span>")
            start_found = True
    
    # Recherche et mise en évidence du marqueur de fin
    end_found = False
    if end_marker and end_marker in text:
        html_text = html_text.replace(end_marker, f"<span style='background-color: #FFFF00; font-weight: bold;'>{end_marker}</span>")
        end_found = True
    
    return html_text, start_found, end_found

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
    if not text or not search_term:
        return []
    
    flags = 0 if case_sensitive else re.IGNORECASE
    matches = list(re.finditer(re.escape(search_term), text, flags))
    return matches

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
    if not text or not search_term:
        return "<p>Texte vide ou terme de recherche manquant</p>", 0
    
    matches = search_in_text(text, search_term, case_sensitive)
    if not matches:
        return f"<p>Aucun résultat pour '{search_term}'</p>", 0
    
    html_parts = []
    last_end = 0
    
    for match in matches:
        start_pos = max(0, match.start() - context_size)
        end_pos = min(len(text), match.end() + context_size)
        
        # Ajouter le texte avant le match
        if start_pos > last_end:
            html_parts.append("<p>...</p>")
        elif start_pos < last_end:
            start_pos = last_end
        
        # Extraire le contexte
        context = text[start_pos:end_pos]
        context_html = context.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        
        # Mettre en évidence le terme recherché
        match_start_in_context = match.start() - start_pos
        match_end_in_context = match.end() - start_pos
        highlighted_context = (
            context_html[:match_start_in_context] +
            f"<span style='background-color: #4CAF50; color: white; font-weight: bold;'>{context_html[match_start_in_context:match_end_in_context]}</span>" +
            context_html[match_end_in_context:]
        )
        
        html_parts.append(f"<div style='margin: 10px 0; padding: 5px; border-left: 3px solid #4CAF50;'>{highlighted_context}</div>")
        last_end = end_pos
    
    if last_end < len(text):
        html_parts.append("<p>...</p>")
    
    return "".join(html_parts), len(matches)

def load_extract_definitions_safely(
    config_file: Path, 
    encryption_key: bytes, 
    fallback_file: Optional[Path] = None
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Charge les définitions d'extraits avec gestion d'erreurs robuste.
    
    Args:
        config_file: Chemin vers le fichier de configuration principal
        encryption_key: Clé de chiffrement
        fallback_file: Chemin vers le fichier de secours (optionnel)
        
    Returns:
        Tuple contenant (extract_definitions, error_message)
    """
    extract_definitions = []
    error_message = None
    
    # Essayer de charger depuis le fichier principal
    try:
        extract_definitions = load_extract_definitions(config_file, encryption_key)
        if extract_definitions:
            extract_utils_logger.info(f"✅ Définitions chargées depuis {config_file}")
            return extract_definitions, None
    except Exception as e:
        error_message = f"Erreur lors du chargement de {config_file}: {str(e)}"
        extract_utils_logger.error(error_message)
    
    # Si échec ou pas de définitions, essayer le fichier de secours
    if fallback_file and fallback_file.exists():
        try:
            with open(fallback_file, 'r', encoding='utf-8') as f:
                extract_definitions = json.load(f)
            extract_utils_logger.info(f"✅ Définitions chargées depuis {fallback_file}")
            return extract_definitions, None
        except Exception as e:
            error_message = f"Erreur lors du chargement de {fallback_file}: {str(e)}"
            extract_utils_logger.error(error_message)
    
    # Si toujours rien, retourner une liste vide et le message d'erreur
    return extract_definitions, error_message or "Aucune définition d'extrait trouvée."

def save_extract_definitions_safely(
    definitions: List[Dict[str, Any]], 
    config_file: Path, 
    encryption_key: bytes, 
    fallback_file: Optional[Path] = None
) -> Tuple[bool, Optional[str]]:
    """
    Sauvegarde les définitions d'extraits avec gestion d'erreurs robuste.
    
    Args:
        definitions: Liste des définitions d'extraits
        config_file: Chemin vers le fichier de configuration principal
        encryption_key: Clé de chiffrement
        fallback_file: Chemin vers le fichier de secours (optionnel)
        
    Returns:
        Tuple contenant (success, error_message)
    """
    success = False
    error_message = None
    
    # Essayer de sauvegarder dans le fichier principal
    try:
        success = save_extract_definitions(definitions, config_file, encryption_key)
        if success:
            extract_utils_logger.info(f"✅ Définitions sauvegardées dans {config_file}")
            return True, None
    except Exception as e:
        error_message = f"Erreur lors de la sauvegarde dans {config_file}: {str(e)}"
        extract_utils_logger.error(error_message)
    
    # Si échec, essayer le fichier de secours
    if fallback_file:
        try:
            fallback_file.parent.mkdir(parents=True, exist_ok=True)
            with open(fallback_file, 'w', encoding='utf-8') as f:
                json.dump(definitions, f, indent=2, ensure_ascii=False)
            extract_utils_logger.info(f"✅ Définitions sauvegardées dans {fallback_file}")
            return True, None
        except Exception as e:
            error_message = f"Erreur lors de la sauvegarde dans {fallback_file}: {str(e)}"
            extract_utils_logger.error(error_message)
    
    # Si toujours pas de succès, retourner False et le message d'erreur
    return False, error_message or "Échec de la sauvegarde des définitions."

def export_definitions_to_json(
    definitions: List[Dict[str, Any]], 
    output_path: Optional[Path] = None
) -> Tuple[bool, str]:
    """
    Exporte les définitions d'extraits vers un fichier JSON.
    
    Args:
        definitions: Liste des définitions d'extraits
        output_path: Chemin vers le fichier de sortie (optionnel)
        
    Returns:
        Tuple contenant (success, message)
    """
    if not output_path:
        output_path = Path("./export_definitions.json")
    
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(definitions, f, indent=2, ensure_ascii=False)
        return True, f"✅ Définitions exportées vers {output_path}"
    except Exception as e:
        return False, f"❌ Erreur lors de l'exportation: {str(e)}"

def import_definitions_from_json(
    input_path: Path
) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
    """
    Importe les définitions d'extraits depuis un fichier JSON.
    
    Args:
        input_path: Chemin vers le fichier d'entrée
        
    Returns:
        Tuple contenant (success, definitions_or_error_message)
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            definitions = json.load(f)
        return True, definitions
    except Exception as e:
        return False, f"❌ Erreur lors de l'importation: {str(e)}"

# Initialisation du module
extract_utils_logger.info("Module extract_utils chargé.")