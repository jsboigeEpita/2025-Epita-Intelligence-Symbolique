# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.core.io_manager
Covers load_extract_definitions and save_extract_definitions with crypto mocking.
"""

import pytest
import json
import gzip
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from cryptography.fernet import InvalidToken

from argumentation_analysis.core.io_manager import (
    load_extract_definitions,
    save_extract_definitions,
)

# ============================================================
# Helpers
# ============================================================

VALID_DEFINITION = {
    "source_name": "Test Source",
    "source_type": "url",
    "schema": "https",
    "host_parts": ["example", "com"],
    "path": "/test",
    "extracts": [{"name": "extract1"}],
}

FALLBACK_DEFINITIONS = [
    {
        "source_name": "Fallback",
        "source_type": "file",
        "schema": "file",
        "host_parts": [],
        "path": "/fallback",
        "extracts": [],
    }
]


def _make_encrypted_payload(definitions):
    """Simulate encrypt pipeline: JSON → gzip → 'encrypted' bytes."""
    json_data = json.dumps(definitions).encode("utf-8")
    return gzip.compress(json_data)


# ============================================================
# load_extract_definitions
# ============================================================


class TestLoadExtractDefinitions:
    """Tests for load_extract_definitions."""

    def test_file_not_found_returns_fallback(self, tmp_path):
        nonexistent = tmp_path / "missing.dat"
        result = load_extract_definitions(
            nonexistent, "some_key", fallback_definitions=FALLBACK_DEFINITIONS
        )
        assert len(result) == 1
        assert result[0]["source_name"] == "Fallback"

    def test_file_not_found_returns_empty_by_default(self, tmp_path):
        nonexistent = tmp_path / "missing.dat"
        result = load_extract_definitions(nonexistent, "some_key")
        assert result == []

    def test_file_not_found_fallback_is_copy(self, tmp_path):
        nonexistent = tmp_path / "missing.dat"
        result = load_extract_definitions(
            nonexistent, "some_key", fallback_definitions=FALLBACK_DEFINITIONS
        )
        # Should be a copy, not same reference
        assert result[0] is not FALLBACK_DEFINITIONS[0]

    def test_load_with_key_success(self, tmp_path):
        definitions = [VALID_DEFINITION]
        compressed = _make_encrypted_payload(definitions)

        config_file = tmp_path / "config.dat"
        config_file.write_bytes(b"encrypted_data")

        with patch(
            "argumentation_analysis.core.io_manager.decrypt_data_with_fernet",
            return_value=compressed,
        ):
            result = load_extract_definitions(config_file, "valid_key")
            assert len(result) == 1
            assert result[0]["source_name"] == "Test Source"

    def test_load_with_key_invalid_token(self, tmp_path):
        config_file = tmp_path / "config.dat"
        config_file.write_bytes(b"encrypted_data")

        with patch(
            "argumentation_analysis.core.io_manager.decrypt_data_with_fernet",
            return_value=None,
        ):
            result = load_extract_definitions(
                config_file, "bad_key", fallback_definitions=FALLBACK_DEFINITIONS
            )
            assert result[0]["source_name"] == "Fallback"

    def test_load_with_key_invalid_token_raises(self, tmp_path):
        config_file = tmp_path / "config.dat"
        config_file.write_bytes(b"encrypted_data")

        with patch(
            "argumentation_analysis.core.io_manager.decrypt_data_with_fernet",
            return_value=None,
        ):
            with pytest.raises(InvalidToken):
                load_extract_definitions(
                    config_file, "bad_key", raise_on_decrypt_error=True
                )

    def test_load_with_key_generic_error(self, tmp_path):
        config_file = tmp_path / "config.dat"
        config_file.write_bytes(b"encrypted_data")

        with patch(
            "argumentation_analysis.core.io_manager.decrypt_data_with_fernet",
            side_effect=RuntimeError("Unexpected"),
        ):
            result = load_extract_definitions(
                config_file, "key", fallback_definitions=FALLBACK_DEFINITIONS
            )
            assert result[0]["source_name"] == "Fallback"

    def test_load_no_key_valid_json(self, tmp_path):
        definitions = [VALID_DEFINITION]
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(definitions), encoding="utf-8")

        result = load_extract_definitions(config_file, None)
        assert len(result) == 1
        assert result[0]["source_name"] == "Test Source"

    def test_load_no_key_invalid_json(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text("not valid json {{{", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            load_extract_definitions(config_file, None)

    def test_load_no_key_generic_error(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text("", encoding="utf-8")

        # Empty file → JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            load_extract_definitions(config_file, None)

    def test_load_invalid_format_returns_fallback(self, tmp_path):
        # Valid JSON but wrong format (missing required keys)
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps([{"wrong": "format"}]), encoding="utf-8")

        result = load_extract_definitions(
            config_file, None, fallback_definitions=FALLBACK_DEFINITIONS
        )
        assert result[0]["source_name"] == "Fallback"

    def test_load_invalid_format_not_list(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

        result = load_extract_definitions(
            config_file, None, fallback_definitions=FALLBACK_DEFINITIONS
        )
        assert result[0]["source_name"] == "Fallback"

    def test_load_valid_format_passes_validation(self, tmp_path):
        definitions = [VALID_DEFINITION]
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(definitions), encoding="utf-8")

        result = load_extract_definitions(config_file, None)
        assert len(result) == 1


# ============================================================
# save_extract_definitions
# ============================================================


class TestSaveExtractDefinitions:
    """Tests for save_extract_definitions."""

    def test_save_no_key_returns_false(self, tmp_path):
        config_file = tmp_path / "output.dat"
        result = save_extract_definitions([VALID_DEFINITION], config_file, None)
        assert result is False

    def test_save_empty_key_returns_false(self, tmp_path):
        config_file = tmp_path / "output.dat"
        result = save_extract_definitions([VALID_DEFINITION], config_file, "")
        assert result is False

    def test_save_non_list_returns_false(self, tmp_path):
        config_file = tmp_path / "output.dat"
        result = save_extract_definitions("not_a_list", config_file, "valid_key")
        assert result is False

    def test_save_success(self, tmp_path):
        config_file = tmp_path / "output.dat"

        with patch(
            "argumentation_analysis.core.io_manager.encrypt_data_with_fernet",
            return_value=b"encrypted_content",
        ):
            result = save_extract_definitions(
                [VALID_DEFINITION], config_file, "valid_key"
            )
            assert result is True
            assert config_file.exists()
            assert config_file.read_bytes() == b"encrypted_content"

    def test_save_creates_parent_dirs(self, tmp_path):
        config_file = tmp_path / "sub" / "dir" / "output.dat"

        with patch(
            "argumentation_analysis.core.io_manager.encrypt_data_with_fernet",
            return_value=b"data",
        ):
            result = save_extract_definitions(
                [VALID_DEFINITION], config_file, "valid_key"
            )
            assert result is True
            assert config_file.parent.exists()

    def test_save_encrypt_returns_none(self, tmp_path):
        config_file = tmp_path / "output.dat"

        with patch(
            "argumentation_analysis.core.io_manager.encrypt_data_with_fernet",
            return_value=None,
        ):
            result = save_extract_definitions(
                [VALID_DEFINITION], config_file, "valid_key"
            )
            assert result is False

    def test_save_encrypt_raises(self, tmp_path):
        config_file = tmp_path / "output.dat"

        with patch(
            "argumentation_analysis.core.io_manager.encrypt_data_with_fernet",
            side_effect=RuntimeError("Encrypt error"),
        ):
            result = save_extract_definitions(
                [VALID_DEFINITION], config_file, "valid_key"
            )
            assert result is False

    def test_save_with_embed_full_text_no_retriever(self, tmp_path):
        config_file = tmp_path / "output.dat"

        with patch(
            "argumentation_analysis.core.io_manager.encrypt_data_with_fernet",
            return_value=b"data",
        ):
            result = save_extract_definitions(
                [VALID_DEFINITION], config_file, "key", embed_full_text=True
            )
            assert result is True

    def test_save_with_embed_full_text_and_retriever(self, tmp_path):
        config_file = tmp_path / "output.dat"
        definition = dict(VALID_DEFINITION)  # Copy

        retriever = MagicMock(return_value="Full text content here")

        with patch(
            "argumentation_analysis.core.io_manager.encrypt_data_with_fernet",
            return_value=b"data",
        ):
            result = save_extract_definitions(
                [definition],
                config_file,
                "key",
                embed_full_text=True,
                text_retriever=retriever,
            )
            assert result is True
            retriever.assert_called_once()

    def test_save_embed_full_text_retriever_returns_none(self, tmp_path):
        config_file = tmp_path / "output.dat"
        definition = dict(VALID_DEFINITION)

        retriever = MagicMock(return_value=None)

        with patch(
            "argumentation_analysis.core.io_manager.encrypt_data_with_fernet",
            return_value=b"data",
        ):
            result = save_extract_definitions(
                [definition],
                config_file,
                "key",
                embed_full_text=True,
                text_retriever=retriever,
            )
            assert result is True

    def test_save_embed_full_text_retriever_connection_error(self, tmp_path):
        config_file = tmp_path / "output.dat"
        definition = dict(VALID_DEFINITION)

        retriever = MagicMock(side_effect=ConnectionError("Network error"))

        with patch(
            "argumentation_analysis.core.io_manager.encrypt_data_with_fernet",
            return_value=b"data",
        ):
            result = save_extract_definitions(
                [definition],
                config_file,
                "key",
                embed_full_text=True,
                text_retriever=retriever,
            )
            assert result is True

    def test_save_embed_full_text_retriever_generic_error(self, tmp_path):
        config_file = tmp_path / "output.dat"
        definition = dict(VALID_DEFINITION)

        retriever = MagicMock(side_effect=RuntimeError("Unexpected"))

        with patch(
            "argumentation_analysis.core.io_manager.encrypt_data_with_fernet",
            return_value=b"data",
        ):
            result = save_extract_definitions(
                [definition],
                config_file,
                "key",
                embed_full_text=True,
                text_retriever=retriever,
            )
            assert result is True

    def test_save_without_embed_removes_full_text(self, tmp_path):
        config_file = tmp_path / "output.dat"
        definition = dict(VALID_DEFINITION)
        definition["full_text"] = "Some text that should be removed"

        saved_data = {}

        def capture_encrypt(data, key):
            # Decompress to inspect what was encrypted
            decompressed = gzip.decompress(data)
            saved_data["definitions"] = json.loads(decompressed)
            return b"encrypted"

        with patch(
            "argumentation_analysis.core.io_manager.encrypt_data_with_fernet",
            side_effect=capture_encrypt,
        ):
            save_extract_definitions(
                [definition], config_file, "key", embed_full_text=False
            )
            # full_text should have been removed
            assert "full_text" not in saved_data["definitions"][0]

    def test_save_with_existing_full_text_kept(self, tmp_path):
        config_file = tmp_path / "output.dat"
        definition = dict(VALID_DEFINITION)
        definition["full_text"] = "Existing full text"

        saved_data = {}

        def capture_encrypt(data, key):
            decompressed = gzip.decompress(data)
            saved_data["definitions"] = json.loads(decompressed)
            return b"encrypted"

        retriever = MagicMock()  # Should not be called since text already exists

        with patch(
            "argumentation_analysis.core.io_manager.encrypt_data_with_fernet",
            side_effect=capture_encrypt,
        ):
            save_extract_definitions(
                [definition],
                config_file,
                "key",
                embed_full_text=True,
                text_retriever=retriever,
            )
            retriever.assert_not_called()
            assert saved_data["definitions"][0]["full_text"] == "Existing full text"
