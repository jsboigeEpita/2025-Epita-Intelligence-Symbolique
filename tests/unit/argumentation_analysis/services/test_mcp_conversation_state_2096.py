"""Né-rouge guard for #2096 — conversation rounds must carry state across turns.

Measured on the pristine tree (base ``14fbe867``): ``SessionState.state``
defaults to ``None`` and nothing in the repo ever assigns it — so
``_execute_round`` always built its ``WorkflowTurnStrategy`` with
``state_writers=None`` (``conversation_tools.py:171``) and executed every
turn with ``state=None`` (:180). No inter-round state continuity: each
``continue_conversation`` re-analyzed from scratch and
``CAPABILITY_STATE_WRITERS`` stayed dead on the MCP path.

The seam under test: ``WorkflowTurnStrategy`` is imported inside
``_execute_round`` at call time, so monkeypatching its home module
intercepts the real round driver without running a full workflow.
"""

from types import SimpleNamespace

from argumentation_analysis.services.mcp_server.session_manager import (
    SessionManager,
)
from argumentation_analysis.services.mcp_server.tools import conversation_tools


def _fake_turn_result(turn_number: int):
    return SimpleNamespace(
        turn_number=turn_number,
        confidence=0.9,
        needs_refinement=False,
        questions_for_user=[],
        duration_seconds=0.01,
        phase_results={},
    )


def _install_fake_strategy(monkeypatch, seen):
    class FakeStrategy:
        def __init__(self, workflow, registry, state_writers=None):
            seen.setdefault("inits", []).append({"state_writers": state_writers})

        async def execute_turn(self, text, context, state=None):
            seen.setdefault("states_in", []).append(state)
            return _fake_turn_result(context.get("turn_number", 1))

    monkeypatch.setattr(
        "argumentation_analysis.orchestration.conversational_executor"
        ".WorkflowTurnStrategy",
        FakeStrategy,
    )


async def test_first_round_creates_and_carries_state_2096(monkeypatch):
    seen = {}
    _install_fake_strategy(monkeypatch, seen)

    sm = SessionManager()
    session = sm.create_session("Un texte qui avance une thèse et une raison.")
    await conversation_tools._execute_round(lambda: object(), session, round_number=1)

    assert session.state is not None, (
        "session.state was never assigned — every MCP conversation round "
        "restarts from scratch and CAPABILITY_STATE_WRITERS stays dead (#2096)"
    )
    assert (
        seen["states_in"][0] is session.state
    ), "the round must execute against the session's state object"
    assert seen["inits"][0]["state_writers"] is not None, (
        "state_writers must be live (CAPABILITY_STATE_WRITERS) once a state "
        "exists — 'if session.state else None' is only honest if the state "
        "is ever created (#2096)"
    )


async def test_second_round_reuses_the_same_state_2096(monkeypatch):
    seen = {}
    _install_fake_strategy(monkeypatch, seen)

    sm = SessionManager()
    session = sm.create_session("Première thèse.")
    await conversation_tools._execute_round(lambda: object(), session, round_number=1)
    first_state = session.state
    assert first_state is not None

    await conversation_tools._execute_round(
        lambda: object(),
        session,
        round_number=2,
        text_override="Texte complémentaire pour le second tour.",
    )

    assert seen["states_in"][1] is first_state, (
        "round 2 must reuse the state accumulated by round 1 — continuity "
        "is the point of continue_conversation (#2096)"
    )
    assert seen["inits"][1]["state_writers"] is not None
