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
def test_dung_framework_analysis_api(playwright: Playwright):
    """
    NOTE: Ce test est temporairement désactivé.
    Teste directement l'endpoint de l'API pour l'analyse de A.F. Dung.
    Ceci valide l'intégration du service Dung sans passer par l'UI.
    Le serveur backend est démarré par l'orchestrateur de test.
    """
    # Création du contexte API. L'URL est récupérée depuis les variables d'environnement
    # ou une valeur par défaut, ce qui correspond à la configuration de l'orchestrateur de test.
    api_request_context = playwright.request.new_context(
        base_url=os.environ.get("BACKEND_URL", "http://127.0.0.1:5003")
    )
    
    # Données d'exemple pour un framework d'argumentation simple
    test_data = {
        "arguments": [
            {"id": "a", "content": "Argument a", "attacks": ["b"]},
            {"id": "b", "content": "Argument b", "attacks": ["c"]},
            {"id": "c", "content": "Argument c", "attacks": []}
        ],
        "options": {
            "semantics": "preferred",
            "compute_extensions": True,
            "include_visualization": False
        }
    }

    # Appel direct de l'API
    response = api_request_context.post(
        "/api/framework",
        data=test_data
    )

    # Vérifications de base
    expect(response).to_be_ok()
    response_data = response.json()

    # Vérification de la structure et du contenu de la réponse
    assert "argument_count" in response_data, "La clé 'argument_count' est manquante dans la réponse"
    assert response_data["argument_count"] == 3

    assert "attack_count" in response_data, "La clé 'attack_count' est manquante dans la réponse"
    assert response_data["attack_count"] == 2, f"Expected 2 attacks, but got {response_data.get('attack_count')}"

    if "extensions" in response_data:
        extensions_list = response_data["extensions"]
        assert isinstance(extensions_list, list), "Les extensions devraient être une liste"

        # Trouver l'extension préférée
        preferred_extensions = [ext for ext in extensions_list if ext.get('type') == 'preferred']
        
        assert len(preferred_extensions) > 0, "Aucune extension de type 'preferred' n'a été trouvée"
        
        # Pour le graphe a->b->c, l'extension préférée est {a, c}
        # Prenons la première extension préférée trouvée pour la validation
        preferred_ext_data = preferred_extensions[0]
        
        assert "arguments" in preferred_ext_data, "La clé 'arguments' est manquante dans l'extension"
        
        found_extension = set(preferred_ext_data["arguments"])
        expected_extension = {"a", "c"}
        assert found_extension == expected_extension, f"L'extension préférée est incorrecte. Attendu: {expected_extension}, Obtenu: {found_extension}"