#!/usr/bin/env python3
"""
Orchestrateur Spécialisé - Tests UnifiedConfig
============================================

Script d'orchestration pour tous les tests liés au système de configuration unifié.
"""

import sys
import subprocess
from pathlib import Path
import time

# Ajout du chemin du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_unified_config_tests():
    """Exécute tous les tests UnifiedConfig de manière ordonnée."""
    
    print("🧪 TESTS UNIFIED CONFIG - ORCHESTRATEUR SPÉCIALISÉ")
    print("="*60)
    
    # Configuration des tests
    test_files = [
        "tests/unit/config/test_unified_config.py",
        "tests/unit/scripts/test_configuration_cli.py", 
        "tests/unit/integration/test_unified_config_integration.py"
    ]
    
    total_start = time.time()
    results = []
    
    for i, test_file in enumerate(test_files, 1):
        print(f"\n[{i}/{len(test_files)}] 🔄 {test_file}")
        print("-" * 40)
        
        start_time = time.time()
        
        # Vérification existence
        full_path = PROJECT_ROOT / test_file
        if not full_path.exists():
            print(f"⚠️  Fichier manquant: {test_file}")
            results.append(False)
            continue
        
        # Exécution
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(full_path),
                "-v", "--tb=short"
            ], capture_output=True, text=True, timeout=60)
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                print(f"✅ Succès - {duration:.2f}s")
                results.append(True)
            else:
                print(f"❌ Échec - {duration:.2f}s")
                print("Erreurs:")
                print(result.stdout[-500:])  # Dernières 500 chars
                results.append(False)
                
        except subprocess.TimeoutExpired:
            print("⏰ Timeout")
            results.append(False)
        except Exception as e:
            print(f"💥 Exception: {e}")
            results.append(False)
    
    # Résumé
    total_duration = time.time() - total_start
    passed = sum(results)
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"📊 RÉSUMÉ UNIFIED CONFIG")
    print(f"✅ Passés: {passed}/{total}")
    print(f"⏱️  Durée: {total_duration:.2f}s")
    
    if passed == total:
        print("🎉 TOUS LES TESTS UNIFIED CONFIG SONT PASSÉS!")
        return 0
    else:
        print("❌ Des tests ont échoué")
        return 1

if __name__ == "__main__":
    sys.exit(run_unified_config_tests())
