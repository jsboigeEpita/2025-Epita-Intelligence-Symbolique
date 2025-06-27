# argumentation_analysis/agents/core/extract/extract_definitions.py
"""
Structures de données et définitions pour l'agent d'extraction.

Ce module fournit les briques de base pour l'`ExtractAgent` :
1.  `ExtractResult`: Une classe pour encapsuler de manière structurée le
    résultat d'une opération d'extraction.
2.  `ExtractDefinition`: Une classe pour définir les paramètres d'un
    extrait à rechercher.
3.  `ExtractAgentPlugin`: Un plugin pour Semantic Kernel qui regroupe des
    fonctions natives (non-LLM) pour la manipulation de texte, comme la
    recherche par bloc ou la division de texte.
"""

import re
import logging
from pathlib import Path # De la version stashed
from typing import List, Dict, Any, Tuple, Optional, Union
import json

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


class ExtractResult:
    """
    Encapsule le résultat d'une opération d'extraction de texte.

    Cette classe sert de structure de données standardisée pour retourner les
    informations issues d'une tentative d'extraction, qu'elle ait réussi ou
    échoué.

    Attributes:
        source_name (str): Nom de la source du texte (ex: nom de fichier).
        extract_name (str): Nom sémantique de l'extrait recherché.
        status (str): Statut de l'opération ('valid', 'rejected', 'error').
        message (str): Message lisible décrivant le résultat.
        start_marker (str): Le marqueur de début trouvé ou proposé.
        end_marker (str): Le marqueur de fin trouvé ou proposé.
        template_start (str): Template de début optionnel associé.
        explanation (str): Justification potentiellement fournie par le LLM.
        extracted_text (str): Le contenu textuel effectivement extrait.
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
        """Initialise une instance de ExtractResult."""
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
        """
        Convertit l'instance en un dictionnaire sérialisable.

        Returns:
            Dict[str, Any]: Une représentation de l'objet sous forme de dictionnaire.
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
        """
        Convertit l'instance en une chaîne de caractères JSON.

        Returns:
            str: Une représentation JSON de l'objet.
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractResult':
        """
        Crée une instance de `ExtractResult` à partir d'un dictionnaire.

        Args:
            data (Dict[str, Any]): Dictionnaire contenant les attributs de l'objet.

        Returns:
            ExtractResult: Une nouvelle instance de la classe.
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


class ExtractAgentPlugin:
    """
    Boîte à outils de fonctions natives pour la manipulation de texte.

    Ce plugin pour Semantic Kernel ne contient aucune fonction sémantique (LLM).
    Il sert de collection de fonctions utilitaires déterministes qui peuvent
    être appelées par l'agent ou d'autres composants pour effectuer des tâches
    de traitement de texte, telles que la recherche ou le découpage en blocs.
    """

    def __init__(self):
        """Initialise le plugin."""
        self.extract_results: List[Dict[str, Any]] = []

    def find_similar_markers(
        self,
        text: str,
        marker: str,
        max_results: int = 5,
        find_similar_text_func=None
    ) -> List[Dict[str, Any]]:
        """
        Trouve des passages de texte similaires à un marqueur donné.

        Cette fonction peut opérer de deux manières :
        - Si `find_similar_text_func` est fourni, elle l'utilise pour une recherche
          potentiellement sémantique ou avancée.
        - Sinon, elle effectue une recherche par expression régulière simple.

        Args:
            text (str): Le texte source dans lequel effectuer la recherche.
            marker (str): Le texte du marqueur à rechercher.
            max_results (int): Le nombre maximum de résultats à retourner.
            find_similar_text_func (Optional[Callable]): Fonction externe optionnelle
                pour effectuer la recherche.

        Returns:
            List[Dict[str, Any]]: Une liste de dictionnaires, où chaque dictionnaire
            représente une correspondance et contient 'marker', 'position', et 'context'.
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
        Recherche un terme par balayage de blocs (recherche non dichotomique).

        Note: Le nom de la méthode est un héritage historique. L'implémentation
        actuelle effectue une recherche par fenêtres glissantes (blocs) et non
        une recherche dichotomique.

        Args:
            text (str): Le texte à analyser.
            search_term (str): Le terme de recherche.
            block_size (int): La taille de chaque bloc d'analyse.
            overlap (int): Le nombre de caractères de chevauchement entre les blocs.

        Returns:
            List[Dict[str, Any]]: Une liste de correspondances, chacune étant un
            dictionnaire avec les détails de la correspondance.
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
        Divise un texte en blocs de taille spécifiée avec chevauchement.

        Cette fonction est utile pour traiter de grands textes en les segmentant
        en morceaux plus petits qui peuvent être traités individuellement.

        Args:
            text (str): Le texte source à segmenter.
            block_size (int): La taille de chaque bloc.
            overlap (int): La taille du chevauchement entre les blocs consécutifs.

        Returns:
            List[Dict[str, Any]]: Une liste de dictionnaires, où chaque dictionnaire
            représente un bloc et contient 'block', 'start_pos', et 'end_pos'.
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
        """
        Récupère les résultats d'extraction stockés.

        Note: La gestion de l'état via un attribut de classe est simple mais
        peut ne pas être robuste dans des scénarios complexes.

        Returns:
            List[Dict[str, Any]]: La liste des résultats stockés.
        """
        return self.extract_results


class ExtractDefinition:
    """
    Définit les paramètres pour une opération d'extraction.

    Cette classe est une structure de données qui contient toutes les
    informations nécessaires pour qu'un agent ou un outil puisse localiser
    un extrait de texte.

    Attributes:
        source_name (str): Nom de la source (ex: nom de fichier).
        extract_name (str): Nom sémantique de l'extrait à rechercher.
        start_marker (str): Texte du marqueur de début de l'extrait.
        end_marker (str): Texte du marqueur de fin de l'extrait.
        template_start (str): Template optionnel précédant le marqueur de début.
        description (str): Description textuelle de ce que représente l'extrait.
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
        """Initialise une instance de ExtractDefinition."""
        self.source_name = source_name
        self.extract_name = extract_name
        self.start_marker = start_marker
        self.end_marker = end_marker
        self.template_start = template_start
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance en un dictionnaire sérialisable.

        Returns:
            Dict[str, Any]: Une représentation de l'objet sous forme de dictionnaire.
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
        """
        Crée une instance de `ExtractDefinition` à partir d'un dictionnaire.

        Args:
            data (Dict[str, Any]): Dictionnaire contenant les attributs de l'objet.

        Returns:
            ExtractDefinition: Une nouvelle instance de la classe.
        """
        return cls(
            source_name=data.get("source_name", ""),
            extract_name=data.get("extract_name", ""),
            start_marker=data.get("start_marker", ""),
            end_marker=data.get("end_marker", ""),
            template_start=data.get("template_start", ""),
            description=data.get("description", "")
        )