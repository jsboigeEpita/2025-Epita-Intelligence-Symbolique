import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module analysis_services.py.
"""

import pytest
import logging
from unittest.mock import patch, MagicMock

# Chemins pour le patching
SETTINGS_PATH = "argumentation_analysis.service_setup.analysis_services.settings"
LOAD_DOTENV_PATH = "argumentation_analysis.service_setup.analysis_services.load_dotenv"
FIND_DOTENV_PATH = "argumentation_analysis.service_setup.analysis_services.find_dotenv"
INITIALIZE_JVM_PATH = (
    "argumentation_analysis.service_setup.analysis_services.initialize_jvm"
)
CREATE_LLM_SERVICE_PATH = (
    "argumentation_analysis.service_setup.analysis_services.create_llm_service"
)

# Importation de la fonction à tester
from argumentation_analysis.service_setup.analysis_services import (
    initialize_analysis_services,
)
from pathlib import Path


@pytest.fixture
def mock_settings(mocker):
    """Fixture pour mocker l'objet settings importé."""
    mock = MagicMock()
    # Configuration par défaut pour la plupart des tests
    mock.enable_jvm = True
    mock.libs_dir = Path("/fake/libs/dir")
    mock.use_mock_llm = False  # Par défaut on ne mock pas le LLM, on mock sa création

    return mocker.patch(SETTINGS_PATH, new=mock)


@pytest.fixture
def mock_load_dotenv(mocker):
    """Mock la fonction load_dotenv."""
    return mocker.patch(LOAD_DOTENV_PATH, return_value=True)


@pytest.fixture
def mock_find_dotenv(mocker):
    """Mock la fonction find_dotenv."""
    return mocker.patch(FIND_DOTENV_PATH, return_value=".env.test")


@pytest.fixture
def mock_init_jvm(mocker):
    """Mock la fonction initialize_jvm."""
    return mocker.patch(INITIALIZE_JVM_PATH, return_value=True)


@pytest.fixture
def mock_create_llm(mocker):
    """Mock la fonction create_llm_service."""
    mock_llm_instance = MagicMock()
    mock_llm_instance.service_id = "mock-llm"
    return mocker.patch(CREATE_LLM_SERVICE_PATH, return_value=mock_llm_instance)


def test_initialize_services_nominal_case(
    mock_settings,
    mock_load_dotenv,
    mock_find_dotenv,
    mock_init_jvm,
    mock_create_llm,
    caplog,
    mocker,
):
    """Teste le cas nominal d'initialisation des services."""
    caplog.set_level(logging.INFO)
    mock_settings.enable_jvm = True
    mock_settings.libs_dir = Path("/fake/libs/dir")
    # Forcer l'utilisation du mock LLM via les settings, ce qui est la méthode standard testée ici
    mock_settings.use_mock_llm = True
    mocker.patch("pathlib.Path.exists", return_value=True)

    # La fixture mock_create_llm retourne déjà un MagicMock avec service_id='mock-llm'
    # Il n'est pas nécessaire de le reconfigurer ici.

    services = initialize_analysis_services()

    mock_find_dotenv.assert_called_once()
    mock_load_dotenv.assert_called_once()

    mock_init_jvm.assert_called_once_with()
    assert services.get("jvm_ready") is True

    # create_llm_service est appelé avec force_mock=True car mock_settings.use_mock_llm = True
    mock_create_llm.assert_called_once_with(
        service_id="default_llm_service",
        model_id=mock_settings.default_model_id,
        force_mock=True,
    )
    # L'objet retourné doit être celui de la fixture mock_create_llm
    assert services.get("llm_service") == mock_create_llm.return_value

    # Rendre l'assertion robuste à l'OS en reconstruisant le chemin attendu
    expected_path_str = str(Path("/fake/libs/dir"))
    assert (
        f"Initialisation de la JVM avec LIBS_DIR: {expected_path_str}..." in caplog.text
    )
    # L'assertion doit correspondre au service_id du mock de la fixture, soit 'mock-llm'
    assert "[OK] Service LLM créé (Type: MagicMock, ID: mock-llm)." in caplog.text


def test_initialize_services_dotenv_fails(
    mock_settings, mock_load_dotenv, mock_find_dotenv, caplog
):
    """Teste le cas où le chargement de .env échoue, mais sans impacter le reste."""
    caplog.set_level(logging.INFO)
    mock_settings.enable_jvm = False  # disable jvm to isolate
    mock_find_dotenv.return_value = "/fake/.env"
    mock_load_dotenv.return_value = False

    with patch(CREATE_LLM_SERVICE_PATH, return_value=MagicMock()):
        initialize_analysis_services()
        mock_load_dotenv.assert_called_once_with("/fake/.env")


def test_initialize_services_jvm_fails(
    mock_settings, mock_init_jvm, mock_load_dotenv, mock_find_dotenv, caplog, mocker
):
    """Teste le cas où l'initialisation de la JVM échoue."""
    caplog.set_level(logging.WARNING)
    mock_settings.enable_jvm = True
    mock_settings.libs_dir = Path("/fake/libs/dir")
    mock_init_jvm.return_value = False
    mocker.patch("pathlib.Path.exists", return_value=True)

    with patch(CREATE_LLM_SERVICE_PATH, return_value=MagicMock()):
        services = initialize_analysis_services()

    mock_init_jvm.assert_called_once_with()
    assert services.get("jvm_ready") is False
    assert "La JVM n'a pas pu être initialisée." in caplog.text


def test_initialize_services_llm_fails_returns_none(
    mock_settings,
    mock_create_llm,
    mock_init_jvm,
    mock_load_dotenv,
    mock_find_dotenv,
    caplog,
):
    """Teste le cas où la création du LLM retourne None."""
    caplog.set_level(logging.WARNING)
    mock_settings.use_mock_llm = True  # Important
    mock_create_llm.return_value = None

    services = initialize_analysis_services()

    assert services.get("llm_service") is None
    assert "create_llm_service a retourné None." in caplog.text


def test_initialize_services_llm_fails_raises_exception(
    mock_settings,
    mock_create_llm,
    mock_init_jvm,
    mock_load_dotenv,
    mock_find_dotenv,
    caplog,
):
    """Teste le cas où la création du LLM lève une exception."""
    caplog.set_level(logging.CRITICAL)
    mock_settings.use_mock_llm = True
    expected_exception = Exception("Erreur critique LLM")
    mock_create_llm.side_effect = expected_exception

    services = initialize_analysis_services()

    mock_create_llm.assert_called_once_with(
        service_id="default_llm_service",
        model_id=mock_settings.default_model_id,
        force_mock=True,
    )
    assert services.get("llm_service") is None
    assert (
        f"Échec critique lors de la création du service LLM: {expected_exception}"
        in caplog.text
    )


def test_initialize_services_jvm_disabled(mock_settings, mock_init_jvm, caplog):
    """Teste que la JVM n'est pas initialisée si elle est désactivée dans la config."""
    caplog.set_level(logging.INFO)
    mock_settings.enable_jvm = False

    with patch(CREATE_LLM_SERVICE_PATH, return_value=MagicMock()):
        services = initialize_analysis_services()

    assert "Initialisation de la JVM sautée" in caplog.text
    assert services.get("jvm_ready") is False
    mock_init_jvm.assert_not_called()


def test_initialize_services_libs_dir_is_none(mock_settings, mock_init_jvm, caplog):
    """Teste le cas où LIBS_DIR est None dans la config."""
    caplog.set_level(logging.ERROR)
    mock_settings.enable_jvm = True
    mock_settings.libs_dir = None

    with patch(CREATE_LLM_SERVICE_PATH, return_value=MagicMock()):
        services = initialize_analysis_services()

    assert services.get("jvm_ready") is False
    assert "enable_jvm=True mais settings.libs_dir n'est pas configuré" in caplog.text
    mock_init_jvm.assert_not_called()


# Note: Tester les échecs d'import de LIBS_DIR est complexe car cela se produit au moment de l'import du module
# analysis_services.py lui-même. Les tests ci-dessus simulent LIBS_DIR ayant une valeur (ou None)
# au moment où initialize_analysis_services est exécutée.
