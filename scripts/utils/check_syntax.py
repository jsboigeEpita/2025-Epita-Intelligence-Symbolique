#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour vérifier la syntaxe d'un fichier Python.
"""

import os
import sys
from pathlib import Path # NOUVEAU: Pour ajuster sys.path

# Ajout du répertoire parent au chemin pour permettre l'import des modules du projet
# Ceci est important si le script est exécuté directement et que project_core n'est pas dans PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from project_core.dev_utils.code_validation import check_python_syntax, check_python_tokens
except ImportError as e:
    print(f"Erreur d'importation: {e}")
    print("Assurez-vous que project_core.dev_utils.code_validation est accessible.")
    print("Vérifiez votre PYTHONPATH ou la structure du projet.")
    sys.exit(1)

# Les fonctions check_syntax et check_tokens ont été déplacées vers project_core.dev_utils.code_validation

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_syntax.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"Le fichier n'existe pas : {file_path}")
        sys.exit(1)
    
    print(f"--- Vérification de la syntaxe pour : {file_path} ---")
    syntax_ok, syntax_msg, context = check_python_syntax(file_path)
    print(syntax_msg)
    if not syntax_ok:
        if context:
            print("\nContexte de l'erreur :")
            for line_ctx in context:
                print(line_ctx)
        sys.exit(1) # Arrêter si la syntaxe est incorrecte
    
    print(f"\n--- Analyse des tokens pour : {file_path} ---")
    tokens_ok, tokens_msg, error_tokens_details = check_python_tokens(file_path)
    print(tokens_msg)
    if not tokens_ok:
        if error_tokens_details:
            print("\nDétails des tokens d'erreur :")
            for err_token in error_tokens_details:
                print(f"  Ligne {err_token['line']}, Col {err_token['col']}: {err_token['message']}")
        sys.exit(1)
        
    print(f"\n✅ Toutes les vérifications sont passées pour {file_path}")