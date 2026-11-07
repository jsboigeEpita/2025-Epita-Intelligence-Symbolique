"""#3470 — the conversation_real engine's recorded findings reach the judge.

Measured on main (``f3157c634``, before the fix): the real mode runs its
informal agent then its FOL agent and records into its own ``AnalysisState``
(``agent_results``, ``fallacies_detected``, consistency tri-state). The #3378
harness exposes no ``panel_state`` for it — the sweep writes no judge
artifacts and ``panel_state_absence_reason`` names
``engine_has_no_unified_analysis_state`` — so the engine decides internally
but the blind judge has no arm to read.

The fix is an honest adapter, never a templated act: the harness hands the
JUDGE a dict carrying what the run RECORDED (fallacy types and
justifications, FOL formulas, the solver's tri-state verdict), and the
reading-folder renders it in the engine's own voice. Nothing recorded stays
a named absence; a run that captured nothing keeps the named absence.

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
    run_conversation_real_mode,
)
from scripts.dataset.judge_panel import arm_health, pipeline_text_from_state

#: The recorded material of a synthetic real-mode run: two fallacies the
#: informal agent found, two FOL formulas the solver did not decide on.
_RECORDED_FALLACIES = [
    {
        "nom": "appel à l'autorité",
        "explication": "un exemple synthétique de justification",
    },
    {"type": "fausse dichotomie", "justification": "un second exemple"},
]
_RECORDED_FORMULAS = ["∀x (P(x) → Q(x))", "∃y R(y)"]

_CONVERSATION_STATE_DICT = {
    "engine": "conversation_real",
    "steps_completed": ["informal", "fol_logic"],
    "fallacies_count": 2,
    "fallacies": [
        {"type": "appel à l'autorité", "justification": "un exemple synthétique"},
        {"type": "fausse dichotomie", "justification": "un second exemple"},
    ],
    "fol": {
        "formulas": list(_RECORDED_FORMULAS),
        "formulas_count": 2,
        "consistency": None,
        "consistency_undetermined": True,
        "consistency_message": "",
    },
}

_REAL_SIGNATURE = {
    "opaque_id": "corpus_3470",
    "workflow": "conversation_real",
    "outcome": {"status": "ok", "reason": None},
    "provenance": {"issue": 3378, "mode": "conversation_real"},
}


class TestTheJudgeReadsTheEngineOwnRecord:
    """The arm text carries the recorded findings, in the engine's voice."""

    def test_the_judge_text_carries_the_recorded_findings(self):
        """Born red on main: the judge's producer prints four absence lines.

        ``pipeline_text_from_state`` is the judge's exact consumer for every
        arm; a conversation_real signature must route to the engine's own
        rendering, not the pipeline's acts.
        """
        text = pipeline_text_from_state(
            {"state": dict(_CONVERSATION_STATE_DICT)}, dict(_REAL_SIGNATURE)
        )
        assert "appel à l'autorité" in text
        assert "un exemple synthétique" in text
        assert "∀x (P(x) → Q(x))" in text
        # The tri-state verdict is named, never defaulted.
        assert "non déterminée" in text
        # The pipeline's acts vocabulary never appears for this engine.
        assert "absent de l'état" not in text

    def test_the_consistency_verdict_wording_is_tri_state(self):
        """None is undetermined; 1.0 established; 0.0 refuted — three words."""

        def _text(consistency: object) -> str:
            state = dict(_CONVERSATION_STATE_DICT)
            state["fol"] = {
                "formulas": list(_RECORDED_FORMULAS),
                "formulas_count": 2,
                "consistency": consistency,
                "consistency_undetermined": consistency is None,
                "consistency_message": "",
            }
            return pipeline_text_from_state({"state": state}, dict(_REAL_SIGNATURE))

        assert "non déterminée" in _text(None)
        assert "établie" in _text(1.0)
        refuted = _text(0.0)
        assert "réfutée" in refuted
        assert "contradiction" in refuted

    def test_nothing_recorded_stays_a_named_absence(self):
        """A run that recorded nothing renders that, inventing no finding."""
        text = pipeline_text_from_state(
            {
                "state": {
                    "engine": "conversation_real",
                    "steps_completed": [],
                    "fallacies_count": 0,
                    "fallacies": [],
                    "fol": {
                        "formulas": [],
                        "formulas_count": 0,
                        "consistency": None,
                        "consistency_undetermined": True,
                        "consistency_message": "",
                    },
                }
            },
            dict(_REAL_SIGNATURE),
        )
        assert "appel à l'autorité" not in text
        assert "aucun sophisme" in text or "rien" in text

    def test_the_arm_is_not_degraded(self):
        """No acts by design carries no degraded report — #3458's rule."""
        health = arm_health({"state": dict(_CONVERSATION_STATE_DICT)})
        assert health["pipeline_degraded"] is False


class TestTheHarnessHandsTheJudgeAState:
    """The panel sweep captures what the run recorded — never invents."""

    def test_panel_mode_returns_the_recorded_state(self):
        """Born red on main: the runner exposes no ``panel_state``.

        A fake orchestrator (patched at its home module — the runner imports
        it inside the function body) records two fallacies and an undecided
        FOL check; ``panel_mode=True`` must surface them on the result.
        """
        import asyncio

        class _FakeState:
            fallacies_detected = 2
            fallacy_analysis_errors = []
            consistency_score = None
            agent_results = {
                "informal": {
                    "fallacies_count": 2,
                    "main_issues": [
                        "appel à l'autorité",
                        "fausse dichotomie",
                    ],
                    "raw_result": {"fallacies": list(_RECORDED_FALLACIES)},
                },
                "fol_logic": {
                    "formulas_count": 2,
                    "consistency": None,
                    "consistency_undetermined": True,
                    "consistency_message": "",
                    "raw_result": {"formulas": list(_RECORDED_FORMULAS)},
                },
            }

        class _FakeOrchestrator:
            mode = "real"
            state = _FakeState()

            def __init__(self, mode=None, kernel=None):
                pass

            async def run_orchestration_async(self, text):
                return None

            def get_conversation_state(self):
                return {
                    "real_agent_setup_failures": {},
                    "messages_count": 0,
                    "tools_count": 0,
                }

        import argumentation_analysis.orchestration.conversation_orchestrator as home

        original = home.ConversationOrchestrator
        home.ConversationOrchestrator = _FakeOrchestrator
        try:
            result = asyncio.run(
                run_conversation_real_mode(
                    "Texte synthétique.",
                    "corpus_3470",
                    panel_mode=True,
                )
            )
        finally:
            home.ConversationOrchestrator = original
        assert result.success is True
        panel_state = result.panel_state
        assert panel_state is not None
        # The judge's dict carries the RECORDED material, not a mimicry.
        assert panel_state["fallacies_count"] == 2
        types = [f["type"] for f in panel_state["fallacies"]]
        assert "appel à l'autorité" in types
        assert panel_state["fol"]["consistency"] is None
        assert panel_state["fol"]["formulas"] == _RECORDED_FORMULAS

    def test_a_stateful_run_no_longer_names_the_engine_absence(self):
        """Born red on main: the reason is ``engine_has_no_unified...``."""
        result = ModeResult(
            mode="conversation_real",
            corpus_id="corpus_3470",
            success=True,
            terminates=True,
            panel_state=dict(_CONVERSATION_STATE_DICT),
        )
        assert panel_state_absence_reason(result) is None

    def test_the_sweep_passes_panel_flags_to_conversation_real(self):
        """Born red on main: the mode is not in the stateful set."""
        assert "conversation_real" in PANEL_STATEFUL_MODES


class TestThePipelineArmIsUntouched:
    """A pipeline signature keeps the pipeline's producer — #3468 intact."""

    def test_a_pipeline_signature_keeps_the_pipeline_text(self):
        """No provenance mode: the fiche's producer renders the acts."""
        state = {
            "act1_framing": "Acte I synthétique.",
            "act2_narrative": None,
            "act3_conclusion": None,
            "narrative_synthesis": None,
            "interpretive_question": None,
            "raw_text": "Texte synthétique.",
        }
        signature = {
            "opaque_id": "corpus_3470",
            "outcome": {"status": "ok", "reason": None},
        }
        text = pipeline_text_from_state({"state": state}, signature)
        assert "Acte I synthétique." in text
        # The pipeline's vocabulary — absence lines — stays this arm's own.
        assert "absent de l'état" in text
