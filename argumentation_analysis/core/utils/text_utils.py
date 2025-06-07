"""
Module utilitaire pour le traitement de texte.
"""

import re
import json
from typing import Dict, List, Any, Optional


def clean_text(text: str) -> str:
    """Nettoie le texte en supprimant les espaces en trop et caractères indésirables."""
    if not text:
        return ""
    
    # Supprimer les espaces en trop
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Supprimer les caractères de contrôle
    text = re.sub(r'[\x00-\x1F\x7F]', '', text)
    
    return text


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extrait un objet JSON valide d'un texte."""
    if not text:
        return None
    
    # Chercher les blocs JSON potentiels
    json_patterns = [
        r'\{[^{}]*\}',  # JSON simple
        r'\{.*?\}',     # JSON avec imbrication
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    return None


def sanitize_for_json(text: str) -> str:
    """Prépare le texte pour l'inclusion dans un JSON."""
    if not text:
        return ""
    
    # Échapper les caractères spéciaux JSON
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    text = text.replace('\n', '\\n')
    text = text.replace('\r', '\\r')
    text = text.replace('\t', '\\t')
    
    return text


def truncate_text(text: str, max_length: int = 1000) -> str:
    """Tronque le texte à la longueur maximale spécifiée."""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length] + "..."


def split_into_chunks(text: str, chunk_size: int = 500) -> List[str]:
    """Divise le texte en chunks de taille spécifiée."""
    if not text:
        return []
    
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    
    return chunks


def find_text_boundaries(text: str, start_marker: str, end_marker: str) -> List[tuple]:
    """Trouve les limites de texte entre des marqueurs."""
    boundaries = []
    start_pos = 0
    
    while True:
        start_idx = text.find(start_marker, start_pos)
        if start_idx == -1:
            break
            
        end_idx = text.find(end_marker, start_idx + len(start_marker))
        if end_idx == -1:
            break
            
        boundaries.append((start_idx, end_idx + len(end_marker)))
        start_pos = end_idx + len(end_marker)
    
    return boundaries


def extract_between_markers(text: str, start_marker: str, end_marker: str) -> List[str]:
    """Extrait le texte entre des marqueurs spécifiés."""
    extracts = []
    boundaries = find_text_boundaries(text, start_marker, end_marker)
    
    for start_pos, end_pos in boundaries:
        extract = text[start_pos + len(start_marker):end_pos - len(end_marker)]
        extracts.append(extract.strip())
    
    return extracts


def normalize_whitespace(text: str) -> str:
    """Normalise les espaces blancs dans le texte."""
    if not text:
        return ""
    
    # Remplacer tous les types d'espaces par des espaces simples
    text = re.sub(r'\s+', ' ', text)
    
    # Supprimer les espaces en début et fin
    return text.strip()


def count_words(text: str) -> int:
    """Compte le nombre de mots dans le texte."""
    if not text:
        return 0
    
    words = re.findall(r'\b\w+\b', text)
    return len(words)


def count_sentences(text: str) -> int:
    """Compte le nombre de phrases dans le texte."""
    if not text:
        return 0
    
    sentences = re.split(r'[.!?]+', text)
    return len([s for s in sentences if s.strip()])
def extract_text_with_markers(text: str, start_marker: str = "<<<", end_marker: str = ">>>") -> str:
    """
    Extrait le texte entre des marqueurs spécifiés.
    
    Args:
        text: Le texte source
        start_marker: Marqueur de début 
        end_marker: Marqueur de fin
        
    Returns:
        Le texte extrait entre les marqueurs, ou une chaîne vide si non trouvé
        
    Example:
        >>> extract_text_with_markers("Avant <<<contenu>>> Après")
        'contenu'
    """
    try:
        start_index = text.find(start_marker)
        if start_index == -1:
            return ""
            
        start_index += len(start_marker)
        end_index = text.find(end_marker, start_index)
        
        if end_index == -1:
            return ""
            
        return text[start_index:end_index].strip()
    except Exception:
        return ""