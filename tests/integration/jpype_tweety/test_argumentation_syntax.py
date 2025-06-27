import pytest
from pathlib import Path

# Ce fichier regroupe les tests de syntaxe d'argumentation de Tweety.
# La logique de test est maintenant exécutée dans un worker dédié
# pour assurer la stabilité de la JVM.

@pytest.mark.real_jpype
def test_argumentation_syntax_in_subprocess(run_in_jvm_subprocess):
    """
    Exécute les tests de syntaxe d'argumentation dans un sous-processus isolé.
    """
    worker_script_path = Path(__file__).parent / "workers" / "worker_argumentation_syntax.py"
    
    print(f"Lancement du worker pour les tests de syntaxe d'argumentation: {worker_script_path}")
    run_in_jvm_subprocess(worker_script_path)
    print("Le worker de syntaxe s'est terminé, le test principal est considéré comme réussi.")