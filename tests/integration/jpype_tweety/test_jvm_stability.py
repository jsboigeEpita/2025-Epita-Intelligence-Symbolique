import pytest
from pathlib import Path

# Ce test n'interagit plus directement avec JPype.
# Il délègue l'exécution à un worker dans un sous-processus propre.

@pytest.mark.real_jpype
def test_jvm_stability_in_subprocess(run_in_jvm_subprocess):
    """
    Exécute le test de stabilité de la JVM dans un sous-processus isolé.
    """
    worker_script_path = Path(__file__).parent / "workers" / "worker_jvm_stability.py"
    
    print(f"Lancement du worker pour le test de stabilité JVM: {worker_script_path}")
    run_in_jvm_subprocess(worker_script_path)
    print("Le worker de stabilité JVM s'est terminé, le test principal est considéré comme réussi.")