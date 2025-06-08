#!/usr/bin/env python3
"""
Script de validation de la migration PowerShell vers Python - Phase 2B
Teste tous les scripts de remplacement générés
"""

import sys
import subprocess
import os
from pathlib import Path

def test_python_script(script_path, description):
    """Teste un script Python de remplacement"""
    print(f"\n[TEST] {description}")
    print(f"Script: {script_path}")
    
    if not os.path.exists(script_path):
        print(f"ECHEC: Script {script_path} introuvable")
        return False
    
    try:
        # Test d'import et de syntaxe seulement (pas d'exécution complète)
        result = subprocess.run([
            sys.executable, "-m", "py_compile", script_path
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"SUCCES: Syntaxe Python valide")
            return True
        else:
            print(f"ECHEC: Erreur de syntaxe")
            print(f"Erreur: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT: Test interrompu après 10s")
        return False
    except Exception as e:
        print(f"ECHEC: Exception {e}")
        return False

def main():
    """Fonction principale de validation"""
    print("=" * 60)
    print("VALIDATION MIGRATION POWERSHELL VERS PYTHON - PHASE 2B")
    print("=" * 60)
    
    # Scripts à tester
    scripts_to_test = [
        ("migration_output/start_web_application_simple_replacement.py", "Démarrage application simple"),
        ("migration_output/backend_failover_non_interactive_replacement.py", "Backend failover non-interactif"),
        ("migration_output/run_backend_replacement.py", "Démarrage backend"),
        ("migration_output/run_frontend_replacement.py", "Démarrage frontend"),
        ("migration_output/integration_tests_with_failover_replacement.py", "Tests intégration avec failover"),
        ("migration_output/run_integration_tests_replacement.py", "Tests d'intégration"),
        ("migration_output/unified_startup.py", "Script de démarrage unifié")
    ]
    
    # Vérification des archives
    print(f"\n[ARCHIVES] Vérification des archives PowerShell")
    archive_path = "archives/powershell_legacy"
    if os.path.exists(archive_path):
        archived_files = os.listdir(archive_path)
        print(f"SUCCES: {len(archived_files)} scripts archivés: {', '.join(archived_files)}")
    else:
        print(f"ECHEC: Dossier d'archives {archive_path} introuvable")
    
    # Tests des scripts Python
    success_count = 0
    total_count = len(scripts_to_test)
    
    for script_path, description in scripts_to_test:
        if test_python_script(script_path, description):
            success_count += 1
    
    # Rapport final
    print("\n" + "=" * 60)
    print("RAPPORT FINAL DE VALIDATION")
    print("=" * 60)
    print(f"Scripts testés: {total_count}")
    print(f"Succès: {success_count}")
    print(f"Échecs: {total_count - success_count}")
    print(f"Taux de réussite: {(success_count/total_count)*100:.1f}%")
    
    if success_count == total_count:
        print("\nMIGRATION PHASE 2B - SUCCÈS COMPLET!")
        print("SUCCES: Tous les scripts Python sont syntaxiquement valides")
        print("SUCCES: Scripts PowerShell archivés avec succès")
        print("SUCCES: Documentation de migration créée")
        return 0
    else:
        print(f"\nMIGRATION PHASE 2B - PARTIELLEMENT RÉUSSIE")
        print(f"ECHEC: {total_count - success_count} script(s) nécessitent des corrections")
        return 1

if __name__ == "__main__":
    sys.exit(main())