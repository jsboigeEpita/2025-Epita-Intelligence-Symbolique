# Fichier adapté pour Oracle Enhanced v2.1.0
#!/usr/bin/env python3
"""
Script de validation de la couverture pour le framework Oracle Enhanced.
Ce script vérifie la couverture des tests pour les agents Oracle,
y compris les composants comme CluedoOracle et le dataset_manager.
"""

import subprocess
import sys


def run_coverage_check():
    """Exécute les tests avec couverture"""
    try:
        # Exécuter les tests Oracle avec couverture
        oracle_tests_path = "tests/unit/argumentation_analysis/agents/core/oracle"

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            oracle_tests_path,
            "--cov=argumentation_analysis.agents.core.oracle",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/oracle",
            "-v",
        ]

        print("🧪 Exécution tests Oracle avec couverture...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Tests Oracle réussis")
            print(result.stdout)
        else:
            print("❌ Échec des tests Oracle")
            print(result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Erreur lors de l'exécution des tests: {e}")
        return False


if __name__ == "__main__":
    success = run_coverage_check()
    sys.exit(0 if success else 1)
