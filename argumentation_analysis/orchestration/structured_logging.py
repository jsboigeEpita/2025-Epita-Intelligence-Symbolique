"""Structured logging for orchestration with correlation IDs.

Provides a JSON-capable log formatter and a PhaseLogger adapter that
injects ``correlation_id`` and ``phase_name`` into every log record.

Output mode is controlled by the ``LOG_FORMAT`` environment variable, read by
``formatter_from_env`` when an entry point configures logging:
- ``LOG_FORMAT=json`` → JSON lines to stderr (for production / corpus runs)
- anything else → human-readable format (default, for dev / tests)

The module itself configures nothing: the entry point installs the formatter
(``run_orchestration.setup_logging``, ``compare_orchestration_modes.main``).

Usage in orchestration modules::

    from argumentation_analysis.orchestration.structured_logging import get_phase_logger

    logger = get_phase_logger("workflow_executor", correlation_id="run-abc")
    logger.info("Phase completed", extra={"phase_name": "extract", "duration": 1.2})
"""
import json
import logging
import os
import uuid
from typing import Any, Dict, Optional

# Attributes every LogRecord carries; anything else on a record came from ``extra``.
_RECORD_ATTRIBUTES = frozenset(vars(logging.makeLogRecord({}))) | {
    "message",
    "asctime",
}


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line, with every field passed in ``extra``."""

    def format(self, record: logging.LogRecord) -> str:
        obj: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt or "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge extra fields from the record
        for key, val in vars(record).items():
            if key not in _RECORD_ATTRIBUTES and val is not None:
                obj[key] = val

        if record.exc_info and record.exc_info[1]:
            obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(obj, ensure_ascii=False, default=str)


class HumanFormatter(logging.Formatter):
    """Human-readable formatter with optional correlation/phase context."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        cid = getattr(record, "correlation_id", None)
        phase = getattr(record, "phase_name", None)
        prefix_parts = []
        if cid:
            prefix_parts.append(f"[{cid[:8]}]")
        if phase:
            prefix_parts.append(f"[{phase}]")
        if prefix_parts:
            return " ".join(prefix_parts) + " " + base
        return base


class PhaseLogger(logging.LoggerAdapter):
    """Logger adapter that injects correlation_id and phase_name."""

    def __init__(
        self,
        logger: logging.Logger,
        correlation_id: Optional[str] = None,
        phase_name: Optional[str] = None,
    ):
        extra: Dict[str, Any] = {}
        if correlation_id:
            extra["correlation_id"] = correlation_id
        if phase_name:
            extra["phase_name"] = phase_name
        super().__init__(logger, extra)

    def process(self, msg: str, kwargs: Any) -> tuple:
        extra = dict(self.extra)
        # Allow per-call overrides via extra kwarg
        if "extra" in kwargs:
            extra.update(kwargs["extra"])
        kwargs["extra"] = extra
        return msg, kwargs

    def with_phase(self, phase_name: str) -> "PhaseLogger":
        """Return a child adapter with an updated phase_name."""
        return PhaseLogger(
            self.logger,
            correlation_id=self.extra.get("correlation_id"),
            phase_name=phase_name,
        )


def generate_correlation_id() -> str:
    """Generate a new correlation ID (UUID4)."""
    return str(uuid.uuid4())


def get_phase_logger(
    name: str,
    correlation_id: Optional[str] = None,
    phase_name: Optional[str] = None,
) -> PhaseLogger:
    """Get a PhaseLogger for the given module name.

    Configures nothing: the output format is the entry point's, see
    ``formatter_from_env``.
    """
    logger = logging.getLogger(name)
    return PhaseLogger(logger, correlation_id=correlation_id, phase_name=phase_name)


def formatter_from_env(fmt: str, datefmt: Optional[str] = None) -> logging.Formatter:
    """The formatter an entry point installs, chosen by ``LOG_FORMAT`` when called.

    ``LOG_FORMAT=json`` gives ``JsonFormatter``. Anything else gives
    ``HumanFormatter(fmt)``, which prefixes the correlation id and phase name a
    ``PhaseLogger`` attaches, and prints other records as ``fmt`` alone would.
    """
    if os.environ.get("LOG_FORMAT", "").lower() == "json":
        return JsonFormatter()
    return HumanFormatter(fmt, datefmt=datefmt)
