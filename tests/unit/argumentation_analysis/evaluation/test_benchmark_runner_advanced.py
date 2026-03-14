"""
Advanced tests for benchmark_runner.py (dataset loading, encrypted datasets).
"""

import gzip
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from argumentation_analysis.evaluation.benchmark_runner import BenchmarkRunner
from argumentation_analysis.evaluation.model_registry import ModelRegistry, ModelConfig


# =====================================================================
# Dataset Loading Tests
# =====================================================================


class TestDatasetLoading:
    """Tests for dataset loading functionality."""

    def test_load_dataset_unencrypted(self, tmp_path):
        """Verify unencrypted JSON dataset loading."""
        dataset_path = tmp_path / "dataset.json"
        dataset = [
            {"source_name": "Doc1", "full_text": "Text 1", "extracts": []},
            {"source_name": "Doc2", "full_text": "Text 2", "extracts": []},
        ]
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f)

        reg = ModelRegistry()
        runner = BenchmarkRunner(reg)
        loaded = runner.load_dataset_unencrypted(str(dataset_path))

        assert len(loaded) == 2
        assert loaded[0]["source_name"] == "Doc1"

    def test_load_dataset_unencrypted_not_found(self):
        """Verify missing unencrypted dataset raises error."""
        reg = ModelRegistry()
        runner = BenchmarkRunner(reg)

        with pytest.raises(FileNotFoundError):
            runner.load_dataset_unencrypted("/nonexistent/path.json")

    @pytest.mark.skip(reason="Encryption tests depend on environment-specific crypto configuration")
    def test_load_dataset_encrypted_success(self, tmp_path):
        """Verify encrypted dataset loading with correct passphrase."""
        from argumentation_analysis.core.utils.crypto_utils import (
            derive_encryption_key,
            encrypt_data_with_fernet,
        )

        # Create test data
        dataset = [
            {"source_name": "Secret Doc", "full_text": "Secret text", "extracts": []}
        ]
        json_data = json.dumps(dataset).encode("utf-8")

        # Encrypt
        passphrase = "test_passphrase_123"
        key = derive_encryption_key(passphrase)
        encrypted = encrypt_data_with_fernet(json_data, key)
        compressed = gzip.compress(encrypted)

        enc_path = tmp_path / "dataset.encrypted"
        with open(enc_path, "wb") as f:
            f.write(compressed)

        # Load
        reg = ModelRegistry()
        runner = BenchmarkRunner(reg)
        loaded = runner.load_dataset_encrypted(str(enc_path), passphrase)

        assert len(loaded) == 1
        assert loaded[0]["source_name"] == "Secret Doc"

    @pytest.mark.skip(reason="Encryption tests depend on environment-specific crypto configuration")
    def test_load_dataset_encrypted_wrong_passphrase(self, tmp_path):
        """Verify wrong passphrase raises error."""
        from argumentation_analysis.core.utils.crypto_utils import (
            derive_encryption_key,
            encrypt_data_with_fernet,
        )

        dataset = [{"source_name": "Doc", "full_text": "Text", "extracts": []}]
        json_data = json.dumps(dataset).encode("utf-8")

        key = derive_encryption_key("correct_pass")
        encrypted = encrypt_data_with_fernet(json_data, key)
        compressed = gzip.compress(encrypted)

        enc_path = tmp_path / "dataset.encrypted"
        with open(enc_path, "wb") as f:
            f.write(compressed)

        reg = ModelRegistry()
        runner = BenchmarkRunner(reg)

        with pytest.raises(ValueError, match="Decryption failed"):
            runner.load_dataset_encrypted(str(enc_path), "wrong_passphrase")

    def test_load_dataset_encrypted_file_not_found(self):
        """Verify missing encrypted dataset raises error."""
        reg = ModelRegistry()
        runner = BenchmarkRunner(reg)

        with pytest.raises(FileNotFoundError):
            runner.load_dataset_encrypted("/nonexistent/file.enc", "pass")

    def test_get_document_text_from_full_text(self):
        """Verify text extraction from full_text field."""
        reg = ModelRegistry()
        runner = BenchmarkRunner(reg)
        runner._dataset = [
            {"source_name": "Doc1", "full_text": "Complete document text here."}
        ]

        text = runner.get_document_text(0)
        assert "Complete document" in text

    def test_get_document_text_from_extracts(self):
        """Verify text extraction from extracts when full_text is missing."""
        reg = ModelRegistry()
        runner = BenchmarkRunner(reg)
        runner._dataset = [
            {
                "source_name": "Doc1",
                "full_text": None,
                "extracts": [
                    {"extract_text": "First extract."},
                    {"text": "Second extract."},
                ],
            }
        ]

        text = runner.get_document_text(0)
        assert "First extract" in text
        assert "Second extract" in text

    def test_get_document_text_mixed_sources(self):
        """Verify text extraction combines full_text and extracts."""
        reg = ModelRegistry()
        runner = BenchmarkRunner(reg)
        runner._dataset = [
            {
                "source_name": "Doc1",
                "full_text": "Main text.",
                "extracts": [{"extract_text": "Additional text."}],
            }
        ]

        text = runner.get_document_text(0)
        assert "Main text" in text

    def test_get_document_text_empty_fallback(self):
        """Verify empty text when both sources are missing."""
        reg = ModelRegistry()
        runner = BenchmarkRunner(reg)
        runner._dataset = [
            {"source_name": "Doc1", "full_text": None, "extracts": []}
        ]

        text = runner.get_document_text(0)
        assert text == ""

    def test_get_document_name_from_source_name(self):
        """Verify document name from source_name field."""
        reg = ModelRegistry()
        runner = BenchmarkRunner(reg)
        runner._dataset = [{"source_name": "My Document"}]

        name = runner.get_document_name(0)
        assert name == "My Document"

    def test_get_document_name_fallback_to_name(self):
        """Verify document name fallback to 'name' field."""
        reg = ModelRegistry()
        runner = BenchmarkRunner(reg)
        runner._dataset = [{"name": "Fallback Name"}]

        name = runner.get_document_name(0)
        assert name == "Fallback Name"

    def test_get_document_name_fallback_to_index(self):
        """Verify document name fallback to index."""
        reg = ModelRegistry()
        runner = BenchmarkRunner(reg)
        runner._dataset = [{}]

        name = runner.get_document_name(0)
        assert name == "document_0"

    @pytest.mark.asyncio
    async def test_run_cell_truncates_long_text(self):
        """Verify text is truncated when max_text_chars is set."""
        reg = ModelRegistry()
        reg.register("mock", ModelConfig("mock", "http://mock", "key"))
        runner = BenchmarkRunner(reg)
        runner._dataset = [
            {"source_name": "Doc1", "full_text": "A" * 10000}
        ]

        mock_result = {
            "phases": {"p1": MagicMock(status=MagicMock(value="completed"), capability="test", output={})},
            "summary": {"completed": 1, "total": 1, "failed": 0, "skipped": 0},
            "unified_state": None,
        }

        with patch("argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
                   new_callable=AsyncMock, return_value=mock_result) as mock_run:
            await runner.run_cell("light", "mock", 0, max_text_chars=100)

        # Verify the text passed to analysis was truncated
        call_args = mock_run.call_args[0]
        assert len(call_args[0]) <= 100


# =====================================================================
# Model Registry Advanced Tests
# =====================================================================


class TestModelRegistryAdvanced:
    """Advanced tests for ModelRegistry."""

    def test_from_env_default_endpoint(self, monkeypatch):
        """Verify from_env creates default model from OPENAI_* vars."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "gpt-test")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://test.api/v1")

        reg = ModelRegistry.from_env()
        models = reg.list_models()
        assert "default" in models
        assert models["default"].model_id == "gpt-test"

    def test_from_env_numbered_endpoints(self, monkeypatch):
        """Verify from_env loads numbered endpoints."""
        monkeypatch.setenv("OPENAI_API_KEY", "key1")
        monkeypatch.setenv("OPENAI_API_KEY_2", "key2")
        monkeypatch.setenv("OPENAI_BASE_URL_2", "https://endpoint2/v1")
        monkeypatch.setenv("OPENAI_ENDPOINT_NAME_2", "Endpoint 2")

        reg = ModelRegistry.from_env()
        models = reg.list_models()
        assert "endpoint-2" in models

    def test_from_env_multiple_numbered_endpoints(self, monkeypatch):
        """Verify from_env loads multiple numbered endpoints."""
        monkeypatch.setenv("OPENAI_API_KEY", "key1")

        # Add endpoints 2, 3, and 4
        for i in range(2, 5):
            monkeypatch.setenv(f"OPENAI_API_KEY_{i}", f"key{i}")
            monkeypatch.setenv(f"OPENAI_BASE_URL_{i}", f"https://endpoint{i}/v1")
            monkeypatch.setenv(f"OPENAI_ENDPOINT_NAME_{i}", f"Endpoint {i}")

        reg = ModelRegistry.from_env()
        models = reg.list_models()

        assert "endpoint-2" in models
        assert "endpoint-3" in models
        assert "endpoint-4" in models

    def test_from_env_openrouter(self, monkeypatch):
        """Verify from_env loads OpenRouter configuration."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "or-key-123")
        monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/v1")

        reg = ModelRegistry.from_env()
        models = reg.list_models()
        assert "openrouter" in models
        assert "openrouter" in models["openrouter"].base_url

    def test_from_env_no_api_keys(self, monkeypatch):
        """Verify from_env works with no API keys set."""
        # Clear all relevant env vars (primary + numbered + openrouter)
        for key in ["OPENAI_API_KEY", "OPENROUTER_API_KEY"] + \
                   [f"OPENAI_API_KEY_{i}" for i in range(2, 10)] + \
                   [f"OPENAI_BASE_URL_{i}" for i in range(2, 10)] + \
                   [f"OPENAI_ENDPOINT_NAME_{i}" for i in range(2, 10)]:
            monkeypatch.delenv(key, raising=False)

        reg = ModelRegistry.from_env()
        models = reg.list_models()
        # Should have no models if no keys are set
        assert len(models) == 0

    def test_activate_switches_env_vars(self, monkeypatch):
        """Verify activate() switches the active model environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "original_key")
        monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "original_model")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://original/v1")

        reg = ModelRegistry()
        reg.register("new_model", ModelConfig(
            model_id="new-model-id",
            base_url="https://new/v1",
            api_key="new-key"
        ))

        original_env = reg.save_env()
        reg.activate("new_model")

        assert os.environ.get("OPENAI_CHAT_MODEL_ID") == "new-model-id"
        assert os.environ.get("OPENAI_BASE_URL") == "https://new/v1"
        assert os.environ.get("OPENAI_API_KEY") == "new-key"

        # Restore
        reg.restore_env(original_env)
        assert os.environ.get("OPENAI_CHAT_MODEL_ID") == "original_model"

    def test_restore_env_clears_values(self, monkeypatch):
        """Verify restore_env clears vars when saved value is None."""
        monkeypatch.setenv("OPENAI_API_KEY", "temp_key")

        reg = ModelRegistry()
        saved = reg.save_env()

        # Manually set a value to None in saved snapshot
        saved["OPENAI_API_KEY"] = None
        os.environ["OPENAI_API_KEY"] = "different_key"

        reg.restore_env(saved)

        # Should be cleared
        assert os.environ.get("OPENAI_API_KEY") is None

    def test_model_config_defaults(self):
        """Verify ModelConfig default values."""
        from argumentation_analysis.evaluation.model_registry import ModelConfig

        cfg = ModelConfig(model_id="x", base_url="y", api_key="z")
        assert cfg.display_name == "x"  # Defaults to model_id
        assert cfg.cost_per_1k_tokens == 0.0
        assert cfg.is_thinking_model is False
        assert cfg.max_tokens is None

    def test_model_config_custom_fields(self):
        """Verify ModelConfig custom field values."""
        from argumentation_analysis.evaluation.model_registry import ModelConfig

        cfg = ModelConfig(
            model_id="x",
            base_url="y",
            api_key="z",
            display_name="Custom Name",
            cost_per_1k_tokens=0.002,
            is_thinking_model=True,
            max_tokens=4096,
        )
        assert cfg.display_name == "Custom Name"
        assert cfg.cost_per_1k_tokens == 0.002
        assert cfg.is_thinking_model is True
        assert cfg.max_tokens == 4096
