import pytest
from playwright.sync_api import Playwright, expect
import os

# Marqueur pour facilement cibler ces tests
# Les fixtures sont injectées par l'orchestrateur de test.
# donc le démarrage du serveur est géré automatiquement.
pytestmark = [
    pytest.mark.api_integration,
    pytest.mark.e2e_test
]

@pytest.mark.playwright
def test_dung_framework_analysis_api(playwright: Playwright, e2e_servers, backend_url: str):
    """
    Teste directement le nouvel endpoint /api/v1/framework/analyze.
    Ceci valide l'intégration du service Dung sans passer par l'UI.
    """
    api_request_context = playwright.request.new_context(
        base_url=backend_url
    )
    
    # Données conformes au modèle FrameworkAnalysisRequest
    test_data = {
        "arguments": ["a", "b", "c"],
        "attacks": [["a", "b"], ["b", "c"]]
    }

    # Appel à la nouvelle API
    response = api_request_context.post(
        "/api/v1/framework/analyze",
        data=test_data
    )

    # Vérifications de base
    expect(response).to_be_ok()
    response_data = response.json()

    # La réponse est une SuccessResponse, les données sont dans le champ 'data'
    assert "data" in response_data, "La clé 'data' est manquante dans la réponse"
    data = response_data["data"]

    # Vérification des statistiques
    assert "statistics" in data, "La clé 'statistics' est manquante"
    stats = data["statistics"]
    assert stats.get("arguments_count") == 3
    assert stats.get("attacks_count") == 2

    # Vérification des extensions (basé sur la logique factice actuelle)
    assert "extensions" in data, "La clé 'extensions' est manquante"
    extensions = data["extensions"]
    assert isinstance(extensions, list), "Les extensions devraient être une liste"
    assert len(extensions) > 0, "La liste des extensions ne devrait pas être vide"
    
    # La logique factice renvoie les arguments non attaqués.
    # Pour a->b et b->c, les arguments attaqués sont 'b' et 'c'.
    # Seul 'a' n'est pas attaqué.
    found_extension = set(extensions[0])
    expected_extension = {"a"}
    assert found_extension == expected_extension, f"L'extension est incorrecte. Attendu: {expected_extension}, Obtenu: {found_extension}"