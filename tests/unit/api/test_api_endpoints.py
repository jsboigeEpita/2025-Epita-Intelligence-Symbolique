import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.endpoints import framework_router, router as default_router
from api.services import DungAnalysisService
from unittest.mock import MagicMock
import os
from api.dependencies import get_dung_analysis_service

@pytest.fixture(scope="module")
def api_client(integration_jvm):
    """
    Crée un client de test pour l'API avec les dépendances surchargées.
    """
    if not integration_jvm or not integration_jvm.isJVMStarted():
        pytest.fail("La fixture integration_jvm n'a pas réussi à démarrer la JVM pour le client API.")

    test_app = FastAPI(title="Test Argumentation Analysis API")
    
    # Créer un mock de service qui sera partagé par tous les tests de ce module
    mock_service = MagicMock(spec=DungAnalysisService)
    
    # Surcharger la dépendance de l'application avec le mock
    test_app.dependency_overrides[get_dung_analysis_service] = lambda: mock_service
    
    # Inclure les routeurs APRÈS avoir surchargé les dépendances
    test_app.include_router(default_router)
    test_app.include_router(framework_router)
    
    with TestClient(test_app) as client:
        # Attacher le mock au client pour y accéder facilement dans les tests
        client.mock_service = mock_service
        yield client

def test_analyze_framework_endpoint_success(api_client):
    """
    Teste la réussite de l'endpoint /api/v1/framework/analyze avec des données valides.
    """
    # Préparer une réponse complète et valide pour le mock
    mock_response = {
        "semantics": {
            "grounded": ["a", "c"],
            "preferred": [["a", "c"]],
            "stable": [["a", "c"]],
            "complete": [["a", "c"]],
            "admissible": [["a", "c"], []],
            "ideal": ["a"],
            "semi_stable": [["a", "c"]]
        },
        "argument_status": {
            "a": {"credulously_accepted": True, "skeptically_accepted": True, "grounded_accepted": True, "stable_accepted": True},
            "b": {"credulously_accepted": False, "skeptically_accepted": False, "grounded_accepted": False, "stable_accepted": False},
            "c": {"credulously_accepted": True, "skeptically_accepted": True, "grounded_accepted": False, "stable_accepted": True}
        },
        "graph_properties": {
            "num_arguments": 3,
            "num_attacks": 2,
            "has_cycles": False,
            "cycles": [],
            "self_attacking_nodes": []
        }
    }
    api_client.mock_service.analyze_framework.return_value = mock_response

    request_data = {
        "arguments": ["a", "b", "c"],
        "attacks": [["a", "b"], ["b", "c"]]
    }
    
    response = api_client.post("/api/v1/framework/analyze", json=request_data)
    
    assert response.status_code == 200
    assert response.json() == mock_response
    
    api_client.mock_service.analyze_framework.assert_called_once_with(
        request_data['arguments'],
        [tuple(att) for att in request_data['attacks']]
    )

def test_analyze_framework_endpoint_invalid_input(api_client):
    """
    Teste l'endpoint avec des données invalides (format d'attaque incorrect).
    """
    invalid_request_data = {
        "arguments": ["a", "b"],
        "attacks": ["a-b"]
    }
    
    response = api_client.post("/api/v1/framework/analyze", json=invalid_request_data)
    
    assert response.status_code == 422

def test_analyze_framework_endpoint_empty_input(api_client):
    """
    Teste l'endpoint avec des listes vides.
    """
    # Préparer une réponse complète et valide pour un cas vide
    mock_response = {
        "semantics": {
            "grounded": [],
            "preferred": [[]],
            "stable": [[]],
            "complete": [[]],
            "admissible": [[]],
            "ideal": [],
            "semi_stable": [[]]
        },
        "argument_status": {},
        "graph_properties": {
            "num_arguments": 0,
            "num_attacks": 0,
            "has_cycles": False,
            "cycles": [],
            "self_attacking_nodes": []
        }
    }
    api_client.mock_service.analyze_framework.return_value = mock_response

    request_data = {
        "arguments": [],
        "attacks": []
    }

    response = api_client.post("/api/v1/framework/analyze", json=request_data)
    
    assert response.status_code == 200
    assert response.json() == mock_response