# project_core/dev_utils/format_utils.py
import logging
import os 
import sys 
import re 

# Configuration du logging pour ce module
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def fix_docstrings_apostrophes(file_path: str) -> bool:
    """
    Corrige certaines apostrophes problématiques dans les docstrings d'un fichier Python
    en les remplaçant par une version échappée ou entre guillemets.
    Cette fonction lit le fichier, effectue les remplacements, et réécrit le fichier.
    Utilise re.sub avec un pattern trié pour gérer correctement les sous-chaînes.

    Args:
        file_path: Chemin du fichier à corriger.

    Returns:
        True si l'opération a réussi (lecture et écriture), False en cas d'erreur.
    """
    logger.info(f"Tentative de correction des apostrophes de docstrings dans : {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        logger.error(f"Fichier non trouvé : {file_path}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier {file_path}: {e}", exc_info=True)
        return False

    original_content_for_comparison = content 

    replacements_map_full = {
        "Liste d'arguments": 'Liste "d\'arguments"',
        "d'abord": '"d\'abord"',
        "d'accord": '"d\'accord"',
        "d'ailleurs": '"d\'ailleurs"',
        "d'analyse": '"d\'analyse"',
        "d'application": '"d\'application"',
        "d'approche": '"d\'approche"',
        "d'apprentissage": '"d\'apprentissage"',
        "d'évaluation": '"d\'évaluation"',
        "d'éléments": '"d\'éléments"',
        "d'ensemble": '"d\'ensemble"',
        "d'entre": '"d\'entre"',
        "d'erreur": '"d\'erreur"',
        "d'état": '"d\'état"',
        "d'étude": '"d\'étude"',
        "d'être": '"d\'être"',
        "d'un": '"d\'un"',
        "d'une": '"d\'une"',
        "d'information": '"d\'information"',
        "d'utilisation": '"d\'utilisation"',
        "d'exécution": '"d\'exécution"',
        "d'accès": '"d\'accès"',
        "d'entrée": '"d\'entrée"',
        "d'interface": '"d\'interface"',
        "d'affichage": '"d\'affichage"',
        "d'initialisation": '"d\'initialisation"',
        "d'identification": '"d\'identification"',
        "d'authentification": '"d\'authentification"',
        "d'autorisation": '"d\'autorisation"',
        "d'enregistrement": '"d\'enregistrement"',
        "d'événement": '"d\'événement"',
        "d'exception": '"d\'exception"',
         "l'analyse": '"l\'analyse"',
         "l'application": '"l\'application"',
         "l'approche": '"l\'approche"',
         "l'apprentissage": '"l\'apprentissage"',
         "l'argumentation": '"l\'argumentation"',
         "l'article": '"l\'article"',
         "l'attention": '"l\'attention"',
         "l'auteur": '"l\'auteur"',
         "l'environnement": '"l\'environnement"',
         "l'évaluation": '"l\'évaluation"',
         "l'exemple": '"l\'exemple"',
         "l'expérience": '"l\'expérience"',
         "l'explication": '"l\'explication"',
         "l'expression": '"l\'expression"',
         "l'extraction": '"l\'extraction"',
         "l'historique": '"l\'historique"',
         "l'idée": '"l\'idée"',
         "l'image": '"l\'image"',
         "l'impact": '"l\'impact"',
         "l'importance": '"l\'importance"',
         "l'implémentation": '"l\'implémentation"',
         "l'information": '"l\'information"',
         "l'initiative": '"l\'initiative"',
         "l'instance": '"l\'instance"',
         "l'intégration": '"l\'intégration"',
         "l'intelligence": '"l\'intelligence"',
         "l'intention": '"l\'intention"',
         "l'interface": '"l\'interface"',
         "l'interprétation": '"l\'interprétation"',
         "l'introduction": '"l\'introduction"',
         "l'objet": '"l\'objet"',
         "l'objectif": '"l\'objectif"',
         "l'occurrence": '"l\'occurrence"',
         "l'offre": '"l\'offre"',
         "l'on": '"l\'on"',
         "l'opération": '"l\'opération"',
         "l'optimisation": '"l\'optimisation"',
         "l'option": '"l\'option"',
         "l'ordre": '"l\'ordre"',
         "l'organisation": '"l\'organisation"',
         "l'origine": '"l\'origine"',
         "l'outil": '"l\'outil"',
         "l'ouverture": '"l\'ouverture"',
         "l'utilisateur": '"l\'utilisateur"',
         "l'utilisation": '"l\'utilisation"',
         "lorsqu'il": '"lorsqu\'il"',
         "lorsqu'elle": '"lorsqu\'elle"',
         "lorsqu'on": '"lorsqu\'on"',
         "jusqu'à": '"jusqu\'à"',
         "jusqu'au": '"jusqu\'au"',
         "jusqu'en": '"jusqu\'en"',
         "quelqu'un": '"quelqu\'un"',
         "quelqu'une": '"quelqu\'une"',
         "presqu'île": '"presqu\'île"',
         "prud'hommal": '"prud\'hommal"',
         "prud'hommes": '"prud\'hommes"',
         "C'est": '"C\'est"',
         "c'est": '"c\'est"',
         "N'est": '"N\'est"',
         "n'est": '"n\'est"',
         "S'il": '"S\'il"',
         "s'il": '"s\'il"',
         "Qu'il": '"Qu\'il"',
         "qu'il": '"qu\'il"',
         "Qu'elle": '"Qu\'elle"',
         "qu'elle": '"qu\'elle"',
         "Qu'on": '"Qu\'on"',
         "qu'on": '"qu\'on"',
    }
    
    current_replacements_to_use = replacements_map_full

    # Trier les remplacements par la longueur de la clé de recherche (décroissant)
    # pour que le moteur regex essaie de faire correspondre les plus longs termes en premier.
    sorted_replacements_list = sorted(current_replacements_to_use.items(), key=lambda item: len(item[0]), reverse=True)
    
    logger.debug(f"Ordre des remplacements pour regex (terme, longueur): {[(item[0], len(item[0])) for item in sorted_replacements_list]}")

    # Créer un dictionnaire pour un accès rapide au remplacement basé sur le terme trouvé par regex
    replacements_dict_for_regex = dict(sorted_replacements_list)

    # Construire le pattern regex. re.escape est important pour les caractères spéciaux.
    # L'ordre dans le join est crucial et est assuré par sorted_replacements_list.
    # Le moteur regex de Python, lorsqu'il utilise des alternatives (|), essaie les patterns de gauche à droite
    # et prend la première correspondance trouvée. En triant par longueur décroissante, on s'assure
    # que les correspondances plus longues (et plus spécifiques) sont testées avant les plus courtes.
    pattern_str = "|".join(re.escape(term) for term, _ in sorted_replacements_list)
    regex_pattern = re.compile(pattern_str)
    logger.debug(f"Pattern Regex compilé: {regex_pattern.pattern}")

    def replacement_function(match):
        matched_text = match.group(0)
        original_content_str = match.string # Contenu sur lequel sub est appelé
        replacement_value = replacements_dict_for_regex.get(matched_text)
        
        if replacement_value is None:
            logger.warning(f"  Regex Match: '{matched_text}', mais aucun remplacement trouvé dans le dict. Laissé tel quel.")
            return matched_text

        # Logique d'idempotence:
        # Vérifier si le matched_text est déjà entouré par des guillemets
        # et si la valeur de remplacement attendue est bien le terme entouré de guillemets.
        already_formatted = False
        # Cas 1: remplacement simple type term -> "term"
        if replacement_value == f'"{matched_text}"':
            # Vérifier les caractères avant et après le match
            char_before_is_quote = False
            if match.start() > 0:
                if original_content_str[match.start()-1] == '"':
                    char_before_is_quote = True
            
            char_after_is_quote = False
            if match.end() < len(original_content_str):
                if original_content_str[match.end()] == '"':
                    char_after_is_quote = True
            
            if char_before_is_quote and char_after_is_quote:
                # Vérifier si le segment entier correspond déjà au remplacement
                # e.g., original: ..."d'un"... et replacement_value est "\"d'un\""
                # Le segment est original_content_str[match.start()-1 : match.end()+1]
                # S'il est égal à replacement_value, alors c'est déjà formaté.
                if original_content_str[match.start()-1 : match.end()+1] == replacement_value:
                    already_formatted = True
                    logger.debug(f"  Regex Match: '{matched_text}' (dans '{original_content_str[match.start()-1 : match.end()+1]}') semble déjà formaté comme '{replacement_value}'. Laissé tel quel.")

        # Cas 2: remplacement plus complexe comme 'Liste d'arguments' -> 'Liste "d'arguments"'
        # Pour ces cas, la logique ci-dessus n'est pas suffisante.
        # On pourrait vérifier si le `replacement_value` est une sous-chaîne de `original_content_str`
        # aux positions attendues.
        # Exemple: pour 'Liste d'arguments', si on trouve `Liste "d'arguments"`
        # Le match est 'Liste d'arguments'. start() est au début de 'L'. end() est après 's'.
        # replacement_value est 'Liste "d'arguments"'.
        # Si original_content_str[match.start() : match.start() + len(replacement_value)] == replacement_value
        # Cela pourrait être une heuristique, mais attention aux longueurs.
        # Pour l'instant, on se concentre sur le cas simple.
        # L'ordre de `sorted_replacements_list` (plus long d'abord) est la principale défense
        # contre les remplacements incorrects pour les cas complexes.

        if already_formatted:
            return matched_text # Ne pas re-remplacer
        else:
            logger.debug(f"  Regex Match: '{matched_text}' -> Remplacement par: '{replacement_value}'")
            return replacement_value

    modified_content = regex_pattern.sub(replacement_function, content)
            
    if modified_content == original_content_for_comparison:
        logger.info(f"Aucune modification d'apostrophe nécessaire dans {file_path}.")
    else:
        logger.info(f"Des modifications d'apostrophes ont été appliquées à {file_path}.")

    try:
        if modified_content != original_content_for_comparison: # Écrire uniquement si changement réel
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            logger.info(f"Fichier {file_path} sauvegardé avec les corrections d'apostrophes.")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'écriture du fichier corrigé {file_path}: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    # Section de test simple pour la fonction
    logger.setLevel(logging.DEBUG)
    
    # Créer un fichier de test
    test_file_content = """
def my_function():
    \"\"\"Ceci est un test d'évaluation.
    Il contient aussi d'un exemple et d'une note.
    Liste d'arguments:
        arg1: description d'un argument.
    \"\"\"
    pass

class MyClass:
    '''Test d'analyse pour la classe.
    Avec une note d'information.
    '''
    def __init__(self):
        # Ceci n'est pas une docstring
        # d'un commentaire
        pass
"""
    temp_test_file = "temp_docstring_test_file.py"
    with open(temp_test_file, "w", encoding="utf-8") as f:
        f.write(test_file_content)

    logger.info(f"\n--- Test de fix_docstrings_apostrophes sur {temp_test_file} ---")
    success = fix_docstrings_apostrophes(temp_test_file)
    if success:
        logger.info(f"Correction terminée. Contenu du fichier {temp_test_file}:")
        with open(temp_test_file, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        logger.error(f"Échec de la correction pour {temp_test_file}.")

    # Nettoyage
    if os.path.exists(temp_test_file):
        os.remove(temp_test_file)