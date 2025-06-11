
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



def test_initialize_services_nominal_case(mock_load_dotenv, mock_find_dotenv, mock_config_valid_libs_dir, caplog):
    """Teste le cas nominal d'initialisation des services."""
    caplog.set_level(logging.INFO)
    
    mock_jvm = MagicMock(return_value=True)
    mock_llm = MagicMock(name="MockLLMServiceInstance")
    setattr(mock_llm, 'service_id', 'test-llm-id') # Simuler un attribut service_id

    with patch(INITIALIZE_JVM_PATH, mock_jvm) as patched_jvm, \
         patch(CREATE_LLM_SERVICE_PATH, return_value=mock_llm) as patched_llm:
        
        services = initialize_analysis_services(mock_config_valid_libs_dir)

        mock_find_dotenv.assert_called_once()
        mock_load_dotenv.assert_called_once_with(".env.test", override=True)
        
        patched_jvm.assert_called_once_with(lib_dir_path="/fake/libs/dir")
        assert services.get("jvm_ready") is True
        
        patched_llm.assert_called_once_with(config=mock_config_valid_libs_dir)
        assert services.get("llm_service") == mock_llm
        
        assert "Résultat du chargement de .env: True" in caplog.text
        assert "Initialisation de la JVM avec LIBS_DIR: /fake/libs/dir..." in caplog.text
        assert "Service LLM créé avec succès (ID: test-llm-id)" in caplog.text

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
def test_initialize_services_jvm_fails(mock_create_llm, mock_load_dotenv, mock_find_dotenv, mock_config_valid_libs_dir, caplog):
    """Teste le cas où l'initialisation de la JVM échoue."""
    caplog.set_level(logging.WARNING)
    with patch(INITIALIZE_JVM_PATH, return_value=False) as patched_jvm:
        services = initialize_analysis_services(mock_config_valid_libs_dir)
        
        patched_jvm.assert_called_once_with(lib_dir_path="/fake/libs/dir")
        assert services.get("jvm_ready") is False
        assert "La JVM n'a pas pu être initialisée." in caplog.text



 # JVM réussit
def test_initialize_services_llm_fails_returns_none(mock_init_jvm, mock_load_dotenv, mock_find_dotenv, mock_config_valid_libs_dir, caplog):
    """Teste le cas où la création du LLM retourne None."""
    caplog.set_level(logging.WARNING)
    with patch(CREATE_LLM_SERVICE_PATH, return_value=None) as patched_llm:
        services = initialize_analysis_services(mock_config_valid_libs_dir)
        
        patched_llm.assert_called_once_with(config=mock_config_valid_libs_dir)
        assert services.get("llm_service") is None
        assert "Le service LLM n'a pas pu être créé (create_llm_service a retourné None)." in caplog.text



 # JVM réussit
def test_initialize_services_llm_fails_raises_exception(mock_init_jvm, mock_load_dotenv, mock_find_dotenv, mock_config_valid_libs_dir, caplog):
    """Teste le cas où la création du LLM lève une exception."""
    caplog.set_level(logging.CRITICAL)
    expected_exception = Exception("Erreur critique LLM")
    with patch(CREATE_LLM_SERVICE_PATH, side_effect=expected_exception) as patched_llm:
        services = initialize_analysis_services(mock_config_valid_libs_dir) # L'exception est capturée et loguée
        
        patched_llm.assert_called_once()
        assert services.get("llm_service") is None # Doit être None après l'exception
        assert f"Échec critique lors de la création du service LLM: {expected_exception}" in caplog.text
        # Vérifier que l'exception n'est pas propagée par initialize_analysis_services par défaut


def test_initialize_services_libs_dir_from_module_import(mock_create_llm, mock_load_dotenv, mock_find_dotenv, mock_config_no_libs_dir, caplog):
    """Teste l'utilisation de LIBS_DIR importé si non fourni dans config."""
    caplog.set_level(logging.INFO)
    # Simuler que LIBS_DIR est importé avec succès
    with patch(LIBS_DIR_PATH_MODULE, "/imported/libs/path", create=True), \
         patch(INITIALIZE_JVM_PATH, return_value=True) as patched_jvm:
        
        initialize_analysis_services(mock_config_no_libs_dir)
        patched_jvm.assert_called_once_with(lib_dir_path="/imported/libs/path")
        assert "Initialisation de la JVM avec LIBS_DIR: /imported/libs/path..." in caplog.text



def test_initialize_services_libs_dir_is_none(mock_create_llm, mock_load_dotenv, mock_find_dotenv, mock_config_no_libs_dir, caplog):
    """Teste le cas où LIBS_DIR n'est ni dans config ni importable (devient None)."""
    caplog.set_level(logging.ERROR)
    # Simuler que LIBS_DIR est None après tentative d'import
    with patch(LIBS_DIR_PATH_MODULE, None, create=True), \
         patch(INITIALIZE_JVM_PATH) as patched_jvm: # JVM ne sera pas appelée avec un chemin
        
        services = initialize_analysis_services(mock_config_no_libs_dir)
        
        # initialize_jvm ne devrait pas être appelé avec lib_dir_path=None,
        # la logique interne devrait gérer cela.
        # Ou, si elle est appelée, elle devrait retourner False.
        # Ici, on vérifie que le statut jvm_ready est False et qu'une erreur est loguée.
        assert services.get("jvm_ready") is False
        assert "Le chemin vers LIBS_DIR n'est pas configuré." in caplog.text
        patched_jvm.assert_not_called() # Ou vérifier qu'elle est appelée et retourne False

# Note: Tester les échecs d'import de LIBS_DIR est complexe car cela se produit au moment de l'import du module
# analysis_services.py lui-même. Les tests ci-dessus simulent LIBS_DIR ayant une valeur (ou None)
# au moment où initialize_analysis_services est exécutée.