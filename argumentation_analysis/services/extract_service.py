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
# current_dir = Path(__file__).parent # Commenté car start_api.py devrait gérer sys.path
# parent_dir = current_dir.parent
# if str(parent_dir) not in sys.path:
#     sys.path.insert(0, str(parent_dir))

# Correction des imports pour pointer vers le bon emplacement des modèles
from argumentation_analysis.models.extract_definition import ExtractResult, Extract, SourceDefinition, ExtractDefinitions

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
        Extrait le texte situé entre des marqueurs de début et de fin spécifiés.

        Tente de trouver `start_marker`. Si un `template_start` est fourni et que
        `start_marker` n'est pas trouvé directement, essaie de trouver le marqueur
        formaté avec le template. Cherche ensuite `end_marker` après le début trouvé.

        :param text: Le texte source complet à partir duquel extraire.
        :type text: str
        :param start_marker: La chaîne de caractères marquant le début de l'extrait.
        :type start_marker: str
        :param end_marker: La chaîne de caractères marquant la fin de l'extrait.
        :type end_marker: str
        :param template_start: Un template optionnel pour le marqueur de début,
                               où "{0}" sera remplacé par `start_marker`.
        :type template_start: Optional[str]
        :return: Un tuple contenant:
                 - Le texte extrait (str, ou None si échec).
                 - Un message de statut décrivant le résultat de l'extraction (str).
                 - Un booléen indiquant si le marqueur de début a été trouvé (bool).
                 - Un booléen indiquant si le marqueur de fin a été trouvé (bool).
        :rtype: Tuple[Optional[str], str, bool, bool]
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
                start_index = found_start + len(start_marker) # Exclure le marqueur de début
                start_found = True
            except ValueError:
                # Si échec et template disponible, essayer avec le template
                if template_start:
                    try:
                        # Remplacer {0} dans le template par le marqueur original
                        complete_start_marker = template_start.replace("{0}", start_marker)
                        found_start = text.index(complete_start_marker)
                        start_index = found_start + len(complete_start_marker) # Exclure le marqueur de début avec template
                        start_found = True
                    except ValueError:
                        pass
        
        # Recherche du marqueur de fin
        if end_marker:
            try:
                found_end = text.index(end_marker, start_index)
                end_index = found_end # Exclure le marqueur de fin
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
        Trouve des portions de texte similaires à un marqueur donné dans un texte source.

        Utilise `re.finditer` pour les marqueurs courts et `difflib.SequenceMatcher`
        pour les marqueurs plus longs afin de trouver des correspondances.

        :param text: Le texte source complet dans lequel rechercher.
        :type text: str
        :param marker: Le marqueur (chaîne de caractères) à rechercher.
        :type marker: str
        :param context_size: Le nombre de caractères de contexte à inclure avant et
                             après chaque correspondance trouvée.
        :type context_size: int
        :param max_results: Le nombre maximum de résultats similaires à retourner.
        :type max_results: int
        :return: Une liste de tuples. Chaque tuple contient:
                 - Le contexte entourant le texte trouvé (str).
                 - La position de début du texte trouvé dans le texte source original (int).
                 - Le texte trouvé qui est similaire au marqueur (str).
                 Retourne une liste vide si aucun texte similaire n'est trouvé ou si
                 `text` ou `marker` sont vides.
        :rtype: List[Tuple[str, int, str]]
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
        Met en évidence les marqueurs de début et de fin dans un texte en les entourant
        de balises HTML `<span>` avec un style spécifique.

        Gère l'échappement des caractères HTML de base et la conversion des sauts de ligne.

        :param text: Le texte source complet.
        :type text: str
        :param start_marker: Le marqueur de début à mettre en évidence.
        :type start_marker: str
        :param end_marker: Le marqueur de fin à mettre en évidence.
        :type end_marker: str
        :param template_start: Un template optionnel pour le marqueur de début.
        :type template_start: Optional[str]
        :return: Un tuple contenant:
                 - Le texte formaté en HTML avec les marqueurs en évidence (str).
                 - Un booléen indiquant si le marqueur de début a été trouvé (bool).
                 - Un booléen indiquant si le marqueur de fin a été trouvé (bool).
        :rtype: Tuple[str, bool, bool]
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
        Recherche toutes les occurrences d'un terme dans un texte.

        Utilise les expressions régulières pour trouver les correspondances.

        :param text: Le texte source complet dans lequel rechercher.
        :type text: str
        :param search_term: Le terme à rechercher.
        :type search_term: str
        :param case_sensitive: Si True, la recherche est sensible à la casse.
                               Par défaut à False (insensible à la casse).
        :type case_sensitive: bool
        :return: Une liste d'objets `re.Match` représentant toutes les correspondances
                 trouvées. Retourne une liste vide si `text` ou `search_term` sont vides.
        :rtype: List[re.Match]
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
        Met en évidence toutes les occurrences d'un terme de recherche dans un texte,
        en fournissant un contexte HTML pour chaque correspondance.

        :param text: Le texte source complet.
        :type text: str
        :param search_term: Le terme à rechercher et à mettre en évidence.
        :type search_term: str
        :param case_sensitive: Si True, la recherche est sensible à la casse.
                               Par défaut à False.
        :type case_sensitive: bool
        :param context_size: Le nombre de caractères de contexte à afficher avant
                             et après chaque correspondance.
        :type context_size: int
        :return: Un tuple contenant:
                 - Une chaîne HTML avec les résultats de recherche mis en évidence
                   et leur contexte (str).
                 - Le nombre total de correspondances trouvées (int).
        :rtype: Tuple[str, int]
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
        Divise un texte en blocs de taille spécifiée avec un chevauchement défini.

        Utile pour traiter de grands textes par morceaux pour des analyses
        qui pourraient être limitées par la taille de l'entrée.

        :param text: Le texte source complet à diviser en blocs.
        :type text: str
        :param block_size: La taille souhaitée pour chaque bloc de texte.
        :type block_size: int
        :param overlap: Le nombre de caractères de chevauchement entre les blocs consécutifs.
        :type overlap: int
        :return: Une liste de dictionnaires. Chaque dictionnaire représente un bloc et
                 contient:
                 - "block" (str): Le contenu textuel du bloc.
                 - "start_pos" (int): La position de début du bloc dans le texte original.
                 - "end_pos" (int): La position de fin du bloc dans le texte original.
                 Retourne une liste vide si le texte d'entrée est vide.
        :rtype: List[Dict[str, Any]]
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
        Recherche un terme dans un texte en le divisant d'abord en blocs.

        Cette méthode est une simplification et ne réalise pas une recherche
        dichotomique au sens strict algorithmique, mais plutôt une recherche
        par blocs. Elle divise le texte en blocs avec chevauchement et recherche
        le terme dans chaque bloc.

        :param text: Le texte source complet dans lequel rechercher.
        :type text: str
        :param search_term: Le terme à rechercher (insensible à la casse).
        :type search_term: str
        :param block_size: La taille des blocs dans lesquels diviser le texte.
        :type block_size: int
        :param overlap: Le chevauchement entre les blocs consécutifs.
        :type overlap: int
        :return: Une liste de dictionnaires. Chaque dictionnaire représente une
                 correspondance trouvée et contient:
                 - "match" (str): Le texte exact de la correspondance.
                 - "position" (int): La position de début de la correspondance dans le texte original.
                 - "context" (str): Un extrait de contexte entourant la correspondance.
                 - "block_start" (int): La position de début du bloc où la correspondance a été trouvée.
                 - "block_end" (int): La position de fin du bloc.
                 Retourne une liste vide si `text` ou `search_term` sont vides.
        :rtype: List[Dict[str, Any]]
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