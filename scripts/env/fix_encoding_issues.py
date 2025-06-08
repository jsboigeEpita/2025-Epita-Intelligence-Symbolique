#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de correction des problèmes d'encodage Unicode
Remplace les emojis problématiques par des alternatives compatibles
"""

import os
import re
import sys
from pathlib import Path

def fix_encoding_in_file(file_path):
    """Corrige les problèmes d'encodage dans un fichier."""
    replacements = {
        # Emojis problématiques -> Alternatives compatibles
        '\\U0001f30d': '[MONDE]',
        '\\U0001f50d': '[LOUPE]',
        '\\U0001f4ca': '[GRAPHIQUE]',
        '\\U0001f680': '[FUSEE]',
        '\\U0001f504': '[ROTATION]',
        '\\U0001f393': '[DIPLOME]',
        '\\u274c': '[X]',
        '\\u2699': '[ENGRENAGE]',
        '\\u26a0': '[ATTENTION]',
        '\\u2705': '[OK]',
        '\\u2764': '[COEUR]',
        '\\U0001f4bb': '[ORDI]',
        '\\U0001f527': '[CLE]',
        '\\U0001f4dd': '[NOTE]',
        '\\U0001f4a1': '[AMPOULE]',
        # Emojis directs aussi
        '🌍': '[MONDE]',
        '🔍': '[LOUPE]',
        '📊': '[GRAPHIQUE]',
        '🚀': '[FUSEE]',
        '🔄': '[ROTATION]',
        '🎓': '[DIPLOME]',
        '❌': '[X]',
        '⚙️': '[ENGRENAGE]',
        '⚠️': '[ATTENTION]',
        '✅': '[OK]',
        '❤️': '[COEUR]',
        '💻': '[ORDI]',
        '🔧': '[CLE]',
        '📝': '[NOTE]',
        '💡': '[AMPOULE]',
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Applique les remplacements
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        # Sauvegarde si modifié
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[OK] Corrigé: {file_path}")
            return True
        else:
            print(f"[--] Aucun changement: {file_path}")
            return False
            
    except Exception as e:
        print(f"[ERREUR] {file_path}: {e}")
        return False

def main():
    """Corrige les fichiers problématiques."""
    print("=" * 60)
    print("CORRECTION PROBLEMES ENCODAGE UNICODE")
    print("=" * 60)
    
    files_to_fix = [
        'scripts/env/manage_environment.py',
        'scripts/env/diagnose_environment.py',
        'scripts/env/check_environment.py',
        'demos/demo_epita_diagnostic.py',
        'demos/demo_unified_system.py'
    ]
    
    fixed_count = 0
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_encoding_in_file(file_path):
                fixed_count += 1
        else:
            print(f"[IGNORE] Fichier inexistant: {file_path}")
    
    print("=" * 60)
    print(f"RESUME: {fixed_count} fichiers corrigés")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())