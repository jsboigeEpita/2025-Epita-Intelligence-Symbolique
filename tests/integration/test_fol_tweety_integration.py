import pytest
from pathlib import Path

# Importer la fixture depuis son emplacement partagé
from tests.fixtures.jvm_subprocess_fixture import run_in_jvm_subprocess

# Le chemin vers le script worker qui contient les vrais tests.
WORKER_SCRIPT_PATH = Path(__file__).parent / "workers" / "worker_fol_tweety.py"

@pytest.mark.integration
def test_fol_tweety_integration_in_subprocess(run_in_jvm_subprocess):
    """
    Exécute l'ensemble des tests d'intégration FOL-Tweety 
    dans un sous-processus isolé pour éviter les conflits JVM.
    """
    assert WORKER_SCRIPT_PATH.exists(), f"Le script worker n'a pas été trouvé à {WORKER_SCRIPT_PATH}"
    
    # La fixture 'run_in_jvm_subprocess' exécute le script worker.
    # Le troisième argument `False` indique de ne pas terminer si le script échoue,
    # afin que nous puissions voir les erreurs de test du worker.
    run_in_jvm_subprocess(WORKER_SCRIPT_PATH)
