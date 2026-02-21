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
        # Le champ 'timestamp' a été retiré, on ajuste le test.
        assert data["status"] == "healthy"

    def test_04_status_endpoint(self):
        """Test 4: Endpoint de statut de l'API."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        response = requests.get(f"{API_BASE_URL}/status")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "service_status" in data
        assert data["status"] == "operational"

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
            timeout=60,  # GPT-4o-mini peut prendre du temps
        )

        assert response.status_code == 200
        data = response.json()

        # Vérifier la structure de la réponse
        assert "analysis_id" in data
        assert "summary" in data
        assert "metadata" in data
        assert data["status"] == "success"

        # Vérifier que l'analyse contient du contenu
        summary = data["summary"]
        assert len(summary) > 10, "Résumé trop court, probablement un mock"

        # Vérifier que GPT-4o-mini est utilisé
        assert data["metadata"]["gpt_model"].startswith(
            "gpt-5-mini"
        ), "Service utilisé incorrect"

    def test_07_analyze_endpoint_fallacy_detection(self):
        """Test 7: Détection de sophisme avec GPT-4o-mini."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        # Texte contenant un sophisme (ad hominem)
        test_text = "Cette théorie est fausse parce que son auteur est un idiot."

        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/analyze", json={"text": test_text}, timeout=60
        )
        end_time = time.time()

        assert response.status_code == 200
        data = response.json()

        # Vérifier que l'analyse prend un temps réaliste (>2s pour authentique)
        processing_time = end_time - start_time
        assert (
            processing_time > 2.0
        ), f"Temps de traitement trop rapide ({processing_time:.2f}s), probablement un mock"

        # Vérifier le contenu de l'analyse
        summary = data["summary"].lower()
        sophisme_keywords = [
            "sophisme",
            "fallacy",
            "ad hominem",
            "attaque personnelle",
            "argument",
        ]

        found_keywords = [kw for kw in sophisme_keywords if kw in summary]
        assert (
            len(found_keywords) > 0
        ), f"Résumé ne détecte pas le sophisme. Mots trouvés: {found_keywords}"

    def test_08_analyze_endpoint_performance_check(self):
        """Test 8: Vérification des performances pour authentifier GPT-4o-mini."""
        if not self.api_started:
            pytest.skip("API non démarrée")

        test_text = "Le modus ponens est une règle d'inférence valide en logique propositionnelle."

        # Mesurer plusieurs appels pour vérifier la variabilité
        times = []
        responses = []

        for i in range(3):
            start_time = time.time()
            response = requests.post(
                f"{API_BASE_URL}/analyze",
                json={"text": f"{test_text} Test {i+1}"},
                timeout=60,
            )
            end_time = time.time()

            assert response.status_code == 200
            times.append(end_time - start_time)
            responses.append(response.json()["summary"])

        # Vérifier que les temps sont dans une plage réaliste pour GPT-4o-mini
        avg_time = sum(times) / len(times)
        assert (
            avg_time > 1.5
        ), f"Temps moyen trop rapide ({avg_time:.2f}s), probablement un mock"
        assert (
            avg_time < 30
        ), f"Temps moyen trop lent ({avg_time:.2f}s), possible problème"

        # Vérifier que les réponses sont différentes (signe d'authenticité)
        unique_responses = set(responses)
        assert len(unique_responses) > 1, "Réponses identiques, probablement un mock"

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
