"""
Utilitaires pour l'interface utilisateur (UI) de l'analyse d'argumentation.

Ce module sert de point d'entrée principal pour les utilitaires UI,
important des fonctionnalités spécifiques depuis des sous-modules dédiés.
"""
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union # Gardé pour reconstruct_url et exposition potentielle

# Import config depuis le même package ui (peut être nécessaire pour des constantes globales)
from . import config as ui_config

# Logger principal pour les utilitaires UI
# Les sous-modules peuvent définir leurs propres loggers ou utiliser celui-ci s'il est importé.
utils_logger = logging.getLogger("App.UI.Utils")
if not utils_logger.handlers and not utils_logger.propagate:
     handler = logging.StreamHandler()
     formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
     handler.setFormatter(formatter)
     utils_logger.addHandler(handler)
     utils_logger.setLevel(logging.INFO)

# --- Fonctions Utilitaires de Base ---

def reconstruct_url(schema: str, host_parts: List[str], path: Optional[str]) -> Optional[str]:
    """Reconstruit une URL complète à partir de ses composants.

    :param schema: Le schéma de l'URL (par exemple, "http", "https").
    :type schema: str
    :param host_parts: Une liste des parties composant le nom d'hôte.
    :type host_parts: List[str]
    :param path: Le chemin de la ressource sur le serveur. Peut être None ou vide.
    :type path: Optional[str]
    :return: L'URL reconstruite, ou None si `schema` ou `host_parts` sont invalides.
    :rtype: Optional[str]
    """
    if not schema or not host_parts: return None
    host = ".".join(part for part in host_parts if part)
    current_path = path if path is not None else ""
    current_path = current_path if current_path.startswith('/') or not current_path else '/' + current_path
    if not current_path:
        current_path = "/"
    return f"{schema}://{host}{current_path}"

# --- Importation des fonctionnalités depuis les sous-modules ---

# Exposer toutes les fonctions des sous-modules pour la compatibilité ascendante
# ou importer sélectivement ce qui doit être public via ce module.
# Pour l'instant, j'importe tout avec '*' pour simplifier.

from .cache_utils import *
from .fetch_utils import *
from .verification_utils import *

# Les fonctions de chiffrement ont été déplacées vers project_core.utils.crypto_utils
# et ne sont plus directement exposées ou utilisées par ce module ui.utils central.
# Les appels se font via les modules qui en ont besoin (par ex. file_operations.py)

# Les fonctions load_extract_definitions et save_extract_definitions ont été déplacées
# vers argumentation_analysis/ui/file_operations.py.

utils_logger.info("Module principal des utilitaires UI (utils.py) initialisé et sous-modules importés.")
