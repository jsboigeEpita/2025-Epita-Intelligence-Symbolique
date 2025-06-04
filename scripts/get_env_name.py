import sys
import os

# Assurer que setup_core est dans le path pour l'import de env_utils
# Ce script est dans scripts/, env_utils.py est dans scripts/setup_core/
_current_script_path = os.path.abspath(__file__)
_scripts_dir = os.path.dirname(_current_script_path)
_project_root = os.path.dirname(_scripts_dir) # Racine du projet

# Ajouter le répertoire racine du projet à sys.path pour trouver scripts.setup_core
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from scripts.setup_core.env_utils import get_conda_env_name_from_yaml
except ModuleNotFoundError:
    # Fallback si l'ajout au path n'a pas suffi (ex: exécution depuis un autre contexte)
    # Essayons d'ajouter explicitement le dossier 'scripts' qui contient 'setup_core'
    # Ceci est plus une rustine, la structure d'appel devrait gérer le PYTHONPATH
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    # Et aussi le dossier setup_core lui-même, au cas où
    _setup_core_dir = os.path.join(_scripts_dir, "setup_core")
    if _setup_core_dir not in sys.path:
        sys.path.insert(0, _setup_core_dir)
    
    # Nouvelle tentative d'import
    try:
        from setup_core.env_utils import get_conda_env_name_from_yaml
    except ModuleNotFoundError:
        # Si toujours pas trouvé, on essaie un import direct, au cas où le CWD serait scripts/setup_core
        try:
            from env_utils import get_conda_env_name_from_yaml
        except ModuleNotFoundError as e:
            print(f"CRITICAL_ERROR: Could not import get_conda_env_name_from_yaml. sys.path: {sys.path}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    try:
        env_name = get_conda_env_name_from_yaml()
        print(env_name) # Sortie standard pour être capturée par le script appelant
    except Exception as e:
        print(f"ERROR_GETTING_ENV_NAME: {e}", file=sys.stderr)
        sys.exit(1)