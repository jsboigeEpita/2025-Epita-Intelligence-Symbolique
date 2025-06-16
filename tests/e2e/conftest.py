import pytest
import subprocess
import time
import requests
from requests.exceptions import ConnectionError
import os
from typing import Generator

# ============================================================================
# Simplified Webapp Service Fixture
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def webapp_service() -> Generator:
    """
    A simplified fixture that directly starts and stops the backend server
    using subprocess.Popen, bypassing the UnifiedWebOrchestrator for stability.
    """
    backend_port = 5003
    api_health_url = f"http://127.0.0.1:{backend_port}/api/health"
    
    # Command to run the backend via the project activation script
    # We force the use of conda run to ensure environment consistency
    command = [
        "powershell", "-File", ".\\activate_project_env.ps1",
        "-CommandToRun", f"conda run -n projet-is --no-capture-output python -m uvicorn api.main:app --host 127.0.0.1 --port {backend_port}"
    ]
    
    print("\n[Simple Fixture] Starting backend server...")
    
    # Use Popen to run the server in the background
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    stdout_log = open(os.path.join(log_dir, f"backend_stdout_{backend_port}.log"), "wb")
    stderr_log = open(os.path.join(log_dir, f"backend_stderr_{backend_port}.log"), "wb")
    
    process = subprocess.Popen(
        command,
        stdout=stdout_log,
        stderr=stderr_log,
        cwd=project_root,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP # For Windows to kill the whole process tree
    )
    
    # Wait for the backend to be ready by polling the health endpoint
    start_time = time.time()
    timeout = 60  # 60 seconds timeout for startup
    ready = False
    
    print(f"[Simple Fixture] Waiting for backend at {api_health_url}...")
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(api_health_url, timeout=1)
            if response.status_code == 200:
                print(f"[Simple Fixture] Backend is ready! (took {time.time() - start_time:.2f}s)")
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
        
        stdout_log.close()
        stderr_log.close()
        pytest.fail(f"Backend failed to start within {timeout} seconds.")

    # Yield control to the tests
    yield
    
    # Teardown: Stop the server after tests are done
    print("\n[Simple Fixture] Stopping backend server...")
    try:
        if os.name == 'nt':
            # On Windows, terminate the whole process group
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
        else:
            process.terminate()

        process.wait(timeout=10)
    except (subprocess.TimeoutExpired, ProcessLookupError):
        if process.poll() is None:
            print("[Simple Fixture] process.terminate() timed out, killing.")
            process.kill()
    finally:
        stdout_log.close()
        stderr_log.close()
        print("[Simple Fixture] Backend server stopped.")