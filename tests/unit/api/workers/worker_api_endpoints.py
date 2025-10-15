import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.endpoints import framework_router, router as default_router
from api.services import DungAnalysisService
from unittest.mock import MagicMock
from api.dependencies import get_dung_analysis_service
from argumentation_analysis.core.jvm_setup import initialize_jvm
import sys
import os
import logging

LOG_FILE = os.path.join(os.path.dirname(__file__), "worker_api_endpoints.log")

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=LOG_FILE,
    filemode="w",  # 'w' pour écraser le fichier à chaque exécution
)


def main():
    """
    Fonction principale du worker pour exécuter les tests d'API dans un processus isolé.
    """
    logging.info("--- DEBUT DU WORKER DE TEST API ---")

    # Ce worker s'exécute dans un sous-processus et doit initialiser la JVM lui-même.
    # Il utilise la fonction centralisée `initialize_jvm` pour garantir la cohérence.
    if not initialize_jvm():
        logging.error(
            "ERREUR CRITIQUE: Échec de l'initialisation de la JVM dans le worker."
        )
        exit(1)
    logging.info("JVM initialisée avec succès.")

    test_app = FastAPI(title="Worker Test API")

    # Création du mock pour le service d'analyse
    mock_service = MagicMock(spec=DungAnalysisService)
    test_app.dependency_overrides[get_dung_analysis_service] = lambda: mock_service
    logging.info("Service mocké.")

    # Inclusion des routeurs
    test_app.include_router(default_router)
    test_app.include_router(framework_router)
    logging.info("Routeurs inclus.")

    with TestClient(test_app) as client:
        # --- Test 1: Succès de l'analyse ---
        logging.info("\n--- Début Test 1 (Succès) ---")
        mock_response_success = {
            "extensions": {
                "grounded": ["a", "c"],
                "preferred": [["a", "c"]],
                "stable": [["a", "c"]],
                "complete": [["a", "c"]],
                "admissible": [["a", "c"], []],
                "ideal": ["a"],
                "semi_stable": [["a", "c"]],
            },
            "argument_status": {
                "a": {
                    "credulously_accepted": True,
                    "skeptically_accepted": True,
                    "grounded_accepted": True,
                    "stable_accepted": True,
                },
                "b": {
                    "credulously_accepted": False,
                    "skeptically_accepted": False,
                    "grounded_accepted": False,
                    "stable_accepted": False,
                },
                "c": {
                    "credulously_accepted": True,
                    "skeptically_accepted": True,
                    "grounded_accepted": False,
                    "stable_accepted": True,
                },
            },
            "graph_properties": {
                "num_arguments": 3,
                "num_attacks": 2,
                "has_cycles": False,
                "cycles": [],
                "self_attacking_nodes": [],
            },
        }
        mock_service.analyze_framework.return_value = mock_response_success
        request_data_success = {
            "arguments": ["a", "b", "c"],
            "attacks": [["a", "b"], ["b", "c"]],
        }
        response_success = client.post(
            "/api/v1/framework/analyze", json=request_data_success
        )
        logging.debug(f"Test 1 Status Code: {response_success.status_code}")
        logging.debug(f"Test 1 Réponse attendue (mock): {mock_response_success}")
        try:
            response_json = response_success.json()
            logging.debug(f"Test 1 Réponse obtenue (json): {response_json}")
            assert response_success.status_code == 200
            assert response_json == {"analysis": mock_response_success}
            logging.info("Test 1 (Succès) : OK")
        except Exception as e:
            logging.error(f"ERREUR Test 1: {e}", exc_info=True)

        # --- Test 2: Entrée invalide ---
        logging.info("\n--- Début Test 2 (Entrée invalide) ---")
        mock_service.reset_mock()
        invalid_request_data = {"arguments": ["a", "b"], "attacks": ["a-b"]}
        response_invalid = client.post(
            "/api/v1/framework/analyze", json=invalid_request_data
        )
        logging.debug(f"Test 2 Status Code: {response_invalid.status_code}")
        assert response_invalid.status_code == 422
        logging.info("Test 2 (Entrée invalide) : OK")

        # --- Test 3: Entrée vide ---
        logging.info("\n--- Début Test 3 (Entrée vide) ---")
        mock_service.reset_mock()
        mock_response_empty = {
            "extensions": {
                "grounded": [],
                "preferred": [[]],
                "stable": [[]],
                "complete": [[]],
                "admissible": [[]],
                "ideal": [],
                "semi_stable": [[]],
            },
            "argument_status": {},
            "graph_properties": {
                "num_arguments": 0,
                "num_attacks": 0,
                "has_cycles": False,
                "cycles": [],
                "self_attacking_nodes": [],
            },
        }
        mock_service.analyze_framework.return_value = mock_response_empty
        request_data_empty = {"arguments": [], "attacks": []}
        response_empty = client.post(
            "/api/v1/framework/analyze", json=request_data_empty
        )
        logging.debug(f"Test 3 Status Code: {response_empty.status_code}")
        logging.debug(f"Test 3 Réponse attendue (mock): {mock_response_empty}")
        try:
            response_json_empty = response_empty.json()
            logging.debug(f"Test 3 Réponse obtenue (json): {response_json_empty}")
            assert response_empty.status_code == 200
            assert response_json_empty == {"analysis": mock_response_empty}
            logging.info("Test 3 (Entrée vide) : OK")
        except Exception as e:
            logging.error(f"ERREUR Test 3: {e}", exc_info=True)
            sys.exit(1)  # Quitter avec un code d'erreur si un test échoue

    logging.info("\n--- FIN DU WORKER DE TEST API ---")
    sys.exit(0)  # Quitter avec un code de succès si tout s'est bien passé


if __name__ == "__main__":
    main()
