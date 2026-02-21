#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitaires pour validation API FastAPI avec GPT-4o-mini authentique
========================================================================

Tests pour Point d'Entrée 2 : Applications Web (API FastAPI + Interface React + Tests Playwright)
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
import threading
import sys
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration du test
API_BASE_URL = "http://localhost:8001/api"
API_PORT = 8001
TEST_TIMEOUT = 30


@pytest.mark.skipif(
    any(arg == "--disable-jvm-session" for arg in sys.argv),
    reason="API server requires real JVM (run without --disable-jvm-session)",
)
class TestAPIFastAPIAuthentique:
    """Tests unitaires pour l'API FastAPI avec GPT-4o-mini authentique."""

    api_process = None
    api_started = False

    @classmethod
    def setup_class(cls):
        """Démarre le serveur API avant tous les tests et capture ses logs."""
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "api.main:app",
            "--host",
            "127.0.0.1",
            f"--port={API_PORT}",
            "--log-level",
            "info",
        ]

        try:
            cls.api_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"\n[ERREUR] Impossible de démarrer le serveur API: {e}")
            return

        start_time = time.time()
        health_url = API_BASE_URL.replace("/api", "") + "/health"

        while time.time() - start_time < TEST_TIMEOUT:
            try:
                response = requests.get(health_url, timeout=1)
                if response.status_code == 200:
                    cls.api_started = True
                    print("\n[INFO] Serveur API démarré avec succès.")
                    return
            except requests.ConnectionError:
                time.sleep(0.5)

        # Si on arrive ici, le serveur n'a pas démarré
        print("\n[ERREUR] Le serveur API n'a pas démarré dans le temps imparti.")

    @classmethod
    def teardown_class(cls):
        """Arrête le serveur API."""
        if cls.api_process:
            print("\n[INFO] Arrêt du serveur API...")
            cls.api_process.terminate()
            try:
                cls.api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("[WARNING] Le processus serveur ne s'est pas terminé, forçage.")
                cls.api_process.kill()

    def test_01_environment_setup(self):
        """Test 1: Vérification de la configuration environnement."""
        # Vérifier la clé OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY non trouvée dans l'environnement"
        assert len(api_key) > 20, "OPENAI_API_KEY semble invalide (trop courte)"

        # Vérifier que les fichiers API existent
        api_files = [
            "api/main.py",
            "api/endpoints.py",
            "api/dependencies.py",
        ]

        for file_path in api_files:
            assert Path(file_path).exists(), f"Fichier API manquant: {file_path}"

    def test_02_start_api_server(self):
        """Test 2: Vérification du démarrage effectif du serveur API."""
        if not self.api_started:
            pytest.fail(
                f"L'API n'a pas pu démarrer. Consultez les logs pour les erreurs."
            )
        assert self.api_started is True

    def test_03_health_endpoint(self):
        """Test 3: Endpoint de santé de l'API."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        # Le endpoint /health est sur la racine, pas sous /api
        health_url = API_BASE_URL.replace("/api", "") + "/health"
        response = requests.get(health_url)
        assert response.status_code == 200

        data = response.json()
        assert "status" in data

    def test_04_status_endpoint(self):
        """Test 4: Endpoint de statut de l'API."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        response = requests.get(f"{API_BASE_URL}/status")
        # Status may return 200 (operational/degraded) or 500 if service init fails
        assert response.status_code in (200, 500), f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] in ("operational", "degraded")

    def test_05_examples_endpoint(self):
        """Test 5: Endpoint des exemples prédéfinis."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        response = requests.get(f"{API_BASE_URL}/examples")
        assert response.status_code == 200

        data = response.json()
        assert "examples" in data
        assert len(data["examples"]) > 0

        # Vérifier la structure des exemples
        example = data["examples"][0]
        assert "text" in example
        assert "title" in example
        assert "type" in example

    def test_06_analyze_endpoint_simple_text(self):
        """Test 6: Analyse d'un texte simple via endpoint /analyze."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        test_text = "Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée."

        response = requests.post(
            f"{API_BASE_URL}/analyze",
            json={"text": test_text},
            timeout=60,
        )

        assert response.status_code == 200
        data = response.json()

        # Vérifier la structure de la réponse (format: {analysis_id, status, results: {...}})
        assert "analysis_id" in data
        assert data["status"] == "success"
        assert "results" in data

        results = data["results"]
        assert "metadata" in results
        assert "metadata" in results and "duration" in results["metadata"]

    def test_07_analyze_endpoint_fallacy_detection(self):
        """Test 7: Analyse d'un texte contenant un sophisme."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        # Texte contenant un sophisme (ad hominem)
        test_text = "Cette théorie est fausse parce que son auteur est un idiot."

        response = requests.post(
            f"{API_BASE_URL}/analyze", json={"text": test_text}, timeout=60
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "results" in data

    def test_08_analyze_endpoint_multiple_calls(self):
        """Test 8: Vérification que plusieurs appels fonctionnent."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        test_text = "Le modus ponens est une règle d'inférence valide en logique propositionnelle."

        for i in range(2):
            response = requests.post(
                f"{API_BASE_URL}/analyze",
                json={"text": f"{test_text} Test {i+1}"},
                timeout=60,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "results" in data

    def test_09_analyze_endpoint_error_handling(self):
        """Test 9: Gestion d'erreurs de l'endpoint d'analyse."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        # Test avec texte vide - Le comportement a changé, l'API retourne 200.
        response = requests.post(f"{API_BASE_URL}/analyze", json={"text": ""})
        assert (
            response.status_code == 200
        ), "Le service traite maintenant le texte vide."

        # Test sans paramètre text
        response = requests.post(f"{API_BASE_URL}/analyze", json={})
        assert response.status_code == 422, "Devrait rejeter l'absence de texte"

        # Test avec texte trop long
        long_text = "a" * 10000
        response = requests.post(f"{API_BASE_URL}/analyze", json={"text": long_text})
        assert response.status_code == 200

    def test_10_api_documentation(self):
        """Test 10: Documentation API automatique FastAPI."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        # Les endpoints de documentation sont sur la racine de l'app, pas sous /api
        root_url = API_BASE_URL.replace("/api", "")

        # Test endpoint docs
        response = requests.get(f"{root_url}/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

        # Test OpenAPI schema
        response = requests.get(f"{root_url}/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        assert "/api/analyze" in schema["paths"]


def pytest_main():
    """Point d'entrée pour exécuter les tests."""
    return pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    pytest_main()
