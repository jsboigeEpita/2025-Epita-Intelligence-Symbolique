# tests/unit/project_core/pipelines/test_archival_pipeline.py
"""
Tests unitaires pour le pipeline d'archivage (archival_pipeline).
"""
import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from argumentation_analysis.pipelines.archival_pipeline import run_archival_pipeline

# Constantes pour les chemins de test
TEST_SOURCE_DIR = "test_source"
TEST_ARCHIVE_BASE_DIR = "test_archive_base"

@pytest.fixture
def mock_logger():
    """Fixture pour mocker le logger retourné par setup_logging."""
    logger = MagicMock()
    # Configurez les méthodes de logging si nécessaire, par exemple:
    # logger.info = MagicMock()
    # logger.error = MagicMock()
    # logger.debug = MagicMock()
    return logger

@pytest.fixture
def mock_path_obj():
    """Fixture pour mocker un objet Path individuel."""
    path_mock = MagicMock(spec=Path)
    path_mock.is_file.return_value = True # Par défaut, simule un fichier
    path_mock.name = "test_file.txt"
    path_mock.__str__.return_value = str(path_mock.name)
    return path_mock

@patch('argumentation_analysis.pipelines.archival_pipeline.setup_logging')
@patch('argumentation_analysis.pipelines.archival_pipeline.check_path_exists')
@patch('argumentation_analysis.pipelines.archival_pipeline.create_archive_path')
@patch('argumentation_analysis.pipelines.archival_pipeline.archive_file')
@patch('argumentation_analysis.pipelines.archival_pipeline.Path')
def test_run_archival_pipeline_success_no_files(
    mock_path_class,
    mock_archive_file,
    mock_create_archive_path,
    mock_check_path_exists,
    mock_setup_logging,
    mock_logger # Utilisation de la fixture pour le logger
):
    """
    Teste le pipeline d'archivage dans un scénario de succès où aucun fichier ne correspond au pattern.
    """
    # Configuration des mocks
    mock_setup_logging.return_value = mock_logger
    
    # Simuler Path() pour source_dir et archive_base_dir
    mock_source_dir_path = MagicMock(spec=Path)
    mock_archive_base_dir_path = MagicMock(spec=Path)
    
    # Configurer rglob pour ne retourner aucun fichier
    mock_source_dir_path.rglob.return_value = []
    
    # Path() doit retourner nos mocks spécifiques quand appelé avec les bons arguments
    def path_side_effect(path_arg):
        if str(path_arg) == TEST_SOURCE_DIR:
            return mock_source_dir_path
        if str(path_arg) == TEST_ARCHIVE_BASE_DIR:
            return mock_archive_base_dir_path
        return MagicMock(spec=Path) # Fallback pour d'autres appels à Path()
        
    mock_path_class.side_effect = path_side_effect
    mock_path_class.return_value = MagicMock(spec=Path) # Comportement par défaut si side_effect n'est pas déclenché

    # Appel de la fonction à tester
    run_archival_pipeline(
        source_dir=TEST_SOURCE_DIR,
        archive_base_dir=TEST_ARCHIVE_BASE_DIR,
        file_pattern="*.txt",
        preserve_levels=1,
        log_level_str="INFO"
    )

    # Vérifications
    mock_setup_logging.assert_called_once_with("INFO", "archival_pipeline")
    mock_logger.info.assert_any_call("Démarrage du pipeline d'archivage.")
    
    # check_path_exists doit être appelé pour source_dir et archive_base_dir
    expected_check_calls = [
        call(mock_source_dir_path, "répertoire source", is_dir=True),
        call(mock_archive_base_dir_path, "répertoire de base d'archivage", is_dir=True)
    ]
    mock_check_path_exists.assert_has_calls(expected_check_calls, any_order=False) # L'ordre est important ici

    mock_logger.info.assert_any_call(f"Répertoire source: {mock_source_dir_path}")
    mock_logger.info.assert_any_call(f"Répertoire de base d'archivage: {mock_archive_base_dir_path}")
    mock_logger.info.assert_any_call("Motif de fichier: *.txt, Niveaux à préserver: 1")

    mock_source_dir_path.rglob.assert_called_once_with("*.txt")
    
    # Aucune fonction d'archivage ne doit être appelée si aucun fichier n'est trouvé
    mock_create_archive_path.assert_not_called()
    mock_archive_file.assert_not_called()

    mock_logger.info.assert_any_call(
        "Pipeline d'archivage terminé. 0 fichier(s) archivé(s) sur 0 élément(s) traité(s) correspondant au motif."
    )

@patch('argumentation_analysis.pipelines.archival_pipeline.setup_logging')
@patch('argumentation_analysis.pipelines.archival_pipeline.check_path_exists')
@patch('argumentation_analysis.pipelines.archival_pipeline.create_archive_path')
@patch('argumentation_analysis.pipelines.archival_pipeline.archive_file')
@patch('argumentation_analysis.pipelines.archival_pipeline.Path')
def test_run_archival_pipeline_success_one_file(
    mock_path_class,
    mock_archive_file,
    mock_create_archive_path,
    mock_check_path_exists,
    mock_setup_logging,
    mock_logger, # Utilisation de la fixture pour le logger
    mock_path_obj # Utilisation de la fixture pour un objet Path mocké
):
    """
    Teste le pipeline d'archivage dans un scénario de succès où un fichier est archivé.
    """
    # Configuration des mocks
    mock_setup_logging.return_value = mock_logger
    
    mock_source_file = mock_path_obj # Utilise la fixture
    mock_source_file.name = "file1.txt"
    mock_source_file.__str__.return_value = f"{TEST_SOURCE_DIR}/{mock_source_file.name}"


    mock_source_dir_path = MagicMock(spec=Path)
    mock_archive_base_dir_path = MagicMock(spec=Path)
    
    # Configurer rglob pour retourner un fichier mocké
    mock_source_dir_path.rglob.return_value = [mock_source_file]
    
    def path_side_effect(path_arg):
        if str(path_arg) == TEST_SOURCE_DIR:
            return mock_source_dir_path
        if str(path_arg) == TEST_ARCHIVE_BASE_DIR:
            return mock_archive_base_dir_path
        # Pour les appels Path(source_file) dans la boucle, nous voulons retourner le mock lui-même
        # Cependant, create_archive_path attend des objets Path, pas des strings.
        # Le mock_source_file est déjà un MagicMock(spec=Path)
        return MagicMock(spec=Path)
        
    mock_path_class.side_effect = path_side_effect
    # Comportement par défaut si side_effect n'est pas déclenché pour Path()
    # ou pour les instances créées à partir de chaînes (comme dans create_archive_path si on ne mocke pas bien)
    mock_path_class.return_value = MagicMock(spec=Path)


    mock_target_archive_path = MagicMock(spec=Path)
    mock_target_archive_path.__str__.return_value = f"{TEST_ARCHIVE_BASE_DIR}/preserved_level/{mock_source_file.name}"
    mock_create_archive_path.return_value = mock_target_archive_path

    # Appel de la fonction à tester
    run_archival_pipeline(
        source_dir=TEST_SOURCE_DIR,
        archive_base_dir=TEST_ARCHIVE_BASE_DIR,
        file_pattern="*.txt",
        preserve_levels=1,
        log_level_str="DEBUG"
    )

    # Vérifications
    mock_setup_logging.assert_called_once_with("DEBUG", "archival_pipeline")
    mock_check_path_exists.assert_any_call(mock_source_dir_path, "répertoire source", is_dir=True)
    mock_check_path_exists.assert_any_call(mock_archive_base_dir_path, "répertoire de base d'archivage", is_dir=True)

    mock_source_dir_path.rglob.assert_called_once_with("*.txt")
    mock_source_file.is_file.assert_called_once() # Vérifie qu'on a testé si c'est un fichier

    mock_logger.debug.assert_any_call(f"Traitement du fichier source: {mock_source_file}")

    mock_create_archive_path.assert_called_once_with(
        source_file_path=mock_source_file,
        source_base_dir=mock_source_dir_path,
        archive_base_dir=mock_archive_base_dir_path,
        preserve_levels=1
    )
    mock_logger.debug.assert_any_call(f"Chemin d'archivage calculé: {mock_target_archive_path}")

    mock_archive_file.assert_called_once_with(mock_source_file, mock_target_archive_path, create_parent_dirs=True)
    mock_logger.info.assert_any_call(f"Archivé: '{mock_source_file}' -> '{mock_target_archive_path}'")

    mock_logger.info.assert_any_call(
        "Pipeline d'archivage terminé. 1 fichier(s) archivé(s) sur 1 élément(s) traité(s) correspondant au motif."
    )

@patch('argumentation_analysis.pipelines.archival_pipeline.setup_logging')
@patch('argumentation_analysis.pipelines.archival_pipeline.check_path_exists')
@patch('argumentation_analysis.pipelines.archival_pipeline.Path')
def test_run_archival_pipeline_fail_source_dir_not_found(
    mock_path_class,
    mock_check_path_exists,
    mock_setup_logging,
    mock_logger
):
    """
    Teste l'échec du pipeline si le répertoire source n'est pas trouvé.
    """
    mock_setup_logging.return_value = mock_logger
    
    mock_source_dir_path = MagicMock(spec=Path)
    mock_archive_base_dir_path = MagicMock(spec=Path)

    def path_side_effect(path_arg):
        if str(path_arg) == TEST_SOURCE_DIR:
            return mock_source_dir_path
        if str(path_arg) == TEST_ARCHIVE_BASE_DIR:
            return mock_archive_base_dir_path
        return MagicMock(spec=Path)
    mock_path_class.side_effect = path_side_effect
    mock_path_class.return_value = MagicMock(spec=Path)

    # Simuler l'échec de check_path_exists pour le répertoire source
    error_message = "Répertoire source introuvable"
    mock_check_path_exists.side_effect = [
        FileNotFoundError(error_message), # Pour source_dir
        None # Pour archive_base_dir (ou une autre exception si on veut être plus précis)
    ]

    run_archival_pipeline(
        source_dir=TEST_SOURCE_DIR,
        archive_base_dir=TEST_ARCHIVE_BASE_DIR,
        file_pattern="*.txt",
        preserve_levels=1
    )

    mock_check_path_exists.assert_any_call(mock_source_dir_path, "répertoire source", is_dir=True)
    # S'assurer que le pipeline logge l'erreur et s'arrête (ou gère l'erreur comme prévu)
    mock_logger.error.assert_any_call(
        f"Erreur de configuration du pipeline (chemin non trouvé): {error_message}", exc_info=True
    )
    # Les étapes suivantes ne devraient pas être appelées
    assert mock_source_dir_path.rglob.call_count == 0


@patch('argumentation_analysis.pipelines.archival_pipeline.setup_logging')
@patch('argumentation_analysis.pipelines.archival_pipeline.check_path_exists')
@patch('argumentation_analysis.pipelines.archival_pipeline.Path')
def test_run_archival_pipeline_fail_archive_dir_not_found(
    mock_path_class,
    mock_check_path_exists,
    mock_setup_logging,
    mock_logger
):
    """
    Teste l'échec du pipeline si le répertoire d'archive de base n'est pas trouvé.
    """
    mock_setup_logging.return_value = mock_logger

    mock_source_dir_path = MagicMock(spec=Path)
    mock_archive_base_dir_path = MagicMock(spec=Path)

    def path_side_effect(path_arg):
        if str(path_arg) == TEST_SOURCE_DIR:
            return mock_source_dir_path
        if str(path_arg) == TEST_ARCHIVE_BASE_DIR:
            return mock_archive_base_dir_path
        return MagicMock(spec=Path)
    mock_path_class.side_effect = path_side_effect
    mock_path_class.return_value = MagicMock(spec=Path)

    # Simuler l'échec de check_path_exists pour le répertoire d'archive
    error_message = "Répertoire d'archive introuvable"
    mock_check_path_exists.side_effect = [
        None, # Succès pour source_dir
        FileNotFoundError(error_message) # Échec pour archive_base_dir
    ]

    run_archival_pipeline(
        source_dir=TEST_SOURCE_DIR,
        archive_base_dir=TEST_ARCHIVE_BASE_DIR,
        file_pattern="*.txt",
        preserve_levels=1
    )

    mock_check_path_exists.assert_any_call(mock_source_dir_path, "répertoire source", is_dir=True)
    mock_check_path_exists.assert_any_call(mock_archive_base_dir_path, "répertoire de base d'archivage", is_dir=True)
    
    mock_logger.error.assert_any_call(
        f"Erreur de configuration du pipeline (chemin non trouvé): {error_message}", exc_info=True
    )
    assert mock_source_dir_path.rglob.call_count == 0

@patch('argumentation_analysis.pipelines.archival_pipeline.setup_logging')
@patch('argumentation_analysis.pipelines.archival_pipeline.check_path_exists')
@patch('argumentation_analysis.pipelines.archival_pipeline.create_archive_path')
@patch('argumentation_analysis.pipelines.archival_pipeline.archive_file')
@patch('argumentation_analysis.pipelines.archival_pipeline.Path')
def test_run_archival_pipeline_error_in_create_archive_path(
    mock_path_class,
    mock_archive_file,
    mock_create_archive_path,
    mock_check_path_exists,
    mock_setup_logging,
    mock_logger,
    mock_path_obj
):
    """
    Teste la gestion d'erreur si create_archive_path lève une exception.
    Le pipeline doit logger l'erreur et continuer avec les autres fichiers.
    """
    mock_setup_logging.return_value = mock_logger
    mock_source_file1 = mock_path_obj
    mock_source_file1.name = "file1.txt"
    mock_source_file1.__str__.return_value = f"{TEST_SOURCE_DIR}/{mock_source_file1.name}"
    
    mock_source_file2 = MagicMock(spec=Path)
    mock_source_file2.is_file.return_value = True
    mock_source_file2.name = "file2.txt"
    mock_source_file2.__str__.return_value = f"{TEST_SOURCE_DIR}/{mock_source_file2.name}"

    mock_source_dir_path = MagicMock(spec=Path)
    mock_archive_base_dir_path = MagicMock(spec=Path)
    mock_source_dir_path.rglob.return_value = [mock_source_file1, mock_source_file2]

    def path_side_effect(path_arg):
        if str(path_arg) == TEST_SOURCE_DIR: return mock_source_dir_path
        if str(path_arg) == TEST_ARCHIVE_BASE_DIR: return mock_archive_base_dir_path
        return MagicMock(spec=Path)
    mock_path_class.side_effect = path_side_effect
    mock_path_class.return_value = MagicMock(spec=Path)

    error_message = "Erreur de création de chemin"
    # Pour le deuxième appel réussi à create_archive_path
    mock_target_path_file2 = MagicMock(spec=Path)
    mock_target_path_file2.__str__.return_value = f"{TEST_ARCHIVE_BASE_DIR}/file2_archived.txt"
    # Faire en sorte que create_archive_path échoue pour le premier fichier et réussisse pour le second
    mock_create_archive_path.side_effect = [
        Exception(error_message),  # Le premier appel lèvera une exception
        mock_target_path_file2     # Le deuxième appel retournera le chemin mocké
    ]


    run_archival_pipeline(
        source_dir=TEST_SOURCE_DIR,
        archive_base_dir=TEST_ARCHIVE_BASE_DIR,
        file_pattern="*.txt",
        preserve_levels=1
    )

    mock_logger.error.assert_any_call(
        f"Erreur lors de l'archivage du fichier '{mock_source_file1}': {error_message}", exc_info=True
    )
    # archive_file ne doit pas être appelé pour le fichier en erreur
    # mais doit être appelé pour le fichier qui réussit
    mock_archive_file.assert_called_once_with(mock_source_file2, mock_target_path_file2, create_parent_dirs=True)
    mock_logger.info.assert_any_call(f"Archivé: '{mock_source_file2}' -> '{mock_target_path_file2}'")
    mock_logger.info.assert_any_call(
        "Pipeline d'archivage terminé. 1 fichier(s) archivé(s) sur 2 élément(s) traité(s) correspondant au motif."
    )


@patch('argumentation_analysis.pipelines.archival_pipeline.setup_logging')
@patch('argumentation_analysis.pipelines.archival_pipeline.check_path_exists')
@patch('argumentation_analysis.pipelines.archival_pipeline.create_archive_path')
@patch('argumentation_analysis.pipelines.archival_pipeline.archive_file')
@patch('argumentation_analysis.pipelines.archival_pipeline.Path')
def test_run_archival_pipeline_error_in_archive_file(
    mock_path_class,
    mock_archive_file,
    mock_create_archive_path,
    mock_check_path_exists,
    mock_setup_logging,
    mock_logger,
    mock_path_obj
):
    """
    Teste la gestion d'erreur si archive_file lève une exception.
    Le pipeline doit logger l'erreur et continuer.
    """
    mock_setup_logging.return_value = mock_logger
    mock_source_file1 = mock_path_obj
    mock_source_file1.name = "file1.txt"
    mock_source_file1.__str__.return_value = f"{TEST_SOURCE_DIR}/{mock_source_file1.name}"

    mock_source_file2 = MagicMock(spec=Path)
    mock_source_file2.is_file.return_value = True
    mock_source_file2.name = "file2.txt"
    mock_source_file2.__str__.return_value = f"{TEST_SOURCE_DIR}/{mock_source_file2.name}"

    mock_source_dir_path = MagicMock(spec=Path)
    mock_archive_base_dir_path = MagicMock(spec=Path)
    mock_source_dir_path.rglob.return_value = [mock_source_file1, mock_source_file2]

    def path_side_effect(path_arg):
        if str(path_arg) == TEST_SOURCE_DIR: return mock_source_dir_path
        if str(path_arg) == TEST_ARCHIVE_BASE_DIR: return mock_archive_base_dir_path
        return MagicMock(spec=Path)
    mock_path_class.side_effect = path_side_effect
    mock_path_class.return_value = MagicMock(spec=Path)

    mock_target_path_file1 = MagicMock(spec=Path)
    mock_target_path_file1.__str__.return_value = f"{TEST_ARCHIVE_BASE_DIR}/file1_archived.txt"
    mock_target_path_file2 = MagicMock(spec=Path)
    mock_target_path_file2.__str__.return_value = f"{TEST_ARCHIVE_BASE_DIR}/file2_archived.txt"
    
    mock_create_archive_path.side_effect = [mock_target_path_file1, mock_target_path_file2]

    error_message = "Erreur d'archivage IO"
    # archive_file échoue pour file1, réussit pour file2
    mock_archive_file.side_effect = [
        Exception(error_message), # Le premier appel lèvera une exception
        None                      # Le deuxième appel ne fera rien (comportement de succès)
    ]


    run_archival_pipeline(
        source_dir=TEST_SOURCE_DIR,
        archive_base_dir=TEST_ARCHIVE_BASE_DIR,
        file_pattern="*.txt",
        preserve_levels=1
    )

    mock_logger.error.assert_any_call(
        f"Erreur lors de l'archivage du fichier '{mock_source_file1}': {error_message}", exc_info=True
    )
    # Vérifier que create_archive_path a été appelé pour les deux
    assert mock_create_archive_path.call_count == 2
    # Vérifier que archive_file a été appelé pour les deux (même si l'un a échoué)
    assert mock_archive_file.call_count == 2
    mock_archive_file.assert_any_call(mock_source_file1, mock_target_path_file1, create_parent_dirs=True)
    mock_archive_file.assert_any_call(mock_source_file2, mock_target_path_file2, create_parent_dirs=True)

    mock_logger.info.assert_any_call(f"Archivé: '{mock_source_file2}' -> '{mock_target_path_file2}'")
    mock_logger.info.assert_any_call(
        "Pipeline d'archivage terminé. 1 fichier(s) archivé(s) sur 2 élément(s) traité(s) correspondant au motif."
    )

@patch('argumentation_analysis.pipelines.archival_pipeline.setup_logging')
@patch('argumentation_analysis.pipelines.archival_pipeline.check_path_exists')
@patch('argumentation_analysis.pipelines.archival_pipeline.create_archive_path')
@patch('argumentation_analysis.pipelines.archival_pipeline.archive_file')
@patch('argumentation_analysis.pipelines.archival_pipeline.Path')
def test_run_archival_pipeline_item_is_not_file(
    mock_path_class,
    mock_archive_file,
    mock_create_archive_path,
    mock_check_path_exists,
    mock_setup_logging,
    mock_logger # Utilisation de la fixture logger
):
    """
    Teste le comportement lorsque rglob retourne un élément qui n'est pas un fichier.
    Cet élément doit être ignoré et le pipeline doit continuer.
    """
    mock_setup_logging.return_value = mock_logger

    mock_item_dir = MagicMock(spec=Path)
    mock_item_dir.is_file.return_value = False # Simule un répertoire
    mock_item_dir.name = "a_directory"
    mock_item_dir.__str__.return_value = f"{TEST_SOURCE_DIR}/{mock_item_dir.name}"
    
    mock_source_file = MagicMock(spec=Path)
    mock_source_file.is_file.return_value = True # Simule un fichier
    mock_source_file.name = "real_file.txt"
    mock_source_file.__str__.return_value = f"{TEST_SOURCE_DIR}/{mock_source_file.name}"

    mock_source_dir_path = MagicMock(spec=Path)
    mock_archive_base_dir_path = MagicMock(spec=Path)
    
    # rglob retourne le répertoire puis le fichier
    mock_source_dir_path.rglob.return_value = [mock_item_dir, mock_source_file]

    def path_side_effect(path_arg):
        if str(path_arg) == TEST_SOURCE_DIR: return mock_source_dir_path
        if str(path_arg) == TEST_ARCHIVE_BASE_DIR: return mock_archive_base_dir_path
        return MagicMock(spec=Path)
    mock_path_class.side_effect = path_side_effect
    mock_path_class.return_value = MagicMock(spec=Path)

    mock_target_archive_path_for_file = MagicMock(spec=Path)
    mock_target_archive_path_for_file.__str__.return_value = f"{TEST_ARCHIVE_BASE_DIR}/archived_{mock_source_file.name}"
    mock_create_archive_path.return_value = mock_target_archive_path_for_file

    run_archival_pipeline(
        source_dir=TEST_SOURCE_DIR,
        archive_base_dir=TEST_ARCHIVE_BASE_DIR,
        file_pattern="*", # Un pattern large pour s'assurer que rglob retourne les deux
        preserve_levels=1,
        log_level_str="DEBUG" # Pour vérifier les logs de debug
    )

    # Vérifier que is_file a été appelé pour les deux éléments
    mock_item_dir.is_file.assert_called_once()
    mock_source_file.is_file.assert_called_once()

    # Vérifier que le répertoire est loggué comme ignoré
    mock_logger.debug.assert_any_call(f"Ignoré (n'est pas un fichier): {mock_item_dir}")
    
    # Vérifier que le fichier est traité et archivé
    mock_logger.debug.assert_any_call(f"Traitement du fichier source: {mock_source_file}")
    mock_create_archive_path.assert_called_once_with(
        source_file_path=mock_source_file,
        source_base_dir=mock_source_dir_path,
        archive_base_dir=mock_archive_base_dir_path,
        preserve_levels=1
    )
    mock_archive_file.assert_called_once_with(mock_source_file, mock_target_archive_path_for_file, create_parent_dirs=True)
    mock_logger.info.assert_any_call(f"Archivé: '{mock_source_file}' -> '{mock_target_archive_path_for_file}'")

    # Vérifier le message final du logger
    mock_logger.info.assert_any_call(
        "Pipeline d'archivage terminé. 1 fichier(s) archivé(s) sur 2 élément(s) traité(s) correspondant au motif."
    )

# TODO: Ajouter plus de cas de test:
# 7. Différents preserve_levels.
# 8. Différents file_patterns.