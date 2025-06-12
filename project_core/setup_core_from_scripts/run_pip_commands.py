import os
import subprocess
import logging
import sys # Ajout pour le logger par défaut

# Logger par défaut pour ce module
module_logger_pip = logging.getLogger(__name__)
if not module_logger_pip.hasHandlers():
    _console_handler_pip = logging.StreamHandler(sys.stdout)
    _console_handler_pip.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (module default pip)'))
    module_logger_pip.addHandler(_console_handler_pip)
    module_logger_pip.setLevel(logging.INFO)

def _get_logger_pip(logger_instance=None):
    """Retourne le logger fourni ou le logger par défaut du module."""
    return logger_instance if logger_instance else module_logger_pip


def _run_command_in_conda_env(conda_env_name: str, command_list: list, project_root: str, logger_instance=None):
    """
    Exécute une commande dans l'environnement Conda spécifié.

    Args:
        conda_env_name (str): Le nom de l'environnement Conda.
        command_list (list): La commande et ses arguments sous forme de liste.
        project_root (str): Le répertoire racine du projet où la commande doit être exécutée.
        logger_instance (logging.Logger, optional): Instance du logger à utiliser.

    Returns:
        bool: True si la commande a réussi, False sinon.
    """
    logger = _get_logger_pip(logger_instance)
    try:
        conda_run_command = ['conda', 'run', '-n', conda_env_name] + command_list
        logger.info(f"Exécution de la commande dans l'environnement Conda '{conda_env_name}': {' '.join(conda_run_command)}")
        
        is_windows = os.name == 'nt'
        
        result = subprocess.run(
            conda_run_command,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
            shell=is_windows,
            encoding='utf-8'
        )

        if result.returncode == 0:
            logger.info(f"Commande exécutée avec succès.")
            if result.stdout: # Log stdout seulement si non vide
                logger.debug(f"Sortie standard:\n{result.stdout}")
            if result.stderr: # Log stderr seulement si non vide (peut contenir des warnings)
                logger.debug(f"Erreur standard (peut être des warnings):\n{result.stderr}")
            return True
        else:
            logger.error(f"Erreur lors de l'exécution de la commande.")
            logger.error(f"Commande: {' '.join(conda_run_command)}")
            logger.error(f"Code de retour: {result.returncode}")
            if result.stdout:
                logger.error(f"Sortie standard:\n{result.stdout}")
            if result.stderr:
                logger.error(f"Erreur standard:\n{result.stderr}")
            return False
    except FileNotFoundError:
        logger.error(f"La commande 'conda' n'a pas été trouvée. Assurez-vous que Conda est installé et dans le PATH.", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Une erreur inattendue est survenue lors de l'exécution de la commande: {e}", exc_info=True)
        logger.error(f"Commande tentée: {' '.join(conda_run_command if 'conda_run_command' in locals() else command_list)}")
        return False

def install_project_dependencies(project_root: str, conda_env_name: str, logger_instance=None):
    """
    Installe les dépendances du projet en utilisant pip dans l'environnement Conda spécifié.
    Tente d'abord `pip install -e .`, puis `pip install -e ./src` si le premier échoue
    et qu'un setup.py ou pyproject.toml existe dans src/.

    Args:
        project_root (str): Le chemin racine du projet.
        conda_env_name (str): Le nom de l'environnement Conda.
        logger_instance (logging.Logger, optional): Instance du logger à utiliser.

    Returns:
        bool: True si l'installation a réussi, False sinon.
    """
    logger = _get_logger_pip(logger_instance)
    logger.info(f"Début de l'installation des dépendances du projet dans '{project_root}' pour l'environnement '{conda_env_name}'.")

    pip_command_root = ['pip', 'install', '-e', '.']
    logger.info("Tentative d'installation des dépendances avec 'pip install -e .'")
    if _run_command_in_conda_env(conda_env_name, pip_command_root, project_root, logger_instance=logger):
        logger.info("Dépendances installées avec succès via 'pip install -e .'.")
        return True
    
    logger.warning("'pip install -e .' a échoué ou n'a rien installé. Vérification de la présence de setup.py/pyproject.toml dans src/.")

    src_path = os.path.join(project_root, 'src')
    setup_py_in_src = os.path.exists(os.path.join(src_path, 'setup.py'))
    pyproject_toml_in_src = os.path.exists(os.path.join(src_path, 'pyproject.toml'))

    if os.path.isdir(src_path) and (setup_py_in_src or pyproject_toml_in_src):
        logger.info(f"Un fichier {'setup.py' if setup_py_in_src else 'pyproject.toml'} a été trouvé dans '{src_path}'.")
        logger.info("Tentative d'installation des dépendances avec 'pip install -e ./src'")
        
        pip_command_src = ['pip', 'install', '-e', './src']
        if _run_command_in_conda_env(conda_env_name, pip_command_src, project_root, logger_instance=logger):
            logger.info("Dépendances installées avec succès via 'pip install -e ./src'.")
            return True
        else:
            logger.error("Échec de l'installation des dépendances via 'pip install -e ./src'.")
            return False
    else:
        logger.warning(f"Aucun répertoire 'src' avec 'setup.py' ou 'pyproject.toml' trouvé, ou 'pip install -e .' a déjà échoué.")
        logger.error("Impossible d'installer les dépendances du projet via pip editable install.")
        return False

if __name__ == '__main__':
    # Configuration du logger pour les tests locaux directs
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s (main test pip)',
                        handlers=[logging.StreamHandler(sys.stdout)])
    logger_main_pip = logging.getLogger(__name__)

    current_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    test_conda_env_name = "epita_symbolic_ai"

    logger_main_pip.info(f"Test du module run_pip_commands.py avec project_root='{current_project_root}' et conda_env_name='{test_conda_env_name}'")
    
    mock_setup_py_path = os.path.join(current_project_root, "setup.py")
    is_mock_setup_created = False
    if not os.path.exists(mock_setup_py_path):
        logger_main_pip.info(f"Création d'un fichier setup.py factice pour le test : {mock_setup_py_path}")
        with open(mock_setup_py_path, "w") as f:
            f.write("# Fichier setup.py factice pour les tests\n")
            f.write("from setuptools import setup, find_packages\n")
            f.write("setup(name='test_project', version='0.1', packages=find_packages())\n")
        is_mock_setup_created = True

    success = install_project_dependencies(current_project_root, test_conda_env_name, logger_instance=logger_main_pip)

    if success:
        logger_main_pip.info("Test de install_project_dependencies réussi.")
    else:
        logger_main_pip.error("Test de install_project_dependencies échoué.")

    if is_mock_setup_created:
        logger_main_pip.info(f"Suppression du fichier setup.py factice : {mock_setup_py_path}")
        os.remove(mock_setup_py_path)

    mock_src_path = os.path.join(current_project_root, "src")
    mock_setup_py_in_src_path = os.path.join(mock_src_path, "setup.py")
    is_mock_src_setup_created = False
    if not os.path.exists(mock_src_path):
        os.makedirs(mock_src_path)
    
    if os.path.exists(mock_setup_py_path):
        os.remove(mock_setup_py_path)

    if not os.path.exists(mock_setup_py_in_src_path):
        logger_main_pip.info(f"Création d'un fichier setup.py factice pour le test dans src/ : {mock_setup_py_in_src_path}")
        with open(mock_setup_py_in_src_path, "w") as f:
            f.write("# Fichier setup.py factice dans src/ pour les tests\n")
            f.write("from setuptools import setup, find_packages\n")
            f.write("setup(name='test_project_src', version='0.1', packages=find_packages())\n")
        is_mock_src_setup_created = True
    
    logger_main_pip.info(f"Test du module run_pip_commands.py avec setup.py dans src/")
    success_src = install_project_dependencies(current_project_root, test_conda_env_name, logger_instance=logger_main_pip)
    if success_src:
        logger_main_pip.info("Test de install_project_dependencies (avec setup.py dans src/) réussi.")
    else:
        logger_main_pip.error("Test de install_project_dependencies (avec setup.py dans src/) échoué.")

    if is_mock_src_setup_created:
        logger_main_pip.info(f"Suppression du fichier setup.py factice dans src/ : {mock_setup_py_in_src_path}")
        os.remove(mock_setup_py_in_src_path)
    if os.path.exists(mock_src_path) and not os.listdir(mock_src_path):
        os.rmdir(mock_src_path)