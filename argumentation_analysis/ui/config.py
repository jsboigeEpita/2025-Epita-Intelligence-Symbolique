# ui/config.py
import os
import logging
from pathlib import Path
from dotenv import load_dotenv, find_dotenv # Gardé au cas où d'autres variables .env sont utilisées
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import json
from argumentation_analysis.paths import DATA_DIR
# Import pour la fonction de chargement JSON mutualisée (chemin corrigé)
from argumentation_analysis.utils.core_utils.file_utils import load_json_file

config_logger = logging.getLogger("App.UI.Config")
if not config_logger.handlers and not config_logger.propagate:
     handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); config_logger.addHandler(handler); config_logger.setLevel(logging.INFO)

# --- Chargement .env et Dérivation Clé ---
load_dotenv(find_dotenv()) # Gardé au cas où d'autres variables .env sont utilisées

# MODIFICATION: Utiliser directement "Propaganda" comme passphrase
TEXT_CONFIG_PASSPHRASE = "Propaganda"
passphrase = TEXT_CONFIG_PASSPHRASE # Assignation directe
ENCRYPTION_KEY = None
FIXED_SALT = b'q\x8b\t\x97\x8b\xe9\xa3\xf2\xe4\x8e\xea\xf5\xe8\xb7\xd6\x8c' # Sel fixe

config_logger.info(f"Utilisation de la phrase secrète fixe pour la dérivation de la clé.")
if passphrase: # Cette condition sera toujours vraie maintenant
    config_logger.info(f"✅ Phrase secrète définie sur \"{passphrase}\". Dérivation de la clé...")
    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), length=32, salt=FIXED_SALT,
            iterations=480000, backend=default_backend()
        )
        derived_key_raw = kdf.derive(passphrase.encode('utf-8'))
        ENCRYPTION_KEY = base64.urlsafe_b64encode(derived_key_raw)
        if ENCRYPTION_KEY: config_logger.info("✅ Clé de chiffrement dérivée et encodée.")
    except Exception as e:
        config_logger.error(f"⚠️ Erreur dérivation clé : {e}. Chiffrement désactivé.", exc_info=True)
        ENCRYPTION_KEY = None
else:
    # Ce bloc ne devrait plus être atteint car passphrase est maintenant fixée.
    config_logger.critical(f"⚠️ La phrase secrète n'est pas définie malgré la modification. Problème inattendu.")
    ENCRYPTION_KEY = None

# --- URLs et Chemins ---
# Utiliser l'URL du serveur Tika depuis le fichier .env ou utiliser l'URL par défaut
# Assurez-vous que l'URL du serveur Tika se termine par '/tika'
tika_url_from_env = os.getenv("TIKA_SERVER_ENDPOINT")
if tika_url_from_env:
    # Nettoyer les guillemets potentiels au début/fin et s'assurer que c'est une chaîne
    tika_url = str(tika_url_from_env).strip('"')
    config_logger.info(f"TIKA_SERVER_ENDPOINT depuis .env (nettoyé): '{tika_url}'")
else:
    tika_url = "https://tika.open-webui.myia.io/tika" # Valeur par défaut si non définie
    config_logger.info(f"TIKA_SERVER_ENDPOINT non trouvé dans .env, utilisation de la valeur par défaut: '{tika_url}'")

# S'assurer que l'URL se termine correctement par /tika
if tika_url.endswith('/tika'):
    TIKA_SERVER_URL = tika_url
else:
    TIKA_SERVER_URL = f"{tika_url.rstrip('/')}/tika"
TIKA_SERVER_TIMEOUT = int(os.getenv("TIKA_SERVER_TIMEOUT", "30"))
config_logger.info(f"URL du serveur Tika: {TIKA_SERVER_URL}")
JINA_READER_PREFIX = "https://r.jina.ai/"

# Chemins relatifs au projet
_project_root = Path(__file__).parent.parent.parent # Remonte de ui/ -> argumentation_analysis/ -> racine du projet
CACHE_DIR = _project_root / "_temp" / "text_cache" # Modifié
CONFIG_DIR = _project_root / "argumentation_analysis" / "data" # Maintenu ici (contient extract_sources.json.gz.enc)
CONFIG_FILE_JSON = CONFIG_DIR / "extract_sources.json"
CONFIG_FILE_ENC = CONFIG_DIR / "extract_sources.json.gz.enc"
CONFIG_FILE = CONFIG_FILE_ENC
TEMP_DOWNLOAD_DIR = _project_root / "_temp" / "temp_downloads" # Modifié

# Extensions texte simple
PLAINTEXT_EXTENSIONS = ['.txt', '.md', '.json', '.csv', '.xml', '.py', '.js', '.html', '.htm']

# Création des répertoires nécessaires
try:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    config_logger.info(f"Cache répertoire assuré : {CACHE_DIR.resolve()}")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True) # S'assurer que data/ existe
    config_logger.info(f"Répertoire config UI assuré : {CONFIG_DIR.resolve()}")
    TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    config_logger.info(f"Répertoire temporaire assuré : {TEMP_DOWNLOAD_DIR.resolve()}")
except Exception as e:
    config_logger.error(f"Erreur création répertoires (cache/config/temp): {e}")


# --- Définitions Sources par Défaut ---
DEFAULT_EXTRACT_SOURCES = [
    {"source_name": "Exemple Vide (Config manquante)", "source_type": "jina",
     "schema": "https:", "host_parts": ["example", "com"], "path": "/",
     "extracts": []}
]

# --- Chargement des Sources d'Extraction ---

# La fonction load_extract_sources est maintenant remplacée par l'utilisation directe de
# project_core.utils.file_utils.load_json_file où c'est nécessaire.
# La logique de chargement initiale des EXTRACT_SOURCES est adaptée ci-dessous.

EXTRACT_SOURCES = DEFAULT_EXTRACT_SOURCES # Initialisation par défaut

# La logique de chargement dynamique de EXTRACT_SOURCES sera gérée par les scripts appelants
# pour éviter les importations circulaires lors de l'initialisation du module.
# EXTRACT_SOURCES reste initialisé avec DEFAULT_EXTRACT_SOURCES.
config_logger.info(f"Config UI initialisée. EXTRACT_SOURCES est sur DEFAULT_EXTRACT_SOURCES. Le chargement dynamique est délégué.")

# --- État Global (pour ce module UI) ---
# current_extract_definitions n'est plus pertinent ici si le chargement est externe.
# Si d'autres parties de ui/ l'utilisaient, il faudrait revoir. Pour l'instant, on le commente/supprime.
# current_extract_definitions = []

config_logger.info(f"Module config.py initialisé. {len(EXTRACT_SOURCES)} sources par défaut disponibles dans EXTRACT_SOURCES.")

PROJECT_ROOT = _project_root
config_logger.info(f"PROJECT_ROOT exporté: {PROJECT_ROOT}")
