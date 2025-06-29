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

PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent # Devrait pointer vers d:/2025-Epita-Intelligence-Symbolique

# Chemin racine du module argumentation_analysis
ROOT_DIR = Path(__file__).resolve().parent # Devrait pointer vers d:/2025-Epita-Intelligence-Symbolique/argumentation_analysis

# Chemins des répertoires principaux (relatifs à ROOT_DIR ou PROJECT_ROOT_DIR selon le contexte)
# Pour la configuration interne au package, ROOT_DIR est souvent utilisé.
# Pour les éléments à la racine du projet (comme _temp, portable_jdk), PROJECT_ROOT_DIR est nécessaire.
CONFIG_DIR = ROOT_DIR / CONFIG_DIR_NAME
DATA_DIR = ROOT_DIR / DATA_DIR_NAME # Données spécifiques au module
LIBS_DIR = PROJECT_ROOT_DIR / LIBS_DIR_NAME / "tweety" # Les libs Tweety sont dans libs/tweety/
NATIVE_LIBS_DIR = LIBS_DIR / "tweety" / "native" # Les DLLs natives sont dans libs/tweety/native
RESULTS_DIR = PROJECT_ROOT_DIR / RESULTS_DIR_NAME # Les résultats sont souvent au niveau projet

# Chemins des fichiers de configuration
ENV_FILE = PROJECT_ROOT_DIR / ".env" # .env est typiquement à la racine du projet
CONFIG_FILE = CONFIG_DIR / "settings.json"

# Chemins des fichiers de données
EXTRACT_SOURCES_FILE = DATA_DIR / "extract_sources.json.gz.enc" # Données spécifiques au module

# Répertoires au niveau du projet qui pourraient être utiles
PORTABLE_JDK_PARENT_DIR_FROM_PATHS = PROJECT_ROOT_DIR / "portable_jdk"
TEMP_DIR_FROM_PATHS = PROJECT_ROOT_DIR / "_temp"


# Assurer que les répertoires existent
def ensure_directories_exist():
    """Crée les répertoires nécessaires s'ils n'existent pas."""
    directories = [
        CONFIG_DIR,
        DATA_DIR,
        PROJECT_ROOT_DIR / LIBS_DIR_NAME, # Assurer que le répertoire parent 'libs' existe
        LIBS_DIR, # Sera 'libs/'
        LIBS_DIR / "tweety", # Assurer que 'libs/tweety' existe pour les DLLs natives
        NATIVE_LIBS_DIR, # Sera 'libs/tweety/native'
        RESULTS_DIR,
        PORTABLE_JDK_PARENT_DIR_FROM_PATHS, # Assurer que portable_jdk existe
        TEMP_DIR_FROM_PATHS # Assurer que _temp existe
    ]
    
    for directory in directories:
        try:
            directory.mkdir(exist_ok=True)
            logger.debug(f"Répertoire assuré: {directory}")
        except Exception as e:
            logger.warning(f"Impossible de créer le répertoire {directory}: {e}")

def get_project_root() -> Path:
    """Retourne le chemin racine du projet."""
    return PROJECT_ROOT_DIR


# Créer les répertoires au moment de l'importation du module
ensure_directories_exist()