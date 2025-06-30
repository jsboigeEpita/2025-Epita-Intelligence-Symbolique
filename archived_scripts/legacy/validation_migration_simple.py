#!/usr/bin/env python3
"""
VALIDATION SIMPLE DE LA MIGRATION AUTOMATIQUE DETECTEE
Teste les composants critiques avant le nettoyage des 77 fichiers
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path

# Configuration encodage pour Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def test_project_core():
    """Test infrastructure project_core/"""
    print("\n[TEST] Infrastructure project_core/")
    print("-" * 40)
    
    try:
        # Test ServiceManager
        print("1. Import ServiceManager...")
        result = subprocess.run([
            sys.executable, "-c", 
            "from project_core.service_manager import ServiceManager; print('[OK] ServiceManager')"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"[FAIL] ServiceManager: {result.stderr}")
            return False
        else:
            print("[OK] ServiceManager")
        
        # Test TestRunner
        print("2. Import TestRunner...")
        result = subprocess.run([
            sys.executable, "-c",
            "from project_core.test_runner import TestRunner; print('[OK] TestRunner')"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"[FAIL] TestRunner: {result.stderr}")
            return False
        else:
            print("[OK] TestRunner")
            
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def test_migration_output():
    """Test repertoire migration_output/"""
    print("\n[TEST] Repertoire migration_output/")
    print("-" * 40)
    
    migration_dir = Path("migration_output")
    
    if not migration_dir.exists():
        print("[FAIL] Repertoire migration_output/ introuvable")
        return False
    
    # Fichiers attendus
    expected_files = [
        "migration_report.json",
        "backend_failover_non_interactive_replacement.py",
        "integration_tests_with_failover_replacement.py",
        "unified_startup.py"
    ]
    
    missing = []
    for f in expected_files:
        if not (migration_dir / f).exists():
            missing.append(f)
    
    if missing:
        print(f"[WARN] Fichiers manquants: {missing}")
        return False
    
    print(f"[OK] Tous les fichiers attendus présents ({len(expected_files)})")
    return True

def test_migration_report():
    """Test du rapport de migration JSON"""
    print("\n[TEST] Rapport de migration")
    print("-" * 40)
    
    try:
        with open("migration_output/migration_report.json", 'r') as f:
            report = json.load(f)
        
        # Vérifications clés
        obsolete_count = len(report.get("obsolete_scripts_found", []))
        pattern_count = len(report.get("pattern_matches", []))
        replacement_count = len(report.get("replacement_commands", {}))
        
        print(f"- Scripts obsolètes détectés: {obsolete_count}")
        print(f"- Patterns migrés trouvés: {pattern_count}")
        print(f"- Commandes de remplacement: {replacement_count}")
        
        if obsolete_count >= 6 and pattern_count >= 15:
            print("[OK] Migration report valide")
            return True
        else:
            print("[WARN] Migration report incomplet")
            return False
            
    except Exception as e:
        print(f"[ERROR] Lecture migration_report.json: {e}")
        return False

def main():
    """Validation principale"""
    print("=" * 50)
    print("VALIDATION MIGRATION AUTOMATIQUE DETECTEE")
    print("=" * 50)
    
    results = []
    
    # Tests critiques
    results.append(("Infrastructure project_core", test_project_core()))
    results.append(("Repertoire migration_output", test_migration_output()))
    results.append(("Rapport de migration", test_migration_report()))
    
    # Résumé
    print("\n" + "=" * 50)
    print("RESUME VALIDATION:")
    print("-" * 25)
    
    success_count = 0
    for test_name, success in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {test_name}")
        if success:
            success_count += 1
    
    print(f"\nResultat: {success_count}/{len(results)} tests réussis")
    
    if success_count == len(results):
        print("\n[SUCCESS] MIGRATION VALIDEE")
        print("=> Prêt pour le nettoyage des 77 fichiers")
        return True
    else:
        print(f"\n[PARTIAL] VALIDATION PARTIELLE")
        print("=> Vérification manuelle requise")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[CRITICAL] Erreur: {e}")
        sys.exit(1)