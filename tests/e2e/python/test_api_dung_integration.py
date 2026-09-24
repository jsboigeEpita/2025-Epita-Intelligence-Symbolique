import pytest
from playwright.sync_api import Playwright, expect
import os
import json

# Marqueur pour facilement cibler ces tests
# Les fixtures sont injectées par l'orchestrateur de test.
# donc le démarrage du serveur est géré automatiquement.
pytestmark = [pytest.mark.api_integration, pytest.mark.e2e]


@pytest.mark.playwright
def test_dung_framework_analysis_api(
    playwright: Playwright, e2e_servers, backend_url: str
):
    """
    Teste directement l'endpoint de l'API pour l'analyse de A.F. Dung.
    Ceci valide l'intégration du service Dung sans passer par l'UI.
    """
    api_request_context = playwright.request.new_context(base_url=backend_url)

    # #2526: the route the framework view calls, with the body api.js
    # analyzeDungFramework sends (argument ids, attack pairs, the semantics).
    # a attacks b, which attacks c.
    test_data = {
        "arguments": ["a", "b", "c"],
        "attacks": [["a", "b"], ["b", "c"]],
        "options": {"semantics": "preferred", "compute_extensions": True},
    }

    response = api_request_context.post(
        "/api/v1/framework/analyze",
        data=json.dumps(test_data),
        headers={"Content-Type": "application/json"},
        timeout=60000,
    )

    expect(response).to_be_ok()
    analysis = response.json()["analysis"]

    properties = analysis["graph_properties"]
    assert properties["num_arguments"] == 3, properties
    assert properties["num_attacks"] == 2, properties

    extensions = analysis["extensions"]
    assert sorted(extensions["grounded"]) == ["a", "c"], extensions
    assert [sorted(ext) for ext in extensions["preferred"]] == [["a", "c"]], extensions
    assert analysis["argument_status"]["b"]["credulously_accepted"] is False
