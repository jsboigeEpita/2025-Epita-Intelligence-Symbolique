# -*- coding: utf-8 -*-
"""
Utilitaires pour la manipulation de fichiers.

Ce module sert de point d'entrée principal pour les utilitaires de fichiers,
important des fonctionnalités spécifiques depuis des sous-modules dédiés.
Il centralise la logique de manipulation de fichiers pour le projet.
"""

import logging

# Logger principal pour les utilitaires de fichiers du project_core
# Les sous-modules définissent leurs propres loggers spécifiques.
logger = logging.getLogger(__name__)  # __name__ sera 'project_core.utils.file_utils'
if (
    not logger.handlers and not logger.propagate
):  # Configuration de base si pas déjà configurée
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# --- Importation des fonctionnalités depuis les sous-modules ---
# Surface explicite et finie : les star-imports précédents laissaient fuir
# tout nom public des feuilles — y compris le paquet PyPI `markdown`
# (importé par markdown_utils) — dans l'espace de noms de la façade (#2146).
from .file_loaders import (
    load_base_analysis_results,
    load_csv_file,
    load_document_content,
    load_extracts,
    load_json_file,
    load_text_file,
)
from .file_savers import save_json_file, save_text_file
from .markdown_utils import save_markdown_to_html
from .path_operations import (
    archive_file,
    check_path_exists,
    create_archive_path,
    sanitize_filename,
)

__all__ = [
    "archive_file",
    "check_path_exists",
    "create_archive_path",
    "load_base_analysis_results",
    "load_csv_file",
    "load_document_content",
    "load_extracts",
    "load_json_file",
    "load_text_file",
    "save_json_file",
    "save_markdown_to_html",
    "save_text_file",
    "sanitize_filename",
]

logger.info(
    "Module principal des utilitaires de fichiers (file_utils.py) initialisé et sous-modules importés."
)
