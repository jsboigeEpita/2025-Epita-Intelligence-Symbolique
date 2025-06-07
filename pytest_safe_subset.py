#!/usr/bin/env python3
"""
SUBSET SAFE TESTS - Test d'un sous-ensemble sûr pour validation rapide
"""

import subprocess
import sys
import os

def main():
    """Test d'un subset safe pour validation"""
    
    # Tests connus comme "sûrs" (pas JPype, pas AsyncIO, pas Playwright)
    safe_test_patterns = [
        "tests/environment_checks/test_core_dependencies.py",
        "tests/environment_checks/test_project_module_imports.py",
        "tests/unit/argumentation_analysis/test_utils.py::TestSystemUtils::test_get_project_root",
        "tests/unit/argumentation_analysis/utils/test_data_loader.py",
        "tests/unit/argumentation_analysis/utils/test_text_processing.py",
        "tests/unit/argumentation_analysis/utils/core_utils/test_file_utils.py",
        "tests/unit/argumentation_analysis/utils/core_utils/test_text_utils.py",
        "tests/unit/argumentation_analysis/utils/core_utils/test_system_utils.py",
        "tests/unit/argumentation_analysis/utils/dev_tools/test_env_checks.py",
        "tests/unit/mocks/test_numpy_rec_mock.py",
    ]
    
    # Commande pytest pour tests spécifiques
    cmd = [
        "python", "-m", "pytest", 
        "--tb=short", "-v"
    ] + safe_test_patterns
    
    print("PYTEST SAFE SUBSET - Validation rapide")
    print("=" * 50)
    print(f"Tests sélectionnés: {len(safe_test_patterns)}")
    for pattern in safe_test_patterns:
        print(f"  - {pattern}")
    print("=" * 50)
    
    # Exécuter avec timeout court
    try:
        result = subprocess.run(
            cmd,
            timeout=120,  # 2 minutes max
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")  
            print(result.stderr)
            
        # Analyser les résultats
        output = result.stdout + result.stderr
        if "failed" in output and "passed" in output:
            # Extraire statistiques
            lines = output.split('\n')
            for line in lines:
                if 'failed' in line and 'passed' in line:
                    print(f"\nRÉSULTAT: {line.strip()}")
                    break
        
        print(f"\nCode de retour: {result.returncode}")
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("TIMEOUT après 2 minutes - problème persistant")
        return False
    except Exception as e:
        print(f"Erreur: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)