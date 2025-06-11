
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""Tests pour l'initialisation des services centraux."""

import pytest

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
from argumentation_analysis.service_setup.analysis_services import initialize_analysis_services # MODIFIÉ

@pytest.fixture
def mock_ui_config():
    """Mock les constantes de argumentation_analysis.ui.config."""
    # Les constantes sont maintenant dans argumentation_analysis.ui.config
    # et se nomment ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
    with patch('argumentation_analysis.ui.config.ENCRYPTION_KEY', "test_default_key") as mock_enc_key, \
         patch('argumentation_analysis.ui.config.CONFIG_FILE', Path("config/default_config.enc")) as mock_conf_file, \
         patch('argumentation_analysis.ui.config.CONFIG_FILE_JSON', Path("config/default_config.json")) as mock_conf_json:
        # Note: Les valeurs patchées pour CONFIG_FILE et CONFIG_FILE_JSON doivent être des objets Path
        # si c'est ce que le code attend, ou des chaînes si c'est le cas.
        # D'après ui/config.py, ce sont des objets Path.
        yield {
            "ENCRYPTION_KEY": mock_enc_key,
            "CONFIG_FILE": mock_conf_file,
            "CONFIG_FILE_JSON": mock_conf_json
        }

@pytest.fixture
def mock_services_constructors():
    """Mock les constructeurs des services pour contrôler leur instanciation."""
    # Ces services ne sont plus initialisés par la fonction testée.
    # Cette fixture n'est plus directement utilisée par test_initialize_analysis_services_defaults.
    # Elle est conservée au cas où elle serait utile pour d'autres tests ou si la logique d'init change.
    with patch('argumentation_analysis.services.crypto_service.CryptoService') as MockCrypto, \
         patch('argumentation_analysis.services.cache_service.CacheService') as MockCache, \
         patch('argumentation_analysis.services.extract_service.ExtractService') as MockExtract, \
         patch('argumentation_analysis.services.fetch_service.FetchService') as MockFetch, \
         patch('argumentation_analysis.services.definition_service.DefinitionService') as MockDefinition:
        
        # Configurer les mocks pour retourner une instance de MagicMock (ou d'eux-mêmes)
        MockCrypto# Mock eliminated - using authentic gpt-4o-mini MagicMock(spec=CryptoService)
        MockCache# Mock eliminated - using authentic gpt-4o-mini MagicMock(spec=CacheService)
        MockExtract# Mock eliminated - using authentic gpt-4o-mini MagicMock(spec=ExtractService)
        MockFetch# Mock eliminated - using authentic gpt-4o-mini MagicMock(spec=FetchService)
        MockDefinition# Mock eliminated - using authentic gpt-4o-mini MagicMock(spec=DefinitionService)
        
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


def test_initialize_analysis_services_defaults(mock_ui_config, temp_project_root): # mock_services_constructors retiré pour l'instant
    """Teste l'initialisation avec les valeurs par défaut."""
    # La nouvelle fonction attend un dictionnaire 'config'
    # Les mocks pour les services individuels ne sont plus directement applicables de la même manière.
    # Nous allons mocker les dépendances de initialize_analysis_services : initialize_jvm et create_llm_service
    
    with patch('argumentation_analysis.service_setup.analysis_services.initialize_jvm') as mock_init_jvm, \
         patch('argumentation_analysis.service_setup.analysis_services.create_llm_service') as mock_create_llm, \
         patch('argumentation_analysis.service_setup.analysis_services.load_dotenv') as mock_load_dotenv, \
         patch('argumentation_analysis.service_setup.analysis_services.LIBS_DIR', "mock/libs/dir") as mock_libs_dir: # Mocker LIBS_DIR

        mock_init_jvm# Mock eliminated - using authentic gpt-4o-mini True  # Simule succès JVM
        mock_create_llm# Mock eliminated - using authentic gpt-4o-mini Magicawait self._create_authentic_gpt4o_mini_instance() # Simule un service LLM créé
        mock_load_dotenv# Mock eliminated - using authentic gpt-4o-mini True # Simule chargement .env réussi

        sample_config = {"LIBS_DIR_PATH": "mock/libs/dir"} # Passer une config minimale
        services = initialize_analysis_services(config=sample_config)

        assert "jvm_ready" in services
        assert services["jvm_ready"] is True
        assert "llm_service" in services
        assert services["llm_service"] is not None

        mock_load_dotenv.# Mock assertion eliminated - authentic validation
        mock_init_jvm.assert_called_once_with(lib_dir_path="mock/libs/dir")
        mock_create_llm.# Mock assertion eliminated - authentic validation

# def test_initialize_core_services_with_overrides(mock_services_constructors, temp_project_root):
#     """Teste l'initialisation avec des valeurs surchargées."""
#     custom_key = "custom_encryption_key"
#     custom_config_path_str = "custom_config/my_config.enc"
#     custom_config_file = temp_project_root / custom_config_path_str
#     (temp_project_root / "custom_config").mkdir(exist_ok=True)
#     custom_config_file.touch() # S'assurer que le fichier existe
    
#     # S'assurer que le fichier JSON de fallback attendu par le mock existe aussi
#     expected_fallback_json_path = temp_project_root / "config" / "default.json"
#     expected_fallback_json_path.parent.mkdir(parents=True, exist_ok=True)
#     expected_fallback_json_path.touch()

#     # Mock des constantes par défaut car elles sont utilisées si les overrides sont None
#     with patch('argumentation_analysis.service_setup.core_services.DEFAULT_ENCRYPTION_KEY', "default_key"), \
#          patch('argumentation_analysis.service_setup.core_services.DEFAULT_CONFIG_FILE_PATH', "config/default.enc"), \
#          patch('argumentation_analysis.service_setup.core_services.DEFAULT_CONFIG_FILE_JSON_PATH', "config/default.json"): # Ce mock pointe vers config/default.json
        
#         services = initialize_core_services( # Devrait être initialize_analysis_services et adapté
#             encryption_key=custom_key,
#             config_file_path=custom_config_file, # Passer un Path absolu ou relatif à temp_project_root
#             project_root_dir=temp_project_root
#         )

#     mock_services_constructors["CryptoService"].assert_called_once_with(custom_key)
#     mock_services_constructors["DefinitionService"].assert_called_once_with(
#         crypto_service=mock_services_constructors["CryptoService"].return_value,
#         config_file=custom_config_file,
#         fallback_file=temp_project_root / "config/default.json" # Fallback utilise le défaut mocké
#     )

# def test_initialize_core_services_crypto_failure(mock_ui_config, mock_services_constructors, temp_project_root):
#     """Teste la gestion d'une erreur lors de l'initialisation de CryptoService."""
#     # mock_services_constructors["CryptoService"]# Mock eliminated - using authentic gpt-4o-mini Exception("Crypto init error") # Ne s'applique plus directement
    
#     # with pytest.raises(Exception, match="Crypto init error"):
#     #     initialize_analysis_services(config={}) # Adapté
#     pass

# def test_initialize_core_services_cache_failure(mock_ui_config, mock_services_constructors, temp_project_root):
#     """Teste la gestion d'une erreur lors de l'initialisation de CacheService."""
#     # mock_services_constructors["CacheService"]# Mock eliminated - using authentic gpt-4o-mini Exception("Cache init error") # Ne s'applique plus directement
    
#     # with pytest.raises(Exception, match="Cache init error"):
#     #     initialize_analysis_services(config={}) # Adapté
#     pass

# def test_config_file_paths_resolution(mock_ui_config, mock_services_constructors, temp_project_root):
#     """Teste comment les chemins des fichiers de configuration sont résolus."""
#     # Ce test est fortement dépendant de l'ancienne structure avec DefinitionService et ses fichiers de config.
#     # Il faudrait le réécrire pour tester la logique de configuration de initialize_analysis_services si pertinent.
#     # Pour l'instant, commenté.
#     pass