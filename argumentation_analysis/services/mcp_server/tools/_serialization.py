"""Serialization helpers for MCP tool results."""

from enum import Enum
from typing import Any


def safe_serialize(obj: Any) -> Any:
    """Recursively convert dataclasses, enums, sets to JSON-compatible form."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [safe_serialize(v) for v in obj]
    if isinstance(obj, set):
        return sorted(safe_serialize(v) for v in obj)
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "__dataclass_fields__"):
        return {
            k: safe_serialize(getattr(obj, k)) for k in obj.__dataclass_fields__
        }
    return str(obj)
