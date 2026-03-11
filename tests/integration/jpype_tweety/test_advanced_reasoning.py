import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# Le test est maintenant beaucoup plus simple. Il ne fait que
# orchestrer l'exécution de la logique de test dans un sous-processus.
# Notez l'absence d'imports de jpype ou de code Java.

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)


@pytest.mark.jvm_test
@pytest.mark.skipif(
    _jpype_is_mocked,
    reason="Requires real JVM (--disable-jvm-session mocks jpype)",
)
def test_asp_reasoner_consistency_in_subprocess(run_in_jvm_subprocess):
    """
    Exécute le test de raisonneur ASP dans un sous-processus isolé pour
    garantir la stabilité de la JVM.
    """
    # Chemin vers le script worker qui contient la logique de test réelle.
    worker_script_path = (
        Path(__file__).parent / "workers" / "worker_advanced_reasoning.py"
    )

    # La fixture 'run_in_jvm_subprocess' nous a retourné une fonction. On l'appelle.
    # Cette fonction s'occupe de lancer le worker dans un environnement propre
    # via activate_project_env.ps1 et de vérifier le résultat.
    print(f"Lancement du worker pour le test ASP: {worker_script_path}")
    run_in_jvm_subprocess(worker_script_path)
    print(
        "Le worker pour le test ASP s'est terminé, le test principal est considéré comme réussi."
    )
