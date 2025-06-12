#!/usr/bin/env python3
"""
Test minimaliste pour diagnostic Phase 2
"""
import subprocess
import sys
import os
from pathlib import Path

def test_single_simple_file():
    """Test d'un seul fichier simple pour diagnostic"""
    print("=== TEST MINIMALISTE DIAGNOSTIC ===")
    
    # Créer un test ultra-simple pour diagnostic
    test_content = '''
import pytest

def test_basic_addition():
    """Test basique pour vérifier que pytest fonctionne"""
    assert 1 + 1 == 2

def test_basic_import():
    """Test que les imports Python de base fonctionnent"""
    import os
    import sys
    assert os.path.exists(".")
'''
    
    # Écrire le test temporaire
    test_file = Path("test_minimal_diagnostic.py")
    test_file.write_text(test_content, encoding='utf-8')
    
    try:
        print(f"Test fichier créé: {test_file}")
        
        # Environnement simplifié
        env = os.environ.copy()
        env['USE_REAL_JPYPE'] = 'false'
        env['USE_REAL_GPT'] = 'false'
        
        # Test avec timeout court
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            str(test_file),
            "-v", "--tb=short"
        ], capture_output=True, text=True, timeout=15, env=env)
        
        print(f"Code de retour: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("TIMEOUT même sur test minimal - problème systémique")
        return False
    except Exception as e:
        print(f"Erreur: {e}")
        return False
    finally:
        # Nettoyage
        if test_file.exists():
            test_file.unlink()

def analyze_environment():
    """Analyser l'environnement Python"""
    print("\n=== ANALYSE ENVIRONNEMENT ===")
    print(f"Python: {sys.version}")
    print(f"Executable: {sys.executable}")
    print(f"Path: {sys.path[:3]}...")
    
    # Vérifier pytest
    try:
        import pytest
        print(f"Pytest version: {pytest.__version__}")
    except ImportError:
        print("ERREUR: Pytest non disponible")
        return False
    
    # Vérifier les modules problématiques
    modules_to_check = ['jpype', 'semantic_kernel', 'openai']
    for module in modules_to_check:
        try:
            __import__(module)
            print(f"{module}: disponible")
        except ImportError:
            print(f"{module}: non disponible (normal)")
    
    return True

def main():
    print("DIAGNOSTIC MINIMALISTE PHASE 2")
    print("==============================")
    
    # Analyser l'environnement
    env_ok = analyze_environment()
    if not env_ok:
        print("Problème d'environnement détecté")
        return False
    
    # Test minimal
    test_ok = test_single_simple_file()
    
    if test_ok:
        print("\nTEST MINIMAL RÉUSSI")
        print("Le problème vient probablement du volume/complexité des tests")
    else:
        print("\nTEST MINIMAL ÉCHOUÉ") 
        print("Problème systémique avec pytest ou l'environnement")
    
    return test_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)