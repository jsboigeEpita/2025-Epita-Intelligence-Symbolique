import sys
import os

# Ajouter le répertoire du projet au PYTHONPATH
from pathlib import Path # Ajout pour la clarté
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


# Maintenant, essayons d'importer les modules nécessaires
try:
    from argumentation_analysis.core.jvm_setup import initialize_jvm
    print("Module jvm_setup importé avec succès")
except ImportError as e:
    print(f"Erreur lors de l'importation du module jvm_setup: {e}")

# Afficher le PYTHONPATH actuel
print("\nPYTHONPATH:")
for path in sys.path:
    print(f"  - {path}")

# Vérifier si le fichier .env existe
env_path = os.path.join('argumentation_analysis', '.env')
if os.path.exists(env_path):
    print(f"\nLe fichier .env existe à {env_path}")
else:
    print(f"\nLe fichier .env n'existe pas à {env_path}")

# Lister les fichiers dans le répertoire argumentation_analysis
print("\nFichiers dans le répertoire argumentation_analysis:")
try:
    files = os.listdir('argumentation_analysis')
    for file in files:
        print(f"  - {file}")
except Exception as e:
    print(f"Erreur lors de la lecture du répertoire: {e}")