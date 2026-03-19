"""
Benchmark runner: execute a single (workflow × model × document) cell.

Wraps run_unified_analysis() with timing, token tracking, and error handling.
"""

import asyncio
import gzip
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from argumentation_analysis.evaluation.model_registry import ModelRegistry, ModelConfig

logger = logging.getLogger("evaluation.benchmark_runner")


@dataclass
class BenchmarkResult:
    """Result of a single benchmark cell execution."""

    workflow_name: str
    model_name: str
    document_index: int
    document_name: str
    success: bool
    duration_seconds: float
    phases_completed: int
    phases_total: int
    phases_failed: int
    phases_skipped: int
    error: Optional[str] = None
    state_snapshot: Optional[Dict[str, Any]] = None
    phase_results: Optional[Dict[str, Any]] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            from datetime import datetime

            self.timestamp = datetime.now().isoformat()


class BenchmarkRunner:
    """Execute benchmark cells (workflow × model × document)."""

    def __init__(
        self, model_registry: ModelRegistry, dataset_path: Optional[str] = None
    ):
        self.model_registry = model_registry
        self._dataset: Optional[List[Dict[str, Any]]] = None
        self._dataset_path = dataset_path

    def load_dataset_unencrypted(self, path: str) -> List[Dict[str, Any]]:
        """Load the unencrypted dataset JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._dataset = data.get("documents", [])
        logger.info(f"Loaded {len(self._dataset)} documents from {path}")
        return self._dataset

    def load_dataset_encrypted(
        self, path: str, passphrase: str
    ) -> List[Dict[str, Any]]:
        """Load the encrypted dataset (Fernet + gzip)."""
        from argumentation_analysis.core.utils.crypto_utils import (
            derive_encryption_key,
            decrypt_data_with_fernet,
        )

        key = derive_encryption_key(passphrase)
        if key is None:
            raise ValueError("Failed to derive encryption key")

        with open(path, "rb") as f:
            enc_data = f.read()

        dec_data = decrypt_data_with_fernet(enc_data, key)
        if dec_data is None:
            raise ValueError("Decryption failed — wrong passphrase?")

        json_data = gzip.decompress(dec_data)
        data = json.loads(json_data)
        self._dataset = data.get("documents", [])
        logger.info(f"Loaded {len(self._dataset)} documents from encrypted {path}")
        return self._dataset

    @property
    def dataset(self) -> List[Dict[str, Any]]:
        if self._dataset is None:
            raise RuntimeError("Dataset not loaded. Call load_dataset_*() first.")
        return self._dataset

    def get_document_text(self, index: int) -> str:
        """Get the full text of a document by index."""
        doc = self.dataset[index]
        text = doc.get("full_text") or ""
        if not text:
            # Try extracting from extracts
            for ext in doc.get("extracts", []):
                ext_text = ext.get("extract_text") or ext.get("text") or ""
                if ext_text:
                    text += ext_text + "\n\n"
        return text

    def get_document_name(self, index: int) -> str:
        doc = self.dataset[index]
        return doc.get("source_name", doc.get("name", f"document_{index}"))

    async def run_cell(
        self,
        workflow_name: str,
        model_name: str,
        document_index: int,
        max_text_chars: int = 5000,
        timeout: float = 120.0,
    ) -> BenchmarkResult:
        """
        Execute a single benchmark cell.

        Args:
            workflow_name: Name of the workflow to run.
            model_name: Registered model name.
            document_index: Index into the loaded dataset.
            max_text_chars: Truncate input text to this length (controls cost).
            timeout: Max seconds for the entire analysis.
        """
        doc_name = self.get_document_name(document_index)
        text = self.get_document_text(document_index)

        if not text:
            return BenchmarkResult(
                workflow_name=workflow_name,
                model_name=model_name,
                document_index=document_index,
                document_name=doc_name,
                success=False,
                duration_seconds=0.0,
                phases_completed=0,
                phases_total=0,
                phases_failed=0,
                phases_skipped=0,
                error="Document has no text content",
            )

        # Truncate for cost control
        if len(text) > max_text_chars:
            text = text[:max_text_chars]

        # Switch model
        saved_env = self.model_registry.save_env()
        try:
            self.model_registry.activate(model_name)

            from argumentation_analysis.orchestration.unified_pipeline import (
                run_unified_analysis,
            )

            start = time.monotonic()
            result = await asyncio.wait_for(
                run_unified_analysis(text, workflow_name=workflow_name),
                timeout=timeout,
            )
            elapsed = time.monotonic() - start

            phases = result.get("phases", {})
            summary = result.get("summary", {})
            state_snap = result.get("unified_state")
            if hasattr(state_snap, "get_state_snapshot"):
                # Use summarize=False so judge sees actual data (arguments, scores, etc.)
                # not just counts (argument_count=0 hides real analysis output)
                state_snap = state_snap.get_state_snapshot(summarize=False)

            # Serialize phase results (strip non-serializable)
            serializable_phases = {}
            for pname, presult in phases.items():
                serializable_phases[pname] = {
                    "status": (
                        presult.status.value
                        if hasattr(presult.status, "value")
                        else str(presult.status)
                    ),
                    "capability": (
                        presult.capability if hasattr(presult, "capability") else None
                    ),
                    "has_output": (
                        presult.output is not None
                        if hasattr(presult, "output")
                        else False
                    ),
                }

            return BenchmarkResult(
                workflow_name=workflow_name,
                model_name=model_name,
                document_index=document_index,
                document_name=doc_name,
                success=True,
                duration_seconds=elapsed,
                phases_completed=summary.get("completed", 0),
                phases_total=summary.get("total", len(phases)),
                phases_failed=summary.get("failed", 0),
                phases_skipped=summary.get("skipped", 0),
                state_snapshot=state_snap if isinstance(state_snap, dict) else None,
                phase_results=serializable_phases,
            )

        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start
            return BenchmarkResult(
                workflow_name=workflow_name,
                model_name=model_name,
                document_index=document_index,
                document_name=doc_name,
                success=False,
                duration_seconds=elapsed,
                phases_completed=0,
                phases_total=0,
                phases_failed=0,
                phases_skipped=0,
                error=f"Timeout after {timeout}s",
            )
        except Exception as e:
            elapsed = time.monotonic() - start if "start" in dir() else 0.0
            return BenchmarkResult(
                workflow_name=workflow_name,
                model_name=model_name,
                document_index=document_index,
                document_name=doc_name,
                success=False,
                duration_seconds=elapsed,
                phases_completed=0,
                phases_total=0,
                phases_failed=0,
                phases_skipped=0,
                error=str(e),
            )
        finally:
            self.model_registry.restore_env(saved_env)
