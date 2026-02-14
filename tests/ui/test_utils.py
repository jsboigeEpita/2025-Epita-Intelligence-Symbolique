# Authentic gpt-5-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-


import tempfile
import os

import pytest
import json
import gzip
import logging  # Ajout de l'import manquant
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY

# sys.path est géré par la configuration pytest (ex: pytest.ini, conftest.py)

from argumentation_analysis.ui import utils as aa_utils

# Importer les fonctions déplacées depuis file_operations pour les tests qui les concernent directement
from argumentation_analysis.core.io_manager import (
    load_extract_definitions,
    save_extract_definitions,
)
from argumentation_analysis.ui import (
    config as ui_config_module,
)  # Pour mocker les constantes
from cryptography.fernet import Fernet, InvalidToken  # Ajout InvalidToken

# Importer les fonctions de crypto directement pour les tests qui les utilisent
from argumentation_analysis.core.utils.crypto_utils import (
    encrypt_data_with_fernet,
    decrypt_data_with_fernet,
)
import base64  # Ajouté pour la fixture test_key

# --- Fixtures ---


@pytest.fixture
def mock_logger():
    # Crée un mock partagé
    shared_mock_log = MagicMock()

    # Liste des patchers à appliquer
    patchers = [
        patch("argumentation_analysis.ui.utils.utils_logger", shared_mock_log),
        patch(
            "argumentation_analysis.ui.file_operations.file_ops_logger", shared_mock_log
        ),
        patch("argumentation_analysis.core.utils.crypto_utils.logger", shared_mock_log),
        patch("argumentation_analysis.core.io_manager.io_logger", shared_mock_log),
        patch("argumentation_analysis.ui.cache_utils.cache_logger", shared_mock_log),
    ]

    # Démarrer tous les patchers
    for p in patchers:
        p.start()

    yield shared_mock_log  # Le mock partagé est utilisé pour les assertions

    # Arrêter tous les patchers
    for p in patchers:
        p.stop()


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Crée un répertoire de cache temporaire et le configure dans ui_config."""
    original_cache_dir = ui_config_module.CACHE_DIR
    ui_config_module.CACHE_DIR = tmp_path / "cache"
    ui_config_module.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    yield ui_config_module.CACHE_DIR
    ui_config_module.CACHE_DIR = original_cache_dir  # Restaurer


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
    # Retourne une clé Fernet valide (bytes, déjà encodés en base64url)
    return Fernet.generate_key()


@pytest.fixture
def sample_source_info_direct():
    return {
        "source_name": "Direct Source",
        "source_type": "direct_download",  # Devrait correspondre à une clé dans FETCH_METHODS
        "fetch_method": "direct_download",  # Explicitement pour la clarté des tests
        "schema": "https",
        "host_parts": ["example", "com"],
        "path": "/text.txt",
        "extracts": [],
    }


@pytest.fixture
def sample_source_info_jina():
    return {
        "source_name": "Jina Source",
        "source_type": "jina",  # Devrait correspondre à une clé dans FETCH_METHODS
        "fetch_method": "jina",  # Explicitement pour la clarté des tests
        "schema": "https",
        "host_parts": ["another-example", "com"],
        "path": "/page.html",
        "extracts": [],
    }


@pytest.fixture
def sample_source_info_tika_txt():
    return {
        "source_name": "Tika TXT Source",
        "source_type": "tika",  # Devrait correspondre à une clé dans FETCH_METHODS
        "fetch_method": "tika",  # Explicitement pour la clarté des tests
        "schema": "https",
        "host_parts": ["tika-example", "com"],
        "path": "/document.txt",  # Sera traité comme direct_download par fetch_with_tika
        "extracts": [],
    }


@pytest.fixture
def sample_source_info_tika_pdf():
    return {
        "source_name": "Tika PDF Source",
        "source_type": "tika",  # Devrait correspondre à une clé dans FETCH_METHODS
        "fetch_method": "tika",  # Explicitement pour la clarté des tests
        "schema": "https",
        "host_parts": ["tika-pdf-example", "com"],
        "path": "/document.pdf",
        "extracts": [],
    }


@pytest.fixture
def app_config_override():
    return {
        "JINA_READER_PREFIX": "http://localhost:8080/r?url=",
        "TIKA_SERVER_URL": "http://localhost:9998/tika",
        "PLAINTEXT_EXTENSIONS": [".txt", ".md"],
        "TEMP_DOWNLOAD_DIR": Path(
            "custom_temp_dir"
        ),  # Sera surchargé par tmp_path dans les tests
    }


# --- Tests pour get_full_text_for_source ---


@patch("argumentation_analysis.ui.utils.fetch_direct_text")
@patch("argumentation_analysis.ui.utils.load_from_cache")
@patch("argumentation_analysis.ui.utils.save_to_cache")
def test_get_full_text_direct_download_no_cache(
    mock_save_cache,
    mock_load_cache,
    mock_fetch_direct,
    sample_source_info_direct,
    mock_logger,
    temp_cache_dir,
):
    mock_load_cache.return_value = None
    mock_fetch_direct.return_value = "Direct content"
    url = aa_utils.reconstruct_url(
        sample_source_info_direct["schema"],
        sample_source_info_direct["host_parts"],
        sample_source_info_direct["path"],
    )

    result = aa_utils.get_full_text_for_source(sample_source_info_direct)

    assert result == "Direct content"
    mock_load_cache.assert_called_once_with(url)
    mock_fetch_direct.assert_called_once_with(url)
    mock_save_cache.assert_called_once_with(url, "Direct content")
    mock_logger.info.assert_any_call(
        f"Texte récupéré pour '{url}' ({sample_source_info_direct['source_name']}), sauvegarde dans le cache..."
    )


@patch("argumentation_analysis.ui.utils.load_from_cache")
def test_get_full_text_from_cache(
    mock_load_cache, sample_source_info_direct, mock_logger, temp_cache_dir
):
    url = aa_utils.reconstruct_url(
        sample_source_info_direct["schema"],
        sample_source_info_direct["host_parts"],
        sample_source_info_direct["path"],
    )
    mock_load_cache.return_value = "Cached content"

    result = aa_utils.get_full_text_for_source(sample_source_info_direct)

    assert result == "Cached content"
    mock_load_cache.assert_called_once_with(url)
    mock_logger.info.assert_any_call(
        f"Texte chargé depuis cache fichier pour URL '{url}' ({sample_source_info_direct['source_name']})"
    )


@patch("argumentation_analysis.ui.utils.fetch_with_jina")
@patch("argumentation_analysis.ui.utils.load_from_cache", return_value=None)
@patch("argumentation_analysis.ui.utils.save_to_cache")
def test_get_full_text_jina(
    mock_save_cache,
    mock_load_cache,
    mock_fetch_jina,
    sample_source_info_jina,
    mock_logger,
    temp_cache_dir,
    app_config_override,
    temp_download_dir,
):
    mock_fetch_jina.return_value = "Jina content"
    app_config_override["TEMP_DOWNLOAD_DIR"] = (
        temp_download_dir  # S'assurer que tmp_path est utilisé
    )

    result = aa_utils.get_full_text_for_source(
        sample_source_info_jina, app_config=app_config_override
    )

    assert result == "Jina content"
    url = aa_utils.reconstruct_url(
        sample_source_info_jina["schema"],
        sample_source_info_jina["host_parts"],
        sample_source_info_jina["path"],
    )
    mock_fetch_jina.assert_called_once_with(
        url, jina_reader_prefix_override=app_config_override["JINA_READER_PREFIX"]
    )
    mock_save_cache.assert_called_once_with(url, "Jina content")


@patch("argumentation_analysis.ui.utils.fetch_with_tika")
@patch("argumentation_analysis.ui.utils.load_from_cache", return_value=None)
@patch("argumentation_analysis.ui.utils.save_to_cache")
def test_get_full_text_tika_pdf(
    mock_save_cache,
    mock_load_cache,
    mock_fetch_tika,
    sample_source_info_tika_pdf,
    mock_logger,
    temp_cache_dir,
    app_config_override,
    temp_download_dir,
):
    mock_fetch_tika.return_value = "Tika PDF content"
    app_config_override["TEMP_DOWNLOAD_DIR"] = temp_download_dir

    result = aa_utils.get_full_text_for_source(
        sample_source_info_tika_pdf, app_config=app_config_override
    )

    assert result == "Tika PDF content"
    url = aa_utils.reconstruct_url(
        sample_source_info_tika_pdf["schema"],
        sample_source_info_tika_pdf["host_parts"],
        sample_source_info_tika_pdf["path"],
    )
    mock_fetch_tika.assert_called_once_with(
        source_url=url,
        tika_server_url_override=app_config_override["TIKA_SERVER_URL"],
        plaintext_extensions_override=app_config_override["PLAINTEXT_EXTENSIONS"],
        temp_download_dir_override=app_config_override["TEMP_DOWNLOAD_DIR"],
    )
    mock_save_cache.assert_called_once_with(url, "Tika PDF content")


@patch(
    "argumentation_analysis.ui.utils.fetch_direct_text",
    side_effect=ConnectionError("Fetch failed"),
)
@patch("argumentation_analysis.ui.utils.load_from_cache", return_value=None)
@patch("argumentation_analysis.ui.utils.save_to_cache")
def test_get_full_text_fetch_error(
    mock_save_cache,
    mock_load_cache,
    mock_fetch_direct,
    sample_source_info_direct,
    mock_logger,
    temp_cache_dir,
):
    result = aa_utils.get_full_text_for_source(sample_source_info_direct)
    assert result is None
    mock_save_cache.assert_not_called()
    # Le message de log réel est "Erreur de connexion lors de la récupération de '{url}' ({source_name}, méthode: {fetch_method}): {e}"
    expected_log_message_part_url = aa_utils.reconstruct_url(
        sample_source_info_direct["schema"],
        sample_source_info_direct["host_parts"],
        sample_source_info_direct["path"],
    )
    expected_log_message_part_source = sample_source_info_direct["source_name"]

    error_found = False
    for call_args_tuple in mock_logger.error.call_args_list:
        logged_message = call_args_tuple[0][0]  # Premier argument positionnel
        if (
            f"Erreur de connexion lors de la récupération de '{expected_log_message_part_url}'"
            in logged_message
            and f"({expected_log_message_part_source}" in logged_message
            and "Fetch failed" in logged_message
        ):
            error_found = True
            break
    assert (
        error_found
    ), f"Le message d'erreur de fetch attendu contenant '{expected_log_message_part_url}' et '{expected_log_message_part_source}' n'a pas été loggué. Logs: {mock_logger.error.call_args_list}"


def test_get_full_text_invalid_url(mock_logger):
    source_info_invalid_url = {
        "source_name": "Invalid",
        "source_type": "direct_download",
        "fetch_method": "direct_download",
    }  # Manque schema, host_parts, path
    result = aa_utils.get_full_text_for_source(source_info_invalid_url)
    assert result is None
    expected_log_message = (
        f"URL invalide pour source: {source_info_invalid_url['source_name']}"
    )
    mock_logger.error.assert_any_call(expected_log_message)


def test_get_full_text_unknown_source_type(
    sample_source_info_direct, mock_logger, temp_cache_dir
):
    source_info_unknown = sample_source_info_direct.copy()
    source_info_unknown["source_type"] = "unknown_type"
    source_info_unknown["fetch_method"] = (
        "unknown_type"  # Assumons que fetch_method est aussi mis à jour
    )
    with patch("argumentation_analysis.ui.utils.load_from_cache", return_value=None):
        result = aa_utils.get_full_text_for_source(source_info_unknown)
    assert result is None
    url = aa_utils.reconstruct_url(
        source_info_unknown["schema"],
        source_info_unknown["host_parts"],
        source_info_unknown["path"],
    )
    expected_log_message = f"Type de source inconnu '{source_info_unknown['source_type']}' pour '{url}' ({source_info_unknown['source_name']}). Impossible de récupérer le texte."
    mock_logger.warning.assert_any_call(expected_log_message)


# --- Tests pour save_extract_definitions ---


@pytest.fixture
def sample_definitions():
    return [
        {
            "source_name": "Source 1",
            "source_type": "direct_download",
            "schema": "http",
            "host_parts": ["s1"],
            "path": "/p1",
            "extracts": [],
            "full_text": "Texte original 1",
        },
        {
            "source_name": "Source 2",
            "source_type": "jina",
            "schema": "http",
            "host_parts": ["s2"],
            "path": "/p2",
            "extracts": [],
        },  # full_text manquant
    ]


@pytest.fixture
def config_file_path(tmp_path):
    return tmp_path / "test_config.json.gz.enc"


def test_save_extract_definitions_embed_true_fetch_needed(
    sample_definitions, config_file_path, test_key, mock_logger
):
    """Vérifie que le text_retriever est appelé si full_text est manquant."""
    mock_retriever = MagicMock(return_value="Fetched Content")
    definitions_without_text = [d for d in sample_definitions if "full_text" not in d]

    # Create a copy to avoid modifying the original fixture
    definitions_to_save = [dict(d) for d in sample_definitions]

    success = save_extract_definitions(
        definitions_to_save,
        config_file_path,
        test_key,
        embed_full_text=True,
        text_retriever=mock_retriever,
    )

    assert success is True
    assert mock_retriever.call_count == len(definitions_without_text)

    loaded_defs = load_extract_definitions(config_file_path, test_key)
    saved_def_with_fetched_text = next(
        d for d in loaded_defs if d["source_name"] == "Source 2"
    )
    assert saved_def_with_fetched_text["full_text"] == "Fetched Content"


def test_save_extract_definitions_embed_false_removes_text(
    sample_definitions, config_file_path, test_key, mock_logger
):
    """Vérifie que le champ full_text est retiré si embed_full_text est False."""
    with patch(
        "argumentation_analysis.core.io_manager.json.dumps", side_effect=json.dumps
    ) as mock_json_dumps:
        success = save_extract_definitions(
            sample_definitions, config_file_path, test_key, embed_full_text=False
        )

    assert success is True
    # Vérifier que le json.dumps a été appelé avec des données où "full_text" a été retiré.
    defs_passed_to_dumps = mock_json_dumps.call_args[0][0]
    for d in defs_passed_to_dumps:
        assert "full_text" not in d


def test_save_extract_definitions_no_encryption_key(
    sample_definitions, config_file_path, mock_logger
):
    # Utiliser la fonction importée directement depuis file_operations
    success = save_extract_definitions(
        sample_definitions, config_file_path, None, embed_full_text=True
    )
    assert success is False
    mock_logger.error.assert_called_with(
        "Clé chiffrement (b64_derived_key) absente ou vide. Sauvegarde annulée."
    )


@patch(
    "argumentation_analysis.core.io_manager.encrypt_data_with_fernet",
    side_effect=Exception("Crypto Error"),
)
def test_save_extract_definitions_encryption_fails(
    mock_encrypt, sample_definitions, config_file_path, test_key, mock_logger
):
    """Vérifie que la sauvegarde échoue si le chiffrement échoue."""
    success = save_extract_definitions(
        sample_definitions,
        config_file_path,
        test_key,
        embed_full_text=False,  # Désactivé pour ne pas dépendre du fetch
    )
    assert success is False
    mock_logger.error.assert_any_call(
        f"[FAIL] Erreur lors de la sauvegarde chiffrée vers '{config_file_path}': Crypto Error",
        exc_info=True,
    )


def test_save_extract_definitions_embed_true_fetch_fails(
    sample_definitions, config_file_path, test_key, mock_logger
):
    """Vérifie que la sauvegarde continue mais loggue un warning si le fetch du texte échoue."""
    mock_retriever = MagicMock(side_effect=ConnectionError("API down"))
    definitions_to_save = [dict(d) for d in sample_definitions]

    success = save_extract_definitions(
        definitions_to_save,
        config_file_path,
        test_key,
        embed_full_text=True,
        text_retriever=mock_retriever,
    )

    assert success is True
    mock_logger.warning.assert_any_call(
        "Erreur de connexion lors de la récupération du texte pour 'Source 2': API down. Champ 'full_text' non peuplé."
    )

    # Vérifier que le fichier sauvegardé ne contient pas de full_text pour la source 2
    loaded_defs = load_extract_definitions(config_file_path, test_key)
    source_2_loaded = next(d for d in loaded_defs if d["source_name"] == "Source 2")
    assert source_2_loaded.get("full_text") is None


# --- Tests pour load_extract_definitions ---


def test_load_extract_definitions_file_not_found(tmp_path, test_key, mock_logger):
    """Vérifie que les définitions de secours sont retournées si le fichier n'existe pas."""
    non_existent_file = tmp_path / "non_existent.enc"
    fallback_defs = [{"default": True}]

    definitions = load_extract_definitions(
        non_existent_file, test_key, fallback_definitions=fallback_defs
    )

    assert definitions == fallback_defs
    mock_logger.info.assert_called_with(
        f"Fichier config '{non_existent_file}' non trouvé. Utilisation définitions par défaut."
    )


def test_load_extract_definitions_no_key(config_file_path, mock_logger):
    """Vérifie que le fichier est lu comme du JSON simple si aucune clé n'est fournie."""
    # Définir des données valides pour la structure attendue
    definitions = [
        {
            "source_name": "simple",
            "source_type": "direct",
            "schema": "http",
            "host_parts": ["example"],
            "path": "/",
            "extracts": [],
        }
    ]
    config_file_path.write_text(json.dumps(definitions))

    result = load_extract_definitions(config_file_path, b64_derived_key=None)

    assert result == definitions
    mock_logger.info.assert_any_call(
        f"[OK] Définitions chargées comme JSON simple depuis '{config_file_path}'."
    )


@patch(
    "argumentation_analysis.core.io_manager.decrypt_data_with_fernet",
    side_effect=InvalidToken,
)
def test_load_extract_definitions_decryption_fails(
    mock_decrypt, config_file_path, test_key, mock_logger
):
    """Vérifie le comportement lorsque le déchiffrement échoue avec InvalidToken."""
    config_file_path.write_bytes(b"invalid_encrypted_data")
    fallback_defs = [{"default": "decryption_fail"}]

    result = load_extract_definitions(
        config_file_path,
        test_key,
        fallback_definitions=fallback_defs,
        raise_on_decrypt_error=False,  # Comportement par défaut
    )

    assert result == fallback_defs
    mock_logger.error.assert_any_call(
        f"❌ Token invalide (InvalidToken) lors du déchiffrement de '{config_file_path}'.",
        exc_info=True,
    )


@patch(
    "argumentation_analysis.core.io_manager.gzip.decompress",
    side_effect=gzip.BadGzipFile,
)
@patch(
    "argumentation_analysis.core.io_manager.decrypt_data_with_fernet",
    return_value=b"decrypted_but_bad_gzip",
)
def test_load_extract_definitions_decompression_fails(
    mock_decrypt, mock_decompress, config_file_path, test_key, mock_logger
):
    """Vérifie le comportement lorsque la décompression gzip échoue."""
    config_file_path.write_bytes(b"dummy_data")
    fallback_defs = [{"default": "decompression_fail"}]

    result = load_extract_definitions(
        config_file_path, test_key, fallback_definitions=fallback_defs
    )

    assert result == fallback_defs
    mock_logger.error.assert_any_call(
        f"[FAIL] Erreur chargement/dechiffrement '{config_file_path}': . Utilisation definitions par defaut.",
        exc_info=True,
    )


@patch("argumentation_analysis.core.io_manager.decrypt_data_with_fernet")
def test_load_extract_definitions_invalid_json(
    mock_decrypt, config_file_path, test_key, mock_logger
):
    """Vérifie le comportement lorsque les données déchiffrées ne sont pas du JSON valide."""
    mock_decrypt.return_value = gzip.compress(b"this is not json")
    config_file_path.write_bytes(b"dummy_encrypted_data")
    fallback_defs = [{"default": "invalid_json"}]

    result = load_extract_definitions(
        config_file_path, test_key, fallback_definitions=fallback_defs
    )

    assert result == fallback_defs
    mock_logger.error.assert_any_call(
        f"[FAIL] Erreur chargement/dechiffrement '{config_file_path}': Expecting value: line 1 column 1 (char 0). Utilisation definitions par defaut.",
        exc_info=True,
    )


@patch("argumentation_analysis.core.io_manager.decrypt_data_with_fernet")
def test_load_extract_definitions_invalid_format(
    mock_decrypt, config_file_path, test_key, mock_logger
):
    """Vérifie le comportement lorsque les données JSON n'ont pas le format attendu (pas une liste de dicts)."""
    invalid_format_data = {"not_a_list": "data"}
    json_bytes = json.dumps(invalid_format_data).encode("utf-8")
    compressed_data = gzip.compress(json_bytes)
    mock_decrypt.return_value = compressed_data
    config_file_path.write_bytes(b"dummy_encrypted_data")

    fallback_defs = [{"default": "invalid_format"}]

    result = load_extract_definitions(
        config_file_path, test_key, fallback_definitions=fallback_defs
    )

    assert result == fallback_defs
    mock_logger.warning.assert_called_with(
        f"[WARN] Format definitions invalide apres chargement de '{config_file_path}'. Utilisation definitions par defaut."
    )


# --- Tests pour le cache (get_cache_filepath, load_from_cache, save_to_cache) ---


def test_get_cache_filepath(temp_cache_dir):
    url = "http://example.com/file.txt"
    path = aa_utils.get_cache_filepath(url)
    assert path.parent == temp_cache_dir
    assert path.name.endswith(".txt")
    assert len(path.name) > 40


def test_save_and_load_from_cache(temp_cache_dir, mock_logger):
    url = "http://example.com/cached_content.txt"
    content = "This is cached content."
    aa_utils.save_to_cache(url, content)
    cache_file = aa_utils.get_cache_filepath(url)
    assert cache_file.exists()
    assert cache_file.read_text(encoding="utf-8") == content
    mock_logger.info.assert_any_call(f"   -> Texte sauvegardé : {cache_file.name}")

    loaded_content = aa_utils.load_from_cache(url)
    assert loaded_content == content
    mock_logger.info.assert_any_call(f"   -> Lecture depuis cache : {cache_file.name}")


def test_load_from_cache_not_exists(temp_cache_dir, mock_logger):
    url = "http://example.com/non_existent_cache.txt"
    loaded_content = aa_utils.load_from_cache(url)
    assert loaded_content is None
    mock_logger.debug.assert_any_call(f"Cache miss pour URL: {url}")


@patch("pathlib.Path.read_text", side_effect=IOError("Read error"))
def test_load_from_cache_read_error(mock_read_text, temp_cache_dir, mock_logger):
    url = "http://example.com/cache_read_error.txt"
    cache_file = aa_utils.get_cache_filepath(url)
    cache_file.write_text("dummy")

    loaded_content = aa_utils.load_from_cache(url)
    assert loaded_content is None
    mock_logger.warning.assert_any_call(
        f"   -> Erreur lecture cache {cache_file.name}: Read error"
    )


@patch("pathlib.Path.write_text", side_effect=IOError("Write error"))
def test_save_to_cache_write_error(mock_write_text, temp_cache_dir, mock_logger):
    url = "http://example.com/cache_write_error.txt"
    content = "Cannot write this."
    aa_utils.save_to_cache(url, content)
    cache_file = aa_utils.get_cache_filepath(url)
    mock_logger.error.assert_any_call(
        f"   -> Erreur sauvegarde cache {cache_file.name}: Write error"
    )


def test_save_to_cache_empty_text(temp_cache_dir, mock_logger):
    url = "http://example.com/empty_cache.txt"
    aa_utils.save_to_cache(url, "")
    cache_file = aa_utils.get_cache_filepath(url)
    assert not cache_file.exists()
    mock_logger.info.assert_any_call("   -> Texte vide, non sauvegardé.")


# --- Tests pour reconstruct_url ---
@pytest.mark.parametrize(
    "schema, host_parts, path, expected",
    [
        (
            "https",
            ["example", "com"],
            "/path/to/file",
            "https://example.com/path/to/file",
        ),
        (
            "http",
            ["sub", "domain", "org"],
            "resource",
            "http://sub.domain.org/resource",
        ),
        ("ftp", ["localhost"], "", "ftp://localhost/"),
        ("https", ["site", None, "com"], "/p", "https://site.com/p"),
        ("", ["example", "com"], "/path", None),
        ("https", [], "/path", None),
        ("https", ["example", "com"], None, "https://example.com/"),
        ("http", ["localhost"], None, "http://localhost/"),
        ("http", ["localhost"], "", "http://localhost/"),
    ],
)
def test_reconstruct_url(schema, host_parts, path, expected):
    assert aa_utils.reconstruct_url(schema, host_parts, path) == expected


# --- Tests pour encrypt_data et decrypt_data (tests basiques, Fernet est déjà testé) ---
def test_encrypt_decrypt_data(test_key):
    original_data = b"Secret data"
    encrypted = encrypt_data_with_fernet(original_data, test_key)
    assert encrypted is not None
    assert encrypted != original_data

    decrypted = decrypt_data_with_fernet(encrypted, test_key)
    assert decrypted == original_data


def test_encrypt_data_no_key(mock_logger):
    assert encrypt_data_with_fernet(b"data", None) is None
    mock_logger.error.assert_any_call(
        "Erreur chiffrement Fernet: Clé (str b64 ou bytes) manquante."
    )


def test_decrypt_data_no_key(mock_logger):
    assert decrypt_data_with_fernet(b"encrypted", None) is None
    mock_logger.error.assert_any_call(
        "Erreur déchiffrement Fernet: Clé (str b64 ou bytes) manquante."
    )


def test_decrypt_data_invalid_token(test_key, mock_logger):
    result = decrypt_data_with_fernet(
        b"not_really_encrypted_data_longer_than_key", test_key
    )
    assert result is None

    error_found = False
    expected_log_start = "Erreur déchiffrement Fernet (InvalidToken/Signature):"
    for call_args_tuple in mock_logger.error.call_args_list:
        args, _ = call_args_tuple
        if args and isinstance(args[0], str) and args[0].startswith(expected_log_start):
            error_found = True
            break
    assert (
        error_found
    ), f"Le message d'erreur '{expected_log_start}' attendu n'a pas été loggué."
