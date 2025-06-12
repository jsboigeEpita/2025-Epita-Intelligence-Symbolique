#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration pytest locale pour les tests d'orchestration.
Évite les dépendances JPype du conftest.py global.
"""

import project_core.core_from_scripts.auto_env
import pytest
import sys
import os
import logging
from pathlib import Path

# Configuration du logging pour les tests
logging.basicConfig(level=logging.WARNING)

# Ajouter le répertoire racine au PYTHONPATH
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Configuration de l'environnement de test."""
    # Désactiver les logs verbeux pendant les tests
    logging.getLogger('argumentation_analysis').setLevel(logging.ERROR)
    
    # Mock des composants JPype si nécessaires
    if 'jpype' not in sys.modules:
        # Mock basique de jpype pour éviter les erreurs d'import
        sys.modules['jpype'] = type(sys)('jpype')
        sys.modules['jpype'].isJVMStarted = lambda: False
        sys.modules['jpype'].shutdownJVM = lambda: None
        sys.modules['jpype'].startJVM = lambda *args, **kwargs: None
    
    yield
    
    # Nettoyage après les tests
    pass

@pytest.fixture
def llm_service():
    """Crée une instance réelle du service LLM pour les tests d'intégration."""
    from argumentation_analysis.core.llm_service import create_llm_service
    
    # Assurez-vous que votre fichier .env est correctement configuré
    # avec OPENAI_API_KEY et OPENAI_CHAT_MODEL_ID
    try:
        service = create_llm_service(
            service_id="real_test_llm_service",
            force_mock=False
        )
        return service
    except Exception as e:
        pytest.skip(f"Impossible de créer le service LLM réel : {e}")

@pytest.fixture
def sample_text():
    """Texte d'exemple standard pour les tests."""
    return "Ceci est un argument de test pour l'analyse d'orchestration."

# Markers pour les tests
def pytest_configure(config):
    """Configuration des markers pytest."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")