#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de validation de la correction ImportError
==============================================

Ce script teste si l'ImportError de 'run_analysis_conversation' a été résolue
grâce au wrapper de compatibilité pl_agent.py.
"""

import project_core.core_from_scripts.auto_env
import sys
import warnings
from pathlib import Path

# Ajouter la racine du projet au PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_import_pl_agent():
    """Test l'import du wrapper de compatibilité pl_agent."""
    print("🔍 Test 1: Import de pl_agent (wrapper de compatibilité)...")
    
    try:
        # Capturer les warnings d'obsolescence
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            from argumentation_analysis.agents.core.pl.pl_agent import PropositionalLogicAgent
            
            print("✅ Import réussi !")
            print(f"📝 Agent importé: {PropositionalLogicAgent.__name__}")
            print(f"📍 Module: {PropositionalLogicAgent.__module__}")
            
            # Vérifier les warnings d'obsolescence
            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
            if deprecation_warnings:
                print(f"⚠️  Warning d'obsolescence capturé (OK): {len(deprecation_warnings)} warning(s)")
                for warning in deprecation_warnings:
                    print(f"   📢 {warning.message}")
            else:
                print("ℹ️  Aucun warning d'obsolescence (inattendu)")
                
            return True
            
    except ImportError as e:
        print(f"❌ Échec de l'import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def test_import_analysis_runner():
    """Test l'import de analysis_runner qui causait l'erreur originale."""
    print("\n🔍 Test 2: Import de analysis_runner.run_analysis_conversation...")
    
    try:
        from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
        
        print("✅ Import réussi !")
        print(f"📝 Fonction importée: {run_analysis_conversation.__name__}")
        print(f"📍 Module: {run_analysis_conversation.__module__}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Échec de l'import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def test_import_text_analyzer():
    """Test l'import de text_analyzer qui était l'origine du problème."""
    print("\n🔍 Test 3: Import de text_analyzer.perform_text_analysis...")
    
    try:
        from argumentation_analysis.analytics.text_analyzer import perform_text_analysis
        
        print("✅ Import réussi !")
        print(f"📝 Fonction importée: {perform_text_analysis.__name__}")
        print(f"📍 Module: {perform_text_analysis.__module__}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Échec de l'import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def main():
    """Fonction principale de test."""
    print("🧪 VALIDATION DE LA CORRECTION ImportError")
    print("="*50)
    
    tests = [
        test_import_pl_agent,
        test_import_analysis_runner,
        test_import_text_analyzer
    ]
    
    results = []
    for test_func in tests:
        result = test_func()
        results.append(result)
    
    print("\n📊 RÉSUMÉ DES TESTS:")
    print("="*30)
    
    success_count = sum(results)
    total_count = len(results)
    
    for i, (test_func, result) in enumerate(zip(tests, results), 1):
        status = "✅ RÉUSSI" if result else "❌ ÉCHEC"
        print(f"Test {i} ({test_func.__name__}): {status}")
    
    print(f"\n🎯 BILAN: {success_count}/{total_count} tests réussis")
    
    if success_count == total_count:
        print("🎉 CORRECTION VALIDÉE: L'ImportError a été résolue !")
        print("✨ Les étudiants peuvent maintenant utiliser leur code existant.")
        return True
    else:
        print("⚠️  CORRECTION INCOMPLÈTE: Des problèmes subsistent.")
        return False

if __name__ == "__main__":
    main()
