# scripts/setup_core/manage_conda_env.py
import os
import subprocess
import re
import sys
import shutil
from pathlib import Path # Ajout pour la nouvelle logique de suppression
import json # Ajout pour parser la sortie de conda info --json
import logging # Ajout pour le logger

# Importer les utilitaires nécessaires depuis env_utils
import scripts.setup_core.env_utils as env_utils

# Logger par défaut pour ce module, si aucun n'est passé.
# Cela permet au module d'être utilisable indépendamment pour des tests, par exemple.
module_logger = logging.getLogger(__name__)
if not module_logger.hasHandlers():
    # Configurer un handler basique si aucun n'est configuré par le script appelant
    # pour éviter le message "No handlers could be found for logger..."
    _console_handler = logging.StreamHandler(sys.stdout)
    _console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (module default)'))
    module_logger.addHandler(_console_handler)
    module_logger.setLevel(logging.INFO) # Ou DEBUG si nécessaire pour les tests autonomes

# Forcer le nom de l'environnement Conda pour cette tâche spécifique
CONDA_ENV_NAME_DEFAULT = "projet-is" # Conserver pour référence si besoin
CONDA_ENV_NAME = "projet-is"
# Remplacé par logger.info dans la fonction setup_environment ou un appelant
# print(f"[INFO] Using Conda environment name: {CONDA_ENV_NAME} (Hardcoded for repair task)")
CONDA_ENV_FILE_NAME = "environment.yml"

def _get_logger(logger_instance=None):
    """Retourne le logger fourni ou le logger par défaut du module."""
    return logger_instance if logger_instance else module_logger

def _find_conda_executable(logger_instance=None):
    """Trouve l'exécutable Conda."""
    logger = _get_logger(logger_instance)
    conda_exe = shutil.which("conda")
    if conda_exe:
        return conda_exe
    
    # Vérifier les variables d'environnement courantes
    conda_root = os.environ.get("CONDA_ROOT")
    if conda_root:
        # Sur Windows, Conda est souvent dans CONDA_ROOT/Scripts/conda.exe
        # Sur Linux/macOS, il est dans CONDA_ROOT/bin/conda
        conda_path_win = os.path.join(conda_root, "Scripts", "conda.exe")
        conda_path_unix = os.path.join(conda_root, "bin", "conda")
        if os.path.exists(conda_path_win):
            return conda_path_win
        if os.path.exists(conda_path_unix):
            return conda_path_unix

    conda_exe_env = os.environ.get("CONDA_EXE")
    if conda_exe_env and os.path.exists(conda_exe_env):
        return conda_exe_env

    # Si on est dans un environnement Conda activé, CONDA_PREFIX est défini
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        # Essayer de remonter pour trouver l'installation de base de Conda
        # Cela peut être fragile, mais c'est une tentative
        possible_conda_root = os.path.dirname(os.path.dirname(conda_prefix)) # ex: envs/myenv -> anaconda3
        conda_path_win = os.path.join(possible_conda_root, "Scripts", "conda.exe")
        conda_path_unix = os.path.join(possible_conda_root, "bin", "conda")
        if os.path.exists(conda_path_win):
            return conda_path_win
        if os.path.exists(conda_path_unix):
            return conda_path_unix
            
    return None

_CONDA_EXE_PATH = _find_conda_executable() # Initialisation globale

def _run_conda_command(command_args, logger_instance=None, capture_output=True, check=True, **kwargs):
    """Fonction utilitaire pour exécuter les commandes conda."""
    logger = _get_logger(logger_instance)
    
    # Utiliser _CONDA_EXE_PATH déterminé au chargement du module
    conda_exe_to_use = _CONDA_EXE_PATH
    if not conda_exe_to_use:
        # Tenter de le retrouver si la première tentative a échoué (par ex. PATH modifié entre-temps)
        conda_exe_to_use = _find_conda_executable(logger_instance=logger)
        if not conda_exe_to_use:
            logger.error("Conda executable not found. Cannot run Conda commands.")
            if check:
                raise FileNotFoundError("Conda executable not found.")
            return subprocess.CompletedProcess(command_args, -1, stdout="", stderr="Conda executable not found.")

    command = [conda_exe_to_use] + command_args
    logger.debug(f"Running Conda command: {' '.join(command)}")
    try:
        process = subprocess.run(command, capture_output=capture_output, text=True, check=check, encoding='utf-8', **kwargs)
        if capture_output: # Log stdout/stderr même si check=False et returncode != 0
            if process.stdout: # Vérifier si stdout n'est pas None ou vide
                 logger.debug(f"Conda stdout:\n{process.stdout}")
            if process.stderr: # Vérifier si stderr n'est pas None ou vide
                 logger.debug(f"Conda stderr:\n{process.stderr}")
        return process
    except subprocess.CalledProcessError as e:
        logger.error(f"Conda command '{' '.join(command)}' failed with exit code {e.returncode}.")
        if capture_output: # e.stdout et e.stderr sont déjà remplis par CalledProcessError
            if e.stdout:
                logger.error(f"Conda STDOUT (on error):\n{e.stdout}")
            if e.stderr:
                logger.error(f"Conda STDERR (on error):\n{e.stderr}")
        if check:
            raise
        return e # Retourner l'objet exception si check=False
    except FileNotFoundError:
        logger.error(f"Conda command '{conda_exe_to_use}' not found. Is Conda installed and in PATH?", exc_info=True)
        if check:
            raise
        return subprocess.CompletedProcess(command, -1, stdout="", stderr=f"Conda executable '{conda_exe_to_use}' not found during run.")


def is_conda_installed(logger_instance=None):
    """Vérifie si Conda est accessible."""
    logger = _get_logger(logger_instance)
    conda_exe = _find_conda_executable(logger_instance=logger) # S'assurer qu'on a le chemin
    if not conda_exe:
        logger.warning("Conda executable not found by _find_conda_executable in is_conda_installed.")
        return False
    try:
        process = _run_conda_command(["--version"], logger_instance=logger, capture_output=True, check=True)
        # Le check=True dans _run_conda_command gère déjà l'échec.
        # Si on arrive ici, la commande a réussi.
        return process.returncode == 0 and "conda" in process.stdout.lower()
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("Conda --version command failed or Conda not found.", exc_info=True)
        return False

def conda_env_exists(env_name, logger_instance=None):
    """Vérifie si un environnement Conda avec le nom donné existe."""
    logger = _get_logger(logger_instance)
    if not is_conda_installed(logger_instance=logger):
        logger.warning("Conda not installed, cannot check if environment exists.")
        return False
    try:
        process = _run_conda_command(["env", "list"], logger_instance=logger, capture_output=True, check=True)
        env_pattern = re.compile(r"^\s*" + re.escape(env_name) + r"\s+|\s+" + re.escape(env_name) + r"$", re.MULTILINE)
        exists = env_pattern.search(process.stdout) is not None
        logger.debug(f"Conda env list stdout for '{env_name}' check:\n{process.stdout}")
        logger.debug(f"Environment '{env_name}' exists: {exists}")
        return exists
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning(f"Failed to list Conda environments or Conda not found while checking for '{env_name}'.", exc_info=True)
        return False

def create_conda_env(env_name, env_file_path, logger_instance=None, force_create=False, interactive=False):
    """Crée l'environnement."""
    logger = _get_logger(logger_instance)
    if force_create and conda_env_exists(env_name, logger_instance=logger):
        logger.info(f"Force create: Removing existing environment '{env_name}' before creation.")
        if not remove_conda_env(env_name, logger_instance=logger, interactive=interactive): # Non-interactive pour la suppression forcée si interactive=False
            logger.error(f"Failed to remove existing environment '{env_name}' during force create.")
            return False
    
    logger.info(f"Creating Conda environment '{env_name}' from file '{env_file_path}'. This may take a while...")
    try:
        _run_conda_command(["env", "create", "-f", env_file_path, "-n", env_name], logger_instance=logger, capture_output=True, check=True)
        logger.info(f"Conda environment '{env_name}' created successfully.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Failed to create Conda environment '{env_name}'. Error: {e}", exc_info=True)
        return False

def update_conda_env(env_name, env_file_path, logger_instance=None):
    """Met à jour l'environnement existant."""
    logger = _get_logger(logger_instance)
    logger.info(f"Updating Conda environment '{env_name}' from file '{env_file_path}'. This may take a while...")
    try:
        _run_conda_command(["env", "update", "-n", env_name, "--file", env_file_path, "--prune"], logger_instance=logger, capture_output=True, check=True)
        logger.info(f"Conda environment '{env_name}' updated successfully.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Failed to update Conda environment '{env_name}'. Error: {e}", exc_info=True)
        return False

def remove_conda_env(conda_env_name, logger_instance=None, interactive=False):
    """Supprime l'environnement Conda avec une logique de suppression robuste."""
    logger = _get_logger(logger_instance)
    logger.info(f"Attempting robust removal of Conda environment '{conda_env_name}'.")

    if interactive:
        try:
            confirm = input(f"Are you sure you want to delete Conda environment '{conda_env_name}' and its directory? [y/N]: ")
            if confirm.lower() != 'y':
                logger.info("Deletion cancelled by user.")
                return False
        except EOFError: # Cas où input() est appelé dans un contexte non interactif
            logger.warning("input() called in non-interactive context during remove_conda_env. Assuming 'No' for safety.")
            return False

    env_dir_to_remove = None
    try:
        info_process = _run_conda_command(["info", "--json"], logger_instance=logger, capture_output=True, check=True)
        conda_info_json = json.loads(info_process.stdout)
        
        if 'envs_dirs' in conda_info_json and conda_info_json['envs_dirs']:
            for envs_dir_str in conda_info_json['envs_dirs']:
                potential_path = Path(envs_dir_str) / conda_env_name
                if potential_path.exists() and potential_path.is_dir():
                    env_dir_to_remove = potential_path
                    logger.debug(f"Found environment directory candidate: {env_dir_to_remove}")
                    break
        
        if not env_dir_to_remove and 'envs' in conda_info_json:
            for env_path_str in conda_info_json['envs']:
                if env_path_str.endswith(os.sep + conda_env_name):
                    env_path_candidate = Path(env_path_str)
                    if env_path_candidate.exists() and env_path_candidate.is_dir():
                        env_dir_to_remove = env_path_candidate
                        logger.debug(f"Found environment directory candidate from 'envs' list: {env_dir_to_remove}")
                        break
        
        if not env_dir_to_remove and 'envs_dirs' in conda_info_json and conda_info_json['envs_dirs']:
             env_dir_to_remove = Path(conda_info_json['envs_dirs'][0]) / conda_env_name
             logger.debug(f"Using first 'envs_dirs' entry as base for environment directory: {env_dir_to_remove}")
        
        if not env_dir_to_remove:
            logger.warning(f"Could not definitively determine the directory for environment '{conda_env_name}' via 'conda info --json'.")
    except Exception as e:
        logger.warning(f"Exception while retrieving Conda info to determine environment path: {e}. Direct directory removal might be affected.", exc_info=True)

    if env_dir_to_remove and env_dir_to_remove.exists():
        logger.info(f"Attempting direct removal of existing environment directory: {env_dir_to_remove}")
        try:
            shutil.rmtree(env_dir_to_remove, onerror=env_utils.handle_remove_readonly_retry)
            if env_dir_to_remove.exists():
                error_message = f"CRITICAL ERROR: Failed to delete environment directory {env_dir_to_remove} even after shutil.rmtree. Manual intervention may be required. Script will stop."
                logger.critical(error_message)
                raise Exception(error_message)
            else:
                logger.info(f"Environment directory {env_dir_to_remove} successfully deleted.")
        except Exception as e:
            error_message = f"CRITICAL ERROR: Exception during shutil.rmtree attempt on {env_dir_to_remove}: {e}. Manual intervention may be required. Script will stop."
            logger.critical(error_message, exc_info=True)
            raise Exception(error_message)
    elif env_dir_to_remove:
        logger.info(f"Environment directory {env_dir_to_remove} does not exist or could not be determined with certainty. Skipping direct directory removal.")
    else:
         logger.info(f"Environment directory for '{conda_env_name}' could not be determined. Skipping direct directory removal.")

    logger.info("Executing 'conda clean --all --yes' to clean Conda caches.")
    try:
        _run_conda_command(["clean", "--all", "--yes"], logger_instance=logger, check=False)
        logger.info("Conda cache cleaning finished (or attempt made).")
    except Exception as e:
        logger.warning(f"Failed to clean Conda caches: {e}. Continuing script.", exc_info=True)

    logger.info(f"Attempting 'conda env remove --name {conda_env_name}' to clean Conda metadata.")
    try:
        _run_conda_command(["env", "remove", "--name", conda_env_name, "--yes"], logger_instance=logger, check=False)
        logger.info(f"'conda env remove' command for '{conda_env_name}' executed.")
    except Exception as e:
        logger.info(f"'conda env remove --name {conda_env_name}' potentially failed (may be normal if directory no longer existed or env was not recognized): {e}", exc_info=True)
    
    env_still_exists = conda_env_exists(conda_env_name, logger_instance=logger)
    if not env_still_exists:
        logger.info(f"Confirmation: Environment '{conda_env_name}' no longer exists after cleanup steps (according to conda env list).")
        if env_dir_to_remove and env_dir_to_remove.exists():
             logger.warning(f"Directory {env_dir_to_remove} still exists although conda no longer lists the environment. This might indicate an incomplete cleanup.")
        return True
    else:
        error_message = f"CRITICAL ERROR: Environment '{conda_env_name}' (potential directory: {env_dir_to_remove if env_dir_to_remove else 'Not determined'}) still exists according to 'conda env list' despite all removal attempts. Script will stop."
        logger.critical(error_message)
        if env_dir_to_remove and env_dir_to_remove.exists():
            logger.critical(f"Physical directory {env_dir_to_remove} also exists.")
        raise Exception(error_message)

def setup_environment(env_name, env_file_path, project_root, logger_instance=None, force_reinstall=False, interactive=False):
    """Gère la configuration de l'environnement Conda."""
    logger = _get_logger(logger_instance)
    logger.info(f"--- Managing Conda Environment: {env_name} ---")
    logger.info(f"Project root: {project_root}")
    logger.info(f"Environment file: {env_file_path}")
    logger.info(f"Using Conda environment name: {CONDA_ENV_NAME} (Hardcoded for repair task in manage_conda_env.py)")


    if not is_conda_installed(logger_instance=logger):
        logger.error("Conda is not installed or not found in PATH. Please install Conda and ensure it's in your PATH.")
        return False

    if not os.path.exists(env_file_path):
        logger.error(f"Conda environment file not found: {env_file_path}")
        return False

    env_already_exists = conda_env_exists(env_name, logger_instance=logger)

    if env_already_exists:
        if force_reinstall:
            logger.info(f"Force reinstall of Conda environment '{env_name}' requested.")
            if remove_conda_env(env_name, logger_instance=logger, interactive=interactive):
                return create_conda_env(env_name, env_file_path, logger_instance=logger, force_create=True)
            else:
                logger.error(f"Failed to remove existing environment '{env_name}' for reinstallation.")
                return False
        else:
            logger.info(f"Conda environment '{env_name}' already exists. Attempting to update.")
            return update_conda_env(env_name, env_file_path, logger_instance=logger)
    else:
        logger.info(f"Conda environment '{env_name}' not found. Creating new environment.")
        return create_conda_env(env_name, env_file_path, logger_instance=logger)

if __name__ == '__main__':
    # Configuration du logger pour les tests locaux directs
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s (main test)',
                        handlers=[logging.StreamHandler(sys.stdout)])
    logger_main = logging.getLogger(__name__) # Utiliser le logger du module pour les tests
    
    current_script_path = os.path.abspath(__file__)
    setup_core_dir = os.path.dirname(current_script_path)
    scripts_dir = os.path.dirname(setup_core_dir)
    project_root_dir = os.path.dirname(scripts_dir)
    
    test_env_file = os.path.join(project_root_dir, CONDA_ENV_FILE_NAME)
    
    logger_main.info(f"--- Testing Conda environment setup ---")
    logger_main.info(f"Project root: {project_root_dir}")
    logger_main.info(f"Environment file: {test_env_file}")
    
    conda_exe_path_test = _find_conda_executable(logger_instance=logger_main)
    logger_main.info(f"Conda executable found at: {conda_exe_path_test if conda_exe_path_test else 'Not found'}")

    if not is_conda_installed(logger_instance=logger_main):
        logger_main.error("Conda is not installed or not found. Aborting tests.")
        sys.exit(1)

    if os.path.exists(test_env_file):
        logger_main.info(f"\n--- Auto Execution for Repair Task: Force reinstall environment '{CONDA_ENV_NAME}' ---")
        success_reinstall = setup_environment(CONDA_ENV_NAME, test_env_file, project_root_dir, logger_instance=logger_main, force_reinstall=True, interactive=False)
        logger_main.info(f"Force reinstall successful: {success_reinstall}")
        if not success_reinstall:
            logger_main.error(f"Exiting due to failed reinstallation of environment '{CONDA_ENV_NAME}'.")
            sys.exit(1)
        else:
            logger_main.info(f"Environment '{CONDA_ENV_NAME}' reinstalled successfully through main execution block.")
    else:
        logger_main.error(f"\nCannot run repair: '{CONDA_ENV_FILE_NAME}' not found at project root '{project_root_dir}'.")
        sys.exit(1)