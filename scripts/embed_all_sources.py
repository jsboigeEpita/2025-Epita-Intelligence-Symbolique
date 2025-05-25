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

# Assurer que le répertoire racine du projet est dans sys.path
# pour permettre les imports relatifs (ex: from argumentation_analysis.ui import utils)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    # Importer les fonctions load/save depuis file_operations
    from argumentation_analysis.ui.file_operations import load_extract_definitions, save_extract_definitions
    # Importer get_full_text_for_source depuis utils
    from argumentation_analysis.ui.utils import get_full_text_for_source
    # Importer les configurations UI si nécessaire (par exemple, pour TIKA_SERVER_URL)
    from argumentation_analysis.ui import config as ui_config
except ImportError as e:
    print(f"Erreur d'importation: {e}. Assurez-vous que le script est exécuté depuis la racine du projet "
          "et que l'environnement est correctement configuré.")
    sys.exit(1)

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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
        required=True,
        help="Chemin vers le fichier de configuration chiffré d'entrée (.json.gz.enc)."
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
        help="Passphrase pour déchiffrer/chiffrer. "
             "Si non fournie, utilise la variable d'environnement TEXT_CONFIG_PASSPHRASE."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Écrase le fichier de sortie s'il existe déjà."
    )

    args = parser.parse_args()

    logger.info(f"Démarrage du script d'embarquement des sources.")
    logger.info(f"Fichier d'entrée: {args.input_config}")
    logger.info(f"Fichier de sortie: {args.output_config}")

    # 1. La configuration de l'application est gérée par ui_config
    # Plus besoin de charger explicitement app_config ici


    # 2. Obtenir la passphrase
    passphrase = args.passphrase or os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        logger.error("Passphrase non fournie (ni via --passphrase, ni via TEXT_CONFIG_PASSPHRASE). Arrêt.")
        sys.exit(1)
    logger.info("Passphrase obtenue.")

    # 3. Vérifier les fichiers d'entrée/sortie
    if not args.input_config.exists():
        logger.error(f"Le fichier d'entrée {args.input_config} n'existe pas. Arrêt.")
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
    try:
        logger.info(f"Chargement des définitions d'extraits depuis le fichier JSON non chiffré: {args.input_config}...")
        with open(args.input_config, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Le fichier JSON reconstruit contient une clé "sources"
        extract_definitions = data.get("sources", [])
        
        if not extract_definitions:
             logger.warning(f"Aucune définition d'extrait trouvée dans {args.input_config}.")
             extract_definitions = []
        logger.info(f"{len(extract_definitions)} définitions d'extraits chargées depuis le fichier JSON.")

    except Exception as e:
        logger.error(f"Erreur lors du chargement ou du déchiffrement de {args.input_config}: {e}")
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
                # get_full_text_for_source utilise déjà ui_config en interne, pas besoin de passer app_config
                full_text = get_full_text_for_source(source_info)
                if full_text:
                    source_info['full_text'] = full_text
                    logger.info(f"  Texte complet récupéré et mis à jour pour la source {source_id} (longueur: {len(full_text)}).")
                    updated_sources_count += 1
                else:
                    logger.warning(f"  Impossible de récupérer le texte complet pour la source {source_id}. full_text reste vide.")
                    sources_with_errors_count += 1
            except Exception as e:
                logger.error(f"  Erreur lors de la récupération du texte pour la source {source_id}: {e}")
                sources_with_errors_count += 1

    logger.info(f"Traitement des sources terminé. {updated_sources_count} sources mises à jour, {sources_with_errors_count} erreurs de récupération.")

    # 6. Sauvegarder les définitions mises à jour
    if not extract_definitions and updated_sources_count == 0:
        logger.info("Aucune définition d'extrait à sauvegarder ou aucune mise à jour effectuée.")
    else:
        try:
            logger.info(f"Sauvegarde des définitions d'extraits mises à jour dans {args.output_config}...")
            # Note: la fonction save_extract_definitions dans file_operations attend 'config_file' et 'encryption_key'
            save_extract_definitions(
                extract_definitions=extract_definitions,
                config_file=args.output_config,
                encryption_key=passphrase,
                embed_full_text=True
            )
            logger.info(f"Définitions d'extraits sauvegardées avec succès dans {args.output_config}.")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des définitions dans {args.output_config}: {e}")
            sys.exit(1)

    logger.info("Script d'embarquement des sources terminé avec succès.")

if __name__ == "__main__":
    main()