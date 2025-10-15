# -*- coding: utf-8 -*-
# tests/integration/test_logic_api_integration.py
"""
Lanceur pour les tests d'intégration de LogicService.
Exécute les tests dans un sous-processus pour isoler la JVM.
"""

import pytest
from pathlib import Path

# Importer la fixture depuis son emplacement partagé
from tests.fixtures.jvm_subprocess_fixture import run_in_jvm_subprocess

# Le chemin vers le script worker qui contient les vrais tests.
WORKER_SCRIPT_PATH = Path(__file__).parent / "workers" / "worker_logic_api.py"


@pytest.mark.integration
def test_logic_api_integration_in_subprocess(run_in_jvm_subprocess):
    """
    Exécute l'ensemble des tests d'intégration de LogicService
    dans un sous-processus isolé pour éviter les conflits JVM.
    """
    assert (
        WORKER_SCRIPT_PATH.exists()
    ), f"Le script worker n'a pas été trouvé à {WORKER_SCRIPT_PATH}"

    # La fixture 'run_in_jvm_subprocess' exécute le script worker.
    run_in_jvm_subprocess(WORKER_SCRIPT_PATH)
