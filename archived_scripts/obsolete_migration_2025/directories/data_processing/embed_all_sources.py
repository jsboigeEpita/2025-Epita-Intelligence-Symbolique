#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour s'assurer que toutes les sources dans une configuration d'extraits
ont leur texte source complet (`full_text`) embarqué, et optionnellement
générer des embeddings pour ces textes.
"""

import argparse
import logging
import sys
from pathlib import Path

# Assurer que le répertoire racine du projet est dans sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent 
sys.path.insert(0, str(PROJECT_ROOT))

try:
    # Import de la nouvelle fonction de pipeline
    from argumentation_analysis.pipelines.embedding_pipeline import run_embedding_generation_pipeline
except ImportError as e:
    print(f"Erreur d'importation: {e}. Assurez-vous que le script est exécuté depuis la racine du projet "
          "et que l'environnement est correctement configuré.")
    sys.exit(1)

# Configuration du logging (prise de la version Stash)
log_dir = PROJECT_ROOT / "_temp" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file_path = log_dir / "embed_all_sources.log"

# Le logger est configuré plus bas dans main() en utilisant args.log_level
# Cette configuration initiale est un fallback ou sera écrasée.
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
                    datefmt='%H:%M:%S',
                    handlers=[
                        logging.FileHandler(log_file_path, mode='a', encoding='utf-8'),
                        logging.StreamHandler(sys.stdout)
                    ])
logger = logging.getLogger(__name__)


def main():
    """
    Fonction principale du script.
    Parse les arguments et appelle le pipeline de génération d'embeddings.
    """
    parser = argparse.ArgumentParser(
        description="Lanceur pour le pipeline d'embarquement de texte source complet et de génération d'embeddings."
    )
    parser.add_argument(
        "--input-config",
        type=Path,
        required=False,
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
        help="Passphrase (OBSOLÈTE pour la dérivation de clé dans ce script, ENCRYPTION_KEY de ui.config est utilisée par le pipeline). "
             "Passé au pipeline pour information si nécessaire par d'autres composants."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Écrase le fichier de sortie s'il existe déjà."
    )
    parser.add_argument(
       "--generate-embeddings",
       type=str,
       metavar="MODEL_NAME",
       default=None,
       help="Nom du modèle d'embedding à utiliser pour générer les embeddings des textes complets. "
            "Si fourni, active la génération d'embeddings."
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Niveau de verbosité du logging pour le pipeline et ce script."
    )

    args = parser.parse_args()

    # Reconfigurer le logging de base avec le niveau choisi pour ce script
    # et pour le logger de ce module spécifique.
    logging.basicConfig(level=args.log_level.upper(), 
                        format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
                        datefmt='%H:%M:%S',
                        handlers=[
                            logging.FileHandler(log_file_path, mode='a', encoding='utf-8'),
                            logging.StreamHandler(sys.stdout)
                        ],
                        force=True) # force=True pour réécrire la config si basicConfig a déjà été appelé
    logger.setLevel(args.log_level.upper()) # Assurer que le logger de ce module respecte aussi le niveau

    logger.info(f"Lancement du script '{Path(__file__).name}'. Délégation au pipeline d'embedding...")
    logger.debug(f"Arguments reçus: {args}")

    try:
        run_embedding_generation_pipeline(
            input_config_path=args.input_config,
            json_string=args.json_string,
            input_json_file_path=args.input_json_file,
            output_config_path=args.output_config,
            generate_embeddings_model=args.generate_embeddings,
            force_overwrite=args.force,
            log_level=args.log_level, 
            passphrase=args.passphrase
        )
        logger.info(f"Pipeline d'embedding terminé. Le script '{Path(__file__).name}' a fini son exécution.")
    except SystemExit:
        logger.warning(f"Le pipeline s'est terminé prématurément (SystemExit). Vérifiez les logs du pipeline.")
    except Exception as e:
        logger.error(f"Une erreur s'est produite lors de l'exécution du pipeline d'embedding: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()