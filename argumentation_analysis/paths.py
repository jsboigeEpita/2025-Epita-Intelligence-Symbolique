"""
Module de gestion centralisée des chemins du projet.

Ce module définit tous les chemins utilisés dans le projet et assure
que les répertoires nécessaires existent.
"""

from pathlib import Path
import logging

# Définition des noms de répertoires
CONFIG_DIR_NAME = "config"
DATA_DIR_NAME = "data"
LIBS_DIR_NAME = "libs"
RESULTS_DIR_NAME = "results"

logger = logging.getLogger("Paths")
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Chemin racine du projet
ROOT_DIR = Path(__file__).parent

# Chemins des répertoires principaux
CONFIG_DIR = ROOT_DIR / CONFIG_DIR_NAME  # Pour les fichiers de configuration
DATA_DIR = ROOT_DIR / DATA_DIR_NAME      # Pour les données et ressources
LIBS_DIR = ROOT_DIR / LIBS_DIR_NAME
NATIVE_LIBS_DIR = LIBS_DIR / "native"
RESULTS_DIR = ROOT_DIR / RESULTS_DIR_NAME

# Chemins des fichiers de configuration
ENV_FILE = ROOT_DIR / ".env"
CONFIG_FILE = CONFIG_DIR / "settings.json"  # Exemple

# Chemins des fichiers de données
EXTRACT_SOURCES_FILE = DATA_DIR / "extract_sources.json.gz.enc"

# Assurer que les répertoires existent
def ensure_directories_exist():
    """Crée les répertoires nécessaires s'ils n'existent pas."""
    directories = [CONFIG_DIR, DATA_DIR, LIBS_DIR, NATIVE_LIBS_DIR, RESULTS_DIR]
    
    for directory in directories:
        try:
            directory.mkdir(exist_ok=True)
            logger.debug(f"Répertoire assuré: {directory}")
        except Exception as e:
            logger.warning(f"Impossible de créer le répertoire {directory}: {e}")

# Créer les répertoires au moment de l'importation du module
ensure_directories_exist()