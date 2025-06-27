# argumentation_analysis/ui/config.py
# Fichier de compatibilité - Remplacé par le système de configuration centralisé.
# Ce fichier maintient les anciennes constantes en les chargeant depuis `settings`
# pour assurer le fonctionnement du code existant sans refactoring immédiat.

import logging
from pathlib import Path
import warnings

# Importer l'objet de configuration central
from argumentation_analysis.config.settings import settings

# --- Logger ---
config_logger = logging.getLogger("App.UI.Config")
warnings.warn(
    "Le module 'argumentation_analysis.ui.config' est obsolète. "
    "Utilisez directement 'argumentation_analysis.config.settings'.",
    DeprecationWarning,
    stacklevel=2
)

# --- Constantes de base ---
_project_root = Path(__file__).resolve().parents[2] # ui -> argumentation_analysis -> racine
PROJECT_ROOT = _project_root

# --- Ré-exportation des configurations depuis `settings` ---

# URLs et Timeouts
TIKA_SERVER_URL = str(settings.tika.server_endpoint)
TIKA_SERVER_TIMEOUT = settings.tika.server_timeout
JINA_READER_PREFIX = str(settings.jina.reader_prefix)

# Passphrase et clé (compatibilité)
# NOTE: La dérivation de clé est maintenant gérée dans `core.utils.crypto_utils`.
# Ces valeurs sont fournies pour une compatibilité de base si d'anciens scripts les attendent.
TEXT_CONFIG_PASSPHRASE = settings.passphrase.get_secret_value() if settings.passphrase else None
ENCRYPTION_KEY = settings.encryption_key.get_secret_value() if settings.encryption_key else None

# Chemins de répertoires
# Utilise les valeurs de `settings.ui` et construit des chemins absolus si nécessaire.
# Correction pour robustesse aux tests : si `settings` est un mock, `settings.ui.temp_download_dir`
# ne sera pas une chaîne et l'opérateur de chemin plantera. On vérifie le type
# et on fournit une valeur par défaut si ce n'est pas une chaîne.
temp_dir_value = settings.ui.temp_download_dir
if not isinstance(temp_dir_value, str):
    temp_dir_value = "_temp/downloads_mock" # Valeur par défaut sûre pour les tests
TEMP_DOWNLOAD_DIR = PROJECT_ROOT / temp_dir_value

# Les répertoires suivants sont conservés pour compatibilité s'ils sont importés ailleurs.
CACHE_DIR = PROJECT_ROOT / "_temp" / "text_cache"
CONFIG_DIR = PROJECT_ROOT / "argumentation_analysis" / "data"

# Fichiers de configuration
CONFIG_FILE_JSON = CONFIG_DIR / "extract_sources.json"
CONFIG_FILE_ENC = CONFIG_DIR / "extract_sources.json.gz.enc"
CONFIG_FILE = CONFIG_FILE_ENC # L'ancien code pointait vers le fichier chiffré

# Extensions de fichiers
PLAINTEXT_EXTENSIONS = settings.ui.plaintext_extensions

# Sources par défaut (conservé si l'ancien code en dépend)
DEFAULT_EXTRACT_SOURCES = [
    {"source_name": "Exemple Vide (Config manquante)", "source_type": "jina",
     "schema": "https:", "host_parts": ["example", "com"], "path": "/",
     "extracts": []}
]
EXTRACT_SOURCES = DEFAULT_EXTRACT_SOURCES # Maintenir l'initialisation

# --- Création des répertoires (conservé pour exécution "autonome") ---
try:
    TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_logger.info(f"Répertoires de compatibilité assurés: {TEMP_DOWNLOAD_DIR}, {CACHE_DIR}, {CONFIG_DIR}")
except Exception as e:
    config_logger.error(f"Erreur création répertoires de compatibilité: {e}")

config_logger.info("Module de configuration UI (obsolète) initialisé en mode compatibilité.")