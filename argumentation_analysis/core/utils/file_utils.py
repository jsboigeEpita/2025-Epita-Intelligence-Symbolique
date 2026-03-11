# -*- coding: utf-8 -*-
"""
Utilitaires pour la manipulation de fichiers.

Ce module sert de point d'entrée principal pour les utilitaires de fichiers,
important des fonctionnalités spécifiques depuis des sous-modules dédiés.
Il centralise la logique de manipulation de fichiers pour le projet.
"""

import logging
from pathlib import (
    Path,
)  # Gardé pour type hinting si nécessaire, ou si des fonctions y restent
from typing import (
    List,
    Dict,
    Any,
    Optional,
    Union,
    Tuple,
)  # Gardé pour exposition potentielle ou type hinting

# Logger principal pour les utilitaires de fichiers du project_core
# Les sous-modules définissent leurs propres loggers spécifiques.
logger = logging.getLogger(__name__)  # __name__ sera 'project_core.utils.file_utils'
if (
    not logger.handlers and not logger.propagate
):  # Configuration de base si pas déjà configuré
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# --- Importation des fonctionnalités depuis les sous-modules ---

# Exposer toutes les fonctions des sous-modules pour la compatibilité ascendante
# et pour que les autres parties du projet puissent continuer à importer depuis file_utils.
from .file_loaders import *
from .file_savers import *
from .markdown_utils import *
from .path_operations import *

# Les constantes PATH_TYPE_* ont été déplacées dans path_operations.py

logger.info(
    "Module principal des utilitaires de fichiers (file_utils.py) initialisé et sous-modules importés."
)
