"""Pydantic models for structured fallacy identification output."""

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


def fallacy_measured_fields(
    fallacy: Dict[str, Any],
) -> Tuple[Optional[float], Optional[str]]:
    """Extract the measured (confidence, problematic_quote) pair from a detection.

    One rule for every lane (#3011 rework, R1083; #3029 moved it here so the
    plugin layer can apply it too — plugins cannot import orchestration).
    The pipeline writer (``_write_hierarchical_fallacy_to_state``), the
    conversational lane's parent-harness loop and the one-shot plugin parse
    all call this helper — no second copy of the extraction, so the lanes
    cannot disagree on which detections are filterable downstream.

    - a numeric confidence stores ``float(raw)``; anything else (absent,
      string, bool) stores ``None`` — an unmeasured confidence is not 0.0
      (#1019), and a boolean flag is not a measurement (#3015: ``True`` is
      not 1.0);
    - the quote returns ``None`` when absent or empty (``add_fallacy`` drops
      an empty one, shared_state.py:384), so one rule covers both lanes.
    """
    raw_confidence = fallacy.get("confidence")
    if isinstance(raw_confidence, bool) or not isinstance(raw_confidence, (int, float)):
        confidence = None
    else:
        confidence = float(raw_confidence)
    return confidence, fallacy.get("problematic_quote") or None


def confidence_outranks(new: Optional[float], incumbent: Optional[float]) -> bool:
    """None-safe confidence ordering for every dedup comparator (#3029).

    A detection's confidence is Optional once ``fallacy_measured_fields``
    extracts it: ``None`` means the model's reply carried no usable number,
    and a bare ``new > incumbent`` crashes on None. The ordering is the one
    the comparators always had, extended by one rule: a measured detection
    outranks an unmeasured one; between two unmeasured (or two equal)
    entries the incumbent stays — no invented tiebreak.

    Lives here (not in orchestration) because both layers compare: the
    plugin's gather-phase dedup and the pipeline's merges — one rule, no
    copies.
    """
    if new is None:
        return False
    if incumbent is None:
        return True
    return new > incumbent


class IdentifiedFallacy(BaseModel):
    """Structured result from hierarchical taxonomy-guided fallacy detection."""

    fallacy_type: str = Field(
        ..., description="The exact name of the identified fallacy from the taxonomy"
    )
    taxonomy_pk: str = Field(
        ..., description="The PK (primary key) of the fallacy in the taxonomy"
    )
    taxonomy_path: str = Field(
        default="", description="The full dot-separated path through the taxonomy"
    )
    explanation: str = Field(
        ..., description="Why this fallacy applies to the analyzed text"
    )
    problematic_quote: str = Field(
        default="",
        description="The exact quote from the text that exhibits the fallacy",
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Measured confidence score (0.0 to 1.0), or None when the model's "
            "reply carried no usable number — None and 0.0 stay distinct "
            "(#1019 family, #3029)"
        ),
    )
    navigation_trace: List[str] = Field(
        default_factory=list,
        description="List of taxonomy node PKs visited during iterative deepening",
    )
    family: str = Field(
        default="",
        description="The CSV 'Famille' column value (one of the 7 French families)",
    )
    depth: Optional[int] = Field(
        default=None,
        description=(
            "Taxonomy depth of the confirmed node. None = not measured "
            "(one-shot regime, where no descent happened)"
        ),
    )


class FallacyAnalysisResult(BaseModel):
    """Complete result of a fallacy analysis run."""

    fallacies: List[IdentifiedFallacy] = Field(default_factory=list)
    exploration_method: str = Field(
        default="one_shot",
        description="Detection method used: 'iterative_deepening' or 'one_shot'",
    )
    branches_explored: int = Field(
        default=0, description="Number of taxonomy branches explored"
    )
    total_iterations: int = Field(
        default=0, description="Total iterations across all branches"
    )
