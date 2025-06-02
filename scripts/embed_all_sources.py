#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour s'assurer que toutes les sources dans une configuration d'extraits
ont leur texte source complet (`full_text`) embarqué.
"""

import argparse
import logging # Gardé ici pour la configuration initiale
import os
import sys
from pathlib import Path
import json

# Configuration du logging au tout début du script pour un maximum de verbosité
EMBED_SCRIPT_LOGGER_NAME = "embed_all_sources_script.main" # Nom spécifique pour ce logger
# force=True (Python 3.8+) écrase toute configuration existante du root logger.
# Ceci est utile pour le débogage afin de s'assurer que nos paramètres sont appliqués.
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - [%(name)s] - %(module)s.%(funcName)s:%(lineno)d - %(message)s',
                    force=True)
logger = logging.getLogger(EMBED_SCRIPT_LOGGER_NAME) # Utiliser ce logger dans tout le script

logger.debug(f"Logging pour {EMBED_SCRIPT_LOGGER_NAME} initialisé au niveau DEBUG.")

# import base64 # Supprimé car la dérivation de clé est retirée de ce script
# from cryptography.hazmat.primitives import hashes # Supprimé
# from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC # Supprimé
# from cryptography.hazmat.backends import default_backend # Supprimé

# Assurer que le répertoire racine du projet est dans sys.path
# pour permettre les imports relatifs (ex: from argumentation_analysis.ui import utils)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    logger.debug(f"Ajout de {PROJECT_ROOT} à sys.path.")

logger.debug(f"sys.path: {sys.path}")

try:
    logger.debug("Tentative d'importation des modules de argumentation_analysis...")
    # Importer les fonctions load/save depuis file_operations
    from argumentation_analysis.ui.file_operations import load_extract_definitions, save_extract_definitions
    logger.debug("Importé: load_extract_definitions, save_extract_definitions")
    # Importer get_full_text_for_source depuis utils
    from argumentation_analysis.ui.utils import get_full_text_for_source
    logger.debug("Importé: get_full_text_for_source")
    # Importer les configurations UI si nécessaire (par exemple, pour TIKA_SERVER_URL)
    from argumentation_analysis.ui import config as ui_config
    logger.debug("Importé: ui_config")
    # Importer ENCRYPTION_KEY directement depuis la configuration UI
    from argumentation_analysis.ui.config import ENCRYPTION_KEY as CONFIG_UI_ENCRYPTION_KEY
    logger.debug("Importé: CONFIG_UI_ENCRYPTION_KEY")
    # Essayer d'importer use_mcp_tool
    try:
        logger.debug("Tentative d'importation de use_mcp_tool...")
        from argumentation_analysis.utils.mcp_utils import use_mcp_tool
        MCP_AVAILABLE = True
        logger.info("use_mcp_tool importé avec succès.")
    except ImportError as mcp_e:
        MCP_AVAILABLE = False
        logger.warning(f"Impossible d'importer use_mcp_tool: {mcp_e}. Les fonctionnalités MCP (comme Jina) ne seront pas disponibles.")
        def use_mcp_tool(*args, **kwargs): # Placeholder
            logger.error("use_mcp_tool appelé mais non disponible en raison d'une erreur d'importation.")
            return None
    logger.debug("Imports de argumentation_analysis terminés.")
except ImportError as e:
    # Utiliser le logger configuré si possible, sinon print
    logger.error(f"Erreur d'importation majeure: {e}. Assurez-vous que le script est exécuté depuis la racine du projet "
                 "et que l'environnement est correctement configuré. Vérifiez PYTHONPATH et les dépendances.", exc_info=True)
    # Fallback sur print si le logger lui-même a un problème ou n'est pas encore pleinement fonctionnel
    print(f"PRINT ERREUR D'IMPORTATION: {e}. PYTHONPATH={os.getenv('PYTHONPATH')}, sys.path={sys.path}", file=sys.stderr)
    sys.exit(1)
except Exception as e_init:
    logger.error(f"Erreur inattendue pendant l'initialisation (imports): {e_init}", exc_info=True)
    print(f"PRINT ERREUR INIT: {e_init}", file=sys.stderr)
    sys.exit(1)


# La ligne "logger = logging.getLogger(__name__)" est supprimée car logger est défini globalement ci-dessus.
# La configuration de logging de base est également déplacée et gérée ci-dessus.

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
        logger.info(f"Traitement de la source: {source_id} ({source_info.get('fetch_method', source_info.get('source_type', 'N/A'))}: {source_info.get('path', 'N/A')})")
 
        full_text_content = source_info.get('full_text', '')
        if full_text_content and full_text_content.strip():
            logger.info(f"  Le texte complet est déjà présent pour la source {source_id}.")
        else:
            logger.info(f"  Texte complet manquant pour la source {source_id}. Tentative de récupération...")
            fetch_method = source_info.get('fetch_method')
            source_path = source_info.get('path') # URL ou chemin de fichier

            try:
                if fetch_method == 'jina':
                    if not MCP_AVAILABLE:
                        logger.error(f"  MCP_AVAILABLE est False. Impossible d'utiliser Jina pour {source_id} ({source_path}).")
                        full_text_content = ""
                    else:
                        logger.info(f"  Utilisation de Jina (via use_mcp_tool) pour récupérer le contenu de : {source_path}")
                        # constructed_url est déjà le 'path' pour jina
                        jina_result = use_mcp_tool("jinavigator", "convert_web_to_markdown", {"url": source_path})
                        if jina_result and jina_result.get("markdown_content"):
                            full_text_content = jina_result["markdown_content"]
                            logger.info(f"  Texte complet récupéré via Jina pour {source_id} (longueur: {len(full_text_content)}).")
                        else:
                            logger.warning(f"  Échec de la récupération du contenu via Jina pour {source_id}. Résultat: {jina_result}")
                            full_text_content = ""
                elif fetch_method == 'direct_download' or source_info.get('source_type') in ['file', 'tika']: # et autres cas gérés par get_full_text_for_source
                    logger.info(f"  Utilisation de get_full_text_for_source pour {fetch_method or source_info.get('source_type')}: {source_path}")
                    full_text_content = get_full_text_for_source(source_info)
                    if full_text_content:
                        logger.info(f"  Texte complet récupéré via get_full_text_for_source pour {source_id} (longueur: {len(full_text_content)}).")
                    else:
                        logger.warning(f"  get_full_text_for_source n'a pas retourné de contenu pour {source_id}.")
                        full_text_content = ""
                else:
                    logger.warning(f"  Méthode de récupération non reconnue '{fetch_method}' pour la source {source_id}. Tentative avec get_full_text_for_source.")
                    full_text_content = get_full_text_for_source(source_info)
                    if full_text_content:
                        logger.info(f"  Texte complet récupéré via get_full_text_for_source (fallback) pour {source_id} (longueur: {len(full_text_content)}).")
                    else:
                        logger.warning(f"  get_full_text_for_source (fallback) n'a pas retourné de contenu pour {source_id}.")
                        full_text_content = ""
                
                if full_text_content:
                    source_info['full_text'] = full_text_content
                    updated_sources_count += 1
                else:
                    # Assurer que full_text est une chaîne vide si rien n'est récupéré
                    source_info['full_text'] = ""
                    logger.warning(f"  Impossible de récupérer le texte complet pour la source {source_id}. full_text reste vide.")
                    sources_with_errors_count += 1

            except Exception as e:
                logger.error(f"  Erreur lors de la récupération du texte pour la source {source_id} ({fetch_method}: {source_path}): {e}", exc_info=True)
                source_info['full_text'] = "" # Assurer que c'est une chaîne vide en cas d'erreur
                sources_with_errors_count += 1
        
        # Logique d'extraction des full_text_segment pour les extraits
        if source_info.get('full_text'):
            current_full_text_of_source = source_info['full_text']
            logger.info(f"  Traitement des extraits pour la source {source_id} (full_text disponible, longueur: {len(current_full_text_of_source)}).")
            
            # Logging de diagnostic pour Source_1
            if source_info.get('id') == "Source_1":
                logger.info(f"  [DIAGNOSTIC Source_1] Aperçu des 500 premiers caractères du full_text: {current_full_text_of_source[:500]}")

            for extract_info in source_info.get("extracts", []):
                extract_name = extract_info.get('extract_name', extract_info.get('id', 'NomExtraitInconnu'))
                logger.info(f"    Traitement de l'extrait: {extract_name}")

                start_marker = extract_info.get("start_marker")
                end_marker = extract_info.get("end_marker")

                # Logging de diagnostic spécifique pour l'extrait cible
                is_target_extract = source_info.get('id') == "Source_1" and extract_name == "1. DAcbat Complet (Ottawa, 1858)"
                if is_target_extract:
                    logger.info(f"    [DIAGNOSTIC Extrait Cible - {source_id}/{extract_name}] Marqueurs: START='{start_marker}', END='{end_marker}'")
                
                if not start_marker or not end_marker:
                    logger.warning(f"    Marqueurs de début ou de fin manquants pour l'extrait {extract_name} de la source {source_id}. Segment non extrait.")
                    extract_info['full_text_segment'] = ""
                    continue

                start_index = current_full_text_of_source.find(start_marker)
                if is_target_extract:
                    logger.info(f"    [DIAGNOSTIC Extrait Cible - {source_id}/{extract_name}] start_index trouvé: {start_index}")

                if start_index != -1:
                    # Chercher end_marker après start_marker
                    search_from_index_for_end_marker = start_index + len(start_marker)
                    end_index = current_full_text_of_source.find(end_marker, search_from_index_for_end_marker)
                    if is_target_extract:
                        logger.info(f"    [DIAGNOSTIC Extrait Cible - {source_id}/{extract_name}] end_index trouvé (recherche à partir de {search_from_index_for_end_marker}): {end_index}")
                    
                    if end_index != -1:
                        # L'extraction inclut les marqueurs
                        segment = current_full_text_of_source[start_index : end_index + len(end_marker)]
                        extract_info['full_text_segment'] = segment
                        logger.info(f"    Segment extrait avec succès pour {extract_name} (longueur: {len(segment)}).")
                        if is_target_extract:
                             logger.info(f"    [DIAGNOSTIC Extrait Cible - {source_id}/{extract_name}] Aperçu du segment (100 premiers car.): {segment[:100]}")
                             logger.info(f"    [DIAGNOSTIC Extrait Cible - {source_id}/{extract_name}] Aperçu du segment (100 derniers car.): {segment[-100:]}")
                    else:
                        logger.warning(f"    Marqueur de fin '{end_marker}' non trouvé après le marqueur de début pour l'extrait {extract_name} dans {source_id}. Segment non extrait.")
                        extract_info['full_text_segment'] = ""
                else:
                    logger.warning(f"    Marqueur de début '{start_marker}' non trouvé pour l'extrait {extract_name} dans {source_id}. Segment non extrait.")
                    extract_info['full_text_segment'] = ""
        else:
            logger.warning(f"  Full_text vide ou non disponible pour la source {source_id}. Impossible d'extraire les segments pour ses extraits.")
            for extract_info in source_info.get("extracts", []):
                extract_info['full_text_segment'] = ""
            
        # Afficher les informations sur le full_text récupéré (déplacé après l'extraction des segments pour contexte)
        logger.info(f"--- Informations finales pour Source ID: {source_info.get('id', f'Source_{i+1}')} ---")
        if source_info.get('full_text'):
            logger.info(f"  Full text récupéré. Longueur: {len(source_info['full_text'])} caractères.")
            try:
                # Utiliser logger.debug pour l'aperçu complet pour ne pas polluer les logs INFO
                logger.debug(f"  Aperçu (500 premiers caractères): {source_info['full_text'][:500].encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)}")
            except Exception as e_print:
                logger.warning(f"  Aperçu (500 premiers caractères): Erreur lors de l'affichage de l'aperçu - {e_print}")
        else:
            logger.info("  Full text NON récupéré ou vide.")
        logger.info("---------------------------------------\n")
 
    logger.info(f"Traitement des sources terminé. {updated_sources_count} sources mises à jour, {sources_with_errors_count} erreurs de récupération.")
 
    # 6. Sauvegarder les définitions mises à jour
    output_file_path = args.output_config
    # Comparaison robuste de chemins, insensible aux slashes
    expected_debug_path = Path("_temp/debug_output.json")
    
    if output_file_path.resolve() == expected_debug_path.resolve():
        logger.info(f"Sauvegarde des définitions (avec segments) en JSON simple dans: {output_file_path}")
        try:
            # S'assurer que le répertoire parent existe
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(extract_definitions, f, indent=2, ensure_ascii=False)
            logger.info(f"Définitions sauvegardées avec succès dans {output_file_path}.")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde en JSON simple dans {output_file_path}: {e}", exc_info=True)
            sys.exit(1)
    else:
        logger.info(f"Sauvegarde chiffrée demandée pour {output_file_path} (ou autre format non-debug).")
        logger.warning("Pour cette étape de diagnostic, la sauvegarde chiffrée est commentée. Seuls les logs sont importants.")
        logger.warning(f"Si vous souhaitez réellement sauvegarder, décommentez le bloc save_extract_definitions et ajustez la destination si besoin.")
        # try:
        #     logger.info(f"Sauvegarde des définitions d'extraits (mises à jour ou vides) dans {args.output_config}...")
        #     save_success = save_extract_definitions(
        #         extract_definitions=extract_definitions,
        #         config_file=args.output_config,
        #         encryption_key=encryption_key_to_use,
        #         embed_full_text=True # Assure que full_text et full_text_segment sont inclus
        #     )
        #     if save_success:
        #         logger.info(f"Définitions d'extraits sauvegardées avec succès dans {args.output_config}.")
        #     else:
        #         logger.error(f"Échec de la sauvegarde des définitions dans {args.output_config}.")
        # except Exception as e:
        #     logger.error(f"Erreur majeure lors de la tentative de sauvegarde des définitions dans {args.output_config}: {e}")
        #     sys.exit(1)
 
    logger.info("Script d'embarquement des sources et d'extraction des segments terminé.")

if __name__ == "__main__":
    main()