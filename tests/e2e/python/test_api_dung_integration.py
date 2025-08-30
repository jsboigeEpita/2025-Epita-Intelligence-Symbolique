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
        "arguments": [
            {"id": "a", "content": "Argument A"},
            {"id": "b", "content": "Argument B"},
            {"id": "c", "content": "Argument C"}
        ],
        "attacks": [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"}
        ],
        "options": {
            "semantics": "preferred"
        }
    }

    response = api_request_context.post(
        "/api/framework",
        data=json.dumps(test_data),
        headers={"Content-Type": "application/json"}
    )

    expect(response).to_be_ok()
    response_data = response.json()
    
    # DEBUG: Afficher la réponse complète de l'API
    print(f"API Response: {json.dumps(response_data, indent=2)}")

    # Vérification de la structure de réponse correcte
    assert "argument_count" in response_data, "La clé 'argument_count' est manquante dans la réponse."
    assert response_data["argument_count"] == 3, f"Attendu 3 arguments, mais obtenu {response_data['argument_count']}"
    
    assert "extensions" in response_data, "La clé 'extensions' est manquante."
    extensions_list = response_data.get('extensions', [])
    assert len(extensions_list) > 0, "La liste des extensions est vide."
    
    first_extension = extensions_list[0]
    assert first_extension.get('type') == 'preferred', "La sémantique 'preferred' n'a pas été trouvée dans les extensions."
    
    # Vérification du contenu de l'extension
    expected_extension_content = {"a", "c"}
    actual_extension_content = set(first_extension.get("arguments", []))
    assert actual_extension_content == expected_extension_content, f"Attendu l'extension {expected_extension_content}, mais obtenu {actual_extension_content}"
