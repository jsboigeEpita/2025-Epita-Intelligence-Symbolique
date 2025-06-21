# tests/integration/test_einstein_tweetyproject_integration.py
import pytest
from pathlib import Path

# Ce test agit comme un "lanceur" pour exécuter les vrais tests dans un
# sous-processus isolé, garantissant une initialisation propre de la JVM.

# Chemin vers le script "worker" qui contient la logique de test réelle.
WORKER_SCRIPT_PATH = Path(__file__).parent / "workers" / "worker_einstein_tweety.py"

@pytest.mark.integration
def test_einstein_tweety_in_subprocess(run_in_jvm_subprocess):
    """
    Exécute les tests d'intégration Einstein/Tweety dans un sous-processus.
    """
    assert WORKER_SCRIPT_PATH.exists(), f"Le script worker n'a pas été trouvé à {WORKER_SCRIPT_PATH}"
    
    print(f"Lancement du worker pour les tests EINSTEIN / TWEETY : {WORKER_SCRIPT_PATH}")
    # La fixture 'run_in_jvm_subprocess' s'occupe de l'exécution et des assertions.
    # Si le worker échoue, la fixture fera échouer ce test.
    run_in_jvm_subprocess(WORKER_SCRIPT_PATH)
    print("Le worker Einstein / Tweety s'est terminé avec succès.")