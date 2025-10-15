import pytest
from pathlib import Path

# Ce fichier de test exécute les tests d'opérations logiques
# dans un sous-processus pour garantir la stabilité de la JVM.


@pytest.mark.real_jpype
def test_logic_operations_in_subprocess(run_in_jvm_subprocess):
    """
    Exécute les tests d'opérations logiques dans un sous-processus isolé.
    """
    worker_script_path = (
        Path(__file__).parent / "workers" / "worker_logic_operations.py"
    )

    print(
        f"Lancement du worker pour les tests d'opérations logiques: {worker_script_path}"
    )
    run_in_jvm_subprocess(worker_script_path)
    print(
        "Le worker d'opérations logiques s'est terminé, le test principal est considéré comme réussi."
    )
