# tests/unit/project_core/pipelines/test_diagnostic_pipeline.py
"""
Tests unitaires pour le pipeline de diagnostic de l'environnement.
"""
import pytest
from unittest.mock import patch, MagicMock, ANY
import logging
from pathlib import Path

from argumentation_analysis.pipelines.diagnostic_pipeline import run_environment_diagnostic_pipeline, EnvironmentDiagnostic

TEST_REQ_FILE_DIAG = "dummy_requirements_diag.txt"

@pytest.fixture
def mock_logger_diag_fixture():
    """Fixture pour mocker le logger utilisé dans le pipeline de diagnostic."""
    logger = MagicMock()
    # Simuler les méthodes de logging de base
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger

@pytest.fixture
def mock_env_diagnostic_instance(mock_logger_diag_fixture):
    """Fixture pour mocker une instance de EnvironmentDiagnostic."""
    instance = MagicMock(spec=EnvironmentDiagnostic)
    instance.results = { # Simuler une structure de base pour results
        "package_installation": {"installed": True},
        "dependencies": {"missing_essential": []},
        "java_config": {"is_ok": True},
        "jpype_config": {"is_ok": True},
        "python_dependencies_status": {"all_ok": True},
        "recommendations": []
    }
    # La méthode run_full_diagnostic est celle qui orchestre tout dans la classe
    instance.run_full_diagnostic.return_value = instance.results 
    return instance

@patch('argumentation_analysis.pipelines.diagnostic_pipeline.setup_logging')
@patch('argumentation_analysis.pipelines.diagnostic_pipeline.EnvironmentDiagnostic')
@patch('argumentation_analysis.pipelines.diagnostic_pipeline.Path')
def test_run_diagnostic_pipeline_success(
    mock_path_class,
    mock_env_diagnostic_class,
    mock_setup_logging,
    mock_env_diagnostic_instance, # Utilise la fixture pour l'instance mockée
    mock_logger_diag_fixture # Utilise la fixture pour le logger
):
    """
    Teste le scénario de succès du pipeline de diagnostic.
    Toutes les vérifications critiques sont supposées réussir.
    """
    # Remplacer le logger global du module par notre mock
    # Ceci est nécessaire car le logger est initialisé au niveau du module
    with patch('argumentation_analysis.pipelines.diagnostic_pipeline.logger', mock_logger_diag_fixture):
        mock_setup_logging.return_value = None # setup_logging est appelé, mais on ne vérifie pas son effet ici
        
        mock_req_path_obj = MagicMock(spec=Path)
        mock_req_path_obj.is_absolute.return_value = True # Simuler un chemin absolu
        mock_path_class.return_value = mock_req_path_obj
        
        # Configurer la classe mockée pour retourner notre instance mockée
        mock_env_diagnostic_class.return_value = mock_env_diagnostic_instance

        exit_code = run_environment_diagnostic_pipeline(
            requirements_path=TEST_REQ_FILE_DIAG,
            log_level="INFO"
        )

        assert exit_code == 0 # Succès
        
        # Vérifier que setup_logging a été appelé avec le bon niveau
        # Note: getattr(logging, "INFO", logging.INFO) résoudra en la valeur numérique de INFO
        mock_setup_logging.assert_called_once_with(level=logging.INFO)
        
        # Vérifier que le logger du module a été utilisé
        mock_logger_diag_fixture.info.assert_any_call(f"Démarrage du pipeline de diagnostic de l'environnement avec log_level=INFO.")
        mock_logger_diag_fixture.info.assert_any_call(f"Fichier requirements utilisé : {TEST_REQ_FILE_DIAG}")

        # Vérifier que EnvironmentDiagnostic a été initialisé correctement
        mock_env_diagnostic_class.assert_called_once_with(requirements_file_path=mock_req_path_obj)
        
        # Vérifier que run_full_diagnostic a été appelé sur l'instance
        mock_env_diagnostic_instance.run_full_diagnostic.assert_called_once()
        
        mock_logger_diag_fixture.info.assert_any_call("Pipeline de diagnostic terminé avec succès.")

@patch('argumentation_analysis.pipelines.diagnostic_pipeline.setup_logging')
@patch('argumentation_analysis.pipelines.diagnostic_pipeline.EnvironmentDiagnostic')
@patch('argumentation_analysis.pipelines.diagnostic_pipeline.Path')
def test_run_diagnostic_pipeline_critical_failure(
    mock_path_class,
    mock_env_diagnostic_class,
    mock_setup_logging,
    mock_env_diagnostic_instance, # Utilise la fixture pour l'instance mockée
    mock_logger_diag_fixture # Utilise la fixture pour le logger
):
    """
    Teste le scénario d'échec du pipeline de diagnostic.
    Une vérification critique (ex: package non installé) est supposée échouer.
    """
    with patch('argumentation_analysis.pipelines.diagnostic_pipeline.logger', mock_logger_diag_fixture):
        mock_setup_logging.return_value = None
        
        mock_req_path_obj = MagicMock(spec=Path)
        mock_req_path_obj.is_absolute.return_value = True
        mock_path_class.return_value = mock_req_path_obj
        
        # Simuler un échec critique, par exemple, le package n'est pas installé
        mock_env_diagnostic_instance.results["package_installation"]["installed"] = False
        mock_env_diagnostic_class.return_value = mock_env_diagnostic_instance

        exit_code = run_environment_diagnostic_pipeline(
            requirements_path=TEST_REQ_FILE_DIAG,
            log_level="WARNING"
        )

        assert exit_code == 1 # Échec
        
        mock_setup_logging.assert_called_once_with(level=logging.WARNING)
        mock_env_diagnostic_class.assert_called_once_with(requirements_file_path=mock_req_path_obj)
        mock_env_diagnostic_instance.run_full_diagnostic.assert_called_once()
        
        mock_logger_diag_fixture.warning.assert_any_call("Pipeline de diagnostic terminé avec des problèmes détectés.")

# TODO:
# - Tester le cas où requirements_path est relatif (Path.is_absolute est False).
# - Tester plus en détail les appels internes à EnvironmentDiagnostic.run_full_diagnostic si nécessaire,
#   en mockant les méthodes individuelles de la classe EnvironmentDiagnostic
#   (check_python_environment, check_package_installation, etc.) et les fonctions externes
#   (check_java_environment, etc.). Cela rendrait les tests plus granulaires mais aussi plus complexes.
#   Pour l'instant, mocker run_full_diagnostic est une bonne première approche pour l'orchestration principale.