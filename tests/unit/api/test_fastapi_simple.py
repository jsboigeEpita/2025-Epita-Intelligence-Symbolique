#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitaires simples pour validation API FastAPI avec GPT-4o-mini
==================================================================

Tests simplifiés pour Point d'Entrée 2 : Applications Web
"""

# AUTO_ENV: Activation automatique environnement
try:
    import argumentation_analysis.core.environment  # Auto-activation environnement intelligent
except ImportError:
    print("[WARNING] auto_env non disponible - environnement non activé")

import pytest
import time
import requests
import subprocess
import os
import sys

# Configuration modèle LLM depuis .env
EXPECTED_MODEL = os.getenv("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
import threading
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration du test
API_BASE_URL = "http://localhost:8001/api"
API_PORT = 8001
TEST_TIMEOUT = 45


@pytest.mark.skipif(
    any(arg == "--disable-jvm-session" for arg in sys.argv),
    reason="API server requires real JVM (run without --disable-jvm-session)",
)
class TestAPIFastAPISimple:
    """Tests unitaires simplifiés pour l'API FastAPI avec GPT-4o-mini authentique."""

    @classmethod
    def setup_class(cls):
        """Configuration initiale des tests."""
        cls.api_process = None
        cls.api_started = False

    @classmethod
    def teardown_class(cls):
        """Nettoyage après tous les tests."""
        if cls.api_process:
            cls.api_process.terminate()
            try:
                cls.api_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                cls.api_process.kill()

    def test_01_environment_verification(self):
        """Test 1: Vérification de l'environnement de base."""
        # Vérifier la clé OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY non trouvée"
        assert len(api_key) > 20, "OPENAI_API_KEY semble invalide"

        # Vérifier que les fichiers API existent
        api_files = [
            "api/main.py",
            "api/endpoints.py",
            "api/dependencies.py",
        ]

        for file_path in api_files:
            assert Path(file_path).exists(), f"Fichier API manquant: {file_path}"

    def test_02_start_api_via_command(self):
        """Test 2: Démarrage du serveur API via ligne de commande."""

        def start_api_server():
            """Démarre l'API via uvicorn en ligne de commande."""
            try:
                cmd = [
                    "python",
                    "-m",
                    "uvicorn",
                    "api.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(API_PORT),
                    "--log-level",
                    "info",
                ]

                self.__class__.api_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=os.getcwd(),
                    env=dict(os.environ, PYTHONPATH=os.getcwd()),
                )
                print(f"API process started with PID: {self.api_process.pid}")

            except Exception as e:
                print(f"Erreur démarrage API: {e}")

        # Démarrer l'API dans un thread
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()

        # Attendre que l'API soit prête
        start_time = time.time()
        while time.time() - start_time < TEST_TIMEOUT:
            try:
                # Le health check est à la racine, pas sous /api
                health_check_url = f"http://localhost:{API_PORT}/health"
                response = requests.get(health_check_url, timeout=3)
                if response.status_code == 200:
                    self.__class__.api_started = True
                    print(
                        f"API démarrée avec succès après {time.time() - start_time:.1f}s"
                    )
                    break
            except (requests.ConnectionError, requests.Timeout):
                pass
            time.sleep(2)

        assert self.api_started, f"API n'a pas démarré dans les {TEST_TIMEOUT}s"

    def test_03_health_check(self):
        """Test 3: Vérification de l'endpoint de santé."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        # Le health check est à la racine, pas sous /api
        health_check_url = f"http://localhost:{API_PORT}/health"
        response = requests.get(health_check_url, timeout=10)
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        print(f"Health check OK: {data}")

    def test_04_examples_endpoint(self):
        """Test 4: Vérification de l'endpoint des exemples."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        response = requests.get(f"{API_BASE_URL}/examples", timeout=10)
        assert response.status_code == 200

        data = response.json()
        assert "examples" in data
        assert len(data["examples"]) > 0
        print(f"Exemples trouvés: {len(data['examples'])}")

    def test_05_simple_analysis(self):
        """Test 5: Analyse simple via /api/analyze."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        test_text = "Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée."

        response = requests.post(
            f"{API_BASE_URL}/analyze",
            json={"text": test_text},
            timeout=60,
        )

        assert response.status_code == 200, f"Erreur API: {response.text}"

        data = response.json()
        # Response format: {analysis_id, status, results: {fallacies, metadata, ...}}
        assert "analysis_id" in data
        assert data["status"] == "success"
        assert "results" in data
        assert "metadata" in data["results"]

    def test_06_fallacy_detection(self):
        """Test 6: Analyse d'un texte contenant un sophisme."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        test_text = "Cette théorie est fausse parce que son auteur est un charlatan."

        response = requests.post(
            f"{API_BASE_URL}/analyze", json={"text": test_text}, timeout=60
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "results" in data

    def test_07_api_consistency(self):
        """Test 7: Vérification de la cohérence des réponses."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        test_text = "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."

        for i in range(2):
            response = requests.post(
                f"{API_BASE_URL}/analyze",
                json={"text": f"{test_text} (Test {i+1})"},
                timeout=60,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "results" in data


def pytest_main():
    """Point d'entrée pour exécuter les tests."""
    return pytest.main([__file__, "-v", "--tb=short", "-s"])


if __name__ == "__main__":
    pytest_main()
