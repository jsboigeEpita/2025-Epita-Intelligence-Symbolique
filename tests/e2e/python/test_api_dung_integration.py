import pytest
from playwright.sync_api import Playwright, expect
import os
import json

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
    Teste directement l'endpoint de l'API pour l'analyse de A.F. Dung.
    Ceci valide l'intégration du service Dung sans passer par l'UI.
    """
    api_request_context = playwright.request.new_context(
        base_url=backend_url
    )
    
    test_data = {
        "arguments": ["a", "b", "c"],
        "attacks": [("a", "b"), ("b", "c")],
        "semantics": "preferred"
    }

    response = api_request_context.post(
        "/api/v1/framework/analyze",
        data=json.dumps(test_data),
        headers={"Content-Type": "application/json"}
    )

    expect(response).to_be_ok()
    response_data = response.json()
    
    # DEBUG: Afficher la réponse complète de l'API
    print(f"API Response: {json.dumps(response_data, indent=2)}")

    # Vérification de la structure de réponse correcte
    assert "statistics" in response_data, "La clé 'statistics' est manquante dans la réponse."
    stats = response_data["statistics"]
    assert stats.get("arguments_count") == 3, f"Attendu 3 arguments, mais obtenu {stats.get('arguments_count')}"
    assert stats.get("attacks_count") == 2, f"Attendu 2 attaques, mais obtenu {stats.get('attacks_count')}"

    assert "extensions" in response_data, "La clé 'extensions' est manquante."
    extensions = response_data.get('extensions', {})
    assert "preferred" in extensions, "La clé 'preferred' est manquante dans les extensions."
    
    preferred_extensions = extensions['preferred']
    assert isinstance(preferred_extensions, list), "Les extensions préférées devraient être une liste."
    assert len(preferred_extensions) > 0, "Aucune extension préférée n'a été retournée."
    
    # Dans ce cas, avec le framework a->b, b->c, l'extension préférée est {a, c}
    # La réponse doit être une liste de listes d'arguments.
    expected_extension_set = [["a", "c"]]
    assert preferred_extensions == expected_extension_set, f"Attendu {expected_extension_set}, mais obtenu {preferred_extensions}"
