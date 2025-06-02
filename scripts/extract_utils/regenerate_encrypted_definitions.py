"""
Script pour reconstituer le fichier chiffré extract_sources.json.gz.enc
à partir des métadonnées JSON fournies.
"""
import os
import sys
import json
import gzip
from pathlib import Path

# Ajoute le répertoire parent (racine du projet) au sys.path
# pour permettre les imports comme argumentation_analysis.services.xxx
current_script_path = os.path.abspath(__file__)
scripts_dir = os.path.dirname(current_script_path)
project_root = os.path.dirname(scripts_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Imports des modules du projet
try:
    from argumentation_analysis.services.crypto_service import CryptoService as RealCryptoService
    from argumentation_analysis.ui.config import ENCRYPTION_KEY # TEXT_CONFIG_PASSPHRASE n'est pas exportée et cause une erreur
except ImportError as e:
    print(f"Erreur d'importation des modules nécessaires: {e}")
    print("Veuillez vous assurer que le script est exécuté depuis la racine du projet et que l'environnement est correctement configuré.")
    sys.exit(1)

# Métadonnées JSON à utiliser
METADATA_JSON = [
  {
    "source_name": "Lincoln-Douglas DAcbat 1 (NPS)",
    "source_type": "jina",
    "schema": "https",
    "host_parts": [
      "www",
      "nps",
      "gov"
    ],
    "path": "/liho/learn/historyculture/debate1.htm",
    "extracts": [
      {
        "extract_name": "1. DAcbat Complet (Ottawa, 1858)",
        "start_marker": "**August 21, 1858**",
        "end_marker": "(Three times three cheers were here given for Senator Douglas.)"
      },
      {
        "extract_name": "2. Discours Principal de Lincoln",
        "start_marker": "MY FELLOW-CITIZENS: When a man hears himself",
        "end_marker": "The Judge can take his half hour."
      },
      {
        "extract_name": "3. Discours d'Ouverture de Douglas",
        "start_marker": "Ladies and gentlemen: I appear before you",
        "end_marker": "occupy an half hour in replying to him."
      },
      {
        "extract_name": "4. Lincoln sur Droits Naturels/A%galitAc",
        "start_marker": "I will say here, while upon this subject,",
        "end_marker": "equal of every living man._ [Great applause.]"
      },
      {
        "extract_name": "5. Douglas sur Race/Dred Scott",
        "start_marker": "utterly opposed to the Dred Scott decision,",
        "end_marker": "equality with the white man. (\"Good.\")"
      }
    ]
  },
  {
    "source_name": "Lincoln-Douglas DAcbat 2 (NPS)",
    "source_type": "jina",
    "schema": "https",
    "host_parts": [
      "www",
      "nps",
      "gov"
    ],
    "path": "/liho/learn/historyculture/debate2.htm",
    "extracts": [
      {
        "extract_name": "1. DAcbat Complet (Freeport, 1858)",
        "start_marker": "It was a cloudy, cool, and damp day.",
        "end_marker": "I cannot, gentlemen, my time has expired."
      },
      {
        "extract_name": "2. Discours Principal de Douglas",
        "start_marker": "**Mr. Douglas' Speech**\\n\\nLadies and Gentlemen-",
        "end_marker": "stopped on the moment."
      },
      {
        "extract_name": "3. Discours d'Ouverture de Lincoln",
        "start_marker": "LADIES AND GENTLEMEN - On Saturday last,",
        "end_marker": "Go on, Judge Douglas."
      },
      {
        "extract_name": "4. Doctrine de Freeport (Douglas)",
        "start_marker": "The next question propounded to me by Mr. Lincoln is,",
        "end_marker": "satisfactory on that point."
      },
      {
        "extract_name": "5. Lincoln rAcpond aux 7 questions",
        "start_marker": "The first one of these interrogatories is in these words:,",
        "end_marker": "aggravate the slavery question among ourselves. [Cries of good, good.]"
      }
    ]
  },
  {
    "source_name": "Kremlin Discours 21/02/2022",
    "source_type": "jina",
    "schema": "http",
    "host_parts": [
      "en",
      "kremlin",
      "ru"
    ],
    "path": "/events/president/transcripts/67828",
    "extracts": [
      {
        "extract_name": "1. Discours Complet",
        "start_marker": "Citizens of Russia, friends,",
        "end_marker": "Thank you."
      },
      {
        "extract_name": "2. Argument Historique Ukraine",
        "start_marker": "So, I will start with the fact that modern Ukraine",
        "end_marker": "He was its creator and architect."
      },
      {
        "extract_name": "3. Menace OTAN",
        "start_marker": "Ukraine is home to NATO training missions",
        "end_marker": "These principled proposals of ours have been ignored."
      },
      {
        "extract_name": "4. DAccommunisation selon Poutine",
        "start_marker": "And today the \"grateful progeny\"",
        "end_marker": "what real decommunizations would mean for Ukraine."
      },
      {
        "extract_name": "5. DAccision Reconnaissance Donbass",
        "start_marker": "Everything was in vain.",
        "end_marker": "These two documents will be prepared and signed shortly."
      }
    ]
  },
  {
    "source_name": "Hitler Discours Collection (PDF)",
    "source_type": "tika",
    "schema": "https",
    "host_parts": [
      "drive",
      "google",
      "com"
    ],
    "path": "/uc?export=download&id=1D6ZESrdeuWvlPlsNq0rbVaUyxqUOB-KQ",
    "extracts": [
      {
        "extract_name": "1. 1923.04.13 - Munich",
        "start_marker": "In our view, the times when",
        "end_marker": "build a new Germany!36",
        "template_start": "I{0}"
      },
      {
        "extract_name": "2. 1923.04.24 - Munich",
        "start_marker": "reject the word 'Proletariat.'",
        "end_marker": "the greatest social achievement.38"
      },
      {
        "extract_name": "3. 1923.04.27 - Munich",
        "start_marker": "What we need if we are to have",
        "end_marker": "the Germany of fighters which yet shall be.",
        "template_start": "W{0}"
      },
      {
        "extract_name": "4. 1933.03.23 - Duel Otto Wels",
        "start_marker": "You are talking today about your achievements",
        "end_marker": "Germany will be liberated, but not by you!125"
      },
      {
        "extract_name": "5. 1933.05.01 - Lustgarten",
        "start_marker": "Three cheers for our Reich President,",
        "end_marker": "thus our German Volk und Vaterland!",
        "template_start": "T{0}"
      },
      {
        "extract_name": "6. 1936.03.09 - Interview Ward Price",
        "start_marker": "First question: Does the Fuhrer's offer",
        "end_marker": "service to Europe and to the cause of peace.313",
        "template_start": "F{0}"
      },
      {
        "extract_name": "7. 1936.03.12 - Karlsruhe",
        "start_marker": "Iknow no regime of the bourgeoisie,",
        "end_marker": "now and for all time to come!316",
        "template_start": "I{0}"
      },
      {
        "extract_name": "8. 1936.03.20 - Hambourg",
        "start_marker": "It is a pity that the statesmen-",
        "end_marker": "now give me your faith!",
        "template_start": "I{0}"
      },
      {
        "extract_name": "9. 1939.01.30 - Reichstag (ProphActie)",
        "start_marker": "Once again I will be a prophet:",
        "end_marker": "complementary nature of these economies to the German one.549"
      },
      {
        "extract_name": "10. 1942.11.09 - LAwenbrAukeller",
        "start_marker": "Icare of this. This danger has been recognized",
        "end_marker": "will always be a prayer for our Germany!",
        "template_start": "I{0}"
      }
    ]
  }
]

# Chemin de sortie du fichier chiffré
OUTPUT_FILE_PATH = Path(project_root) / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"

def main():
    """
    Fonction principale du script.
    """
    print("Début de la regénération du fichier chiffré...")

    # La variable ENCRYPTION_KEY est directement importée depuis config.py.
    # config.py est responsable de la dériver à partir de la variable d'environnement TEXT_CONFIG_PASSPHRASE.
    # Pour que ce script fonctionne comme attendu (avec la passphrase "Propaganda"),
    # il faut que la variable d'environnement TEXT_CONFIG_PASSPHRASE soit "Propaganda"
    # lorsque config.py est exécuté (au moment de l'import).
    # Les logs de l'exécution précédente confirment que la clé est trouvée et dérivée.
    print("Utilisation de ENCRYPTION_KEY importée depuis argumentation_analysis.ui.config.")

    if not ENCRYPTION_KEY:
        print("ERREUR: ENCRYPTION_KEY n'est pas définie. Impossible de chiffrer.")
        sys.exit(1)

    # Initialiser CryptoService
    crypto_service = RealCryptoService(encryption_key=ENCRYPTION_KEY)
    print("RealCryptoService initialisé.")

    # Préparer les données (elles le sont déjà)
    definitions_data = METADATA_JSON
    print(f"{len(definitions_data)} sources de définitions à traiter.")

    # Convertir en JSON, compresser et chiffrer
    print("Conversion en JSON, compression et chiffrement des données...")
    try:
        # La méthode encrypt_and_compress_json fait exactement ce qu'il faut:
        # 1. Convertit `definitions_data` en une chaîne JSON.
        # 2. Encode cette chaîne en UTF-8.
        # 3. Compresse les bytes résultants avec gzip.
        # 4. Chiffre les bytes compressés.
        encrypted_gzipped_data = crypto_service.encrypt_and_compress_json(definitions_data)

        if encrypted_gzipped_data is None:
            print("ERREUR: Le chiffrement et la compression ont échoué (résultat None).")
            sys.exit(1)
        print("Données chiffrées et compressées avec succès.")

    except Exception as e:
        print(f"ERREUR lors du chiffrement et de la compression: {e}")
        sys.exit(1)

    # Écrire le résultat dans le fichier de sortie
    try:
        OUTPUT_FILE_PATH.parent.mkdir(parents=True, exist_ok=True) # Assurer que le répertoire data existe
        with open(OUTPUT_FILE_PATH, 'wb') as f_out:
            f_out.write(encrypted_gzipped_data)
        print(f"Fichier chiffré sauvegardé avec succès dans: {OUTPUT_FILE_PATH}")
    except IOError as e:
        print(f"ERREUR lors de l'écriture du fichier de sortie {OUTPUT_FILE_PATH}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERREUR inattendue lors de l'écriture du fichier: {e}")
        sys.exit(1)

    print("Script terminé avec succès.")

if __name__ == "__main__":
    main()