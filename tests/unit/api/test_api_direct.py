#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Direct API FastAPI - Point d'Entrée 2
==========================================

Démarre l'API FastAPI et appelle /api/analyze. Cette route fait analyser le
texte par Tweety (AspicParser) et n'appelle aucun LLM : ni clé OpenAI ni mode
mock n'entrent en jeu (#2525).
"""

import os
import sys
import time
import socket
import requests
import subprocess
import threading
from pathlib import Path
import pytest

# Disponibilité calculée À L'EXÉCUTION (#1827) : l'import de ce fichier ne
# doit ni charger .env ni écrire os.environ. La route testée n'utilise pas de
# clé (#2525), donc ce fichier ne charge plus .env du tout.
API_FILES_REQUIRED = ["api/main.py", "api/endpoints.py", "api/dependencies.py"]


def _api_environment_status():
    """(disponible, raison) — évalué au moment où le test démarre."""
    try:
        # Vérifier fichiers API
        missing_files = [f for f in API_FILES_REQUIRED if not Path(f).exists()]
        if missing_files:
            return False, f"Fichiers API manquants: {', '.join(missing_files)}"

        # Vérifier disponibilité PyTorch (requis pour démarrage API via spacy/thinc)
        if sys.platform == "win32":
            try:
                import torch
            except (ImportError, OSError) as e:
                return False, (
                    f"PyTorch indisponible sur Windows (requis pour API) - {str(e)[:100]}"
                )
    except Exception as e:
        return False, str(e)
    return True, None


def _ensure_api_environment():
    """Vérifie la disponibilité au début de CHAQUE test."""
    available, error = _api_environment_status()
    if not available:
        pytest.skip(
            f"API test environment not configured - " f"{error or 'Missing API files'}"
        )


def test_environment_setup():
    """Test 1: Vérification environnement."""
    _ensure_api_environment()
    print("\n=== Test 1: Vérification environnement ===")

    # Vérifier fichiers API
    api_files = ["api/main.py", "api/endpoints.py", "api/dependencies.py"]
    for file_path in api_files:
        assert Path(file_path).exists(), f"Fichier manquant: {file_path}"
    print(f"✓ Fichiers API présents: {len(api_files)}")

    print("✓ Test environnement RÉUSSI")


def test_api_startup_and_basic_functionality():
    """Test 2: Démarrage API et fonctionnalité de base."""
    _ensure_api_environment()
    print("\n=== Test 2: Démarrage API et fonctionnalités ===")

    # Find a free port to avoid conflicts with Docker or other services
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    free_port = sock.getsockname()[1]
    sock.close()
    api_url = f"http://localhost:{free_port}"
    api_process = None

    # Fonction pour lire les flux de sortie en continu
    def stream_reader(stream, buffer):
        for line in iter(stream.readline, ""):
            buffer.append(line)
        stream.close()

    try:
        # Démarrer l'API
        print(f"Démarrage de l'API FastAPI sur port {free_port}...")
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
            "info",
        ]

        api_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd(),
            env=dict(os.environ, PYTHONPATH=os.getcwd()),
        )

        print(f"API process démarré (PID: {api_process.pid})")

        # Buffers pour capturer stdout et stderr
        stdout_buffer = []
        stderr_buffer = []

        # Démarrer les threads pour lire les flux
        stdout_thread = threading.Thread(
            target=stream_reader, args=(api_process.stdout, stdout_buffer)
        )
        stderr_thread = threading.Thread(
            target=stream_reader, args=(api_process.stderr, stderr_buffer)
        )
        stdout_thread.start()
        stderr_thread.start()

        # Attendre que l'API soit prête
        api_ready = False
        max_wait = 30
        wait_time = 0

        while wait_time < max_wait:
            if not stdout_thread.is_alive() and not stderr_thread.is_alive():
                print("✗ Le processus API s'est terminé prématurément.")
                break
            try:
                response = requests.get(f"{api_url}/health", timeout=3)
                if response.status_code == 200:
                    # Verify the response body is valid JSON with expected content
                    try:
                        data = response.json()
                        if data.get("status") == "healthy":
                            api_ready = True
                            print(f"✓ API prête après {wait_time}s")
                            break
                    except requests.exceptions.JSONDecodeError:
                        # Response body not ready yet, continue waiting
                        pass
            except (requests.ConnectionError, requests.Timeout):
                pass

            time.sleep(2)
            wait_time += 2
            print(f"  Attente API... {wait_time}s/{max_wait}s")

        if not api_ready:
            error_message = f"API non prête après {max_wait}s.\n"
            error_message += "--- STDERR ---\n"
            error_message += "".join(stderr_buffer)
            error_message += "\n--- STDOUT ---\n"
            error_message += "".join(stdout_buffer)
            assert False, error_message

        # Test health endpoint
        print("\nTest endpoint /health...")
        response = requests.get(f"{api_url}/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Health check: {data}")

        # Test examples endpoint
        print("\nTest endpoint /api/examples...")
        response = requests.get(f"{api_url}/api/examples", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "examples" in data
        print(f"✓ Exemples trouvés: {len(data['examples'])}")

        # Test analyse simple
        print("\nTest endpoint /analyze...")
        test_text = "Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée."

        start_time = time.time()
        response = requests.post(
            f"{api_url}/api/analyze", json={"text": test_text}, timeout=60
        )
        processing_time = time.time() - start_time

        assert response.status_code == 200, f"Erreur API: {response.text}"
        data = response.json()

        # Vérifications
        assert "analysis_id" in data
        assert "status" in data
        assert data["status"] == "success"
        assert "results" in data
        assert "fallacies" in data["results"]

        print(f"✓ Analyse reçue en {processing_time:.2f}s")

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

        print("✓ Test API et fonctionnalités RÉUSSI")

    except Exception as e:
        print(f"✗ ERREUR: {e}")
        raise

    finally:
        # Nettoyer
        if api_process:
            print("\nArrêt de l'API...")
            api_process.terminate()
            try:
                api_process.wait(timeout=10)
                print("✓ API arrêtée proprement")
            except subprocess.TimeoutExpired:
                api_process.kill()
                print("✓ API tuée forcément")


def run_all_tests():
    """Exécuter tous les tests."""
    print("=== TESTS VALIDATION POINT D'ENTRÉE 2 - API FASTAPI ===")

    try:
        test_environment_setup()
        test_api_startup_and_basic_functionality()

        print("\n" + "=" * 60)
        print("🎉 TOUS LES TESTS RÉUSSIS - VALIDATION CONFIRMÉE")
        print("✓ /health et /api/analyze répondent")
        print("=" * 60)

        return True

    except pytest.skip.Exception:
        # _ensure_api_environment() skippe quand l'env API est absent ; Skipped
        # hérite de BaseException, le except Exception ci-dessous ne l'attrape
        # pas — sans ce catch le __main__ trace une exception brute au lieu
        # d'un message.
        print("\n⏭️ SKIP: environnement API non configuré")
        return False
    except Exception as e:
        print(f"\n❌ ÉCHEC DE VALIDATION: {e}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
