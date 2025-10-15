# -*- coding: utf-8 -*-
"""
Tests d'intégration pour les démonstrations de logique formelle "Cluedo" et "Einstein".

Ces tests valident que les scripts de démonstration peuvent être exécutés de bout en bout
dans un environnement contrôlé, en utilisant des sous-processus pour garantir l'isolation,
notamment pour la gestion de la JVM.
"""

import subprocess
import sys
import os
from pathlib import Path
import pytest

# Détermination du répertoire racine du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Chemin vers les scripts de démonstration à tester
CLUEDO_DEMO_SCRIPT = (
    PROJECT_ROOT / "scripts" / "sherlock_watson" / "run_cluedo_oracle_enhanced.py"
)
EINSTEIN_DEMO_SCRIPT = (
    PROJECT_ROOT / "scripts" / "sherlock_watson" / "run_einstein_oracle_demo.py"
)


@pytest.mark.integration
@pytest.mark.no_jvm_session
def test_einstein_demo_runs_successfully():
    """
    Teste l'exécution du script de la démo Einstein en mode intégration.
    Le test vérifie que le script se termine avec un code de succès et que la
    solution correcte est présente dans la sortie.
    """
    assert (
        EINSTEIN_DEMO_SCRIPT.exists()
    ), f"Script Einstein non trouvé à {EINSTEIN_DEMO_SCRIPT}"

    command = [
        sys.executable,
        str(EINSTEIN_DEMO_SCRIPT),
        "--integration-test",
    ]

    # Créer une copie de l'environnement actuel et supprimer PYTEST_RUNNING
    env = os.environ.copy()
    if "PYTEST_RUNNING" in env:
        del env["PYTEST_RUNNING"]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding=sys.stdout.encoding,
        errors="replace",
        cwd=PROJECT_ROOT,
        env=env,
    )

    # Affichage pour le débogage en cas d'échec
    print("--- STDOUT (Einstein Demo) ---")
    print(result.stdout)
    print("--- STDERR (Einstein Demo) ---")
    print(result.stderr)

    assert (
        result.returncode == 0
    ), f"Le script Einstein a échoué avec le code {result.returncode}"
    assert (
        "L'Allemand possède le poisson" in result.stdout
    ), "La solution de l'énigme d'Einstein n'a pas été trouvée dans la sortie."
    assert (
        "SOLUTION TROUVÉE" in result.stdout
    ), "La mention 'SOLUTION TROUVÉE' est absente de la sortie."


@pytest.mark.integration
@pytest.mark.no_jvm_session
def test_cluedo_demo_runs_successfully():
    """
    Teste l'exécution du script de la démo Cluedo en mode intégration.
    Le test vérifie que le script s'exécute jusqu'au bout sans erreur technique.
    """
    assert (
        CLUEDO_DEMO_SCRIPT.exists()
    ), f"Script Cluedo non trouvé à {CLUEDO_DEMO_SCRIPT}"

    command = [
        sys.executable,
        str(CLUEDO_DEMO_SCRIPT),
        "--integration-test",
        "--max-turns",
        "5",  # Limiter le nombre de tours pour un test rapide
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding=sys.stdout.encoding,
        errors="ignore",
        cwd=PROJECT_ROOT,
    )

    # Affichage pour le débogage
    print("--- STDOUT (Cluedo Demo) ---")
    print(result.stdout)
    print("--- STDERR (Cluedo Demo) ---")
    print(result.stderr)

    assert (
        result.returncode == 0
    ), f"Le script Cluedo a échoué avec le code {result.returncode}"
    assert (
        "RAPPORT FINAL DE LA PARTIE" in result.stdout
    ), "Le rapport final de la partie de Cluedo n'a pas été trouvé dans la sortie."
    assert (
        "Initialisation du scénario Cluedo Oracle Enhanced" in result.stdout
    ), "Le script Cluedo ne semble pas s'être initialisé correctement."
