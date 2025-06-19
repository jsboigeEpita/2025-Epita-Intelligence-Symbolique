import pytest
import os

def test_api_endpoints_via_worker(run_in_jvm_subprocess):
    """
    Exécute les tests des endpoints de l'API via un script worker dans un sous-processus.
    
    Ce test délègue toute la logique de test (création du client, envoi des requêtes, assertions)
    au script `worker_api_endpoints.py`. La fixture `run_in_jvm_subprocess` se charge de
    l'exécution isolée et de la gestion de la JVM.
    """
    # Le chemin du script worker est relatif au répertoire racine du projet.
    worker_script_path = os.path.join("tests", "unit", "api", "workers", "worker_api_endpoints.py")

    # La fixture exécute le script et lève une exception en cas d'échec.
    # Aucune assertion n'est nécessaire ici car les assertions sont dans le worker.
    # Si le worker échoue, `run_in_jvm_subprocess` lèvera une exception `subprocess.CalledProcessError`.
    run_in_jvm_subprocess(worker_script_path)