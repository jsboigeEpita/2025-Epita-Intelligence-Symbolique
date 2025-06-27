import pytest
from pathlib import Path

# Le test est maintenant beaucoup plus simple. Il ne fait que
# orchestrer l'exécution de la logique de test dans un sous-processus.
# Notez l'absence d'imports de jpype ou de code Java.

@pytest.mark.skip(reason="Dépendances JAR Tweety corrompues ou manquantes dans le projet (TICKET-1234)")
def test_asp_reasoner_consistency_in_subprocess(run_in_jvm_subprocess):
    """
    Exécute le test de raisonneur ASP dans un sous-processus isolé pour
    garantir la stabilité de la JVM.

    NOTE: Ce test est actuellement désactivé car les JARs requis de Tweety ne sont
    pas correctement fournis dans le répertoire libs/tweety. Le script de téléchargement
    semble être défectueux.
    """
    # Chemin vers le script worker qui contient la logique de test réelle.
    worker_script_path = Path(__file__).parent / "workers" / "worker_advanced_reasoning.py"
    
    # La fixture 'run_in_jvm_subprocess' nous a retourné une fonction. On l'appelle.
    # Cette fonction s'occupe de lancer le worker dans un environnement propre
    # via activate_project_env.ps1 et de vérifier le résultat.
    print(f"Lancement du worker pour le test ASP: {worker_script_path}")
    run_in_jvm_subprocess(worker_script_path)
    print("Le worker pour le test ASP s'est terminé, le test principal est considéré comme réussi.")