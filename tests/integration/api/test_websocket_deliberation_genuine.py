"""BO-2 #1472 DoD #2 — WebSocket last-mile GENUINE proof (real LLM, no mock).

Companion to ``tests/unit/api/test_websocket_deliberation_cable.py`` (fast gate,
mocked pipeline) and to the HTTP genuine test
``tests/integration/api/test_deliberation_genuine_verdict.py`` (#1481). This
closes the WS last-mile: a client subscribed to ``/ws/deliberation/{delib_id}``
receives the genuine governance verdict — decided firsthand by real LLM agents —
not only pongs.

Before the cable (grep-confirmed): ``AnalysisWebSocketManager.broadcast_*`` were
called only in tests; the production execution path never emitted, so a connected
client saw only ping/pong (theatre #1019 at the WS boundary, same family as the
HTTP serialization 500 fixed in #1481).

Anti-theatre HARD: this test runs the REAL pipeline (no mock) on a synthetic
domain-public chess-club budget proposition, so the broadcast ``winner`` and
``governance_decided_firsthand`` are the genuine LLM-decided verdict.

Note on the WS transport: a ``_FakeSocket`` registered in the real manager's
connection set is the capture point. ``_send_to_session`` calls ``ws.send_json``
on it identically to a live socket (the cable is manager-side), and the genuine
proof is that the *real* pipeline verdict reaches it. The HTTP POST -> WS
concurrent flow is unreachable under FastAPI TestClient (BackgroundTasks run
synchronously), so ``run_deliberation_workflow`` is awaited directly with a
pre-registered socket.
"""

import pytest
from starlette.websockets import WebSocketState

from api.proposal_service import ProposalStore, run_deliberation_workflow
from argumentation_analysis.services.websocket_manager import AnalysisWebSocketManager


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


class _FakeSocket:
    def __init__(self):
        self.client_state = WebSocketState.CONNECTED
        self.received: list[dict] = []

    async def send_json(self, message):
        self.received.append(message)


@pytest.mark.requires_api
@pytest.mark.slow
class TestWebSocketDeliberationGenuineVerdict:
    @pytest.mark.asyncio
    async def test_ws_client_receives_genuine_governance_verdict(self, monkeypatch):
        # Isolated store + fresh manager.
        store = ProposalStore()
        manager = AnalysisWebSocketManager()
        import argumentation_analysis.services.websocket_manager as wsm

        monkeypatch.setattr(wsm, "_manager", manager)

        proposal = store.create_proposal(
            type(
                "P",
                (),
                {"text": PROPOSITION, "author": "src0_ext0", "title": None, "tags": ["budget"]},
            )()
        )
        delib = store.create_deliberation(proposal.id, "democratech")

        # Subscribe a client to this deliberation's session (= delib_id) BEFORE
        # running the workflow, as a real browser would after POST /deliberate.
        sock = _FakeSocket()
        manager._connections[delib.id] = {sock}

        # REAL pipeline — no mock. Blocks ~150-200s with a live key.
        await run_deliberation_workflow(
            store, delib.id, proposal.text, "democratech", {}
        )

        # 1. The deliberation decided firsthand at the store level.
        d = store.get_deliberation(delib.id)
        assert d is not None
        assert d.status.value == "completed", f"error={d.error!r}"

        # 2. The subscribed WS client received the lifecycle + the GENUINE verdict.
        types = [m["type"] for m in sock.received]
        assert types[0] == "status" and sock.received[0]["status"] == "running"
        assert "deliberation_result" in types, f"no verdict broadcast: {types}"
        result_ev = next(m for m in sock.received if m["type"] == "deliberation_result")
        # Genuine markers — decided firsthand by real LLM agents, not fabricated.
        assert result_ev["governance_decided_firsthand"] is True, result_ev
        assert result_ev["degraded"] is False, result_ev
        assert result_ev["winner"] is not None, result_ev
        assert result_ev["proposal_id"] == proposal.id
        assert types[-1] == "status" and sock.received[-1]["status"] == "completed"
