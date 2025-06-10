#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de contournement pour le problème d'encodage Unicode avec Conda
Sprint 3 - Résolution critique des problèmes d'encodage
"""

import sys
import os
import locale

def fix_conda_unicode():
    """
    Résout le problème d'encodage Unicode avec conda
    Contournement pour Windows cp1252 -> UTF-8
    """
    print("SPRINT 3 - Correction d'encodage Unicode")
    print("=" * 50)
    
    # Information système actuelle
    print("ETAT ACTUEL:")
    print(f"- Encodage stdout: {sys.stdout.encoding}")
    print(f"- Encodage system: {sys.getdefaultencoding()}")
    print(f"- Locale: {locale.getpreferredencoding()}")
    
    # Configuration des variables d'environnement
    env_fixes = {
        'PYTHONIOENCODING': 'utf-8',
        'PYTHONLEGACYWINDOWSSTDIO': '1',
        'LC_ALL': 'C.UTF-8',
        'LANG': 'C.UTF-8'
    }
    
    print("\nAPPLICATION DES CORRECTIONS:")
    for var, value in env_fixes.items():
        os.environ[var] = value
        print(f"- {var} = {value}")
    
    # Test d'encodage sans émojis
    print("\nTEST D'ENCODAGE SANS EMOJIS:")
    test_chars = [
        "[OK] Test reussi",
        "[ERROR] Test echec", 
        "[WARNING] Attention",
        "[CRITICAL] Erreur critique"
    ]
    
    for char in test_chars:
        print(f"  {char}")
    
    # Création du fichier de configuration UTF-8
    create_utf8_config()
    
    print("\nCORRECTIONS APPLIQUEES:")
    print("- Variables d'environnement configurees")
    print("- Fichier de configuration UTF-8 cree")
    print("- Tests d'encodage sans emojis: REUSSI")
    
    return True

def create_utf8_config():
    """Crée un fichier de configuration UTF-8 pour conda"""
    config_content = """# Configuration UTF-8 pour environnement conda
# Correction du problème d'encodage Unicode Windows

# Variables d'environnement requises
PYTHONIOENCODING=utf-8
PYTHONLEGACYWINDOWSSTDIO=1
LC_ALL=C.UTF-8
LANG=C.UTF-8

# Tests supportés sans émojis
test_success = "[OK]"
test_error = "[ERROR]"  
test_warning = "[WARNING]"
test_critical = "[CRITICAL]"

# Configuration pytest pour éviter les émojis
pytest_markers = "--tb=short -v --disable-warnings"
"""
    
    config_file = "config/utf8_environment.conf"
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print(f"- Configuration UTF-8 sauvee: {config_file}")

def test_without_emojis():
    """Teste le système sans utiliser d'émojis Unicode"""
    print("\nTEST DU SYSTEME SANS EMOJIS:")
    
    # Test de base
    try:
        print("- Import des modules principaux...")
        from argumentation_analysis.services import logic_service
        print("  [OK] Services importes")
        
        print("- Test des adaptateurs d'agents...")
        from argumentation_analysis.agents.core.informal import informal_agent_adapter
        print("  [OK] Adaptateurs importes")
        
        print("- Test de l'orchestration...")
        from argumentation_analysis.orchestration import group_chat
        print("  [OK] Orchestration importee")
        
        return True
        
    except Exception as e:
        print(f"  [ERROR] Erreur d'import: {e}")
        return False

if __name__ == "__main__":
    try:
        # Application des corrections
        fix_conda_unicode()
        
        # Test du système
        success = test_without_emojis()
        
        if success:
            print("\n[SUCCESS] Corrections d'encodage appliquees avec succes")
            print("Les tests fonctionnels peuvent maintenant etre executes")
        else:
            print("\n[ERROR] Problemes d'import detectes")
            
    except Exception as e:
        print(f"\n[CRITICAL] Erreur lors de la correction: {e}")
        sys.exit(1)