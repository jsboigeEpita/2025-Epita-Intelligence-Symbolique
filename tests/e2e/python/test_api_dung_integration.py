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
    Le serveur backend est démarré par l'orchestrateur de test.
    """
    api_request_context = playwright.request.new_context(
        base_url=backend_url
    )
    
    test_data = {
        "arguments": [
            {"id": "a", "content": "Argument A", "attacks": ["b"]},
            {"id": "b", "content": "Argument B", "attacks": ["c"]},
            {"id": "c", "content": "Argument C", "attacks": []}
        ],
        "options": {
            "semantics": "preferred",
            "compute_extensions": True,
            "include_visualization": False
        }
    }

    response = api_request_context.post(
        "/api/v1/framework/analyze",
        data=test_data
    )

    expect(response).to_be_ok()
    response_data = response.json()
    
    # DEBUG: Afficher la réponse complète de l'API
    print(f"API Response: {json.dumps(response_data, indent=2)}")

    # Vérification de la nouvelle structure de réponse 
    assert response_data.get("argument_count") == 3, f"Attendu 3 arguments, mais obtenu {response_data.get('argument_count')}"
    assert response_data.get("attack_count") == 2, f"Attendu 2 attaques, mais obtenu {response_data.get('attack_count')}"

    assert "extensions" in response_data, "La clé 'extensions' est manquante."
    extensions = response_data['extensions']
    # La structure des extensions a aussi changé
    assert len(extensions) > 0, "Aucune extension n'a été retournée"
    preferred_ext_obj = extensions[0]
    assert preferred_ext_obj['type'] == 'preferred'
    
    preferred_ext = preferred_ext_obj["arguments"]
    assert isinstance(preferred_ext, list), "Les extensions 'preferred' devraient être une liste."
    
    expected_extension = {'a', 'c'}
    assert set(preferred_ext) == expected_extension, f"L'extension préférée {expected_extension} n'a pas été trouvée dans {preferred_ext}"