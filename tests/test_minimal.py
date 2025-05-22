"""
Script de test minimal pour vérifier l'installation du projet argumentation_analysis.
Ce script évite les importations circulaires en important uniquement les modules essentiels.
"""

import os
import sys

# Ajouter le répertoire du projet au PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print(f"Répertoire courant: {current_dir}")
print("\nPYTHONPATH:")
for path in sys.path:
    print(f"  - {path}")

# Vérifier si le fichier .env existe
env_path = os.path.join('argumentation_analysis', '.env')
if os.path.exists(env_path):
    print(f"\nLe fichier .env existe à {env_path}")
else:
    print(f"\nLe fichier .env n'existe pas à {env_path}")

# Tester l'importation de modules individuels sans dépendances circulaires
print("\nTest d'importation de modules individuels:")

try:
    from argumentation_analysis.core import state_manager
    print("✓ Module state_manager importé avec succès")
except ImportError as e:
    print(f"✗ Erreur lors de l'importation du module state_manager: {e}")

try:
    from argumentation_analysis.utils import text_utils
    print("✓ Module text_utils importé avec succès")
except ImportError as e:
    print(f"✗ Erreur lors de l'importation du module text_utils: {e}")

try:
    import jpype
    print("✓ Module jpype importé avec succès")
except ImportError as e:
    print(f"✗ Erreur lors de l'importation du module jpype: {e}")

try:
    from cryptography.fernet import Fernet
    print("✓ Module cryptography.fernet importé avec succès")
except ImportError as e:
    print(f"✗ Erreur lors de l'importation du module cryptography.fernet: {e}")

try:
    import semantic_kernel
    print("✓ Module semantic_kernel importé avec succès")
except ImportError as e:
    print(f"✗ Erreur lors de l'importation du module semantic_kernel: {e}")

print("\nTest terminé.")