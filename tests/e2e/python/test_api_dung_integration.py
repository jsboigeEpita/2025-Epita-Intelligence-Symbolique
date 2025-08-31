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

    # --- Vérifications Robustes de la Réponse ---

    # 1. Vérification des statistiques de base au premier niveau
    assert "argument_count" in response_data, "La clé 'argument_count' est manquante."
    assert response_data["argument_count"] == 3, f"Attendu 3 arguments, mais obtenu {response_data['argument_count']}"
    
    assert "attack_count" in response_data, "La clé 'attack_count' est manquante."
    assert response_data["attack_count"] == 2, f"Attendu 2 attaques, mais obtenu {response_data['attack_count']}"

    # 2. Vérification de la présence et du contenu des extensions
    assert "extensions" in response_data, "La clé 'extensions' est manquante."
    extensions_list = response_data.get('extensions', [])
    assert len(extensions_list) > 0, "La liste des extensions ne devrait pas être vide."
    
    # Recherche de l'extension 'preferred' spécifique
    preferred_extension = next((ext for ext in extensions_list if ext.get('type') == 'preferred'), None)
    assert preferred_extension is not None, "Aucune extension de type 'preferred' n'a été trouvée."
    
    # 3. Vérification du contenu de l'extension trouvée
    expected_extension_content = {"a", "c"}
    actual_extension_content = set(preferred_extension.get("arguments", []))
    assert actual_extension_content == expected_extension_content, f"Contenu de l'extension incorrect. Attendu: {expected_extension_content}, Obtenu: {actual_extension_content}"
