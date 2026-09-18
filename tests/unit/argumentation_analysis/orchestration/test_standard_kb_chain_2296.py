"""#2296 — the standard workflow wires the belief-set production chain.

Real-run evidence (2026-09-18, post-``25e23c8a``, JVM started, 74 jars,
OpenRouter healthy): the standard workflow finished
``15 completed, 0 failed, 0 skipped, 0 degraded`` with ``belief_sets: 0`` and
``tweety_formulas_from_kb`` ABSENT from the state dump. The refusal payload
that ``_write_kb_to_tweety_to_state`` persists whenever it runs never
appeared — the callable never ran. No phase among standard's 15 carried
capability ``nl_extraction`` or ``kb_to_tweety``, the only two capabilities
whose state writers call ``add_belief_set``. The golden threshold
``min_belief_sets: 1`` (born 2026-04-08, ``a9dce5e26``) has therefore tested a
production the workflow never ordered since its birth — permanently red on
real-key runs, masked for five months by the ``requires_api`` auto-skip, and
surfaced only when #1603 recorded real-key cassettes.

The nl_to_logic → pl → fol chain does NOT produce belief sets: its writers
fill ``nl_to_logic_translations`` / ``propositional_analysis_results`` /
``fol_analysis_results`` (measured on the same run: 6 / 1 / 1 produced, 0
belief sets).

The repair is upstream of the writer (anti-pendulum, per the dispatch: no
writer error-rewriting, no threshold re-baseline to ``>= 0``): standard wires
the same kb chain spectacular has carried since ``afa5b3236`` (#506/#514),
where the same corpus produces hundreds of belief sets per document.
"""

from argumentation_analysis.core.capability_registry import (
    ComponentRegistration,
    ComponentType,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    CAPABILITY_STATE_WRITERS,
    _write_kb_to_tweety_to_state,
    _write_text_to_kb_to_state,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowExecutor,
    WorkflowPhase,
)
from argumentation_analysis.orchestration.workflows import build_standard_workflow


def _capabilities(workflow) -> dict:
    return {p.capability: p for p in workflow.phases}


class TestStandardWiresTheKbChain:
    def test_standard_carries_nl_extraction_and_kb_to_tweety(self):
        caps = _capabilities(build_standard_workflow())
        assert "nl_extraction" in caps, (
            "#2296: standard wires no phase with capability nl_extraction — "
            "its writer is one of only two that call add_belief_set"
        )
        assert "kb_to_tweety" in caps, (
            "#2296: standard wires no phase with capability kb_to_tweety — "
            "its writer is one of only two that call add_belief_set"
        )

    def test_kb_to_tweety_depends_on_text_to_kb(self):
        wf = build_standard_workflow()
        by_name = {p.name: p for p in wf.phases}
        assert "kb_to_tweety" in by_name
        assert "text_to_kb" in by_name
        assert "text_to_kb" in by_name["kb_to_tweety"].depends_on


class TestTheMappingCannotGoVacuous:
    """If the writer table re-points nl_extraction/kb_to_tweety away from the
    belief-set writers, phase presence above stops being evidence of
    production — this guard reddens instead."""

    def test_kb_capabilities_still_own_the_belief_set_writers(self):
        assert (
            CAPABILITY_STATE_WRITERS["nl_extraction"] is _write_text_to_kb_to_state
        ), "nl_extraction no longer maps to the text_to_kb belief-set writer"
        assert (
            CAPABILITY_STATE_WRITERS["kb_to_tweety"] is _write_kb_to_tweety_to_state
        ), "kb_to_tweety no longer maps to the kb_to_tweety belief-set writer"


class TestTheWiredChainProduces:
    """Non-vacuity: the wired writers actually populate belief_sets."""

    def test_both_writers_grow_belief_sets(self):
        state = UnifiedAnalysisState(initial_text="texte de test")
        before = len(state.belief_sets)

        _write_text_to_kb_to_state(
            {"belief_candidates": ["mortal(socrates)"]}, state, {}
        )
        _write_kb_to_tweety_to_state(
            {
                "status": "ok",
                "formulas": [{"formula": "man(x) -> mortal(x)", "logic_type": "fol"}],
            },
            state,
            {},
        )

        assert len(state.belief_sets) == before + 2, (
            "the kb-chain writers must populate belief_sets — a phase wired "
            "to writers that produce nothing would satisfy the guards above "
            "while leaving the golden threshold red"
        )


class _FakeRegistry:
    """Deterministic registry: returns a FIXED provider order, so the
    executor's selection is observable without depending on set-hash order
    (the very nondeterminism under test)."""

    def __init__(self, providers):
        self._providers = providers

    def find_for_capability(self, capability):
        return list(self._providers)


def _kb_plugin_registration(name: str = "text_to_kb_plugin") -> ComponentRegistration:
    return ComponentRegistration(
        name=name, component_type=ComponentType.PLUGIN, capabilities=["nl_extraction"]
    )


async def _service_invoke(input_text: str, context: dict) -> dict:
    return {"belief_candidates": ["mortal(socrates)"], "ran": "service"}


def _kb_service_registration(name: str = "text_to_kb_service") -> ComponentRegistration:
    return ComponentRegistration(
        name=name,
        component_type=ComponentType.SERVICE,
        capabilities=["nl_extraction"],
        invoke=_service_invoke,
    )


class TestExecutorPrefersRunnableProvider:
    """The second layer of #2296, measured on the post-wiring real run: the
    text_to_kb phase completed in 0.00 s with a None output because the
    capability resolved (set-ordered — hash order varies per process, 1 of 4
    measured) to ``text_to_kb_plugin``, an SK plugin with NO pipeline
    invoke, while ``text_to_kb_service`` sat unused in the same list. The
    workflow reported 17 completed / 0 degraded and belief_sets stayed 0.

    A capability served by both an agent-side plugin and a pipeline service
    must run the runnable one, whatever order the set gave.
    """

    async def test_dead_plugin_first_still_runs_the_service(self):
        registry = _FakeRegistry(
            [_kb_plugin_registration(), _kb_service_registration()]
        )
        executor = WorkflowExecutor(registry)
        phase = WorkflowPhase(name="text_to_kb", capability="nl_extraction")
        _name, result, output = await executor._execute_phase(
            phase, "text_to_kb", "some text", {}
        )
        assert result.status.value == "completed"
        assert result.component_used == "text_to_kb_service", (
            "the no-invoke plugin provider won selection and the phase "
            "completed with a None output — the belief-set production the "
            "phase exists for never ran (#2296)"
        )
        assert output == {"belief_candidates": ["mortal(socrates)"], "ran": "service"}

    async def test_service_first_still_runs_the_service(self):
        registry = _FakeRegistry(
            [_kb_service_registration(), _kb_plugin_registration()]
        )
        executor = WorkflowExecutor(registry)
        phase = WorkflowPhase(name="text_to_kb", capability="nl_extraction")
        _name, result, output = await executor._execute_phase(
            phase, "text_to_kb", "some text", {}
        )
        assert result.component_used == "text_to_kb_service"
        assert output is not None
