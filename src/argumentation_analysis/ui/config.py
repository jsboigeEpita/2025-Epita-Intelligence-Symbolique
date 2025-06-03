"""
Configuration pour l'interface utilisateur (UI) du module d'analyse d'argumentation.

Ce module centralise la configuration relative à l'interface utilisateur,
y compris :
- La gestion de la clé de chiffrement pour les fichiers de configuration.
- Les chemins vers les répertoires de cache, de configuration et temporaires.
- Les URLs et timeouts pour les services externes (Tika, Jina).
- Les extensions de fichiers considérées comme du texte brut.
- Le chargement initial des définitions de sources d'extraction.
"""
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
# Import pour la fonction de chargement JSON mutualisée
from project_core.utils.file_utils import load_json_file

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
tika_url = os.getenv("TIKA_SERVER_ENDPOINT", "https://tika.open-webui.myia.io/tika")
TIKA_SERVER_URL = tika_url if tika_url.endswith('/tika') else f"{tika_url.rstrip('/')}/tika"
TIKA_SERVER_TIMEOUT = int(os.getenv("TIKA_SERVER_TIMEOUT", "30"))
config_logger.info(f"URL du serveur Tika: {TIKA_SERVER_URL}")
JINA_READER_PREFIX = "https://r.jina.ai/"

# Chemins relatifs au projet
_project_root = Path(__file__).parent.parent # Remonte de ui/ vers la racine
CACHE_DIR = _project_root / "text_cache"
CONFIG_DIR = _project_root / DATA_DIR # Fichier de config UI dans data/
CONFIG_FILE_JSON = CONFIG_DIR / "extract_sources.json" # Chemin vers le fichier JSON non chiffré
CONFIG_FILE_ENC = CONFIG_DIR / "extract_sources.json.gz.enc" # Chemin vers le futur fichier chiffré
CONFIG_FILE = CONFIG_FILE_ENC  # Variable utilisée par app.py pour charger les définitions
TEMP_DOWNLOAD_DIR = _project_root / "temp_downloads" # Pour cache brut Tika

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

# Tentative de chargement des sources depuis le fichier chiffré (logique conservée mais adaptée)
# ou depuis le fichier JSON non chiffré si le chiffré n'existe pas ou si la clé est absente.

# Note: La logique de migration de JSON vers chiffré est complexe et dépend de file_operations.
# Pour l'instant, cette section se concentre sur le chargement.
# La migration pourrait être une étape séparée ou gérée par file_operations.

# Priorité au fichier chiffré si la clé existe
if ENCRYPTION_KEY and CONFIG_FILE_ENC.exists():
    try:
        config_logger.info(f"Tentative de chargement depuis le fichier chiffré {CONFIG_FILE_ENC.name}...")
        from .file_operations import load_extract_definitions # Import local
        loaded_sources = load_extract_definitions(CONFIG_FILE_ENC, ENCRYPTION_KEY)
        if loaded_sources: # load_extract_definitions retourne une liste ou None (ou les défauts en cas d'erreur)
            EXTRACT_SOURCES = loaded_sources
            config_logger.info(f"✅ Définitions chargées depuis le fichier chiffré {CONFIG_FILE_ENC.name}.")
        else:
            # Si load_extract_definitions retourne None/vide à cause d'une erreur interne gérée,
            # EXTRACT_SOURCES reste sur DEFAULT_EXTRACT_SOURCES ou ce que load_extract_definitions a retourné.
            config_logger.warning(f"⚠️ Échec ou retour vide du chargement depuis le fichier chiffré {CONFIG_FILE_ENC.name}. Vérifier logs de file_operations.")
            # Si load_extract_definitions a déjà loggué et retourné DEFAULT_EXTRACT_SOURCES, ce log est redondant.
            # Si elle retourne None, alors EXTRACT_SOURCES sera None, ce qui n'est pas souhaité.
            # Assurons-nous que EXTRACT_SOURCES a une valeur par défaut si loaded_sources est None.
            if EXTRACT_SOURCES is None: # S'assurer qu'on ne reste pas avec None
                 EXTRACT_SOURCES = DEFAULT_EXTRACT_SOURCES
                 config_logger.info("Rétablissement des sources par défaut après échec de chargement chiffré.")

    except Exception as e:
        config_logger.error(f"❌ Erreur majeure lors du chargement du fichier chiffré {CONFIG_FILE_ENC.name}: {e}", exc_info=True)
        EXTRACT_SOURCES = DEFAULT_EXTRACT_SOURCES # Rétablir les valeurs par défaut en cas d'erreur majeure
# Sinon, si le fichier JSON non chiffré existe, l'utiliser
elif CONFIG_FILE_JSON.exists():
    config_logger.info(f"Chargement depuis le fichier JSON non chiffré {CONFIG_FILE_JSON.name}...")
    loaded_json_sources = load_json_file(CONFIG_FILE_JSON) # Utilisation de la fonction mutualisée
    if isinstance(loaded_json_sources, list):
        EXTRACT_SOURCES = loaded_json_sources
        config_logger.info(f"✅ Configuration chargée depuis {CONFIG_FILE_JSON.name} (non chiffré).")
        # Ici, on pourrait envisager de déclencher la migration vers le chiffré si ENCRYPTION_KEY est dispo
        if ENCRYPTION_KEY:
            config_logger.info(f"Migration suggérée: {CONFIG_FILE_JSON.name} existe, {CONFIG_FILE_ENC.name} non (ou échec chargement), et clé disponible.")
            # La logique de migration active est commentée pour se concentrer sur le chargement.
            # from .file_operations import save_extract_definitions
            # save_extract_definitions(EXTRACT_SOURCES, CONFIG_FILE_ENC, ENCRYPTION_KEY, embed_full_text=False)
            # CONFIG_FILE_JSON.unlink() # etc.
    elif loaded_json_sources is None: # Erreur de chargement gérée par load_json_file
        config_logger.warning(f"⚠️ Échec du chargement depuis {CONFIG_FILE_JSON.name} (retour None). Utilisation des définitions par défaut.")
        EXTRACT_SOURCES = DEFAULT_EXTRACT_SOURCES
    else: # Cas où ce n'est ni une liste ni None (ex: un dict à la racine non attendu ici)
        config_logger.warning(f"⚠️ Données depuis {CONFIG_FILE_JSON.name} ne sont pas une liste (type: {type(loaded_json_sources)}). Utilisation des définitions par défaut.")
        EXTRACT_SOURCES = DEFAULT_EXTRACT_SOURCES
# Si aucun fichier de configuration n'est trouvé ou chargé avec succès
else:
    config_logger.warning(f"⚠️ Aucun fichier de configuration ({CONFIG_FILE_ENC.name} ou {CONFIG_FILE_JSON.name}) trouvé ou chargé. Utilisation des définitions par défaut.")
    EXTRACT_SOURCES = DEFAULT_EXTRACT_SOURCES


# --- État Global (pour ce module UI) ---
# Note: Utiliser global ici est une simplification liée à la structure UI originale.
# Une approche plus orientée objet pourrait encapsuler cela.
current_extract_definitions = [] # Sera peuplé par load_extract_definitions (de file_operations)

config_logger.info(f"Config UI initialisée. {len(EXTRACT_SOURCES)} sources chargées.")