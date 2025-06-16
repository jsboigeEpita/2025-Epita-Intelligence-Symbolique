# argumentation_analysis/agents/core/extract/extract_definitions.py
"""
Définitions et structures de données pour l'agent d'extraction.

Ce module contient les classes Pydantic (ou similaires) et les structures de données
utilisées par `ExtractAgent` et ses composants. Il définit :
    - `ExtractResult`: Pour encapsuler le résultat d'une opération d'extraction.
    - `ExtractAgentPlugin`: Un plugin contenant des fonctions natives utiles
      pour le traitement de texte dans le contexte de l'extraction.
    - `ExtractDefinition`: Pour représenter la définition d'un extrait spécifique
      à rechercher dans un texte source.
"""

import re
import logging
from pathlib import Path # De la version stashed
from typing import List, Dict, Any, Tuple, Optional, Union

# Importer PROJECT_ROOT depuis la configuration centrale (de la version stashed)
try:
    from argumentation_analysis.ui.config import PROJECT_ROOT
except ImportError:
    # Fallback si le script est exécuté dans un contexte où l'import direct n'est pas possible
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# Configuration du logging (de la version stashed)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ExtractAgent.Definitions")

# Création d'un handler pour écrire les logs dans un fichier (de la version stashed)
log_dir = PROJECT_ROOT / "_temp" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file_path = log_dir / "extract_agent.log"

file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(file_handler)


class ExtractResult: # De la version HEAD (Updated upstream)
    """
    Classe représentant le résultat d'une opération d'extraction.

    Cette classe encapsule toutes les informations pertinentes suite à une tentative
    d'extraction, y compris le statut, les marqueurs, le texte extrait et
    toute explication ou message d'erreur.

    Attributes:
        source_name (str): Nom de la source du texte.
        extract_name (str): Nom de l'extrait.
        status (str): Statut de l'extraction (ex: "valid", "rejected", "error").
        message (str): Message descriptif concernant le résultat.
        start_marker (str): Marqueur de début utilisé ou proposé.
        end_marker (str): Marqueur de fin utilisé ou proposé.
        template_start (str): Template de début utilisé ou proposé.
        explanation (str): Explication fournie par l'agent pour l'extraction.
        extracted_text (str): Le texte effectivement extrait.
    """
    
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
        Initialise un objet `ExtractResult`.

        :param source_name: Nom de la source du texte.
        :type source_name: str
        :param extract_name: Nom de l'extrait.
        :type extract_name: str
        :param status: Statut de l'extraction (par exemple, "valid", "rejected", "error").
        :type status: str
        :param message: Message descriptif concernant le résultat de l'extraction.
        :type message: str
        :param start_marker: Marqueur de début utilisé ou proposé. Par défaut "".
        :type start_marker: str
        :param end_marker: Marqueur de fin utilisé ou proposé. Par défaut "".
        :type end_marker: str
        :param template_start: Template de début utilisé ou proposé. Par défaut "".
        :type template_start: str
        :param explanation: Explication fournie par l'agent pour l'extraction. Par défaut "".
        :type explanation: str
        :param extracted_text: Le texte effectivement extrait. Par défaut "".
        :type extracted_text: str
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
        """Convertit l'instance `ExtractResult` en un dictionnaire.

        :return: Un dictionnaire représentant l'objet.
        :rtype: Dict[str, Any]
        """
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
    
    def to_json(self) -> str:
        """Convertit l'instance `ExtractResult` en une chaîne JSON.

        :return: Une chaîne JSON représentant l'objet.
        :rtype: str
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractResult':
        """Crée une instance de `ExtractResult` à partir d'un dictionnaire.

        :param data: Dictionnaire contenant les données pour initialiser l'objet.
        :type data: Dict[str, Any]
        :return: Une nouvelle instance de `ExtractResult`.
        :rtype: ExtractResult
        """
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


class ExtractAgentPlugin: # De la version HEAD (Updated upstream)
    """
    Plugin contenant des fonctions natives utiles pour l'agent d'extraction.

    Ce plugin regroupe des méthodes de traitement de texte qui ne nécessitent pas
    d'appel à un LLM mais sont utiles pour préparer les données ou analyser
    les textes sources dans le cadre du processus d'extraction.

    Attributes:
        extract_results (List[Dict[str, Any]]): Une liste pour stocker les résultats
            des opérations d'extraction effectuées, à des fins de journalisation ou de suivi.
            (Note: L'utilisation de cette liste pourrait être revue pour une meilleure gestion d'état).
    """
    
    def __init__(self):
        """Initialise le plugin `ExtractAgentPlugin`.

        Initialise une liste vide `extract_results` pour stocker les résultats
        des opérations d'extraction effectuées par ce plugin.
        """
        self.extract_results: List[Dict[str, Any]] = []
    
    def find_similar_markers(
        self, 
        text: str, 
        marker: str, 
        max_results: int = 5,
        find_similar_text_func=None
    ) -> List[Dict[str, Any]]:
        """
        Trouve des marqueurs textuels similaires à un marqueur donné dans un texte source.

        Utilise soit une fonction `find_similar_text_func` fournie, soit une
        implémentation basique par défaut basée sur des regex simples.

        :param text: Le texte source complet dans lequel rechercher.
        :type text: str
        :param marker: Le marqueur (chaîne de caractères) à rechercher.
        :type marker: str
        :param max_results: Le nombre maximum de résultats similaires à retourner.
        :type max_results: int
        :param find_similar_text_func: Fonction optionnelle à utiliser pour trouver
                                       du texte similaire. Si None, une recherche
                                       basique est effectuée.
        :type find_similar_text_func: Optional[Callable]
        :return: Une liste de dictionnaires, chaque dictionnaire représentant un marqueur
                 similaire trouvé et contenant "marker", "position", et "context".
                 Retourne une liste vide si aucun marqueur similaire n'est trouvé ou
                 si `text` ou `marker` sont vides.
        :rtype: List[Dict[str, Any]]
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
        Recherche un terme dans un texte en le divisant d'abord en blocs.

        Cette méthode est une simplification et ne réalise pas une recherche
        dichotomique au sens strict algorithmique, mais plutôt une recherche
        par blocs. Elle divise le texte en blocs avec chevauchement et recherche
        le terme (insensible à la casse) dans chaque bloc.

        :param text: Le texte source complet dans lequel rechercher.
        :type text: str
        :param search_term: Le terme à rechercher.
        :type search_term: str
        :param block_size: La taille des blocs dans lesquels diviser le texte.
        :type block_size: int
        :param overlap: Le chevauchement entre les blocs consécutifs.
        :type overlap: int
        :return: Une liste de dictionnaires. Chaque dictionnaire représente une
                 correspondance trouvée et contient "match", "position", "context",
                 "block_start", et "block_end".
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
    
    def extract_blocks(
        self, 
        text: str, 
        block_size: int = 500, 
        overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Divise un texte en blocs de taille spécifiée avec un chevauchement défini.

        Utile pour traiter de grands textes par morceaux.

        :param text: Le texte source complet à diviser en blocs.
        :type text: str
        :param block_size: La taille souhaitée pour chaque bloc de texte.
        :type block_size: int
        :param overlap: Le nombre de caractères de chevauchement entre les blocs consécutifs.
        :type overlap: int
        :return: Une liste de dictionnaires. Chaque dictionnaire représente un bloc et
                 contient "block", "start_pos", et "end_pos".
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
    
    def get_extract_results(self) -> List[Dict[str, Any]]:
        """Récupère la liste des résultats des opérations d'extraction stockées.

        :return: Une liste de dictionnaires, chaque dictionnaire représentant
                 le résultat d'une opération d'extraction.
        :rtype: List[Dict[str, Any]]
        """
        return self.extract_results


class ExtractDefinition: # De la version HEAD (Updated upstream)
    """
    Classe représentant la définition d'un extrait à rechercher ou à gérer.

    Cette structure de données contient les informations nécessaires pour identifier
    et localiser un segment de texte spécifique (un "extrait") au sein d'un
    document source plus large.

    Attributes:
        source_name (str): Nom de la source du texte.
        extract_name (str): Nom ou description de l'extrait.
        start_marker (str): Le marqueur textuel indiquant le début de l'extrait.
        end_marker (str): Le marqueur textuel indiquant la fin de l'extrait.
        template_start (str): Un template optionnel qui peut précéder le `start_marker`.
        description (str): Une description optionnelle de ce que représente l'extrait.
    """
    
    def __init__(
        self,
        source_name: str,
        extract_name: str,
        start_marker: str,
        end_marker: str,
        template_start: str = "",
        description: str = ""
    ):
        """
        Initialise un objet `ExtractDefinition`.

        :param source_name: Nom de la source du texte.
        :type source_name: str
        :param extract_name: Nom de l'extrait.
        :type extract_name: str
        :param start_marker: Marqueur de début pour l'extrait.
        :type start_marker: str
        :param end_marker: Marqueur de fin pour l'extrait.
        :type end_marker: str
        :param template_start: Template optionnel pour le marqueur de début. Par défaut "".
        :type template_start: str
        :param description: Description optionnelle de l'extraction. Par défaut "".
        :type description: str
        """
        self.source_name = source_name
        self.extract_name = extract_name
        self.start_marker = start_marker
        self.end_marker = end_marker
        self.template_start = template_start
        self.description = description
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance `ExtractDefinition` en un dictionnaire.

        :return: Un dictionnaire représentant l'objet.
        :rtype: Dict[str, Any]
        """
        return {
            "source_name": self.source_name,
            "extract_name": self.extract_name,
            "start_marker": self.start_marker,
            "end_marker": self.end_marker,
            "template_start": self.template_start,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractDefinition':
        """Crée une instance de `ExtractDefinition` à partir d'un dictionnaire.

        :param data: Dictionnaire contenant les données pour initialiser l'objet.
        :type data: Dict[str, Any]
        :return: Une nouvelle instance de `ExtractDefinition`.
        :rtype: ExtractDefinition
        """
        return cls(
            source_name=data.get("source_name", ""),
            extract_name=data.get("extract_name", ""),
            start_marker=data.get("start_marker", ""),
            end_marker=data.get("end_marker", ""),
            template_start=data.get("template_start", ""),
            description=data.get("description", "")
        )