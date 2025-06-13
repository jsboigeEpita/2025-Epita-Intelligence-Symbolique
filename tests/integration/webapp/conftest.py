import pytest

@pytest.fixture
def webapp_config():
    """Provides a basic webapp configuration dictionary."""
    return {
        "backend": {},
        "frontend": {},
        "playwright": {}
    }

@pytest.fixture
def test_config_path(tmp_path):
    """Provides a temporary path for a config file."""
    return tmp_path / "test_config.yml"