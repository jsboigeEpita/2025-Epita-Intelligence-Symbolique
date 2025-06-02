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
# import base64 # Supprimé car la dérivation de clé est retirée de ce script
# from cryptography.hazmat.primitives import hashes # Supprimé
# from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC # Supprimé
# from cryptography.hazmat.backends import default_backend # Supprimé

# Assurer que le répertoire racine du projet est dans sys.path
# pour permettre les imports relatifs (ex: from argumentation_analysis.ui import utils)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent # MODIFIÉ: Remonter à la racine du projet
sys.path.insert(0, str(PROJECT_ROOT))

try:
    # Import de la nouvelle fonction de pipeline
    from argumentation_analysis.pipelines.embedding_pipeline import run_embedding_generation_pipeline
    # Le logger est configuré dans le pipeline, plus besoin de le configurer ici.
    # Les autres imports spécifiques à la logique (file_operations, utils, nlp_utils)
    # sont maintenant gérés dans embedding_pipeline.py
except ImportError as e:
    print(f"Erreur d'importation: {e}. Assurez-vous que le script est exécuté depuis la racine du projet "
          "et que l'environnement est correctement configuré.")
    sys.exit(1)

# Le logger global du script, s'il est encore utilisé, peut être défini ici,
# mais la configuration principale du logging est faite dans le pipeline.
# logger = logging.getLogger(__name__) # Supprimé car non utilisé, script_logger est utilisé dans main


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
        help="Niveau de verbosité du logging pour le pipeline."
    )

    args = parser.parse_args()

    # Le logging initial du script lui-même peut être simple.
    # La configuration détaillée est faite par setup_logging dans le pipeline.
    script_logger = logging.getLogger(__name__) # Utiliser un logger spécifique au script si besoin
    logging.basicConfig(level=args.log_level.upper()) # Configuration de base pour ce script avant appel pipeline
    script_logger.info(f"Lancement du script '{Path(__file__).name}'. Délégation au pipeline d'embedding...")

    try:
        run_embedding_generation_pipeline(
            input_config_path=args.input_config,
            json_string=args.json_string,
            input_json_file_path=args.input_json_file,
            output_config_path=args.output_config,
            generate_embeddings_model=args.generate_embeddings,
            force_overwrite=args.force,
            log_level=args.log_level,
            passphrase=args.passphrase # Passé au pipeline
        )
        script_logger.info(f"Pipeline d'embedding terminé. Le script '{Path(__file__).name}' a fini son exécution.")
    except SystemExit:
        # Si le pipeline sort avec sys.exit(), on ne veut pas forcément le considérer comme une erreur ici,
        # car le pipeline aura déjà loggué l'erreur.
        script_logger.warning(f"Le pipeline s'est terminé prématurément (SystemExit). Vérifiez les logs du pipeline.")
    except Exception as e:
        script_logger.error(f"Une erreur s'est produite lors de l'exécution du pipeline d'embedding: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()