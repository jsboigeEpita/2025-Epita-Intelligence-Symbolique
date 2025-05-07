#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour corriger l'indentation d'un fichier Python.
"""

import os
import sys
import re

def fix_indentation(file_path):
    """
    Corrige l'indentation d'un fichier Python.
    
    Args:
        file_path: Chemin du fichier à corriger
    """
    print(f"Correction de l'indentation du fichier : {file_path}")
    
    # Lire le contenu du fichier
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Analyser et corriger l'indentation
    fixed_lines = []
    current_indent = 0
    in_class = False
    in_method = False
    in_function = False
    
    for line in lines:
        # Ignorer les lignes vides
        if not line.strip():
            fixed_lines.append(line)
            continue
        
        # Détecter les définitions de classe
        if re.match(r'^\s*class\s+\w+', line):
            in_class = True
            current_indent = 0
            fixed_lines.append(line)
            continue
        
        # Détecter les définitions de méthode ou de fonction
        if re.match(r'^\s*def\s+\w+', line):
            if in_class:
                # C'est une méthode
                in_method = True
                current_indent = 4  # 4 espaces pour les méthodes
            else:
                # C'est une fonction
                in_function = True
                current_indent = 0
            fixed_lines.append(' ' * current_indent + line.lstrip())
            continue
        
        # Détecter la fin d'une méthode ou d'une fonction
        if in_method or in_function:
            if line.strip() == '}' or line.strip() == '):':
                in_method = False
                in_function = False
                fixed_lines.append(' ' * current_indent + line.lstrip())
                continue
        
        # Corriger l'indentation des autres lignes
        if in_method:
            # Indenter les lignes dans une méthode
            fixed_lines.append(' ' * (current_indent + 4) + line.lstrip())
        elif in_function:
            # Indenter les lignes dans une fonction
            fixed_lines.append(' ' * (current_indent + 4) + line.lstrip())
        elif in_class:
            # Indenter les lignes dans une classe
            fixed_lines.append(' ' * (current_indent + 4) + line.lstrip())
        else:
            # Garder l'indentation des autres lignes
            fixed_lines.append(line)
    
    # Écrire le contenu corrigé dans le fichier
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print(f"Indentation corrigée dans le fichier : {file_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_indentation.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"Le fichier n'existe pas : {file_path}")
        sys.exit(1)
    
    success = fix_indentation(file_path)
    if success:
        print("Correction de l'indentation terminée avec succès.")
    else:
        print("Échec de la correction de l'indentation.")
        sys.exit(1)