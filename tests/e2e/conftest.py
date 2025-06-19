import pytest
import subprocess
import os
import time
from typing import Generator, Tuple

# Fichier sentinelle pour indiquer que le serveur est prêt
SERVER_READY_SENTINEL = "SERVER_READY.tmp"

@pytest.fixture(scope="session")
def webapp_service() -> Generator[Tuple[str, str], None, None]:
    """
    Fixture synchrone qui démarre les serveurs web (backend, frontend) dans un
    processus complètement séparé pour éviter les conflits de boucle asyncio
    entre pytest-asyncio et pytest-playwright.
    """
    
    # Les URL sont codées en dur car elles sont définies dans le script de démarrage
    frontend_url = "http://localhost:8051"
    backend_url = "http://localhost:8000"
    
    # Commande pour lancer le script de démarrage des serveurs
    start_script_path = os.path.join(os.path.dirname(__file__), "util_start_servers.py")
    command = ["python", start_script_path]
    
    # Supprimer le fichier sentinelle s'il existe
    if os.path.exists(SERVER_READY_SENTINEL):
        os.remove(SERVER_READY_SENTINEL)

    # Démarrer le script dans un nouveau processus
    server_process = subprocess.Popen(command)
    
    try:
        # On yield immédiatement pour ne pas bloquer la collecte de pytest
        yield frontend_url, backend_url
        
    finally:
        print("\n[Conftest] Tearing down servers...")
        server_process.terminate()
        try:
            server_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server_process.kill()
            server_process.wait()
        
        # Nettoyer le fichier sentinelle
        if os.path.exists(SERVER_READY_SENTINEL):
            os.remove(SERVER_READY_SENTINEL)
        print("[Conftest] Servers torn down.")


@pytest.fixture(scope="session")
def frontend_url(webapp_service: Tuple[str, str]) -> str:
    """Fixture simple qui extrait l'URL du frontend du service web."""
    return webapp_service[0]

@pytest.fixture(scope="session")
def backend_url(webapp_service: Tuple[str, str]) -> str:
    """Fixture simple qui extrait l'URL du backend du service web."""
    return webapp_service[1]