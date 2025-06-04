# tests/unit/project_core/pipelines/test_dependency_management_pipeline.py
"""
Tests unitaires pour le pipeline de gestion des dépendances.
"""
import pytest
from unittest.mock import patch, MagicMock, mock_open, call
from pathlib import Path
import sys

from argumentation_analysis.pipelines.dependency_management_pipeline import run_dependency_installation_pipeline

TEST_REQ_FILE = "test_requirements.txt"

@pytest.fixture
def mock_logger_fixture(): # Renommé pour éviter conflit avec le logger du module testé
    """Fixture pour mocker le logger retourné par setup_logging."""
    logger = MagicMock()
    return logger

@patch('argumentation_analysis.pipelines.dependency_management_pipeline.setup_logging')
@patch('argumentation_analysis.pipelines.dependency_management_pipeline.run_shell_command')
@patch('argumentation_analysis.pipelines.dependency_management_pipeline.Path')
@patch('builtins.open', new_callable=mock_open)
def test_run_dependency_installation_success_no_deps(
    mock_file_open,
    mock_path_class,
    mock_run_shell_command,
    mock_setup_logging,
    mock_logger_fixture
):
    """
    Teste le succès du pipeline quand le fichier requirements est vide ou ne contient que des commentaires.
    """
    mock_setup_logging.return_value = mock_logger_fixture
    
    mock_req_file_path_obj = MagicMock(spec=Path)
    mock_req_file_path_obj.is_file.return_value = True
    mock_path_class.return_value = mock_req_file_path_obj
    
    # Simuler un fichier requirements vide ou avec commentaires
    mock_file_open.return_value.readlines.return_value = ["# commentaire\n", "\n"]

    result = run_dependency_installation_pipeline(
        requirements_file_path=TEST_REQ_FILE,
        log_level="INFO"
    )

    assert result is True
    mock_setup_logging.assert_called_once_with("INFO")
    mock_logger_fixture.info.assert_any_call(f"Démarrage du pipeline d'installation des dépendances depuis: {TEST_REQ_FILE}")
    mock_path_class.assert_called_once_with(TEST_REQ_FILE)
    mock_req_file_path_obj.is_file.assert_called_once()
    mock_file_open.assert_called_once_with(mock_req_file_path_obj, 'r', encoding='utf-8')
    
    mock_run_shell_command.assert_not_called() # Aucune dépendance à installer
    mock_logger_fixture.info.assert_any_call("Toutes les dépendances listées dans le fichier requirements ont été traitées avec succès.")


@patch('argumentation_analysis.pipelines.dependency_management_pipeline.setup_logging')
@patch('argumentation_analysis.pipelines.dependency_management_pipeline.run_shell_command')
@patch('argumentation_analysis.pipelines.dependency_management_pipeline.Path')
@patch('builtins.open', new_callable=mock_open)
def test_run_dependency_installation_req_file_not_found(
    mock_file_open,
    mock_path_class,
    mock_run_shell_command,
    mock_setup_logging,
    mock_logger_fixture
):
    """
    Teste l'échec du pipeline si le fichier requirements n'est pas trouvé.
    """
    mock_setup_logging.return_value = mock_logger_fixture
    
    mock_req_file_path_obj = MagicMock(spec=Path)
    mock_req_file_path_obj.is_file.return_value = False # Fichier non trouvé
    mock_path_class.return_value = mock_req_file_path_obj

    result = run_dependency_installation_pipeline(requirements_file_path=TEST_REQ_FILE)

    assert result is False
    mock_logger_fixture.error.assert_called_once_with(f"Le fichier requirements '{TEST_REQ_FILE}' n'a pas été trouvé.")
    mock_file_open.assert_not_called()
    mock_run_shell_command.assert_not_called()

@patch('argumentation_analysis.pipelines.dependency_management_pipeline.setup_logging')
@patch('argumentation_analysis.pipelines.dependency_management_pipeline.run_shell_command')
@patch('argumentation_analysis.pipelines.dependency_management_pipeline.Path')
@patch('builtins.open', new_callable=mock_open)
def test_run_dependency_installation_read_file_error(
    mock_file_open,
    mock_path_class,
    mock_run_shell_command,
    mock_setup_logging,
    mock_logger_fixture
):
    """
    Teste l'échec du pipeline si une erreur survient lors de la lecture du fichier requirements.
    """
    mock_setup_logging.return_value = mock_logger_fixture
    
    mock_req_file_path_obj = MagicMock(spec=Path)
    mock_req_file_path_obj.is_file.return_value = True
    mock_path_class.return_value = mock_req_file_path_obj
    
    error_message = "Erreur de lecture"
    mock_file_open.side_effect = Exception(error_message)

    result = run_dependency_installation_pipeline(requirements_file_path=TEST_REQ_FILE)

    assert result is False
    mock_logger_fixture.error.assert_called_once_with(
        f"Erreur lors de la lecture du fichier '{TEST_REQ_FILE}': {error_message}"
    )
    mock_run_shell_command.assert_not_called()

@patch('argumentation_analysis.pipelines.dependency_management_pipeline.setup_logging')
@patch('argumentation_analysis.pipelines.dependency_management_pipeline.run_shell_command')
@patch('argumentation_analysis.pipelines.dependency_management_pipeline.Path')
@patch('builtins.open', new_callable=mock_open)
@patch('argumentation_analysis.pipelines.dependency_management_pipeline.sys') # Pour mocker sys.executable
def test_run_dependency_installation_success_one_dep(
    mock_sys,
    mock_file_open,
    mock_path_class,
    mock_run_shell_command,
    mock_setup_logging,
    mock_logger_fixture
):
    """
    Teste le succès du pipeline avec l'installation d'une dépendance.
    Vérifie l'utilisation de force_reinstall et pip_options.
    """
    mock_setup_logging.return_value = mock_logger_fixture
    
    # Mocker sys.executable
    mock_sys.executable = "/path/to/custom_python"
    # Mocker Path(sys.executable).name
    mock_python_exe_path_obj = MagicMock(spec=Path)
    mock_python_exe_path_obj.name = "custom_python"


    mock_req_file_path_obj = MagicMock(spec=Path)
    mock_req_file_path_obj.is_file.return_value = True
    
    # Path() doit retourner le mock de sys.executable ou le mock du fichier requirements
    def path_side_effect(path_arg):
        if path_arg == TEST_REQ_FILE:
            return mock_req_file_path_obj
        if path_arg == "/path/to/custom_python": # Correspond à mock_sys.executable
            return mock_python_exe_path_obj
        return MagicMock(spec=Path) # Fallback
    mock_path_class.side_effect = path_side_effect
    
    # Simuler un fichier requirements avec une dépendance
    dep_name = "requests==2.25.1"
    mock_file_open.return_value.readlines.return_value = [f"{dep_name}\n"]
    
    # Simuler un succès de run_shell_command
    mock_run_shell_command.return_value = (0, "Success output", "") # code, stdout, stderr

    custom_pip_options = ["--no-cache-dir", "--upgrade"]

    result = run_dependency_installation_pipeline(
        requirements_file_path=TEST_REQ_FILE,
        force_reinstall=True,
        pip_options=custom_pip_options,
        log_level="DEBUG"
    )

    assert result is True
    mock_setup_logging.assert_called_once_with("DEBUG")
    mock_file_open.assert_called_once_with(mock_req_file_path_obj, 'r', encoding='utf-8')
    
    expected_command_parts = [
        mock_python_exe_path_obj.name, # Doit être "custom_python"
        "-m",
        "pip",
        "install",
        dep_name,
        "--force-reinstall" # Ajouté car force_reinstall=True
    ]
    expected_command_parts.extend(custom_pip_options)
    expected_command = " ".join(expected_command_parts)
    
    mock_run_shell_command.assert_called_once_with(expected_command)
    mock_logger_fixture.info.assert_any_call(f"Tentative d'installation de '{dep_name}' avec la commande: '{expected_command}'")
    mock_logger_fixture.info.assert_any_call(f"Installation de '{dep_name}' réussie.")
    mock_logger_fixture.debug.assert_any_call(f"Sortie pip (stdout) pour {dep_name}:\nSuccess output")
    mock_logger_fixture.info.assert_any_call("Toutes les dépendances listées dans le fichier requirements ont été traitées avec succès.")

@patch('argumentation_analysis.pipelines.dependency_management_pipeline.setup_logging')
@patch('argumentation_analysis.pipelines.dependency_management_pipeline.run_shell_command')
@patch('argumentation_analysis.pipelines.dependency_management_pipeline.Path')
@patch('builtins.open', new_callable=mock_open)
@patch('argumentation_analysis.pipelines.dependency_management_pipeline.sys')
def test_run_dependency_installation_partial_failure(
    mock_sys,
    mock_file_open,
    mock_path_class,
    mock_run_shell_command,
    mock_setup_logging,
    mock_logger_fixture
):
    """
    Teste un échec partiel où une dépendance s'installe et une autre échoue.
    Le pipeline doit retourner False.
    """
    mock_setup_logging.return_value = mock_logger_fixture
    mock_sys.executable = "python" # Utilisation simple pour ce test
    
    mock_python_exe_path_obj = MagicMock(spec=Path)
    mock_python_exe_path_obj.name = "python"

    mock_req_file_path_obj = MagicMock(spec=Path)
    mock_req_file_path_obj.is_file.return_value = True

    def path_side_effect(path_arg):
        if path_arg == TEST_REQ_FILE: return mock_req_file_path_obj
        if path_arg == "python": return mock_python_exe_path_obj
        return MagicMock(spec=Path)
    mock_path_class.side_effect = path_side_effect

    dep1_ok = "package_ok"
    dep2_fail = "package_fail"
    mock_file_open.return_value.readlines.return_value = [f"{dep1_ok}\n", f"{dep2_fail}\n"]

    # Simuler succès pour dep1_ok, échec pour dep2_fail
    mock_run_shell_command.side_effect = [
        (0, "OK stdout", "OK stderr"),       # Succès pour package_ok
        (1, "FAIL stdout", "FAIL stderr")  # Échec pour package_fail
    ]

    result = run_dependency_installation_pipeline(requirements_file_path=TEST_REQ_FILE)

    assert result is False # Le pipeline global doit échouer
    
    # Vérifier les appels à run_shell_command
    expected_command1_parts = [mock_python_exe_path_obj.name, "-m", "pip", "install", dep1_ok]
    expected_command2_parts = [mock_python_exe_path_obj.name, "-m", "pip", "install", dep2_fail]
    
    calls = [
        call(" ".join(expected_command1_parts)),
        call(" ".join(expected_command2_parts))
    ]
    mock_run_shell_command.assert_has_calls(calls)
    assert mock_run_shell_command.call_count == 2

    # Vérifier les logs pour package_ok (succès)
    mock_logger_fixture.info.assert_any_call(f"Tentative d'installation de '{dep1_ok}' avec la commande: '{' '.join(expected_command1_parts)}'")
    mock_logger_fixture.info.assert_any_call(f"Installation de '{dep1_ok}' réussie.")
    
    # Vérifier les logs pour package_fail (échec)
    mock_logger_fixture.info.assert_any_call(f"Tentative d'installation de '{dep2_fail}' avec la commande: '{' '.join(expected_command2_parts)}'")
    mock_logger_fixture.error.assert_any_call(f"Erreur lors de l'installation de '{dep2_fail}'. Code de retour: 1")
    mock_logger_fixture.error.assert_any_call(f"Sortie pip (stdout) pour {dep2_fail} (erreur):\nFAIL stdout")
    mock_logger_fixture.error.assert_any_call(f"Sortie pip (stderr) pour {dep2_fail} (erreur):\nFAIL stderr")

    mock_logger_fixture.warning.assert_called_once_with(
        "Au moins une dépendance n'a pas pu être installée correctement. Veuillez vérifier les logs."
    )


# TODO: Ajouter plus de cas de test:
# 3. Différentes combinaisons de force_reinstall et pip_options (plus de variations).
# 4. Cas où sys.executable est différent (pour s'assurer que Path(sys.executable).name est bien utilisé). - Déjà couvert en partie