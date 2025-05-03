"""
Définitions et structures de données pour l'agent d'extraction.

Ce module contient les classes et structures de données utilisées par l'agent d'extraction
pour gérer les extraits et leurs métadonnées.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional, Union

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ExtractAgent.Definitions")

# Création d'un handler pour écrire les logs dans un fichier
file_handler = logging.FileHandler("extract_agent.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(file_handler)


class ExtractResult:
    """Classe représentant le résultat d'une extraction."""
    
    def __init__(
        self,
        source_name: str,
        extract_name: str,
        status: str,
        message: str,
        start_marker: str = "",
        end_marker: str = "",
        template_start: str = "",
        explanation: str = "",
        extracted_text: str = ""
    ):
        """
        Initialise un résultat d'extraction.
        
        Args:
            source_name: Nom de la source
            extract_name: Nom de l'extrait
            status: Statut de l'extraction (valid, rejected, error)
            message: Message explicatif
            start_marker: Marqueur de début
            end_marker: Marqueur de fin
            template_start: Template pour le marqueur de début
            explanation: Explication de l'extraction
            extracted_text: Texte extrait
        """
        self.source_name = source_name
        self.extract_name = extract_name
        self.status = status
        self.message = message
        self.start_marker = start_marker
        self.end_marker = end_marker
        self.template_start = template_start
        self.explanation = explanation
        self.extracted_text = extracted_text
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        return {
            "source_name": self.source_name,
            "extract_name": self.extract_name,
            "status": self.status,
            "message": self.message,
            "start_marker": self.start_marker,
            "end_marker": self.end_marker,
            "template_start": self.template_start,
            "explanation": self.explanation,
            "extracted_text": self.extracted_text
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractResult':
        """Crée un résultat à partir d'un dictionnaire."""
        return cls(
            source_name=data.get("source_name", ""),
            extract_name=data.get("extract_name", ""),
            status=data.get("status", ""),
            message=data.get("message", ""),
            start_marker=data.get("start_marker", ""),
            end_marker=data.get("end_marker", ""),
            template_start=data.get("template_start", ""),
            explanation=data.get("explanation", ""),
            extracted_text=data.get("extracted_text", "")
        )


class ExtractAgentPlugin:
    """Plugin pour les fonctions natives de l'extracteur agentique."""
    
    def __init__(self):
        """Initialise le plugin d'extraction."""
        self.extract_results = []
    
    def find_similar_markers(
        self, 
        text: str, 
        marker: str, 
        max_results: int = 5,
        find_similar_text_func=None
    ) -> List[Dict[str, Any]]:
        """
        Trouve des marqueurs similaires dans le texte source.
        
        Args:
            text: Texte source complet
            marker: Marqueur à rechercher
            max_results: Nombre maximum de résultats à retourner
            find_similar_text_func: Fonction pour trouver du texte similaire
            
        Returns:
            Liste de dictionnaires contenant les marqueurs similaires
        """
        if not text or not marker:
            return []
        
        if find_similar_text_func is None:
            # Implémentation par défaut si la fonction n'est pas fournie
            logger.warning("Fonction find_similar_text non fournie, utilisation d'une implémentation basique")
            
            similar_markers = []
            try:
                # Recherche simple avec regex
                pattern = re.escape(marker[:min(10, len(marker))])
                matches = list(re.finditer(pattern, text, re.IGNORECASE))
                
                for match in matches[:max_results]:
                    start_pos = max(0, match.start() - 50)
                    end_pos = min(len(text), match.end() + 50)
                    context = text[start_pos:end_pos]
                    
                    similar_markers.append({
                        "marker": match.group(),
                        "position": match.start(),
                        "context": context
                    })
                
                return similar_markers
            except Exception as e:
                logger.error(f"Erreur lors de la recherche de marqueurs similaires: {e}")
                return []
        else:
            # Utiliser la fonction fournie
            similar_markers = []
            results = find_similar_text_func(text, marker, context_size=50, max_results=max_results)
            
            for context, position, found_text in results:
                similar_markers.append({
                    "marker": found_text,
                    "position": position,
                    "context": context
                })
            
            return similar_markers
    
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
    
    def get_extract_results(self) -> List[Dict[str, Any]]:
        """Récupère les résultats des extractions effectuées."""
        return self.extract_results