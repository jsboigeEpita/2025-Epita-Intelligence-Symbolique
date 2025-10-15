import sys
from pathlib import Path
from dotenv import load_dotenv
import os


def load_environment():
    """
    Charge le fichier .env et configure le PYTHONPATH pour l'ensemble du projet.
    Cette fonction est conçue pour être appelée au début de chaque script
    afin de garantir un environnement d'exécution cohérent.
    """
    # Chemin vers la racine du projet, calculé à partir de l'emplacement de ce script
    project_root = Path(__file__).resolve().parent.parent.parent

    # Chemin vers le fichier .env
    dotenv_path = project_root / ".env"

    # Chargement des variables d'environnement depuis le fichier .env
    # override=True garantit que les valeurs du .env écrasent les valeurs existantes
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path, override=True)
        # print(f"Variables d'environnement chargées depuis : {dotenv_path}")
    else:
        print(f"AVERTISSEMENT: Fichier .env introuvable à : {dotenv_path}")

    # Ajout de la racine du projet au PYTHONPATH si elle n'y est pas déjà.
    # Cela permet aux scripts de trouver les modules du projet
    # (par exemple, 'argumentation_analysis', 'project_core').
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        # print(f"Racine du projet ajoutée au PYTHONPATH : {project_root}")


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
