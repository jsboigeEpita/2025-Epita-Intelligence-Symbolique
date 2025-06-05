import yaml
import os
from pathlib import Path
import logging # Ajout pour le logger
import sys # Ajout pour le logger par défaut

# Logger par défaut pour ce module
module_logger_env_utils = logging.getLogger(__name__)
if not module_logger_env_utils.hasHandlers():
    _console_handler_env_utils = logging.StreamHandler(sys.stdout)
    _console_handler_env_utils.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (module default env_utils)'))
    module_logger_env_utils.addHandler(_console_handler_env_utils)
    module_logger_env_utils.setLevel(logging.INFO)

def _get_logger_env_utils(logger_instance=None):
    """Retourne le logger fourni ou le logger par défaut du module."""
    return logger_instance if logger_instance else module_logger_env_utils

# Déterminer le répertoire racine du projet de manière robuste
# Ce script est dans scripts/setup_core, donc la racine est deux niveaux au-dessus.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def get_conda_env_name_from_yaml(env_file_path: Path = None, logger_instance=None) -> str:
    """
    Lit le nom de l'environnement Conda à partir du fichier environment.yml.

    Args:
        env_file_path (Path, optional): Chemin vers le fichier environment.yml.
                                         Par défaut, 'PROJECT_ROOT/environment.yml'.
        logger_instance (logging.Logger, optional): Instance du logger à utiliser.

    Returns:
        str: Le nom de l'environnement Conda.

    Raises:
        FileNotFoundError: Si le fichier environment.yml n'est pas trouvé.
        KeyError: Si la clé 'name' n'est pas trouvée dans le fichier YAML.
        yaml.YAMLError: Si le fichier YAML est malformé.
    """
    logger = _get_logger_env_utils(logger_instance)
    if env_file_path is None:
        env_file_path = PROJECT_ROOT / "environment.yml"
    logger.debug(f"Attempting to read Conda env name from: {env_file_path}")

    if not env_file_path.is_file():
        logger.error(f"Environment file '{env_file_path}' not found.")
        raise FileNotFoundError(f"Le fichier d'environnement '{env_file_path}' n'a pas été trouvé.")

    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            env_config = yaml.safe_load(f)
        
        if env_config and 'name' in env_config:
            env_name = env_config['name']
            logger.debug(f"Successfully read env name '{env_name}' from {env_file_path}")
            return env_name
        else:
            logger.error(f"Key 'name' is missing or YAML file is empty in '{env_file_path}'.")
            raise KeyError(f"La clé 'name' est manquante ou le fichier YAML est vide dans '{env_file_path}'.")
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file '{env_file_path}': {e}", exc_info=True)
        raise yaml.YAMLError(f"Erreur lors de l'analyse du fichier YAML '{env_file_path}': {e}")
    except Exception as e:
        logger.error(f"Unexpected error reading '{env_file_path}': {e}", exc_info=True)
        raise RuntimeError(f"Une erreur inattendue est survenue lors de la lecture de '{env_file_path}': {e}")

import stat # Ajout pour handle_remove_readonly_retry
import time # Ajout pour handle_remove_readonly_retry

def handle_remove_readonly_retry(func, path, exc_info):
    """
    Error handler for shutil.rmtree.

    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries the removal.
    If the error is for another reason it re-raises the error.
    
    Usage: shutil.rmtree(path, onerror=handle_remove_readonly_retry)
    """
    # exc_info est un tuple (type, value, traceback)
    excvalue = exc_info[1]
    # Tenter de gérer les erreurs de permission spécifiquement pour les opérations de suppression
    if func in (os.rmdir, os.remove, os.unlink) and isinstance(excvalue, PermissionError):
        print(f"[DEBUG_ROO_HANDLE_REMOVE] PermissionError for {path} with {func.__name__}. Attempting to change permissions and retry.")
        try:
            # Tenter de rendre le fichier/répertoire accessible en écriture
            # S_IWRITE est obsolète, utiliser S_IWUSR pour l'utilisateur
            current_permissions = os.stat(path).st_mode
            new_permissions = current_permissions | stat.S_IWUSR | stat.S_IRUSR # Assurer lecture et écriture pour l'utilisateur
            
            # Pour les répertoires, il faut aussi s'assurer qu'ils sont exécutables pour y accéder
            if stat.S_ISDIR(current_permissions):
                new_permissions |= stat.S_IXUSR

            os.chmod(path, new_permissions)
            print(f"[DEBUG_ROO_HANDLE_REMOVE] Changed permissions for {path} to {oct(new_permissions)}.")
            
            # Réessayer l'opération
            func(path)
            print(f"[DEBUG_ROO_HANDLE_REMOVE] Successfully executed {func.__name__} on {path} after chmod.")
        except Exception as e_chmod_retry:
            print(f"[WARNING_ROO_HANDLE_REMOVE] Failed to execute {func.__name__} on {path} even after chmod: {e_chmod_retry}")
            # Optionnel: ajouter un petit délai et une nouvelle tentative
            time.sleep(0.2) # Augmenté légèrement le délai
            try:
                func(path)
                print(f"[DEBUG_ROO_HANDLE_REMOVE] Successfully executed {func.__name__} on {path} after chmod and delay.")
            except Exception as e_retry_final:
                 print(f"[ERROR_ROO_HANDLE_REMOVE] Still failed to execute {func.__name__} on {path} after chmod and delay: {e_retry_final}. Raising original error.")
                 raise excvalue # Relancer l'erreur originale si la correction échoue
    else:
        # Si ce n'est pas une PermissionError ou si la fonction n'est pas celle attendue, relancer.
        # Ceci est important pour ne pas masquer d'autres types d'erreurs.
        print(f"[DEBUG_ROO_HANDLE_REMOVE] Error not handled by custom logic for {path} with {func.__name__} (Error: {excvalue}). Raising original error.")
        raise excvalue

if __name__ == '__main__':
    # Pour des tests rapides lors de l'exécution directe du script
    try:
        env_name = get_conda_env_name_from_yaml()
        print(f"Nom de l'environnement Conda (depuis environment.yml): {env_name}")
    except Exception as e:
        print(f"Erreur: {e}")