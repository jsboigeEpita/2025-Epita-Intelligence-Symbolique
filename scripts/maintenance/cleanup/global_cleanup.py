#!/usr/bin/env python3
"""
Script de nettoyage global du projet d'analyse argumentative.

Ce script effectue les opérations suivantes :
1. Identifie et supprime les fichiers temporaires ou redondants à la racine du projet
2. Fusionne les dossiers results/ en un seul dossier bien organisé
3. Classe les résultats par type d'analyse et par corpus
4. Crée une structure de dossiers claire et logique
5. Génère un fichier README.md pour le dossier results/ qui documente la structure et le contenu
import argumentation_analysis.core.environment
6. Produit un rapport de nettoyage indiquant les actions effectuées

Options:
--dry-run : Affiche les actions sans les exécuter
--verbose : Affiche des informations détaillées
--force : Exécute le nettoyage sans demander de confirmation
"""

import os
import sys
import shutil
import argparse
import re
import json
import glob
from pathlib import Path
from datetime import datetime
import logging
import hashlib

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
RESULTS_DIR = PROJECT_ROOT / "results"
ARCHIVES_DIR = PROJECT_ROOT / "_archives"
TEMP_EXTRACTS_DIR = PROJECT_ROOT / "temp_extracts"
BACKUP_DIR = ARCHIVES_DIR / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("global_cleanup")

# Patterns de fichiers temporaires à supprimer
TEMP_FILE_PATTERNS = [
    "*.tmp",
    "*.bak",
    "*.swp",
    "*.swo",
    "*~",
    "Thumbs.db",
    ".DS_Store",
    "*.pyc",
    "__pycache__",
    ".ipynb_checkpoints",
    "*.log"
]