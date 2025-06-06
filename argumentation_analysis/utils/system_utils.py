# utils/system_utils.py
import sys
import importlib
import subprocess
import logging

logger = logging.getLogger("Utils.System")
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); logger.addHandler(handler); logger.setLevel(logging.INFO)


def ensure_directory_exists(directory_path):
    """
    Assure qu'un répertoire existe, le crée si nécessaire.
    
    Args:
        directory_path: Chemin du répertoire (str ou Path)
        
    Returns:
        bool: True si le répertoire existe ou a été créé, False sinon
    """
    from pathlib import Path
    
    # Convertir en Path si ce n'est pas déjà le cas
    path = Path(directory_path) if not isinstance(directory_path, Path) else directory_path
    
    # Si le chemin existe déjà
    if path.exists():
        # Vérifier que c'est bien un répertoire
        if path.is_dir():
            return True
        else:
            logger.error(f"Le chemin existe mais n'est pas un répertoire: {path}")
            return False
    
    # Créer le répertoire
    try:
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Répertoire créé: {path}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la création du répertoire {path}: {e}")
        return False

def get_project_root():
    """
    Récupère le chemin racine du projet.
    
    Returns:
        Path: Chemin racine du projet
    """
    from pathlib import Path
    import os
    
    # Obtenir le répertoire du script courant
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # Remonter de deux niveaux pour obtenir la racine du projet (depuis utils -> argumentation_analysis -> project_root)
    project_root = current_dir.parent.parent
    
    return project_root

def is_running_in_notebook():
    """
    Vérifie si le code est exécuté dans un notebook Jupyter.
    
    Returns:
        bool: True si exécuté dans un notebook, False sinon
    """
    import sys
    
    # Vérifier si le module ipykernel est présent dans les modules chargés
    return 'ipykernel' in sys.modules

def check_and_install(package_import_name: str, package_install_name: str):
    """Vérifie si un package est importable, sinon tente de l'installer."""
    try:
        importlib.import_module(package_import_name)
        logger.info(f"✔️ Dépendance '{package_import_name}' trouvée.")
        return True
    except ImportError:
        logger.warning(f"⚠️ Dépendance '{package_import_name}' manquante (package: {package_install_name}). Tentative d'installation...")
        try:
            # Utilisation de -q pour une sortie moins verbeuse, --disable-pip-version-check pour éviter les warnings
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check", package_install_name])
            logger.info(f"✅ {package_install_name} installé avec succès.")
            # Recharger les modules ou invalider les caches peut être nécessaire dans certains environnements
            importlib.invalidate_caches()
            importlib.import_module(package_import_name) # Re-tester l'import
            logger.info(f"✔️ {package_import_name} trouvé après installation.")
            return True
        except Exception as e:
            logger.error(f"❌ Échec de l'installation/import de {package_install_name}: {e}")
            logger.warning("‼️ Un redémarrage du noyau (Kernel -> Restart Kernel) peut être nécessaire si l'import échoue toujours.")
            return False

# Optionnel : Log de chargement
module_logger = logging.getLogger(__name__)
module_logger.debug("Module utils.system_utils chargé.")