#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour initialiser le cache des textes à partir du fichier encrypté.
"""

import os
import sys
import hashlib
from pathlib import Path
from dotenv import load_dotenv

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Ajouter le répertoire grand-parent au chemin de recherche des modules
sys.path.append(str(parent_dir.parent))

# Charger les variables d'environnement
load_dotenv(override=True)

# Importer les modules nécessaires
from argumentation_analysis.ui.app import initialize_text_cache
from argumentation_analysis.ui.utils import get_cache_filepath

if __name__ == "__main__":
    print("\n=== Initialisation du cache des textes ===\n")
    
    # Vérifier si la variable d'environnement TEXT_CONFIG_PASSPHRASE est définie
    if not os.getenv("TEXT_CONFIG_PASSPHRASE"):
        print(f"⚠️ La variable d'environnement 'TEXT_CONFIG_PASSPHRASE' n'est pas définie.")
        print(f"   Veuillez la définir avant d'exécuter ce script.")
        sys.exit(1)
    
    # Initialiser le cache des textes
    initialize_text_cache()
    
    print("\n=== Initialisation terminée ===\n")