"""#3395 — reading producers that supply the text's own content.

``first_reading`` reads the whole document once and writes its defining moves,
labelled ``first_reading``: what the text does, with verified verbatim quotes.
Distinct from ``agents.core.context`` (#3377), whose personas write what the
MODEL knows about the situation (``model_knowledge``) — two producers, two
fields, two labels.
"""

from __future__ import annotations

from argumentation_analysis.agents.core.reading.first_reading import (
    ANCHOR_MIN_RUN,
    ANCHOR_MIN_SHARE,
    ANCHOR_RELOCATED,
    ANCHOR_UNANCHORED,
    FIRST_READING_BASIS,
    MAX_MOVES,
    MAX_PILLARS,  # #3432
    MOVE_KINDS,
    DefiningMove,
    FirstReading,
    anchor_quote_in,  # #3415 ask 4
    build_first_reading,
    build_first_reading_prompt,
    defining_move_spans,
    defining_moves,
    document_statements_for_unit,  # #3416
    extract_first_reading,
    first_reading_note,
    move_kind,
)

__all__ = [
    "ANCHOR_MIN_RUN",
    "ANCHOR_MIN_SHARE",
    "ANCHOR_RELOCATED",
    "ANCHOR_UNANCHORED",
    "FIRST_READING_BASIS",
    "MAX_MOVES",
    "MAX_PILLARS",
    "MOVE_KINDS",
    "DefiningMove",
    "FirstReading",
    "anchor_quote_in",
    "build_first_reading",
    "build_first_reading_prompt",
    "defining_move_spans",
    "defining_moves",
    "document_statements_for_unit",
    "extract_first_reading",
    "first_reading_note",
    "move_kind",
]
