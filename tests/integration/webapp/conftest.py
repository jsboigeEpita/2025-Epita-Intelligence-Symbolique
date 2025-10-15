import pytest
from pathlib import Path


@pytest.fixture
def webapp_config():
    """
    Fournit une configuration de webapp mockée pour les tests.
    Basé sur la structure de _get_default_config dans UnifiedWebOrchestrator.
    """
    return {
        "webapp": {"name": "Test Web App", "version": "0.1.0", "environment": "test"},
        "backend": {
            "enabled": True,
            "module": "argumentation_analysis.services.web_api.app:app",
            "start_port": 8000,
            "fallback_ports": [8001, 8002],
            "timeout_seconds": 180,
            "health_endpoint": "/api/health",
        },
        "frontend": {
            "enabled": False,
            "path": "fake/frontend/path",
            "port": 3000,
            "start_command": "npm start",
            "timeout_seconds": 10,
        },
        "playwright": {"enabled": False},
        "logging": {"level": "DEBUG", "file": "logs/test_webapp.log"},
        "cleanup": {"auto_cleanup": False},
    }


@pytest.fixture
def test_config_path(tmp_path: Path) -> Path:
    """Crée un chemin vers un fichier de configuration temporaire."""
    return tmp_path / "test_config.yml"
