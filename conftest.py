"""
Configuration globale pytest pour le projet.

Ce fichier configure les fixtures et le comportement automatique des markers pytest
pour la gestion des clés API et des secrets CI.
"""

import os
import pytest


def pytest_configure(config):
    """
    Enregistre les markers personnalisés pour pytest.

    Note: Les markers sont aussi définis dans pytest.ini pour la documentation,
    mais cette fonction les enregistre programmatiquement pour s'assurer qu'ils
    sont disponibles même si pytest.ini n'est pas lu correctement.
    """
    # Markers pour API keys (ajoutés dans Phase 1 - D-CI-05-IMPL-P1)
    config.addinivalue_line(
        "markers",
        "requires_api: marks tests as requiring API keys (skipped if not available)",
    )
    config.addinivalue_line(
        "markers", "requires_openai: marks tests requiring OPENAI_API_KEY"
    )
    config.addinivalue_line(
        "markers", "requires_github: marks tests requiring GITHUB_TOKEN"
    )
    config.addinivalue_line(
        "markers", "requires_openrouter: marks tests requiring OPENROUTER_API_KEY"
    )


@pytest.fixture(autouse=True)
def skip_if_no_api_keys(request):
    """
    Fixture automatique qui skip les tests nécessitant des API keys si elles ne sont pas disponibles.

    Cette fixture s'exécute automatiquement avant chaque test et vérifie la présence
    des markers suivants :

    - @pytest.mark.requires_api : Skip si AUCUNE clé API n'est disponible
    - @pytest.mark.requires_openai : Skip si OPENAI_API_KEY n'est pas disponible
    - @pytest.mark.requires_github : Skip si GITHUB_TOKEN n'est pas disponible
    - @pytest.mark.requires_openrouter : Skip si OPENROUTER_API_KEY n'est pas disponible

    Args:
        request: Objet request de pytest contenant les informations du test

    Raises:
        pytest.skip: Si les clés API requises ne sont pas disponibles

    Examples:
        @pytest.mark.requires_openai
        def test_openai_integration():
            # Ce test sera skippé si OPENAI_API_KEY n'est pas défini
            pass

        @pytest.mark.requires_api
        def test_any_api():
            # Ce test sera skippé si AUCUNE clé API n'est définie
            pass
    """
    # Vérifier le marker requires_api (au moins une clé API doit être disponible)
    marker = request.node.get_closest_marker("requires_api")
    if marker:
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        has_github = bool(os.getenv("GITHUB_TOKEN"))
        has_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))

        if not (has_openai or has_github or has_openrouter):
            pytest.skip(
                "Test requires at least one API key (OPENAI_API_KEY, GITHUB_TOKEN, or OPENROUTER_API_KEY) "
                "but none are configured. Configure API keys in .env file for local testing."
            )

    # Vérifier le marker requires_openai
    marker_openai = request.node.get_closest_marker("requires_openai")
    if marker_openai:
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip(
                "Test requires OPENAI_API_KEY but it is not configured. "
                "Set OPENAI_API_KEY in .env file for local testing."
            )

    # Vérifier le marker requires_github
    marker_github = request.node.get_closest_marker("requires_github")
    if marker_github:
        if not os.getenv("GITHUB_TOKEN"):
            pytest.skip(
                "Test requires GITHUB_TOKEN but it is not configured. "
                "Set GITHUB_TOKEN in .env file for local testing."
            )

    # Vérifier le marker requires_openrouter
    marker_openrouter = request.node.get_closest_marker("requires_openrouter")
    if marker_openrouter:
        if not os.getenv("OPENROUTER_API_KEY"):
            pytest.skip(
                "Test requires OPENROUTER_API_KEY but it is not configured. "
                "Set OPENROUTER_API_KEY in .env file for local testing."
            )


# Informations de configuration disponibles pour tous les tests
@pytest.fixture(scope="session")
def api_keys_available():
    """
    Fixture de session qui retourne un dict indiquant quelles clés API sont disponibles.

    Utile pour les tests qui veulent adapter leur comportement selon les clés disponibles
    sans être complètement skippés.

    Returns:
        dict: Dictionnaire avec les clés 'openai', 'github', 'openrouter' (bool)

    Example:
        def test_conditional_behavior(api_keys_available):
            if api_keys_available['openai']:
                # Test avec vraie API
                result = call_openai_api()
            else:
                # Test avec mock
                result = mock_openai_api()
    """
    return {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "github": bool(os.getenv("GITHUB_TOKEN")),
        "openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
    }
