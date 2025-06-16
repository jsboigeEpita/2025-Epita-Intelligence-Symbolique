#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour corriger l'encodage d'un fichier.
"""

import project_core.core_from_scripts.auto_env
import os
import sys
import argparse
from pathlib import Path # Ajout pour la clarté

# Ajout du répertoire racine du projet au chemin pour permettre l'import des modules
project_root_path_setup = Path(__file__).resolve().parent.parent.parent
if str(project_root_path_setup) not in sys.path:
    sys.path.insert(0, str(project_root_path_setup))

from argumentation_analysis.utils.dev_tools.encoding_utils import fix_file_encoding, logger as encoding_logger
import logging

# Configurer le logger pour ce script afin qu'il affiche les logs de encoding_utils
script_logger = logging.getLogger(__name__)
if not script_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s (SCRIPT): %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    script_logger.addHandler(handler)
    script_logger.setLevel(logging.INFO) # Ou DEBUG si plus de détails sont nécessaires

# Faire en sorte que les logs du module encoding_utils soient également visibles
encoding_logger.setLevel(logging.INFO) # Assurez-vous que le logger du module est au bon niveau
if not encoding_logger.handlers: # S'il n'a pas de handler, en ajouter un
    encoding_logger.addHandler(handler)


def main():
    parser = argparse.ArgumentParser(description="Corrige l'encodage d'un fichier vers UTF-8.")
    parser.add_argument("file_path", help="Chemin du fichier à corriger.")
    parser.add_argument(
        "--source-encodings",
        nargs='+',
        default=None,
        help="Liste optionnelle d'encodages source à essayer (ex: latin-1 cp1252)."
    )
    parser.add_argument(
        "--target-encoding",
        default='utf-8',
        help="Encodage cible pour la réécriture du fichier (par défaut: utf-8)."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Activer les logs de niveau DEBUG."
    )

    args = parser.parse_args()

    if args.verbose:
        script_logger.setLevel(logging.DEBUG)
        encoding_logger.setLevel(logging.DEBUG)
        script_logger.debug("Mode verbose activé.")

    if not os.path.isfile(args.file_path):
        script_logger.error(f"Le fichier n'existe pas : {args.file_path}")
        sys.exit(1)
    
    success = fix_file_encoding(args.file_path, target_encoding=args.target_encoding, source_encodings=args.source_encodings)
    
    if success:
        script_logger.info("Correction d'encodage terminée avec succès.")
    else:
        script_logger.error("Échec de la correction d'encodage.")
        sys.exit(1)

if __name__ == "__main__":
    main()