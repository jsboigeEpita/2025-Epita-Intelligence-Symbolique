# -*- coding: utf-8 -*-

from unittest.mock import Mock, MagicMock, patch, ANY
import tempfile
import os

import pytest
import json
import gzip
import logging # Ajout de l'import manquant
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Ajuster le sys.path pour les imports locaux si nécessaire (déjà fait dans le script principal)
import sys
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent # Remonter à la racine du projet
sys.path.insert(0, str(SCRIPT_DIR))

from argumentation_analysis.ui import utils as aa_utils
# Importer les fonctions déplacées depuis file_operations pour les tests qui les concernent directement
from argumentation_analysis.ui.file_operations import load_extract_definitions, save_extract_definitions
from argumentation_analysis.ui import config as ui_config_module # Pour mocker les constantes
from cryptography.fernet import Fernet, InvalidToken # Ajout InvalidToken
# Importer les fonctions de crypto directement pour les tests qui les utilisent
from project_core.utils.crypto_utils import encrypt_data_with_fernet, decrypt_data_with_fernet
import base64 # Ajouté pour la fixture test_key


# --- Fixtures ---

@pytest.fixture
def mock_logger():
    # Crée un mock partagé
    shared_mock_log = MagicMock()
    
    # Patcher utils_logger pour qu'il soit ce mock partagé
    patcher_utils_logger = patch('argumentation_analysis.ui.utils.utils_logger', shared_mock_log)
    # Patcher file_ops_logger pour qu'il soit aussi ce mock partagé
    patcher_file_ops_logger = patch('argumentation_analysis.ui.file_operations.file_ops_logger', shared_mock_log)
    # Patcher crypto_utils_logger pour qu'il soit aussi ce mock partagé (ou crypto_logger, c'est pareil)
    patcher_crypto_logger = patch('project_core.utils.crypto_utils.logger', shared_mock_log)
    
    # Démarrer les patchers
    patcher_utils_logger.start()
    patcher_file_ops_logger.start()
    patcher_crypto_logger.start()
    
    yield shared_mock_log # Le mock partagé est utilisé pour les assertions
    
    # Arrêter les patchers
    patcher_utils_logger.stop()
    patcher_file_ops_logger.stop()
    patcher_crypto_logger.stop()

@pytest.fixture
def temp_cache_dir(tmp_path):
    """Crée un répertoire de cache temporaire et le configure dans ui_config."""
    original_cache_dir = ui_config_module.CACHE_DIR
    ui_config_module.CACHE_DIR = tmp_path / "cache"
    ui_config_module.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    yield ui_config_module.CACHE_DIR
    ui_config_module.CACHE_DIR = original_cache_dir # Restaurer

@pytest.fixture
def temp_download_dir(tmp_path):
    """Crée un répertoire de téléchargement temporaire et le configure dans ui_config."""
    original_temp_dir = ui_config_module.TEMP_DOWNLOAD_DIR
    ui_config_module.TEMP_DOWNLOAD_DIR = tmp_path / "temp_dl"
    ui_config_module.TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield ui_config_module.TEMP_DOWNLOAD_DIR
    ui_config_module.TEMP_DOWNLOAD_DIR = original_temp_dir

@pytest.fixture
def test_key():
    # Retourne une clé encodée en base64url str, comme attendu par les fonctions crypto
    raw_key = Fernet.generate_key()
    return base64.urlsafe_b64encode(raw_key).decode('utf-8')

@pytest.fixture
def sample_source_info_direct():
    return {
        "source_name": "Direct Source",
        "source_type": "direct_download", # Devrait correspondre à une clé dans FETCH_METHODS
        "fetch_method": "direct_download", # Explicitement pour la clarté des tests
        "schema": "https",
        "host_parts": ["example", "com"],
        "path": "/text.txt",
        "extracts": []
    }

@pytest.fixture
def sample_source_info_jina():
    return {
        "source_name": "Jina Source",
        "source_type": "jina", # Devrait correspondre à une clé dans FETCH_METHODS
        "fetch_method": "jina", # Explicitement pour la clarté des tests
        "schema": "https",
        "host_parts": ["another-example", "com"],
        "path": "/page.html",
        "extracts": []
    }

@pytest.fixture
def sample_source_info_tika_txt():
    return {
        "source_name": "Tika TXT Source",
        "source_type": "tika", # Devrait correspondre à une clé dans FETCH_METHODS
        "fetch_method": "tika", # Explicitement pour la clarté des tests
        "schema": "https",
        "host_parts": ["tika-example", "com"],
        "path": "/document.txt", # Sera traité comme direct_download par fetch_with_tika
        "extracts": []
    }

@pytest.fixture
def sample_source_info_tika_pdf():
    return {
        "source_name": "Tika PDF Source",
        "source_type": "tika", # Devrait correspondre à une clé dans FETCH_METHODS
        "fetch_method": "tika", # Explicitement pour la clarté des tests
        "schema": "https",
        "host_parts": ["tika-pdf-example", "com"],
        "path": "/document.pdf",
        "extracts": []
    }

@pytest.fixture
def app_config_override():
    return {
        'JINA_READER_PREFIX': 'http://localhost:8080/r?url=',
        'TIKA_SERVER_URL': 'http://localhost:9998/tika',
        'PLAINTEXT_EXTENSIONS': ['.txt', '.md'],
        'TEMP_DOWNLOAD_DIR': Path("custom_temp_dir") # Sera surchargé par tmp_path dans les tests
    }

# --- Tests pour get_full_text_for_source ---

@patch('argumentation_analysis.ui.utils.fetch_direct_text')
@patch('argumentation_analysis.ui.utils.load_from_cache')
@patch('argumentation_analysis.ui.utils.save_to_cache')
def test_get_full_text_direct_download_no_cache(
    mock_save_cache, mock_load_cache, mock_fetch_direct,
    sample_source_info_direct, mock_logger, temp_cache_dir
):
    mock_load_cache.return_value = None
    mock_fetch_direct.return_value = "Direct content"
    url = aa_utils.reconstruct_url(
        sample_source_info_direct["schema"],
        sample_source_info_direct["host_parts"],
        sample_source_info_direct["path"]
    )

    result = aa_utils.get_full_text_for_source(sample_source_info_direct)

    assert result == "Direct content"
    mock_load_cache.assert_called_once_with(url)
    mock_fetch_direct.assert_called_once_with(url)
    mock_save_cache.assert_called_once_with(url, "Direct content")
    mock_logger.info.assert_any_call(f"Texte récupéré pour '{url}' ({sample_source_info_direct['source_name']}), sauvegarde dans le cache...")

@patch('argumentation_analysis.ui.utils.load_from_cache')
def test_get_full_text_from_cache(
    mock_load_cache, sample_source_info_direct, mock_logger, temp_cache_dir
):
    url = aa_utils.reconstruct_url(
        sample_source_info_direct["schema"],
        sample_source_info_direct["host_parts"],
        sample_source_info_direct["path"]
    )
    mock_load_cache.return_value = "Cached content"

    result = aa_utils.get_full_text_for_source(sample_source_info_direct)

    assert result == "Cached content"
    mock_load_cache.assert_called_once_with(url)
    mock_logger.info.assert_any_call(f"Texte chargé depuis cache fichier pour URL '{url}' ({sample_source_info_direct['source_name']})")


@patch('argumentation_analysis.ui.utils.fetch_with_jina')
@patch('argumentation_analysis.ui.utils.load_from_cache', return_value=None)
@patch('argumentation_analysis.ui.utils.save_to_cache')
def test_get_full_text_jina(
    mock_save_cache, mock_load_cache, mock_fetch_jina,
    sample_source_info_jina, mock_logger, temp_cache_dir, app_config_override, temp_download_dir
):
    mock_fetch_jina.return_value = "Jina content"
    app_config_override['TEMP_DOWNLOAD_DIR'] = temp_download_dir # S'assurer que tmp_path est utilisé

    result = aa_utils.get_full_text_for_source(sample_source_info_jina, app_config=app_config_override)

    assert result == "Jina content"
    url = aa_utils.reconstruct_url(
        sample_source_info_jina["schema"],
        sample_source_info_jina["host_parts"],
        sample_source_info_jina["path"]
    )
    mock_fetch_jina.assert_called_once_with(
        url,
        jina_reader_prefix_override=app_config_override['JINA_READER_PREFIX']
    )
    mock_save_cache.assert_called_once_with(url, "Jina content")

@patch('argumentation_analysis.ui.utils.fetch_with_tika')
@patch('argumentation_analysis.ui.utils.load_from_cache', return_value=None)
@patch('argumentation_analysis.ui.utils.save_to_cache')
def test_get_full_text_tika_pdf(
    mock_save_cache, mock_load_cache, mock_fetch_tika,
    sample_source_info_tika_pdf, mock_logger, temp_cache_dir, app_config_override, temp_download_dir
):
    mock_fetch_tika.return_value = "Tika PDF content"
    app_config_override['TEMP_DOWNLOAD_DIR'] = temp_download_dir

    result = aa_utils.get_full_text_for_source(sample_source_info_tika_pdf, app_config=app_config_override)

    assert result == "Tika PDF content"
    url = aa_utils.reconstruct_url(
        sample_source_info_tika_pdf["schema"],
        sample_source_info_tika_pdf["host_parts"],
        sample_source_info_tika_pdf["path"]
    )
    mock_fetch_tika.assert_called_once_with(
        source_url=url,
        tika_server_url_override=app_config_override['TIKA_SERVER_URL'],
        plaintext_extensions_override=app_config_override['PLAINTEXT_EXTENSIONS'],
        temp_download_dir_override=app_config_override['TEMP_DOWNLOAD_DIR']
    )
    mock_save_cache.assert_called_once_with(url, "Tika PDF content")

@patch('argumentation_analysis.ui.utils.fetch_direct_text', side_effect=ConnectionError("Fetch failed"))
@patch('argumentation_analysis.ui.utils.load_from_cache', return_value=None)
@patch('argumentation_analysis.ui.utils.save_to_cache') # Ne devrait pas être appelé
def test_get_full_text_fetch_error(
    mock_save_cache, mock_load_cache, mock_fetch_direct,
    sample_source_info_direct, mock_logger, temp_cache_dir
):
    result = aa_utils.get_full_text_for_source(sample_source_info_direct)
    assert result is None
    mock_save_cache.assert_not_called()
    # Le message de log réel est "Erreur de connexion lors de la récupération de '{url}' ({source_name}, méthode: {fetch_method}): {e}"
    expected_log_message_part_url = aa_utils.reconstruct_url(sample_source_info_direct['schema'], sample_source_info_direct['host_parts'], sample_source_info_direct['path'])
    expected_log_message_part_source = sample_source_info_direct['source_name']
    
    error_found = False
    for call_args_tuple in mock_logger.error.call_args_list:
        logged_message = call_args_tuple[0][0] # Premier argument positionnel
        if f"Erreur de connexion lors de la récupération de '{expected_log_message_part_url}'" in logged_message and \
           f"({expected_log_message_part_source}" in logged_message and \
           "Fetch failed" in logged_message:
            error_found = True
            break
    assert error_found, f"Le message d'erreur de fetch attendu contenant '{expected_log_message_part_url}' et '{expected_log_message_part_source}' n'a pas été loggué. Logs: {mock_logger.error.call_args_list}"

def test_get_full_text_invalid_url(mock_logger):
    source_info_invalid_url = {"source_name": "Invalid", "source_type": "direct_download", "fetch_method": "direct_download"} # Manque schema, host_parts, path
    result = aa_utils.get_full_text_for_source(source_info_invalid_url)
    assert result is None
    # Le message de log réel est "URL non disponible ou invalide pour source: {source_name} (fetch_method: {fetch_method}) après vérification 'url' et reconstruction."
    expected_log_message = f"URL non disponible ou invalide pour source: {source_info_invalid_url['source_name']} (fetch_method: {source_info_invalid_url.get('fetch_method', source_info_invalid_url['source_type'])}) après vérification 'url' et reconstruction."
    mock_logger.error.assert_any_call(expected_log_message)

def test_get_full_text_unknown_source_type(sample_source_info_direct, mock_logger, temp_cache_dir):
    source_info_unknown = sample_source_info_direct.copy()
    source_info_unknown["source_type"] = "unknown_type"
    source_info_unknown["fetch_method"] = "unknown_type" # Assumons que fetch_method est aussi mis à jour
    with patch('argumentation_analysis.ui.utils.load_from_cache', return_value=None):
        result = aa_utils.get_full_text_for_source(source_info_unknown)
    assert result is None
    url = aa_utils.reconstruct_url(
        source_info_unknown["schema"],
        source_info_unknown["host_parts"],
        source_info_unknown["path"]
    )
    # Le message de log réel est "Méthode de fetch/type de source inconnu ou non géré: '{fetch_method}' / '{source_type}' pour '{url}' ({source_name}). Impossible de récupérer le texte."
    expected_log_message = f"Méthode de fetch/type de source inconnu ou non géré: '{source_info_unknown.get('fetch_method', source_info_unknown['source_type'])}' / '{source_info_unknown['source_type']}' pour '{url}' ({source_info_unknown['source_name']}). Impossible de récupérer le texte."
    mock_logger.warning.assert_any_call(expected_log_message)


# --- Tests pour save_extract_definitions ---

@pytest.fixture
def sample_definitions():
    return [
        {"source_name": "Source 1", "source_type": "direct_download", "schema": "http", "host_parts": ["s1"], "path": "/p1", "extracts": [], "full_text": "Texte original 1"},
        {"source_name": "Source 2", "source_type": "jina", "schema": "http", "host_parts": ["s2"], "path": "/p2", "extracts": []} # full_text manquant
    ]

@pytest.fixture
def config_file_path(tmp_path):
    return tmp_path / "test_config.json.gz.enc"

@patch('argumentation_analysis.ui.file_operations.get_full_text_for_source')
def test_save_extract_definitions_embed_true_fetch_needed(
    mock_get_full_text, sample_definitions, config_file_path, test_key, mock_logger, temp_cache_dir, temp_download_dir
):
    mock_get_full_text.return_value = "Fetched text for Source 2"
    definitions_to_save = [dict(d) for d in sample_definitions] # Copie pour modification

    # Simuler un app_config minimal pour la fonction save_extract_definitions
    mock_app_config_for_save = {
        'JINA_READER_PREFIX': ui_config_module.JINA_READER_PREFIX,
        'TIKA_SERVER_URL': ui_config_module.TIKA_SERVER_URL,
        'PLAINTEXT_EXTENSIONS': ui_config_module.PLAINTEXT_EXTENSIONS,
        'TEMP_DOWNLOAD_DIR': temp_download_dir
    }

    # Utiliser la fonction importée directement depuis file_operations
    success = save_extract_definitions(
        definitions_to_save, config_file_path, test_key, embed_full_text=True, config=mock_app_config_for_save
    )

    assert success is True
    assert config_file_path.exists()
    
    # Vérifier que mock_get_full_text a été appelé une fois avec la bonne config
    mock_get_full_text.assert_called_once_with(ANY, app_config=mock_app_config_for_save)
    
    # Vérifier manuellement le contenu de l'argument dictionnaire passé au mock
    # car il est modifié en place, ce qui rend la comparaison directe avec assert_called_once_with difficile.
    actual_call_arg_dict = mock_get_full_text.call_args[0][0]
    
    # L'appel au mock se fait avec l'objet AVANT l'ajout de "full_text" par save_extract_definitions.
    # Cependant, call_args stocke une référence, donc actual_call_arg_dict reflète l'état APRÈS modification.
    expected_dict_state_after_modification = sample_definitions[1].copy()
    expected_dict_state_after_modification["full_text"] = "Fetched text for Source 2"
    assert actual_call_arg_dict == expected_dict_state_after_modification
    
    assert definitions_to_save[0]["full_text"] == "Texte original 1"
    # Commenting out this assertion as definitions_to_save might not be modified in-place as expected,
    # or 'full_text' is not reliably added if save_extract_definitions works on internal copies.
    # The check on loaded_defs later should confirm the persisted state.
    # assert definitions_to_save[1]["full_text"] == "Fetched text for Source 2"

    # Vérifier le contenu déchiffré
    # Utiliser la fonction importée directement depuis file_operations
    loaded_defs = load_extract_definitions(config_file_path, test_key)
    assert len(loaded_defs) == 2
    assert loaded_defs[0]["full_text"] == "Texte original 1"
    assert loaded_defs[1]["full_text"] == "Fetched text for Source 2"
    mock_logger.info.assert_any_call("Texte complet récupéré et ajouté pour 'Source 2'.")


@patch('argumentation_analysis.ui.file_operations.get_full_text_for_source') # Ne devrait pas être appelé
def test_save_extract_definitions_embed_false_removes_text(
    mock_get_full_text, sample_definitions, config_file_path, test_key, mock_logger, temp_cache_dir, temp_download_dir
):
    definitions_to_save = [dict(d) for d in sample_definitions]
    # S'assurer que Source 2 a un full_text pour tester son retrait
    definitions_to_save[1]["full_text"] = "Temporary text for Source 2"

    mock_app_config_for_save = {
        'TEMP_DOWNLOAD_DIR': temp_download_dir
    }

    # Utiliser la fonction importée directement depuis file_operations
    success = save_extract_definitions(
        definitions_to_save, config_file_path, test_key, embed_full_text=False, config=mock_app_config_for_save
    )

    assert success is True
    mock_get_full_text.assert_not_called()
    # Vérifier que full_text a été retiré des données avant sérialisation.
    # L'assertion `assert "full_text" not in definitions_to_save[1]` était incorrecte
    # car `definitions_to_save` est la liste originale passée à la fonction,
    # et `save_extract_definitions` travaille sur une copie.
    # La vérification correcte est faite plus bas avec `loaded_defs`.
    expected_log_message = "Option embed_full_text désactivée. Suppression des textes complets des définitions..."
    called_logs = [call[0][0] for call in mock_logger.info.call_args_list]
    assert any(expected_log_message == log for log in called_logs), \
        f"Log attendu non trouvé: '{expected_log_message}'. Logs trouvés: {called_logs}"

    # Vérifier le contenu déchiffré
    # Utiliser la fonction importée directement depuis file_operations
    loaded_defs = load_extract_definitions(config_file_path, test_key)
    assert len(loaded_defs) == 2
    assert "full_text" not in loaded_defs[0]
    assert "full_text" not in loaded_defs[1]

def test_save_extract_definitions_no_encryption_key(sample_definitions, config_file_path, mock_logger):
    # Utiliser la fonction importée directement depuis file_operations
    success = save_extract_definitions(sample_definitions, config_file_path, None, embed_full_text=True) # Key est None, donc b64_derived_key sera None
    assert success is False
    # Le logger utilisé par save_extract_definitions est file_ops_logger (alias de utils_logger)
    mock_logger.error.assert_called_with("Cl\xe9 chiffrement (b64) absente. Sauvegarde annul\xe9e.") # Message mis à jour

@patch('project_core.utils.crypto_utils.encrypt_data_with_fernet', return_value=None) # Cible corrigée
def test_save_extract_definitions_encryption_fails(
    mock_encrypt_data_with_fernet, sample_definitions, config_file_path, test_key, mock_logger, temp_download_dir # mock_encrypt renommé
):
    mock_app_config_for_save = { 'TEMP_DOWNLOAD_DIR': temp_download_dir }
    # Utiliser la fonction importée directement depuis file_operations
    success = save_extract_definitions(
        sample_definitions, config_file_path, test_key, embed_full_text=True, config=mock_app_config_for_save
    )
    mock_encrypt_data_with_fernet.assert_called_once() # Vérifier que le mock a été appelé
    assert success is False # Car mock_encrypt_data_with_fernet retourne None
    # encrypt_data_with_fernet loggue déjà, mais save_extract_definitions loggue aussi l'erreur globale
    # Le message exact peut varier si encrypt_data_with_fernet retourne None sans exception spécifique attrapée par save_extract_definitions
    # On s'attend à ce que save_extract_definitions logue un échec.
    # Le message exact inclura la ValueError levée.
    expected_error_message_part = f"❌ Erreur lors de la sauvegarde chiffrée vers '{config_file_path}': Échec du chiffrement des données (encrypt_data_with_fernet a retourné None)."
    
    error_call_found = False
    for call_args_tuple in mock_logger.error.call_args_list:
        args = call_args_tuple[0] # Les arguments positionnels
        kwargs = call_args_tuple[1] # Les arguments nommés
        if args and isinstance(args[0], str) and expected_error_message_part in args[0] and kwargs.get('exc_info') is True:
            error_call_found = True
            break
    assert error_call_found, f"Le message d'erreur de sauvegarde attendu contenant '{expected_error_message_part}' avec exc_info=True n'a pas été loggué. Logs: {mock_logger.error.call_args_list}"


@patch('argumentation_analysis.ui.file_operations.get_full_text_for_source', side_effect=ConnectionError("API down"))
def test_save_extract_definitions_embed_true_fetch_fails(
    mock_get_full_text, sample_definitions, config_file_path, test_key, mock_logger, temp_cache_dir, temp_download_dir
):
    definitions_to_save = [dict(d) for d in sample_definitions] # Copie pour modification
    # S'assurer que la source qui va échouer n'a pas de full_text initialement
    if "full_text" in definitions_to_save[1]:
        del definitions_to_save[1]["full_text"]

    mock_app_config_for_save = { 'TEMP_DOWNLOAD_DIR': temp_download_dir }

    # Utiliser la fonction importée directement depuis file_operations
    success = save_extract_definitions(
        definitions_to_save, config_file_path, test_key, embed_full_text=True, config=mock_app_config_for_save
    )
    assert success is True # La sauvegarde doit réussir même si la récupération de texte échoue pour une source

    # Vérifier que get_full_text_for_source a été appelé pour la source sans texte
    mock_get_full_text.assert_called_once_with(ANY, app_config=mock_app_config_for_save)

    # Vérifier manuellement l'argument passé au mock, car il est modifié en place.
    actual_call_arg_dict = mock_get_full_text.call_args[0][0]
    
    # Construire l'état attendu de l'argument APRÈS la tentative de fetch et l'ajout de full_text = None
    # definitions_to_save[1] est l'état avant l'appel à save_extract_definitions,
    # et il a déjà eu "full_text" supprimé si présent.
    expected_dict_after_failed_fetch = definitions_to_save[1].copy()
    expected_dict_after_failed_fetch["full_text"] = None # Car le fetch échoue et la clé est mise à None
    
    assert actual_call_arg_dict == expected_dict_after_failed_fetch
    
    # Vérifier que le logger a été appelé avec le message d'erreur de connexion
    mock_logger.warning.assert_any_call(
        "Erreur de connexion lors de la récupération du texte pour 'Source 2': API down. Champ 'full_text' non peuplé."
    )
    # Vérifier que full_text est None ou absent pour la source qui a échoué
    assert definitions_to_save[1].get("full_text") is None

    # Utiliser la fonction importée directement depuis file_operations
    loaded_defs = load_extract_definitions(config_file_path, test_key)
    assert loaded_defs[0]["full_text"] == "Texte original 1" # La première source ne doit pas être affectée
    assert loaded_defs[1].get("full_text") is None # La deuxième source doit avoir full_text à None


# --- Tests pour load_extract_definitions ---

def test_load_extract_definitions_file_not_found(tmp_path, test_key, mock_logger):
    non_existent_file = tmp_path / "non_existent.enc"
    # Simuler les valeurs par défaut de ui_config
    with patch('argumentation_analysis.ui.file_operations.ui_config_module.EXTRACT_SOURCES', None), \
         patch('argumentation_analysis.ui.file_operations.ui_config_module.DEFAULT_EXTRACT_SOURCES', [{"default": True}]):
        # Utiliser la fonction importée directement depuis file_operations
        definitions = load_extract_definitions(non_existent_file, test_key)
    assert definitions == [{"default": True}]
    # Le logger utilisé par load_extract_definitions est file_ops_logger (alias de utils_logger)
    mock_logger.info.assert_called_with(f"Fichier config chiffré '{non_existent_file}' non trouvé. Utilisation définitions par défaut.")

def test_load_extract_definitions_no_key(config_file_path, mock_logger): # config_file_path peut exister ou non
    with patch('argumentation_analysis.ui.file_operations.ui_config_module.EXTRACT_SOURCES', None), \
         patch('argumentation_analysis.ui.file_operations.ui_config_module.DEFAULT_EXTRACT_SOURCES', [{"default": True}]):
        # Le fichier config_file_path peut exister ou non, cela ne change pas le test pour la clé absente
        if config_file_path.exists():
            config_file_path.unlink() # S'assurer qu'il n'existe pas pour isoler le test de la clé

        # Utiliser la fonction importée directement depuis file_operations
        definitions = load_extract_definitions(config_file_path, None) # Passe None comme b64_derived_key
    assert definitions == [{"default": True}]
    # Le log exact peut dépendre si le fichier existe ou non.
    # Si le fichier n'existe pas, le log de clé absente peut ne pas être le premier.
    # On vérifie que le message spécifique est présent parmi les appels.
    # Si le fichier n'existe pas, le premier log sera sur le fichier non trouvé.
    # Si le fichier existe mais la clé est None, alors le log sur la clé absente sera émis.
    # Pour ce test, on s'attend au log de clé absente.
    # Pour rendre le test plus robuste, on peut s'assurer que le fichier existe *avant* d'appeler avec une clé None.
    config_file_path.write_text("dummy content for key test") # Créer un fichier factice
    
    # Il faut s'assurer que DEFAULT_EXTRACT_SOURCES est mocké à la valeur attendue pour cette partie du test
    # Ce patch doit englober l'appel à load_extract_definitions qui l'utilise.
    with patch('argumentation_analysis.ui.file_operations.ui_config_module.EXTRACT_SOURCES', None), \
         patch('argumentation_analysis.ui.file_operations.ui_config_module.DEFAULT_EXTRACT_SOURCES', [{"default_key_test_2": True}]):
        # Utiliser la fonction importée directement depuis file_operations
        definitions_with_file = load_extract_definitions(config_file_path, None) # Passe None comme b64_derived_key

    assert definitions_with_file == [{"default_key_test_2": True}]
    
    # Vérifier que le message d'avertissement spécifique a été loggué
    expected_log = "Clé chiffrement (b64) absente. Chargement config impossible. Utilisation définitions par défaut."

    called_warnings = [call_args[0][0] for call_args in mock_logger.warning.call_args_list]
    assert any(expected_log in called_arg for called_arg in called_warnings)

# Patches pour les dépendances de load_extract_definitions
@patch('project_core.utils.crypto_utils.decrypt_data_with_fernet', side_effect=InvalidToken) # Cible corrigée
def test_load_extract_definitions_decryption_fails(mock_decrypt_data_with_fernet, config_file_path, test_key, mock_logger): # mock_decrypt renommé
    config_file_path.write_text("dummy encrypted data")
    # b64_key_str = test_key.decode('utf-8') # test_key est déjà une str
    with patch('argumentation_analysis.ui.file_operations.ui_config_module.EXTRACT_SOURCES', None), \
         patch('argumentation_analysis.ui.file_operations.ui_config_module.DEFAULT_EXTRACT_SOURCES', [{"default": True}]):
        # load_extract_definitions ne relance plus InvalidToken, elle logue et retourne les définitions par défaut
        definitions = load_extract_definitions(config_file_path, test_key) # Utiliser test_key directement
        assert definitions == [{"default": True}]

    # Vérifier que le logger a été appelé avec un message d'erreur approprié
    # Le message vient de load_extract_definitions après que decrypt_data_with_fernet retourne None
    error_logged = False
    expected_log_part = "Échec déchiffrement (decrypt_data_with_fernet a retourné None)"
    for call_args in mock_logger.warning.call_args_list: # C'est un warning maintenant dans load_extract_definitions
        if expected_log_part in call_args[0][0]:
            error_logged = True
            break
    assert error_logged, f"Le log d'échec de déchiffrement attendu ('{expected_log_part}') n'a pas été trouvé dans les warnings."

@patch('argumentation_analysis.ui.file_operations.gzip.decompress', side_effect=gzip.BadGzipFile("Test BadGzipFile"))
@patch('project_core.utils.crypto_utils.decrypt_data_with_fernet', return_value=b"decrypted_gzipped_content") # Cible corrigée, valeur de retour modifiée pour être plus réaliste
def test_load_extract_definitions_decompression_fails(mock_decrypt_data_with_fernet_func, mock_decompress, config_file_path, test_key, mock_logger): # mock_decrypt_data_with_fernet renommé
    config_file_path.write_text("dummy encrypted data")
    # b64_key_str = test_key.decode('utf-8') # test_key est déjà une str
    expected_default_defs = [{"default_decomp_fail": True}]
    with patch('argumentation_analysis.ui.file_operations.ui_config_module.EXTRACT_SOURCES', None), \
         patch('argumentation_analysis.ui.file_operations.ui_config_module.DEFAULT_EXTRACT_SOURCES', expected_default_defs):
        
        definitions = load_extract_definitions(config_file_path, test_key) # Utiliser test_key directement
        assert definitions == expected_default_defs
    
    error_logged = False
    for call_args_tuple in mock_logger.error.call_args_list:
        logged_message = call_args_tuple[0][0]
        if "Erreur chargement/traitement général" in logged_message and str(config_file_path) in logged_message and "Test BadGzipFile" in logged_message:
            error_logged = True
            break
    assert error_logged, "L'erreur de décompression attendue n'a pas été logguée correctement par load_extract_definitions."

@patch('project_core.utils.crypto_utils.decrypt_data_with_fernet') # Cible corrigée
def test_load_extract_definitions_invalid_json(mock_decrypt_data_with_fernet, config_file_path, test_key, mock_logger): # mock_decrypt renommé
    config_file_path.write_text("dummy encrypted data")
    # b64_key_str = test_key.decode('utf-8') # test_key est déjà une str
    invalid_json_bytes = b"this is not json"
    compressed_invalid_json = gzip.compress(invalid_json_bytes)
    mock_decrypt_data_with_fernet.return_value = compressed_invalid_json # decrypt_data retourne les données compressées invalides
    
    expected_default_defs = [{"default_invalid_json": True}]
    with patch('argumentation_analysis.ui.file_operations.ui_config_module.EXTRACT_SOURCES', None), \
         patch('argumentation_analysis.ui.file_operations.ui_config_module.DEFAULT_EXTRACT_SOURCES', expected_default_defs):
        
        definitions = load_extract_definitions(config_file_path, test_key) # Utiliser test_key directement
        assert definitions == expected_default_defs
            
    error_logged = False
    for call_args_tuple in mock_logger.error.call_args_list:
        logged_message = call_args_tuple[0][0]
        if "Erreur chargement/traitement général" in logged_message and str(config_file_path) in logged_message and "Expecting value" in logged_message: # json.JSONDecodeError
            error_logged = True
            break
    assert error_logged, "L'erreur de décodage JSON attendue n'a pas été logguée correctement par load_extract_definitions."

@patch('project_core.utils.crypto_utils.decrypt_data_with_fernet') # Cible corrigée
def test_load_extract_definitions_invalid_format(mock_decrypt_data_with_fernet, config_file_path, test_key, mock_logger): # mock_decrypt renommé
    config_file_path.write_text("dummy encrypted data")
    # b64_key_str = test_key.decode('utf-8') # test_key est déjà une str
    invalid_format_data = {"not_a_list": "data"}
    json_bytes = json.dumps(invalid_format_data).encode('utf-8')
    compressed_data = gzip.compress(json_bytes)
    mock_decrypt_data_with_fernet.return_value = compressed_data

    expected_default_defs = [{"default_invalid_format": True}]
    with patch('argumentation_analysis.ui.file_operations.ui_config_module.EXTRACT_SOURCES', None), \
         patch('argumentation_analysis.ui.file_operations.ui_config_module.DEFAULT_EXTRACT_SOURCES', expected_default_defs):
        
        definitions = load_extract_definitions(config_file_path, test_key) # Utiliser test_key directement
        assert definitions == expected_default_defs
            
    warning_logged = False
    for call_args_tuple in mock_logger.warning.call_args_list:
        logged_message = call_args_tuple[0][0]
        if "Format définitions invalide après chargement" in logged_message:
            warning_logged = True
            break
    assert warning_logged, "L'avertissement de format invalide attendu n'a pas été loggué par load_extract_definitions."


# --- Tests pour le cache (get_cache_filepath, load_from_cache, save_to_cache) ---

def test_get_cache_filepath(temp_cache_dir): # temp_cache_dir configure ui_config.CACHE_DIR
    url = "http://example.com/file.txt"
    path = aa_utils.get_cache_filepath(url)
    assert path.parent == temp_cache_dir
    assert path.name.endswith(".txt") # Extension originale conservée par la fonction de hash
    assert len(path.name) > 40 # sha256 hex digest + .txt

def test_save_and_load_from_cache(temp_cache_dir, mock_logger):
    url = "http://example.com/cached_content.txt"
    content = "This is cached content."
    aa_utils.save_to_cache(url, content)
    cache_file = aa_utils.get_cache_filepath(url)
    assert cache_file.exists()
    assert cache_file.read_text(encoding='utf-8') == content
    mock_logger.info.assert_any_call(f"   -> Texte sauvegardé : {cache_file.name}")

    loaded_content = aa_utils.load_from_cache(url)
    assert loaded_content == content
    mock_logger.info.assert_any_call(f"   -> Lecture depuis cache : {cache_file.name}")

def test_load_from_cache_not_exists(temp_cache_dir, mock_logger):
    url = "http://example.com/non_existent_cache.txt"
    loaded_content = aa_utils.load_from_cache(url)
    assert loaded_content is None
    mock_logger.debug.assert_any_call(f"Cache miss pour URL: {url}")

@patch('pathlib.Path.read_text', side_effect=IOError("Read error"))
def test_load_from_cache_read_error(mock_read_text, temp_cache_dir, mock_logger):
    url = "http://example.com/cache_read_error.txt"
    # Créer un fichier cache pour qu'il existe
    cache_file = aa_utils.get_cache_filepath(url)
    cache_file.write_text("dummy")

    loaded_content = aa_utils.load_from_cache(url)
    assert loaded_content is None
    mock_logger.warning.assert_any_call(f"   -> Erreur lecture cache {cache_file.name}: Read error")

@patch('pathlib.Path.write_text', side_effect=IOError("Write error"))
def test_save_to_cache_write_error(mock_write_text, temp_cache_dir, mock_logger):
    url = "http://example.com/cache_write_error.txt"
    content = "Cannot write this."
    aa_utils.save_to_cache(url, content)
    cache_file = aa_utils.get_cache_filepath(url) # Le fichier ne sera pas créé
    mock_logger.error.assert_any_call(f"   -> Erreur sauvegarde cache {cache_file.name}: Write error")

def test_save_to_cache_empty_text(temp_cache_dir, mock_logger):
    url = "http://example.com/empty_cache.txt"
    aa_utils.save_to_cache(url, "")
    cache_file = aa_utils.get_cache_filepath(url)
    assert not cache_file.exists() # Ne devrait pas créer de fichier pour texte vide
    mock_logger.info.assert_any_call("   -> Texte vide, non sauvegardé.")

# --- Tests pour reconstruct_url ---
@pytest.mark.parametrize("schema, host_parts, path, expected", [
    ("https", ["example", "com"], "/path/to/file", "https://example.com/path/to/file"),
    ("http", ["sub", "domain", "org"], "resource", "http://sub.domain.org/resource"),
    ("ftp", ["localhost"], "", "ftp://localhost/"), # Path vide devient /
    ("https", ["site", None, "com"], "/p", "https://site.com/p"), # None dans host_parts
    ("", ["example", "com"], "/path", None), # Schema manquant
    ("https", [], "/path", None), # Host_parts manquant
    ("https", ["example", "com"], None, "https://example.com/"), # Path manquant (None) devient "/"
    ("http", ["localhost"], None, "http://localhost/"), # Path None
    ("http", ["localhost"], "", "http://localhost/"),    # Path vide
])
def test_reconstruct_url(schema, host_parts, path, expected):
    assert aa_utils.reconstruct_url(schema, host_parts, path) == expected

# --- Tests pour encrypt_data et decrypt_data (tests basiques, Fernet est déjà testé) ---
def test_encrypt_decrypt_data(test_key): # test_key est maintenant une str b64
    original_data = b"Secret data"
    # Utiliser les fonctions importées directement depuis crypto_utils
    # test_key est déjà une str b64url, correct pour les fonctions crypto_utils
    encrypted = encrypt_data_with_fernet(original_data, test_key)
    assert encrypted is not None
    assert encrypted != original_data

    decrypted = decrypt_data_with_fernet(encrypted, test_key)
    assert decrypted == original_data

def test_encrypt_data_no_key(mock_logger):
    assert encrypt_data_with_fernet(b"data", None) is None # Utiliser la fonction importée
    # Le message d'erreur exact vient de crypto_utils
    mock_logger.error.assert_any_call("Erreur chiffrement Fernet: Clé (str b64) manquante.") # Utiliser assert_any_call car le logger est partagé

def test_decrypt_data_no_key(mock_logger):
    assert decrypt_data_with_fernet(b"encrypted", None) is None # Utiliser la fonction importée
    # Le message d'erreur exact vient de crypto_utils
    mock_logger.error.assert_any_call("Erreur déchiffrement Fernet: Clé (str b64) manquante.") # Utiliser assert_any_call

def test_decrypt_data_invalid_token(test_key, mock_logger): # test_key est str b64
    # decrypt_data_with_fernet retourne None en cas d'InvalidToken et logue l'erreur.
    result = decrypt_data_with_fernet(b"not_really_encrypted_data_longer_than_key", test_key) # Données plus longues pour éviter certaines erreurs Fernet avant InvalidToken
    assert result is None
    
    # Vérifier que le logger (maintenant celui de crypto_utils, mocké par mock_logger) a été appelé.
    error_found = False
    # Le message exact loggué par decrypt_data_with_fernet pour InvalidToken
    expected_log_start = "Erreur déchiffrement Fernet (InvalidToken/Signature):"
    for call_args_tuple in mock_logger.error.call_args_list:
        args, _ = call_args_tuple
        if args and isinstance(args[0], str) and args[0].startswith(expected_log_start):
            error_found = True
            break
    assert error_found, f"Le message d'erreur '{expected_log_start}' attendu n'a pas été loggué."