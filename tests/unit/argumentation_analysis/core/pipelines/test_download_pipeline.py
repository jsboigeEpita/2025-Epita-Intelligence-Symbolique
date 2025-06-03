# tests/unit/project_core/pipelines/test_download_pipeline.py
"""
Tests unitaires pour le pipeline de téléchargement de JARs.
"""
import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import logging

# Assurez-vous que le module testé est importable
from argumentation_analysis.core.pipelines.download_pipeline import run_download_jars_pipeline

DEST_DIR = Path("test_download_dest")

# Configuration minimale pour les JARs de test
JAR1_CONFIG = {"name": "jar1.jar", "url": "http://example.com/jar1.jar", "expected_size": 1024}
JAR2_CONFIG = {"name": "jar2.jar", "url": "http://example.com/jar2.jar", "expected_size": 2048}
INVALID_JAR_CONFIG = {"name": "invalid.jar"} # URL manquante

@pytest.fixture
def mock_logger_download_fixture():
    """Fixture pour mocker le logger utilisé dans le pipeline de téléchargement."""
    # Utiliser le vrai module logging mais patcher ses fonctions au niveau du module testé
    # ou patcher l'instance de logger si elle est accessible.
    # Ici, on va patcher les fonctions de logging au niveau du module 'download_pipeline'
    with patch('argumentation_analysis.core.pipelines.download_pipeline.logging') as mock_log_module:
        yield mock_log_module

@patch('argumentation_analysis.core.pipelines.download_pipeline.download_file')
@patch('argumentation_analysis.core.pipelines.download_pipeline.Path') # Pour mocker Path() et ses instances
def test_run_download_pipeline_success_all_jars(
    mock_path_class,
    mock_download_file,
    mock_logger_download_fixture # Utilise la fixture pour le logger
):
    """
    Teste le succès du pipeline quand tous les JARs sont téléchargés avec succès.
    """
    mock_dest_dir_path = MagicMock(spec=Path)
    mock_dest_dir_path.exists.return_value = False # Simule que les fichiers n'existent pas
    
    # Path(DEST_DIR) retourne notre mock_dest_dir_path
    # Et mock_dest_dir_path / "jar_name" retourne un autre mock Path pour le fichier
    def path_side_effect(arg):
        if arg == DEST_DIR:
            return mock_dest_dir_path
        # Pour les fichiers individuels, retourner un nouveau mock à chaque fois
        # ou un mock préconfiguré si nécessaire.
        file_mock = MagicMock(spec=Path)
        file_mock.exists.return_value = False # Par défaut, le fichier n'existe pas
        file_mock.name = str(arg).split('/')[-1] # Extrait le nom du fichier
        return file_mock

    mock_path_class.side_effect = path_side_effect
    # Assurer que Path() lui-même retourne un mock si appelé directement
    mock_path_class.return_value = mock_dest_dir_path


    mock_download_file.return_value = True # Simule un téléchargement réussi

    jars_to_download = [JAR1_CONFIG, JAR2_CONFIG]
    result = run_download_jars_pipeline(jars_to_download, DEST_DIR, force_download=True)

    assert result is True
    mock_dest_dir_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    # Vérifier les appels à download_file
    calls_download = [
        call(url=JAR1_CONFIG["url"], destination_path=ANY, expected_size=JAR1_CONFIG["expected_size"]),
        call(url=JAR2_CONFIG["url"], destination_path=ANY, expected_size=JAR2_CONFIG["expected_size"])
    ]
    mock_download_file.assert_has_calls(calls_download, any_order=False) # L'ordre est important
    assert mock_download_file.call_count == 2
    
    # Vérifier les logs (exemples)
    mock_logger_download_fixture.info.assert_any_call(f"Début du pipeline de téléchargement des JARs vers {mock_dest_dir_path}.")
    mock_logger_download_fixture.info.assert_any_call(f"✅ {JAR1_CONFIG['name']} téléchargé avec succès dans {ANY}.")
    mock_logger_download_fixture.info.assert_any_call(f"✅ {JAR2_CONFIG['name']} téléchargé avec succès dans {ANY}.")
    mock_logger_download_fixture.info.assert_any_call("✅ Tous les JARs configurés ont été traités avec succès.")

@patch('argumentation_analysis.core.pipelines.download_pipeline.download_file')
@patch('argumentation_analysis.core.pipelines.download_pipeline.Path')
def test_run_download_pipeline_no_jars_to_download(
    mock_path_class,
    mock_download_file,
    mock_logger_download_fixture
):
    """
    Teste le pipeline quand la liste des JARs à télécharger est vide.
    """
    result = run_download_jars_pipeline([], DEST_DIR)
    assert result is True
    mock_logger_download_fixture.info.assert_any_call("Aucun JAR n'est configuré pour le téléchargement dans le pipeline.")
    # mkdir ne devrait pas être appelé si la liste est vide au début
    # Cependant, la logique actuelle crée le répertoire même si la liste est vide,
    # ce qui est acceptable. Si on voulait changer ça, le test devrait être ajusté.
    # mock_path_class.return_value.mkdir.assert_not_called() # Ou assert_called_once si on le crée quand même
    mock_download_file.assert_not_called()

@patch('argumentation_analysis.core.pipelines.download_pipeline.download_file')
@patch('argumentation_analysis.core.pipelines.download_pipeline.Path')
def test_run_download_pipeline_skip_existing_files(
    mock_path_class,
    mock_download_file,
    mock_logger_download_fixture
):
    """
    Teste que le pipeline skippe les fichiers existants si force_download est False.
    """
    mock_dest_dir_path = MagicMock(spec=Path)
    
    # Simuler que les fichiers existent déjà
    mock_file1_path = MagicMock(spec=Path)
    mock_file1_path.exists.return_value = True
    mock_file1_path.name = JAR1_CONFIG["name"]

    mock_file2_path = MagicMock(spec=Path)
    mock_file2_path.exists.return_value = True
    mock_file2_path.name = JAR2_CONFIG["name"]

    # Path(DEST_DIR) retourne mock_dest_dir_path
    # mock_dest_dir_path / "jar_name" retourne le mock de fichier correspondant
    def path_side_effect(arg):
        if arg == DEST_DIR:
            return mock_dest_dir_path
        elif str(arg).endswith(JAR1_CONFIG["name"]): # Check based on name
            return mock_file1_path
        elif str(arg).endswith(JAR2_CONFIG["name"]):
            return mock_file2_path
        return MagicMock(spec=Path) # Fallback

    mock_path_class.side_effect = path_side_effect
    mock_path_class.return_value = mock_dest_dir_path # Pour l'appel Path(destination_dir)

    jars_to_download = [JAR1_CONFIG, JAR2_CONFIG]
    result = run_download_jars_pipeline(jars_to_download, DEST_DIR, force_download=False)

    assert result is True
    mock_dest_dir_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    # download_file ne doit pas être appelé
    mock_download_file.assert_not_called()
    
    # Vérifier les logs de skip
    mock_logger_download_fixture.info.assert_any_call(f"Le fichier {JAR1_CONFIG['name']} existe déjà dans {mock_dest_dir_path} et force_download est False. Skip.")
    mock_logger_download_fixture.info.assert_any_call(f"Le fichier {JAR2_CONFIG['name']} existe déjà dans {mock_dest_dir_path} et force_download est False. Skip.")
    mock_logger_download_fixture.info.assert_any_call("✅ Tous les JARs configurés ont été traités avec succès.")

@patch('argumentation_analysis.core.pipelines.download_pipeline.download_file')
@patch('argumentation_analysis.core.pipelines.download_pipeline.Path')
def test_run_download_pipeline_one_jar_fails_download(
    mock_path_class,
    mock_download_file,
    mock_logger_download_fixture
):
    """
    Teste le pipeline quand un JAR échoue au téléchargement (download_file retourne False).
    Le pipeline doit continuer et retourner False globalement.
    """
    mock_dest_dir_path = MagicMock(spec=Path)
    mock_file_path = MagicMock(spec=Path)
    mock_file_path.exists.return_value = False
    
    def path_side_effect(arg):
        if arg == DEST_DIR: return mock_dest_dir_path
        return mock_file_path # Tous les fichiers utilisent ce mock pour exists()
    mock_path_class.side_effect = path_side_effect
    mock_path_class.return_value = mock_dest_dir_path

    # Simuler échec pour le premier JAR, succès pour le second
    mock_download_file.side_effect = [False, True]

    jars_to_download = [JAR1_CONFIG, JAR2_CONFIG]
    result = run_download_jars_pipeline(jars_to_download, DEST_DIR, force_download=True)

    assert result is False # Échec global
    assert mock_download_file.call_count == 2
    
    mock_logger_download_fixture.error.assert_any_call(f"❌ Échec du téléchargement de {JAR1_CONFIG['name']} depuis {JAR1_CONFIG['url']}.")
    mock_logger_download_fixture.info.assert_any_call(f"✅ {JAR2_CONFIG['name']} téléchargé avec succès dans {mock_file_path}.")
    mock_logger_download_fixture.error.assert_any_call(f"❌ Échec du traitement d'un ou plusieurs JARs. 1/{len(jars_to_download)} JARs traités avec un certain succès (téléchargés ou skippés).")

@patch('argumentation_analysis.core.pipelines.download_pipeline.download_file')
@patch('argumentation_analysis.core.pipelines.download_pipeline.Path')
def test_run_download_pipeline_one_jar_download_exception(
    mock_path_class,
    mock_download_file,
    mock_logger_download_fixture
):
    """
    Teste le pipeline quand download_file lève une exception pour un JAR.
    Le pipeline doit continuer et retourner False globalement.
    """
    mock_dest_dir_path = MagicMock(spec=Path)
    mock_file_path = MagicMock(spec=Path)
    mock_file_path.exists.return_value = False

    def path_side_effect(arg):
        if arg == DEST_DIR: return mock_dest_dir_path
        return mock_file_path
    mock_path_class.side_effect = path_side_effect
    mock_path_class.return_value = mock_dest_dir_path

    error_message = "Erreur réseau majeure"
    # Simuler exception pour le premier JAR, succès pour le second
    mock_download_file.side_effect = [Exception(error_message), True]

    jars_to_download = [JAR1_CONFIG, JAR2_CONFIG]
    result = run_download_jars_pipeline(jars_to_download, DEST_DIR, force_download=True)

    assert result is False # Échec global
    assert mock_download_file.call_count == 2
    
    mock_logger_download_fixture.error.assert_any_call(f"Une erreur inattendue est survenue lors du téléchargement de {JAR1_CONFIG['name']}: {error_message}")
    mock_logger_download_fixture.info.assert_any_call(f"✅ {JAR2_CONFIG['name']} téléchargé avec succès dans {mock_file_path}.")
    mock_logger_download_fixture.error.assert_any_call(f"❌ Échec du traitement d'un ou plusieurs JARs. 1/{len(jars_to_download)} JARs traités avec un certain succès (téléchargés ou skippés).")

@patch('argumentation_analysis.core.pipelines.download_pipeline.download_file')
@patch('argumentation_analysis.core.pipelines.download_pipeline.Path')
def test_run_download_pipeline_invalid_jar_config(
    mock_path_class,
    mock_download_file,
    mock_logger_download_fixture
):
    """
    Teste le pipeline avec une configuration de JAR invalide (nom ou URL manquant).
    Le JAR invalide doit être skippé, et le pipeline retourne False.
    """
    mock_dest_dir_path = MagicMock(spec=Path)
    mock_path_class.return_value = mock_dest_dir_path # Pour Path(DEST_DIR)

    jars_to_download = [INVALID_JAR_CONFIG, JAR1_CONFIG] # Un invalide, un valide
    
    # download_file ne sera appelé que pour le JAR valide
    mock_download_file.return_value = True

    result = run_download_jars_pipeline(jars_to_download, DEST_DIR, force_download=True)

    assert result is False # Échec global à cause de la config invalide
    mock_dest_dir_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    mock_logger_download_fixture.warning.assert_any_call(f"Informations incomplètes pour un JAR (nom ou URL manquant): {INVALID_JAR_CONFIG}. Ce JAR est ignoré.")
    
    # download_file ne doit être appelé que pour le JAR valide
    mock_download_file.assert_called_once_with(
        url=JAR1_CONFIG["url"], destination_path=ANY, expected_size=JAR1_CONFIG["expected_size"]
    )
    mock_logger_download_fixture.info.assert_any_call(f"✅ {JAR1_CONFIG['name']} téléchargé avec succès dans {ANY}.")
    # Le message final devrait refléter l'échec dû à la config invalide, même si un téléchargement a réussi.
    # La logique actuelle du code source pour le message final pourrait être affinée pour ce cas.
    # Pour l'instant, on vérifie que all_successful est False.
    # Le message exact dépend de la logique dans le code source.
    # Si un JAR valide est traité, et un invalide est skippé, all_successful devient False.
    # Le message sera "❌ Échec du traitement d'un ou plusieurs JARs..."
    mock_logger_download_fixture.error.assert_any_call(f"❌ Échec du traitement d'un ou plusieurs JARs. 1/{len(jars_to_download)} JARs traités avec un certain succès (téléchargés ou skippés).")


@patch('argumentation_analysis.core.pipelines.download_pipeline.download_file')
@patch('argumentation_analysis.core.pipelines.download_pipeline.Path')
def test_run_download_pipeline_mkdir_fails(
    mock_path_class,
    mock_download_file,
    mock_logger_download_fixture
):
    """
    Teste l'échec du pipeline si la création du répertoire de destination échoue.
    """
    mock_dest_dir_path = MagicMock(spec=Path)
    mock_path_class.return_value = mock_dest_dir_path
    
    error_message = "Permission refusée"
    mock_dest_dir_path.mkdir.side_effect = OSError(error_message)

    jars_to_download = [JAR1_CONFIG]
    
    with pytest.raises(OSError, match=error_message):
        run_download_jars_pipeline(jars_to_download, DEST_DIR, force_download=True)
    
    mock_dest_dir_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_logger_download_fixture.error.assert_any_call(f"Impossible de créer le répertoire de destination {mock_dest_dir_path}: {error_message}")
    mock_download_file.assert_not_called() # Le pipeline doit s'arrêter avant les téléchargements

# TODO:
# - Test avec une configuration de JAR invalide (nom ou URL manquant).
# - Test échec création répertoire de destination (mkdir lève OSError).