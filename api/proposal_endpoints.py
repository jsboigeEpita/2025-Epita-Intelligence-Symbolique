"""REST endpoints for citizen proposals, voting, deliberation, and capabilities.

Routes:
    POST /api/propose           — Submit a citizen proposal
    GET  /api/proposals         — List proposals (with optional status filter)
    GET  /api/proposals/{id}    — Get proposal detail + analysis results
    POST /api/proposals/{id}/vote — Vote on a proposal
    POST /api/deliberate        — Launch a deliberation workflow
    GET  /api/deliberate/{id}/status — Check deliberation status
    GET  /api/capabilities      — List available registry capabilities
    POST /api/workflow/custom   — Run a custom workflow on text
"""

import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from .proposal_models import (
    CapabilitiesResponse,
    CapabilityInfo,
    CustomWorkflowRequest,
    DeliberationRequest,
    DeliberationStatusResponse,
    Proposal,
    ProposalCreate,
    ProposalStatus,
    VoteCreate,
    VoteResponse,
    WorkflowResult,
)
from .proposal_service import (
    ProposalStore,
    get_proposal_store,
    run_deliberation_workflow,
)

logger = logging.getLogger(__name__)

proposal_router = APIRouter(tags=["Proposals & Deliberation"])


# ──── Proposals ────


@proposal_router.post("/propose", response_model=Proposal, status_code=201)
async def submit_proposal(data: ProposalCreate):
    """Submit a new citizen proposal for analysis and deliberation."""
    store = get_proposal_store()
    proposal = store.create_proposal(data)
    return proposal


@proposal_router.get("/proposals", response_model=List[Proposal])
async def list_proposals(
    status: Optional[ProposalStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List proposals, optionally filtered by status."""
    store = get_proposal_store()
    return store.list_proposals(status=status, limit=limit, offset=offset)


@proposal_router.get("/proposals/{proposal_id}", response_model=Proposal)
async def get_proposal(proposal_id: str):
    """Get a single proposal by ID, including analysis results."""
    store = get_proposal_store()
    proposal = store.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


# ──── Voting ────


@proposal_router.post(
    "/proposals/{proposal_id}/vote", response_model=VoteResponse, status_code=201
)
async def vote_on_proposal(proposal_id: str, vote: VoteCreate):
    """Cast a vote on a proposal (one vote per voter)."""
    store = get_proposal_store()
    proposal = store.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    result = store.add_vote(proposal_id, vote)
    if result is None:
        raise HTTPException(
            status_code=409, detail="Voter has already voted on this proposal"
        )
    return result


# ──── Deliberation ────


@proposal_router.post(
    "/deliberate", response_model=DeliberationStatusResponse, status_code=202
)
async def start_deliberation(
    request: DeliberationRequest, background_tasks: BackgroundTasks
):
    """Launch a deliberation workflow on a proposal (runs in background)."""
    store = get_proposal_store()
    proposal = store.get_proposal(request.proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    delib = store.create_deliberation(request.proposal_id, request.workflow)

    # Run workflow asynchronously
    background_tasks.add_task(
        run_deliberation_workflow,
        store,
        delib.id,
        proposal.text,
        request.workflow,
        request.options,
    )

    return delib


@proposal_router.get(
    "/deliberate/{delib_id}/status", response_model=DeliberationStatusResponse
)
async def get_deliberation_status(delib_id: str):
    """Check the status of a running or completed deliberation."""
    store = get_proposal_store()
    delib = store.get_deliberation(delib_id)
    if not delib:
        raise HTTPException(status_code=404, detail="Deliberation not found")
    return delib


# ──── Capabilities ────


@proposal_router.get("/capabilities", response_model=CapabilitiesResponse)
async def list_capabilities():
    """List available capabilities from the registry."""
    try:
        from argumentation_analysis.core.capability_registry import CapabilityRegistry

        registry = CapabilityRegistry()

        agents = []
        plugins = []
        services = []

        for name, reg in registry._registrations.items():
            info = CapabilityInfo(
                name=name,
                type=(
                    reg.component_type.value
                    if hasattr(reg.component_type, "value")
                    else str(reg.component_type)
                ),
                capabilities=(
                    list(reg.capabilities) if hasattr(reg, "capabilities") else []
                ),
            )
            if "agent" in info.type.lower():
                agents.append(info)
            elif "plugin" in info.type.lower():
                plugins.append(info)
            else:
                services.append(info)

        workflows = [
            "light",
            "standard",
            "full",
            "auto",
            "democratech",
            "debate_tournament",
            "fact_check",
        ]

        return CapabilitiesResponse(
            agents=agents, plugins=plugins, services=services, workflows=workflows
        )
    except Exception as e:
        logger.warning(f"Could not load registry: {e}")
        return CapabilitiesResponse(
            agents=[],
            plugins=[],
            services=[],
            workflows=["light", "standard", "full", "auto"],
        )


# ──── Custom Workflow ────


@proposal_router.post("/workflow/custom", response_model=WorkflowResult)
async def run_custom_workflow(request: CustomWorkflowRequest):
    """Run a custom analysis workflow on arbitrary text."""
    try:
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        result = await run_unified_analysis(
            request.text, workflow_name=request.workflow
        )

        if isinstance(result, dict):
            return WorkflowResult(
                workflow=request.workflow, status="completed", results=result
            )
        if hasattr(result, "dict"):
            return WorkflowResult(
                workflow=request.workflow, status="completed", results=result.dict()
            )
        return WorkflowResult(
            workflow=request.workflow,
            status="completed",
            results={"raw": str(result)},
        )
    except Exception as e:
        logger.error(f"Custom workflow failed: {e}")
        return WorkflowResult(workflow=request.workflow, status="failed", error=str(e))
