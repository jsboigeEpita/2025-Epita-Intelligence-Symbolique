"""#3395 — reading producers that supply the text's own content.

``first_reading`` reads the whole document once and writes its defining moves,
labelled ``first_reading``: what the text does, with verified verbatim quotes.
Distinct from ``agents.core.context`` (#3377), whose personas write what the
MODEL knows about the situation (``model_knowledge``) — two producers, two
fields, two labels.
"""

from __future__ import annotations

from argumentation_analysis.agents.core.reading.coverage_review import (
    COVERAGE_KEYS_BY_CLASS,
    CoverageItem,
    CoverageReview,
    build_coverage_review,
    coverage_family_by_unit,  # #3505 part 3
    coverage_item_line,  # #3505
    coverage_items_by_unit,  # #3505
    coverage_procede_lines,  # #3505 part 2
    coverage_review_note,
    examined_unit_ids,
    examined_unit_ids_for_class,
    extract_coverage_review,
    unit_id_at_offset,
)
from argumentation_analysis.agents.core.reading.cross_passage import (
    build_cross_passage_consistency,
    cross_passage_note,
)
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
    document_frame_for_unit,  # #3428
    document_statements_for_unit,  # #3416
    examined_unit_budget,  # #3511
    extract_first_reading,
    first_pass_move_spans,  # #3511(b) revision
    first_reading_note,
    move_kind,
    pillar_budget,
    pillar_prose,  # #3480 rework
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
    "build_cross_passage_consistency",
    "cross_passage_note",
    "build_first_reading",
    "build_first_reading_prompt",
    "defining_move_spans",
    "defining_moves",
    "document_frame_for_unit",
    "document_statements_for_unit",
    "examined_unit_budget",
    "extract_first_reading",
    "first_pass_move_spans",
    "first_reading_note",
    "move_kind",
    "pillar_budget",
    "pillar_prose",
    # #3492 — the coverage reviewer: a whole-document pass, per question.
    "COVERAGE_KEYS_BY_CLASS",
    "CoverageItem",
    "CoverageReview",
    "build_coverage_review",
    "coverage_family_by_unit",
    "coverage_item_line",
    "coverage_items_by_unit",
    "coverage_procede_lines",
    "coverage_review_note",
    "examined_unit_ids",
    "examined_unit_ids_for_class",
    "extract_coverage_review",
    "unit_id_at_offset",
]
