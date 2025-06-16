
# Authentic gpt-4o-mini imports (replacing mocks)
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
LOAD_DOTENV_PATH = "argumentation_analysis.service_setup.analysis_services.load_dotenv"
FIND_DOTENV_PATH = "argumentation_analysis.service_setup.analysis_services.find_dotenv"
INITIALIZE_JVM_PATH = "argumentation_analysis.service_setup.analysis_services.initialize_jvm"
CREATE_LLM_SERVICE_PATH = "argumentation_analysis.service_setup.analysis_services.create_llm_service"
LIBS_DIR_PATH_MODULE = "argumentation_analysis.service_setup.analysis_services.LIBS_DIR" # Pour le cas où il est importé

# Importation de la fonction à tester
from argumentation_analysis.service_setup.analysis_services import initialize_analysis_services

@pytest.fixture
def mock_config_valid_libs_dir():
    """Configuration avec un chemin LIBS_DIR valide."""
    return {"LIBS_DIR_PATH": "/fake/libs/dir"}

@pytest.fixture
def mock_config_no_libs_dir():
    """Configuration sans chemin LIBS_DIR explicite (dépendra de l'import)."""
    return {}

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
    mock_llm_instance.service_id = 'mock-llm'
    return mocker.patch(CREATE_LLM_SERVICE_PATH, return_value=mock_llm_instance)


def test_initialize_services_nominal_case(mock_load_dotenv, mock_find_dotenv, mock_init_jvm, mock_create_llm, mock_config_valid_libs_dir, caplog):
    """Teste le cas nominal d'initialisation des services."""
    caplog.set_level(logging.INFO)
    
    # mock_llm est maintenant la valeur de retour de la fixture mock_create_llm
    mock_llm = mock_create_llm
    setattr(mock_llm, 'service_id', 'test-llm-id')

    services = initialize_analysis_services(mock_config_valid_libs_dir)

    mock_find_dotenv.assert_called_once()
    mock_load_dotenv.assert_called_once_with(".env.test", override=True)
    
    mock_init_jvm.assert_called_once_with(lib_dir_path="/fake/libs/dir")
    assert services.get("jvm_ready") is True
    
    # La fixture mock_create_llm est un patch, donc on vérifie son mock
    CREATE_LLM_SERVICE_PATH.assert_called_once_with(config=mock_config_valid_libs_dir)
    assert services.get("llm_service") == mock_llm
    
    assert "Résultat du chargement de .env: True" in caplog.text
    assert "Initialisation de la JVM avec LIBS_DIR: /fake/libs/dir..." in caplog.text
    assert f"Service LLM créé avec succès (ID: {mock_llm.service_id})" in caplog.text

 # Simule .env non trouvé
 # Simule .env non chargé
def test_initialize_services_dotenv_fails(mock_load_dotenv, mock_find_dotenv, mock_config_valid_libs_dir, caplog):
    """Teste le cas où le chargement de .env échoue."""
    caplog.set_level(logging.INFO)
    mock_find_dotenv.return_value = None
    mock_load_dotenv.return_value = False
    with patch(INITIALIZE_JVM_PATH, return_value=True), \
         patch(CREATE_LLM_SERVICE_PATH, return_value=MagicMock()):
        
        initialize_analysis_services(mock_config_valid_libs_dir)
        assert "Résultat du chargement de .env: False" in caplog.text



# ) # LLM réussit # Commentaire orphelin, la parenthèse a été supprimée
def test_initialize_services_jvm_fails(mock_create_llm, mock_init_jvm, mock_load_dotenv, mock_find_dotenv, mock_config_valid_libs_dir, caplog):
    """Teste le cas où l'initialisation de la JVM échoue."""
    caplog.set_level(logging.WARNING)
    mock_init_jvm.return_value = False
    services = initialize_analysis_services(mock_config_valid_libs_dir)
    
    mock_init_jvm.assert_called_once_with(lib_dir_path="/fake/libs/dir")
    assert services.get("jvm_ready") is False
    assert "La JVM n'a pas pu être initialisée." in caplog.text



 # JVM réussit
def test_initialize_services_llm_fails_returns_none(mock_init_jvm, mock_load_dotenv, mock_find_dotenv, mock_config_valid_libs_dir, caplog):
    """Teste le cas où la création du LLM retourne None."""
    caplog.set_level(logging.WARNING)
    # On utilise directement la fixture qui patche, et on change sa valeur de retour
    mock_create_llm.return_value = None
    services = initialize_analysis_services(mock_config_valid_libs_dir)
    
    # La fixture est un patch, donc on vérifie le mock sous-jacent
    CREATE_LLM_SERVICE_PATH.assert_called_once_with(config=mock_config_valid_libs_dir)
    assert services.get("llm_service") is None
    assert "Le service LLM n'a pas pu être créé (create_llm_service a retourné None)." in caplog.text



 # JVM réussit
def test_initialize_services_llm_fails_raises_exception(mock_init_jvm, mock_load_dotenv, mock_find_dotenv, mock_config_valid_libs_dir, caplog):
    """Teste le cas où la création du LLM lève une exception."""
    caplog.set_level(logging.CRITICAL)
    expected_exception = Exception("Erreur critique LLM")
    mock_create_llm.side_effect = expected_exception
    services = initialize_analysis_services(mock_config_valid_libs_dir)
    
    CREATE_LLM_SERVICE_PATH.assert_called_once()
    assert services.get("llm_service") is None
    assert f"Échec critique lors de la création du service LLM: {expected_exception}" in caplog.text
        # Vérifier que l'exception n'est pas propagée par initialize_analysis_services par défaut


def test_initialize_services_libs_dir_from_module_import(mock_create_llm, mock_init_jvm, mock_load_dotenv, mock_find_dotenv, mock_config_no_libs_dir, caplog):
    """Teste l'utilisation de LIBS_DIR importé si non fourni dans config."""
    caplog.set_level(logging.INFO)
    # Simuler que LIBS_DIR est importé avec succès
    with patch(LIBS_DIR_PATH_MODULE, "/imported/libs/path", create=True), \
         patch(INITIALIZE_JVM_PATH, return_value=True):
        
        initialize_analysis_services(mock_config_no_libs_dir)
        mock_init_jvm.assert_called_once_with(lib_dir_path="/imported/libs/path")
        assert "Initialisation de la JVM avec LIBS_DIR: /imported/libs/path..." in caplog.text



def test_initialize_services_libs_dir_is_none(mock_create_llm, mock_init_jvm, mock_load_dotenv, mock_find_dotenv, mock_config_no_libs_dir, caplog):
    """Teste le cas où LIBS_DIR n'est ni dans config ni importable (devient None)."""
    caplog.set_level(logging.ERROR)
    # Simuler que LIBS_DIR est None après tentative d'import
    with patch(LIBS_DIR_PATH_MODULE, None, create=True), \
         patch(INITIALIZE_JVM_PATH): # JVM ne sera pas appelée avec un chemin
        
        services = initialize_analysis_services(mock_config_no_libs_dir)
        
        assert services.get("jvm_ready") is False
        assert "Le chemin vers LIBS_DIR n'est pas configuré." in caplog.text
        mock_init_jvm.assert_not_called()

# Note: Tester les échecs d'import de LIBS_DIR est complexe car cela se produit au moment de l'import du module
# analysis_services.py lui-même. Les tests ci-dessus simulent LIBS_DIR ayant une valeur (ou None)
# au moment où initialize_analysis_services est exécutée.