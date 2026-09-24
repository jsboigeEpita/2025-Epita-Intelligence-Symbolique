#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Direct API FastAPI - Point d'Entree 2 (sans Unicode)
=========================================================

Demarre l'API FastAPI et appelle /api/analyze. Cette route fait analyser le
texte par Tweety (AspicParser) et n'appelle aucun LLM : ni cle OpenAI ni mode
mock n'entrent en jeu (#2525).
"""

import os
import sys
import time
import socket
import requests
import subprocess
import pytest
from pathlib import Path

# Vérifier la présence des fichiers API. La route testée n'utilise pas de clé
# OpenAI (#2525), donc son absence ne fait pas sauter ces tests.
API_ENVIRONMENT_AVAILABLE = True
API_ENVIRONMENT_ERROR = None
API_FILES_REQUIRED = [
    "api/main.py",
    "api/endpoints.py",
    "api/dependencies.py",
]

try:
    # Vérifier fichiers API
    missing_files = [f for f in API_FILES_REQUIRED if not Path(f).exists()]
    if missing_files:
        API_ENVIRONMENT_AVAILABLE = False
        API_ENVIRONMENT_ERROR = f"Fichiers API manquants: {', '.join(missing_files)}"
except Exception as e:
    API_ENVIRONMENT_AVAILABLE = False
    API_ENVIRONMENT_ERROR = str(e)


@pytest.mark.skipif(
    not API_ENVIRONMENT_AVAILABLE,
    reason=f"API test environment not configured - {API_ENVIRONMENT_ERROR if API_ENVIRONMENT_ERROR else 'Missing API files'}",
)
def test_environment_setup():
    """Test 1: Verification environnement."""
    print("\n=== Test 1: Verification environnement ===")

    # Verifier fichiers API
    api_files = [
        "api/main.py",
        "api/endpoints.py",
        "api/dependencies.py",
    ]
    for file_path in api_files:
        assert Path(file_path).exists(), f"Fichier manquant: {file_path}"
    print(f"[OK] Fichiers API presents: {len(api_files)}")

    print("[OK] Test environnement REUSSI")


@pytest.mark.skipif(
    not API_ENVIRONMENT_AVAILABLE,
    reason=f"API test environment not configured - {API_ENVIRONMENT_ERROR if API_ENVIRONMENT_ERROR else 'Missing API files'}",
)
def test_api_startup_and_basic_functionality():
    """Test 2: Demarrage API et fonctionnalite de base."""
    print("\n=== Test 2: Demarrage API et fonctionnalites ===")

    # La configuration de l'environnement est gérée par conftest.py
    # load_dotenv(override=True) # Cette ligne n'est plus nécessaire.

    # Find a free port to avoid conflicts with Docker or other services
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    free_port = sock.getsockname()[1]
    sock.close()
    api_url = f"http://localhost:{free_port}"
    api_process = None

    try:
        # Demarrer l'API
        print(f"Demarrage de l'API FastAPI sur port {free_port}...")
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(free_port),
            "--log-level",
            "debug",  # Augmenter les logs pour le débogage
        ]

        # Creation d'un environnement controle pour le sous-processus
        proc_env = os.environ.copy()
        proc_env["PYTHONPATH"] = os.getcwd()
        # Remove PYTEST_CURRENT_TEST so API subprocess doesn't auto-mock
        proc_env.pop("PYTEST_CURRENT_TEST", None)

        # Use DEVNULL to avoid pipe buffer deadlock — with debug logging,
        # the pipe fills up and blocks the uvicorn process from starting.
        api_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=os.getcwd(),
            env=proc_env,
        )

        print(f"API process demarre (PID: {api_process.pid})")

        # Attendre que l'API soit prete
        api_ready = False
        max_wait = 45
        wait_time = 0

        while wait_time < max_wait:
            try:
                response = requests.get(f"{api_url}/health", timeout=3)
                if response.status_code == 200:
                    api_ready = True
                    print(f"[OK] API prete apres {wait_time}s")
                    break
            except (requests.ConnectionError, requests.Timeout):
                pass

            time.sleep(2)
            wait_time += 2
            print(f"  Attente API... {wait_time}s/{max_wait}s")

        assert api_ready, f"API non prete apres {max_wait}s"

        # Test health endpoint
        print("\nTest endpoint /health...")
        response = requests.get(f"{api_url}/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"[OK] Health check: {data}")

        # Test examples endpoint
        print("\nTest endpoint /examples...")
        response = requests.get(f"{api_url}/api/examples", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "examples" in data
        print(f"[OK] Exemples trouves: {len(data['examples'])}")

        # Test analyse simple
        print("\nTest endpoint /analyze...")
        test_text = "Si il pleut, alors la route est mouillee. Il pleut. Donc la route est mouillee."

        start_time = time.time()
        response = requests.post(
            f"{api_url}/api/analyze", json={"text": test_text}, timeout=60
        )
        processing_time = time.time() - start_time

        assert response.status_code == 200, f"Erreur API: {response.text}"
        data = response.json()

        # Verifications — API returns {status, analysis_id, results: {...}}
        assert "analysis_id" in data
        assert data.get("status") == "success", data
        print(f"[OK] Analyse recue en {processing_time:.2f}s")

        # Le contrat de /api/analyze (#2525) : Tweety parse le texte avec son
        # AspicParser, sans LLM. La réponse nomme le composant qui l'a produite.
        # Cette route ne détecte aucun sophisme (#2526) ; ce test ne l'exige pas.
        metadata = data["results"].get("metadata", {})
        assert metadata.get("components_used") == [
            "TweetyArgumentReconstructor_centralized_v2"
        ], f"composant inattendu : {metadata!r}"
        structure = data["results"].get("argument_structure") or {}
        assert isinstance(structure.get("premises"), list), structure
        assert isinstance(structure.get("conclusion"), str), structure

        print("[OK] Test API et fonctionnalites REUSSI")

    except Exception as e:
        print(f"[ERREUR] {e}")
        raise

    finally:
        # Nettoyer
        if api_process:
            print("\nArret de l'API...")
            api_process.terminate()
            try:
                api_process.wait(timeout=10)
                print("[OK] API arretee proprement")
            except subprocess.TimeoutExpired:
                api_process.kill()
                print("[OK] API tuee forcement")


def run_all_tests():
    """Executer tous les tests."""
    print("=== TESTS VALIDATION POINT D'ENTREE 2 - API FASTAPI ===")

    try:
        test_environment_setup()
        test_api_startup_and_basic_functionality()

        print("\n" + "=" * 60)
        print("TOUS LES TESTS REUSSIS - VALIDATION CONFIRMEE")
        print("[OK] /health et /api/analyze repondent")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\nECHEC DE VALIDATION: {e}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
