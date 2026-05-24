"""Tests for the conversational PL/FOL volet-1 gap (Track HH #697).

The conversational dialogue routes formal logic to ``belief_sets`` and never
calls the volet-1 writers, so ``propositional_analysis_results`` /
``fol_analysis_results`` stayed empty (PL/FOL = 0), losing to the zero-shot
baseline on the formal axis. These tests verify, with mocked invoke callables
(no real LLM, no JVM/Tweety), that:

  1. ``_run_formal_logic_from_state`` sweeps every identified argument and writes
     PL and FOL results back via the state's add_* methods, handling
     ``identified_arguments`` as a dict (conversational) OR a list.
  2. It is a no-op when there are no arguments, and skips a layer that is
     already populated (idempotent post-processor).
  3. A failing invoke callable is caught per-layer and never sinks the other.
  4. The PL/FOL except blocks degrade gracefully when ``TweetyBridge`` import /
     construction itself raises (``bridge = None`` guard) — the phase returns a
     Python fallback dict instead of raising into ``failed_phases``.
  5. The conversational orchestrator imports cleanly with the 5b-7 block wired in.
"""

from unittest.mock import AsyncMock, patch

import argumentation_analysis.orchestration.invoke_callables as mod


class _FakeState:
    """Minimal stand-in for UnifiedAnalysisState (real lists, real add_*)."""

    def __init__(self, identified_arguments, pl=None, fol=None):
        self.identified_arguments = identified_arguments
        self.propositional_analysis_results = pl if pl is not None else []
        self.fol_analysis_results = fol if fol is not None else []
        self.fol_signature = []
        self.source_id = "test_corpus"

    def add_propositional_analysis_result(
        self, formulas, satisfiable, model=None, arg_id=None
    ):
        self.propositional_analysis_results.append(
            {"formulas": formulas, "satisfiable": satisfiable, "model": model or {}}
        )
        return f"pl_{len(self.propositional_analysis_results)}"

    def add_fol_analysis_result(
        self, formulas, consistent, inferences, confidence=0.0, arg_id=None
    ):
        self.fol_analysis_results.append(
            {"formulas": formulas, "consistent": consistent, "confidence": confidence}
        )
        return f"fol_{len(self.fol_analysis_results)}"


def _pl_resp(formulas):
    return {"formulas": formulas, "satisfiable": True, "model": {"p1": True}}


def _fol_resp(formulas):
    return {
        "formulas": formulas,
        "consistent": True,
        "inferences": ["i"],
        "confidence": 0.8,
        "fol_signature": ["sort A"],
    }


class TestRunFormalLogicFromState:
    """The post-processor populates both volet-1 writers, dict OR list args."""

    async def test_dict_arguments_populate_both_layers(self):
        state = _FakeState(
            {"arg_1": "all men are mortal", "arg_2": "socrates is a man"}
        )
        with patch.object(
            mod,
            "_invoke_propositional_logic",
            new=AsyncMock(return_value=_pl_resp(["p1", "p2"])),
        ), patch.object(
            mod,
            "_invoke_fol_reasoning",
            new=AsyncMock(return_value=_fol_resp(["forall X: (M(X))"])),
        ):
            out = await mod._run_formal_logic_from_state(state, "source text")

        assert out == {"pl_added": 2, "fol_added": 1}
        assert len(state.propositional_analysis_results) == 1
        assert state.propositional_analysis_results[0]["formulas"] == ["p1", "p2"]
        assert len(state.fol_analysis_results) == 1
        assert state.fol_signature == ["sort A"]

    async def test_list_of_dict_arguments_supported(self):
        state = _FakeState([{"text": "a1"}, {"description": "a2"}, {"content": "a3"}])
        with patch.object(
            mod,
            "_invoke_propositional_logic",
            new=AsyncMock(return_value=_pl_resp(["p1"])),
        ), patch.object(
            mod,
            "_invoke_fol_reasoning",
            new=AsyncMock(return_value=_fol_resp(["P(a)"])),
        ):
            out = await mod._run_formal_logic_from_state(state, "src")
        assert out["pl_added"] == 1
        assert out["fol_added"] == 1

    async def test_list_of_plain_strings_supported(self):
        state = _FakeState(["bare arg one", "bare arg two"])
        with patch.object(
            mod,
            "_invoke_propositional_logic",
            new=AsyncMock(return_value=_pl_resp(["p1"])),
        ), patch.object(
            mod,
            "_invoke_fol_reasoning",
            new=AsyncMock(return_value=_fol_resp(["Q(b)"])),
        ):
            out = await mod._run_formal_logic_from_state(state, "src")
        assert out["pl_added"] == 1 and out["fol_added"] == 1

    async def test_no_args_is_noop(self):
        state = _FakeState({})
        pl = AsyncMock(return_value=_pl_resp(["p1"]))
        with patch.object(mod, "_invoke_propositional_logic", new=pl):
            out = await mod._run_formal_logic_from_state(state, "src")
        assert out == {"pl_added": 0, "fol_added": 0}
        pl.assert_not_called()

    async def test_already_populated_pl_is_skipped(self):
        state = _FakeState({"arg_1": "x"}, pl=[{"id": "pl_existing"}])
        pl = AsyncMock(return_value=_pl_resp(["p1"]))
        with patch.object(mod, "_invoke_propositional_logic", new=pl), patch.object(
            mod,
            "_invoke_fol_reasoning",
            new=AsyncMock(return_value=_fol_resp(["P(a)"])),
        ):
            out = await mod._run_formal_logic_from_state(state, "src")
        # PL already present => not regenerated; FOL still produced.
        assert out["pl_added"] == 0
        assert out["fol_added"] == 1
        pl.assert_not_called()

    async def test_pl_invoke_failure_does_not_sink_fol(self):
        state = _FakeState({"arg_1": "x"})
        with patch.object(
            mod,
            "_invoke_propositional_logic",
            new=AsyncMock(side_effect=RuntimeError("transient")),
        ), patch.object(
            mod,
            "_invoke_fol_reasoning",
            new=AsyncMock(return_value=_fol_resp(["P(a)"])),
        ):
            out = await mod._run_formal_logic_from_state(state, "src")
        assert out["pl_added"] == 0
        assert out["fol_added"] == 1

    async def test_unknown_args_type_returns_zero(self):
        state = _FakeState(None)
        out = await mod._run_formal_logic_from_state(state, "src")
        assert out == {"pl_added": 0, "fol_added": 0}


class TestExceptBlockHardening:
    """A TweetyBridge construction failure must degrade, not raise (#697 HH)."""

    async def test_pl_bridge_failure_degrades_to_python_fallback(self):
        context = {"formulas": ["p1", "p2"]}
        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            side_effect=RuntimeError("no JVM"),
        ):
            out = await mod._invoke_propositional_logic("text", context)
        # No exception bubbled; we still get a usable result dict.
        assert isinstance(out, dict)
        assert "formulas" in out
        assert out.get("fallback") == "python"

    async def test_fol_bridge_failure_degrades_to_python_fallback(self):
        context = {"formulas": ["P(a)", "Q(b)"]}
        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            side_effect=RuntimeError("no JVM"),
        ):
            out = await mod._invoke_fol_reasoning("text", context)
        assert isinstance(out, dict)
        assert "formulas" in out
        # Python fallback path sets confidence and does not raise.
        assert "confidence" in out


class TestConversationalWiring:
    """The 5b-7 post-processor edit must keep the orchestrator importable."""

    def test_orchestrator_imports_and_helper_present(self):
        import argumentation_analysis.orchestration.conversational_orchestrator as co

        assert hasattr(co, "run_conversational_analysis")
        assert hasattr(mod, "_run_formal_logic_from_state")
