import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.endpoints import framework_router, router as default_router
from api.services import DungAnalysisService
from unittest.mock import MagicMock
from api.dependencies import get_dung_analysis_service
from argumentation_analysis.core.jvm_setup import initialize_jvm

def main():
    """
    Fonction principale du worker pour exécuter les tests d'API dans un processus isolé.
    """
    # Ce worker s'exécute dans un sous-processus et doit initialiser la JVM lui-même.
    # Il utilise la fonction centralisée `initialize_jvm` pour garantir la cohérence.
    if not initialize_jvm():
        print("ERREUR CRITIQUE: Échec de l'initialisation de la JVM dans le worker.")
        exit(1)

    test_app = FastAPI(title="Worker Test API")

    # Création du mock pour le service d'analyse
    mock_service = MagicMock(spec=DungAnalysisService)
    test_app.dependency_overrides[get_dung_analysis_service] = lambda: mock_service

    # Inclusion des routeurs
    test_app.include_router(default_router)
    test_app.include_router(framework_router)

    with TestClient(test_app) as client:
        # --- Test 1: Succès de l'analyse ---
        mock_response_success = {
            "extensions": {
                "grounded": ["a", "c"], "preferred": [["a", "c"]], "stable": [["a", "c"]],
                "complete": [["a", "c"]], "admissible": [["a", "c"], []], "ideal": ["a"],
                "semi_stable": [["a", "c"]]
            },
            "argument_status": {
                "a": {"credulously_accepted": True, "skeptically_accepted": True, "grounded_accepted": True, "stable_accepted": True},
                "b": {"credulously_accepted": False, "skeptically_accepted": False, "grounded_accepted": False, "stable_accepted": False},
                "c": {"credulously_accepted": True, "skeptically_accepted": True, "grounded_accepted": False, "stable_accepted": True}
            },
            "graph_properties": {"num_arguments": 3, "num_attacks": 2, "has_cycles": False, "cycles": [], "self_attacking_nodes": []}
        }
        mock_service.analyze_framework.return_value = mock_response_success
        request_data_success = {"arguments": ["a", "b", "c"], "attacks": [["a", "b"], ["b", "c"]]}
        response_success = client.post("/api/v1/framework/analyze", json=request_data_success)
        assert response_success.status_code == 200
        # La réponse de l'API est imbriquée sous la clé "analysis"
        assert response_success.json() == {"analysis": mock_response_success}
        print("Test 1 (Success) : OK")

        # --- Test 2: Entrée invalide ---
        mock_service.reset_mock()
        invalid_request_data = {"arguments": ["a", "b"], "attacks": ["a-b"]}
        response_invalid = client.post("/api/v1/framework/analyze", json=invalid_request_data)
        assert response_invalid.status_code == 422
        print("Test 2 (Invalid Input) : OK")

        # --- Test 3: Entrée vide ---
        mock_service.reset_mock()
        mock_response_empty = {
            "extensions": {
                "grounded": [], "preferred": [[]], "stable": [[]], "complete": [[]],
                "admissible": [[]], "ideal": [], "semi_stable": [[]]
            },
            "argument_status": {},
            "graph_properties": {"num_arguments": 0, "num_attacks": 0, "has_cycles": False, "cycles": [], "self_attacking_nodes": []}
        }
        mock_service.analyze_framework.return_value = mock_response_empty
        request_data_empty = {"arguments": [], "attacks": []}
        response_empty = client.post("/api/v1/framework/analyze", json=request_data_empty)
        assert response_empty.status_code == 200
        assert response_empty.json() == {"analysis": mock_response_empty}
        print("Test 3 (Empty Input) : OK")

if __name__ == "__main__":
    main()