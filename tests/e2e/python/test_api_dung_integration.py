import pytest
from playwright.sync_api import Playwright, expect
import os

# Marqueur pour facilement cibler ces tests
pytestmark = [pytest.mark.api_integration, pytest.mark.e2e_test]

@pytest.mark.playwright
def test_dung_framework_analysis_api(playwright: Playwright):
    """
    Teste directement l'endpoint de l'API pour l'analyse de A.F. Dung.
    Ceci valide l'intégration du service Dung sans passer par l'UI.
    """
    # Création manuelle du contexte API
    api_request_context = playwright.request.new_context(
        base_url=os.environ.get("BACKEND_URL", "http://localhost:5003")
    )
    
    # Données d'exemple pour un framework d'argumentation simple
    test_data = {
        "arguments": ["a", "b", "c"],
        "attacks": [["a", "b"], ["b", "c"]],
        "options": {
            "semantics": "preferred",
            "compute_extensions": True,
            "include_visualization": False
        }
    }

    # Appel direct de l'API
    response = api_request_context.post(
        "/api/v1/framework/analyze",
        data=test_data
    )

    # Vérifications de base
    expect(response).to_be_ok()
    response_data = response.json()

    # Vérification de la structure de la réponse
    assert "analysis" in response_data, "La clé 'analysis' est manquante dans la réponse"
    analysis = response_data["analysis"]

    assert "extensions" in analysis, "La clé 'extensions' est manquante dans l'objet d'analyse"
    assert "graph_properties" in analysis, "La clé 'graph_properties' est manquante dans l'objet d'analyse"

    # Vérification du contenu (peut être affiné)
    # Pour sémantique "preferred" et le graphe a->b->c, l'extension préférée est {a, c}
    extensions = analysis["extensions"]
    assert "preferred" in extensions, "La sémantique 'preferred' est manquante dans les extensions"
    
    preferred_extensions = extensions["preferred"]
    assert len(preferred_extensions) > 0, "Aucune extension préférée n'a été retournée"

    # Normalisons les extensions pour une comparaison robuste
    normalized_extensions = [sorted(ext) for ext in preferred_extensions]
    assert sorted(['a', 'c']) in normalized_extensions, f"L'extension attendue {{'a', 'c'}} n'est pas dans les résultats: {preferred_extensions}"

    # La vérification de la présence de "graph_properties" est déjà faite