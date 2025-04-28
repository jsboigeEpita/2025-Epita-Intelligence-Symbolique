# ui/config.py
import os
import logging
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

config_logger = logging.getLogger("App.UI.Config")
if not config_logger.handlers and not config_logger.propagate:
     handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); config_logger.addHandler(handler); config_logger.setLevel(logging.INFO)

# --- Chargement .env et Dérivation Clé ---
load_dotenv(find_dotenv())
PASSPHRASE_VAR_NAME = "TEXT_CONFIG_PASSPHRASE"
passphrase = os.getenv(PASSPHRASE_VAR_NAME)
ENCRYPTION_KEY = None
FIXED_SALT = b'q\x8b\t\x97\x8b\xe9\xa3\xf2\xe4\x8e\xea\xf5\xe8\xb7\xd6\x8c' # Sel fixe

config_logger.info(f"Vérification de la phrase secrète '{PASSPHRASE_VAR_NAME}' dans .env...")
if passphrase:
    config_logger.info(f"✅ Phrase secrète trouvée. Dérivation de la clé...")
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
    config_logger.warning(f"⚠️ Variable '{PASSPHRASE_VAR_NAME}' non trouvée dans .env. Chiffrement désactivé.")

# --- URLs et Chemins ---
TIKA_URL_PARTS = ["https:", "", "tika", "open-webui", "myia", "io", "tika"]
TIKA_SERVER_URL = f"{TIKA_URL_PARTS[0]}//{'.'.join(TIKA_URL_PARTS[2:-1])}/{TIKA_URL_PARTS[-1]}"
JINA_READER_PREFIX = "https://r.jina.ai/"

# Chemins relatifs au projet
_project_root = Path(__file__).parent.parent # Remonte de ui/ vers la racine
CACHE_DIR = _project_root / "text_cache"
CONFIG_DIR = _project_root / "data" # Fichier de config UI dans data/
CONFIG_FILE = CONFIG_DIR / "extract_sources.json.gz.enc"
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

# Définition initiale (utilisée si CONFIG_FILE non trouvé/déchiffrable)
EXTRACT_SOURCES = [
     {
         "source_name": "Lincoln-Douglas Débat 1 (NPS)", "source_type": "jina",
         "schema": "https:", "host_parts": ["www", "nps", "gov"], "path": "/liho/learn/historyculture/debate1.htm",
         "extracts": [
             {"extract_name": "1. Débat Complet (Ottawa, 1858)", "start_marker": "**August 21, 1858**", "end_marker": "(Three times three cheers were here given for Senator Douglas.)"},
             {"extract_name": "2. Discours Principal de Lincoln", "start_marker": "MY FELLOW-CITIZENS: When a man hears himself", "end_marker": "The Judge can take his half hour."},
             {"extract_name": "3. Discours d'Ouverture de Douglas", "start_marker": "Ladies and gentlemen: I appear before you", "end_marker": "occupy an half hour in replying to him."},
             {"extract_name": "4. Lincoln sur Droits Naturels/Égalité", "start_marker": "I will say here, while upon this subject,", "end_marker": "equal of every living man._ [Great applause.]"},
             {"extract_name": "5. Douglas sur Race/Dred Scott", "start_marker": "utterly opposed to the Dred Scott decision,", "end_marker": "equality with the white man. (\"Good.\")"},
         ]
     },
     {
         "source_name": "Lincoln-Douglas Débat 2 (NPS)", "source_type": "jina",
         "schema": "https:", "host_parts": ["www", "nps", "gov"], "path": "/liho/learn/historyculture/debate2.htm",
         "extracts": [
              {"extract_name": "1. Débat Complet (Freeport, 1858)", "start_marker": "It was a cloudy, cool, and damp day.", "end_marker": "I cannot, gentlemen, my time has expired."},
              {"extract_name": "2. Discours Principal de Douglas", "start_marker": "**Mr. Douglas' Speech**\n\nLadies and Gentlemen-", "end_marker": "stopped on the moment."},
              {"extract_name": "3. Discours d'Ouverture de Lincoln", "start_marker": "LADIES AND GENTLEMEN - On Saturday last,", "end_marker": "Go on, Judge Douglas."},
              {"extract_name": "4. Doctrine de Freeport (Douglas)", "start_marker": "The next question propounded to me by Mr. Lincoln is,", "end_marker": "satisfactory on that point."},
              {"extract_name": "5. Lincoln répond aux 7 questions", "start_marker": "The first one of these interrogatories is in these words:,", "end_marker": "aggravate the slavery question among ourselves. [Cries of good, good.]"},
         ]
     },
     {
         "source_name": "Kremlin Discours 21/02/2022", "source_type": "jina",
         "schema": "http:", "host_parts": ["en", "kremlin", "ru"], "path": "/events/president/transcripts/67828",
         "extracts": [
             {"extract_name": "1. Discours Complet", "start_marker": "Citizens of Russia, friends,", "end_marker": "Thank you."},
             {"extract_name": "2. Argument Historique Ukraine", "start_marker": "So, I will start with the fact that modern Ukraine", "end_marker": "He was its creator and architect."},
             {"extract_name": "3. Menace OTAN", "start_marker": "Ukraine is home to NATO training missions", "end_marker": "These principled proposals of ours have been ignored."},
             {"extract_name": "4. Décommunisation selon Poutine", "start_marker": "And today the “grateful progeny”", "end_marker": "what real decommunizations would mean for Ukraine."},
             {"extract_name": "5. Décision Reconnaissance Donbass", "start_marker": "Everything was in vain.", "end_marker": "These two documents will be prepared and signed shortly."},
            ]
     },
     {
         "source_name": "Hitler Discours Collection (PDF)", "source_type": "tika",
         "schema": "https:",
         "host_parts": ["drive", "google", "com"],
         "path": "/uc?export=download&id=1D6ZESrdeuWvlPlsNq0rbVaUyxqUOB-KQ",
         "extracts": [
             {"extract_name": "1. 1923.04.13 - Munich", "start_marker": "n our view, the times when", "end_marker": "build a new Germany!36"},
             {"extract_name": "2. 1923.04.24 - Munich", "start_marker": "reject the word 'Proletariat.'", "end_marker": "the greatest social achievement.38"},
             {"extract_name": "3. 1923.04.27 - Munich", "start_marker": "hat we need if we are to have", "end_marker": "the Germany of fighters which yet shall be."},
             {"extract_name": "4. 1933.03.23 - Duel Otto Wels", "start_marker": "You are talking today about your achievements", "end_marker": "Germany will be liberated, but not by you!125"},
             {"extract_name": "5. 1933.05.01 - Lustgarten", "start_marker": "hree cheers for our Reich President,", "end_marker": "thus our German Volk und Vaterland!”"},
             {"extract_name": "6. 1936.03.09 - Interview Ward Price", "start_marker": "irst question: Does the Fuhrer’s offer", "end_marker": "service to Europe and to the cause of peace.313"},
             {"extract_name": "7. 1936.03.12 - Karlsruhe", "start_marker": "know no regime of the bourgeoisie,", "end_marker": "now and for all time to come!316"},
             {"extract_name": "8. 1936.03.20 - Hambourg", "start_marker": "t is a pity that the statesmen-", "end_marker": "now give me your faith!"},
             {"extract_name": "9. 1939.01.30 - Reichstag (Prophétie)", "start_marker": "Once again I will be a prophet:", "end_marker": "complementary nature of these economies to the German one.549"},
             {"extract_name": "10. 1942.11.09 - Löwenbräukeller", "start_marker": "care of this. This danger has been recognized", "end_marker": "will always be a prayer for our Germany!"},
         ]
     },
]

# --- État Global (pour ce module UI) ---
# Note: Utiliser global ici est une simplification liée à la structure UI originale.
# Une approche plus orientée objet pourrait encapsuler cela.
current_extract_definitions = [] # Sera peuplé par load_extract_definitions

config_logger.info(f"Config UI chargée. {len(EXTRACT_SOURCES)} sources initiales définies.")