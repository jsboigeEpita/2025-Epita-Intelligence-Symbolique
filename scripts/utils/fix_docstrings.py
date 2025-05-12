#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour corriger les docstrings dans un fichier Python.
"""

import os
import sys
import re

def fix_docstrings(file_path):
    """
    Corrige les docstrings dans un fichier Python.
    
    Args:
        file_path: Chemin du fichier à corriger
    """
    print(f"Correction des docstrings dans le fichier : {file_path}")
    
    # Lire le contenu du fichier
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remplacer les apostrophes problématiques dans les docstrings
    content = content.replace("Liste d'arguments", 'Liste "d\'arguments"')
    content = content.replace("d'évaluation", '"d\'évaluation"')
    content = content.replace("d'analyse", '"d\'analyse"')
    content = content.replace("d'erreur", '"d\'erreur"')
    content = content.replace("d'information", '"d\'information"')
    content = content.replace("d'un", '"d\'un"')
    content = content.replace("d'une", '"d\'une"')
    content = content.replace("d'utilisation", '"d\'utilisation"')
    content = content.replace("d'exécution", '"d\'exécution"')
    content = content.replace("d'accès", '"d\'accès"')
    content = content.replace("d'entrée", '"d\'entrée"')
    content = content.replace("d'interface", '"d\'interface"')
    content = content.replace("d'affichage", '"d\'affichage"')
    content = content.replace("d'initialisation", '"d\'initialisation"')
    content = content.replace("d'identification", '"d\'identification"')
    content = content.replace("d'authentification", '"d\'authentification"')
    content = content.replace("d'autorisation", '"d\'autorisation"')
    content = content.replace("d'enregistrement", '"d\'enregistrement"')
    content = content.replace("d'événement", '"d\'événement"')
    content = content.replace("d'exception", '"d\'exception"')
    
    # Écrire le contenu corrigé dans le fichier
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Docstrings corrigées dans le fichier : {file_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_docstrings.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"Le fichier n'existe pas : {file_path}")
        sys.exit(1)
    
    success = fix_docstrings(file_path)
    if success:
        print("Correction des docstrings terminée avec succès.")
    else:
        print("Échec de la correction des docstrings.")
        sys.exit(1)