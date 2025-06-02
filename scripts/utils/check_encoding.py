#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour vérifier l'encodage UTF-8 des fichiers Python du projet
en utilisant l'utilitaire de project_core.
"""

import sys
import os

# Ajuster le PYTHONPATH pour trouver project_core si le script est exécuté directement
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from project_core.dev_utils.encoding_utils import check_project_python_files_encoding, logger
    import logging
    logger.setLevel(logging.INFO) # Assurer un output visible pour le script
except ImportError as e:
    print(f"Erreur d'importation: {e}", file=sys.stderr)
    print("Assurez-vous que le PYTHONPATH est correctement configuré ou que le projet est installé.", file=sys.stderr)
    sys.exit(1)

def main():
    """
    Fonction principale pour exécuter la vérification de l'encodage.
    """
    print(f"Lancement de la vérification de l'encodage des fichiers Python du projet (racine: {project_root})...")
    
    non_utf8_files = check_project_python_files_encoding(project_root)
    
    if non_utf8_files:
        print("\n---------------------------------------------------------------------")
        print(f"ATTENTION: {len(non_utf8_files)} fichier(s) Python ne sont pas (ou n'ont pas pu être vérifiés comme étant) encodés en UTF-8:")
        for file_path in non_utf8_files:
            # Afficher le chemin relatif par rapport à project_root pour la lisibilité
            relative_path = os.path.relpath(file_path, project_root)
            print(f"  - {relative_path}")
        print("---------------------------------------------------------------------")
        return 1  # Code de sortie d'erreur
    else:
        print("\n---------------------------------------------------------------------")
        print("Tous les fichiers Python vérifiés sont conformes à l'encodage UTF-8.")
        print("---------------------------------------------------------------------")
        return 0  # Code de sortie de succès

if __name__ == "__main__":
    sys.exit(main())