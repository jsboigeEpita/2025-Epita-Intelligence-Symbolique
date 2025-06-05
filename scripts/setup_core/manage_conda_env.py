# scripts/setup_core/manage_conda_env.py
import os
import subprocess
import re
import sys
import shutil
from pathlib import Path # Ajout pour la nouvelle logique de suppression
import json # Ajout pour parser la sortie de conda info --json

# Importer les utilitaires nécessaires depuis env_utils
import scripts.setup_core.env_utils as env_utils


# Lire le nom de l'environnement Conda depuis une variable d'environnement, sinon utiliser une valeur par défaut
CONDA_ENV_NAME_DEFAULT = "epita_symbolic_ai"
CONDA_ENV_NAME = os.getenv("CONDA_ENV_NAME", CONDA_ENV_NAME_DEFAULT)
print(f"[INFO] Using Conda environment name: {CONDA_ENV_NAME} (Default was: {CONDA_ENV_NAME_DEFAULT}, Env Var was: {os.getenv('CONDA_ENV_NAME')})") # Log amélioré
CONDA_ENV_FILE_NAME = "environment.yml"

def _find_conda_executable():
    """Trouve l'exécutable Conda."""
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

_CONDA_EXE_PATH = _find_conda_executable()

def _run_conda_command(command_args, capture_output=True, check=True, **kwargs):
    """Fonction utilitaire pour exécuter les commandes conda."""
    if not _CONDA_EXE_PATH:
        print("[ERROR] Conda executable not found. Cannot run Conda commands.", file=sys.stderr)
        if check:
            raise FileNotFoundError("Conda executable not found.")
        return subprocess.CompletedProcess(command_args, -1, stdout="", stderr="Conda executable not found.")

    command = [_CONDA_EXE_PATH] + command_args
    print(f"[DEBUG] Running Conda command: {' '.join(command)}")
    try:
        process = subprocess.run(command, capture_output=capture_output, text=True, check=check, **kwargs)
        if capture_output:
            print(f"[DEBUG] Conda stdout:\n{process.stdout}")
            if process.stderr:
                print(f"[DEBUG] Conda stderr:\n{process.stderr}")
        return process
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Conda command '{' '.join(command)}' failed with exit code {e.returncode}.", file=sys.stderr)
        if capture_output:
            print(f"Stdout: {e.stdout}", file=sys.stderr)
            print(f"Stderr: {e.stderr}", file=sys.stderr)
        if check:
            raise
        return e
    except FileNotFoundError:
        # Cela ne devrait pas arriver si _CONDA_EXE_PATH est correct, mais par sécurité
        print(f"[ERROR] Conda command '{_CONDA_EXE_PATH}' not found. Is Conda installed and in PATH?", file=sys.stderr)
        if check:
            raise
        return subprocess.CompletedProcess(command, -1, stdout="", stderr="Conda executable not found during run.")


def is_conda_installed():
    """Vérifie si Conda est accessible."""
    if not _CONDA_EXE_PATH:
        return False
    try:
        process = _run_conda_command(["--version"], capture_output=True, check=True)
        return process.returncode == 0 and "conda" in process.stdout.lower()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def conda_env_exists(env_name):
    """Vérifie si un environnement Conda avec le nom donné existe."""
    if not is_conda_installed(): # Assure que conda est là avant de l'utiliser
        return False
    try:
        process = _run_conda_command(["env", "list"], capture_output=True, check=True)
        # La sortie de `conda env list` liste les environnements.
        # On cherche une ligne qui commence par env_name ou contient /env_name (pour les chemins)
        # Regex pour matcher le nom de l'environnement au début d'une ligne ou après un chemin
        # Exemple de lignes:
        # base                  *  C:\Users\user\miniconda3
        # myenv                    C:\Users\user\miniconda3\envs\myenv
        # another_env              /opt/conda/envs/another_env
        env_pattern = re.compile(r"^\s*" + re.escape(env_name) + r"\s+|\s+" + re.escape(env_name) + r"$", re.MULTILINE)
        return env_pattern.search(process.stdout) is not None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def create_conda_env(env_name, env_file_path, force_create=False):
    """Crée l'environnement."""
    if force_create and conda_env_exists(env_name):
        print(f"[INFO] Force create: Removing existing environment '{env_name}' before creation.")
        if not remove_conda_env(env_name, interactive=False): # Non-interactive pour la suppression forcée
            print(f"[ERROR] Failed to remove existing environment '{env_name}' during force create.")
            return False
    
    print(f"[INFO] Creating Conda environment '{env_name}' from file '{env_file_path}'. This may take a while...")
    try:
        # `conda env create` est la commande préférée pour les fichiers environment.yml
        # `conda create` est plus général mais peut aussi utiliser --file
        # On utilise `conda env create` pour être plus spécifique.
        _run_conda_command(["env", "create", "-f", env_file_path, "-n", env_name], capture_output=True, check=True)
        print(f"[SUCCESS] Conda environment '{env_name}' created successfully.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[ERROR] Failed to create Conda environment '{env_name}'. Error: {e}", file=sys.stderr)
        return False

def update_conda_env(env_name, env_file_path):
    """Met à jour l'environnement existant."""
    print(f"[INFO] Updating Conda environment '{env_name}' from file '{env_file_path}'. This may take a while...")
    try:
        # --prune supprime les dépendances qui ne sont plus nécessaires
        _run_conda_command(["env", "update", "-n", env_name, "--file", env_file_path, "--prune"], capture_output=True, check=True)
        print(f"[SUCCESS] Conda environment '{env_name}' updated successfully.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[ERROR] Failed to update Conda environment '{env_name}'. Error: {e}", file=sys.stderr)
        return False

def remove_conda_env(conda_env_name, interactive=False): # Renommé env_name en conda_env_name pour correspondre au code fourni
    """Supprime l'environnement Conda avec une logique de suppression robuste."""
    print(f"[INFO] Tentative de suppression robuste de l'environnement Conda '{conda_env_name}'.")

    if interactive: # Garder la confirmation interactive si demandée
        confirm = input(f"Êtes-vous sûr de vouloir supprimer l'environnement Conda '{conda_env_name}' et son répertoire ? [y/N]: ")
        if confirm.lower() != 'y':
            print("[INFO] Suppression annulée par l'utilisateur.")
            return False
    
    # Obtenir le répertoire de l'environnement
    env_dir_to_remove = None
    try:
        info_process = _run_conda_command(["info", "--json"], capture_output=True, check=True)
        conda_info_json = json.loads(info_process.stdout)
        
        # Chercher le répertoire de l'environnement spécifique
        # La clé 'envs' liste tous les répertoires d'environnements.
        # On cherche celui qui se termine par /conda_env_name ou \conda_env_name
        target_env_path_segment = os.path.join("envs", conda_env_name) # Pourrait être juste conda_env_name si c'est un chemin absolu direct
        
        # Cas 1: l'environnement est dans l'un des 'envs_dirs'
        if 'envs_dirs' in conda_info_json and conda_info_json['envs_dirs']:
            for envs_dir_str in conda_info_json['envs_dirs']:
                potential_path = Path(envs_dir_str) / conda_env_name
                if potential_path.exists() and potential_path.is_dir():
                    env_dir_to_remove = potential_path
                    break
        
        # Cas 2: si non trouvé, vérifier la liste 'envs' qui contient les chemins complets
        if not env_dir_to_remove and 'envs' in conda_info_json:
            for env_path_str in conda_info_json['envs']:
                if env_path_str.endswith(os.sep + conda_env_name):
                    env_path_candidate = Path(env_path_str)
                    if env_path_candidate.exists() and env_path_candidate.is_dir():
                        env_dir_to_remove = env_path_candidate
                        break
        
        # Cas 3: Fallback si 'envs_dirs' est vide ou si l'env est dans le premier 'envs_dirs' (comportement par défaut)
        # Ceci est plus proche de la logique originale du code fourni.
        if not env_dir_to_remove and 'envs_dirs' in conda_info_json and conda_info_json['envs_dirs']:
             env_dir_to_remove = Path(conda_info_json['envs_dirs'][0]) / conda_env_name
             # On ne vérifie pas exists() ici car on veut tenter la suppression même si conda pense qu'il n'est pas là mais que le dossier existe

        if not env_dir_to_remove:
            # Si on ne trouve toujours pas, on essaie de construire un chemin basé sur CONDA_PREFIX s'il correspond à l'env
            # ou un chemin par défaut si on ne peut pas déterminer le dossier exact.
            # Cela devient plus une heuristique.
            # Pour l'instant, on va se baser sur le premier envs_dirs comme dans le code fourni.
            if 'envs_dirs' in conda_info_json and conda_info_json['envs_dirs']:
                 env_dir_to_remove = Path(conda_info_json['envs_dirs'][0]) / conda_env_name
            else:
                print("[WARNING] Impossible de déterminer le répertoire exact de l'environnement via 'conda info --json'. La suppression du répertoire pourrait échouer ou être incorrecte.")
                # On ne lève pas d'erreur ici, on va quand même tenter `conda env remove`
    except Exception as e:
        print(f"[WARNING] Exception lors de la récupération des informations de Conda pour déterminer le chemin de l'environnement : {e}. La suppression directe du répertoire pourrait être affectée.")
        # On continue pour tenter `conda env remove`

    # Début de la logique de suppression robuste
    if env_dir_to_remove and env_dir_to_remove.exists(): # Vérifier si le chemin a été déterminé ET s'il existe
        print(f"[INFO] Tentative de suppression directe du répertoire de l'environnement existant : {env_dir_to_remove}")
        try:
            shutil.rmtree(env_dir_to_remove, onerror=env_utils.handle_remove_readonly_retry)
            if env_dir_to_remove.exists():
                error_message = f"[CRITICAL ERROR] Échec de la suppression du répertoire de l'environnement {env_dir_to_remove} même après shutil.rmtree. Une intervention manuelle peut être requise pour supprimer ce répertoire. Le script va s'arrêter."
                print(error_message, file=sys.stderr)
                # Lever une exception pour arrêter le processus si la suppression du répertoire est critique
                raise Exception(error_message)
            else:
                print(f"[INFO] Répertoire de l'environnement {env_dir_to_remove} supprimé avec succès.")
        except Exception as e:
            error_message = f"[CRITICAL ERROR] Exception lors de la tentative de suppression de {env_dir_to_remove} avec shutil.rmtree: {e}. Une intervention manuelle peut être requise. Le script va s'arrêter."
            print(error_message, file=sys.stderr)
            raise Exception(error_message) # Redclencher ou lever une nouvelle exception pour arrêter
    elif env_dir_to_remove: # Le chemin a été déterminé mais n'existe pas
        print(f"[INFO] Le répertoire de l'environnement {env_dir_to_remove} n'existe pas ou n'a pas pu être déterminé avec certitude, la suppression directe du répertoire est ignorée.")
    else: # Le chemin n'a pas pu être déterminé
         print(f"[INFO] Le répertoire de l'environnement pour '{conda_env_name}' n'a pas pu être déterminé. La suppression directe du répertoire est ignorée.")


    # Nettoyage des caches Conda
    print("[INFO] Exécution de 'conda clean --all --yes' pour nettoyer les caches Conda.")
    try:
        _run_conda_command(["clean", "--all", "--yes"], check=False) # check=False pour ne pas bloquer si clean échoue
        print("[INFO] Nettoyage des caches Conda terminé (ou tentative effectuée).")
    except Exception as e:
        print(f"[WARNING] Échec du nettoyage des caches Conda : {e}. Continuation du script.")

    # Tentative de suppression via la commande Conda pour nettoyer les métadonnées
    print(f"[INFO] Tentative de 'conda env remove --name {conda_env_name}' pour nettoyer les métadonnées Conda.")
    try:
        # On utilise check=False car la commande peut échouer si l'environnement n'est plus listé par Conda,
        # même si le répertoire a été supprimé manuellement.
        _run_conda_command(["env", "remove", "--name", conda_env_name, "--yes"], check=False)
        print(f"[INFO] Commande 'conda env remove' pour '{conda_env_name}' exécutée.")
    except Exception as e:
        # Un échec ici n'est pas forcément bloquant si le répertoire a été supprimé.
        print(f"[INFO] 'conda env remove --name {conda_env_name}' a potentiellement échoué (peut être normal si le répertoire n'existait plus ou si l'env n'était pas reconnu) : {e}")
    
    # Mettre à jour le statut de l'environnement
    # Utiliser la fonction conda_env_exists locale
    env_still_exists = conda_env_exists(conda_env_name) # Utilise la fonction locale
    if not env_still_exists:
        print(f"[INFO] Confirmation : l'environnement '{conda_env_name}' n'existe plus après les étapes de nettoyage (selon conda env list).")
        # Vérification supplémentaire : le répertoire physique existe-t-il toujours ?
        if env_dir_to_remove and env_dir_to_remove.exists():
             print(f"[WARNING] Le répertoire {env_dir_to_remove} existe toujours bien que conda ne liste plus l'environnement. Cela peut indiquer un nettoyage incomplet.")
             # Ne pas lever d'erreur critique ici, car conda ne le voit plus.
        return True # Succès du point de vue de conda
    else:
        # Si l'environnement existe toujours ici, c'est un problème sérieux.
        error_message = f"[CRITICAL ERROR] L'environnement '{conda_env_name}' (répertoire potentiel: {env_dir_to_remove if env_dir_to_remove else 'Non déterminé'}) existe toujours selon 'conda env list' malgré toutes les tentatives de suppression. Le script va s'arrêter."
        print(error_message, file=sys.stderr)
        # Si le répertoire physique existe aussi, c'est encore plus problématique
        if env_dir_to_remove and env_dir_to_remove.exists():
            print(f"[CRITICAL ERROR] Le répertoire physique {env_dir_to_remove} existe également.", file=sys.stderr)
        raise Exception(error_message)
    # Fin de la logique de suppression robuste

def setup_environment(env_name, env_file_path, project_root, force_reinstall=False, interactive=False):
    """Gère la configuration de l'environnement Conda."""
    print(f"--- Managing Conda Environment: {env_name} ---")
    print(f"Project root: {project_root}")
    print(f"Environment file: {env_file_path}")

    if not is_conda_installed():
        print("[ERROR] Conda is not installed or not found in PATH. Please install Conda and ensure it's in your PATH.", file=sys.stderr)
        return False

    if not os.path.exists(env_file_path):
        print(f"[ERROR] Conda environment file not found: {env_file_path}", file=sys.stderr)
        # Pourrait créer un environment.yml de base ici si nécessaire, mais pour l'instant, c'est une erreur.
        # print(f"[INFO] You can create a default '{CONDA_ENV_FILE_NAME}' with python, pip, etc.")
        return False

    env_already_exists = conda_env_exists(env_name)

    if env_already_exists:
        if force_reinstall:
            print(f"[INFO] Force reinstall of Conda environment '{env_name}' requested.")
            # La fonction remove_conda_env gère l'interactivité
            if remove_conda_env(env_name, interactive=interactive): 
                # force_create=True n'est pas nécessaire ici car create_conda_env le fait déjà si on lui dit de forcer
                # mais on s'assure que l'environnement est bien recréé
                return create_conda_env(env_name, env_file_path, force_create=True) 
            else:
                print(f"[ERROR] Failed to remove existing environment '{env_name}' for reinstallation.", file=sys.stderr)
                return False
        else:
            print(f"[INFO] Conda environment '{env_name}' already exists. Attempting to update.")
            return update_conda_env(env_name, env_file_path)
    else:
        print(f"[INFO] Conda environment '{env_name}' not found. Creating new environment.")
        return create_conda_env(env_name, env_file_path)

    # Ce fallback ne devrait pas être atteint si la logique ci-dessus est correcte.
    # print("[ERROR] Unexpected state in setup_environment.", file=sys.stderr)
    # return False 

if __name__ == '__main__':
    # Pour tests locaux
    # Déterminer la racine du projet en remontant de deux niveaux par rapport à scripts/setup_core
    current_script_path = os.path.abspath(__file__)
    setup_core_dir = os.path.dirname(current_script_path)
    scripts_dir = os.path.dirname(setup_core_dir)
    project_root_dir = os.path.dirname(scripts_dir)
    
    test_env_file = os.path.join(project_root_dir, CONDA_ENV_FILE_NAME)
    
    print(f"--- Testing Conda environment setup ---")
    print(f"Project root: {project_root_dir}")
    print(f"Environment file: {test_env_file}")
    print(f"Conda executable found at: {_CONDA_EXE_PATH if _CONDA_EXE_PATH else 'Not found'}")

    if not is_conda_installed():
        print("Conda is not installed or not found. Aborting tests.")
        sys.exit(1)

    # Assurez-vous d'avoir un fichier environment.yml à la racine pour tester
    # Exemple de test (crée/met à jour l'environnement)
    # Pour tester, décommentez les lignes suivantes et assurez-vous qu'un fichier
    # 'environment.yml' existe à la racine du projet.
    # Contenu minimal pour environment.yml pour tester:
    # name: epita_symbolic_ai
    # channels:
    #   - defaults
    # dependencies:
    #   - python=3.10
    #   - pip
    
    # print(f"\n--- Test Scenario: Check if environment '{CONDA_ENV_NAME}' exists ---")
    # if conda_env_exists(CONDA_ENV_NAME):
    #     print(f"Environment '{CONDA_ENV_NAME}' exists.")
    # else:
    #     print(f"Environment '{CONDA_ENV_NAME}' does not exist.")

    # if os.path.exists(test_env_file):
    #     print(f"\n--- Test Scenario: Setup environment (create/update) '{CONDA_ENV_NAME}' ---")
    #     # Mettre force_reinstall=True pour tester la suppression et recréation
    #     success = setup_environment(CONDA_ENV_NAME, test_env_file, project_root_dir, force_reinstall=False, interactive=True)
    #     print(f"Setup successful: {success}")

    #     if success:
    #         print(f"\n--- Test Scenario: Attempt to update again ---")
    #         success_update = setup_environment(CONDA_ENV_NAME, test_env_file, project_root_dir, force_reinstall=False, interactive=False)
    #         print(f"Second update successful: {success_update}")

    #     print(f"\n--- Test Scenario: Force reinstall environment '{CONDA_ENV_NAME}' ---")
    #     success_reinstall = setup_environment(CONDA_ENV_NAME, test_env_file, project_root_dir, force_reinstall=True, interactive=True) # Mettre interactive à False pour les tests automatisés
    #     print(f"Force reinstall successful: {success_reinstall}")

    #     # print(f"\n--- Test Scenario: Remove environment '{CONDA_ENV_NAME}' ---")
    #     # if remove_conda_env(CONDA_ENV_NAME, interactive=True): # Mettre interactive à False pour les tests automatisés
    #     #     print(f"Environment '{CONDA_ENV_NAME}' removed for cleanup.")
    #     # else:
    #     #     print(f"Failed to remove environment '{CONDA_ENV_NAME}' during cleanup.")
    # else:
    #     print(f"\n[WARNING] Cannot run full setup tests: '{CONDA_ENV_FILE_NAME}' not found at project root '{project_root_dir}'.")
    #     print("Please create it with basic content (e.g., python version) to test environment creation.")

    print("\nRun this script directly to test its functionality (uncomment test calls and ensure environment.yml exists).")
    print("Make sure Conda is installed and accessible.")