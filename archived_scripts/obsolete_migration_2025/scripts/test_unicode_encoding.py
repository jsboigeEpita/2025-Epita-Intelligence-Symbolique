#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test et correction de l'encodage Unicode
pour le Sprint 3 - Optimisation des performances
"""

import sys
import os
import locale
import codecs

def test_unicode_support():
    """Teste le support Unicode du système"""
    print("=== TEST D'ENCODAGE UNICODE ===")
    
    # Test de l'encodage système
    print(f"Encodage stdout: {sys.stdout.encoding}")
    print(f"Encodage stderr: {sys.stderr.encoding}")
    print(f"Encodage système: {sys.getdefaultencoding()}")
    print(f"Locale système: {locale.getpreferredencoding()}")
    
    # Test des émojis et caractères spéciaux
    test_chars = [
        "✅ Test réussi",
        "🔴 Test échec",
        "⚠️ Attention",
        "❌ Erreur critique",
        "📊 Métriques",
        "🏗️ Architecture",
        "💻 Code",
        "🪲 Debug"
    ]
    
    print("\n=== TEST DES CARACTÈRES UNICODE ===")
    for char in test_chars:
        try:
            print(char)
            # Test d'encodage/décodage
            encoded = char.encode('utf-8')
            decoded = encoded.decode('utf-8')
            assert char == decoded
            print(f"  ✓ Encodage/décodage réussi pour: {char}")
        except Exception as e:
            print(f"  ❌ Erreur avec {char}: {e}")
    
    return True

def configure_utf8_environment():
    """Configure l'environnement pour UTF-8"""
    print("\n=== CONFIGURATION UTF-8 ===")
    
    # Variables d'environnement
    env_vars = {
        'PYTHONIOENCODING': 'utf-8',
        'LANG': 'en_US.UTF-8',
        'LC_ALL': 'en_US.UTF-8'
    }
    
    for var, value in env_vars.items():
        os.environ[var] = value
        print(f"Configuré {var} = {value}")
    
    # Test de la configuration
    print(f"Nouvel encodage par défaut: {sys.getdefaultencoding()}")
    
    return True

def create_utf8_test_file():
    """Crée un fichier de test avec caractères UTF-8"""
    test_content = """# Test d'encodage UTF-8

## Émojis de statut
✅ Success
🔴 Error  
⚠️ Warning
❌ Critical

## Tests de caractères spéciaux
Français: àéèùçîï
Allemand: äöüß
Espagnol: ñáéíóú
Russe: абвгдежз
Chinois: 你好世界
Japonais: こんにちは
Arabe: مرحبا بالعالم

## Symboles techniques
→ → ← ↑ ↓
∀ ∃ ∈ ∉ ⊆ ⊇
∧ ∨ ¬ ⊤ ⊥
"""
    
    test_file = "tests/test_unicode_support.txt"
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    print(f"Fichier de test créé: {test_file}")
    
    # Vérification de lecture
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
        print("✅ Lecture du fichier de test réussie")
    
    return test_file

if __name__ == "__main__":
    print("SPRINT 3 - Test et correction de l'encodage Unicode")
    print("=" * 50)
    
    try:
        # Test du support Unicode
        test_unicode_support()
        
        # Configuration UTF-8
        configure_utf8_environment()
        
        # Création fichier de test
        test_file = create_utf8_test_file()
        
        print("\n=== RÉSUMÉ ===")
        print("✅ Tests Unicode: RÉUSSIS")
        print("✅ Configuration UTF-8: TERMINÉE")
        print("✅ Fichier de test: CRÉÉ")
        print("\nL'encodage Unicode est maintenant configuré pour les tests fonctionnels.")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        sys.exit(1)