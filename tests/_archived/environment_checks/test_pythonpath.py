# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
# Déterminer la racine du projet par rapport à l'emplacement de ce fichier de test
# tests/environment_checks/test_pythonpath.py -> remonter de deux niveaux pour atteindre la racine
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# L'installation du package via `pip install -e .` devrait gérer l'accessibilité,
# mais cette modification assure le fonctionnement même sans installation en mode édition.
# Ce script est spécifiquement pour tester PYTHONPATH, cette modification est donc cruciale.

current_dir = Path.cwd()
print(f"Répertoire courant: {current_dir}")
print("\nPYTHONPATH:")
for path in sys.path:
    print(f"  - {path}")

try:
    import argumentation_analysis

    print("\nModule argumentation_analysis importé avec succès")
except ImportError as e:
    print(f"\nErreur lors de l'importation du module argumentation_analysis: {e}")

# Vérifier si le fichier .env existe
env_path = os.path.join("argumentation_analysis", ".env")
if os.path.exists(env_path):
    print(f"\nLe fichier .env existe à {env_path}")
else:
    print(f"\nLe fichier .env n'existe pas à {env_path}")
