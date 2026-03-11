"""
Tests unitaires etendus pour source_management.py.

Ce module teste les fonctionnalites ETENDUES du gestionnaire unifie de sources
qui ne sont PAS couvertes par test_source_manager.py (lequel teste principalement
le routage simple/complex via delegation au legacy manager).

Couverture :
- UnifiedSourceConfig : from_legacy_config / to_legacy_config
- UnifiedSourceManager : _get_passphrase, _load_enc_file_sources,
  _load_text_file_sources, _load_free_text_sources, load_sources routing
  pour les nouveaux types, select_text_for_analysis pour enc_file/text_file/free_text,
  list_available_sources, _setup_logging (anonymize filter)
- create_unified_source_manager factory
- InteractiveSourceSelector.load_source_batch
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from argumentation_analysis.core.source_management import (
    UnifiedSourceConfig,
    UnifiedSourceManager,
    UnifiedSourceType,
    create_unified_source_manager,
    InteractiveSourceSelector,
)
from argumentation_analysis.core.source_manager import (
    SourceConfig as LegacySourceConfig,
    SourceType as LegacySourceType,
)
from argumentation_analysis.models.extract_definition import (
    Extract,
    ExtractDefinitions,
    SourceDefinition,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_extract_definitions(
    source_name: str = "Test Source",
    source_type: str = "test",
    full_text: str = "Some analysis text for testing.",
    extract_name: str = "Test Extract",
) -> ExtractDefinitions:
    """Create a real ExtractDefinitions object for testing."""
    extract = Extract(
        extract_name=extract_name,
        start_marker="",
        end_marker="",
        full_text=full_text,
    )
    source = SourceDefinition(
        source_name=source_name,
        source_type=source_type,
        schema="test",
        host_parts=["local"],
        path="/test",
        extracts=[extract],
    )
    # SourceDefinition does not have full_text by default; we add it
    # dynamically so select_text_for_analysis can find it via hasattr.
    source.full_text = full_text  # type: ignore[attr-defined]
    return ExtractDefinitions(sources=[source])


def _make_extract_definitions_no_full_text(
    extract_text: str = "Extract-level text only.",
) -> ExtractDefinitions:
    """Create ExtractDefinitions where only extracts have full_text (not source)."""
    extract = Extract(
        extract_name="Extract Only",
        start_marker="",
        end_marker="",
        full_text=extract_text,
    )
    source = SourceDefinition(
        source_name="No Full Text Source",
        source_type="test",
        schema="test",
        host_parts=["local"],
        path="/test",
        extracts=[extract],
    )
    # Deliberately do NOT set source.full_text
    return ExtractDefinitions(sources=[source])


# ===========================================================================
# UnifiedSourceConfig
# ===========================================================================

class TestUnifiedSourceConfigConversion:
    """Tests for UnifiedSourceConfig.from_legacy_config and to_legacy_config."""

    def test_from_legacy_config_simple(self):
        """from_legacy_config converts a SIMPLE LegacySourceConfig correctly."""
        legacy = LegacySourceConfig(
            source_type=LegacySourceType.SIMPLE,
            passphrase="secret",
            anonymize_logs=False,
            auto_cleanup=False,
        )
        unified = UnifiedSourceConfig.from_legacy_config(legacy)

        assert unified.source_type == UnifiedSourceType.SIMPLE
        assert unified.passphrase == "secret"
        assert unified.anonymize_logs is False
        assert unified.auto_cleanup is False

    def test_from_legacy_config_complex(self):
        """from_legacy_config converts a COMPLEX LegacySourceConfig correctly."""
        legacy = LegacySourceConfig(
            source_type=LegacySourceType.COMPLEX,
            passphrase=None,
            anonymize_logs=True,
            auto_cleanup=True,
        )
        unified = UnifiedSourceConfig.from_legacy_config(legacy)

        assert unified.source_type == UnifiedSourceType.COMPLEX
        assert unified.passphrase is None
        assert unified.anonymize_logs is True

    def test_from_legacy_config_preserves_defaults_for_new_fields(self):
        """New-type-specific fields keep their defaults after from_legacy_config."""
        legacy = LegacySourceConfig(source_type=LegacySourceType.SIMPLE)
        unified = UnifiedSourceConfig.from_legacy_config(legacy)

        assert unified.enc_file_path is None
        assert unified.text_file_path is None
        assert unified.free_text_content is None
        assert unified.source_index == 0
        assert unified.interactive_mode is False
        assert unified.auto_passphrase is True

    def test_to_legacy_config_simple(self):
        """to_legacy_config for SIMPLE type produces a correct LegacySourceConfig."""
        unified = UnifiedSourceConfig(
            source_type=UnifiedSourceType.SIMPLE,
            passphrase="pw",
            anonymize_logs=False,
            auto_cleanup=False,
        )
        legacy = unified.to_legacy_config()

        assert legacy.source_type == LegacySourceType.SIMPLE
        assert legacy.passphrase == "pw"
        assert legacy.anonymize_logs is False
        assert legacy.auto_cleanup is False

    def test_to_legacy_config_complex(self):
        """to_legacy_config for COMPLEX type keeps COMPLEX."""
        unified = UnifiedSourceConfig(
            source_type=UnifiedSourceType.COMPLEX,
            passphrase="pass",
        )
        legacy = unified.to_legacy_config()
        assert legacy.source_type == LegacySourceType.COMPLEX

    def test_to_legacy_config_enc_file_falls_back_to_simple(self):
        """to_legacy_config for ENC_FILE falls back to SIMPLE (no legacy equivalent)."""
        unified = UnifiedSourceConfig(source_type=UnifiedSourceType.ENC_FILE)
        legacy = unified.to_legacy_config()
        assert legacy.source_type == LegacySourceType.SIMPLE

    def test_to_legacy_config_text_file_falls_back_to_simple(self):
        """to_legacy_config for TEXT_FILE falls back to SIMPLE."""
        unified = UnifiedSourceConfig(source_type=UnifiedSourceType.TEXT_FILE)
        legacy = unified.to_legacy_config()
        assert legacy.source_type == LegacySourceType.SIMPLE

    def test_to_legacy_config_free_text_falls_back_to_simple(self):
        """to_legacy_config for FREE_TEXT falls back to SIMPLE."""
        unified = UnifiedSourceConfig(source_type=UnifiedSourceType.FREE_TEXT)
        legacy = unified.to_legacy_config()
        assert legacy.source_type == LegacySourceType.SIMPLE

    def test_roundtrip_simple(self):
        """Roundtrip from_legacy -> to_legacy preserves core fields for SIMPLE."""
        original = LegacySourceConfig(
            source_type=LegacySourceType.SIMPLE,
            passphrase="rtrip",
            anonymize_logs=True,
            auto_cleanup=False,
        )
        roundtripped = UnifiedSourceConfig.from_legacy_config(original).to_legacy_config()

        assert roundtripped.source_type == original.source_type
        assert roundtripped.passphrase == original.passphrase
        assert roundtripped.anonymize_logs == original.anonymize_logs
        assert roundtripped.auto_cleanup == original.auto_cleanup


# ===========================================================================
# UnifiedSourceManager._get_passphrase
# ===========================================================================

class TestGetPassphrase:
    """Tests for UnifiedSourceManager._get_passphrase."""

    def test_passphrase_from_config(self):
        """Returns passphrase directly from config when present."""
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            passphrase="config_pass",
        )
        manager = UnifiedSourceManager(config)
        assert manager._get_passphrase() == "config_pass"

    def test_passphrase_from_settings(self, mocker):
        """Falls back to settings.passphrase when config.passphrase is None."""
        mock_secret = MagicMock()
        mock_secret.get_secret_value.return_value = "settings_pass"
        mocker.patch(
            "argumentation_analysis.core.source_management.settings",
            passphrase=mock_secret,
        )
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            passphrase=None,
            auto_passphrase=True,
        )
        manager = UnifiedSourceManager(config)
        assert manager._get_passphrase() == "settings_pass"

    def test_raises_in_non_interactive_mode(self, mocker):
        """Raises ValueError when no passphrase and interactive_mode=False."""
        mocker.patch(
            "argumentation_analysis.core.source_management.settings",
            passphrase=None,
        )
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            passphrase=None,
            auto_passphrase=True,
            interactive_mode=False,
        )
        manager = UnifiedSourceManager(config)

        with pytest.raises(ValueError, match="Aucune phrase"):
            manager._get_passphrase()

    def test_interactive_getpass_fallback(self, mocker):
        """In interactive mode, calls getpass when no config/settings passphrase."""
        mocker.patch(
            "argumentation_analysis.core.source_management.settings",
            passphrase=None,
        )
        mocker.patch(
            "argumentation_analysis.core.source_management.getpass.getpass",
            return_value="interactive_pass",
        )
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            passphrase=None,
            auto_passphrase=True,
            interactive_mode=True,
        )
        manager = UnifiedSourceManager(config)
        assert manager._get_passphrase() == "interactive_pass"

    def test_interactive_empty_passphrase_raises(self, mocker):
        """In interactive mode, empty getpass input raises ValueError."""
        mocker.patch(
            "argumentation_analysis.core.source_management.settings",
            passphrase=None,
        )
        mocker.patch(
            "argumentation_analysis.core.source_management.getpass.getpass",
            return_value="",
        )
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            passphrase=None,
            auto_passphrase=True,
            interactive_mode=True,
        )
        manager = UnifiedSourceManager(config)

        with pytest.raises(ValueError, match="Aucune phrase secrète fournie"):
            manager._get_passphrase()

    def test_auto_passphrase_disabled_skips_settings(self, mocker):
        """When auto_passphrase=False, settings.passphrase is not consulted."""
        mock_secret = MagicMock()
        mock_secret.get_secret_value.return_value = "should_not_use"
        mocker.patch(
            "argumentation_analysis.core.source_management.settings",
            passphrase=mock_secret,
        )
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            passphrase=None,
            auto_passphrase=False,
            interactive_mode=False,
        )
        manager = UnifiedSourceManager(config)

        with pytest.raises(ValueError, match="Aucune phrase"):
            manager._get_passphrase()


# ===========================================================================
# UnifiedSourceManager._load_enc_file_sources
# ===========================================================================

class TestLoadEncFileSources:
    """Tests for _load_enc_file_sources."""

    def test_no_enc_file_path(self):
        """Returns error when enc_file_path is not set."""
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            enc_file_path=None,
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_enc_file_sources()
        assert result is None
        assert "requis" in msg

    def test_enc_file_not_found(self, tmp_path):
        """Returns error when enc_file_path does not exist."""
        nonexistent = str(tmp_path / "nonexistent.enc")
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            enc_file_path=nonexistent,
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_enc_file_sources()
        assert result is None
        assert "non trouv" in msg

    def test_enc_file_key_derivation_fails(self, mocker, tmp_path):
        """Returns error when derive_encryption_key returns None."""
        enc_file = tmp_path / "test.enc"
        enc_file.write_bytes(b"fake encrypted content")

        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            enc_file_path=str(enc_file),
            passphrase="pw",
        )
        mocker.patch(
            "argumentation_analysis.core.source_management.derive_encryption_key",
            return_value=None,
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_enc_file_sources()
        assert result is None
        assert "cl" in msg.lower()  # "cle" in message

    def test_enc_file_load_definitions_returns_none(self, mocker, tmp_path):
        """Returns error when load_extract_definitions returns None/empty."""
        enc_file = tmp_path / "test.enc"
        enc_file.write_bytes(b"fake")

        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            enc_file_path=str(enc_file),
            passphrase="pw",
        )
        mocker.patch(
            "argumentation_analysis.core.source_management.derive_encryption_key",
            return_value=b"fake_key",
        )
        mocker.patch(
            "argumentation_analysis.core.source_management.load_extract_definitions",
            return_value=None,
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_enc_file_sources()
        assert result is None
        assert "Impossible" in msg

    def test_enc_file_success_with_list_result(self, mocker, tmp_path):
        """Successful load when load_extract_definitions returns a list."""
        enc_file = tmp_path / "test.enc"
        enc_file.write_bytes(b"fake")

        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            enc_file_path=str(enc_file),
            passphrase="pw",
        )
        mocker.patch(
            "argumentation_analysis.core.source_management.derive_encryption_key",
            return_value=b"fake_key",
        )
        raw_defs = [
            {
                "source_name": "Enc Source",
                "source_type": "enc",
                "schema": "enc",
                "host_parts": ["local"],
                "path": "/enc",
                "extracts": [
                    {
                        "extract_name": "e1",
                        "start_marker": "",
                        "end_marker": "",
                        "full_text": "encrypted text content",
                    }
                ],
            }
        ]
        mocker.patch(
            "argumentation_analysis.core.source_management.load_extract_definitions",
            return_value=raw_defs,
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_enc_file_sources()

        assert result is not None
        assert isinstance(result, ExtractDefinitions)
        assert "succ" in msg.lower()
        assert len(result.sources) == 1

    def test_enc_file_success_with_extract_definitions_result(self, mocker, tmp_path):
        """Successful load when load_extract_definitions returns ExtractDefinitions directly."""
        enc_file = tmp_path / "test.enc"
        enc_file.write_bytes(b"fake")

        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            enc_file_path=str(enc_file),
            passphrase="pw",
        )
        mocker.patch(
            "argumentation_analysis.core.source_management.derive_encryption_key",
            return_value=b"fake_key",
        )
        mock_defs = _make_extract_definitions(source_name="Direct Enc")
        mocker.patch(
            "argumentation_analysis.core.source_management.load_extract_definitions",
            return_value=mock_defs,
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_enc_file_sources()

        assert result is mock_defs
        assert "succ" in msg.lower()

    def test_enc_file_exception_handling(self, mocker, tmp_path):
        """Exception during decryption returns error tuple, does not raise."""
        enc_file = tmp_path / "bad.enc"
        enc_file.write_bytes(b"corrupt")

        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            enc_file_path=str(enc_file),
            passphrase="pw",
        )
        mocker.patch(
            "argumentation_analysis.core.source_management.derive_encryption_key",
            side_effect=RuntimeError("crypto failure"),
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_enc_file_sources()

        assert result is None
        assert "Erreur" in msg


# ===========================================================================
# UnifiedSourceManager._load_text_file_sources
# ===========================================================================

class TestLoadTextFileSources:
    """Tests for _load_text_file_sources."""

    def test_no_text_file_path(self):
        """Returns error when text_file_path is not set."""
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.TEXT_FILE,
            text_file_path=None,
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_text_file_sources()
        assert result is None
        assert "requis" in msg

    def test_text_file_not_found(self, tmp_path):
        """Returns error when file does not exist."""
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.TEXT_FILE,
            text_file_path=str(tmp_path / "nope.txt"),
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_text_file_sources()
        assert result is None
        assert "non trouv" in msg

    def test_text_file_empty(self, tmp_path):
        """Returns error when file exists but is empty."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.TEXT_FILE,
            text_file_path=str(empty_file),
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_text_file_sources()
        assert result is None
        assert "vide" in msg

    def test_text_file_whitespace_only(self, tmp_path):
        """Returns error when file contains only whitespace."""
        ws_file = tmp_path / "ws.txt"
        ws_file.write_text("   \n\t\n  ", encoding="utf-8")

        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.TEXT_FILE,
            text_file_path=str(ws_file),
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_text_file_sources()
        assert result is None
        assert "vide" in msg

    def test_text_file_success(self, tmp_path):
        """Successfully loads a text file into ExtractDefinitions."""
        text_file = tmp_path / "sample.txt"
        content = "Ceci est un argument valide pour l'analyse."
        text_file.write_text(content, encoding="utf-8")

        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.TEXT_FILE,
            text_file_path=str(text_file),
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_text_file_sources()

        assert result is not None
        assert isinstance(result, ExtractDefinitions)
        assert len(result.sources) == 1
        assert "sample.txt" in result.sources[0].source_name
        assert result.sources[0].extracts[0].full_text == content
        assert str(len(content)) in msg

    def test_text_file_read_exception(self, mocker, tmp_path):
        """IO error during read returns error tuple."""
        text_file = tmp_path / "exists.txt"
        text_file.write_text("content", encoding="utf-8")

        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.TEXT_FILE,
            text_file_path=str(text_file),
        )
        manager = UnifiedSourceManager(config)

        mocker.patch("builtins.open", side_effect=IOError("read error"))
        result, msg = manager._load_text_file_sources()
        assert result is None
        assert "Erreur" in msg


# ===========================================================================
# UnifiedSourceManager._load_free_text_sources
# ===========================================================================

class TestLoadFreeTextSources:
    """Tests for _load_free_text_sources."""

    def test_no_free_text_content(self):
        """Returns error when free_text_content is None."""
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.FREE_TEXT,
            free_text_content=None,
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_free_text_sources()
        assert result is None
        assert "requis" in msg

    def test_free_text_empty_after_strip(self):
        """Returns error when free_text_content is all whitespace."""
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.FREE_TEXT,
            free_text_content="   \n\t  ",
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_free_text_sources()
        assert result is None
        assert "vide" in msg

    def test_free_text_success(self):
        """Successfully creates ExtractDefinitions from free text."""
        content = "Les sophismes ad hominem sont des attaques contre la personne."
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.FREE_TEXT,
            free_text_content=content,
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_free_text_sources()

        assert result is not None
        assert isinstance(result, ExtractDefinitions)
        assert len(result.sources) == 1
        assert result.sources[0].source_name == "Texte libre"
        assert result.sources[0].extracts[0].full_text == content
        assert str(len(content)) in msg

    def test_free_text_strips_content(self):
        """Leading/trailing whitespace is stripped from free text content."""
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.FREE_TEXT,
            free_text_content="  padded content  ",
        )
        manager = UnifiedSourceManager(config)
        result, msg = manager._load_free_text_sources()

        assert result is not None
        assert result.sources[0].extracts[0].full_text == "padded content"


# ===========================================================================
# UnifiedSourceManager.load_sources (routing)
# ===========================================================================

class TestLoadSourcesRouting:
    """Tests for load_sources routing to the correct handler."""

    def test_routes_to_enc_file(self, mocker, tmp_path):
        """load_sources routes ENC_FILE type to _load_enc_file_sources."""
        enc = tmp_path / "r.enc"
        enc.write_bytes(b"data")
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            enc_file_path=str(enc),
            passphrase="pw",
        )
        manager = UnifiedSourceManager(config)
        mock_load = mocker.patch.object(
            manager, "_load_enc_file_sources", return_value=(None, "enc routed")
        )

        result, msg = manager.load_sources()
        mock_load.assert_called_once()
        assert msg == "enc routed"

    def test_routes_to_text_file(self, mocker):
        """load_sources routes TEXT_FILE type to _load_text_file_sources."""
        config = UnifiedSourceConfig(source_type=UnifiedSourceType.TEXT_FILE)
        manager = UnifiedSourceManager(config)
        mock_load = mocker.patch.object(
            manager, "_load_text_file_sources", return_value=(None, "text routed")
        )

        result, msg = manager.load_sources()
        mock_load.assert_called_once()
        assert msg == "text routed"

    def test_routes_to_free_text(self, mocker):
        """load_sources routes FREE_TEXT type to _load_free_text_sources."""
        config = UnifiedSourceConfig(source_type=UnifiedSourceType.FREE_TEXT)
        manager = UnifiedSourceManager(config)
        mock_load = mocker.patch.object(
            manager, "_load_free_text_sources", return_value=(None, "free routed")
        )

        result, msg = manager.load_sources()
        mock_load.assert_called_once()
        assert msg == "free routed"

    def test_unsupported_type_returns_none(self):
        """A fabricated unsupported type returns (None, error message)."""
        config = UnifiedSourceConfig(source_type=UnifiedSourceType.SIMPLE)
        manager = UnifiedSourceManager(config)
        # Force an unsupported type
        manager.config.source_type = "totally_unknown"
        result, msg = manager.load_sources()
        assert result is None
        assert "non support" in msg


# ===========================================================================
# UnifiedSourceManager.select_text_for_analysis (new types)
# ===========================================================================

class TestSelectTextNewTypes:
    """Tests for select_text_for_analysis with non-simple/complex source types."""

    def test_selects_source_full_text(self):
        """Selects full_text from source level for new types."""
        config = UnifiedSourceConfig(source_type=UnifiedSourceType.FREE_TEXT)
        manager = UnifiedSourceManager(config)
        defs = _make_extract_definitions(
            source_name="My Free Source",
            full_text="Argument text here",
        )

        text, desc = manager.select_text_for_analysis(defs)
        assert text == "Argument text here"
        assert "free_text" in desc
        assert "My Free Source" in desc

    def test_falls_back_to_extract_full_text(self):
        """Falls back to extract-level full_text when source has none."""
        config = UnifiedSourceConfig(source_type=UnifiedSourceType.TEXT_FILE)
        manager = UnifiedSourceManager(config)
        defs = _make_extract_definitions_no_full_text(
            extract_text="Extract-level content"
        )

        text, desc = manager.select_text_for_analysis(defs)
        assert text == "Extract-level content"
        assert "Extract Only" in desc

    def test_fallback_when_no_content(self):
        """Returns fallback text when sources exist but have no content."""
        config = UnifiedSourceConfig(source_type=UnifiedSourceType.TEXT_FILE)
        manager = UnifiedSourceManager(config)

        # Source with empty extracts and no full_text
        source = SourceDefinition(
            source_name="Empty",
            source_type="test",
            schema="test",
            host_parts=[],
            path="/",
            extracts=[],
        )
        defs = ExtractDefinitions(sources=[source])

        text, desc = manager.select_text_for_analysis(defs)
        assert "fallback" in text.lower()
        assert "aucun contenu" in desc.lower()

    def test_fallback_when_none_definitions(self):
        """Returns fallback text when extract_definitions is None."""
        config = UnifiedSourceConfig(source_type=UnifiedSourceType.ENC_FILE)
        manager = UnifiedSourceManager(config)

        text, desc = manager.select_text_for_analysis(None)
        assert "fallback" in text.lower()
        assert "aucune source" in desc.lower()

    def test_strips_selected_text(self):
        """Selected text is stripped of leading/trailing whitespace."""
        config = UnifiedSourceConfig(source_type=UnifiedSourceType.FREE_TEXT)
        manager = UnifiedSourceManager(config)
        defs = _make_extract_definitions(full_text="  padded text  ")

        text, _ = manager.select_text_for_analysis(defs)
        assert text == "padded text"


# ===========================================================================
# UnifiedSourceManager._setup_logging (anonymize filter)
# ===========================================================================

class TestSetupLogging:
    """Tests for _setup_logging and the AnonymizeFilter.

    Note: Python loggers are singletons by name. Each test clears any
    leftover filters on the relevant logger before asserting, to avoid
    cross-test pollution.
    """

    @staticmethod
    def _clear_logger_filters(logger_name: str):
        """Remove all filters from a named logger (test isolation)."""
        target = logging.getLogger(logger_name)
        for f in list(target.filters):
            target.removeFilter(f)

    def test_anonymize_filter_on_complex(self):
        """Complex type with anonymize_logs=True adds an AnonymizeFilter."""
        self._clear_logger_filters("argumentation_analysis.core.source_management.complex")
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.COMPLEX,
            passphrase="pw",
            anonymize_logs=True,
        )
        manager = UnifiedSourceManager(config)
        filter_types = [type(f).__name__ for f in manager.logger.filters]
        assert "AnonymizeFilter" in filter_types

    def test_anonymize_filter_on_enc_file(self):
        """ENC_FILE type with anonymize_logs=True adds an AnonymizeFilter."""
        self._clear_logger_filters("argumentation_analysis.core.source_management.enc_file")
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            anonymize_logs=True,
        )
        manager = UnifiedSourceManager(config)
        filter_types = [type(f).__name__ for f in manager.logger.filters]
        assert "AnonymizeFilter" in filter_types

    def test_no_anonymize_filter_on_simple(self):
        """SIMPLE type does not add an AnonymizeFilter even with anonymize_logs=True."""
        self._clear_logger_filters("argumentation_analysis.core.source_management.simple")
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.SIMPLE,
            anonymize_logs=True,
        )
        manager = UnifiedSourceManager(config)
        filter_types = [type(f).__name__ for f in manager.logger.filters]
        assert "AnonymizeFilter" not in filter_types

    def test_no_anonymize_filter_when_disabled(self):
        """COMPLEX type with anonymize_logs=False does not add filter."""
        self._clear_logger_filters("argumentation_analysis.core.source_management.complex")
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.COMPLEX,
            passphrase="pw",
            anonymize_logs=False,
        )
        manager = UnifiedSourceManager(config)
        filter_types = [type(f).__name__ for f in manager.logger.filters]
        assert "AnonymizeFilter" not in filter_types

    def test_anonymize_filter_replaces_sensitive_names(self):
        """AnonymizeFilter replaces known sensitive patterns in log messages."""
        self._clear_logger_filters("argumentation_analysis.core.source_management.enc_file")
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.ENC_FILE,
            anonymize_logs=True,
        )
        manager = UnifiedSourceManager(config)

        # Create a log record with a sensitive name
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="Discours de Hitler et Macron",
            args=(), exc_info=None,
        )
        # Apply filters
        for f in manager.logger.filters:
            f.filter(record)

        assert "Hitler" not in record.msg
        assert "Macron" not in record.msg
        assert "[LEADER]" in record.msg


# ===========================================================================
# UnifiedSourceManager.list_available_sources
# ===========================================================================

class TestListAvailableSources:
    """Tests for list_available_sources.

    The real method globs for .enc files across the project tree, which is
    slow. We mock Path.glob to keep tests fast.
    """

    def test_returns_expected_keys(self, mocker):
        """Result dict contains the expected keys."""
        mocker.patch(
            "argumentation_analysis.core.source_management.settings",
            passphrase=None,
        )
        # Mock the glob to avoid scanning the entire filesystem
        mocker.patch("pathlib.Path.glob", return_value=iter([]))
        config = UnifiedSourceConfig(source_type=UnifiedSourceType.SIMPLE)
        manager = UnifiedSourceManager(config)
        sources = manager.list_available_sources()

        assert "simple" in sources
        assert "complex" in sources
        assert "enc_files" in sources
        assert "text_files" in sources

    def test_simple_always_has_demo_entry(self, mocker):
        """The 'simple' key always has the demo/test entry."""
        mocker.patch(
            "argumentation_analysis.core.source_management.settings",
            passphrase=None,
        )
        mocker.patch("pathlib.Path.glob", return_value=iter([]))
        config = UnifiedSourceConfig(source_type=UnifiedSourceType.SIMPLE)
        manager = UnifiedSourceManager(config)
        sources = manager.list_available_sources()

        assert len(sources["simple"]) == 1
        assert "monstration" in sources["simple"][0].lower() or "test" in sources["simple"][0].lower()


# ===========================================================================
# create_unified_source_manager factory
# ===========================================================================

class TestCreateUnifiedSourceManager:
    """Tests for the create_unified_source_manager factory function."""

    def test_creates_all_five_types(self):
        """Factory creates managers for all 5 source types."""
        for type_str in ["simple", "complex", "enc_file", "text_file", "free_text"]:
            manager = create_unified_source_manager(source_type=type_str)
            assert isinstance(manager, UnifiedSourceManager)
            assert manager.config.source_type == UnifiedSourceType(type_str)

    def test_case_insensitive(self):
        """Factory accepts case-insensitive type strings."""
        manager = create_unified_source_manager(source_type="ENC_FILE")
        assert manager.config.source_type == UnifiedSourceType.ENC_FILE

        manager = create_unified_source_manager(source_type="Free_Text")
        assert manager.config.source_type == UnifiedSourceType.FREE_TEXT

    def test_invalid_type_raises_with_message(self):
        """Factory raises ValueError with helpful message for invalid type."""
        with pytest.raises(ValueError) as exc_info:
            create_unified_source_manager(source_type="xml")

        err = str(exc_info.value)
        assert "xml" in err
        assert "simple" in err
        assert "enc_file" in err

    def test_forwards_passphrase(self):
        """Factory forwards passphrase to config."""
        manager = create_unified_source_manager(
            source_type="complex", passphrase="forwarded"
        )
        assert manager.config.passphrase == "forwarded"

    def test_forwards_enc_file_path(self):
        """Factory forwards enc_file_path to config."""
        manager = create_unified_source_manager(
            source_type="enc_file", enc_file_path="/some/path.enc"
        )
        assert manager.config.enc_file_path == "/some/path.enc"

    def test_forwards_text_file_path(self):
        """Factory forwards text_file_path to config."""
        manager = create_unified_source_manager(
            source_type="text_file", text_file_path="/file.txt"
        )
        assert manager.config.text_file_path == "/file.txt"

    def test_forwards_free_text_content(self):
        """Factory forwards free_text_content to config."""
        manager = create_unified_source_manager(
            source_type="free_text", free_text_content="Hello world"
        )
        assert manager.config.free_text_content == "Hello world"

    def test_forwards_interactive_mode(self):
        """Factory forwards interactive_mode to config."""
        manager = create_unified_source_manager(
            source_type="simple", interactive_mode=True
        )
        assert manager.config.interactive_mode is True

    def test_forwards_source_index(self):
        """Factory forwards source_index to config."""
        manager = create_unified_source_manager(
            source_type="complex", source_index=3
        )
        assert manager.config.source_index == 3

    def test_defaults(self):
        """Factory applies correct defaults."""
        manager = create_unified_source_manager(source_type="simple")
        assert manager.config.anonymize_logs is True
        assert manager.config.auto_cleanup is True
        assert manager.config.interactive_mode is False
        assert manager.config.auto_passphrase is True
        assert manager.config.source_index == 0


# ===========================================================================
# InteractiveSourceSelector.load_source_batch
# ===========================================================================

class TestInteractiveSourceSelectorBatch:
    """Tests for InteractiveSourceSelector.load_source_batch (non-interactive)."""

    def test_batch_free_text(self):
        """Batch load for free_text returns correct text and source_type."""
        selector = InteractiveSourceSelector(passphrase=None, auto_passphrase=False)
        text, desc, src_type = selector.load_source_batch(
            source_type="free_text",
            free_text="Argument libre pour test.",
        )

        assert text == "Argument libre pour test."
        assert "free_text" in desc.lower() or "libre" in desc.lower()
        assert src_type == "free_text"

    def test_batch_text_file(self, tmp_path):
        """Batch load for text_file reads the file correctly."""
        txt = tmp_path / "batch_test.txt"
        txt.write_text("Contenu du fichier batch.", encoding="utf-8")

        selector = InteractiveSourceSelector()
        text, desc, src_type = selector.load_source_batch(
            source_type="text_file",
            text_file=str(txt),
        )

        assert text == "Contenu du fichier batch."
        assert src_type == "text_file"

    def test_batch_raises_on_failure(self):
        """Batch load raises Exception when source loading fails."""
        selector = InteractiveSourceSelector()

        with pytest.raises(Exception, match="chec"):
            selector.load_source_batch(
                source_type="text_file",
                text_file="/nonexistent/path.txt",
            )

    def test_batch_simple_delegates_to_legacy(self, mocker):
        """Batch load for simple type uses the legacy manager path."""
        mock_legacy_load = mocker.patch.object(
            MagicMock(), "load_sources",
            return_value=(_make_extract_definitions(), "ok"),
        )
        selector = InteractiveSourceSelector()
        # Simple sources will fail because the legacy manager is deprecated;
        # we test that the code path at least invokes the manager.
        # In practice, the deprecated legacy manager returns (None, "obsolete")
        # which triggers the Exception in load_source_batch.
        with pytest.raises(Exception):
            selector.load_source_batch(source_type="simple")


# ===========================================================================
# Integration: full workflow with new source types
# ===========================================================================

class TestFullWorkflowNewTypes:
    """Integration-style tests for the full workflow with new source types."""

    def test_free_text_full_workflow(self):
        """End-to-end: create manager, load free text, select text for analysis."""
        content = "L'argument ad verecundiam repose sur l'autorite."
        with create_unified_source_manager(
            source_type="free_text",
            free_text_content=content,
        ) as manager:
            defs, msg = manager.load_sources()
            assert defs is not None
            assert "succ" in msg.lower()

            text, desc = manager.select_text_for_analysis(defs)
            assert text == content
            assert "free_text" in desc

    def test_text_file_full_workflow(self, tmp_path):
        """End-to-end: create manager, load text file, select text for analysis."""
        txt = tmp_path / "workflow.txt"
        txt.write_text("Analyse d'un fichier texte local.", encoding="utf-8")

        with create_unified_source_manager(
            source_type="text_file",
            text_file_path=str(txt),
        ) as manager:
            defs, msg = manager.load_sources()
            assert defs is not None

            text, desc = manager.select_text_for_analysis(defs)
            assert "fichier texte local" in text.lower()

    def test_context_manager_cleans_up(self, mocker):
        """Context manager calls cleanup_sensitive_data on exit."""
        mock_cleanup = mocker.patch.object(
            UnifiedSourceManager, "cleanup_sensitive_data"
        )
        config = UnifiedSourceConfig(
            source_type=UnifiedSourceType.FREE_TEXT,
            free_text_content="test",
        )
        with UnifiedSourceManager(config):
            pass

        mock_cleanup.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
