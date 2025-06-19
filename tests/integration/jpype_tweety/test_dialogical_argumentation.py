import pytest
from pathlib import Path

# Ce fichier de test, bien que contenant des mocks, est destiné à être
# exécuté contre une JVM réelle pour tester l'intégration de l'argumentation dialogique.
# Toute la logique est déplacée vers un worker pour la stabilité.

@pytest.mark.real_jpype
def test_dialogical_argumentation_in_subprocess(run_in_jvm_subprocess):
    """
    Exécute les tests d'argumentation dialogique dans un sous-processus isolé.
    """
    worker_script_path = Path(__file__).parent / "workers" / "worker_dialogical_argumentation.py"
    
    print(f"Lancement du worker pour les tests d'argumentation dialogique: {worker_script_path}")
    run_in_jvm_subprocess(worker_script_path)
    print("Le worker d'argumentation dialogique s'est terminé, le test principal est considéré comme réussi.")