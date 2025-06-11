#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration pytest locale pour les tests d'orchestration.
Évite les dépendances JPype du conftest.py global.
"""

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

# INTÉGRATION AUTO_ENV - CRITIQUE POUR ÉVITER LES ENVIRONNEMENTS GLOBAUX
# Assurer l'activation automatique de l'environnement projet avant tous les tests
try:
    # Import direct par chemin absolu pour éviter les problèmes d'import
    import sys
    scripts_core_path = project_root / "scripts" / "core"
    if str(scripts_core_path) not in sys.path:
        sys.path.insert(0, str(scripts_core_path))
    
    from auto_env import ensure_env
    success = ensure_env(silent=False)
    
    if success:
        print("[OK AUTO_ENV] Environnement projet active avec succes")
        print(f"[INFO] Python: {sys.executable}")
        print(f"[INFO] Environnement conda: {os.environ.get('CONDA_DEFAULT_ENV', 'Non defini')}")
    else:
        print("[WARN AUTO_ENV] Activation en mode degrade - continuez dans l'environnement actuel")
        
except ImportError as e:
    print(f"[ERROR AUTO_ENV] Module auto_env non disponible: {e}")
    print("[INFO] Tests continueront dans l'environnement actuel")
except Exception as e:
    print(f"[ERROR AUTO_ENV] Erreur lors de l'activation: {e}")
    print("[INFO] Tests continueront dans l'environnement actuel")

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
def mock_llm_service():
    """Service LLM mocké standard pour tous les tests."""
    from unittest.mock import MagicMock, AsyncMock
    
    mock_service = MagicMock()
    mock_service.service_id = "test_llm_service"
    mock_service.generate_text = AsyncMock(return_value="Test response")
    mock_service.analyze_text = AsyncMock(return_value={"status": "success"})
    
    return mock_service

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