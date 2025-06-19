import pytest
import os

# Le chemin vers le script worker qui exécute les tests dépendants de la JVM.
# Ce chemin est relatif au répertoire racine du projet.
WORKER_SCRIPT_PATH = "tests/unit/api/workers/worker_dung_service.py"

def test_dung_service_via_worker(run_in_jvm_subprocess):
    """
    Exécute les tests du service Dung dans un sous-processus isolé.
    
    Ce test s'appuie sur la fixture 'run_in_jvm_subprocess' pour:
    1. Configurer un environnement Python avec les dépendances nécessaires.
    2. Démarrer une JVM dédiée pour le sous-processus.
    3. Exécuter le script worker spécifié.
    4. Capturer la sortie (stdout/stderr) et le code de sortie.
    
    Le worker contient la logique de test détaillée (initialisation du service,
    appels de méthodes, assertions). Ce test principal ne fait que valider
    que le worker s'est exécuté sans erreur et a renvoyé un signal de succès.
    """
    # Vérifie que le script worker existe avant de tenter de l'exécuter.
    # Le chemin est construit à partir de la racine du projet.
    assert os.path.exists(WORKER_SCRIPT_PATH), f"Le script worker est introuvable: {WORKER_SCRIPT_PATH}"

    # Appel de la fixture qui exécute le script dans un environnement contrôlé.
    result = run_in_jvm_subprocess(WORKER_SCRIPT_PATH)

    # Validation de la sortie du worker.
    # On s'attend à ce que le worker imprime un message de succès.
    assert "SUCCESS" in result.stdout, f"L'exécution du worker a échoué. Sortie: {result.stdout}\nErreurs: {result.stderr}"
    
    # Vérifie que le worker s'est terminé avec un code de sortie 0 (succès).
    assert result.returncode == 0, f"Le worker s'est terminé avec un code d'erreur. Code: {result.returncode}"