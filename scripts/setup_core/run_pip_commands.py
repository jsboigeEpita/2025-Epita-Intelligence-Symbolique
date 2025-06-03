import os
import subprocess
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _run_command_in_conda_env(conda_env_name: str, command_list: list, project_root: str):
    """
    Exécute une commande dans l'environnement Conda spécifié.

    Args:
        conda_env_name (str): Le nom de l'environnement Conda.
        command_list (list): La commande et ses arguments sous forme de liste.
        project_root (str): Le répertoire racine du projet où la commande doit être exécutée.

    Returns:
        bool: True si la commande a réussi, False sinon.
    """
    try:
        conda_run_command = ['conda', 'run', '-n', conda_env_name] + command_list
        logging.info(f"Exécution de la commande dans l'environnement Conda '{conda_env_name}': {' '.join(conda_run_command)}")
        
        # Utilisation de shell=True sur Windows pour la commande conda, mais attention à la sécurité.
        # Pour une meilleure portabilité et sécurité, il serait préférable de trouver le chemin de l'exécutable python de l'environnement.
        # Cependant, `conda run` est la méthode recommandée pour exécuter des commandes dans un environnement.
        is_windows = os.name == 'nt'
        
        result = subprocess.run(
            conda_run_command,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False, # On ne veut pas que check=True lève une exception ici, on la gère manuellement
            shell=is_windows # Nécessaire pour que `conda run` soit trouvé correctement sur Windows dans certains cas
        )

        if result.returncode == 0:
            logging.info(f"Commande exécutée avec succès:\n{result.stdout}")
            return True
        else:
            logging.error(f"Erreur lors de l'exécution de la commande.")
            logging.error(f"Commande: {' '.join(conda_run_command)}")
            logging.error(f"Code de retour: {result.returncode}")
            logging.error(f"Sortie standard:\n{result.stdout}")
            logging.error(f"Erreur standard:\n{result.stderr}")
            return False
    except FileNotFoundError:
        logging.error(f"La commande 'conda' n'a pas été trouvée. Assurez-vous que Conda est installé et dans le PATH.")
        return False
    except Exception as e:
        logging.error(f"Une erreur inattendue est survenue lors de l'exécution de la commande: {e}")
        logging.error(f"Commande: {' '.join(conda_run_command)}")
        return False

def install_project_dependencies(project_root: str, conda_env_name: str):
    """
    Installe les dépendances du projet en utilisant pip dans l'environnement Conda spécifié.
    Tente d'abord `pip install -e .`, puis `pip install -e ./src` si le premier échoue
    et qu'un setup.py ou pyproject.toml existe dans src/.

    Args:
        project_root (str): Le chemin racine du projet.
        conda_env_name (str): Le nom de l'environnement Conda.

    Returns:
        bool: True si l'installation a réussi, False sinon.
    """
    logging.info(f"Début de l'installation des dépendances du projet dans '{project_root}' pour l'environnement '{conda_env_name}'.")

    # Commande 1: pip install -e .
    pip_command_root = ['python', '-m', 'pip', 'install', '-e', '.']
    logging.info("Tentative d'installation des dépendances avec 'pip install -e .'")
    if _run_command_in_conda_env(conda_env_name, pip_command_root, project_root):
        logging.info("Dépendances installées avec succès via 'pip install -e .'.")
        return True
    
    logging.warning("'pip install -e .' a échoué ou n'a rien installé. Vérification de la présence de setup.py/pyproject.toml dans src/.")

    # Vérifier si setup.py ou pyproject.toml existe dans src/
    src_path = os.path.join(project_root, 'src')
    setup_py_in_src = os.path.exists(os.path.join(src_path, 'setup.py'))
    pyproject_toml_in_src = os.path.exists(os.path.join(src_path, 'pyproject.toml'))

    if os.path.isdir(src_path) and (setup_py_in_src or pyproject_toml_in_src):
        logging.info(f"Un fichier {'setup.py' if setup_py_in_src else 'pyproject.toml'} a été trouvé dans '{src_path}'.")
        logging.info("Tentative d'installation des dépendances avec 'pip install -e ./src'")
        
        # Commande 2: pip install -e ./src (exécutée depuis project_root, pip s'occupe du ./src)
        pip_command_src = ['python', '-m', 'pip', 'install', '-e', './src']
        if _run_command_in_conda_env(conda_env_name, pip_command_src, project_root):
            logging.info("Dépendances installées avec succès via 'pip install -e ./src'.")
            return True
        else:
            logging.error("Échec de l'installation des dépendances via 'pip install -e ./src'.")
            return False
    else:
        logging.warning(f"Aucun répertoire 'src' avec 'setup.py' ou 'pyproject.toml' trouvé, ou 'pip install -e .' a déjà échoué.")
        logging.error("Impossible d'installer les dépendances du projet via pip editable install.")
        return False

if __name__ == '__main__':
    # Exemple d'utilisation (à des fins de test uniquement)
    # Assurez-vous que cet exemple est adapté à votre structure de projet et à votre environnement Conda
    current_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    test_conda_env_name = "epita_symbolic_ai" # Remplacez par le nom de votre environnement de test

    logging.info(f"Test du module run_pip_commands.py avec project_root='{current_project_root}' et conda_env_name='{test_conda_env_name}'")
    
    # Créer un faux setup.py pour le test si nécessaire
    mock_setup_py_path = os.path.join(current_project_root, "setup.py")
    is_mock_setup_created = False
    if not os.path.exists(mock_setup_py_path):
        logging.info(f"Création d'un fichier setup.py factice pour le test : {mock_setup_py_path}")
        with open(mock_setup_py_path, "w") as f:
            f.write("# Fichier setup.py factice pour les tests\n")
            f.write("from setuptools import setup, find_packages\n")
            f.write("setup(name='test_project', version='0.1', packages=find_packages())\n")
        is_mock_setup_created = True

    success = install_project_dependencies(current_project_root, test_conda_env_name)

    if success:
        logging.info("Test de install_project_dependencies réussi.")
    else:
        logging.error("Test de install_project_dependencies échoué.")

    # Nettoyer le faux setup.py
    if is_mock_setup_created:
        logging.info(f"Suppression du fichier setup.py factice : {mock_setup_py_path}")
        os.remove(mock_setup_py_path)

    # Test avec un setup.py dans src/
    mock_src_path = os.path.join(current_project_root, "src")
    mock_setup_py_in_src_path = os.path.join(mock_src_path, "setup.py")
    is_mock_src_setup_created = False
    if not os.path.exists(mock_src_path):
        os.makedirs(mock_src_path)
    
    # Supprimer le setup.py racine s'il existe pour forcer le test du src/
    if os.path.exists(mock_setup_py_path):
        os.remove(mock_setup_py_path) # Assurez-vous qu'il n'y a pas de setup.py à la racine

    if not os.path.exists(mock_setup_py_in_src_path):
        logging.info(f"Création d'un fichier setup.py factice pour le test dans src/ : {mock_setup_py_in_src_path}")
        with open(mock_setup_py_in_src_path, "w") as f:
            f.write("# Fichier setup.py factice dans src/ pour les tests\n")
            f.write("from setuptools import setup, find_packages\n")
            f.write("setup(name='test_project_src', version='0.1', packages=find_packages())\n")
        is_mock_src_setup_created = True
    
    logging.info(f"Test du module run_pip_commands.py avec setup.py dans src/")
    success_src = install_project_dependencies(current_project_root, test_conda_env_name)
    if success_src:
        logging.info("Test de install_project_dependencies (avec setup.py dans src/) réussi.")
    else:
        logging.error("Test de install_project_dependencies (avec setup.py dans src/) échoué.")

    if is_mock_src_setup_created:
        logging.info(f"Suppression du fichier setup.py factice dans src/ : {mock_setup_py_in_src_path}")
        os.remove(mock_setup_py_in_src_path)
    if os.path.exists(mock_src_path) and not os.listdir(mock_src_path): # Supprimer src s'il est vide
        os.rmdir(mock_src_path)