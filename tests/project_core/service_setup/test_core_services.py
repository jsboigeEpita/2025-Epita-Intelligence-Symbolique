# -*- coding: utf-8 -*-
"""Tests pour l'initialisation des services centraux."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Supposer que les services et la config peuvent être importés pour le test.
# En réalité, il faudrait peut-être mocker ces dépendances si elles sont complexes.
from argumentation_analysis.services.cache_service import CacheService
from argumentation_analysis.services.crypto_service import CryptoService
from argumentation_analysis.services.definition_service import DefinitionService
from argumentation_analysis.services.extract_service import ExtractService
from argumentation_analysis.services.fetch_service import FetchService
# Pour DEFAULT_ENCRYPTION_KEY etc., si on ne les mocke pas, le module config sera importé.
# Il est préférable de les mocker pour éviter des dépendances externes aux tests.

# Le module à tester
from project_core.service_setup.core_services import initialize_core_services

@pytest.fixture
def mock_ui_config():
    """Mock les constantes de argumentation_analysis.ui.config."""
    with patch('project_core.service_setup.core_services.DEFAULT_ENCRYPTION_KEY', "test_default_key"), \
         patch('project_core.service_setup.core_services.DEFAULT_CONFIG_FILE_PATH', "config/default_config.enc"), \
         patch('project_core.service_setup.core_services.DEFAULT_CONFIG_FILE_JSON_PATH', "config/default_config.json"):
        yield

@pytest.fixture
def mock_services_constructors():
    """Mock les constructeurs des services pour contrôler leur instanciation."""
    with patch('project_core.service_setup.core_services.CryptoService') as MockCrypto, \
         patch('project_core.service_setup.core_services.CacheService') as MockCache, \
         patch('project_core.service_setup.core_services.ExtractService') as MockExtract, \
         patch('project_core.service_setup.core_services.FetchService') as MockFetch, \
         patch('project_core.service_setup.core_services.DefinitionService') as MockDefinition:
        
        # Configurer les mocks pour retourner une instance de MagicMock (ou d'eux-mêmes)
        MockCrypto.return_value = MagicMock(spec=CryptoService)
        MockCache.return_value = MagicMock(spec=CacheService)
        MockExtract.return_value = MagicMock(spec=ExtractService)
        MockFetch.return_value = MagicMock(spec=FetchService)
        MockDefinition.return_value = MagicMock(spec=DefinitionService)
        
        yield {
            "CryptoService": MockCrypto,
            "CacheService": MockCache,
            "ExtractService": MockExtract,
            "FetchService": MockFetch,
            "DefinitionService": MockDefinition
        }

@pytest.fixture
def temp_project_root(tmp_path: Path) -> Path:
    """Crée une structure de répertoires temporaire simulant la racine du projet."""
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "argumentation_analysis" / "text_cache").mkdir(parents=True, exist_ok=True)
    (tmp_path / "argumentation_analysis" / "temp_downloads").mkdir(parents=True, exist_ok=True)
    
    # Créer des fichiers de configuration vides pour les tests où leur existence est vérifiée
    (tmp_path / "config/default_config.enc").touch()
    (tmp_path / "config/default_config.json").touch()
    return tmp_path


def test_initialize_core_services_defaults(mock_ui_config, mock_services_constructors, temp_project_root):
    """Teste l'initialisation avec les valeurs par défaut."""
    services = initialize_core_services(project_root_dir=temp_project_root)

    assert "crypto_service" in services
    assert "cache_service" in services
    assert "extract_service" in services
    assert "fetch_service" in services
    assert "definition_service" in services

    mock_services_constructors["CryptoService"].assert_called_once_with("test_default_key")
    
    expected_cache_dir = temp_project_root / "argumentation_analysis" / "text_cache"
    mock_services_constructors["CacheService"].assert_called_once_with(cache_dir=expected_cache_dir)
    
    mock_services_constructors["ExtractService"].assert_called_once()
    
    expected_temp_download_dir = temp_project_root / "argumentation_analysis" / "temp_downloads"
    mock_services_constructors["FetchService"].assert_called_once_with(
        cache_service=mock_services_constructors["CacheService"].return_value,
        temp_download_dir=expected_temp_download_dir
    )
    
    expected_config_file = temp_project_root / "config/default_config.enc"
    expected_fallback_file = temp_project_root / "config/default_config.json"
    mock_services_constructors["DefinitionService"].assert_called_once_with(
        crypto_service=mock_services_constructors["CryptoService"].return_value,
        config_file=expected_config_file,
        fallback_file=expected_fallback_file
    )

def test_initialize_core_services_with_overrides(mock_services_constructors, temp_project_root):
    """Teste l'initialisation avec des valeurs surchargées."""
    custom_key = "custom_encryption_key"
    custom_config_path_str = "custom_config/my_config.enc"
    custom_config_file = temp_project_root / custom_config_path_str
    (temp_project_root / "custom_config").mkdir(exist_ok=True)
    custom_config_file.touch() # S'assurer que le fichier existe
    
    # S'assurer que le fichier JSON de fallback attendu par le mock existe aussi
    expected_fallback_json_path = temp_project_root / "config" / "default.json"
    expected_fallback_json_path.parent.mkdir(parents=True, exist_ok=True)
    expected_fallback_json_path.touch()

    # Mock des constantes par défaut car elles sont utilisées si les overrides sont None
    with patch('project_core.service_setup.core_services.DEFAULT_ENCRYPTION_KEY', "default_key"), \
         patch('project_core.service_setup.core_services.DEFAULT_CONFIG_FILE_PATH', "config/default.enc"), \
         patch('project_core.service_setup.core_services.DEFAULT_CONFIG_FILE_JSON_PATH', "config/default.json"): # Ce mock pointe vers config/default.json
        
        services = initialize_core_services(
            encryption_key=custom_key,
            config_file_path=custom_config_file, # Passer un Path absolu ou relatif à temp_project_root
            project_root_dir=temp_project_root
        )

    mock_services_constructors["CryptoService"].assert_called_once_with(custom_key)
    mock_services_constructors["DefinitionService"].assert_called_once_with(
        crypto_service=mock_services_constructors["CryptoService"].return_value,
        config_file=custom_config_file,
        fallback_file=temp_project_root / "config/default.json" # Fallback utilise le défaut mocké
    )

def test_initialize_core_services_crypto_failure(mock_ui_config, mock_services_constructors, temp_project_root):
    """Teste la gestion d'une erreur lors de l'initialisation de CryptoService."""
    mock_services_constructors["CryptoService"].side_effect = Exception("Crypto init error")
    
    with pytest.raises(Exception, match="Crypto init error"):
        initialize_core_services(project_root_dir=temp_project_root)

def test_initialize_core_services_cache_failure(mock_ui_config, mock_services_constructors, temp_project_root):
    """Teste la gestion d'une erreur lors de l'initialisation de CacheService."""
    mock_services_constructors["CacheService"].side_effect = Exception("Cache init error")
    
    with pytest.raises(Exception, match="Cache init error"):
        initialize_core_services(project_root_dir=temp_project_root)

def test_config_file_paths_resolution(mock_ui_config, mock_services_constructors, temp_project_root):
    """Teste comment les chemins des fichiers de configuration sont résolus."""
    # Cas 1: Pas d'override, utilise les défauts relatifs à project_root_dir
    initialize_core_services(project_root_dir=temp_project_root)
    kwargs_def_service = mock_services_constructors["DefinitionService"].call_args.kwargs
    assert kwargs_def_service['config_file'] == temp_project_root / "config/default_config.enc"
    assert kwargs_def_service['fallback_file'] == temp_project_root / "config/default_config.json"
    mock_services_constructors["DefinitionService"].reset_mock()

    # Cas 2: Override avec chemin relatif
    relative_config = Path("specific_config.enc")
    (temp_project_root / relative_config).touch()
    initialize_core_services(project_root_dir=temp_project_root, config_file_path=relative_config)
    kwargs_def_service = mock_services_constructors["DefinitionService"].call_args.kwargs
    assert kwargs_def_service['config_file'] == temp_project_root / relative_config
    mock_services_constructors["DefinitionService"].reset_mock()

    # Cas 3: Override avec chemin absolu
    absolute_config_dir = temp_project_root / "absolute_configs"
    absolute_config_dir.mkdir()
    absolute_config_file = absolute_config_dir / "abs_config.enc"
    absolute_config_file.touch()
    initialize_core_services(project_root_dir=temp_project_root, config_file_path=absolute_config_file)
    kwargs_def_service = mock_services_constructors["DefinitionService"].call_args.kwargs
    assert kwargs_def_service['config_file'] == absolute_config_file
    mock_services_constructors["DefinitionService"].reset_mock()

    # Cas 4: project_root_dir est None, les chemins relatifs sont par rapport à CWD (simulé par tmp_path ici)
    # Pour ce test, on simule CWD en ne passant pas project_root_dir et en s'attendant à ce que
    # les chemins par défaut soient relatifs à tmp_path (qui est notre CWD de test ici)
    # Cela nécessite que les DEFAULT_CONFIG_FILE_PATH soient des chaînes simples sans './'
    with patch('project_core.service_setup.core_services.DEFAULT_CONFIG_FILE_PATH', "config_cwd.enc"), \
         patch('project_core.service_setup.core_services.DEFAULT_CONFIG_FILE_JSON_PATH', "config_cwd.json"):
        (temp_project_root / "config_cwd.enc").touch() # Créer le fichier attendu dans le "CWD"
        (temp_project_root / "config_cwd.json").touch()
        
        # Changer le CWD pour le test est complexe et peut avoir des effets de bord.
        # La fonction utilise Path.cwd() si project_root_dir est None.
        # On va mocker Path.cwd() pour ce test spécifique.
        with patch('project_core.service_setup.core_services.Path.cwd', return_value=temp_project_root):
            initialize_core_services(project_root_dir=None)
            kwargs_def_service = mock_services_constructors["DefinitionService"].call_args.kwargs
            assert kwargs_def_service['config_file'] == temp_project_root / "config_cwd.enc"
            assert kwargs_def_service['fallback_file'] == temp_project_root / "config_cwd.json"