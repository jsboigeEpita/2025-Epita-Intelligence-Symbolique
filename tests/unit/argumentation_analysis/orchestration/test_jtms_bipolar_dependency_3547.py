"""#3547 — spectacular: bipolar runs before jtms, or its support pairs never arrive.

Measured on the c10 panel: the bipolar phase recorded 40 support pairs across
8 of 10 documents, and the JTMS counterfactual stayed empty everywhere. Root
cause: ``bipolar`` and ``jtms`` shared a DAG level (both were ready as soon as
``counter`` completed), and the executor publishes a level's outputs — context
keys AND state writers — only after the whole level's ``asyncio.gather`` ends.
``_invoke_jtms`` read ``state.bipolar_results`` while the level was still
running: empty, silently, on every first run. Same accident-of-levels class as
#2969 (jtms→fol/pl, declared there).

The fix declares the dependency — it does NOT move the read: the invoker keeps
reading the state field, the executor now orders the producer before the
consumer.

Chain under witness:

- DAG (born red on main, where both phases sat at level 5): in
  ``build_spectacular_workflow()``'s execution order, ``jtms`` sits at a
  strictly later level than ``bipolar``.
- Executor (born red on main): the real spectacular workflow through
  ``WorkflowExecutor`` — a fake bipolar provider emits the U5 support pairs,
  every other capability is a no-op fake except ``belief_maintenance`` (the
  real ``_invoke_jtms``). The pairs reach the JTMS ONLY through the real state
  writer (``_write_bipolar_to_state`` → ``state.add_bipolar_result``) — no
  ``supports`` key is pre-supplied in the context — and
  ``state.jtms_counterfactual_withdrawals`` comes back non-empty.
- Pin: ``bipolar`` is optional — when its provider fails, ``jtms`` still runs,
  without the support edges, exactly as it did before the declaration.

Privacy: every fixture is synthetic — opaque ids (arg_N) and neutral text; no
corpus content.
"""

from __future__ import annotations

from typing import Any, Dict

from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentType,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import _invoke_jtms
from argumentation_analysis.orchestration.state_writers import CAPABILITY_STATE_WRITERS
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseStatus,
    WorkflowExecutor,
)
from argumentation_analysis.orchestration.workflows import build_spectacular_workflow

SOURCE = "texte synthetique"

A_TEXT = "The survey shows residents want the market moved"
B_TEXT = "So the market will move to the square"
C_TEXT = "So the square's parking must be rebuilt"
D_TEXT = "The square's lighting is already scheduled for replacement"

UNITS = [
    ("arg_1", A_TEXT),
    ("arg_2", B_TEXT),
    ("arg_3", C_TEXT),
    ("arg_4", D_TEXT),
]
# Same [source, target] convention as the real bipolar output: the source
# REINFORCES the target.
SUPPORTS = [["arg_1", "arg_2"], ["arg_2", "arg_3"]]

_BIPOLAR_OUTPUT: Dict[str, Any] = {
    "framework_type": "necessity",
    "arguments": [uid for uid, _text in UNITS],
    "supports": [list(pair) for pair in SUPPORTS],
}


def _fake_registry(bipolar_raises: bool = False) -> CapabilityRegistry:
    """A provider for every spectacular capability: no-op fakes, except the
    extract shape the JTMS builds its beliefs from, the bipolar output under
    witness, and the real ``_invoke_jtms`` for ``belief_maintenance``."""

    async def _noop(_text: str, _ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    async def _extract(_text: str, _ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "arguments": [{"unit_id": uid, "text": text} for uid, text in UNITS],
            "claims": [],
        }

    async def _bipolar(_text: str, _ctx: Dict[str, Any]) -> Dict[str, Any]:
        if bipolar_raises:
            raise RuntimeError("synthetic bipolar failure")
        return {
            key: (list(value) if isinstance(value, list) else value)
            for key, value in _BIPOLAR_OUTPUT.items()
        }

    registry = CapabilityRegistry()
    for cap in sorted(set(build_spectacular_workflow().get_required_capabilities())):
        if cap == "fact_extraction":
            invoke = _extract
        elif cap == "bipolar_argumentation":
            invoke = _bipolar
        elif cap == "belief_maintenance":
            invoke = _invoke_jtms
        else:
            invoke = _noop
        registry.register(
            name=f"fake_{cap}",
            component_type=ComponentType.AGENT,
            capabilities=[cap],
            invoke=invoke,
        )
    return registry


async def _run(bipolar_raises: bool = False):
    registry = _fake_registry(bipolar_raises=bipolar_raises)
    state = UnifiedAnalysisState(SOURCE)
    results = await WorkflowExecutor(registry).execute(
        build_spectacular_workflow(),
        SOURCE,
        state=state,
        state_writers=CAPABILITY_STATE_WRITERS,
    )
    return results, state


class TestTheDeclaredOrder:
    def test_jtms_sits_after_bipolar_in_the_execution_order(self) -> None:
        """Born red on main: both phases shared level 5, so the JTMS read the
        state field before the bipolar writer had run."""
        order = build_spectacular_workflow().get_execution_order()
        bipolar_level = next(i for i, lvl in enumerate(order) if "bipolar" in lvl)
        jtms_level = next(i for i, lvl in enumerate(order) if "jtms" in lvl)
        assert jtms_level > bipolar_level, (
            f"jtms runs at level {jtms_level}, bipolar at {bipolar_level} — "
            "the support pairs cannot have been written when jtms reads them"
        )


class TestTheExecutorWiring:
    async def test_support_pairs_reach_jtms_through_the_bipolar_writer(self) -> None:
        """Born red on main: same level means ``_write_bipolar_to_state`` has
        not run when ``_invoke_jtms`` reads ``bipolar_results``, so no
        justification edge exists and no premise is ever withdrawn."""
        results, state = await _run()

        assert results["bipolar"].status == PhaseStatus.COMPLETED
        assert results["jtms"].status == PhaseStatus.COMPLETED
        # The pairs were recorded by the real state writer, nothing else.
        assert state.bipolar_results, "the bipolar writer did not record its result"
        assert state.bipolar_results[-1]["supports"] == SUPPORTS
        # …and they reached the JTMS: the withdrawal pass found premises.
        withdrawals = state.jtms_counterfactual_withdrawals
        assert withdrawals, (
            "the bipolar support pairs never reached the JTMS — the "
            "counterfactual pass saw no justification edge"
        )
        assert any(
            str(entry.get("premise", "")).startswith("arg_1:") for entry in withdrawals
        ), withdrawals


class TestOptionalBipolarStillLetsJtmsRun:
    async def test_jtms_runs_without_support_edges_when_bipolar_fails(self) -> None:
        """The pin: ``bipolar`` is optional — its failure must not take the
        JTMS down with it. Without the support edges no premise is premised,
        so the withdrawal list is empty, but the phase completes."""
        results, state = await _run(bipolar_raises=True)

        assert results["bipolar"].status == PhaseStatus.FAILED
        assert results["jtms"].status == PhaseStatus.COMPLETED
        assert state.jtms_counterfactual_withdrawals == []
