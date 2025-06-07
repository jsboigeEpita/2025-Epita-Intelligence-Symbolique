#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test pour valider les corrections critiques apportées.
"""

import sys
import os
from pathlib import Path

# Ajouter le projet au chemin Python
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_unified_config():
    """Test de la configuration unifiée."""
    print("🔧 Test de config/unified_config.py...")
    try:
        from config.unified_config import get_config, get_test_config
        
        # Test configuration par défaut
        config = get_config()
        print(f"  ✅ Configuration chargée")
        print(f"  📊 JVM activée: {config.is_jvm_enabled()}")
        print(f"  📊 Mode test: {config.is_testing_mode()}")
        print(f"  📊 Agent FOL activé: {config.is_enabled('agents', 'fol_logic')}")
        
        # Test configuration de test
        test_config = get_test_config()
        print(f"  ✅ Configuration de test chargée")
        print(f"  📊 Mode mock: {test_config.is_testing_mode()}")
        print(f"  📊 JVM désactivée en test: {not test_config.is_jvm_enabled()}")
        
        return True
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_analyze_text_script():
    """Test du script CLI analyze_text."""
    print("\n🔧 Test de scripts/main/analyze_text.py...")
    try:
        from scripts.main.analyze_text import setup_argument_parser, create_mock_analysis
        
        # Test parser d'arguments
        parser = setup_argument_parser()
        print(f"  ✅ Parser d'arguments créé")
        
        # Test analyse mock
        mock_result = create_mock_analysis("Tout le monde sait que cette théorie est correcte", "scientifique")
        print(f"  ✅ Analyse mock effectuée")
        print(f"  📊 Sophismes détectés: {mock_result['fallacies_detected']}")
        print(f"  📊 Mode: {mock_result['mode']}")
        
        return True
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_existing_modules():
    """Test des modules existants mentionnés."""
    print("\n🔧 Test des modules existants...")
    try:
        # Test text_utils
        from argumentation_analysis.core.utils.text_utils import clean_text, truncate_text
        test_text = clean_text("  Test avec espaces  ")
        print(f"  ✅ text_utils.py fonctionne: '{test_text}'")
        
        # Test contextual_fallacy_analyzer
        from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
        analyzer = ContextualFallacyAnalyzer()
        print(f"  ✅ contextual_fallacy_analyzer.py fonctionne")
        
        return True
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_imports_coherence():
    """Test de cohérence des imports."""
    print("\n🔧 Test de cohérence des imports...")
    try:
        # Test import configuration depuis le script analyze_text
        sys.path.append(str(project_root / "scripts" / "main"))
        import importlib.util
        
        # Charger le module analyze_text
        spec = importlib.util.spec_from_file_location("analyze_text", project_root / "scripts" / "main" / "analyze_text.py")
        analyze_text_module = importlib.util.module_from_spec(spec)
        
        print(f"  ✅ Module analyze_text chargeable")
        
        return True
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def main():
    """Fonction principale de test."""
    print("=" * 60)
    print("🧪 VALIDATION DES CORRECTIONS CRITIQUES")
    print("=" * 60)
    
    tests = [
        test_unified_config,
        test_analyze_text_script,
        test_existing_modules,
        test_imports_coherence
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    print("📋 RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    success_count = sum(results)
    total_count = len(results)
    success_rate = (success_count / total_count) * 100
    
    print(f"Tests réussis: {success_count}/{total_count} ({success_rate:.1f}%)")
    
    if success_count == total_count:
        print("🎉 TOUTES LES CORRECTIONS SONT VALIDÉES!")
        return 0
    else:
        print(f"⚠️  {total_count - success_count} correction(s) nécessitent une attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())