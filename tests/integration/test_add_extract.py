"""Integration tests for scripts/dataset/add_extract.py.

Uses mocked io_manager to avoid needing real encryption keys.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make the script importable.
SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "dataset"
sys.path.insert(0, str(SCRIPT_DIR))

import add_extract


class TestParseMetadata:
    def test_simple_keyval(self):
        result = add_extract._parse_metadata("discourse_type=populist")
        assert result == {"discourse_type": "populist"}

    def test_multiple_keys(self):
        result = add_extract._parse_metadata("a=1,b=2,c=3")
        assert result == {"a": "1", "b": "2", "c": "3"}

    def test_empty_string(self):
        result = add_extract._parse_metadata("")
        assert result == {}

    def test_value_with_equals(self):
        result = add_extract._parse_metadata("key=val=ue")
        assert result == {"key": "val=ue"}


class TestIsTracked:
    def test_tracked_file(self, tmp_path):
        # We mock subprocess.run to simulate git tracking
        with patch("add_extract.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert add_extract._is_tracked(tmp_path / "somefile.txt") is True

    def test_untracked_file(self, tmp_path):
        with patch("add_extract.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=128)
            assert add_extract._is_tracked(tmp_path / "somefile.txt") is False

    def test_git_not_found(self, tmp_path):
        with patch("add_extract.subprocess.run", side_effect=FileNotFoundError):
            assert add_extract._is_tracked(tmp_path / "somefile.txt") is False


class TestPrivacyGuard:
    def test_refuses_tracked_file(self, tmp_path):
        """add_extract must refuse if the plaintext file is git-tracked."""
        plaintext = tmp_path / "tracked.txt"
        plaintext.write_text("Some text", encoding="utf-8")

        with patch("add_extract._is_tracked", return_value=True):
            ret = add_extract.main(
                [
                    "--source-name",
                    "Test",
                    "--extract-text-file",
                    str(plaintext),
                ]
            )
        assert ret == 1

    def test_refuses_nonexistent_file(self, tmp_path):
        ret = add_extract.main(
            [
                "--source-name",
                "Test",
                "--extract-text-file",
                str(tmp_path / "nonexistent.txt"),
            ]
        )
        assert ret == 1

    def test_refuses_empty_file(self, tmp_path):
        plaintext = tmp_path / "empty.txt"
        plaintext.write_text("", encoding="utf-8")
        with patch("add_extract._is_tracked", return_value=False):
            ret = add_extract.main(
                [
                    "--source-name",
                    "Test",
                    "--extract-text-file",
                    str(plaintext),
                ]
            )
        assert ret == 1


class TestRoundtrip:
    def test_add_and_reload(self, tmp_path):
        """Roundtrip: add extract → reload → verify present."""
        plaintext = tmp_path / "speech.txt"
        plaintext.write_text("Citizens must have a voice.", encoding="utf-8")

        saved_definitions: list = []

        def mock_save(
            extract_definitions,
            config_file,
            b64_derived_key,
            embed_full_text=False,
            config=None,
            text_retriever=None,
        ):
            saved_definitions.extend(extract_definitions)
            return True

        with patch("add_extract._is_tracked", return_value=False), patch(
            "argumentation_analysis.core.io_manager.load_extract_definitions",
            return_value=[],
        ), patch(
            "argumentation_analysis.core.io_manager.save_extract_definitions",
            side_effect=mock_save,
        ), patch(
            "argumentation_analysis.core.utils.crypto_utils.derive_encryption_key",
            return_value=b"dGVzdGtleQ==",
        ), patch.dict(
            os.environ, {"TEXT_CONFIG_PASSPHRASE": "test"}
        ):
            ret = add_extract.main(
                [
                    "--source-name",
                    "Test Speaker",
                    "--extract-text-file",
                    str(plaintext),
                    "--metadata",
                    "discourse_type=populist,era=2025",
                ]
            )

        assert ret == 0
        assert len(saved_definitions) == 1
        assert saved_definitions[0]["source_name"] == "Test Speaker"
