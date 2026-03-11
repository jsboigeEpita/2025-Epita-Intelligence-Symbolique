"""Tests for the citizen proposal and deliberation API.

Validates:
- Proposal CRUD (create, list, get by id)
- Voting (cast, duplicate prevention)
- Deliberation lifecycle (start, status)
- Capabilities endpoint
- Custom workflow endpoint
- Error handling (404, 409)
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from api.proposal_models import ProposalStatus
from api.proposal_service import ProposalStore, get_proposal_store


@pytest.fixture(autouse=True)
def fresh_store():
    """Reset the global store before each test."""
    import api.proposal_service as svc

    svc._store = ProposalStore()
    yield
    svc._store = None


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


# ──── Proposal CRUD ────


class TestProposalSubmission:
    def test_create_proposal(self, client):
        resp = client.post(
            "/api/propose",
            json={"text": "We should invest in renewable energy", "author": "alice"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["author"] == "alice"
        assert data["status"] == "pending"
        assert "id" in data
        assert data["vote_counts"] == {"pour": 0, "contre": 0, "abstention": 0}

    def test_create_proposal_with_tags(self, client):
        resp = client.post(
            "/api/propose",
            json={
                "text": "Proposal about climate change mitigation",
                "author": "bob",
                "title": "Climate Action",
                "tags": ["environment", "policy"],
            },
        )
        assert resp.status_code == 201
        assert resp.json()["title"] == "Climate Action"
        assert resp.json()["tags"] == ["environment", "policy"]

    def test_create_proposal_validation(self, client):
        resp = client.post("/api/propose", json={"text": "short", "author": "x"})
        assert resp.status_code == 422  # text too short (min 10)


class TestProposalListing:
    def test_empty_list(self, client):
        resp = client.get("/api/proposals")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_create(self, client):
        client.post(
            "/api/propose",
            json={"text": "First proposal text here", "author": "alice"},
        )
        client.post(
            "/api/propose",
            json={"text": "Second proposal text here", "author": "bob"},
        )
        resp = client.get("/api/proposals")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_with_status_filter(self, client):
        client.post(
            "/api/propose",
            json={"text": "Pending proposal text here", "author": "alice"},
        )
        resp = client.get("/api/proposals?status=pending")
        assert len(resp.json()) == 1

        resp = client.get("/api/proposals?status=decided")
        assert len(resp.json()) == 0

    def test_list_pagination(self, client):
        for i in range(5):
            client.post(
                "/api/propose",
                json={"text": f"Proposal number {i} text content", "author": f"user{i}"},
            )
        resp = client.get("/api/proposals?limit=2&offset=0")
        assert len(resp.json()) == 2

        resp = client.get("/api/proposals?limit=2&offset=3")
        assert len(resp.json()) == 2


class TestProposalDetail:
    def test_get_existing(self, client):
        create_resp = client.post(
            "/api/propose",
            json={"text": "Detailed proposal text here", "author": "alice"},
        )
        pid = create_resp.json()["id"]
        resp = client.get(f"/api/proposals/{pid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == pid

    def test_get_nonexistent(self, client):
        resp = client.get("/api/proposals/nonexistent")
        assert resp.status_code == 404


# ──── Voting ────


class TestVoting:
    def test_cast_vote(self, client):
        create_resp = client.post(
            "/api/propose",
            json={"text": "Vote on this proposal please", "author": "alice"},
        )
        pid = create_resp.json()["id"]

        resp = client.post(
            f"/api/proposals/{pid}/vote",
            json={"voter_id": "voter1", "position": "pour"},
        )
        assert resp.status_code == 201
        assert resp.json()["position"] == "pour"

        # Check vote counts updated
        detail = client.get(f"/api/proposals/{pid}").json()
        assert detail["vote_counts"]["pour"] == 1

    def test_duplicate_vote_rejected(self, client):
        create_resp = client.post(
            "/api/propose",
            json={"text": "No duplicate votes allowed test", "author": "alice"},
        )
        pid = create_resp.json()["id"]

        client.post(
            f"/api/proposals/{pid}/vote",
            json={"voter_id": "voter1", "position": "pour"},
        )
        resp = client.post(
            f"/api/proposals/{pid}/vote",
            json={"voter_id": "voter1", "position": "contre"},
        )
        assert resp.status_code == 409

    def test_vote_nonexistent_proposal(self, client):
        resp = client.post(
            "/api/proposals/fake/vote",
            json={"voter_id": "v1", "position": "pour"},
        )
        assert resp.status_code == 404

    def test_multiple_voters(self, client):
        create_resp = client.post(
            "/api/propose",
            json={"text": "Multiple voters can vote on this", "author": "alice"},
        )
        pid = create_resp.json()["id"]

        for i, pos in enumerate(["pour", "contre", "abstention"]):
            client.post(
                f"/api/proposals/{pid}/vote",
                json={"voter_id": f"voter{i}", "position": pos},
            )

        detail = client.get(f"/api/proposals/{pid}").json()
        assert detail["vote_counts"] == {"pour": 1, "contre": 1, "abstention": 1}


# ──── Deliberation ────


class TestDeliberation:
    def test_start_deliberation(self, client):
        create_resp = client.post(
            "/api/propose",
            json={"text": "Start deliberation on this proposal", "author": "alice"},
        )
        pid = create_resp.json()["id"]

        resp = client.post(
            "/api/deliberate",
            json={"proposal_id": pid, "workflow": "democratech"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "queued"
        assert data["proposal_id"] == pid

    def test_deliberation_nonexistent_proposal(self, client):
        resp = client.post(
            "/api/deliberate",
            json={"proposal_id": "fake", "workflow": "democratech"},
        )
        assert resp.status_code == 404

    def test_get_deliberation_status(self, client):
        """Test deliberation status retrieval using store directly (avoids background task race)."""
        store = get_proposal_store()
        from api.proposal_models import ProposalCreate

        p = store.create_proposal(
            ProposalCreate(text="Check deliberation status endpoint test", author="alice")
        )
        delib = store.create_deliberation(p.id, "light")

        status_resp = client.get(f"/api/deliberate/{delib.id}/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["id"] == delib.id
        assert status_resp.json()["status"] == "queued"

    def test_deliberation_status_not_found(self, client):
        resp = client.get("/api/deliberate/fake/status")
        assert resp.status_code == 404


# ──── Capabilities ────


class TestCapabilities:
    def test_capabilities_endpoint(self, client):
        resp = client.get("/api/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert "plugins" in data
        assert "services" in data
        assert "workflows" in data
        assert "light" in data["workflows"]


# ──── Custom Workflow ────


class TestCustomWorkflow:
    @patch("argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis")
    def test_workflow_endpoint_success(self, mock_run, client):
        mock_run.return_value = {"summary": "Analysis complete", "score": 4}
        resp = client.post(
            "/api/workflow/custom",
            json={"text": "Analyze this argument for fallacies", "workflow": "light"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["workflow"] == "light"
        assert data["status"] == "completed"

    def test_workflow_endpoint_handles_failure(self, client):
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            side_effect=RuntimeError("Pipeline unavailable"),
        ):
            resp = client.post(
                "/api/workflow/custom",
                json={"text": "Test failure handling in workflow", "workflow": "light"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "failed"
            assert "error" in data


# ──── ProposalStore Unit Tests ────


class TestProposalStore:
    def test_store_independence(self):
        store = ProposalStore()
        from api.proposal_models import ProposalCreate

        p = store.create_proposal(
            ProposalCreate(text="Independent store test text", author="test")
        )
        assert store.get_proposal(p.id) is not None
        assert store.get_proposal("nonexistent") is None

    def test_update_status(self):
        store = ProposalStore()
        from api.proposal_models import ProposalCreate

        p = store.create_proposal(
            ProposalCreate(text="Status update test proposal", author="test")
        )
        store.update_status(p.id, ProposalStatus.ANALYZING)
        assert store.get_proposal(p.id).status == ProposalStatus.ANALYZING

    def test_set_analysis_results(self):
        store = ProposalStore()
        from api.proposal_models import ProposalCreate

        p = store.create_proposal(
            ProposalCreate(text="Analysis results test proposal", author="test")
        )
        store.set_analysis_results(p.id, {"score": 42})
        assert store.get_proposal(p.id).analysis_results == {"score": 42}
