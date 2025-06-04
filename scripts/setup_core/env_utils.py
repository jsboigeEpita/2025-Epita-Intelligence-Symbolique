import yaml
import os
from pathlib import Path

# Déterminer le répertoire racine du projet de manière robuste
# Ce script est dans scripts/setup_core, donc la racine est deux niveaux au-dessus.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def get_conda_env_name_from_yaml(env_file_path: Path = None) -> str:
    """
    Lit le nom de l'environnement Conda à partir du fichier environment.yml.

    Args:
        env_file_path (Path, optional): Chemin vers le fichier environment.yml.
                                         Par défaut, 'PROJECT_ROOT/environment.yml'.

    Returns:
        str: Le nom de l'environnement Conda.

    Raises:
        FileNotFoundError: Si le fichier environment.yml n'est pas trouvé.
        KeyError: Si la clé 'name' n'est pas trouvée dans le fichier YAML.
        yaml.YAMLError: Si le fichier YAML est malformé.
    """
    if env_file_path is None:
        env_file_path = PROJECT_ROOT / "environment.yml"

    if not env_file_path.is_file():
        raise FileNotFoundError(f"Le fichier d'environnement '{env_file_path}' n'a pas été trouvé.")

    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            env_config = yaml.safe_load(f)
        
        if env_config and 'name' in env_config:
            return env_config['name']
        else:
            raise KeyError(f"La clé 'name' est manquante ou le fichier YAML est vide dans '{env_file_path}'.")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Erreur lors de l'analyse du fichier YAML '{env_file_path}': {e}")
    except Exception as e:
        # Attraper d'autres exceptions potentielles (ex: problèmes de permission)
        raise RuntimeError(f"Une erreur inattendue est survenue lors de la lecture de '{env_file_path}': {e}")

if __name__ == '__main__':
    # Pour des tests rapides lors de l'exécution directe du script
    try:
        env_name = get_conda_env_name_from_yaml()
        print(f"Nom de l'environnement Conda (depuis environment.yml): {env_name}")
    except Exception as e:
        print(f"Erreur: {e}")