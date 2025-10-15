# Fichier adapté pour Oracle Enhanced v2.1.0
# tests/integration/test_cluedo_extended_workflow.py
import pytest
from pathlib import Path

# Le chemin vers le script worker qui contient les vrais tests.
WORKER_SCRIPT_PATH = (
    Path(__file__).parent / "workers" / "worker_cluedo_extended_workflow.py"
)


@pytest.mark.integration
def test_cluedo_extended_workflow_in_subprocess(run_in_jvm_subprocess):
    """
    Exécute l'ensemble des tests de comparaison du workflow Cluedo
    dans un sous-processus isolé pour éviter les conflits JVM.
    Ce test valide l'intégration avec le CluedoOracle et le dataset_manager
    dans un scénario de bout en bout.
    """
    assert (
        WORKER_SCRIPT_PATH.exists()
    ), f"Le script worker n'a pas été trouvé à {WORKER_SCRIPT_PATH}"

    # La fixture 'run_in_jvm_subprocess' exécute le script worker.
    # Tous les tests définis dans le worker seront exécutés dans cet environnement isolé.
    run_in_jvm_subprocess(WORKER_SCRIPT_PATH)
