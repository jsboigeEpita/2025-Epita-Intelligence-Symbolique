import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.dependencies import get_analysis_service, get_mock_analysis_service
from api.endpoints import router  # Importer le bon routeur

# --- Création de l'application de test ---
# Il est préférable de le faire dans une fixture pour garantir l'isolation,
# mais pour cet exemple simple, une instance globale est suffisante.

app = FastAPI()

# Inclure le routeur qui contient les endpoints /analyze et /health
app.include_router(router, prefix="/api/v1/analyzer")

# Remplacer la dépendance authentique par le mock EXPLICITEMENT pour tous les tests de ce fichier
app.dependency_overrides[get_analysis_service] = get_mock_analysis_service

client = TestClient(app)


def test_status_endpoint_with_mock():
    """
    Vérifie que l'endpoint de statut fonctionne correctement avec le service mocké.
    Cet endpoint utilise bien `get_analysis_service`.
    """
    # L'endpoint est /status, mais le routeur est préfixé par /api/v1/analyzer
    response = client.get("/api/v1/analyzer/status")

    # Vérifications
    assert response.status_code == 200
    data = response.json()

    # Vérifier que la réponse provient bien du mock
    data = response.json()
    assert data["status"] == "operational"  # Le mock se déclare comme "available"
    assert data["service_status"]["service_type"] == "MockAnalysisService"
    assert data["service_status"]["gpt4o_mini_enabled"] is False
