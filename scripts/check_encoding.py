#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour vérifier l'encodage des fichiers Python.
"""

import os
import sys

def check_encoding():
    """
    Vérifie que tous les fichiers Python sont encodés en UTF-8.
    """
    print("Vérification de l'encodage des fichiers Python...")
    non_utf8_files = []
    count = 0
    
    for root, dirs, files in os.walk('.'):
        # Ignorer les répertoires venv et .git
        if 'venv' in dirs:
            dirs.remove('venv')
        if '.git' in dirs:
            dirs.remove('.git')
            
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                count += 1
                try:
                    # Essayer d'ouvrir le fichier en UTF-8
                    with open(file_path, 'r', encoding='utf-8') as f:
                        f.read()
                except UnicodeDecodeError:
                    non_utf8_files.append(file_path)
    
    if non_utf8_files:
        print(f"ATTENTION: {len(non_utf8_files)} fichiers ne sont pas encodés en UTF-8:")
        for file in non_utf8_files:
            print(f"  - {file}")
        return False
    else:
        print(f"Tous les {count} fichiers Python sont encodés en UTF-8.")
        return True

if __name__ == "__main__":
    sys.exit(0 if check_encoding() else 1)