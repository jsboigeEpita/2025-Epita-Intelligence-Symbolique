"""Pydantic models for the citizen proposal and deliberation API."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

# ──── Enums ────


class ProposalStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    DEBATING = "debating"
    VOTING = "voting"
    DECIDED = "decided"


class DeliberationStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ──── Request Models ────


class ProposalCreate(BaseModel):
    text: str = Field(..., min_length=10, description="The proposal text")
    author: str = Field(..., min_length=1, description="Author identifier")
    title: Optional[str] = Field(None, description="Optional proposal title")
    tags: List[str] = Field(default_factory=list, description="Topic tags")


class VoteCreate(BaseModel):
    voter_id: str = Field(..., min_length=1)
    position: Literal["pour", "contre", "abstention"]
    justification: Optional[str] = None


class DeliberationRequest(BaseModel):
    proposal_id: str = Field(..., description="ID of the proposal to deliberate on")
    workflow: str = Field(
        "democratech",
        description="Workflow to use (democratech, debate_tournament, fact_check)",
    )
    options: Dict = Field(default_factory=dict, description="Workflow-specific options")


class CustomWorkflowRequest(BaseModel):
    text: str = Field(..., description="Input text for analysis")
    workflow: str = Field(
        ..., description="Workflow name (light, standard, full, auto)"
    )
    options: Dict = Field(default_factory=dict)
    # Parametric selectors (north-star R311, #903)
    fallacy_tier: Literal["taxonomy", "hybrid", "llm", "full"] = Field(
        "llm",
        description="Fallacy detection tier: taxonomy (lexical), hybrid (neural+symbolic), "
        "llm (default, LLM-based), full (all merged)",
    )
    shield_preset: Literal["off", "basic", "advanced", "output_only", "strict"] = Field(
        "off",
        description="AI Shield preset: off (default), basic, advanced, output_only, strict",
    )
    # Parametric selectors — democratech track (north-star R311, #910)
    vote_method: Literal["copeland", "approval", "stv", "schulze", "kemeny_young"] = Field(
        "copeland",
        description="Social choice voting method for governance analysis",
    )
    consensus_threshold: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="Consensus threshold (0.0–1.0) for governance metrics",
    )
    # Orchestration mode selector (north-star R311, #917)
    orchestration_mode: Literal["pipeline", "conversational", "hierarchical", "sherlock_modern"] = Field(
        "pipeline",
        description="Orchestration mode: pipeline (sequential DAG, default), "
        "conversational (multi-agent dialogue), hierarchical (strategic planning), "
        "sherlock_modern (investigation multi-agent)",
    )
    # dung_provider deferred to #908 — needs real consumption wiring


# ──── Response Models ────


class Proposal(BaseModel):
    id: str
    text: str
    author: str
    title: Optional[str] = None
    tags: List[str] = []
    submitted_at: datetime
    status: ProposalStatus = ProposalStatus.PENDING
    vote_counts: Dict[str, int] = Field(
        default_factory=lambda: {"pour": 0, "contre": 0, "abstention": 0}
    )
    analysis_results: Optional[Dict] = None


class VoteResponse(BaseModel):
    proposal_id: str
    voter_id: str
    position: str
    recorded_at: datetime


class DeliberationStatusResponse(BaseModel):
    id: str
    proposal_id: str
    workflow: str
    status: DeliberationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    results: Optional[Dict] = None
    error: Optional[str] = None


class CapabilityInfo(BaseModel):
    name: str
    type: str
    capabilities: List[str] = []


class CapabilitiesResponse(BaseModel):
    agents: List[CapabilityInfo]
    plugins: List[CapabilityInfo]
    services: List[CapabilityInfo]
    workflows: List[str]


class WorkflowResult(BaseModel):
    workflow: str
    status: str
    results: Optional[Dict] = None
    error: Optional[str] = None
