from typing import Tuple, Optional # Ajout pour le typage
import logging # Ajout pour logging

logger = logging.getLogger(__name__) # Ajout logger
"""
Ce module fournit des fonctions utilitaires pour la manipulation et la normalisation de chaînes de caractères.

Il contient des fonctions pour :
- Normaliser le texte (minuscules, suppression de ponctuation, accents, espaces).
- Tokeniser le texte en mots.
"""
import re
import string
import unicodedata
from typing import List, Dict, Any # Ajout de Dict et Any

def normalize_text(text: str) -> str:
    """
    Normalise un texte en le convertissant en minuscules, en supprimant la ponctuation,
    en normalisant les espaces blancs et en supprimant les accents.

    :param text: Le texte à normaliser.
    :type text: str
    :return: Le texte normalisé.
    :rtype: str
    :raises TypeError: Si l'entrée n'est pas une chaîne de caractères.

    Examples:
        >>> normalize_text("  Ceci est un EXEMPLE, avec des accents (éàç) et des espaces !  ")
        'ceci est un exemple avec des accents eac et des espaces'
        >>> normalize_text("    Multiple    espaces   et   tabulations\t\t")
        'multiple espaces et tabulations'
        >>> normalize_text("Punctuation:!@#$%^&*()_+{}[]|\\:;\"'<>?,./-=")
        'punctuation'
    """
    if not isinstance(text, str):
        raise TypeError("L'entrée doit être une chaîne de caractères.")

    # Conversion en minuscules
    text = text.lower()

    # Suppression des accents (diacritiques)
    # La normalisation Unicode NFD (Normalization Form D) décompose les caractères accentués
    # en leur caractère de base suivi de leurs marques diacritiques combinantes.
    # Par exemple, "é" devient "e" + "´".
    # Ensuite, nous filtrons ces marques diacritiques (catégorie Unicode 'Mn').
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'  # 'Mn' correspond à Mark, Nonspacing (diacritiques)
    )

    # Gestion spécifique des apostrophes avant la suppression générale de la ponctuation.
    # L'objectif est de conserver les apostrophes internes aux mots (ex: "l'important")
    # tout en supprimant celles qui sont en début/fin de mot ou multiples.
    text = re.sub(r"'{2,}", " ", text)  # Remplace les apostrophes doubles ou plus par un espace.
    # Remplace les apostrophes en début ou fin de mot, ou celles isolées par des espaces.
    # (?<!\w) : assertion négative arrière, s'assure qu'il n'y a pas de caractère de mot avant.
    # (?!\w) : assertion négative avant, s'assure qu'il n'y a pas de caractère de mot après.
    text = re.sub(r"(?<!\w)'|'(?!\w)", " ", text)

    # Suppression de tous les autres signes de ponctuation définis dans string.punctuation.
    # L'apostrophe a déjà été traitée, donc on la retire de la liste des ponctuations à supprimer
    # pour ne pas affecter les apostrophes internes conservées.
    # Chaque caractère de ponctuation est remplacé par un espace.
    punctuations_to_remove = string.punctuation.replace("'", "")
    translator = str.maketrans(punctuations_to_remove, ' ' * len(punctuations_to_remove))
    text = text.translate(translator)

    # Normalisation des espaces blancs : remplace les séquences d'espaces multiples
    # (y compris tabulations, nouvelles lignes converties en espaces par les étapes précédentes)
    # par un seul espace, puis supprime les espaces en début et fin de chaîne.
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def tokenize_text(text: str) -> List[str]:
    """
    Tokenise un texte en une liste de mots après l'avoir normalisé.

    La normalisation est effectuée par la fonction `normalize_text`.
    Les tokens sont obtenus en divisant la chaîne normalisée par les espaces.

    :param text: Le texte à tokeniser.
    :type text: str
    :return: Une liste de tokens (mots).
    :rtype: List[str]
    :raises TypeError: Si l'entrée n'est pas une chaîne de caractères.

    Examples:
        >>> tokenize_text("  Ceci est un EXEMPLE, avec des accents (éàç) et des espaces !  ")
        ['ceci', 'est', 'un', 'exemple', 'avec', 'des', 'accents', 'eac', 'et', 'des', 'espaces']
        >>> tokenize_text("L'important c'est d'essayer.") # La normalisation actuelle sépare les mots aux apostrophes.
        ['l', 'important', 'c', 'est', 'd', 'essayer']
        >>> tokenize_text("")
        []
        >>> tokenize_text("Mot1 Mot2")
        ['mot1', 'mot2']
    """
    if not isinstance(text, str):
        raise TypeError("L'entrée doit être une chaîne de caractères.")

    # La normalisation est une étape préalable à la tokenisation.
    normalized_text = normalize_text(text)
    if not normalized_text: # Gérer le cas d'une chaîne vide après normalisation
        return []
    tokens = normalized_text.split()
    return tokens

if __name__ == '__main__':
    import doctest
    results = doctest.testmod()
    if results.failed == 0:
        print(f"Tous les {results.attempted} tests doctest ont réussi !")
    else:
        print(f"{results.failed} tests doctest sur {results.attempted} ont échoué.")

    # Exemples d'utilisation supplémentaires
    sample_text_1 = "  Ceci est un EXEMPLE, avec des accents (éàç) et des espaces !  "
    normalized_1 = normalize_text(sample_text_1)
    tokens_1 = tokenize_text(sample_text_1)
    print(f"\nTexte original 1: '{sample_text_1}'")
    print(f"Normalisé 1: '{normalized_1}'")
    print(f"Tokens 1: {tokens_1}")

    sample_text_2 = "L'élève studieux a obtenu d'excellents résultats."
    normalized_2 = normalize_text(sample_text_2)
    tokens_2 = tokenize_text(sample_text_2)
    print(f"\nTexte original 2: '{sample_text_2}'")
    print(f"Normalisé 2: '{normalized_2}'")
    print(f"Tokens 2: {tokens_2}")

    sample_text_3 = "    Beaucoup    d'espaces...   et\tde\ttabulations   !!!   "
    normalized_3 = normalize_text(sample_text_3)
    tokens_3 = tokenize_text(sample_text_3)
    print(f"\nTexte original 3: '{sample_text_3}'")
    print(f"Normalisé 3: '{normalized_3}'")
    print(f"Tokens 3: {tokens_3}")

    sample_text_4 = "Un texte sans ponctuation ni accents déjà propre"
    normalized_4 = normalize_text(sample_text_4)
    tokens_4 = tokenize_text(sample_text_4)
    print(f"\nTexte original 4: '{sample_text_4}'")
    print(f"Normalisé 4: '{normalized_4}'")
    print(f"Tokens 4: {tokens_4}")

    sample_text_5 = ""
    normalized_5 = normalize_text(sample_text_5)
    tokens_5 = tokenize_text(sample_text_5)
    print(f"\nTexte original 5: '{sample_text_5}'")
    print(f"Normalisé 5: '{normalized_5}'")
    print(f"Tokens 5: {tokens_5}")

    try:
        normalize_text(123)
    except TypeError as e:
        print(f"\nErreur attendue pour normalize_text avec entrée non-string: {e}")

    try:
        tokenize_text(None)
    except TypeError as e:
        print(f"\nErreur attendue pour tokenize_text avec entrée non-string: {e}")
def find_segment_with_markers(
    full_text: str, 
    start_marker: str, 
    end_marker: str
) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """
    Tente de trouver un segment de texte basé sur des marqueurs de début et de fin.

    La recherche du marqueur de fin commence après la fin du marqueur de début trouvé.
    Le segment retourné inclut les marqueurs de début et de fin.

    Args:
        full_text (str): Le texte complet dans lequel chercher.
        start_marker (str): La chaîne de caractères marquant le début du segment.
        end_marker (str): La chaîne de caractères marquant la fin du segment.

    Returns:
        Tuple[Optional[int], Optional[int], Optional[str]]: 
            Un tuple contenant:
            - L'index de début du marqueur de début dans full_text (ou None si non trouvé).
            - L'index de fin du marqueur de fin (c'est-à-dire l'index après le dernier caractère
              du marqueur de fin) dans full_text (ou None si non trouvé ou si erreur).
            - Le segment de texte extrait, incluant les marqueurs (ou None si non trouvé).
            Retourne (None, None, None) si l'un des arguments est invalide,
            si le marqueur de début n'est pas trouvé, ou si le marqueur de fin
            n'est pas trouvé après le marqueur de début.
    """
    if not all(isinstance(arg, str) for arg in [full_text, start_marker, end_marker]):
        logger.warning("find_segment_with_markers a reçu des arguments non-chaînes.")
        return None, None, None
    if not all([full_text, start_marker, end_marker]): # Vérifier aussi si les chaînes sont vides
        logger.debug("Un des arguments (full_text, start_marker, end_marker) est vide.")
        return None, None, None

    try:
        start_idx = full_text.find(start_marker)
        if start_idx == -1:
            logger.debug(f"Marqueur de début '{start_marker[:50]}...' non trouvé.")
            return None, None, None

        # Recherche end_marker APRES la fin de start_marker
        search_from_index = start_idx + len(start_marker)
        end_idx = full_text.find(end_marker, search_from_index)
        
        if end_idx == -1:
            logger.debug(f"Marqueur de fin '{end_marker[:50]}...' non trouvé après l'index {search_from_index}.")
            return None, None, None
            
        # L'index de fin pour le slicing doit inclure le end_marker
        segment_end_idx = end_idx + len(end_marker)
        
        # Le segment extrait inclut les marqueurs
        extracted_segment = full_text[start_idx : segment_end_idx]
        
        logger.debug(f"Segment trouvé: début à {start_idx}, fin (du marqueur de fin) à {segment_end_idx}. Aperçu: '{extracted_segment[:100]}...'")
        return start_idx, segment_end_idx, extracted_segment
        
    except Exception as e:
        logger.error(f"Erreur dans find_segment_with_markers: {e} avec start='{start_marker[:50]}...', end='{end_marker[:50]}...'", exc_info=True)
        return None, None, None
def populate_text_segment(
    source_full_text: str,
    extract_definition: Dict[str, Any] # Nécessite Dict from typing
) -> Optional[str]:
    """
    Peuple le 'full_text_segment' pour une définition d'extrait donnée
    en utilisant son texte source complet et ses marqueurs.

    Utilise la fonction `find_segment_with_markers` pour localiser le segment.

    Args:
        source_full_text (str): Le texte complet de la source à partir duquel extraire.
        extract_definition (Dict[str, Any]): Un dictionnaire représentant la définition
                                             d'un extrait. Doit contenir les clés
                                             'start_marker' et 'end_marker'.
                                             Le champ 'extract_name' est optionnel pour le logging.

    Returns:
        Optional[str]: Le segment de texte extrait (incluant les marqueurs) si trouvé,
                       sinon None.
                       La fonction logue les erreurs ou les marqueurs non trouvés.
    """
    if not source_full_text:
        logger.debug("Texte source complet manquant, impossible de peupler le segment.")
        return None
        
    if not isinstance(extract_definition, dict):
        logger.warning("La définition de l'extrait n'est pas un dictionnaire.")
        return None

    extract_name = extract_definition.get("extract_name", "Extrait Inconnu")
    start_marker = extract_definition.get("start_marker")
    end_marker = extract_definition.get("end_marker")

    if not start_marker or not end_marker:
        missing_info = []
        if not start_marker: missing_info.append("marqueur de début")
        if not end_marker: missing_info.append("marqueur de fin")
        logger.warning(f"{', '.join(missing_info).capitalize()} manquants pour l'extrait '{extract_name}'. Segment non peuplé.")
        return None

    _, _, segment = find_segment_with_markers(source_full_text, start_marker, end_marker)

    if segment:
        logger.debug(f"Segment peuplé pour l'extrait '{extract_name}' (longueur: {len(segment)}).")
        return segment
    else:
        # find_segment_with_markers logue déjà les détails si les marqueurs ne sont pas trouvés.
        logger.warning(f"Impossible de trouver/peupler le segment pour l'extrait '{extract_name}' avec les marqueurs fournis.")
        return None