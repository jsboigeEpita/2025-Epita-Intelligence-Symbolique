# tests/integration/jpype_tweety/conftest.py
"""
Configuration Pytest spécifique pour les tests d'intégration jpype_tweety.

Ce fichier assure que l'initialiseur de classpath pour Tweety est bien
exécuté avant tous les tests de ce répertoire, résolvant les ClassNotFoundException.
"""

import pytest
import logging

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module", autouse=True)
def ensure_jpype_tweety_is_ready(tweety_classpath_initializer):
    """
    Fixture auto-utilisée à portée de module pour garantir que le classpath Tweety est prêt.

    Cette fixture dépend de `tweety_classpath_initializer` (définie dans le
    conftest.py racine et disponible via `pytest_plugins`). En l'utilisant ici,
    nous forçons son exécution avant tout test dans le répertoire jpype_tweety,
    ce qui garantit que les classes Java de Tweety sont disponibles.

    Args:
        tweety_classpath_initializer: Fixture du conftest racine qui prépare le classpath.
                                      Elle est injectée automatiquement par pytest.
    """
    logger.info("Fixture 'ensure_jpype_tweety_is_ready' activée. Le classpath Tweety est prêt pour les tests de ce module.")
    # Il n'y a rien à faire ici, la simple dépendance suffit à forcer l'exécution
    # de l'initialiseur.
    yield
