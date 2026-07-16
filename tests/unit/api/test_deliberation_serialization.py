"""BO-2 #1472 — deliberation result JSON serialization (anti-theatre).

A completed deliberation carries the genuine governance verdict, but the raw
``run_unified_analysis`` result embeds the live ``unified_state`` object and
``PhaseResult`` dataclasses. Returning it verbatim through FastAPI's
``response_model`` raises at encode time → the ``GET /deliberate/{id}/status``
and ``GET /proposals/{id}`` endpoints answered 500 with an empty body for every
real deliberation (the verdict decided firsthand but was unreachable by the
client — theatre #1019 at the API boundary).

These tests exercise the ``sanitize_workflow_result`` fix and the endpoint
regression WITHOUT a live LLM (the pipeline is mocked to return a raw result
mirroring the real shape observed via a live-key probe), so they guard the fix
on the fast CI gate. The genuine end-to-end proof (real LLM) lives in
``tests/integration/api/test_deliberation_genuine_verdict.py`` (requires_api+slow).
"""

import json

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from api.main import app
from api.proposal_service import (
    ProposalStore,
    sanitize_workflow_result,
)
from argumentation_analysis.orchestration.workflow_dsl import PhaseResult, PhaseStatus


class _FakeUnifiedState:
    """Stand-in for the live UnifiedAnalysisState stored under
    ``result['unified_state']``. Holds a self-cycle and a bare object() —
    exactly the shape that makes FastAPI's jsonable_encoder raise, so the
    test reproduces the real 500, not a strawman."""

    def __init__(self):
        self.self_ref = self  # cyclic reference
        self.opaque = object()  # non-JSON-serializable attribute


def _real_shape_raw_result() -> dict:
    """A raw ``run_unified_analysis`` result mirroring the shape observed on a
    live-key probe (keys, PhaseResult dataclasses, unified_state object)."""
    gov_phase = PhaseResult(
        phase_name="democratic_vote",
        status=PhaseStatus.COMPLETED,
        capability="governance_simulation",
        output={
            "governance_decided_firsthand": True,
            "degraded": False,
            "governance_verdict": {
                "degraded": False,
                "condorcet_winner": "arg_1",
                "winners_per_method": {"borda": "arg_1", "copeland": "arg_1"},
            },
        },
        error=None,
    )
    extract_phase = PhaseResult(
        phase_name="extract",
        status=PhaseStatus.COMPLETED,
        capability="fact_extraction",
        output={"arguments": ["arg_1", "arg_2", "arg_3"]},
        error=None,
    )
    return {
        "workflow_name": "democratech",
        "phases": {"extract": extract_phase, "democratic_vote": gov_phase},
        "summary": {"completed": 10, "failed": 0, "skipped": 0, "total": 10},
        "capabilities_used": ["fact_extraction", "governance_simulation"],
        "capabilities_degraded": [],
        "capabilities_missing": [],
        "state_snapshot": {"argument_count": 6, "governance_decision_count": 1},
        "unified_state": _FakeUnifiedState(),
    }


# ──── sanitize_workflow_result unit tests ────


class TestSanitizeWorkflowResult:
    def test_output_is_json_serializable(self):
        safe = sanitize_workflow_result(_real_shape_raw_result())
        # Must not raise — the whole point of the fix.
        json.dumps(safe)

    def test_drops_unified_state(self):
        safe = sanitize_workflow_result(_real_shape_raw_result())
        assert "unified_state" not in safe

    def test_preserves_genuine_verdict(self):
        safe = sanitize_workflow_result(_real_shape_raw_result())
        gov = safe["phases"]["democratic_vote"]["output"]
        assert gov["governance_decided_firsthand"] is True
        assert gov["degraded"] is False
        assert gov["governance_verdict"]["condorcet_winner"] == "arg_1"

    def test_preserves_capabilities_and_snapshot(self):
        safe = sanitize_workflow_result(_real_shape_raw_result())
        assert "governance_simulation" in safe["capabilities_used"]
        assert safe["capabilities_degraded"] == []
        assert safe["state_snapshot"]["argument_count"] == 6

    def test_phase_result_status_enum_coerced(self):
        safe = sanitize_workflow_result(_real_shape_raw_result())
        # PhaseStatus enum → its value (str), not a bare enum member.
        assert safe["phases"]["democratic_vote"]["status"] == PhaseStatus.COMPLETED.value

    def test_non_dict_input_wrapped(self):
        safe = sanitize_workflow_result("just a string")
        assert safe == {"raw_result": "just a string"}

    def test_empty_dict(self):
        assert sanitize_workflow_result({}) == {}


# ──── Endpoint regression (no LLM — pipeline mocked) ────


@pytest.fixture(autouse=True)
def fresh_store():
    import api.proposal_service as svc

    svc._store = ProposalStore()
    yield
    svc._store = None


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


class TestDeliberationStatusSerialization:
    """The status/detail endpoints must return 200 with the genuine verdict for
    a completed deliberation — not 500 on unserializable internals (BO-2 #1472).

    TestClient runs FastAPI BackgroundTasks synchronously, so after POST
    /deliberate returns, the (mocked) deliberation has already completed and its
    results are stored sanitized via the real run_deliberation_workflow path.
    """

    def test_status_endpoint_serializes_completed_deliberation(self, client):
        raw = _real_shape_raw_result()
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new=AsyncMock(return_value=raw),
        ):
            pid = client.post(
                "/api/propose",
                json={"text": "Synthetic multi-option proposal text", "author": "src0"},
            ).json()["id"]

            delib = client.post(
                "/api/deliberate",
                json={"proposal_id": pid, "workflow": "democratech"},
            ).json()

            resp = client.get(f"/api/deliberate/{delib['id']}/status")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "completed"
        gov = body["results"]["phases"]["democratic_vote"]["output"]
        assert gov["governance_decided_firsthand"] is True
        assert "unified_state" not in body["results"]

    def test_proposal_detail_serializes_analysis_results(self, client):
        raw = _real_shape_raw_result()
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new=AsyncMock(return_value=raw),
        ):
            pid = client.post(
                "/api/propose",
                json={"text": "Another synthetic proposal body here", "author": "src0"},
            ).json()["id"]

            client.post(
                "/api/deliberate",
                json={"proposal_id": pid, "workflow": "democratech"},
            )

            resp = client.get(f"/api/proposals/{pid}")

        assert resp.status_code == 200, resp.text
        detail = resp.json()
        assert detail["status"] == "decided"
        assert detail["analysis_results"] is not None
        assert (
            detail["analysis_results"]["phases"]["democratic_vote"]["output"][
                "governance_decided_firsthand"
            ]
            is True
        )
