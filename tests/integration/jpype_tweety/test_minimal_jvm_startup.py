import pytest
from pathlib import Path

# Ce fichier de test vérifie la capacité à démarrer une JVM
# en utilisant le pattern du worker en sous-processus.
# L'ancien contenu qui tentait un démarrage direct a été déplacé dans le worker.


@pytest.mark.real_jpype
def test_minimal_jvm_startup_in_subprocess(run_in_jvm_subprocess):
    """
    Exécute le test de démarrage minimal de la JVM dans un sous-processus isolé.
    """
    worker_script_path = (
        Path(__file__).parent / "workers" / "worker_minimal_jvm_startup.py"
    )

    print(
        f"Lancement du worker pour le test de démarrage JVM minimal: {worker_script_path}"
    )
    run_in_jvm_subprocess(worker_script_path)
    print(
        "Le worker de démarrage minimal s'est terminé, le test principal est considéré comme réussi."
    )
