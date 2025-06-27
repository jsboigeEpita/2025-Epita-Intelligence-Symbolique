#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour corriger l'indentation d'un fichier Python.
"""

import argumentation_analysis.core.environment
import os
import sys
import argparse
import logging
from pathlib import Path # Ajout pour la clarté

# Ajout du répertoire racine du projet au chemin pour permettre l'import des modules
project_root_path_setup = Path(__file__).resolve().parent.parent.parent
if str(project_root_path_setup) not in sys.path:
    sys.path.insert(0, str(project_root_path_setup))

from argumentation_analysis.utils.dev_tools.code_formatting_utils import format_python_file_with_autopep8, logger as formatting_logger

# Configurer le logger pour ce script
script_logger = logging.getLogger(__name__)
if not script_logger.handlers:
    handler = logging.StreamHandler(sys.stdout) # Utiliser stdout pour les messages du script
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s (SCRIPT): %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    script_logger.addHandler(handler)
    script_logger.setLevel(logging.INFO)

# Assurer que les logs du module de formatage sont visibles et configurés
if not formatting_logger.handlers:
    # Si le logger du module n'a pas de handler (par ex. si importé avant sa propre config),
    # on lui en ajoute un pour que ses messages soient visibles.
    # On pourrait aussi le laisser se configurer lui-même s'il est bien conçu.
    module_handler = logging.StreamHandler(sys.stdout)
    module_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s (MODULE): %(message)s', datefmt='%H:%M:%S')
    module_handler.setFormatter(module_formatter)
    formatting_logger.addHandler(module_handler)
formatting_logger.setLevel(logging.INFO) # Le script contrôle le niveau du module ici


def main():
    parser = argparse.ArgumentParser(
        description="Corrige l'indentation et formate un fichier Python en utilisant autopep8."
    )
    parser.add_argument("file_path", help="Chemin du fichier Python à formater.")
    parser.add_argument(
        "--autopep8-args",
        nargs='*', # Permet plusieurs arguments, ou aucun pour utiliser les défauts
        help="Arguments optionnels à passer directement à autopep8 (ex: --max-line-length 100). "
             "Si non spécifié, utilise ['--in-place', '--aggressive', '--aggressive']."
             "Pour ne passer aucun argument spécifique et laisser autopep8 utiliser ses propres défauts "
             "(en dehors de --in-place qui est toujours ajouté si aucun autre n'est fourni pour cela), "
             "fournissez une chaîne vide comme argument: --autopep8-args \"\" "
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Activer les logs de niveau DEBUG pour le script et le module de formatage."
    )

    args = parser.parse_args()

    if args.verbose:
        script_logger.setLevel(logging.DEBUG)
        formatting_logger.setLevel(logging.DEBUG)
        script_logger.debug("Mode verbose activé.")

    autopep8_custom_args = args.autopep8_args
    if args.autopep8_args is not None and len(args.autopep8_args) == 1 and args.autopep8_args[0] == "":
        # Cas spécial pour indiquer "aucun argument personnalisé", laisser autopep8 décider (sauf --in-place)
        # La fonction format_python_file_with_autopep8 gère la logique de --in-place par défaut.
        # Ici, on passe None pour que la fonction utilise ses propres défauts.
        autopep8_custom_args = None
    elif args.autopep8_args is None:
        # Si --autopep8-args n'est pas du tout fourni, on passe None pour utiliser les défauts de la fonction.
        autopep8_custom_args = None


    if not os.path.isfile(args.file_path):
        script_logger.error(f"Le fichier n'existe pas : {args.file_path}")
        sys.exit(1)
    
    script_logger.info(f"Demande de formatage pour : {args.file_path}")
    success = format_python_file_with_autopep8(args.file_path, autopep8_args=autopep8_custom_args)
    
    if success:
        script_logger.info(f"Formatage de {args.file_path} terminé.")
    else:
        script_logger.error(f"Échec du formatage de {args.file_path}.")
        sys.exit(1)

if __name__ == "__main__":
    main()