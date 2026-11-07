"""#3469 — the conversational safety net must not discard the partial state.

Measured on main (``f3157c634``, before the fix): ``run_conversational_mode``'s
safety-net branch — the ``asyncio.TimeoutError`` path that fires when a single
in-flight call hangs past the between-turn check — returns a ``ModeResult``
with **no** ``panel_state``. The partial ``UnifiedAnalysisState`` the run paid
for dies with the cancelled coroutine, ``write_panel_mode_artifacts`` returns
``None``, and the judge has no artifact for that document. The internal bound
(C1 #1500) exits cleanly with a real partial verdict; the safety net is the
one path that still loses it.

The behaviour witnesses fake ``run_conversational_analysis`` (imported inside
``run_conversational_mode``'s body, so patched at its home module) with the
recovery-hook contract this fix adds: build the state, hand it to the
caller-owned ``state_sink`` the moment it exists, then hang past the net.
"""

import asyncio
import inspect

import pytest

import compare_orchestration_modes as harness
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration import conversational_orchestrator

#: Opaque synthetic text — no corpus content, ever (dataset privacy).
TEXT = (
    "Le comité déclare que la réforme est nécessaire et que quiconque "
    "s'y oppose ne sert que ses intérêts propres."
)

#: The real safety net keeps a >=30 s headroom so the internal bound fires
#: first; the witnesses monkeypatch the helper down to this margin so the
#: TimeoutError branch runs in milliseconds. The real formula is pinned by
#: its own companion below.
_FAST_NET = 0.05


def _hang_past_the_net(monkeypatch, fake_analysis):
    """Point the harness at ``fake_analysis`` and shrink the safety net."""
    monkeypatch.setattr(
        conversational_orchestrator, "run_conversational_analysis", fake_analysis
    )
    monkeypatch.setattr(
        harness, "_conversational_safety_net_timeout", lambda s: _FAST_NET
    )


class TestAFakeRunHonouringTheHookContract:
    """The producer-side seam this fix adds."""

    def test_the_real_producer_exposes_the_state_sink_hook(self):
        """``run_conversational_analysis`` accepts a caller-owned state sink.

        Without the parameter the harness cannot pass one, so the safety-net
        branch can never reach the partial state — red on the pre-fix tree.
        """
        parameters = inspect.signature(
            conversational_orchestrator.run_conversational_analysis
        ).parameters
        assert "state_sink" in parameters


class TestTheSafetyNetHandsThePartialStateBack:
    """The cut path returns what the run established, not an empty row."""

    async def test_a_kill_past_the_net_hands_the_state_to_the_panel_dump(
        self, monkeypatch
    ):
        """A hung run with a populated state still exposes it to the dump.

        Born red on main: ``panel_state`` is ``None`` on the safety-net path,
        so ``write_panel_mode_artifacts`` writes no judge artifact.
        """

        async def fake_analysis(**kwargs):
            state = UnifiedAnalysisState(TEXT)
            sink = kwargs.get("state_sink")
            if sink is not None:
                sink.append(state)
            await asyncio.sleep(5.0)  # hung past the net, like a stuck call

        _hang_past_the_net(monkeypatch, fake_analysis)
        result = await harness.run_conversational_mode(
            text=TEXT,
            corpus_id="corpus_3469",
            max_wall_seconds=1.0,
            panel_mode=True,
            source_metadata={"opaque_id": "corpus_3469"},
        )
        # Companions (green on main too): the honest cut flags stay.
        assert result.success is False
        assert result.terminated_by_budget is True
        assert result.terminates is True
        # Born red: the state reaches the panel, labelled as a net partial.
        assert result.panel_state is not None
        snapshot = result.panel_state.get_state_snapshot(summarize=False)
        assert snapshot.get("raw_text") == TEXT
        assert result.panel_state.deanonymized is False
        assert result.panel_state_reason == "safety_net_partial_state"

    async def test_a_kill_before_any_state_existed_stays_an_honest_absence(
        self, monkeypatch
    ):
        """No state was ever built — the absence stays named, never faked."""

        async def fake_analysis(**kwargs):
            await asyncio.sleep(5.0)  # killed before constructing anything

        _hang_past_the_net(monkeypatch, fake_analysis)
        result = await harness.run_conversational_mode(
            text=TEXT,
            corpus_id="corpus_3469",
            max_wall_seconds=1.0,
            panel_mode=True,
            source_metadata={"opaque_id": "corpus_3469"},
        )
        assert result.success is False
        assert result.panel_state is None
        assert (
            harness.panel_state_absence_reason(result)
            == "runner_failed_before_state_capture"
        )


class TestTheInternalBoundPathIsUntouched:
    """The clean-exit path (the common one on a real LLM) keeps its verdict."""

    async def test_the_internal_bound_still_returns_its_own_state(self, monkeypatch):
        state = UnifiedAnalysisState(TEXT)

        async def fake_analysis(**kwargs):
            return {
                "unified_state": state,
                "restitution_report": {"acts": ["acte_i"]},
                "budget": {"wall_clock_bounded": True},
                "state_snapshot": state.get_state_snapshot(summarize=False),
                "phases": ["extraction", "formal", "synthesis"],
                "conversation_log": [{"phase": "extraction"}],
                "total_messages": 1,
            }

        monkeypatch.setattr(
            conversational_orchestrator, "run_conversational_analysis", fake_analysis
        )
        result = await harness.run_conversational_mode(
            text=TEXT,
            corpus_id="corpus_3469",
            max_wall_seconds=1.0,
            panel_mode=True,
            source_metadata={"opaque_id": "corpus_3469"},
        )
        assert result.success is True
        assert result.terminated_by_budget is False
        assert result.panel_state is state
        assert result.panel_state_reason == "completed"
        assert result.panel_state.deanonymized is False


class TestTheHeadroomFormula:
    """The real margin the witnesses bypass for speed is pinned here."""

    @pytest.mark.parametrize(
        "budget,expected",
        [(100.0, 130.0), (10.0, 40.0), (0.0, 30.0)],
    )
    def test_the_safety_net_keeps_its_headroom(self, budget, expected):
        assert harness._conversational_safety_net_timeout(budget) == pytest.approx(
            expected
        )


class TestTheRecoveredStateReachesTheJudgeArtifact:
    """Why the recovery matters: with a state, the dump writes the artifact."""

    def test_write_panel_mode_artifacts_accepts_a_recovered_state(self, tmp_path):
        state = UnifiedAnalysisState(TEXT)
        state.deanonymized = False
        result = harness.ModeResult(
            mode="conversational",
            corpus_id="corpus_3469",
            success=False,
            terminates=True,
            terminated_by_budget=True,
            duration_seconds=1.23,
            error="Safety-net timeout (>=0.05s)",
            panel_state=state,
            panel_state_reason="safety_net_partial_state",
            scope_of_work="AgentGroupChat multi-agent (safety-net witness)",
        )
        artifacts = harness.write_panel_mode_artifacts(
            result, tmp_path / "conversational"
        )
        assert artifacts is not None
        state_path = (
            tmp_path / "conversational" / "states" / "state_full_corpus_3469.json"
        )
        assert state_path.exists()
        import json

        written = json.loads(state_path.read_text(encoding="utf-8"))
        assert written.get("raw_text") == TEXT
        assert written.get("llm_usage") == {}
