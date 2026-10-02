"""#2902: a deliberation whose vote phase failed is not decided, and the
failure is named.

On ``main``, ``run_deliberation_workflow`` records the deliberation
``COMPLETED`` and the proposal ``DECIDED`` before reading the verdict, then
``_broadcast_ws_deliberation_result`` raises on the failed phase's ``output:
None`` (``.get("output", {})`` returns ``None`` when the key exists with a
``None`` value), and the ``except`` rewrites everything ``FAILED`` with
``'NoneType' object has no attribute 'get'`` — the AttributeError replaces
the real cause: the vote phase failed.

After the fix: the failed vote phase is the deliberation's own failure, named
after the phase; the broadcaster admits the failed shape (best-effort
``decided_firsthand=False`` with the phase's status); a run without a verdict
is never ``DECIDED``; the terminal state is written once.

The genuine-verdict shape (completed phase, verdict present) stays ``DECIDED``
— a pure perimeter witness, green before and after.
"""

from api.proposal_models import (
    DeliberationStatus,
    ProposalCreate,
    ProposalStatus,
)
from api.proposal_service import (
    ProposalStore,
    _broadcast_ws_deliberation_result,
    run_deliberation_workflow,
)

FAILED_VOTE_RESULT = {
    "workflow": "democratech",
    "phases": {
        "democratic_vote": {
            "phase_name": "democratic_vote",
            "status": "failed",
            "output": None,
            "error": "Raw cache miss in replay mode",
            "degraded": False,
        }
    },
}

GENUINE_VERDICT_RESULT = {
    "workflow": "democratech",
    "phases": {
        "democratic_vote": {
            "phase_name": "democratic_vote",
            "status": "completed",
            "output": {
                "governance_verdict": {"winner": "pour", "method": "majority"},
                "governance_decided_firsthand": True,
            },
        }
    },
}

VERDICTLESS_RESULT = {
    "workflow": "democratech",
    "text_excerpt": "Pipeline skipped — force-stub requested (offline path)",
}


def _store_with_deliberation() -> tuple:
    store = ProposalStore()
    proposal = store.create_proposal(
        ProposalCreate(text="Deliberation witness proposal text", author="witness")
    )
    delib = store.create_deliberation(proposal.id, "democratech")
    return store, proposal, delib


def _patch_pipeline(monkeypatch, result):
    async def fake_run_pipeline(text, workflow, options):
        return result

    monkeypatch.setattr("api.proposal_service._run_pipeline", fake_run_pipeline)


async def test_failed_vote_phase_fails_the_deliberation_with_the_named_cause(
    monkeypatch,
):
    """The error names the failed vote phase, not the AttributeError that
    only the defect's own crash produced."""
    _patch_pipeline(monkeypatch, FAILED_VOTE_RESULT)
    store, proposal, delib = _store_with_deliberation()

    await run_deliberation_workflow(store, delib.id, proposal.text, "democratech", {})

    final = store.get_deliberation(delib.id)
    assert final.status is DeliberationStatus.FAILED
    assert "democratic_vote" in final.error
    assert "Raw cache miss" in final.error
    assert "NoneType" not in final.error
    assert store.get_proposal(proposal.id).status is not ProposalStatus.DECIDED


async def test_failed_vote_phase_never_writes_completed(monkeypatch):
    """The terminal state is written once: no COMPLETED-then-FAILED flapping
    on the deliberation's way out."""
    _patch_pipeline(monkeypatch, FAILED_VOTE_RESULT)
    store, proposal, delib = _store_with_deliberation()

    written = []
    real_update = store.update_deliberation

    def spying_update(delib_id, status, **kwargs):
        written.append(status)
        real_update(delib_id, status, **kwargs)

    store.update_deliberation = spying_update

    await run_deliberation_workflow(store, delib.id, proposal.text, "democratech", {})

    assert DeliberationStatus.COMPLETED not in written
    assert written.count(DeliberationStatus.FAILED) == 1


async def test_broadcast_admits_a_failed_phase_output_none():
    """The broadcaster must not raise on the failed-phase shape — with no WS
    client connected the broadcast is a best-effort no-op, never a crash that
    rewrites the deliberation's state."""
    # No assertion on the return: on main this call raises AttributeError
    # ('NoneType' object has no attribute 'get'); surviving it IS the witness.
    await _broadcast_ws_deliberation_result("delib", "proposal", FAILED_VOTE_RESULT)


async def test_a_verdictless_run_is_not_decided(monkeypatch):
    """A run whose vote phase produced no verdict (absent phase, stub,
    degraded) completes the deliberation but never decides the proposal —
    PENDING is the store's existing "awaiting decision" status."""
    _patch_pipeline(monkeypatch, VERDICTLESS_RESULT)
    store, proposal, delib = _store_with_deliberation()

    await run_deliberation_workflow(store, delib.id, proposal.text, "democratech", {})

    assert store.get_deliberation(delib.id).status is DeliberationStatus.COMPLETED
    assert store.get_proposal(proposal.id).status is ProposalStatus.PENDING


async def test_a_genuine_verdict_still_decides(monkeypatch):
    """Perimeter: the completed vote phase with a real verdict keeps marking
    the proposal DECIDED — the fix must not kill the genuine path."""
    _patch_pipeline(monkeypatch, GENUINE_VERDICT_RESULT)
    store, proposal, delib = _store_with_deliberation()

    await run_deliberation_workflow(store, delib.id, proposal.text, "democratech", {})

    assert store.get_deliberation(delib.id).status is DeliberationStatus.COMPLETED
    assert store.get_proposal(proposal.id).status is ProposalStatus.DECIDED
