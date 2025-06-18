import pytest
from pathlib import Path

# Ce fichier teste les opérations sur les théories logiques.
# La logique est maintenant exécutée dans un worker dédié pour la stabilité de la JVM.

@pytest.mark.real_jpype
def test_theory_operations_in_subprocess(run_in_jvm_subprocess):
    """
    Exécute les tests d'opérations sur les théories dans un sous-processus isolé.
    """
    worker_script_path = Path(__file__).parent / "workers" / "worker_theory_operations.py"
    
    print(f"Lancement du worker pour les tests d'opérations sur les théories: {worker_script_path}")
    run_in_jvm_subprocess(worker_script_path)
    print("Le worker d'opérations sur les théories s'est terminé, le test principal est considéré comme réussi.")