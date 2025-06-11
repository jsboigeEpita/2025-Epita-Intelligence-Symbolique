#!/usr/bin/env python3
"""
Script pour corriger les tests qui utilisent return au lieu d'assert
"""

import re
from pathlib import Path

def fix_return_assert():
    """Remplace return True/False par assert dans les tests"""
    test_file = Path("tests/validation_sherlock_watson/test_verification_fonctionnalite_oracle.py")
    
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Corrections spécifiques
    content = re.sub(r'return True', 'assert True', content)
    content = re.sub(r'return False', 'assert False', content)
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Corrigé: {test_file}")

if __name__ == "__main__":
    fix_return_assert()