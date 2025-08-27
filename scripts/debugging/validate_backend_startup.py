import sys
import subprocess
from pathlib import Path

# --- Chargement de l'environnement ---
# Cette étape est cruciale pour s'assurer que .env est chargé et que
# le PYTHONPATH est correctement configuré AVANT tout autre import.
try:
    from scripts.utils.environment_loader import load_environment
    load_environment()
except ImportError:
    print("Erreur: Impossible d'importer 'environment_loader'.")
    print("Assurez-vous que 'scripts/utils/environment_loader.py' existe.")
    sys.exit(1)

# --- Imports restants (après chargement de l'environnement) ---
try:
    from scripts.orchestration.orchestrate_webapp_detached import create_backend_config
except ImportError as e:
    print(f"Erreur d'importation: {e}")
    print("Vérifiez que le fichier 'orchestrate_webapp_detached.py' existe bien dans 'scripts/orchestration'")
    sys.exit(1)

def main():
    """
    Lance le backend en avant-plan pour diagnostiquer les erreurs de démarrage.
    """
    print("--- Diagnostic du démarrage du backend ---")
    
    project_root = Path(__file__).resolve().parent.parent.parent
    backend_config = create_backend_config()
    command = backend_config.command
    # Forcer le répertoire de travail à la racine du projet pour assurer la résolution des modules
    working_dir = project_root
    
    print(f"Répertoire de travail: {working_dir}")
    print(f"Lancement de la commande : {' '.join(command)}")

    try:
        # Exécute la commande en avant-plan, en affichant la sortie en temps réel.
        # Le processus s'exécutera jusqu'à ce qu'il soit interrompu (Ctrl+C) ou qu'il plante.
        subprocess.run(command, cwd=working_dir, check=True)
    except subprocess.CalledProcessError as e:
        print(f"--- Le processus a échoué avec le code de sortie {e.returncode} ---")
    except FileNotFoundError:
        print(f"--- ERREUR: La commande '{command[0]}' est introuvable. ---")
        print("Vérifiez que le chemin vers l'exécutable Python est correct dans `create_backend_config`.")
    except KeyboardInterrupt:
        print("\n--- Démarrage interrompu par l'utilisateur ---")

if __name__ == "__main__":
    main()