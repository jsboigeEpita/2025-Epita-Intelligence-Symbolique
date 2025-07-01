# conftest.py pour les tests unitaires de argumentation_analysis

import pytest
from unittest.mock import patch
@pytest.fixture(autouse=True)
def force_mock_llm():
    """
    Fixture 'autouse' qui force l'activation du mock LLM pour tous les tests
    dans ce répertoire et ses sous-répertoires.

    Ceci assure que les tests unitaires n'effectuent jamais d'appels réels
    au LLM, conformément aux bonnes pratiques d'isolation.
    """
    with patch('argumentation_analysis.config.settings.settings.use_mock_llm', True):
        yield