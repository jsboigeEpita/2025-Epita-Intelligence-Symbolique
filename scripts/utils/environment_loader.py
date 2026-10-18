import sys
from pathlib import Path
import os


def load_environment():
    """
    Charge le fichier .env et configure le PYTHONPATH pour l'ensemble du projet.
    Cette fonction est conçue pour être appelée au début de chaque script
    afin de garantir un environnement d'exécution cohérent.
    """
    # Chemin vers la racine du projet, calculé à partir de l'emplacement de ce script
    project_root = Path(__file__).resolve().parent.parent.parent

    # Ajout de la racine du projet au PYTHONPATH si elle n'y est pas déjà.
    # D'abord : le loader unique vit sous la racine, il doit être importable
    # avant de charger quoi que ce soit.
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Chargement des variables d'environnement via le loader unique (#3062) :
    # la valeur posée par l'appelant gagne, même vide (#2472) — plus
    # d'override=True qui recharge le .env par-dessus une session neutralisée.
    from argumentation_analysis.config.env_loader import EnvironmentManager

    manager = EnvironmentManager()
    if not manager.dotenv_path:
        print(f"AVERTISSEMENT: Fichier .env introuvable à : {project_root / '.env'}")


if __name__ == "__main__":
    # Ce bloc est exécuté si le script est appelé directement.
    # Il sert de test rapide pour s'assurer que le chargement fonctionne.
    print("--- Test du chargeur d'environnement ---")
    load_environment()
    print("Environnement chargé.")

    # Affiche quelques variables clés pour vérification
    print("\nVérification des variables clés :")
    conda_env = os.getenv("CONDA_ENV_NAME", "Non défini")
    java_home = os.getenv("JAVA_HOME", "Non défini")

    print(f"  Nom de l'environnement Conda : {conda_env}")
    print(f"  JAVA_HOME : {java_home}")

    print("\nContenu partiel du PYTHONPATH :")
    for i, path in enumerate(sys.path[:3]):
        print(f"  {i}: {path}")
