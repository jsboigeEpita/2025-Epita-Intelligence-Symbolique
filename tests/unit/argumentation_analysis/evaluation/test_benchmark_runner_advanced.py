"""
Advanced tests for BenchmarkRunner.

Tests cover:
- Encrypted/unencrypted dataset loading
- Document text extraction
- Timeout handling
- Phase result serialization
"""

import asyncio
import gzip
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.evaluation.benchmark_runner import (
    BenchmarkRunner,
    BenchmarkResult,
)


@pytest.mark.unit
class TestDatasetLoading:
    """Test dataset loading functionality."""

    def test_load_unencrypted_dataset(self, tmp_path):
        """Test loading an unencrypted JSON dataset."""
        # Create a test dataset
        dataset = {
            "documents": [
                {
                    "id": "doc1",
                    "name": "Document 1",
                    "source_name": "source1.txt",
                    "full_text": "This is the full text of document 1.",
                },
                {
                    "id": "doc2",
                    "name": "Document 2",
                    "source_name": "source2.txt",
                    "full_text": "This is the full text of document 2.",
                },
            ]
        }

        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False)

        # Load with runner
        mock_registry = MagicMock()
        runner = BenchmarkRunner(mock_registry)
        loaded = runner.load_dataset_unencrypted(str(dataset_path))

        assert len(loaded) == 2
        assert loaded[0]["id"] == "doc1"
        assert loaded[1]["full_text"] == "This is the full text of document 2."

    def test_load_unencoded_missing_file(self, tmp_path):
        """Test that loading a missing file raises FileNotFoundError."""
        mock_registry = MagicMock()
        runner = BenchmarkRunner(mock_registry)

        with pytest.raises(FileNotFoundError):
            runner.load_dataset_unencrypted(str(tmp_path / "nonexistent.json"))

    def test_load_unencoded_invalid_json(self, tmp_path):
        """Test that loading invalid JSON raises JSONDecodeError."""
        invalid_path = tmp_path / "invalid.json"
        with open(invalid_path, "w", encoding="utf-8") as f:
            f.write("not valid json content")

        mock_registry = MagicMock()
        runner = BenchmarkRunner(mock_registry)

        with pytest.raises(json.JSONDecodeError):
            runner.load_dataset_unencrypted(str(invalid_path))

    @pytest.mark.crypto
    def test_load_encrypted_dataset(self, tmp_path):
        """Test loading an encrypted dataset (Fernet + gzip)."""
        from argumentation_analysis.core.utils.crypto_utils import (
            derive_encryption_key,
            encrypt_data_with_fernet,
        )

        # Create test dataset
        dataset = {
            "documents": [
                {
                    "id": "secret_doc1",
                    "name": "Secret Document 1",
                    "source_name": "secret1.txt",
                    "full_text": "This is secret content that must be encrypted.",
                }
            ]
        }

        json_data = json.dumps(dataset).encode("utf-8")
        compressed = gzip.compress(json_data)

        passphrase = "test_passphrase_123"
        key = derive_encryption_key(passphrase)
        assert key is not None, "Key derivation failed"

        encrypted = encrypt_data_with_fernet(compressed, key)
        assert encrypted is not None, "Encryption failed"

        # Save encrypted file
        enc_path = tmp_path / "encrypted_dataset.bin"
        with open(enc_path, "wb") as f:
            f.write(encrypted)

        # Load with runner
        mock_registry = MagicMock()
        runner = BenchmarkRunner(mock_registry)
        loaded = runner.load_dataset_encrypted(str(enc_path), passphrase)

        assert len(loaded) == 1
        assert loaded[0]["id"] == "secret_doc1"
        assert "secret content" in loaded[0]["full_text"]

    @pytest.mark.crypto
    def test_load_encrypted_wrong_passphrase(self, tmp_path):
        """Test that wrong passphrase raises ValueError."""
        from argumentation_analysis.core.utils.crypto_utils import (
            derive_encryption_key,
            encrypt_data_with_fernet,
        )

        # Create and encrypt dataset
        dataset = {"documents": [{"id": "doc1", "full_text": "Secret data"}]}
        json_data = json.dumps(dataset).encode("utf-8")
        compressed = gzip.compress(json_data)

        key = derive_encryption_key("correct_passphrase")
        assert key is not None

        encrypted = encrypt_data_with_fernet(compressed, key)
        assert encrypted is not None

        enc_path = tmp_path / "encrypted.bin"
        with open(enc_path, "wb") as f:
            f.write(encrypted)

        # Try to load with wrong passphrase
        mock_registry = MagicMock()
        runner = BenchmarkRunner(mock_registry)

        with pytest.raises(ValueError, match="Decryption failed"):
            runner.load_dataset_encrypted(str(enc_path), "wrong_passphrase")


@pytest.mark.unit
class TestDocumentExtraction:
    """Test document text extraction from dataset."""

    def test_extract_full_text(self, tmp_path):
        """Test extracting full_text from document."""
        dataset = {
            "documents": [
                {
                    "id": "doc1",
                    "name": "Document 1",
                    "full_text": "Complete document text here.",
                }
            ]
        }

        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f)

        mock_registry = MagicMock()
        runner = BenchmarkRunner(mock_registry)
        runner.load_dataset_unencrypted(str(dataset_path))

        text = runner.get_document_text(0)
        assert text == "Complete document text here."

    def test_extract_from_extracts_field(self, tmp_path):
        """Test extracting text from extracts field when full_text is missing."""
        dataset = {
            "documents": [
                {
                    "id": "doc1",
                    "name": "Document 1",
                    "extracts": [
                        {
                            "extract_text": "First extract text.",
                        },
                        {
                            "text": "Second extract text.",
                        },
                    ],
                }
            ]
        }

        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f)

        mock_registry = MagicMock()
        runner = BenchmarkRunner(mock_registry)
        runner.load_dataset_unencrypted(str(dataset_path))

        text = runner.get_document_text(0)
        assert "First extract text." in text
        assert "Second extract text." in text

    def test_extract_mixed_sources(self, tmp_path):
        """Test extracting from both full_text and extracts."""
        dataset = {
            "documents": [
                {
                    "id": "doc1",
                    "full_text": "Main document text.",
                    "extracts": [
                        {"extract_text": "Additional extract 1."},
                        {"text": "Additional extract 2."},
                    ],
                }
            ]
        }

        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f)

        mock_registry = MagicMock()
        runner = BenchmarkRunner(mock_registry)
        runner.load_dataset_unencrypted(str(dataset_path))

        text = runner.get_document_text(0)
        assert "Main document text." in text
        # When full_text exists, extracts should be ignored in current implementation
        # unless full_text is empty

    def test_extract_empty_document(self, tmp_path):
        """Test handling of document with no text."""
        dataset = {
            "documents": [
                {
                    "id": "doc1",
                    "name": "Empty Document",
                    "metadata": {"key": "value"},
                }
            ]
        }

        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f)

        mock_registry = MagicMock()
        runner = BenchmarkRunner(mock_registry)
        runner.load_dataset_unencrypted(str(dataset_path))

        text = runner.get_document_text(0)
        assert text == ""

    def test_get_document_name(self, tmp_path):
        """Test getting document name with fallbacks."""
        dataset = {
            "documents": [
                {"id": "doc1", "source_name": "source1.txt"},
                {"id": "doc2", "name": "Document 2"},
                {"id": "doc3"},  # Should use default
            ]
        }

        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f)

        mock_registry = MagicMock()
        runner = BenchmarkRunner(mock_registry)
        runner.load_dataset_unencrypted(str(dataset_path))

        assert runner.get_document_name(0) == "source1.txt"
        assert runner.get_document_name(1) == "Document 2"
        assert runner.get_document_name(2) == "doc3"  # Falls back to 'id' field

    def test_dataset_not_loaded_error(self):
        """Test that accessing dataset without loading raises RuntimeError."""
        mock_registry = MagicMock()
        runner = BenchmarkRunner(mock_registry)

        with pytest.raises(RuntimeError, match="Dataset not loaded"):
            _ = runner.dataset


@pytest.mark.unit
class TestRunCell:
    """Test run_cell execution."""

    @pytest.mark.asyncio
    async def test_run_cell_success(self, tmp_path):
        """Test successful cell execution."""
        dataset = {
            "documents": [
                {
                    "id": "doc1",
                    "name": "Test Document",
                    "full_text": "Test argument text for analysis.",
                }
            ]
        }

        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f)

        mock_registry = MagicMock()
        mock_registry.activate = MagicMock()
        mock_registry.save_env = MagicMock(return_value={})
        mock_registry.restore_env = MagicMock()

        runner = BenchmarkRunner(mock_registry)
        runner.load_dataset_unencrypted(str(dataset_path))

        # Mock the run_unified_analysis function
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis"
        ) as mock_run:
            mock_run.return_value = {
                "phases": {},
                "summary": {"completed": 1, "total": 1, "failed": 0, "skipped": 0},
                "unified_state": MagicMock(
                    get_state_snapshot=MagicMock(return_value={"test": "data"})
                ),
            }

            result = await runner.run_cell(
                workflow_name="light",
                model_name="default",
                document_index=0,
                timeout=10.0,
            )

            assert result.success is True
            assert result.workflow_name == "light"
            assert result.document_index == 0
            assert result.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_run_cell_timeout(self, tmp_path):
        """Test that timeout is handled correctly."""
        dataset = {
            "documents": [{"id": "doc1", "name": "Test", "full_text": "Test text."}]
        }

        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f)

        mock_registry = MagicMock()
        mock_registry.activate = MagicMock()
        mock_registry.save_env = MagicMock(return_value={})
        mock_registry.restore_env = MagicMock()

        runner = BenchmarkRunner(mock_registry)
        runner.load_dataset_unencrypted(str(dataset_path))

        # Mock run_unified_analysis to timeout
        async def slow_analysis(*args, **kwargs):
            await asyncio.sleep(5)
            return {}

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            side_effect=slow_analysis,
        ):
            result = await runner.run_cell(
                workflow_name="light",
                model_name="default",
                document_index=0,
                timeout=0.1,  # Very short timeout
            )

            assert result.success is False
            assert "Timeout" in result.error
            assert result.duration_seconds >= 0.1

    @pytest.mark.asyncio
    async def test_run_cell_empty_document(self, tmp_path):
        """Test handling of empty document."""
        dataset = {"documents": [{"id": "doc1", "name": "Empty Doc", "full_text": ""}]}

        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f)

        mock_registry = MagicMock()
        runner = BenchmarkRunner(mock_registry)
        runner.load_dataset_unencrypted(str(dataset_path))

        result = await runner.run_cell(
            workflow_name="light",
            model_name="default",
            document_index=0,
            timeout=10.0,
        )

        assert result.success is False
        assert "no text content" in result.error

    @pytest.mark.asyncio
    async def test_run_cell_text_truncation(self, tmp_path):
        """Test that text is truncated to max_text_chars."""
        long_text = "A" * 10000

        dataset = {
            "documents": [{"id": "doc1", "name": "Long Doc", "full_text": long_text}]
        }

        dataset_path = tmp_path / "dataset.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f)

        mock_registry = MagicMock()
        mock_registry.activate = MagicMock()
        mock_registry.save_env = MagicMock(return_value={})
        mock_registry.restore_env = MagicMock()

        runner = BenchmarkRunner(mock_registry)
        runner.load_dataset_unencrypted(str(dataset_path))

        captured_text = []

        def capture_run(text, workflow_name):
            captured_text.append(text)
            return asyncio.sleep(0)

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            side_effect=capture_run,
        ):
            await runner.run_cell(
                workflow_name="light",
                model_name="default",
                document_index=0,
                max_text_chars=100,
                timeout=10.0,
            )

            # Text should be truncated to 100 chars
            assert len(captured_text[0]) == 100


@pytest.mark.unit
class TestPhaseSerialization:
    """Test phase result serialization."""

    def test_phase_result_serialization(self):
        """Test that phase results are properly serialized."""
        from enum import Enum

        class PhaseStatus(Enum):
            COMPLETED = "completed"
            FAILED = "failed"
            SKIPPED = "skipped"

        # Create mock phase result
        mock_phase = MagicMock()
        mock_phase.status = PhaseStatus.COMPLETED
        mock_phase.capability = "test_capability"
        mock_phase.output = {"result": "test_output"}

        # Simulate serialization logic from run_cell
        serializable = {
            "status": mock_phase.status.value,
            "capability": mock_phase.capability,
            "has_output": mock_phase.output is not None,
        }

        assert serializable["status"] == "completed"
        assert serializable["capability"] == "test_capability"
        assert serializable["has_output"] is True

        # Verify it's JSON-serializable
        json_str = json.dumps(serializable)
        assert json_str is not None

    def test_phase_result_without_capability(self):
        """Test serialization of phase without capability attribute."""
        mock_phase = MagicMock()
        mock_phase.status = "completed"
        # Simulate missing capability attribute
        del mock_phase.capability
        mock_phase.output = None

        serializable = {
            "status": mock_phase.status,
            "capability": getattr(mock_phase, "capability", None),
            "has_output": hasattr(mock_phase, "output")
            and mock_phase.output is not None,
        }

        assert serializable["status"] == "completed"
        assert serializable["capability"] is None
        assert serializable["has_output"] is False
