import pytest
from playwright.async_api import Playwright, expect
import os

# Marqueur pour facilement cibler ces tests
# Les fixtures sont injectées par l'orchestrateur de test.
# donc le démarrage du serveur est géré automatiquement.
pytestmark = [
    pytest.mark.api_integration,
    pytest.mark.e2e_test
]

@pytest.mark.asyncio
async def test_dung_framework_analysis_api():
    """
    NOTE: Ce test est temporairement désactivé.
    Teste directement l'endpoint de l'API pour l'analyse de A.F. Dung.
    Ceci valide l'intégration du service Dung sans passer par l'UI.
    Le serveur backend est démarré par l'orchestrateur de test.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        # Création du contexte API. L'URL est récupérée depuis les variables d'environnement
        # ou une valeur par défaut, ce qui correspond à la configuration de l'orchestrateur de test.
        api_request_context = await p.request.new_context(
            base_url=os.environ.get("BACKEND_URL", "http://127.0.0.1:5003")
        )
    
        # Données d'exemple pour un framework d'argumentation simple
        test_data = {
            "arguments": ["a", "b", "c"],
            "attacks": [
                ["a", "b"],
                ["b", "c"]
            ],
            "options": {
                "semantics": "preferred",
                "compute_extensions": True,
                "include_visualization": False
            }
        }

        # Appel direct de l'API
        response = await api_request_context.post(
            "/api/v1/framework/analyze",
            data=test_data
        )

        # Vérifications de base
        await expect(response).to_be_ok()
        response_data = await response.json()

        # Vérification de la structure et du contenu de la réponse
        assert "graph_properties" in response_data, "La clé 'graph_properties' est manquante"
        props = response_data["graph_properties"]
        assert props.get("num_arguments") == 3, f"Attendu 3 arguments, obtenu {props.get('num_arguments')}"
        assert props.get("num_attacks") == 2, f"Attendu 2 attaques, obtenu {props.get('num_attacks')}"

        assert "analysis" in response_data, "La clé 'analysis' est manquante"
        analysis = response_data["analysis"]
        assert "extensions" in analysis, "La clé 'extensions' est manquante dans 'analysis'"
        
        extensions = analysis["extensions"]
        assert "preferred" in extensions, "La sémantique 'preferred' est manquante dans les extensions"
        
        # Les extensions préférées sont une liste de listes d'arguments
        preferred_extensions = extensions["preferred"]
        assert isinstance(preferred_extensions, list), "Les extensions préférées devraient être une liste"
        assert len(preferred_extensions) > 0, "Aucune extension préférée n'a été trouvée"

        # Pour le graphe a->b->c, l'extension préférée est [{a, c}]
        # Nous vérifions si notre extension attendue est dans la liste des extensions trouvées.
        found_extensions_sets = [set(ext) for ext in preferred_extensions]
        expected_extension = {"a", "c"}
        assert expected_extension in found_extensions_sets, f"L'extension préférée est incorrecte. Attendu: {expected_extension}, Obtenu: {found_extensions_sets}"