#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour vérifier la syntaxe d'un fichier Python.
"""

import os
import sys
import ast
import tokenize
import io

def check_syntax(file_path):
    """
    Vérifie la syntaxe d'un fichier Python.
    
    Args:
        file_path: Chemin du fichier à vérifier
    """
    print(f"Vérification de la syntaxe du fichier : {file_path}")
    
    # Lire le contenu du fichier
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Vérifier la syntaxe avec ast.parse
    try:
        ast.parse(content)
        print("✅ La syntaxe du fichier est correcte.")
        return True
    except SyntaxError as e:
        print(f"❌ Erreur de syntaxe : {e}")
        print(f"   Ligne {e.lineno}, colonne {e.offset}: {e.text}")
        
        # Afficher les lignes autour de l'erreur
        lines = content.split('\n')
        start_line = max(0, e.lineno - 5)
        end_line = min(len(lines), e.lineno + 5)
        
        print("\nContexte de l'erreur :")
        for i in range(start_line, end_line):
            prefix = ">> " if i + 1 == e.lineno else "   "
            print(f"{prefix}{i + 1}: {lines[i]}")
        
        return False
    except Exception as e:
        print(f"❌ Autre erreur lors de la vérification : {e}")
        return False

def check_tokens(file_path):
    """
    Vérifie les tokens d'un fichier Python pour détecter des problèmes potentiels.
    
    Args:
        file_path: Chemin du fichier à vérifier
    """
    print(f"\nAnalyse des tokens du fichier : {file_path}")
    
    try:
        with open(file_path, 'rb') as f:
            tokens = list(tokenize.tokenize(f.readline))
        
        # Vérifier les chaînes de caractères non terminées
        for token in tokens:
            if token.type == tokenize.ERRORTOKEN:
                print(f"❌ Token d'erreur détecté à la ligne {token.start[0]}, colonne {token.start[1]}")
                print(f"   Token: {token.string}")
        
        print("✅ Analyse des tokens terminée.")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse des tokens : {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_syntax.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"Le fichier n'existe pas : {file_path}")
        sys.exit(1)
    
    success = check_syntax(file_path)
    if success:
        check_tokens(file_path)
    else:
        sys.exit(1)