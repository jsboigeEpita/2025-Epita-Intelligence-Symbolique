"""
Service d'extraction pour l'analyse d'argumentation.

Ce module fournit un service centralisé pour l'extraction de texte à partir de sources,
la gestion des marqueurs et la recherche de texte similaire.
"""

import re
import difflib
import logging
from typing import List, Dict, Any, Tuple, Optional, Union

# Imports absolus pour les tests
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from models.extract_result import ExtractResult
from models.extract_definition import Extract, SourceDefinition, ExtractDefinitions

# Configuration du logging
logger = logging.getLogger("Services.ExtractService")


class ExtractService:
    """Service pour l'extraction de texte et la gestion des marqueurs."""
    
    def __init__(self):
        """Initialise le service d'extraction."""
        self.logger = logger
    
    def extract_text_with_markers(
        self,
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
        self, 
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
        self, 
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
        self, 
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
        self, 
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
        
        matches = self.search_in_text(text, search_term, case_sensitive)
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
    
    def extract_blocks(
        self, 
        text: str, 
        block_size: int = 500, 
        overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Extrait des blocs de texte avec chevauchement pour l'analyse.
        
        Args:
            text: Texte source complet
            block_size: Taille des blocs de texte à extraire
            overlap: Chevauchement entre les blocs
            
        Returns:
            Liste de dictionnaires contenant les blocs de texte
        """
        if not text:
            return []
        
        blocks = []
        text_length = len(text)
        
        for i in range(0, text_length, block_size - overlap):
            start_pos = i
            end_pos = min(i + block_size, text_length)
            block = text[start_pos:end_pos]
            
            blocks.append({
                "block": block,
                "start_pos": start_pos,
                "end_pos": end_pos
            })
        
        return blocks
    
    def search_text_dichotomically(
        self, 
        text: str, 
        search_term: str, 
        block_size: int = 500, 
        overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Recherche un terme dans le texte en utilisant une approche dichotomique.
        
        Args:
            text: Texte source complet
            search_term: Terme à rechercher
            block_size: Taille des blocs de texte à analyser
            overlap: Chevauchement entre les blocs
            
        Returns:
            Liste de dictionnaires contenant les résultats de recherche
        """
        if not text or not search_term:
            return []
        
        results = []
        text_length = len(text)
        
        # Diviser le texte en blocs avec chevauchement
        for i in range(0, text_length, block_size - overlap):
            start_pos = i
            end_pos = min(i + block_size, text_length)
            block = text[start_pos:end_pos]
            
            # Rechercher le terme dans le bloc
            if search_term.lower() in block.lower():
                # Trouver toutes les occurrences
                for match in re.finditer(re.escape(search_term), block, re.IGNORECASE):
                    match_start = start_pos + match.start()
                    match_end = start_pos + match.end()
                    
                    # Extraire le contexte
                    context_start = max(0, match_start - 50)
                    context_end = min(text_length, match_end + 50)
                    context = text[context_start:context_end]
                    
                    results.append({
                        "match": match.group(),
                        "position": match_start,
                        "context": context,
                        "block_start": start_pos,
                        "block_end": end_pos
                    })
        
        return results