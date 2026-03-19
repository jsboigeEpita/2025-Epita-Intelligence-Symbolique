"""Pydantic models for structured fallacy identification output."""

from typing import List, Optional
from pydantic import BaseModel, Field


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
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)"
    )
    navigation_trace: List[str] = Field(
        default_factory=list,
        description="List of taxonomy node PKs visited during iterative deepening",
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
