# -*- coding: utf-8 -*-
"""#3377 — the ablation SWITCH: a run-time list of phases left out of the workflow.

Two consumers need the same mechanism with a different phase: this issue's
persona arm (``historian,strategist``) and #1649's paired run
(``aspic_analysis``). One switch, a list of phase names.

What is witnessed here:
- the two personas LEAVE the built workflow, and so does every dependency
  edge that pointed at them; the workflow that remains is a valid DAG;
- another phase (``aspic_analysis``) leaves the same way, with ITS edges;
- an empty list leaves the workflow untouched;
- a name that is not a phase RAISES (a caller error, never a silent no-op);
- the state records the list, so an ablation arm is told apart from a full
  run;
- the consumers see what an absent persona gives today: the counter prompt is
  byte-identical to the empty-note prompt, and Acte I says the strategic read
  is absent (measured on a fixture, no model).

Privacy HARD: synthetic sentences only — no corpus text.
"""

import asyncio

import pytest

from argumentation_analysis.core.capability_registry import CapabilityRegistry
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration import workflows as workflows_module
from argumentation_analysis.orchestration.workflows import (
    SKIP_PHASES_ENV_VAR,
    apply_skipped_phases,
    build_spectacular_workflow,
    read_skipped_phases,
)

_FAKE_KEY = "sk-fake-witness-zero-bill-3377"


def _phase_names(workflow) -> set:
    return {phase.name for phase in workflow.phases}


def _deps(workflow, phase_name: str) -> list:
    phase = workflow.get_phase(phase_name)
    assert phase is not None, f"phase '{phase_name}' must exist in the workflow"
    return list(phase.depends_on)


def _level_index(workflow) -> dict:
    """{phase name: level index} from the workflow's own execution order."""
    index = {}
    for level, names in enumerate(workflow.get_execution_order()):
        for name in names:
            index[name] = level
    return index


class TestTheTwoPersonasLeaveTheWorkflow:
    def test_neither_persona_remains(self):
        workflow = build_spectacular_workflow()
        assert {"historian", "strategist"} <= _phase_names(workflow), (
            "the workflow must carry both personas BEFORE the switch, otherwise "
            "this witness measures nothing"
        )

        switched = apply_skipped_phases(workflow, ["historian", "strategist"])

        names = _phase_names(switched)
        assert "historian" not in names
        assert "strategist" not in names
        assert names, "the workflow must keep the phases that were not named"

    def test_the_edges_that_pointed_at_them_leave_too(self):
        workflow = build_spectacular_workflow()
        switched = apply_skipped_phases(workflow, ["historian", "strategist"])

        assert "historian" not in _deps(switched, "nl_to_logic"), (
            "the translator declared the historian as an input; the edge must "
            "leave with the phase, or the DAG carries a dangling dependency"
        )
        assert "strategist" not in _deps(switched, "act1_framing"), (
            "Acte I declared the strategist as an input; the edge must leave "
            "with the phase"
        )
        # the other declared inputs are untouched
        assert "extract" in _deps(switched, "nl_to_logic")
        assert {"extract", "stakes"} <= set(_deps(switched, "act1_framing"))

    def test_the_workflow_that_remains_is_a_valid_dag(self):
        workflow = build_spectacular_workflow()
        switched = apply_skipped_phases(workflow, ["historian", "strategist"])

        assert (
            switched.validate() == []
        ), "no dependency may point at a phase that left the DAG"
        levels = _level_index(switched)
        assert set(levels) == _phase_names(switched), (
            "every remaining phase must be schedulable — a phase that no "
            "level can reach is a broken DAG"
        )
        for phase in switched.phases:
            for dep in phase.depends_on:
                assert (
                    levels[dep] < levels[phase.name]
                ), f"'{phase.name}' must run after '{dep}'"

    def test_the_original_workflow_is_not_mutated(self):
        workflow = build_spectacular_workflow()
        apply_skipped_phases(workflow, ["historian", "strategist"])

        assert {"historian", "strategist"} <= _phase_names(workflow), (
            "the switch must not empty the shared workflow definition — the "
            "next run without the switch must find the phases again"
        )


class TestAnotherPhaseLeavesTheSameWay:
    def test_aspic_leaves_with_its_edges(self):
        workflow = build_spectacular_workflow()
        assert "aspic_analysis" in _phase_names(workflow)

        switched = apply_skipped_phases(workflow, ["aspic_analysis"])

        names = _phase_names(switched)
        assert "aspic_analysis" not in names
        assert "aspic_analysis" not in _deps(switched, "formal_synthesis")
        assert "aspic_analysis" not in _deps(switched, "tweety_interpretation")
        assert switched.validate() == []
        levels = _level_index(switched)
        assert set(levels) == names


class TestTheEmptyListLeavesEverythingAlone:
    def test_an_empty_list_returns_the_same_workflow(self):
        workflow = build_spectacular_workflow()
        switched = apply_skipped_phases(workflow, [])

        assert switched is workflow, "an empty list is not a no-op filter"
        assert _phase_names(switched) == _phase_names(workflow)

    def test_an_empty_list_keeps_every_edge(self):
        workflow = build_spectacular_workflow()
        switched = apply_skipped_phases(workflow, [])

        assert "historian" in _deps(switched, "nl_to_logic")
        assert "strategist" in _deps(switched, "act1_framing")


class TestAnUnknownNameRaises:
    def test_it_raises_and_names_the_valid_phases(self):
        workflow = build_spectacular_workflow()

        with pytest.raises(ValueError) as excinfo:
            apply_skipped_phases(workflow, ["historiann"])

        message = str(excinfo.value)
        assert "historiann" in message, "the error must name the unknown name"
        assert "historian" in message, "the error must name the valid phases"
        assert "strategist" in message

    def test_the_workflow_survives_the_refusal(self):
        workflow = build_spectacular_workflow()
        with pytest.raises(ValueError):
            apply_skipped_phases(workflow, ["not_a_phase"])

        assert "historian" in _phase_names(workflow)


class TestTheSwitchIsReadFromTheEnvironment:
    def test_the_variable_carries_the_list(self, monkeypatch):
        monkeypatch.setenv(SKIP_PHASES_ENV_VAR, "historian,strategist")
        assert read_skipped_phases() == ["historian", "strategist"]

    def test_an_unset_variable_means_no_phase_is_skipped(self, monkeypatch):
        monkeypatch.delenv(SKIP_PHASES_ENV_VAR, raising=False)
        assert read_skipped_phases() == []

    def test_blanks_and_duplicates_are_dropped(self, monkeypatch):
        monkeypatch.setenv(SKIP_PHASES_ENV_VAR, " historian , , strategist ,historian ")
        assert read_skipped_phases() == ["historian", "strategist"]


class TestTheStateRecordsTheArm:
    """The arms must be told apart by what the run recorded."""

    @staticmethod
    def _run(monkeypatch, env_value):
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        if env_value is None:
            monkeypatch.delenv(SKIP_PHASES_ENV_VAR, raising=False)
        else:
            monkeypatch.setenv(SKIP_PHASES_ENV_VAR, env_value)
        state = UnifiedAnalysisState("Synthetic text for the switch witness.")
        # An empty registry: no provider resolves, so no phase reaches a
        # model — the run exercises the wiring, not the analysis.
        result = asyncio.run(
            run_unified_analysis(
                "Synthetic text for the switch witness.",
                workflow_name="spectacular",
                registry=CapabilityRegistry(),
                state=state,
            )
        )
        return state, result

    def test_the_state_carries_the_list(self, monkeypatch):
        state, result = self._run(monkeypatch, "historian,strategist")

        assert state.phases_left_out == ["historian", "strategist"]
        assert result["phases_left_out"] == ["historian", "strategist"]
        assert "historian" not in result["phases"]
        assert "strategist" not in result["phases"]
        snapshot = state.get_state_snapshot(summarize=False)
        assert snapshot["phases_left_out"] == ["historian", "strategist"]
        assert state.get_state_snapshot(summarize=True)["phases_left_out"] == [
            "historian",
            "strategist",
        ]

    def test_a_full_run_records_nothing_skipped(self, monkeypatch):
        state, result = self._run(monkeypatch, None)

        assert state.phases_left_out == []
        assert result["phases_left_out"] == []

    def test_the_shared_catalog_is_not_emptied(self, monkeypatch):
        """The switch is per run: the next run without it finds the phases."""
        self._run(monkeypatch, "historian,strategist")
        catalog = workflows_module.get_workflow_catalog()
        assert "historian" in _phase_names(catalog["spectacular"])
        assert "strategist" in _phase_names(catalog["spectacular"])


class TestWhatTheConsumersSeeWithoutThePersona:
    """#3377 (State of 14/11) — the consumers see what an absent persona gives
    today. Measured here on fixtures, with no model in the loop."""

    def test_the_counter_prompt_is_the_empty_note_prompt(self, monkeypatch):
        from argumentation_analysis.agents.core.context.historian import context_note
        from argumentation_analysis.orchestration import invoke_callables
        from argumentation_analysis.orchestration.invoke_callables import (
            _generate_counters_for_targets,
        )

        captured: dict = {}

        async def _fake(client, model, messages, **kwargs):
            captured["system"] = messages[0]["content"]
            return _FakeResponse("[]")

        monkeypatch.setenv("OPENAI_API_KEY", _FAKE_KEY)
        monkeypatch.setattr(invoke_callables, "_guarded_chat_completion", _fake)

        # A state the historian NEVER wrote: the switch leaves the phase out,
        # so nothing writes the read.
        state = UnifiedAnalysisState("Synthetic text for the switch witness.")
        assert context_note(state) == "", (
            "no historian read means no note — the prompt must not advertise a "
            "provenance that does not exist"
        )

        asyncio.run(
            _generate_counters_for_targets(
                None,
                "fake-model",
                ["one synthetic target"],
                target_ids=["arg_1"],
                context_note=context_note(state),
            )
        )
        without_persona = captured["system"]

        asyncio.run(
            _generate_counters_for_targets(
                None,
                "fake-model",
                ["one synthetic target"],
                target_ids=["arg_1"],
                context_note="",
            )
        )
        empty_note = captured["system"]

        assert without_persona == empty_note, (
            "the counter prompt of a run without the historian must be "
            "byte-identical to the empty-note prompt"
        )
        assert "SITUATION HISTORIQUE" not in without_persona

    def test_acte_i_says_the_strategic_read_is_absent(self):
        """Measured on a fixture: with no strategist, Acte I renders the
        absence — and its instruction still announces a read that is given
        (reported, not fixed: no prompt change is due)."""
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            Act1Evidence,
            build_act1_prompt,
        )

        prompt = build_act1_prompt(Act1Evidence())

        assert (
            "aucune lecture stratégique" in prompt
        ), "the absent read must be named, never filled in by the act"
        assert "ne produis pas la tienne" in prompt
        assert "DÉJÀ DONNÉE ci-dessous" in prompt, (
            "MEASURED: the instruction still announces a given read while the "
            "block says it is absent — reported in the PR body, not fixed "
            "here (a prompt change would need a re-record)"
        )


class _FakeMsg:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMsg(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


def test_the_module_exposes_the_switch():
    assert callable(apply_skipped_phases)
    assert callable(read_skipped_phases)
    assert SKIP_PHASES_ENV_VAR
