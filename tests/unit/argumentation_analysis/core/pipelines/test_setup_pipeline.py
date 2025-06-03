# tests/unit/project_core/pipelines/test_setup_pipeline.py
"""
Tests unitaires pour le pipeline de configuration de l'environnement de test.
"""
import pytest
from unittest.mock import patch, MagicMock, ANY
from pathlib import Path
import logging

from argumentation_analysis.core.pipelines.setup_pipeline import run_test_environment_setup_pipeline

# Constantes pour les chemins de test
TEST_CONFIG_PATH = Path("test_config.json")
TEST_REQ_PATH = Path("test_requirements_setup.txt")
TEST_VENV_PATH = Path("test_venv_setup")
TEST_PROJECT_ROOT = Path("test_project_root_setup")

@pytest.fixture
def mock_logger_setup_fixture():
    """Fixture pour mocker le logger utilisé dans le pipeline de setup."""
    with patch('argumentation_analysis.core.pipelines.setup_pipeline.logger') as mock_log:
        yield mock_log

@patch('argumentation_analysis.core.pipelines.setup_pipeline.run_download_jars_pipeline')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.run_dependency_installation_pipeline')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.setup_jpype_mock')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.Path') # Pour mocker Path() et ses instances
def test_run_setup_pipeline_all_steps_success_no_optional(
    mock_path_class, # Mocker la classe Path
    mock_setup_jpype,
    mock_run_dep_install,
    mock_run_download_jars,
    mock_logger_setup_fixture
):
    """
    Teste le succès du pipeline setup avec les étapes optionnelles désactivées (pas de config_path, mock_jpype=False).
    Seul le pipeline d'installation des dépendances doit tourner (et réussir).
    """
    # Configurer les mocks des pipelines appelés pour qu'ils retournent True (succès)
    mock_run_download_jars.return_value = True
    mock_run_dep_install.return_value = True
    # setup_jpype_mock ne devrait pas être appelé si mock_jpype=False

    # Simuler le comportement de Path pour requirements_path
    mock_req_path_obj = MagicMock(spec=Path)
    # Path() appelé avec TEST_REQ_PATH doit retourner ce mock
    mock_path_class.side_effect = lambda p: mock_req_path_obj if p == TEST_REQ_PATH else MagicMock(spec=Path)


    result = run_test_environment_setup_pipeline(
        requirements_path=TEST_REQ_PATH,
        mock_jpype=False,
        venv_path=TEST_VENV_PATH,
        project_root=TEST_PROJECT_ROOT
    )

    assert result is True
    mock_logger_setup_fixture.info.assert_any_call("Démarrage du pipeline de configuration de l'environnement de test.")
    
    # Étape de téléchargement des JARs doit être skippée car config_path est None
    mock_logger_setup_fixture.info.assert_any_call("Aucun `config_path` fourni. Étape de téléchargement des JARs ignorée.")
    mock_run_download_jars.assert_not_called()

    # Étape d'installation des dépendances doit être appelée
    mock_logger_setup_fixture.info.assert_any_call("Étape 3: Exécution du pipeline de gestion des dépendances Python.")
    mock_run_dep_install.assert_called_once_with(
        requirements_path=TEST_REQ_PATH, # Doit être l'objet Path mocké ou le chemin original
        project_root=TEST_PROJECT_ROOT,
        venv_path=TEST_VENV_PATH
    )
    mock_logger_setup_fixture.info.assert_any_call("Pipeline de gestion des dépendances Python terminé avec succès.")

    # Étape de mock JPype ne doit pas être appelée
    mock_setup_jpype.assert_not_called()
    
    mock_logger_setup_fixture.info.assert_any_call("Pipeline de configuration de l'environnement de test terminé avec succès.")

@patch('argumentation_analysis.core.pipelines.setup_pipeline.run_download_jars_pipeline')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.run_dependency_installation_pipeline')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.setup_jpype_mock')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.Path')
def test_run_setup_pipeline_all_steps_success_all_optional_enabled(
    mock_path_class,
    mock_setup_jpype,
    mock_run_dep_install,
    mock_run_download_jars,
    mock_logger_setup_fixture
):
    """
    Teste le succès du pipeline setup avec toutes les étapes optionnelles activées et réussissant.
    """
    mock_run_download_jars.return_value = True
    mock_run_dep_install.return_value = True
    mock_setup_jpype.return_value = None # setup_jpype_mock ne retourne rien en cas de succès

    # Simuler le comportement de Path
    mock_config_path_obj = MagicMock(spec=Path)
    mock_config_path_obj.exists.return_value = True # Le fichier de config existe
    mock_req_path_obj = MagicMock(spec=Path)
    
    def path_side_effect(p_arg):
        if p_arg == TEST_CONFIG_PATH:
            return mock_config_path_obj
        if p_arg == TEST_REQ_PATH:
            return mock_req_path_obj
        # Pour TEST_VENV_PATH et TEST_PROJECT_ROOT, retourner un mock simple
        return MagicMock(spec=Path)
        
    mock_path_class.side_effect = path_side_effect
    # Path() lui-même peut retourner un mock générique si besoin pour d'autres appels non couverts
    mock_path_class.return_value = MagicMock(spec=Path)


    result = run_test_environment_setup_pipeline(
        config_path=TEST_CONFIG_PATH,
        requirements_path=TEST_REQ_PATH,
        mock_jpype=True, # Activer le mock JPype
        venv_path=TEST_VENV_PATH,
        project_root=TEST_PROJECT_ROOT
    )

    assert result is True
    mock_logger_setup_fixture.info.assert_any_call("Démarrage du pipeline de configuration de l'environnement de test.")

    # Vérifier l'étape de téléchargement des JARs
    mock_logger_setup_fixture.info.assert_any_call(f"Utilisation du fichier de configuration: {mock_config_path_obj}")
    # Note: run_download_jars_pipeline dans le code original est appelé avec config_path=config_path.
    # Si config_path est un objet Path, c'est ce qui est passé.
    mock_run_download_jars.assert_called_once_with(config_path=mock_config_path_obj) # Doit être l'objet Path mocké
    mock_logger_setup_fixture.info.assert_any_call("Pipeline de téléchargement des JARs terminé avec succès.")

    # Vérifier l'étape d'installation des dépendances
    mock_run_dep_install.assert_called_once_with(
        requirements_path=TEST_REQ_PATH,
        project_root=TEST_PROJECT_ROOT,
        venv_path=TEST_VENV_PATH
    )
    mock_logger_setup_fixture.info.assert_any_call("Pipeline de gestion des dépendances Python terminé avec succès.")

    # Vérifier l'étape de mock JPype
    mock_logger_setup_fixture.info.assert_any_call("Étape 4: Configuration du mock JPype.")
    mock_setup_jpype.assert_called_once()
    mock_logger_setup_fixture.info.assert_any_call("Mock JPype configuré avec succès.")
    
    mock_logger_setup_fixture.info.assert_any_call("Pipeline de configuration de l'environnement de test terminé avec succès.")

@patch('argumentation_analysis.core.pipelines.setup_pipeline.run_download_jars_pipeline')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.run_dependency_installation_pipeline')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.setup_jpype_mock')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.Path')
def test_run_setup_pipeline_download_jars_fails(
    mock_path_class,
    mock_setup_jpype,
    mock_run_dep_install,
    mock_run_download_jars,
    mock_logger_setup_fixture
):
    """
    Teste le cas où le pipeline de téléchargement des JARs échoue.
    Le pipeline global doit retourner False et les étapes suivantes ne doivent pas s'exécuter.
    """
    mock_run_download_jars.return_value = False # Échec du téléchargement
    # Les autres mocks n'ont pas besoin de retourner de valeur spécifique car ils ne devraient pas être appelés après l'échec

    mock_config_path_obj = MagicMock(spec=Path)
    mock_config_path_obj.exists.return_value = True
    
    def path_side_effect(p_arg):
        if p_arg == TEST_CONFIG_PATH: return mock_config_path_obj
        # Les autres chemins ne sont pas critiques pour ce test spécifique d'échec précoce
        return MagicMock(spec=Path)
    mock_path_class.side_effect = path_side_effect
    mock_path_class.return_value = MagicMock(spec=Path)


    result = run_test_environment_setup_pipeline(
        config_path=TEST_CONFIG_PATH, # Activer l'étape de téléchargement
        requirements_path=TEST_REQ_PATH,
        mock_jpype=True,
        venv_path=TEST_VENV_PATH,
        project_root=TEST_PROJECT_ROOT
    )

    assert result is False # Échec global
    mock_run_download_jars.assert_called_once_with(config_path=mock_config_path_obj)
    mock_logger_setup_fixture.error.assert_any_call("Le pipeline de téléchargement des JARs a échoué.")
    
    # Les étapes suivantes ne doivent pas être appelées
    mock_run_dep_install.assert_not_called()
    mock_setup_jpype.assert_not_called()
    
    mock_logger_setup_fixture.error.assert_any_call("Le pipeline de configuration de l'environnement de test a rencontré des erreurs.")

@patch('argumentation_analysis.core.pipelines.setup_pipeline.run_download_jars_pipeline')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.run_dependency_installation_pipeline')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.setup_jpype_mock')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.Path')
def test_run_setup_pipeline_dependency_install_fails(
    mock_path_class,
    mock_setup_jpype,
    mock_run_dep_install,
    mock_run_download_jars,
    mock_logger_setup_fixture
):
    """
    Teste le cas où le pipeline d'installation des dépendances échoue.
    Le pipeline global doit retourner False et l'étape de mock JPype ne doit pas s'exécuter.
    """
    mock_run_download_jars.return_value = True # Téléchargement OK
    mock_run_dep_install.return_value = False # Installation des dépendances échoue
    # mock_setup_jpype ne devrait pas être appelé

    mock_config_path_obj = MagicMock(spec=Path)
    mock_config_path_obj.exists.return_value = True
    mock_req_path_obj = MagicMock(spec=Path)

    def path_side_effect(p_arg):
        if p_arg == TEST_CONFIG_PATH: return mock_config_path_obj
        if p_arg == TEST_REQ_PATH: return mock_req_path_obj
        return MagicMock(spec=Path)
    mock_path_class.side_effect = path_side_effect
    mock_path_class.return_value = MagicMock(spec=Path)

    result = run_test_environment_setup_pipeline(
        config_path=TEST_CONFIG_PATH,
        requirements_path=TEST_REQ_PATH,
        mock_jpype=True, # Tentative de mocker JPype
        venv_path=TEST_VENV_PATH,
        project_root=TEST_PROJECT_ROOT
    )

    assert result is False # Échec global
    mock_run_download_jars.assert_called_once() # Doit être appelé
    mock_run_dep_install.assert_called_once() # Doit être appelé
    mock_logger_setup_fixture.error.assert_any_call("Le pipeline de gestion des dépendances Python a échoué.")
    
    # L'étape de mock JPype ne doit pas être appelée si l'installation des deps échoue
    mock_setup_jpype.assert_not_called()
    
    mock_logger_setup_fixture.error.assert_any_call("Le pipeline de configuration de l'environnement de test a rencontré des erreurs.")

@patch('argumentation_analysis.core.pipelines.setup_pipeline.run_download_jars_pipeline')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.run_dependency_installation_pipeline')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.setup_jpype_mock')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.Path')
def test_run_setup_pipeline_jpype_mock_fails(
    mock_path_class,
    mock_setup_jpype,
    mock_run_dep_install,
    mock_run_download_jars,
    mock_logger_setup_fixture
):
    """
    Teste le cas où la configuration du mock JPype échoue.
    Le pipeline global doit retourner False.
    """
    mock_run_download_jars.return_value = True # Téléchargement OK
    mock_run_dep_install.return_value = True   # Installation des dépendances OK
    
    error_message = "JPype mock setup error"
    mock_setup_jpype.side_effect = Exception(error_message) # Mock JPype échoue

    mock_config_path_obj = MagicMock(spec=Path)
    mock_config_path_obj.exists.return_value = True
    mock_req_path_obj = MagicMock(spec=Path)

    def path_side_effect(p_arg):
        if p_arg == TEST_CONFIG_PATH: return mock_config_path_obj
        if p_arg == TEST_REQ_PATH: return mock_req_path_obj
        return MagicMock(spec=Path)
    mock_path_class.side_effect = path_side_effect
    mock_path_class.return_value = MagicMock(spec=Path)

    result = run_test_environment_setup_pipeline(
        config_path=TEST_CONFIG_PATH,
        requirements_path=TEST_REQ_PATH,
        mock_jpype=True, # Activer le mock JPype
        venv_path=TEST_VENV_PATH,
        project_root=TEST_PROJECT_ROOT
    )

    assert result is False # Échec global
    mock_run_download_jars.assert_called_once()
    mock_run_dep_install.assert_called_once()
    mock_setup_jpype.assert_called_once() # Doit être appelé
    
    mock_logger_setup_fixture.error.assert_any_call(f"Erreur lors de la configuration du mock JPype: {error_message}")
    mock_logger_setup_fixture.error.assert_any_call("Le pipeline de configuration de l'environnement de test a rencontré des erreurs.")

@patch('argumentation_analysis.core.pipelines.setup_pipeline.run_download_jars_pipeline')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.run_dependency_installation_pipeline')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.setup_jpype_mock')
@patch('argumentation_analysis.core.pipelines.setup_pipeline.Path')
def test_run_setup_pipeline_config_file_not_found(
    mock_path_class,
    mock_setup_jpype,
    mock_run_dep_install,
    mock_run_download_jars,
    mock_logger_setup_fixture
):
    """
    Teste le cas où config_path est fourni mais le fichier de configuration n'existe pas.
    L'étape de téléchargement des JARs doit être ignorée, mais le pipeline continue
    et peut réussir si les autres étapes réussissent.
    """
    mock_run_dep_install.return_value = True # Installation des dépendances OK
    # mock_run_download_jars ne devrait pas être appelé si le fichier de config n'existe pas
    # mock_setup_jpype ne sera pas appelé si mock_jpype=False (par défaut pour ce test)

    mock_config_path_obj = MagicMock(spec=Path)
    mock_config_path_obj.exists.return_value = False # Le fichier de config N'EXISTE PAS
    mock_req_path_obj = MagicMock(spec=Path)

    def path_side_effect(p_arg):
        if p_arg == TEST_CONFIG_PATH: return mock_config_path_obj
        if p_arg == TEST_REQ_PATH: return mock_req_path_obj
        return MagicMock(spec=Path)
    mock_path_class.side_effect = path_side_effect
    mock_path_class.return_value = MagicMock(spec=Path)

    result = run_test_environment_setup_pipeline(
        config_path=TEST_CONFIG_PATH, # Fournir un config_path
        requirements_path=TEST_REQ_PATH,
        mock_jpype=False, # JPype mock désactivé pour ce test
        venv_path=TEST_VENV_PATH,
        project_root=TEST_PROJECT_ROOT
    )

    # Le pipeline peut réussir globalement si le fichier de config manquant n'est pas critique
    # et que les autres étapes (installation des deps) réussissent.
    # La logique actuelle du code source logge un warning mais ne met pas overall_success à False.
    assert result is True
    
    mock_config_path_obj.exists.assert_called_once()
    mock_logger_setup_fixture.warning.assert_any_call(f"Fichier de configuration {mock_config_path_obj} non trouvé. Étape de téléchargement des JARs ignorée.")
    mock_run_download_jars.assert_not_called() # Ne doit pas être appelé

    # Les étapes suivantes (installation des deps) doivent s'exécuter
    mock_run_dep_install.assert_called_once()
    mock_setup_jpype.assert_not_called() # Car mock_jpype=False
    
    mock_logger_setup_fixture.info.assert_any_call("Pipeline de configuration de l'environnement de test terminé avec succès.")
# - Test où la configuration du mock JPype échoue.
# - Test où config_path est fourni mais le fichier n'existe pas.