"""#3472 — a productive delegation run becomes a judge-readable verdict.

Measured on main (``040f53360``, before the fix): the delegation engine
executes its operational tasks and returns them (``operational_results``,
``conclusion``, the CC #1531 degraded verdict) — but the #3378 harness exposes
no ``panel_state`` for it: ``hierarchical_delegation`` is absent from
``PANEL_STATEFUL_MODES``, so the sweep writes no judge artifacts and
``panel_state_absence_reason`` names ``engine_has_no_unified_analysis_state``.
Five productive tasks can complete and the blind judge still has no arm to
read.

The fix follows the accepted #3470 shape, never a templated act: an adapter
hands the judge a dict carrying what the run RECORDED (objectives, each task's
capability and product, the strategic conclusion, the honest degraded
verdict), a producer renders it in the engine's own voice, and the judge
routes on the signature's provenance mode. A run cut at the wall-clock budget
keeps the absence of its conclusion NAMED — with its task counts, exactly as
the issue words it.

All texts and findings below are synthetic. Offline: no JVM, no network,
no LLM.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.compare_orchestration_modes import (
    PANEL_STATEFUL_MODES,
    ModeResult,
    panel_state_absence_reason,
)
from scripts.dataset.judge_panel import arm_health, pipeline_text_from_state

#: The judge's state dict for a synthetic productive run — the exact shape the
#: #3472 adapter builds (two objectives, one task that produced a fallacy, one
#: that failed for want of a provider, and a strategic conclusion).
_DELEGATION_STATE = {
    "engine": "hierarchical_delegation",
    "objectives": [
        {"id": "obj_1", "description": "Repérer les procédés rhétoriques"},
        {"id": "obj_2", "description": "Vérifier la cohérence logique"},
    ],
    "task_assignments": [
        {
            "task_id": "task_1",
            "agent_id": "informal_agent",
            "motivation": "corpus rhétorique",
        }
    ],
    "tasks": [
        {
            "task_id": "task_1",
            "objective_id": "obj_1",
            "status": "completed",
            "capability": "fallacy_detection",
            "productivity": 1.0,
            "outputs": {
                "total_fallacies": 1,
                "fallacies": [
                    {
                        "type": "appel à l'autorité",
                        "justification": "un exemple synthétique",
                    }
                ],
            },
        },
        {
            "task_id": "task_2",
            "objective_id": "obj_2",
            "status": "failed",
            "capability": None,
            "productivity": 0.0,
            "reason": "no_provider_for_required_capabilities",
        },
    ],
    "conclusion": (
        "L'analyse du document montre un procédé d'autorité dominant, sans "
        "contradiction formelle établie."
    ),
    "degraded": False,
    "degradation_reasons": [],
    "task_counts": {"planned": 2, "productive": 1, "failed": 1, "degraded": 0},
    "partial": False,
}

_DELEGATION_SIGNATURE = {
    "opaque_id": "corpus_3472",
    "workflow": "hierarchical_delegation",
    "outcome": {"status": "ok", "reason": None},
    "provenance": {"issue": 3378, "mode": "hierarchical_delegation"},
}


def _state(**overrides):
    state = dict(_DELEGATION_STATE)
    state.update(overrides)
    return state


def _text(state):
    return pipeline_text_from_state({"state": state}, dict(_DELEGATION_SIGNATURE))


class TestTheJudgeReadsTheEngineOwnRecord:
    """The arm text carries the recorded tasks, in the engine's voice."""

    def test_the_judge_text_carries_the_task_products_and_conclusion(self):
        """Born red on main: the signature routes to the pipeline's producer,
        whose acts vocabulary renders four absence lines instead."""
        text = _text(_state())
        assert "appel à l'autorité" in text
        assert "un exemple synthétique" in text
        assert "L'analyse du document montre" in text
        # A failed task is named as what it is, with its reason.
        assert "no_provider_for_required_capabilities" in text
        # The pipeline's acts vocabulary never appears for this engine.
        assert "absent de l'état" not in text

    def test_a_degraded_run_renders_its_honest_verdict_and_counts(self):
        """CC #1531's degraded conclusion is a report, not an analysis — the
        arm says so, with the task counts the issue demands."""
        state = _state(
            tasks=[
                {
                    "task_id": "task_1",
                    "objective_id": "obj_1",
                    "status": "completed",
                    "capability": "fallacy_detection",
                    "productivity": 0.0,
                    "degradation_reasons": ["status=unavailable"],
                },
                {
                    "task_id": "task_2",
                    "objective_id": "obj_2",
                    "status": "failed",
                    "capability": None,
                    "productivity": 0.0,
                    "reason": "insufficient_input",
                },
            ],
            conclusion=(
                "Analyse dégradée : aucune des 2 tâche(s) opérationnelle(s) "
                "n'a produit de résultat exploitable."
            ),
            degraded=True,
            degradation_reasons=[
                "fallacy_detection: status=unavailable",
                "task_2: insufficient_input",
            ],
            task_counts={"planned": 2, "productive": 0, "failed": 1, "degraded": 1},
        )
        text = _text(state)
        assert "Analyse dégradée" in text
        # The counts ride along: 0 productive on 2 tasks.
        assert "0" in text and "2" in text

    def test_a_budget_cut_run_keeps_the_absent_conclusion_named(self):
        """The strategic conclusion is produced AFTER the task loop — at a
        wall-clock breach it does not exist, and the arm says so with the
        counts of the tasks that finished."""
        state = _state(
            tasks=[
                {
                    "task_id": "task_1",
                    "objective_id": "obj_1",
                    "status": "completed",
                    "capability": "deep_synthesis",
                    "productivity": 1.0,
                    "outputs": {"report": "une analyse partielle du corpus"},
                }
            ],
            conclusion=None,
            task_counts={"planned": 3, "productive": 1, "failed": 0, "degraded": 0},
            partial=True,
        )
        text = _text(state)
        assert "une analyse partielle du corpus" in text
        # The absent conclusion is named, never invented.
        assert "conclusion" in text.lower()
        assert "L'analyse du document montre" not in text

    def test_the_arm_is_not_degraded(self):
        """No acts by design carries no degraded report — #3458's rule."""
        health = arm_health({"state": _state()})
        assert health["pipeline_degraded"] is False


class TestTheAdapterCarriesTheRecord:
    """The dict is what the run recorded — never a mimicry of a state."""

    def test_the_dict_carries_tasks_products_and_counts(self):
        from scripts.compare_orchestration_modes import delegation_panel_state

        result = {
            "mode": "delegation",
            "objectives": _DELEGATION_STATE["objectives"],
            "tasks_created": 2,
            "task_assignments": _DELEGATION_STATE["task_assignments"],
            "operational_results": [
                {
                    "task_id": "task_1",
                    "objective_id": "obj_1",
                    "status": "completed",
                    "capability": "fallacy_detection",
                    "outputs": {
                        "total_fallacies": 1,
                        "fallacies": [
                            {
                                "type": "appel à l'autorité",
                                "justification": "un exemple synthétique",
                            }
                        ],
                    },
                },
                {
                    "task_id": "task_2",
                    "objective_id": "obj_2",
                    "status": "failed",
                    "reason": "no_provider_for_required_capabilities",
                },
            ],
            "evaluation": {"obj_1": {"success_rate": 1.0}},
            "conclusion": _DELEGATION_STATE["conclusion"],
            "degraded": False,
            "degradation_reasons": [],
        }
        state = delegation_panel_state(result)
        assert state["engine"] == "hierarchical_delegation"
        assert state["task_counts"] == {
            "planned": 2,
            "productive": 1,
            "failed": 1,
            "degraded": 0,
        }
        first = state["tasks"][0]
        assert first["capability"] == "fallacy_detection"
        assert first["productivity"] == 1.0
        assert first["outputs"]["fallacies"][0]["type"] == "appel à l'autorité"
        second = state["tasks"][1]
        assert second["status"] == "failed"
        assert second["reason"] == "no_provider_for_required_capabilities"
        assert state["conclusion"].startswith("L'analyse du document")
        assert state["partial"] is False

    def test_a_productive_but_degraded_task_keeps_both_truths(self):
        """#1550's predicate: produced AND partial — the dict keeps the
        product and the admission."""
        from scripts.compare_orchestration_modes import delegation_panel_state

        result = {
            "operational_results": [
                {
                    "task_id": "task_1",
                    "objective_id": "obj_1",
                    "status": "completed",
                    "capability": "fallacy_detection",
                    "degraded": True,
                    "degradation_reasons": ["status=unavailable"],
                    "outputs": {
                        "fallacies": [
                            {
                                "type": "fausse dichotomie",
                                "justification": "partielle",
                            }
                        ]
                    },
                }
            ],
        }
        state = delegation_panel_state(result)
        task = state["tasks"][0]
        assert task["productivity"] == 0.5
        assert task["degradation_reasons"] == ["status=unavailable"]
        assert task["outputs"]["fallacies"][0]["type"] == "fausse dichotomie"
        assert state["task_counts"]["productive"] == 1
        assert state["task_counts"]["degraded"] == 1

    def test_a_partial_run_counts_its_finished_tasks(self):
        from scripts.compare_orchestration_modes import delegation_panel_state

        finished = [
            {
                "task_id": f"task_{i}",
                "objective_id": "obj_1",
                "status": "completed",
                "capability": "fallacy_detection",
                "outputs": {"total_fallacies": 0},
            }
            for i in (1, 2)
        ]
        state = delegation_panel_state(
            {"operational_results": finished}, partial=True, planned=5
        )
        assert state["partial"] is True
        assert state["conclusion"] is None
        assert state["task_counts"]["planned"] == 5
        assert state["task_counts"]["productive"] == 2


class TestTheHarnessHandsTheJudgeAState:
    """The panel sweep captures what the run recorded — never invents."""

    def test_a_stateful_run_no_longer_names_the_engine_absence(self):
        """Born red on main: the reason is ``engine_has_no_unified...``."""
        result = ModeResult(
            mode="hierarchical_delegation",
            corpus_id="corpus_3472",
            success=True,
            terminates=True,
            panel_state=_state(),
        )
        assert panel_state_absence_reason(result) is None

    def test_the_sweep_passes_panel_flags_to_delegation(self):
        """Born red on main: the mode is not in the stateful set."""
        assert "hierarchical_delegation" in PANEL_STATEFUL_MODES

    def test_the_runner_surfaces_the_recorded_state_in_panel_mode(self):
        """Born red on main: the runner accepts no ``panel_mode`` and never
        sets ``panel_state``."""
        import asyncio

        import argumentation_analysis.orchestration.hierarchical.orchestrator as home
        import argumentation_analysis.orchestration.registry_setup as registry_home
        from scripts.compare_orchestration_modes import (
            run_hierarchical_delegation_mode,
        )

        async def _fake_run(
            text,
            capability_registry=None,
            mode="bridge",
            checkpoint_callback=None,
            **kwargs,
        ):
            return {
                "mode": "delegation",
                "objectives": [dict(o) for o in _DELEGATION_STATE["objectives"]],
                "tasks_created": 2,
                "task_assignments": [
                    dict(a) for a in _DELEGATION_STATE["task_assignments"]
                ],
                "operational_results": [
                    {
                        "task_id": "task_1",
                        "objective_id": "obj_1",
                        "status": "completed",
                        "capability": "fallacy_detection",
                        "outputs": {
                            "total_fallacies": 1,
                            "fallacies": [
                                {
                                    "type": "appel à l'autorité",
                                    "justification": "un exemple synthétique",
                                }
                            ],
                        },
                    },
                    {
                        "task_id": "task_2",
                        "objective_id": "obj_2",
                        "status": "failed",
                        "reason": "no_provider_for_required_capabilities",
                    },
                ],
                "evaluation": {"obj_1": {"success_rate": 1.0}},
                "conclusion": _DELEGATION_STATE["conclusion"],
                "degraded": False,
                "degradation_reasons": [],
            }

        original_run = home.run_hierarchical_analysis
        original_registry = registry_home.setup_registry
        home.run_hierarchical_analysis = _fake_run
        registry_home.setup_registry = lambda **kwargs: object()
        try:
            result = asyncio.run(
                run_hierarchical_delegation_mode(
                    "Texte synthétique.",
                    "corpus_3472",
                    panel_mode=True,
                    source_metadata={"opaque_id": "corpus_3472"},
                )
            )
        finally:
            home.run_hierarchical_analysis = original_run
            registry_home.setup_registry = original_registry
        assert result.success is True
        assert result.panel_state is not None
        assert result.panel_state["task_counts"]["productive"] == 1
        assert result.panel_state["source_metadata"]["opaque_id"] == "corpus_3472"

    def test_a_budget_cut_runner_names_the_partial_tasks(self):
        import asyncio

        import argumentation_analysis.orchestration.hierarchical.orchestrator as home
        import argumentation_analysis.orchestration.registry_setup as registry_home
        from scripts.compare_orchestration_modes import (
            run_hierarchical_delegation_mode,
        )

        async def _slow_run(text, **kwargs):
            await asyncio.sleep(5)

        original_run = home.run_hierarchical_analysis
        original_registry = registry_home.setup_registry
        home.run_hierarchical_analysis = _slow_run
        registry_home.setup_registry = lambda **kwargs: object()
        try:
            result = asyncio.run(
                run_hierarchical_delegation_mode(
                    "Texte synthétique.",
                    "corpus_3472",
                    max_wall_seconds=0.05,
                    panel_mode=True,
                )
            )
        finally:
            home.run_hierarchical_analysis = original_run
            registry_home.setup_registry = original_registry
        assert result.terminated_by_budget is True
        assert result.panel_state is not None
        assert result.panel_state["partial"] is True
        assert result.panel_state["conclusion"] is None


class TestThePipelineArmIsUntouched:
    """A pipeline signature keeps the pipeline's producer — #3468 intact."""

    def test_a_pipeline_signature_keeps_the_pipeline_text(self):
        state = {
            "act1_framing": "Acte I synthétique.",
            "act2_narrative": None,
            "act3_conclusion": None,
            "narrative_synthesis": None,
            "interpretive_question": None,
            "raw_text": "Texte synthétique.",
        }
        signature = {
            "opaque_id": "corpus_3472",
            "outcome": {"status": "ok", "reason": None},
        }
        text = pipeline_text_from_state({"state": state}, signature)
        assert "Acte I synthétique." in text
        assert "absent de l'état" in text
