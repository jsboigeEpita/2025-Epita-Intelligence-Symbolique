# tests/integration/test_fol_pipeline_integration.py
import pytest
from pathlib import Path

# Le chemin vers le script worker qui contient les vrais tests.
WORKER_SCRIPT_PATH = Path(__file__).parent / "workers" / "worker_fol_pipeline.py"

@pytest.mark.integration
def test_fol_pipeline_in_subprocess(run_in_jvm_subprocess):
    """
    Exécute l'ensemble des tests du pipeline FOL 
    dans un sous-processus isolé pour éviter les conflits JVM.
    """
    assert WORKER_SCRIPT_PATH.exists(), f"Le script worker n'a pas été trouvé à {WORKER_SCRIPT_PATH}"
    
    # La fixture 'run_in_jvm_subprocess' exécute le script worker.
    run_in_jvm_subprocess(WORKER_SCRIPT_PATH)
