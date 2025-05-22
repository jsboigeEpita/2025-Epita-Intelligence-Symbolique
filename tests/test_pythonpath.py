import sys
import os

# Ajouter le répertoire du projet au PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

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
env_path = os.path.join('argumentation_analysis', '.env')
if os.path.exists(env_path):
    print(f"\nLe fichier .env existe à {env_path}")
else:
    print(f"\nLe fichier .env n'existe pas à {env_path}")