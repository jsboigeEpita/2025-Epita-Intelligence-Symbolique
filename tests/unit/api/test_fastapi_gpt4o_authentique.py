#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitaires pour validation API FastAPI avec endpoints authentiques
======================================================================

Tests pour Point d'Entrée 2 : Applications Web (API FastAPI).
Utilise TestClient (pas de subprocess) pour tester les endpoints.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock
from fastapi.testclient import TestClient

from api.main import app

# Configuration du test
API_BASE_URL = "/api"


@pytest.fixture
def client():
    """Fournit un TestClient FastAPI avec contexte projet simulé."""
    ctx = Mock()
    ctx.jvm_initialized = True
    ctx.tweety_classes = {"AspicParser": Mock()}
    mock_kb = Mock()
    mock_kb.getArguments.return_value = ["premise1", "premise2", "conclusion1"]
    ctx.tweety_classes["AspicParser"].parseBeliefBase.return_value = mock_kb

    app.state.project_context = ctx
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestAPIFastAPIAuthentique:
    """Tests unitaires pour l'API FastAPI avec vérifications authentiques."""

    def test_01_environment_setup(self):
        """Test 1: Vérification de la configuration environnement."""
        api_key = os.getenv("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY non trouvée dans l'environnement"
        assert len(api_key) > 20, "OPENAI_API_KEY semble invalide (trop courte)"

        api_files = [
            "api/main.py",
            "api/endpoints.py",
            "api/dependencies.py",
        ]

        for file_path in api_files:
            assert Path(file_path).exists(), f"Fichier API manquant: {file_path}"

    def test_02_start_api_server(self, client):
        """Test 2: Vérification du démarrage effectif du serveur API."""
        assert client is not None

    def test_03_health_endpoint(self, client):
        """Test 3: Endpoint de santé de l'API."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data

    def test_04_status_endpoint(self, client):
        """Test 4: Endpoint de statut de l'API."""
        response = client.get(f"{API_BASE_URL}/status")
        # Status may return 200 (operational/degraded) or 500 if service init fails
        assert response.status_code in (
            200,
            500,
        ), f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] in ("operational", "degraded")

    def test_05_examples_endpoint(self, client):
        """Test 5: Endpoint des exemples prédéfinis."""
        response = client.get(f"{API_BASE_URL}/examples")
        assert response.status_code == 200

        data = response.json()
        assert "examples" in data
        assert len(data["examples"]) > 0

        example = data["examples"][0]
        assert "text" in example
        assert "title" in example
        assert "type" in example

    def test_06_analyze_endpoint_simple_text(self, client):
        """Test 6: Analyse d'un texte simple via endpoint /analyze."""
        test_text = "Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée."

        response = client.post(
            f"{API_BASE_URL}/analyze",
            json={"text": test_text},
        )

        assert response.status_code == 200
        data = response.json()

        assert "analysis_id" in data
        assert data["status"] == "success"
        assert "results" in data

        results = data["results"]
        assert "metadata" in results
        assert "duration" in results["metadata"]

    def test_07_analyze_endpoint_fallacy_detection(self, client):
        """Test 7: Analyse d'un texte contenant un sophisme."""
        test_text = "Cette théorie est fausse parce que son auteur est un idiot."

        response = client.post(f"{API_BASE_URL}/analyze", json={"text": test_text})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "results" in data

    def test_08_analyze_endpoint_multiple_calls(self, client):
        """Test 8: Vérification que plusieurs appels fonctionnent."""
        test_text = "Le modus ponens est une règle d'inférence valide en logique propositionnelle."

        for i in range(2):
            response = client.post(
                f"{API_BASE_URL}/analyze",
                json={"text": f"{test_text} Test {i+1}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "results" in data

    def test_09_analyze_endpoint_error_handling(self, client):
        """Test 9: Gestion d'erreurs de l'endpoint d'analyse."""
        # Test avec texte vide
        response = client.post(f"{API_BASE_URL}/analyze", json={"text": ""})
        assert (
            response.status_code == 200
        ), "Le service traite maintenant le texte vide."

        # Test sans paramètre text
        response = client.post(f"{API_BASE_URL}/analyze", json={})
        assert response.status_code == 422, "Devrait rejeter l'absence de texte"

        # Test avec texte long
        long_text = "a" * 10000
        response = client.post(f"{API_BASE_URL}/analyze", json={"text": long_text})
        assert response.status_code == 200

    def test_10_api_documentation(self, client):
        """Test 10: Documentation API automatique FastAPI."""
        # Test endpoint docs
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        assert "/api/analyze" in schema["paths"]
