#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour corriger l'encodage d'un fichier.
"""

import os
import sys
import codecs

def fix_encoding(file_path):
    """
    Corrige l'encodage d'un fichier.
    
    Args:
        file_path: Chemin du fichier à corriger
    """
    print(f"Correction de l'encodage du fichier : {file_path}")
    
    # Lire le contenu du fichier avec détection d'encodage
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # Essayer différents encodages
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    decoded_content = None
    
    for encoding in encodings:
        try:
            decoded_content = content.decode(encoding)
            print(f"Décodage réussi avec l'encodage : {encoding}")
            break
        except UnicodeDecodeError:
            continue
    
    if decoded_content is None:
        print("Impossible de décoder le fichier avec les encodages connus.")
        return False
    
    # Encoder le contenu en UTF-8
    encoded_content = decoded_content.encode('utf-8')
    
    # Écrire le contenu corrigé dans le fichier
    with open(file_path, 'wb') as f:
        f.write(encoded_content)
    
    print(f"Fichier corrigé et enregistré en UTF-8 : {file_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_encoding.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"Le fichier n'existe pas : {file_path}")
        sys.exit(1)
    
    success = fix_encoding(file_path)
    if success:
        print("Correction d'encodage terminée avec succès.")
    else:
        print("Échec de la correction d'encodage.")
        sys.exit(1)