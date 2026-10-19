"""BO-2 #1472 DoD — WebSocket last-mile cable (anti-theatre), fast-gate guard.

Empirical SDDD probe (grep) found that ``AnalysisWebSocketManager.broadcast_*``
helpers were called **only in tests** — ``get_websocket_manager()`` was reached
in production solely from ``api/websocket_routes.py`` (connect/disconnect). So a
client connected to ``/ws/deliberation/{id}`` received only pongs: the streaming
surface existed but NOTHING in the execution path ever emitted. Theatre #1019 at
the WS boundary — the same family of latent bug as the HTTP serialization 500
fixed in #1481 (verdict decided but unreachable).

This module guards the cable added in ``run_deliberation_workflow`` (lifecycle
``running``/``completed``/``failed`` + terminal ``deliberation_result`` carrying
the governance verdict) on the **fast per-push gate**, with the pipeline mocked
to a realistic sanitized-result shape. The genuine end-to-end proof (real LLM,
real verdict broadcast) lives in
``tests/integration/api/test_websocket_deliberation_genuine.py`` (requires_api+slow).

A ``FakeSocket`` registered in the real manager's connection set stands in for a
connected client: ``_send_to_session`` calls ``ws.send_json`` on it exactly as on
a live socket, so capturing on it proves the manager actually broadcast.
"""

import pytest
from unittest.mock import AsyncMock, patch

from starlette.websockets import WebSocketState

from api.proposal_service import ProposalStore, run_deliberation_workflow
from argumentation_analysis.orchestration.workflow_dsl import PhaseResult, PhaseStatus
from argumentation_analysis.services.websocket_manager import (
    AnalysisWebSocketManager,
    get_websocket_manager,
)


class _FakeSocket:
    """Stand-in for a connected WebSocket. Captures every broadcast."""

    def __init__(self):
        self.client_state = WebSocketState.CONNECTED
        self.received: list[dict] = []

    async def send_json(self, message):
        self.received.append(message)


def _sanitized_result_shape() -> dict:
    """A sanitized ``run_unified_analysis`` result (post ``sanitize_workflow_result``).

    Mirrors the live shape: phases as dicts (PhaseResult coerced), genuine
    governance verdict. NOT a strawman — ``run_deliberation_workflow`` extracts
    the verdict from ``phases.democratic_vote.output`` exactly this way.
    """
    gov = PhaseResult(
        phase_name="democratic_vote",
        status=PhaseStatus.COMPLETED,
        capability="governance_simulation",
        output={
            "governance_decided_firsthand": True,
            "degraded": False,
            "governance_verdict": {
                "degraded": False,
                "condorcet_winner": "arg_1",
                # #2300 — the aggregate now carries the fallback-canon winner
                # (+ basis); the broadcast reads this, not the raw strict variant.
                "winner": "arg_1",
                "winner_basis": "condorcet",
                "winners_per_method": {"borda": "arg_1", "copeland": "arg_1"},
            },
        },
        error=None,
    )
    extract = PhaseResult(
        phase_name="extract",
        status=PhaseStatus.COMPLETED,
        capability="fact_extraction",
        output={"arguments": ["arg_1", "arg_2"]},
        error=None,
    )
    return {
        "workflow_name": "democratech",
        "phases": {"extract": extract, "democratic_vote": gov},
        "summary": {"completed": 10, "failed": 0, "skipped": 0, "total": 10},
        "capabilities_used": ["fact_extraction", "governance_simulation"],
        "capabilities_degraded": [],
        "capabilities_missing": [],
        "state_snapshot": {"argument_count": 6, "governance_decision_count": 1},
    }


@pytest.fixture
def fresh_store_and_manager(monkeypatch):
    """Isolated store + fresh manager so tests don't leak connections."""
    import api.proposal_service as svc

    monkeypatch.setattr(svc, "_store", ProposalStore())
    fresh_manager = AnalysisWebSocketManager()
    import argumentation_analysis.services.websocket_manager as wsm

    monkeypatch.setattr(wsm, "_manager", fresh_manager)
    yield svc._store, fresh_manager


def _raw_result_with_vote(vote: PhaseResult) -> dict:
    """A raw ``run_unified_analysis``-shaped dict carrying ``vote`` as its
    ``democratic_vote`` phase — real ``PhaseResult`` objects, so the REAL
    ``_run_pipeline`` runs ``sanitize_workflow_result`` over them (the same
    construction the #3058 script witness uses).

    #3070: the existing cable test asserts ``degraded is False`` only on a
    non-degraded COMPLETED run — nothing pinned what the broadcast sends on
    the degraded shapes (#3049 tranche 5 measured: mutating the broadcast
    line back to a one-level read kept 63 neighbours green).
    """
    extract = PhaseResult(
        phase_name="extract",
        status=PhaseStatus.COMPLETED,
        capability="fact_extraction",
        output={"arguments": ["arg_1", "arg_2"]},
        error=None,
    )
    return {
        "workflow_name": "democratech",
        "phases": {"extract": extract, "democratic_vote": vote},
        "summary": {"completed": 10, "failed": 1, "skipped": 0, "total": 11},
        "capabilities_used": ["fact_extraction", "governance_simulation"],
        "capabilities_degraded": ["governance_simulation"],
        "capabilities_missing": [],
        "state_snapshot": {"argument_count": 6, "governance_decision_count": 0},
    }


class TestDegradedVoteStreamsDegradedTrue:
    """#3070 — the broadcast reads the executor's TWO degradation levels.

    The script side is pinned (``TestVerdictReadTwoLevels``); this class pins
    the WebSocket side of the same shared reader: a degraded vote phase is a
    COMPLETED deliberation whose streamed result event carries
    ``degraded is True`` — never a silent ``False`` and never a fabricated
    verdict.
    """

    async def _streamed_result_event(self, fresh_store_and_manager, vote):
        store, manager = fresh_store_and_manager
        proposal = store.create_proposal(
            type(
                "P",
                (),
                {
                    "text": "Synthetic degraded-vote proposal",
                    "author": "src0",
                    "title": None,
                    "tags": [],
                },
            )()
        )
        delib = store.create_deliberation(proposal.id, "democratech")

        sock = _FakeSocket()
        manager._connections[delib.id] = {sock}

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new=AsyncMock(return_value=_raw_result_with_vote(vote)),
        ):
            await run_deliberation_workflow(
                store, delib.id, proposal.text, "democratech", {}
            )
        return (
            store,
            delib,
            next(m for m in sock.received if m["type"] == "deliberation_result"),
        )

    @pytest.mark.asyncio
    async def test_failed_phase_level_degraded_flag_streams_true(
        self, fresh_store_and_manager
    ):
        """DT-1 #1499 shape: FAILED + ``degraded=True`` + ``output=None``.

        The flag the executor sets lives BESIDE the None output — a read
        inside the output reports False on exactly this shape (#3049
        tranche 5). The deliberation still completes (the phase is optional,
        the orchestrator continued) and the event says it degraded.
        """
        vote = PhaseResult(
            phase_name="democratic_vote",
            status=PhaseStatus.FAILED,
            capability="governance_simulation",
            output=None,
            error="vote phase failed after retries (optional, continued)",
            degraded=True,
        )
        store, delib, event = await self._streamed_result_event(
            fresh_store_and_manager, vote
        )

        assert event["degraded"] is True
        assert event["governance_decided_firsthand"] is False
        assert event["winner"] is None
        # Degraded is not failed: the cable completed the deliberation.
        assert store.get_deliberation(delib.id).status.value == "completed"

    @pytest.mark.asyncio
    async def test_completed_self_declared_degraded_output_streams_true(
        self, fresh_store_and_manager
    ):
        """#2971 shape: COMPLETED whose output dict declares ``degraded``."""
        vote = PhaseResult(
            phase_name="democratic_vote",
            status=PhaseStatus.COMPLETED,
            capability="governance_simulation",
            output={"degraded": True, "governance_verdict": {}},
            error=None,
            degraded=False,
        )
        _store, _delib, event = await self._streamed_result_event(
            fresh_store_and_manager, vote
        )

        assert event["degraded"] is True
        assert event["governance_decided_firsthand"] is False


class TestWSCableBroadcastsLifecycleAndVerdict:
    """A connected client receives running -> verdict -> completed (the cable)."""

    @pytest.mark.asyncio
    async def test_completed_deliberation_streams_verdict_to_ws_client(
        self, fresh_store_and_manager
    ):
        store, manager = fresh_store_and_manager
        proposal = store.create_proposal(
            type(
                "P",
                (),
                {
                    "text": "Synthetic 3-option budget proposal",
                    "author": "src0",
                    "title": None,
                    "tags": [],
                },
            )()
        )
        delib = store.create_deliberation(proposal.id, "democratech")

        sock = _FakeSocket()
        manager._connections[delib.id] = {sock}

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new=AsyncMock(return_value=_sanitized_result_shape()),
        ):
            await run_deliberation_workflow(
                store, delib.id, proposal.text, "democratech", {}
            )

        types = [m["type"] for m in sock.received]
        # Lifecycle opened with running, closed with completed.
        assert types[0] == "status" and sock.received[0]["status"] == "running"
        assert sock.received[0]["detail"] == "democratech"
        assert types[-1] == "status" and sock.received[-1]["status"] == "completed"
        # The genuine verdict was broadcast.
        assert "deliberation_result" in types
        result_ev = next(m for m in sock.received if m["type"] == "deliberation_result")
        assert result_ev["proposal_id"] == proposal.id
        assert result_ev["winner"] == "arg_1"
        assert result_ev["governance_decided_firsthand"] is True
        assert result_ev["degraded"] is False
        # Store transitioned too (the cable did not break the deliberation).
        assert store.get_deliberation(delib.id).status.value == "completed"

    @pytest.mark.asyncio
    async def test_failed_deliberation_streams_error_to_ws_client(
        self, fresh_store_and_manager
    ):
        store, manager = fresh_store_and_manager
        proposal = store.create_proposal(
            type(
                "P",
                (),
                {
                    "text": "Synthetic failing proposal",
                    "author": "src0",
                    "title": None,
                    "tags": [],
                },
            )()
        )
        delib = store.create_deliberation(proposal.id, "democratech")

        sock = _FakeSocket()
        manager._connections[delib.id] = {sock}

        # Patch _run_pipeline (not run_unified_analysis): the real _run_pipeline
        # swallows all exceptions and returns an error-stub, which would be treated
        # as a *completed* deliberation. To exercise run_deliberation_workflow's own
        # except branch (-> FAILED + error broadcast) we make _run_pipeline raise.
        with patch(
            "api.proposal_service._run_pipeline",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            await run_deliberation_workflow(
                store, delib.id, proposal.text, "democratech", {}
            )

        types = [m["type"] for m in sock.received]
        assert types[0] == "status" and sock.received[0]["status"] == "running"
        assert "error" in types
        err_ev = next(m for m in sock.received if m["type"] == "error")
        assert "boom" in err_ev["error"]
        assert types[-1] == "status" and sock.received[-1]["status"] == "failed"
        assert store.get_deliberation(delib.id).status.value == "failed"

    @pytest.mark.asyncio
    async def test_broadcast_noop_when_no_client_connected(
        self, fresh_store_and_manager
    ):
        """No client registered -> deliberation still completes, nothing raised.

        Guards the best-effort contract: WS must never break a headless
        deliberation (e.g. POST /deliberate with no WS subscriber).
        """
        store, manager = fresh_store_and_manager
        proposal = store.create_proposal(
            type(
                "P",
                (),
                {
                    "text": "Headless deliberation, no WS client",
                    "author": "src0",
                    "title": None,
                    "tags": [],
                },
            )()
        )
        delib = store.create_deliberation(proposal.id, "democratech")
        # Deliberately do NOT register any socket.

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new=AsyncMock(return_value=_sanitized_result_shape()),
        ):
            await run_deliberation_workflow(
                store, delib.id, proposal.text, "democratech", {}
            )  # must not raise

        assert store.get_deliberation(delib.id).status.value == "completed"
        assert manager.get_active_sessions() == []
