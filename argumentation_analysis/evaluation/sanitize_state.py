"""State sanitizer — strips sensitive fields from analysis state snapshots.

Produces a privacy-safe dict suitable for commits, dashboards, and reports.
All quantitative aggregates (counts, scores, structures) are preserved.
"""

from __future__ import annotations

import copy
from typing import Any

from argumentation_analysis.evaluation.opaque_id import opaque_id

# Fields to remove entirely from the top-level state snapshot.
_STRIP_TOP_LEVEL = {
    "raw_text",
    "full_text",
    "full_text_segment",
    "raw_text_snippet",
    "source_name",
    "document_name",
    "author",
    "date_iso",
    "url",
}

# Fields to replace with opaque IDs (key -> opaque_id(value)).
_OPAQUE_REPLACE = {"source_id"}

# Dict-valued fields where each entry's .text should be stripped but metadata kept.
_TEXT_STRIP_DICTS = {"identified_arguments", "arguments"}

# List-valued fields where each item may have sensitive sub-keys.
_TEXT_STRIP_LISTS = {
    "counter_arguments": {"counter_content", "generated_text"},
    "extracts": set(),  # no text key to strip, keep as-is
    "debate_transcripts": {"proponent_move", "opponent_move"},
}

# Fields that are purely narrative text — replace with length + cited_fields placeholder.
_NARRATIVE_FIELDS = {"narrative_synthesis"}


def _strip_text_from_dict(data: dict[str, Any], text_keys: set[str]) -> dict[str, Any]:
    """Remove text-bearing keys from a dict, keep everything else."""
    return {k: v for k, v in data.items() if k not in text_keys}


def _strip_text_from_list(
    items: list[dict[str, Any]], text_keys: set[str]
) -> list[dict[str, Any]]:
    """Remove text-bearing keys from each dict in a list."""
    return [_strip_text_from_dict(item, text_keys) for item in items]


def sanitize_state(state: dict[str, Any] | Any) -> dict[str, Any]:
    """Strip sensitive fields, keep all quantitative aggregates.

    Args:
        state: A state dict (typically from ``state_snapshot`` in a golden
               fixture) or a ``UnifiedAnalysisState`` instance.  If an object
               with a ``model_dump`` or ``dict`` method is passed, it will be
               serialized first.

    Returns:
        A new dict with all sensitive text removed, opaque IDs substituted,
        and all counts/scores/structures preserved.
    """
    # Handle Pydantic models or objects with serialization.
    if hasattr(state, "model_dump"):
        data = state.model_dump()
    elif hasattr(state, "dict"):
        data = state.dict()
    elif isinstance(state, dict):
        data = copy.deepcopy(state)
    else:
        data = dict(state)

    # 1. Strip top-level sensitive fields.
    for field in _STRIP_TOP_LEVEL:
        data.pop(field, None)

    # 2. Replace identifying fields with opaque IDs.
    for field in _OPAQUE_REPLACE:
        if field in data and isinstance(data[field], str):
            data[field] = opaque_id(data[field])

    # 3. Strip text from dict-valued fields (identified_arguments, etc.).
    for field in _TEXT_STRIP_DICTS:
        if field in data and isinstance(data[field], dict):
            data[field] = {
                k: {"text_stripped": True} if isinstance(v, str) else v
                for k, v in data[field].items()
            }

    # 4. Strip text from list-valued fields.
    for field, text_keys in _TEXT_STRIP_LISTS.items():
        if field in data and isinstance(data[field], list) and text_keys:
            data[field] = _strip_text_from_list(data[field], text_keys)

    # 5. Replace narrative text with length info.
    for field in _NARRATIVE_FIELDS:
        if field in data and isinstance(data[field], str):
            original = data[field]
            data[field] = {
                "length": len(original),
                "stripped": True,
            }

    return data
