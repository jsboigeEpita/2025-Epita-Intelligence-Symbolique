import pytest
import subprocess
import time
import requests
from requests.exceptions import ConnectionError
import os
from typing import Generator
from pathlib import Path

# ============================================================================
# Pytest Configuration Hooks
# ============================================================================

def pytest_configure(config):
    """
    Hook pour configurer pytest avant le début des tests.
    Définit une base_url par défaut si elle n'est pas déjà fournie,
    ce qui est crucial pour les tests UI de Playwright.
    """
    if not config.option.base_url:
        # L'URL du frontend est généralement servie par un serveur de développement React,
        # mais pour les tests E2E, on peut la pointer vers le backend directement
        # si les tests n'interagissent qu'avec l'API via l'UI.
        # Pour une vraie UI, ce serait l'URL du serveur React.
        # On assume que le frontend est servi ou que les tests ne nécessitent que l'API.
        config.option.base_url = os.environ.get("FRONTEND_URL", "http://127.0.0.1:5003")


# ============================================================================
# Simplified Webapp Service Fixture
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def webapp_service() -> Generator:
    """
    A simplified fixture that directly starts and stops the backend server
    using subprocess.Popen, bypassing the UnifiedWebOrchestrator for stability.
    This fixture is automatically used for the entire test session.
    """
    backend_port = 5003
    # L'URL de santé pointe maintenant vers la route /status de l'application Flask
    api_health_url = f"http://127.0.0.1:{backend_port}/status"
    
    # La commande lance maintenant l'application principale Flask (interface_web/app.py)
    # et non plus l'API FastAPI (api/main.py).
    command = [
        "powershell", "-File", ".\\activate_project_env.ps1",
        "-CommandToRun", f"conda run -n projet-is --no-capture-output python interface_web/app.py --port {backend_port}"
    ]
    
    print(f"\n[E2E Fixture] Starting Flask webapp server on port {backend_port}...")
    
    # Use Popen to run the server in the background
    project_root = Path(__file__).parent.parent.parent
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    stdout_log_path = log_dir / f"backend_stdout_{backend_port}.log"
    stderr_log_path = log_dir / f"backend_stderr_{backend_port}.log"

    with open(stdout_log_path, "wb") as stdout_log, open(stderr_log_path, "wb") as stderr_log:
        process = subprocess.Popen(
            command,
            stdout=stdout_log,
            stderr=stderr_log,
            cwd=str(project_root),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP # For Windows to kill the whole process tree
        )
        
        # Wait for the backend to be ready by polling the health endpoint
        start_time = time.time()
        timeout = 90  # 90 seconds timeout for startup
        ready = False
        
        print(f"[E2E Fixture] Waiting for backend at {api_health_url}...")
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(api_health_url, timeout=2)
                # L'application Flask renvoie un JSON. On vérifie que le statut interne est 'operational'.
                if response.status_code == 200 and response.json().get('status') == 'operational':
                    print(f"[E2E Fixture] Flask webapp is ready! (took {time.time() - start_time:.2f}s)")
                    ready = True
                    break
            except ConnectionError:
                time.sleep(1) # Wait and retry
                
        if not ready:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            
            pytest.fail(f"Backend failed to start within {timeout} seconds. Check logs in {log_dir}")

        # At this point, the server is running. Yield control to the tests.
        yield
        
        # Teardown: Stop the server after tests are done
        print("\n[E2E Fixture] Stopping backend server...")
        try:
            if os.name == 'nt':
                # On Windows, terminate the whole process group
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
            else:
                process.terminate()

            process.wait(timeout=10)
        except (subprocess.TimeoutExpired, ProcessLookupError):
            if process.poll() is None:
                print("[E2E Fixture] process.terminate() timed out, killing.")
                process.kill()
        finally:
            print("[E2E Fixture] Backend server stopped.")