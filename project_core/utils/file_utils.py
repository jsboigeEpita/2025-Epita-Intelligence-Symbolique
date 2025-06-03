# -*- coding: utf-8 -*-
"""
Utilitaires pour la manipulation de fichiers.

Ce module fournit un ensemble de fonctions pour effectuer des opérations courantes
sur les fichiers, telles que le chargement et la sauvegarde de données dans
différents formats (JSON, texte, CSV), la sanitization des noms de fichiers,
la vérification de l'existence de chemins, la création de chemins d'archive,
l'archivage de fichiers, et la conversion de Markdown en HTML.
Il vise à centraliser la logique de manipulation de fichiers pour le projet.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union # Ajout de Union
import logging
from datetime import datetime # Ajout de datetime
import re
import shutil
import sys
import markdown

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

    :param filename: La chaîne de caractères originale du nom de fichier.
    :type filename: str
    :param max_len: Longueur maximale du nom de fichier final.
    :type max_len: int, optional
    :return: Le nom de fichier nettoyé.
    :rtype: str
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


def load_json_file(file_path: Path) -> Optional[Union[List[Dict[str, Any]], Dict[str, Any]]]:
    """
    Charge des données depuis un fichier JSON.

    Gère les listes ou dictionnaires à la racine du JSON.
    Tente également de parser le contenu si le JSON initial est une chaîne (double encodage).

    :param file_path: Chemin vers le fichier JSON.
    :type file_path: Path
    :return: Données chargées (liste de dictionnaires ou dictionnaire) ou None si une erreur survient
             (fichier non trouvé, erreur de décodage JSON, type de données inattendu).
    :rtype: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]]
    :raises FileNotFoundError: Techniquement gérée en interne et logguée, retourne None.
    :raises json.JSONDecodeError: Techniquement gérée en interne et logguée, retourne None.
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
            logger.error(f"Type de données inattendu ({type(data)}) après chargement de {file_path}. Attendu List ou Dict. Retour de None.")
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

    Cette fonction est un wrapper autour de `load_json_file` pour maintenir
    la compatibilité avec le code existant qui attend spécifiquement une liste d'extraits.
    Elle assure que le résultat est une liste, retournant une liste vide en cas d'erreur
    ou si les données chargées ne sont pas une liste.

    :param file_path: Chemin vers le fichier JSON contenant les extraits déchiffrés.
    :type file_path: Path
    :return: Liste des extraits déchiffrés, ou une liste vide si une erreur de chargement
             survient ou si le format des données n'est pas une liste.
    :rtype: List[Dict[str, Any]]
    """
    data = load_json_file(file_path)
    if isinstance(data, list):
        return data
    elif data is None: # Erreur de chargement gérée par load_json_file
        return []
    else:
        logger.warning(f"Les données chargées depuis {file_path} ne sont pas une liste comme attendu pour des extraits. Type: {type(data)}. Retour d'une liste vide.")
        return []
def load_base_analysis_results(file_path: Path) -> List[Dict[str, Any]]:
    """
    Charge les résultats de l'analyse rhétorique de base depuis un fichier JSON.

    Cette fonction est un wrapper autour de `load_json_file` pour maintenir
    la compatibilité avec le code existant qui attend spécifiquement une liste de résultats.
    Elle assure que le résultat est une liste, retournant une liste vide en cas d'erreur
    ou si les données chargées ne sont pas une liste.

    :param file_path: Chemin vers le fichier JSON contenant les résultats d'analyse.
    :type file_path: Path
    :return: Liste des résultats d'analyse, ou une liste vide si une erreur de chargement
             survient ou si le format des données n'est pas une liste.
    :rtype: List[Dict[str, Any]]
    """
    data = load_json_file(file_path)
    if isinstance(data, list):
        logger.info(f"Données de type liste chargées pour les résultats d'analyse de base depuis {file_path}")
        return data
    elif data is None: # Erreur de chargement gérée par load_json_file
        return []
    else:
        logger.warning(f"Les données chargées depuis {file_path} pour les résultats d'analyse de base ne sont pas une liste. Type: {type(data)}. Retour d'une liste vide.")
        return []

def load_text_file(file_path: Path, encoding: str = "utf-8") -> Optional[str]:
    """
    Charge le contenu d'un fichier texte.

    :param file_path: Chemin vers le fichier texte.
    :type file_path: Path
    :param encoding: Encodage du fichier.
    :type encoding: str, optional
    :return: Contenu du fichier sous forme de chaîne de caractères, ou None si une erreur survient
             (fichier non trouvé, erreur de décodage, erreur d'E/S).
    :rtype: Optional[str]
    :raises FileNotFoundError: Gérée en interne, retourne None.
    :raises UnicodeDecodeError: Gérée en interne, retourne None.
    :raises IOError: Gérée en interne, retourne None.
    """
    logger.info(f"Chargement du fichier texte {file_path} avec l'encodage {encoding}")
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        logger.info(f"✅ Fichier texte {file_path} chargé avec succès")
        return content
    except FileNotFoundError:
        logger.error(f"❌ Fichier non trouvé: {file_path}")
        return None
    except UnicodeDecodeError as e:
        logger.error(f"❌ Erreur de décodage Unicode lors du chargement du fichier {file_path} avec l'encodage {encoding}: {e}", exc_info=True)
        return None
    except IOError as e: # Inclut FileNotFoundError mais est plus générique pour les problèmes d'IO
        logger.error(f"❌ Erreur d'E/S lors du chargement du fichier {file_path}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors du chargement du fichier texte {file_path}: {e}", exc_info=True)
        return None

def load_csv_file(file_path: Path) -> Optional[Any]: # Remplacement de pd.DataFrame par Any pour éviter l'import de pandas ici
    """
    Charge des données depuis un fichier CSV en utilisant la bibliothèque pandas.

    Si pandas n'est pas installé, une erreur est logguée et None est retourné.

    :param file_path: Chemin vers le fichier CSV.
    :type file_path: Path
    :return: Un DataFrame pandas contenant les données du fichier CSV.
             Retourne un DataFrame vide si le fichier CSV est vide.
             Retourne None si pandas n'est pas installé, si le fichier n'est pas trouvé,
             ou en cas d'autre erreur de chargement.
    :rtype: Optional[Any]
    :raises ImportError: Si pandas n'est pas installé (gérée en interne, retourne None).
    :raises FileNotFoundError: Gérée en interne, retourne None.
    :raises pd.errors.EmptyDataError: Gérée en interne, retourne un DataFrame vide.
    """
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
def save_json_file(file_path: Path, data: Any, indent: int = 4) -> bool:
    """
    Sauvegarde des données Python dans un fichier JSON.

    Crée les répertoires parents si nécessaire.

    :param file_path: Chemin complet du fichier où sauvegarder les données JSON.
    :type file_path: Path
    :param data: Les données Python (par exemple, dict, list) à sérialiser en JSON.
    :type data: Any
    :param indent: Niveau d'indentation pour le formatage du JSON.
    :type indent: int, optional
    :return: True si la sauvegarde a réussi, False sinon.
    :rtype: bool
    :raises IOError: Si une erreur d'E/S se produit (gérée en interne, retourne False).
    :raises TypeError: Si les données ne sont pas sérialisables en JSON (gérée en interne, retourne False).
    """
    logger.info(f"Tentative de sauvegarde des données JSON dans {file_path} avec une indentation de {indent}")
    try:
        # S'assurer que le répertoire parent existe
        file_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Répertoire parent {file_path.parent} pour la sauvegarde JSON vérifié/créé.")

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        logger.info(f"✅ Données JSON sauvegardées avec succès dans {file_path}")
        return True
    except IOError as e:
        logger.error(f"❌ Erreur d'E/S lors de la sauvegarde du fichier JSON {file_path}: {e}", exc_info=True)
        return False
    except TypeError as e:
        logger.error(f"❌ Erreur de type lors de la sérialisation JSON pour le fichier {file_path} (données non sérialisables?): {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors de la sauvegarde du fichier JSON {file_path}: {e}", exc_info=True)
        return False
import markdown # Ajout de l'import manquant pour la nouvelle fonction

def save_markdown_to_html(markdown_content: str, output_path: Path) -> bool:
    """
    Convertit une chaîne de contenu Markdown en HTML et sauvegarde le résultat dans un fichier.

    Le document HTML généré inclut un style CSS de base pour une meilleure lisibilité.
    Les extensions Markdown 'tables' et 'fenced_code' sont activées.
    Crée les répertoires parents si nécessaire.

    :param markdown_content: La chaîne de contenu Markdown à convertir.
    :type markdown_content: str
    :param output_path: Le chemin du fichier où sauvegarder le contenu HTML.
    :type output_path: Path
    :return: True si la conversion et la sauvegarde ont réussi, False sinon.
    :rtype: bool
    :raises Exception: Si une erreur se produit pendant la conversion ou la sauvegarde (gérée en interne, retourne False).
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

def convert_markdown_file_to_html(markdown_file_path: Path, output_html_path: Path, visualization_dir: Optional[Path] = None) -> bool:
    """
    Lit un fichier Markdown, le convertit en HTML et le sauvegarde.

    Utilise la fonction save_markdown_to_html pour la conversion et la sauvegarde.
    Le paramètre visualization_dir n'est pas directement utilisé dans cette version
    mais est conservé pour la compatibilité de signature si la logique d'intégration
    des visualisations devait être ajoutée ici.

    :param markdown_file_path: Chemin vers le fichier Markdown source.
    :type markdown_file_path: Path
    :param output_html_path: Chemin vers le fichier HTML de sortie.
    :type output_html_path: Path
    :param visualization_dir: Chemin vers un répertoire de visualisations (actuellement non utilisé).
    :type visualization_dir: Optional[Path], optional
    :return: True si la conversion et la sauvegarde ont réussi, False sinon.
    :rtype: bool
    """
    logger.info(f"Tentative de conversion du fichier Markdown {markdown_file_path} en HTML vers {output_html_path}.")
    
    markdown_content = load_text_file(markdown_file_path)
    if markdown_content is None:
        logger.error(f"Impossible de lire le contenu du fichier Markdown: {markdown_file_path}")
        return False
    
    # Le paramètre visualization_dir est présent pour correspondre à la signature du candidat #25.
    # Si les visualisations doivent être intégrées dans le HTML, la logique devrait être ajoutée ici
    # ou dans save_markdown_to_html. Pour l'instant, il n'est pas utilisé.
    if visualization_dir:
        logger.debug(f"Le répertoire de visualisations {visualization_dir} est fourni mais non utilisé activement dans cette version de la conversion.")

    return save_markdown_to_html(markdown_content, output_html_path)

import sys # Ajout de l'import sys pour sys.exit

def check_path_exists(path: Path, path_type: str = "file") -> bool:
    """
    Vérifie si un chemin existe et correspond au type spécifié (fichier ou répertoire).

    En cas d'échec de la validation (chemin non trouvé, type incorrect),
    un message d'erreur critique est loggué et le script est arrêté via `sys.exit(1)`.

    :param path: L'objet Path à vérifier.
    :type path: Path
    :param path_type: Le type de chemin attendu. Peut être "file" ou "directory".
    :type path_type: str, optional
    :return: True si le chemin existe et correspond au type attendu.
             Ne retourne jamais False car le script s'arrête en cas d'erreur de validation.
    :rtype: bool
    :raises SystemExit: Si la validation échoue (chemin non trouvé ou type incorrect).
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

    file_name = source_file_path.name
    
    # Obtenir les noms des répertoires parents pertinents
    # source_file_path.parents est une séquence: (parent, grand-parent, ...)
    # parents[0] est le parent direct, parents[1] le parent du parent, etc.
    # On veut les `preserve_levels` derniers noms de répertoires.
    
    parent_names_to_preserve = []
    if preserve_levels > 0 and source_file_path.parents:
        # Nombre de parents disponibles
        num_available_parents = len(source_file_path.parents)
        # Nombre de niveaux à effectivement prendre (ne peut excéder num_available_parents)
        levels_to_take = min(preserve_levels, num_available_parents)
        
        # Prendre les `levels_to_take` premiers parents de la liste `parents`
        # et inverser pour avoir l'ordre correct (du plus éloigné au plus proche)
        # puis prendre leurs noms.
        # Exemple: source = Path("a/b/c/d/file.txt"), preserve_levels = 2
        # parents = (PosixPath('a/b/c/d'), PosixPath('a/b/c'), PosixPath('a/b'), PosixPath('a'))
        # levels_to_take = 2
        # parents_to_consider = [PosixPath('a/b/c/d'), PosixPath('a/b/c')]
        # parent_names_to_preserve = ['c', 'd'] (après .name et inversion)
        
        # On prend les `levels_to_take` parents les plus proches du fichier.
        # parents[0] est le parent direct, parents[1] celui d'avant, etc.
        # On veut les noms de parents[levels_to_take-1], ..., parents[0]
        for i in range(levels_to_take):
            parent_names_to_preserve.append(source_file_path.parents[i].name)
        parent_names_to_preserve.reverse() # Mettre dans l'ordre correct de l'arborescence

    if parent_names_to_preserve:
        archive_sub_path = Path(*parent_names_to_preserve) / file_name
    else:
        archive_sub_path = Path(file_name)

    destination_path = base_archive_dir / archive_sub_path

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Chemin d'archive généré : {destination_path}")
    return destination_path
#    return True # Cette ligne semble être une erreur, commentée

def archive_file(source_path: Path, archive_path: Path) -> bool:
    """
    Archive un fichier en le déplaçant de `source_path` vers `archive_path`.

    Cette fonction s'assure que le répertoire parent de `archive_path` existe,
    le créant si nécessaire. Elle déplace ensuite le fichier source vers
    le chemin d'archivage.

    :param source_path: Le chemin complet du fichier source à archiver.
    :type source_path: Path
    :param archive_path: Le chemin complet de destination pour l'archivage.
                         Le répertoire parent sera créé s'il n'existe pas.
    :type archive_path: Path
    :return: True si l'archivage (déplacement) a réussi, False sinon.
    :rtype: bool
    :raises FileNotFoundError: Si le fichier source n'existe pas (gérée en interne, retourne False).
    :raises PermissionError: Si les permissions sont insuffisantes (gérée en interne, retourne False).
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

    Supporte les fichiers avec les extensions `.txt` et `.md` en utilisant `load_text_file`.
    Pour les autres types de fichiers, un avertissement est loggué et None est retourné.

    :param file_path: Chemin vers le fichier document.
    :type file_path: Path
    :return: Contenu du fichier sous forme de chaîne de caractères, ou None si le type de fichier
             n'est pas supporté, si le chemin n'est pas un fichier, ou en cas d'erreur de lecture.
    :rtype: Optional[str]
    """
    logger.info(f"Tentative de chargement du contenu du document depuis {file_path}")
    if not file_path.is_file():
        logger.error(f"❌ Le chemin spécifié n'est pas un fichier : {file_path}")
        return None

    file_extension = file_path.suffix.lower()

    if file_extension in ['.txt', '.md']:
        logger.debug(f"Chargement du fichier {file_extension} : {file_path} via load_text_file.")
        return load_text_file(file_path)
    else:
        logger.warning(f"Type de fichier non supporté '{file_extension}' pour le chargement direct de document : {file_path}. Seuls .txt et .md sont gérés par cette fonction.")
        return None
def save_text_file(file_path: Path, content: str, encoding: str = "utf-8") -> bool:
    """
    Sauvegarde du contenu textuel dans un fichier.

    Crée les répertoires parents si nécessaire.

    :param file_path: Chemin complet du fichier où sauvegarder le contenu.
    :type file_path: Path
    :param content: Contenu textuel à sauvegarder.
    :type content: str
    :param encoding: Encodage du fichier.
    :type encoding: str, optional
    :return: True si la sauvegarde a réussi, False sinon.
    :rtype: bool
    :raises IOError: Si une erreur d'E/S se produit (gérée en interne, retourne False).
    :raises UnicodeEncodeError: Si une erreur d'encodage se produit (gérée en interne, retourne False).
    """
    logger.info(f"Tentative de sauvegarde du contenu dans {file_path} avec l'encodage {encoding}")
    try:
        # S'assurer que le répertoire parent existe
        file_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Répertoire parent {file_path.parent} pour la sauvegarde vérifié/créé.")

        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        logger.info(f"✅ Contenu sauvegardé avec succès dans {file_path}")
        return True
    except IOError as e:
        logger.error(f"❌ Erreur d'E/S lors de la sauvegarde du fichier {file_path}: {e}", exc_info=True)
        return False
    except UnicodeEncodeError as e:
        logger.error(f"❌ Erreur d'encodage Unicode lors de la sauvegarde du fichier {file_path} avec l'encodage {encoding}: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors de la sauvegarde du fichier {file_path}: {e}", exc_info=True)
        return False

def save_temp_extracts_json(
    extract_definitions: List[Dict[str, Any]],
    base_temp_dir_name: str = "temp_extracts",
    filename_prefix: str = "extracts_decrypted_"
) -> Optional[Path]:
    """
    Sauvegarde les définitions d'extraits dans un fichier JSON temporaire avec horodatage.

    Crée un sous-répertoire temporaire (par défaut 'temp_extracts') dans le répertoire
    de travail courant s'il n'existe pas.

    Args:
        extract_definitions (List[Dict[str, Any]]): La liste des définitions d'extraits.
        base_temp_dir_name (str): Nom du répertoire de base pour les fichiers temporaires.
        filename_prefix (str): Préfixe pour le nom du fichier JSON.

    Returns:
        Optional[Path]: Le chemin complet vers le fichier JSON temporaire sauvegardé,
                        ou None en cas d'erreur.
    """
    if not isinstance(extract_definitions, list):
        logger.error("Les définitions d'extraits fournies ne sont pas une liste.")
        return None

    try:
        # Créer un répertoire temporaire dans le répertoire du projet (ou CWD)
        # Idéalement, le chemin racine du projet serait passé en argument pour plus de robustesse.
        # Pour l'instant, on utilise Path.cwd() comme base si un chemin absolu n'est pas donné.
        current_temp_dir = Path.cwd() / base_temp_dir_name # Path() crée un chemin relatif au CWD
        current_temp_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Répertoire temporaire pour les extraits: {current_temp_dir.resolve()}")
        
        # Créer un nom de fichier avec horodatage
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # Nécessite import datetime
        temp_file_path = current_temp_dir / f"{filename_prefix}{timestamp}.json"
        
        # Utiliser la fonction save_json_file existante pour la sauvegarde
        if save_json_file(temp_file_path, extract_definitions, indent=2):
            logger.info(f"✅ Définitions d'extraits sauvegardées avec succès dans {temp_file_path.resolve()}")
            return temp_file_path
        else:
            # save_json_file logue déjà l'erreur spécifique.
            logger.error(f"Échec de la sauvegarde des extraits temporaires dans {temp_file_path} via save_json_file.")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors de la création ou sauvegarde du fichier d'extraits temporaire: {e}", exc_info=True)
        return None