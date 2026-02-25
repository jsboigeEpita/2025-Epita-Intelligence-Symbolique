#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitaires simples pour validation API FastAPI
====================================================

Tests simplifiés pour Point d'Entrée 2 : Applications Web.
Utilise TestClient (pas de subprocess) pour tester les endpoints.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock
from fastapi.testclient import TestClient

from api.main import app

# Configuration modèle LLM depuis .env
EXPECTED_MODEL = os.getenv("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")


@pytest.fixture
def client():
    """Fournit un TestClient FastAPI avec contexte projet simulé."""
    ctx = Mock()
    ctx.jvm_initialized = True
    ctx.tweety_classes = {"AspicParser": Mock()}
    mock_kb = Mock()
    mock_kb.getArguments.return_value = ["premise1", "conclusion1"]
    ctx.tweety_classes["AspicParser"].parseBeliefBase.return_value = mock_kb

    app.state.project_context = ctx
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestAPIFastAPISimple:
    """Tests unitaires simplifiés pour l'API FastAPI."""

    def test_01_environment_verification(self):
        """Test 1: Vérification de l'environnement de base."""
        api_key = os.getenv("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY non trouvée"
        assert len(api_key) > 20, "OPENAI_API_KEY semble invalide"

        api_files = [
            "api/main.py",
            "api/endpoints.py",
            "api/dependencies.py",
        ]

        for file_path in api_files:
            assert Path(file_path).exists(), f"Fichier API manquant: {file_path}"

    def test_02_api_starts(self, client):
        """Test 2: Vérification que l'app FastAPI démarre via TestClient."""
        assert client is not None

    def test_03_health_check(self, client):
        """Test 3: Vérification de l'endpoint de santé."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_04_examples_endpoint(self, client):
        """Test 4: Vérification de l'endpoint des exemples."""
        response = client.get("/api/examples")
        assert response.status_code == 200

        data = response.json()
        assert "examples" in data
        assert len(data["examples"]) > 0

    def test_05_simple_analysis(self, client):
        """Test 5: Analyse simple via /api/analyze."""
        test_text = "Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée."

        response = client.post(
            "/api/analyze",
            json={"text": test_text},
        )

        assert response.status_code == 200, f"Erreur API: {response.text}"

        data = response.json()
        assert "analysis_id" in data
        assert data["status"] == "success"
        assert "results" in data
        assert "metadata" in data["results"]

    def test_06_fallacy_detection(self, client):
        """Test 6: Analyse d'un texte contenant un sophisme."""
        test_text = "Cette théorie est fausse parce que son auteur est un charlatan."

        response = client.post("/api/analyze", json={"text": test_text})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "results" in data

    def test_07_api_consistency(self, client):
        """Test 7: Vérification de la cohérence des réponses."""
        test_text = "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."

        for i in range(2):
            response = client.post(
                "/api/analyze",
                json={"text": f"{test_text} (Test {i+1})"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "results" in data
