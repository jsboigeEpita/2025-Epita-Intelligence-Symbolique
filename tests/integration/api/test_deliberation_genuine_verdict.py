"""BO-2 #1472 DoD #1 at the API boundary: the deliberation HTTP flow decides
the governance verdict firsthand with real LLM agents (no mock), and the
genuine verdict is retrievable through the JSON endpoints.

Existing coverage stopped at ``202/queued`` (``test_proposal_api.py``) or mocked
the pipeline (``test_workflow_endpoint_success``) — nothing proved that hitting
the real endpoints produces (and returns) a genuine governance decision. This
closes that gap end-to-end:

    POST /api/propose  →  POST /api/deliberate (democratech)  →  GET status

Privacy HARD: synthetic domain-public chess-club budget proposition only — no
corpus, no real names. Marked requires_api+slow: skips without a key / on the
fast per-push gate. FastAPI BackgroundTasks run synchronously under TestClient,
so POST /deliberate blocks until the real workflow (~150-200s) completes.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.proposal_service import ProposalStore, get_proposal_store


PROPOSITION = (
    "Le club d'echecs dispose d'un budget participatif de 2000 euros. "
    "Trois options divergentes s'affrontent. "
    "Option A : organiser un tournoi inter-villes avec buffet et prix pour 2000 "
    "euros, ce qui augmentera la visibilite du club et recrutera de nouveaux membres. "
    "Option B : investir les 2000 euros en materiel pedagogique, echiquiers neufs, "
    "horloges et supports de cours, car les echiquiers actuels sont uses. "
    "Option C : un format hybride, 1000 euros pour un tournoi reduit et 1000 euros "
    "pour le materiel pedagogique, equilibre entre visibilite et pedagogie."
)


@pytest.fixture(autouse=True)
def fresh_store():
    import api.proposal_service as svc

    svc._store = ProposalStore()
    yield
    svc._store = None


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.requires_api
@pytest.mark.slow
class TestDeliberationGenuineVerdictViaAPI:
    @pytest.mark.asyncio
    async def test_deliberation_decides_governance_firsthand_via_http(self, client):
        # 1. Submit a synthetic multi-option proposal.
        create = client.post(
            "/api/propose",
            json={"text": PROPOSITION, "author": "src0_ext0", "tags": ["budget"]},
        )
        assert create.status_code == 201
        pid = create.json()["id"]

        # 2. Launch deliberation. BackgroundTasks run synchronously under
        #    TestClient, so this blocks until the real workflow completes.
        start = client.post(
            "/api/deliberate",
            json={"proposal_id": pid, "workflow": "democratech"},
        )
        assert start.status_code == 202
        delib_id = start.json()["id"]

        # 3. Store-level proof: the workflow decided the verdict firsthand
        #    through the full HTTP POST path (not a direct function call).
        store = get_proposal_store()
        delib = store.get_deliberation(delib_id)
        assert delib is not None
        assert delib.status.value == "completed", f"error={delib.error!r}"
        gov = delib.results["phases"]["democratic_vote"]
        gov_output = gov.output if hasattr(gov, "output") else gov["output"]
        assert gov_output["governance_decided_firsthand"] is True, (
            f"governance must decide firsthand with a live key "
            f"(verdict={gov_output.get('governance_verdict')!r})"
        )
        assert gov_output["degraded"] is False
        assert "governance_simulation" not in delib.results.get(
            "capabilities_degraded", []
        )

        # 4. HTTP-level proof: the genuine verdict is retrievable as JSON —
        #    the status endpoint no longer 500s on unserializable internals.
        status = client.get(f"/api/deliberate/{delib_id}/status")
        assert status.status_code == 200, status.text
        body = status.json()
        assert body["status"] == "completed"
        http_gov = body["results"]["phases"]["democratic_vote"]["output"]
        assert http_gov["governance_decided_firsthand"] is True
        assert "unified_state" not in body["results"]

        # 5. Proposal transitions to DECIDED and exposes its analysis.
        detail = client.get(f"/api/proposals/{pid}")
        assert detail.status_code == 200
        assert detail.json()["status"] == "decided"
