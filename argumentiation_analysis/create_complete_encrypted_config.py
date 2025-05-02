#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script wrapper pour créer un fichier encrypté complet qui embarque les sources avec la configuration des extraits.
Ce script appelle la version originale dans le répertoire agents.
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire du projet au chemin de recherche des modules
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

# Importer le script original
from agents.create_complete_encrypted_config import main

if __name__ == "__main__":
    # Exécuter la fonction principale du script original
    main()
