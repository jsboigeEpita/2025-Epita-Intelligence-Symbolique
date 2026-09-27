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
ENV_MANAGER_PATH = (
    "argumentation_analysis.service_setup.analysis_services.EnvironmentManager"
)
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
def mock_env_manager(mocker):
    """Keep this suite independent of the local root .env."""
    return mocker.patch(ENV_MANAGER_PATH)


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
    mock_env_manager,
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

    mock_env_manager.assert_called_once_with()

    mock_init_jvm.assert_called_once_with()
    assert services.get("jvm_ready") is True

    # #2115: the assertion used to compare against ``mock_settings.default_model_id``
    # — an auto-created MagicMock attribute. Any name passed, so the assertion
    # certified the phantom the production code was reading. #2728 then removed
    # the model choice from this call entirely: no ``model_id`` is passed, the
    # factory resolves it.
    mock_create_llm.assert_called_once_with(
        service_id="default_llm_service",
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


def test_initialize_services_without_root_dotenv(mock_settings, mock_env_manager):
    """The canonical loader can report a missing root .env without stopping setup."""
    mock_settings.enable_jvm = False
    mock_env_manager.return_value.dotenv_loaded = False

    with patch(CREATE_LLM_SERVICE_PATH, return_value=MagicMock()) as create_llm:
        services = initialize_analysis_services()

    mock_env_manager.assert_called_once_with()
    create_llm.assert_called_once()
    assert services["jvm_ready"] is False
    assert services["llm_service"] is create_llm.return_value


def test_initialize_services_jvm_fails(
    mock_settings, mock_init_jvm, mock_env_manager, caplog, mocker
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
    mock_env_manager,
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
    mock_env_manager,
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
        force_mock=True,
    )
    assert services.get("llm_service") is None
    assert (
        f"Échec critique lors de la création du service LLM: {expected_exception}"
        in caplog.text
    )


def test_initialize_services_jvm_disabled(
    mock_settings, mock_init_jvm, mock_env_manager, caplog
):
    """Teste que la JVM n'est pas initialisée si elle est désactivée dans la config."""
    caplog.set_level(logging.INFO)
    mock_settings.enable_jvm = False

    with patch(CREATE_LLM_SERVICE_PATH, return_value=MagicMock()):
        services = initialize_analysis_services()

    assert "Initialisation de la JVM sautée" in caplog.text
    assert services.get("jvm_ready") is False
    mock_init_jvm.assert_not_called()


def test_initialize_services_libs_dir_is_none(
    mock_settings, mock_init_jvm, mock_env_manager, caplog
):
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


# --- #2115 : la lecture du model_id, sur l'objet settings RÉEL ----------------


def test_llm_service_is_built_with_real_settings(mock_env_manager, mock_init_jvm):
    """The service is built when ``settings`` is the real object (#2115).

    Every other test in this module patches ``settings`` with a MagicMock —
    which is precisely why the defect survived: a mock returns an
    auto-attribute for ANY name and never raises ``AttributeError``. Keeping
    ``settings`` real is the point of this test.

    ``create_llm_service`` auto-mocks itself under pytest, so reaching it is
    enough — no network, no key required.
    """
    services = initialize_analysis_services()

    assert services.get("llm_service") is not None, (
        "llm_service is None: the model-id read raised AttributeError and the "
        "surrounding ``except Exception`` swallowed it — every run silently "
        "lost its LLM service (#2115)."
    )


def test_built_service_carries_the_resolver_model_id(
    mock_env_manager, mock_init_jvm, mocker, monkeypatch
):
    """#2728: the service this function builds carries the resolver's model id.

    The site used to pass ``settings.service_manager.default_model_id`` — a
    settings field no resolver reads — so a seat that picks its model through
    ``OPENAI_CHAT_MODEL_ID`` got it everywhere except on this path. The
    subtraction (#1875's class) leaves the choice to the factory, whose
    fallback reads the same env var as ``resolve_chat_endpoint``.
    """
    from argumentation_analysis.config.settings import settings as real_settings

    # The factory auto-mocks under pytest; the witness needs the authentic
    # branch, which only builds a client — no request is sent.
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "witness-key-2728")
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "witness-model-2728")
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    # Inert cache wrap: the built service exposes ai_model_id directly.
    monkeypatch.delenv("LLM_CACHE_MODE", raising=False)
    mocker.patch.object(real_settings, "enable_jvm", False)
    mocker.patch.object(real_settings, "use_mock_llm", False)

    services = initialize_analysis_services()

    service = services.get("llm_service")
    assert service is not None
    assert service.ai_model_id == "witness-model-2728", (
        "the built service does not carry OPENAI_CHAT_MODEL_ID: the site is "
        "choosing the model from somewhere the resolver cannot see"
    )
