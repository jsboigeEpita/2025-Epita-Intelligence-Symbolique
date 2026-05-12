"""Workflow checkpoint manager for resumable pipeline execution.

After each DAG level, the executor writes a checkpoint capturing completed
phases and their serializable outputs.  On resume, completed phases are
skipped and their outputs injected into the execution context.

Checkpoint file schema::

    {
      "opaque_id": "abc12345",
      "workflow": "spectacular",
      "completed_phases": ["extract", "quality"],
      "phase_outputs": {
        "extract": {"status": "completed", "output_json": "...", "duration_s": 1.2},
        "quality": {"status": "completed", "output_json": "...", "duration_s": 0.8}
      },
      "state_snapshot": { ... },
      "timestamp": "2026-05-12T..."
    }
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("checkpoint")


def _try_serialize(value: Any) -> Any:
    """Attempt to JSON-serialize a value.  Returns the raw value on success."""
    json.dumps(value, default=str)
    return value


class CheckpointManager:
    """Manages per-document workflow checkpoints on disk.

    Writes are atomic (tempfile + os.replace) to avoid partial writes on crash.
    """

    def __init__(self, checkpoint_dir: Path) -> None:
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, doc_id: str) -> Path:
        return self.checkpoint_dir / f"{doc_id}.checkpoint.json"

    def save(
        self,
        doc_id: str,
        workflow: str,
        completed_phases: List[str],
        phase_outputs: Dict[str, Dict[str, Any]],
        state_snapshot: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Atomically write a checkpoint file."""
        data = {
            "opaque_id": doc_id,
            "workflow": workflow,
            "completed_phases": completed_phases,
            "phase_outputs": phase_outputs,
            "state_snapshot": state_snapshot,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        target = self._path(doc_id)
        fd, tmp_path = tempfile.mkstemp(dir=str(self.checkpoint_dir), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, target)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        logger.debug("Checkpoint saved: %s (%d phases)", doc_id, len(completed_phases))

    def load(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Load a checkpoint.  Returns None if not found or corrupt."""
        path = self._path(doc_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Corrupt checkpoint %s: %s", doc_id, exc)
            return None

    def remove(self, doc_id: str) -> None:
        """Remove checkpoint after successful completion."""
        path = self._path(doc_id)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Failed to remove checkpoint %s: %s", doc_id, exc)

    def list_incomplete(self) -> List[str]:
        """Return doc_ids that have checkpoint files (incomplete runs)."""
        return sorted(
            p.stem.replace(".checkpoint", "")
            for p in self.checkpoint_dir.glob("*.checkpoint.json")
        )


def serialize_phase_result(
    phase_name: str,
    status: str,
    output: Any,
    duration: float,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a serializable dict for one phase result.

    Non-serializable outputs are stored as ``None`` (phase will re-run on resume).
    """
    output_json = None
    if output is not None and status == "completed":
        try:
            output_json = json.dumps(output, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            output_json = None
    return {
        "status": status,
        "output_json": output_json,
        "duration_s": round(duration, 3),
        "error": error,
    }


def deserialize_phase_outputs(
    phase_outputs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Deserialize all phase outputs from checkpoint.

    Returns a dict of phase_name → deserialized output (or None).
    Phases with ``output_json=None`` are excluded (will re-run).
    """
    result = {}
    for name, data in phase_outputs.items():
        raw = data.get("output_json")
        if raw is not None:
            try:
                result[name] = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Corrupt output for phase '%s', will re-run", name)
        else:
            result[name] = None
    return result
