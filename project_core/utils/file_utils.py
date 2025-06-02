# -*- coding: utf-8 -*-
"""Utilitaires pour la manipulation de fichiers."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional # Ajout de Optional
import logging
import re # Ajout de l'import re
import shutil

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str, max_len: int = 255) -> str:
    """
    Nettoie une chaîne de caractères pour la transformer en un nom de fichier valide et sûr.

    Transformations appliquées :
    - Remplace les espaces et multiples underscores/tirets par un seul underscore.
    - Supprime les caractères non alphanumériques non sûrs (sauf underscores, tirets et points).
    - Convertit le nom de fichier en minuscules.
    - Supprime les points, underscores ou tirets en début ou fin de nom de fichier (avant l'extension).
    - Gère les extensions de manière plus robuste.
    - Tronque à une longueur maximale tout en essayant de préserver l'extension.

    Args:
        filename (str): La chaîne de caractères originale du nom de fichier.
        max_len (int, optional): Longueur maximale du nom de fichier final. Par défaut à 255.

    Returns:
        str: Le nom de fichier nettoyé.
    """
    if not filename:
        logger.warning("Tentative de nettoyer un nom de fichier vide. Retour de 'empty_filename'.")
        return "empty_filename"

    original_filename_for_log = filename # Garder une copie pour le log

    # Séparer le nom de base et l'extension (s'il y en a une)
    name_part, dot, extension_part = filename.rpartition('.')
    
    # Si pas de point, ou si le point est au début (fichier caché type .bashrc),
    # alors tout est considéré comme le nom.
    if not dot or (dot and not name_part and extension_part): # ex: "file", ".bashrc"
        name_to_sanitize = filename
        current_extension = ""
    else: # ex: "archive.tar.gz" -> name_part="archive.tar", extension_part="gz"
        name_to_sanitize = name_part
        current_extension = extension_part

    # 1. Remplacer les espaces et séquences de séparateurs par un seul underscore dans le nom
    sanitized_name = re.sub(r'[\s_.-]+', '_', name_to_sanitize)

    # 2. Supprimer les caractères non autorisés du nom (tout ce qui n'est pas alphanumérique ou underscore)
    sanitized_name = re.sub(r'[^\w_]', '', sanitized_name)

    # 3. Convertir le nom en minuscules
    sanitized_name = sanitized_name.lower()

    # 4. Supprimer les underscores en début ou fin du nom
    sanitized_name = re.sub(r'^_+|_+$', '', sanitized_name)

    # Traiter l'extension si elle existe
    if current_extension:
        # Supprimer les caractères non autorisés de l'extension (tout ce qui n'est pas alphanumérique)
        sanitized_extension = re.sub(r'[^\w]', '', current_extension).lower()
        if not sanitized_extension: # Si l'extension devient vide
            # On rattache ce qui restait de l'extension (avant sanitization) au nom
            sanitized_name = f"{sanitized_name}_{re.sub(r'[^a-zA-Z0-9_]', '', current_extension.lower())}"
            sanitized_name = re.sub(r'_+', '_', sanitized_name).strip('_') # Nettoyer encore
            current_extension = "" # Plus d'extension valide
        else:
            current_extension = sanitized_extension
            
    # Recomposer le nom de fichier
    if current_extension:
        final_filename = f"{sanitized_name}.{current_extension}"
    else:
        final_filename = sanitized_name

    # Assurer que le nom n'est pas vide après nettoyage (avant la troncature)
    if not sanitized_name: # Si le nom (sans extension) est devenu vide
        final_filename = f"default_filename{'.' + current_extension if current_extension else ''}"
        logger.warning(f"Le nom de base du fichier '{original_filename_for_log}' est devenu vide après nettoyage. Utilisation de '{final_filename}'.")


    # 5. Tronquer à une longueur maximale en préservant l'extension
    if len(final_filename) > max_len:
        if current_extension:
            # Laisse de la place pour le point et l'extension
            len_ext_plus_dot = len(current_extension) + 1
            # Si l'extension elle-même (avec le point) est plus longue que max_len,
            # ou si le nom doit être tronqué à 0 ou moins, on tronque brutalement.
            if len_ext_plus_dot >= max_len :
                 # Tenter de garder au moins une partie de l'extension si possible
                final_filename = final_filename[:max_len-1] + final_filename[-1] if max_len > 0 else ""

            else:
                name_part_truncated = final_filename[:max_len - len_ext_plus_dot]
                final_filename = f"{name_part_truncated}.{current_extension}"
        else:
            final_filename = final_filename[:max_len]
    
    # Ultime vérification pour un nom de fichier complètement vide
    if not final_filename:
        logger.error(f"La sanitization du nom de fichier '{original_filename_for_log}' a résulté en une chaîne vide même après troncature. Retour de 'error_empty_filename'.")
        return "error_empty_filename"

    logger.debug(f"Nom de fichier original: '{original_filename_for_log}', nettoyé: '{final_filename}'")
    return final_filename


def load_json_file(file_path: Path) -> List[Dict[str, Any]] | Dict[str, Any] | None:
    """
    Charge des données depuis un fichier JSON.
    Gère les listes ou dictionnaires à la racine du JSON.

    Args:
        file_path (Path): Chemin vers le fichier JSON.

    Returns:
        List[Dict[str, Any]] | Dict[str, Any] | None: Données chargées ou None si erreur.
    """
    logger.info(f"Chargement des données JSON depuis {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            loaded_initial_data = json.load(f)

        # Gérer le cas où le contenu JSON est lui-même une chaîne JSON (double encodage)
        if isinstance(loaded_initial_data, str):
            logger.info(f"Contenu de {file_path} est une chaîne, tentative de re-parse JSON.")
            try:
                data = json.loads(loaded_initial_data)
            except json.JSONDecodeError as e_inner:
                logger.error(f"❌ Erreur lors du re-parse de la chaîne JSON depuis {file_path}: {e_inner}")
                logger.debug(f"Contenu de la chaîne (premiers 500 caractères): {loaded_initial_data[:500]}")
                return None
        else:
            data = loaded_initial_data
        
        # Logique de log générique après chargement et parsing/re-parsing réussi
        if isinstance(data, list):
            logger.info(f"✅ {len(data)} éléments (liste) chargés avec succès depuis {file_path}")
        elif isinstance(data, dict):
            logger.info(f"✅ Dictionnaire chargé avec succès depuis {file_path}")
        else:
            # Ce cas ne devrait pas être atteint si json.load ou json.loads fonctionnent correctement
            # et que le JSON est valide (soit une liste, soit un dict à la racine).
            # Si 'data' n'est ni list ni dict ici, c'est inattendu.
            logger.warning(f"Données chargées depuis {file_path} ne sont ni une liste ni un dictionnaire. Type: {type(data)}. Contenu (premiers 500): {str(data)[:500]}")
            # Selon la politique de gestion d'erreur, on pourrait retourner None ici.
            # Pour l'instant, on retourne les données telles quelles, mais cela pourrait violer la signature de type.
            # Pour être plus strict et correspondre à la signature de type qui attend List ou Dict :
            logger.error(f"Type de données inattendu ({type(data)}) après chargement de {file_path}. Retour de None.")
            return None

        return data
    except FileNotFoundError:
        logger.error(f"❌ Fichier non trouvé: {file_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"❌ Erreur de décodage JSON dans {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors du chargement du fichier JSON {file_path}: {e}")
        return None

# Pour l'instant, je garde le nom load_extracts pour la compatibilité directe,
# mais l'objectif est d'unifier avec load_json_file.
# Cette fonction sera probablement renommée ou fusionnée plus tard.
def load_extracts(file_path: Path) -> List[Dict[str, Any]]:
    """
    Charge les extraits déchiffrés depuis un fichier JSON.
    (Wrapper temporaire pour load_json_file pour maintenir la compatibilité)

    Args:
        file_path (Path): Chemin vers le fichier JSON contenant les extraits déchiffrés

    Returns:
        List[Dict[str, Any]]: Liste des extraits déchiffrés, ou liste vide si erreur.
    """
    data = load_json_file(file_path)
    if isinstance(data, list):
        return data
    elif data is None: # Erreur de chargement gérée par load_json_file
        return []
    else:
        logger.warning(f"Les données chargées depuis {file_path} ne sont pas une liste comme attendu pour des extraits. Type: {type(data)}")
        # Retourner une liste vide si ce n'est pas le format attendu pour les "extracts"
        return []
def load_base_analysis_results(file_path: Path) -> List[Dict[str, Any]]:
    """
    Charge les résultats de l'analyse rhétorique de base depuis un fichier JSON.
    (Wrapper temporaire pour load_json_file pour maintenir la compatibilité)

    Args:
        file_path (Path): Chemin vers le fichier JSON contenant les résultats

    Returns:
        List[Dict[str, Any]]: Liste des résultats, ou liste vide si erreur.
    """
    data = load_json_file(file_path)
    if isinstance(data, list):
        # Le logger.info original mentionnait "résultats d'analyse de base chargés",
        # load_json_file logue déjà le succès du chargement du fichier.
        # On pourrait ajouter un log spécifique si le type est correct.
        logger.info(f"Données de type liste chargées pour les résultats d'analyse de base depuis {file_path}")
        return data
    elif data is None: # Erreur de chargement gérée par load_json_file
        return []
    else:
        logger.warning(f"Les données chargées depuis {file_path} pour les résultats d'analyse de base ne sont pas une liste. Type: {type(data)}")
        return []

def load_text_file(file_path: Path) -> Optional[str]: # Optional a été ajouté à l'import typing
    """
    Charge le contenu d'un fichier texte.

    Args:
        file_path (Path): Chemin vers le fichier texte.

    Returns:
        Optional[str]: Contenu du fichier, ou None si erreur.
    """
    logger.info(f"Chargement du fichier texte depuis {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"✅ Fichier texte chargé avec succès depuis {file_path}")
        return content
    except FileNotFoundError:
        logger.error(f"❌ Fichier non trouvé: {file_path}")
        return None
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors du chargement du fichier texte {file_path}: {e}", exc_info=True)
        return None

def load_csv_file(file_path: Path) -> Optional[Any]: # Remplacement de pd.DataFrame par Any pour éviter l'import de pandas ici
    """
    Charge des données depuis un fichier CSV en utilisant pandas.

    Args:
        file_path (Path): Chemin vers le fichier CSV.

    Returns:
        Optional[Any]: DataFrame pandas contenant les données, ou None si erreur.
    """
    # Vérifier si pandas est disponible, sinon logguer une erreur et retourner None.
    # Cela évite un ImportError si pandas n'est pas installé et que cette fonction est appelée.
    try:
        import pandas as pd
    except ImportError:
        logger.error("Le package 'pandas' est requis pour charger les fichiers CSV mais n'est pas installé.")
        logger.error("Veuillez installer pandas: pip install pandas")
        return None

    logger.info(f"Chargement des données CSV depuis {file_path}")
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"✅ Fichier CSV chargé avec succès ({len(df)} lignes) depuis {file_path}")
        return df
    except FileNotFoundError:
        logger.error(f"❌ Fichier CSV non trouvé: {file_path}")
        return None
    except pd.errors.EmptyDataError: # type: ignore
        logger.warning(f"⚠️ Fichier CSV vide: {file_path}. Retour d'un DataFrame vide.")
        return pd.DataFrame() # Retourner un DataFrame vide pour un fichier CSV vide
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors du chargement du fichier CSV {file_path}: {e}", exc_info=True)
        return None
import markdown # Ajout de l'import manquant pour la nouvelle fonction

def save_markdown_to_html(markdown_content: str, output_path: Path) -> bool:
    """
    Convertit une chaîne de contenu Markdown en HTML et sauvegarde le résultat dans un fichier.

    Args:
        markdown_content (str): La chaîne de contenu Markdown à convertir.
        output_path (Path): Le chemin du fichier où sauvegarder le contenu HTML.

    Returns:
        bool: True si la sauvegarde a réussi, False sinon.
    """
    logger.info(f"Conversion du Markdown en HTML et sauvegarde vers {output_path}")
    try:
        # S'assurer que le répertoire parent existe
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        html_content = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
        
        # Ajouter un style CSS de base pour une meilleure lisibilité
        html_document = f"""
        &lt;!DOCTYPE html&gt;
        &lt;html lang="fr"&gt;
        &lt;head&gt;
            &lt;meta charset="UTF-8"&gt;
            &lt;meta name="viewport" content="width=device-width, initial-scale=1.0"&gt;
            &lt;title&gt;{output_path.stem}&lt;/title&gt;
            &lt;style&gt;
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #2c3e50;
                    margin-top: 24px;
                    margin-bottom: 16px;
                }}
                h1 {{
                    font-size: 2.5em;
                    border-bottom: 1px solid #eaecef;
                    padding-bottom: 0.3em;
                }}
                h2 {{
                    font-size: 2em;
                    border-bottom: 1px solid #eaecef;
                    padding-bottom: 0.3em;
                }}
                h3 {{
                    font-size: 1.5em;
                }}
                h4 {{
                    font-size: 1.25em;
                }}
                p, ul, ol {{
                    margin-bottom: 16px;
                }}
                a {{
                    color: #0366d6;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                pre {{
                    background-color: #f6f8fa;
                    border-radius: 3px;
                    padding: 16px;
                    overflow: auto;
                }}
                code {{
                    background-color: #f6f8fa;
                    border-radius: 3px;
                    padding: 0.2em 0.4em;
                    font-family: SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace;
                }}
                blockquote {{
                    border-left: 4px solid #dfe2e5;
                    padding: 0 1em;
                    color: #6a737d;
                    margin-left: 0;
                    margin-right: 0;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin-bottom: 16px;
                }}
                table, th, td {{
                    border: 1px solid #dfe2e5;
                }}
                th, td {{
                    padding: 8px 16px;
                    text-align: left;
                }}
                th {{
                    background-color: #f6f8fa;
                }}
                tr:nth-child(even) {{
                    background-color: #f6f8fa;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                }}
            &lt;/style&gt;
        &lt;/head&gt;
        &lt;body&gt;
            {html_content}
        &lt;/body&gt;
        &lt;/html&gt;
        """
        with open(output_path, 'w', encoding='utf-8', errors="replace") as f:
            f.write(html_document)
        logger.info(f"✅ Contenu HTML sauvegardé avec succès dans {output_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de la conversion Markdown en HTML ou de la sauvegarde dans {output_path}: {e}", exc_info=True)
        return False
import sys # Ajout de l'import sys pour sys.exit

def check_path_exists(path: Path, path_type: str = "file") -> bool:
    """
    Vérifie si un chemin existe et correspond au type spécifié (fichier ou répertoire).

    En cas d'échec de la validation (chemin non trouvé, type incorrect),
    un message d'erreur critique est loggué et le script est arrêté via sys.exit(1).

    Args:
        path (Path): L'objet Path à vérifier.
        path_type (str, optional): Le type de chemin attendu.
                                   Peut être "file" ou "directory".
                                   Par défaut "file".

    Returns:
        bool: True si le chemin existe et correspond au type attendu.
              Ne retourne jamais False car le script s'arrête en cas d'erreur.
    
    Raises:
        SystemExit: Si la validation échoue.
    """
    logger.debug(f"Vérification de l'existence et du type pour le chemin : {path} (attendu: {path_type})")
    if not path.exists():
        logger.critical(f"❌ ERREUR CRITIQUE: Le chemin {path} n'existe pas.")
        sys.exit(1)

    if path_type == "file":
        if not path.is_file():
            logger.critical(f"❌ ERREUR CRITIQUE: Le chemin {path} existe mais n'est pas un fichier (attendu: fichier).")
            sys.exit(1)
        logger.info(f"✅ Le fichier {path} existe et est un fichier.")
    elif path_type == "directory":
        if not path.is_dir():
            logger.critical(f"❌ ERREUR CRITIQUE: Le chemin {path} existe mais n'est pas un répertoire (attendu: répertoire).")
            sys.exit(1)
        logger.info(f"✅ Le répertoire {path} existe et est un répertoire.")
    else:
        logger.critical(f"❌ ERREUR CRITIQUE: Type de chemin non supporté '{path_type}'. Utilisez 'file' ou 'directory'.")
        sys.exit(1)
    
def create_archive_path(base_archive_dir: Path, source_file_path: Path, preserve_levels: int = 2) -> Path:
    """
    Génère un chemin de destination complet pour archiver un fichier source.

    Cette fonction recrée une partie de l'arborescence du fichier source
    sous le répertoire d'archive de base. Le paramètre `preserve_levels`
    contrôle combien de niveaux de répertoires parents du fichier source
    sont conservés dans la structure d'archivage.

    Args:
        base_archive_dir (Path): Le répertoire de base pour les archives.
        source_file_path (Path): Le chemin complet du fichier source à archiver.
        preserve_levels (int, optional): Le nombre de niveaux de répertoires
                                         parents du fichier source à préserver
                                         dans le chemin d'archive. Par défaut à 2.
                                         Si preserve_levels est 0, seul le nom du fichier
                                         sera utilisé sous base_archive_dir.
                                         Si preserve_levels est supérieur ou égal au nombre
                                         de parents du fichier source, toute l'arborescence
                                         relative au point de montage du fichier source sera préservée.

    Returns:
        Path: Le chemin de destination complet pour le fichier archivé.

    Example:
        &gt;&gt;&gt; base = Path("archives")
        &gt;&gt;&gt; source = Path("data/raw/project_alpha/file.txt")
        &gt;&gt;&gt; create_archive_path(base, source, 2)
        Path('archives/project_alpha/file.txt') # Si 'data/raw' sont les niveaux supérieurs
        &gt;&gt;&gt; create_archive_path(base, source, 1)
        Path('archives/file.txt') # Si 'project_alpha' est le seul niveau préservé
        &gt;&gt;&gt; create_archive_path(base, source, 0)
        Path('archives/file.txt')
        &gt;&gt;&gt; source_short = Path("file.txt")
        &gt;&gt;&gt; create_archive_path(base, source_short, 2)
        Path('archives/file.txt')
    """
    logger.debug(
        f"Création du chemin d'archive pour {source_file_path} dans {base_archive_dir} "
        f"en préservant {preserve_levels} niveaux."
    )

    # Extrait les `preserve_levels` derniers composants du chemin parent du fichier source
    # et le nom du fichier lui-même.
    # source_file_path.parts donne un tuple des composants du chemin.
    # ex: ('data', 'raw', 'project_alpha', 'file.txt')
    # Si preserve_levels = 2, on veut garder 'project_alpha', 'file.txt'.
    # Les parents sont source_file_path.parents.
    # parents[0] est 'data/raw/project_alpha'
    # parents[1] est 'data/raw'
    # parents[preserve_levels-1] nous donnerait le parent à partir duquel commencer,
    # mais c'est plus simple de travailler avec les 'parts' du chemin.

    if preserve_levels < 0:
        logger.warning("preserve_levels ne peut pas être négatif. Utilisation de 0 à la place.")
        preserve_levels = 0

    # Les "parts" du chemin source, ex: ('/', 'data', 'raw', 'project_alpha', 'file.txt') ou ('data', 'raw', ...)
    source_parts = source_file_path.parts

    # Le nom du fichier est toujours le dernier élément
    file_name = source_file_path.name

    # Les parties parentes à considérer pour la préservation
    # Si source_parts = ('data', 'raw', 'project_alpha', 'file.txt'), parent_parts_to_consider = ('data', 'raw', 'project_alpha')
    parent_parts_to_consider = source_parts[:-1]

    if preserve_levels == 0:
        # Si 0 niveau à préserver, on met juste le fichier dans base_archive_dir
        archive_sub_path = Path(file_name)
    elif preserve_levels >= len(parent_parts_to_consider):
        # Si on demande de préserver plus de niveaux qu'il n'y en a (avant le nom du fichier),
        # on préserve toutes les parties parentes disponibles.
        # Par exemple, si source = 'project_alpha/file.txt' (len(parent_parts_to_consider) = 1)
        # et preserve_levels = 2, on garde 'project_alpha/file.txt'
        if parent_parts_to_consider:
            archive_sub_path = Path(*parent_parts_to_consider) / file_name
        else: # Cas où source_file_path est juste un nom de fichier, ex: "file.txt"
            archive_sub_path = Path(file_name)
    else:
        # On prend les `preserve_levels` derniers éléments des parties parentes,
        # puis on ajoute le nom du fichier.
        # Ex: parent_parts_to_consider = ('data', 'raw', 'project_alpha'), preserve_levels = 2
        # preserved_parent_parts = ('raw', 'project_alpha') -- NON, c'est l'inverse
        # On veut les N derniers *répertoires* du chemin source.
        # Path.parents est une séquence de chemins parents.
        # parents[0] = data/raw/project_alpha
        # parents[1] = data/raw
        # parents[n-1] = data
        # Si preserve_levels = 2, on veut les 2 derniers niveaux de l'arborescence du fichier source.
        # Donc, si source_file_path est 'a/b/c/d/file.txt' et preserve_levels = 2,
        # on veut 'd/file.txt' sous base_archive_dir.
        # Les 'niveaux' sont les noms des répertoires.
        # source_file_path.parent.name est 'd'
        # source_file_path.parent.parent.name est 'c'
        # On veut les `preserve_levels` derniers composants du chemin *avant* le nom du fichier.
        
        # Exemple: source_file_path = Path("data/raw/project_alpha/file.txt")
        # preserve_levels = 2
        # On veut garder "project_alpha/file.txt"
        # Les parties du chemin sont: ('data', 'raw', 'project_alpha', 'file.txt')
        # On ignore le nom du fichier pour l'instant: ('data', 'raw', 'project_alpha')
        # On prend les `preserve_levels` derniers éléments: ('project_alpha') si preserve_levels=1, ('raw', 'project_alpha') si preserve_levels=2
        # Non, c'est le nombre de *niveaux de répertoire* à partir de la fin.
        # Si source_file_path = data/raw/project_alpha/file.txt et preserve_levels = 2,
        # les parties à préserver sont project_alpha/file.txt.
        # C'est équivalent à prendre les `preserve_levels` derniers répertoires parents + le nom du fichier.
        
        # Une approche plus simple :
        # 1. Prendre le nom du fichier : source_file_path.name
        # 2. Prendre les `preserve_levels` noms de répertoires parents, en partant du plus proche du fichier.
        
        preserved_components = []
        current_parent = source_file_path.parent
        # On ne peut pas préserver plus de niveaux qu'il n'y a de parents.
        actual_levels_to_preserve = min(preserve_levels, len(source_file_path.parents))

        for i in range(actual_levels_to_preserve):
            if current_parent and current_parent.name: # S'assurer qu'on a un nom (pas la racine)
                preserved_components.insert(0, current_parent.name) # Insérer au début pour garder l'ordre
                current_parent = current_parent.parent
            else:
                break # On a atteint la racine ou un chemin sans nom

        if preserved_components:
            archive_sub_path = Path(*preserved_components) / file_name
        else:
            archive_sub_path = Path(file_name) # Si aucun parent n'a pu être préservé (ex: preserve_levels > 0 mais source est à la racine)

    destination_path = base_archive_dir / archive_sub_path

    # S'assurer que le répertoire de destination existe
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Chemin d'archive généré : {destination_path}")
    return destination_path
#    return True # Cette ligne semble être une erreur, commentée
import shutil

def archive_file(source_path: Path, archive_path: Path) -> bool:
    """
    Archive un fichier en le déplaçant de source_path vers archive_path.

    Cette fonction s'assure que le répertoire parent de archive_path existe,
    le créant si nécessaire. Elle déplace ensuite le fichier source vers
    le chemin d'archivage. Les erreurs potentielles, comme la non-existence
    du fichier source ou des problèmes de permissions, sont logguées.

    Args:
        source_path (Path): Le chemin complet du fichier source à archiver.
        archive_path (Path): Le chemin complet de destination pour l'archivage.

    Returns:
        bool: True si l'archivage a réussi, False sinon.
    """
    logger.info(f"Tentative d'archivage du fichier {source_path} vers {archive_path}")

    if not source_path.exists() or not source_path.is_file():
        logger.error(f"❌ Le fichier source {source_path} n'existe pas ou n'est pas un fichier.")
        return False

    try:
        # S'assurer que le répertoire parent de archive_path existe
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Répertoire parent {archive_path.parent} pour l'archive vérifié/créé.")

        # Déplacer le fichier
        shutil.move(str(source_path), str(archive_path))
        logger.info(f"✅ Fichier {source_path} archivé avec succès vers {archive_path}")
        return True
    except FileNotFoundError:
        # Ce cas devrait être couvert par la vérification initiale, mais inclus pour robustesse
        logger.error(f"❌ Erreur (FileNotFoundError) lors de la tentative d'archivage : {source_path} non trouvé.")
        return False
    except PermissionError:
        logger.error(f"❌ Erreur de permission lors de la tentative d'archivage de {source_path} vers {archive_path}.")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors de l'archivage du fichier {source_path} vers {archive_path}: {e}", exc_info=True)
        return False
def load_document_content(file_path: Path) -> Optional[str]:
    """
    Charge le contenu textuel d'un fichier document.

    Gère les fichiers .txt et .md. Pour les autres types de fichiers,
    un avertissement est loggué et None est retourné.

    Args:
        file_path (Path): Chemin vers le fichier document.

    Returns:
        Optional[str]: Contenu du fichier, ou None si le type de fichier n'est pas
                       supporté ou en cas d'erreur de lecture.
    """
    logger.info(f"Tentative de chargement du contenu du document depuis {file_path}")
    if not file_path.is_file():
        logger.error(f"❌ Le chemin spécifié n'est pas un fichier : {file_path}")
        return None

    file_extension = file_path.suffix.lower()

    if file_extension in ['.txt', '.md']:
        logger.debug(f"Chargement du fichier {file_extension} : {file_path}")
        return load_text_file(file_path)
    # elif file_extension == '.pdf':
    #     # La lecture de PDF peut nécessiter des bibliothèques spécifiques (ex: PyPDF2, pdfminer)
    #     # ou un service externe comme Tika.
    #     # Pour l'instant, nous ne gérons pas les PDF directement ici pour garder file_utils simple.
    #     # Cette logique est gérée ailleurs (par ex. via Tika dans argumentation_analysis.ui.utils)
    #     logger.warning(f"Le chargement direct de fichiers PDF n'est pas implémenté dans cette fonction ({file_path}). Utiliser un processeur de PDF dédié.")
    #     return None
    else:
        logger.warning(f"Type de fichier non supporté '{file_extension}' pour le chargement direct de document : {file_path}")
        return None