# -*- coding: utf-8 -*-
"""Utilitaires pour la manipulation de fichiers."""

import json
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


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

def load_text_file(file_path: Path) -> Optional[str]:
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

def load_csv_file(file_path: Path) -> Optional[pd.DataFrame]:
    """
    Charge des données depuis un fichier CSV en utilisant pandas.

    Args:
        file_path (Path): Chemin vers le fichier CSV.

    Returns:
        Optional[pd.DataFrame]: DataFrame pandas contenant les données, ou None si erreur.
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
    except pd.errors.EmptyDataError:
        logger.warning(f"⚠️ Fichier CSV vide: {file_path}. Retour d'un DataFrame vide.")
        return pd.DataFrame() # Retourner un DataFrame vide pour un fichier CSV vide
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors du chargement du fichier CSV {file_path}: {e}", exc_info=True)
        return None