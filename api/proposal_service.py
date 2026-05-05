"""In-memory proposal store and deliberation orchestrator.

Provides CRUD for proposals, voting, and async workflow execution.
Uses an in-memory dict (no persistence) — suitable for demo/dev.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from .proposal_models import (
    DeliberationStatus,
    DeliberationStatusResponse,
    Proposal,
    ProposalCreate,
    ProposalStatus,
    VoteCreate,
    VoteResponse,
)

logger = logging.getLogger(__name__)


class ProposalStore:
    """In-memory store for proposals, votes, and deliberations."""

    def __init__(self):
        self._proposals: Dict[str, Proposal] = {}
        self._votes: Dict[str, List[VoteResponse]] = {}  # proposal_id -> votes
        self._deliberations: Dict[str, DeliberationStatusResponse] = {}

    # ──── Proposals ────

    def create_proposal(self, data: ProposalCreate) -> Proposal:
        proposal_id = str(uuid.uuid4())[:8]
        proposal = Proposal(
            id=proposal_id,
            text=data.text,
            author=data.author,
            title=data.title or data.text[:60],
            tags=data.tags,
            submitted_at=datetime.utcnow(),
        )
        self._proposals[proposal_id] = proposal
        self._votes[proposal_id] = []
        logger.info(f"Created proposal {proposal_id} by {data.author}")
        return proposal

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        return self._proposals.get(proposal_id)

    def list_proposals(
        self,
        status: Optional[ProposalStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Proposal]:
        proposals = list(self._proposals.values())
        if status:
            proposals = [p for p in proposals if p.status == status]
        proposals.sort(key=lambda p: p.submitted_at, reverse=True)
        return proposals[offset : offset + limit]

    def update_status(self, proposal_id: str, status: ProposalStatus):
        if proposal_id in self._proposals:
            self._proposals[proposal_id].status = status

    def set_analysis_results(self, proposal_id: str, results: Dict):
        if proposal_id in self._proposals:
            self._proposals[proposal_id].analysis_results = results

    # ──── Votes ────

    def add_vote(self, proposal_id: str, vote: VoteCreate) -> Optional[VoteResponse]:
        if proposal_id not in self._proposals:
            return None

        # Check duplicate voter
        existing = [v for v in self._votes[proposal_id] if v.voter_id == vote.voter_id]
        if existing:
            return None  # Already voted

        response = VoteResponse(
            proposal_id=proposal_id,
            voter_id=vote.voter_id,
            position=vote.position,
            recorded_at=datetime.utcnow(),
        )
        self._votes[proposal_id].append(response)

        # Update counts
        self._proposals[proposal_id].vote_counts[vote.position] += 1
        return response

    def get_votes(self, proposal_id: str) -> List[VoteResponse]:
        return self._votes.get(proposal_id, [])

    # ──── Deliberations ────

    def create_deliberation(
        self, proposal_id: str, workflow: str
    ) -> DeliberationStatusResponse:
        delib_id = str(uuid.uuid4())[:8]
        delib = DeliberationStatusResponse(
            id=delib_id,
            proposal_id=proposal_id,
            workflow=workflow,
            status=DeliberationStatus.QUEUED,
            started_at=datetime.utcnow(),
        )
        self._deliberations[delib_id] = delib
        return delib

    def get_deliberation(self, delib_id: str) -> Optional[DeliberationStatusResponse]:
        return self._deliberations.get(delib_id)

    def update_deliberation(
        self,
        delib_id: str,
        status: DeliberationStatus,
        results: Optional[Dict] = None,
        error: Optional[str] = None,
    ):
        if delib_id in self._deliberations:
            self._deliberations[delib_id].status = status
            if results:
                self._deliberations[delib_id].results = results
            if error:
                self._deliberations[delib_id].error = error
            if status in (DeliberationStatus.COMPLETED, DeliberationStatus.FAILED):
                self._deliberations[delib_id].completed_at = datetime.utcnow()


async def run_deliberation_workflow(
    store: ProposalStore,
    delib_id: str,
    proposal_text: str,
    workflow: str,
    options: Dict,
):
    """Execute a deliberation workflow asynchronously.

    Tries to use UnifiedPipeline if available, falls back to a simple summary.
    """
    store.update_deliberation(delib_id, DeliberationStatus.RUNNING)
    proposal_id = store.get_deliberation(delib_id).proposal_id
    store.update_status(proposal_id, ProposalStatus.ANALYZING)

    try:
        # Try to run via UnifiedPipeline
        results = await _run_pipeline(proposal_text, workflow, options)
        store.update_deliberation(
            delib_id, DeliberationStatus.COMPLETED, results=results
        )
        store.set_analysis_results(proposal_id, results)
        store.update_status(proposal_id, ProposalStatus.DECIDED)
        logger.info(f"Deliberation {delib_id} completed successfully")
    except Exception as e:
        logger.error(f"Deliberation {delib_id} failed: {e}")
        store.update_deliberation(delib_id, DeliberationStatus.FAILED, error=str(e))
        store.update_status(proposal_id, ProposalStatus.PENDING)


async def _run_pipeline(text: str, workflow: str, options: Dict) -> Dict:
    """Run the unified pipeline for analysis."""
    try:
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        result = await run_unified_analysis(text, workflow_name=workflow)
        # Extract serializable results
        if hasattr(result, "dict"):
            return result.dict()
        if isinstance(result, dict):
            return result
        return {"raw_result": str(result)}
    except ImportError:
        logger.warning("UnifiedPipeline not available, using stub results")
        return {
            "workflow": workflow,
            "text_excerpt": text[:200],
            "note": "Pipeline not available — stub result",
        }
    except Exception as e:
        logger.warning(f"Pipeline execution failed: {e}, using stub")
        return {
            "workflow": workflow,
            "text_excerpt": text[:200],
            "error": str(e),
            "note": "Pipeline failed — stub result",
        }


# Singleton store
_store: Optional[ProposalStore] = None


def get_proposal_store() -> ProposalStore:
    global _store
    if _store is None:
        _store = ProposalStore()
    return _store
