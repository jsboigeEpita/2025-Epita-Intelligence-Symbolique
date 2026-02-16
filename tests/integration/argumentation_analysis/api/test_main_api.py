from fastapi.testclient import TestClient
import pytest

# On importe l'application FastAPI et les classes nécessaires
from argumentation_analysis.api.main import app, get_orchestration_service
from argumentation_analysis.agents.core.orchestration_service import (
    OrchestrationService,
    BasePlugin,
)

# Création d'un client de test pour l'application
client = TestClient(app)

# --- Début de la configuration du test d'intégration ---


class EchoPlugin(BasePlugin):
    """
    Un plugin de test simple qui retourne les arguments qu'il a reçus.
    """

    @property
    def name(self) -> str:
        return "EchoPlugin"

    def execute(self, **kwargs) -> dict:
        """Retourne simplement les arguments reçus."""
        return {"status": "success", "plugin_name": self.name, "result": kwargs}


@pytest.fixture(autouse=True)
def setup_orchestration_service_for_test():
    """
    Fixture Pytest pour surcharger la dépendance de l'OrchestrationService.
    """
    # Créer une instance de service dédiée au test
    test_service = OrchestrationService()
    test_service.register_plugin(EchoPlugin())

    # Fonction qui retournera notre instance de test
    def get_test_orchestration_service_override():
        return test_service

    # Surcharger la dépendance dans l'application FastAPI
    app.dependency_overrides[get_orchestration_service] = (
        get_test_orchestration_service_override
    )

    yield  # Le test est exécuté ici

    # Nettoyer la surcharge après le test
    app.dependency_overrides.clear()


# --- Fin de la configuration du test d'intégration ---


def test_end_to_end_analysis_execution():
    """
    Test d'intégration de bout en bout.
    """
    test_text = "Ceci est un test de bout en bout."
    response = client.post(
        "/api/v2/analyze", json={"text": test_text, "plugin_name": "EchoPlugin"}
    )

    # Vérification de la réponse HTTP
    assert (
        response.status_code == 200
    ), f"Expected 200 OK, got {response.status_code} with detail: {response.text}"

    # Vérification du contenu de la réponse JSON
    json_response = response.json()
    assert json_response["status"] == "success"
    assert json_response["plugin_name"] == "EchoPlugin"
    assert "result" in json_response
    assert json_response["result"]["text"] == test_text


def test_analyze_endpoint_plugin_not_found():
    """
    Teste que le endpoint /api/v2/analyze retourne bien une erreur 404
    quand le plugin demandé n'existe pas.
    """
    response = client.post(
        "/api/v2/analyze",
        json={"text": "Peu importe le texte", "plugin_name": "PluginInexistant"},
    )
    assert response.status_code == 404
    json_response = response.json()
    detail = json_response["detail"]
    assert (
        "PluginInexistant" in detail
    ), f"Expected plugin not found error mentioning 'PluginInexistant', got: {detail}"
