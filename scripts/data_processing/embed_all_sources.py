#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour s'assurer que toutes les sources dans une configuration d'extraits
ont leur texte source complet (`full_text`) embarqué.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
import json
# import base64 # Supprimé car la dérivation de clé est retirée de ce script
# from cryptography.hazmat.primitives import hashes # Supprimé
# from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC # Supprimé
# from cryptography.hazmat.backends import default_backend # Supprimé

# Assurer que le répertoire racine du projet est dans sys.path
# pour permettre les imports relatifs (ex: from argumentation_analysis.ui import utils)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    # Importer les fonctions load/save depuis file_operations
    from argumentation_analysis.ui.file_operations import load_extract_definitions, save_extract_definitions
    # Importer get_full_text_for_source depuis utils
    from argumentation_analysis.ui.utils import get_full_text_for_source
    # Importer les configurations UI si nécessaire (par exemple, pour TIKA_SERVER_URL)
    from argumentation_analysis.ui import config as ui_config
    # Importer ENCRYPTION_KEY directement depuis la configuration UI
    from argumentation_analysis.ui.config import ENCRYPTION_KEY as CONFIG_UI_ENCRYPTION_KEY
    # Importer la fonction sanitize_filename depuis project_core.utils
    from project_core.utils.file_utils import sanitize_filename, load_document_content
except ImportError as e:
    print(f"Erreur d'importation: {e}. Assurez-vous que le script est exécuté depuis la racine du projet "
          "et que l'environnement est correctement configuré.")
    sys.exit(1)

# Configuration du logging
log_dir = PROJECT_ROOT / "_temp" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file_path = log_dir / "embed_all_sources.log"

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(log_file_path, mode='a', encoding='utf-8'), # 'a' pour append
                        logging.StreamHandler(sys.stdout) # Garder les logs sur la console aussi
                    ])
logger = logging.getLogger(__name__)

# La fonction derive_key_from_passphrase est supprimée car ENCRYPTION_KEY de ui.config sera utilisée.
# FIXED_SALT n'est plus directement utilisé ici non plus.

# def derive_key_from_passphrase(passphrase: str) -> bytes:
#     """
#     Dérive une clé Fernet à partir d'une passphrase.
#     Utilise la même logique que le vrai code.
#     """
#     if not passphrase:
#         raise ValueError("Passphrase vide")
    
#     kdf = PBKDF2HMAC(
#         algorithm=hashes.SHA256(),
#         length=32,
#         salt=CONFIG_FIXED_SALT,  # Utilisation du sel importé
#         iterations=480000,
#         backend=default_backend()
#     )
#     derived_key_raw = kdf.derive(passphrase.encode('utf-8'))
#     return base64.urlsafe_b64encode(derived_key_raw)


def main():
    """
    Fonction principale du script.
    """
    parser = argparse.ArgumentParser(
        description="Embarque le texte source complet dans un fichier de configuration d'extraits."
    )
    parser.add_argument(
        "--input-config",
        type=Path,
        required=False, # Modifié pour ne plus être requis si --json-string ou --input-json-file est utilisé
        help="Chemin vers le fichier de configuration chiffré d'entrée (.json.gz.enc). Optionnel si --json-string ou --input-json-file est fourni."
    )
    parser.add_argument(
        "--json-string",
        type=str,
        default=None,
        help="Chaîne JSON contenant les définitions d'extraits. Prioritaire sur --input-config."
    )
    parser.add_argument(
        "--input-json-file",
        type=Path,
        default=None,
        help="Chemin vers un fichier JSON non chiffré contenant les définitions d'extraits. Prioritaire sur --json-string et --input-config."
    )
    parser.add_argument(
        "--output-config",
        type=Path,
        required=True,
        help="Chemin vers le fichier de configuration chiffré de sortie."
    )
    parser.add_argument(
        "--passphrase",
        type=str,
        default=None,
        help="Passphrase (OBSOLÈTE pour la dérivation de clé dans ce script, ENCRYPTION_KEY de ui.config est utilisée). "
             "Peut être gardé pour une vérification future ou si une interaction avec la passphrase est nécessaire ailleurs."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Écrase le fichier de sortie s'il existe déjà."
    )

    args = parser.parse_args()

    logger.info(f"Démarrage du script d'embarquement des sources.")
    if args.input_json_file:
        logger.info(f"Utilisation des définitions JSON fournies via --input-json-file: {args.input_json_file}")
    elif args.json_string:
        logger.info(f"Utilisation des définitions JSON fournies via --json-string.")
    elif args.input_config:
        logger.info(f"Fichier d'entrée (chiffré): {args.input_config}")
    else:
        logger.error("Aucune source de configuration d'entrée spécifiée (--input-json-file, --json-string, ou --input-config). Arrêt.")
        sys.exit(1)
    logger.info(f"Fichier de sortie: {args.output_config}")

    # 1. La configuration de l'application est gérée par ui_config
    # Plus besoin de charger explicitement app_config ici


    # 2. Obtenir la passphrase - N'est plus utilisé pour dériver la clé ici.
    # La clé ENCRYPTION_KEY de ui.config est directement utilisée.
    # passphrase = args.passphrase or os.getenv("TEXT_CONFIG_PASSPHRASE")
    # if not passphrase:
    #     logger.error("Passphrase non fournie (ni via --passphrase, ni via TEXT_CONFIG_PASSPHRASE). Arrêt.")
    #     sys.exit(1)
    # logger.info("Passphrase obtenue (pour information seulement).")

    # 3. Vérifier les fichiers d'entrée/sortie
    input_source_specified = args.input_json_file or args.json_string or args.input_config

    if not input_source_specified:
        logger.error("Aucune source de configuration d'entrée (--input-json-file, --json-string, ou --input-config) n'a été fournie. Arrêt.")
        sys.exit(1)

    if args.input_json_file and not args.input_json_file.exists():
        logger.error(f"Le fichier d'entrée JSON {args.input_json_file} n'existe pas. Arrêt.")
        sys.exit(1)
    elif args.input_config and not args.input_config.exists() and not args.json_string and not args.input_json_file:
         logger.error(f"Le fichier d'entrée chiffré {args.input_config} n'existe pas et aucune autre source n'est fournie. Arrêt.")
         sys.exit(1)

    if args.output_config.exists() and not args.force:
        logger.error(
            f"Le fichier de sortie {args.output_config} existe déjà. Utilisez --force pour l'écraser. Arrêt."
        )
        sys.exit(1)
    elif args.output_config.exists() and args.force:
        logger.warning(f"Le fichier de sortie {args.output_config} existe et sera écrasé (--force activé).")

    # Créer le répertoire parent pour le fichier de sortie s'il n'existe pas
    args.output_config.parent.mkdir(parents=True, exist_ok=True)

    # 4. Charger les définitions d'extraits
    extract_definitions = []
    # Utiliser directement la clé de chiffrement de ui.config
    encryption_key_to_use = CONFIG_UI_ENCRYPTION_KEY
    if not encryption_key_to_use:
        logger.error("ENCRYPTION_KEY n'est pas disponible depuis argumentation_analysis.ui.config. Impossible de continuer.")
        sys.exit(1)
    logger.info(f"Utilisation de ENCRYPTION_KEY directement depuis ui.config ('{encryption_key_to_use[:10].decode('utf-8', 'ignore')}...') pour toutes les opérations de chiffrement/déchiffrement.")

    if args.input_json_file:
        try:
            logger.info(f"Chargement des définitions d'extraits depuis le fichier JSON: {args.input_json_file}...")
            with open(args.input_json_file, 'r', encoding='utf-8') as f:
                extract_definitions = json.load(f)
            if not isinstance(extract_definitions, list):
                logger.error(f"Le fichier JSON {args.input_json_file} ne contient pas une liste de définitions. Arrêt.")
                sys.exit(1)
            logger.info(f"{len(extract_definitions)} définitions d'extraits chargées depuis {args.input_json_file}.")
        except json.JSONDecodeError as e:
            logger.error(f"Erreur lors du décodage du fichier JSON {args.input_json_file}: {e}. Arrêt.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du fichier JSON {args.input_json_file}: {e}. Arrêt.")
            sys.exit(1)
    elif args.json_string:
        try:
            logger.info("Chargement des définitions d'extraits depuis la chaîne JSON fournie...")
            extract_definitions = json.loads(args.json_string)
            if not isinstance(extract_definitions, list):
                logger.error("La chaîne JSON fournie ne contient pas une liste de définitions. Arrêt.")
                sys.exit(1)
            logger.info(f"{len(extract_definitions)} définitions d'extraits chargées depuis la chaîne JSON.")
        except json.JSONDecodeError as e:
            logger.error(f"Erreur lors du décodage de la chaîne JSON: {e}. Arrêt.")
            sys.exit(1)
    elif args.input_config: # Doit être un fichier chiffré
        try:
            logger.info(f"Chargement et déchiffrement des définitions d'extraits depuis: {args.input_config}...")
            loaded_defs = load_extract_definitions(
                config_file=args.input_config,
                key=encryption_key_to_use # Utilisation de la clé de ui.config
            )
            if not loaded_defs:
                 logger.warning(f"Aucune définition d'extrait trouvée ou erreur de chargement depuis {args.input_config}.")
                 extract_definitions = []
            else:
                extract_definitions = loaded_defs
            logger.info(f"{len(extract_definitions)} définitions d'extraits chargées et déchiffrées depuis le fichier.")
        except Exception as e:
            logger.error(f"Erreur lors du chargement ou du déchiffrement de {args.input_config}: {e}")
            sys.exit(1)
    else:
        # Ce cas ne devrait pas être atteint à cause des vérifications précédentes
        logger.error("Aucune source de configuration (fichier JSON, chaîne JSON, ou fichier chiffré) n'a été traitée. Arrêt.")
        sys.exit(1)

    # 5. Traiter chaque source_info
    updated_sources_count = 0
    sources_with_errors_count = 0

    for i, source_info in enumerate(extract_definitions):
        source_id = source_info.get('id', f"Source_{i+1}")
        logger.info(f"Traitement de la source: {source_id} ({source_info.get('type', 'N/A')}: {source_info.get('path', 'N/A')})")

        if source_info.get('full_text') and source_info['full_text'].strip():
            logger.info(f"  Le texte complet est déjà présent pour la source {source_id}.")
        else:
            logger.info(f"  Texte complet manquant pour la source {source_id}. Tentative de récupération...")
            try:
                # fetch_method = source_info.get("fetch_method", source_info.get("source_type")) # Ancienne logique
                current_source_type = source_info.get("source_type")
                current_fetch_method = source_info.get("fetch_method", current_source_type) # Garde la logique originale pour fetch_method si source_type n'est pas tika

                full_text_content = None
                logger.info(f"  Détermination de la méthode de récupération pour {source_id}: source_type='{current_source_type}', fetch_method='{current_fetch_method}'")

                if current_source_type == "tika":
                    logger.info(f"  Source {source_id} est de type 'tika'. Utilisation de get_full_text_for_source pour traitement Tika (même si fetch_method est '{current_fetch_method}').")
                    # On s'attend à ce que get_full_text_for_source utilise le 'path' si disponible pour les sources 'tika' locales
                    full_text_content = get_full_text_for_source(source_info)
                elif current_fetch_method == "file": # Gère les fichiers non-Tika (txt, md)
                    file_path_str = source_info.get("path")
                    if file_path_str:
                        document_path = Path(file_path_str)
                        if not document_path.is_absolute():
                            document_path = PROJECT_ROOT / file_path_str
                        document_path = document_path.resolve()
                        logger.info(f"  Utilisation de load_document_content pour le fichier texte/markdown : {document_path}")
                        full_text_content = load_document_content(document_path) # load_document_content ne gère pas Tika
                    else:
                        logger.error(f"  Champ 'path' manquant pour la source locale de type 'file': {source_id}.")
                else: # Gère les autres types (web, jina, etc. qui ne sont pas 'tika' et pas 'file')
                    logger.info(f"  Utilisation de get_full_text_for_source pour la source {source_id} (type/méthode: {current_fetch_method}).")
                    full_text_content = get_full_text_for_source(source_info)

                if full_text_content:
                    source_info['full_text'] = full_text_content
                    logger.info(f"  Texte complet récupéré et mis à jour pour la source {source_id} (longueur: {len(full_text_content)}).")
                    updated_sources_count += 1
                else:
                    logger.warning(f"  Impossible de récupérer le texte complet pour la source {source_id} (méthode: {current_fetch_method}). full_text reste vide.")
                    sources_with_errors_count += 1
            except Exception as e:
                logger.error(f"  Erreur lors de la récupération du texte pour la source {source_id}: {e}")
                sources_with_errors_count += 1
        
        # LOG SPÉCIFIQUE POUR SOURCE_4
        if source_id == "Source_4":
            logger.info(f"--- DEBUG Source_4 ---")
            logger.info(f"  ID: {source_id}")
            logger.info(f"  Type: {source_info.get('source_type')}")
            logger.info(f"  Fetch Method: {source_info.get('fetch_method')}")
            logger.info(f"  Path: {source_info.get('path')}")
            retrieved_text = source_info.get('full_text') # Ne pas mettre de valeur par défaut ici pour voir si c'est None
            logger.info(f"  Full_text récupéré (premiers 300 caractères): {str(retrieved_text)[:300] if retrieved_text else 'VIDE ou None'}")
            logger.info(f"  Longueur full_text: {len(retrieved_text) if retrieved_text else 0}")
            logger.info(f"--- FIN DEBUG Source_4 ---")

    logger.info(f"Traitement des sources terminé. {updated_sources_count} sources mises à jour, {sources_with_errors_count} erreurs de récupération.")

    # 6. Sauvegarder la version non chiffrée pour débogage
    unencrypted_output_path = PROJECT_ROOT / "_temp" / "final_processed_config_unencrypted.json"
    try:
        logger.info(f"Création du répertoire _temp s'il n'existe pas: {unencrypted_output_path.parent}")
        unencrypted_output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Sauvegarde des définitions traitées (non chiffrées) dans {unencrypted_output_path}...")
        with open(unencrypted_output_path, 'w', encoding='utf-8') as f_unencrypted:
            json.dump(extract_definitions, f_unencrypted, indent=2, ensure_ascii=False)
        logger.info(f"Définitions traitées (non chiffrées) sauvegardées avec succès dans {unencrypted_output_path}.")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du fichier JSON non chiffré {unencrypted_output_path}: {e}")
        # Continuer même si cette sauvegarde échoue, car la sauvegarde chiffrée est prioritaire.

    # 7. Sauvegarder les définitions mises à jour (chiffrées)
    # Toujours tenter de sauvegarder, même si extract_definitions est vide, pour créer le fichier de sortie.
    # La fonction save_extract_definitions gérera une liste vide.
    try:
        logger.info(f"Sauvegarde des définitions d'extraits (mises à jour ou vides) dans {args.output_config}...")
        # Note: la fonction save_extract_definitions dans file_operations attend 'config_file' et 'encryption_key'
        save_success = save_extract_definitions(
            extract_definitions=extract_definitions, # Peut être une liste vide
            config_file=args.output_config,
            b64_derived_key=encryption_key_to_use, # Utilisation de la clé de ui.config
            embed_full_text=True # embed_full_text=True est important pour que le script tente d'ajouter les textes
        )
        if save_success:
            logger.info(f"Définitions d'extraits sauvegardées avec succès dans {args.output_config}.")
        else:
            # L'erreur aura déjà été logguée par save_extract_definitions
            logger.error(f"Échec de la sauvegarde des définitions dans {args.output_config}.")
            # sys.exit(1) # On pourrait choisir de sortir ici si la sauvegarde est critique même pour un fichier vide
    except Exception as e:
        logger.error(f"Erreur majeure lors de la tentative de sauvegarde des définitions dans {args.output_config}: {e}")
        sys.exit(1)

    logger.info("Script d'embarquement des sources terminé avec succès.")

if __name__ == "__main__":
    main()