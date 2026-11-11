# -*- coding: utf-8 -*-
"""Render corpus metadata fields into LLM prompts without lying to the model.

#3512 — the corpus metadata carries the literal ``unknown`` for fields it did
not record. Formatting it verbatim into a prompt makes the model treat the
placeholder as data: the stakes extractor copied it as a stakeholder name.
One helper renders every metadata field, so no prompt builder formats the
literal on its own.
"""

from typing import Any, Optional

NOT_RECORDED_IN_METADATA = (
    "not recorded in the corpus metadata — identify it from the text if the "
    "text names it, empty otherwise"
)


def metadata_prompt_value(
    metadata: Any, field: str, fallback_field: Optional[str] = None
) -> str:
    """Return the prompt-facing value of ``metadata[field]``.

    A recorded value passes through unchanged. A missing, empty or
    ``unknown`` value falls back to ``fallback_field`` when given, then
    renders as an instruction instead of a placeholder: the field is not
    recorded, identify it from the text if the text names it, empty
    otherwise.
    """
    if isinstance(metadata, dict):
        for key in (field, fallback_field):
            if key is None:
                continue
            value = str(metadata.get(key, "") or "").strip()
            if value and value.lower() != "unknown":
                return value
    return NOT_RECORDED_IN_METADATA


__all__ = ["NOT_RECORDED_IN_METADATA", "metadata_prompt_value"]
