"""KB completeness test — validates Sprint 4 wiring produces complete KB (#567).

Tests that after running all conversational post-phase hooks, every identified
argument has corresponding entries across PL, FOL, modal, JTMS, Dung, and ASPIC.

This is a wiring test (no LLM/JVM needed) — it verifies the hooks work together.
"""

import pytest

from argumentation_analysis.core.shared_state import (
    UnifiedAnalysisState,
)


class TestKBCompleteness:
    """End-to-end wiring test for Sprint 4 post-phase hooks."""

    def _setup_realistic_state(self):
        """Create state with realistic arguments containing various markers."""
        state = UnifiedAnalysisState(
            "The government must implement stricter regulations on industrial "
            "pollution. Scientists believe that climate change is accelerating. "
            "Economic growth is essential for development. It is possible that "
            "renewable energy will replace fossil fuels. The data proves that "
            "emissions are rising."
        )

        # Add arguments with diverse linguistic cues
        arg_ids = []
        args = [
            "The government must implement stricter regulations",  # deontic
            "Scientists believe that climate change is accelerating",  # epistemic
            "Economic growth is essential for development",  # factual (strict)
            "It is possible that renewable energy will replace fossil fuels",  # alethic
            "The data proves that emissions are rising",  # factual (strict)
        ]
        for desc in args:
            arg_ids.append(state.add_argument(desc))

        # Add JTMS beliefs for all arguments
        for aid in arg_ids:
            state.add_jtms_belief(name=aid, valid=True, justifications=[])

        # Add fallacies targeting arg 0 and arg 2
        state.add_fallacy("appeal_to_authority", "Regulation demand", target_arg_id=arg_ids[0])
        state.add_fallacy("hasty_generalization", "Growth claim", target_arg_id=arg_ids[2])

        # Add counter-argument
        state.counter_arguments.append({
            "strategy": "REBUT",
            "original_argument": args[2],
            "counter_argument": args[4],
        })

        # Add PL analysis result
        state.add_propositional_analysis_result(
            formulas=["p => q", "r && s"],
            satisfiable=True,
            model={},
        )

        # Add FOL analysis result
        state.add_fol_analysis_result(
            formulas=["forall X: Person => Mortal(X)"],
            consistent=True,
            inferences=["Mortal(socrates)"],
        )

        return state, arg_ids

    def test_jtms_beliefs_for_all_arguments(self):
        """Every argument has a JTMS belief."""
        state, arg_ids = self._setup_realistic_state()
        for aid in arg_ids:
            belief_names = [b["name"] for b in state.jtms_beliefs.values()]
            assert aid in belief_names, f"Missing JTMS belief for {aid}"

    def test_dung_framework_built(self):
        """Dung framework is built from arguments + attacks."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        state, _ = self._setup_realistic_state()
        result = _build_dung_framework_from_state(state)
        assert result is not None
        assert result["arguments"] >= 2
        assert result["attacks"] >= 1
        assert len(state.dung_frameworks) >= 1

    def test_modal_analysis_for_modal_arguments(self):
        """Modal analysis detects epistemic/deontic/alethic arguments."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _detect_and_run_modal_analysis,
        )

        state, _ = self._setup_realistic_state()
        result = _detect_and_run_modal_analysis(state)
        assert result is not None
        assert result["modal_results"] >= 3  # deontic + epistemic + alethic
        assert "epistemic" in result["modalities_found"]
        assert "deontic" in result["modalities_found"]

    def test_aspic_framework_built(self):
        """ASPIC framework classifies arguments into strict/defeasible."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
        )

        state, _ = self._setup_realistic_state()
        result = _build_aspic_from_state(state)
        assert result is not None
        assert result["strict_rules"] + result["defeasible_rules"] == 5
        assert len(state.aspic_results) >= 1

    def test_belief_revision_on_contradictions(self):
        """Beliefs targeted by fallacies are revised."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_belief_revision_from_state,
        )

        state, _ = self._setup_realistic_state()
        result = _run_belief_revision_from_state(state)
        assert result is not None
        assert len(result["removed"]) >= 1
        assert len(state.belief_revision_results) >= 1

    def test_all_hooks_together(self):
        """Running all hooks produces complete KB for all arguments."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
            _build_dung_framework_from_state,
            _detect_and_run_modal_analysis,
            _run_belief_revision_from_state,
        )

        state, arg_ids = self._setup_realistic_state()

        # Run all post-phase hooks
        dung = _build_dung_framework_from_state(state)
        modal = _detect_and_run_modal_analysis(state)
        aspic = _build_aspic_from_state(state)
        revision = _run_belief_revision_from_state(state)

        # Verify completeness
        # 1. JTMS: all arguments have beliefs
        assert len(state.jtms_beliefs) >= len(arg_ids)

        # 2. Dung: framework built with attacks
        assert dung is not None
        assert dung["attacks"] >= 1

        # 3. Modal: at least 3 arguments with modal markers
        assert modal is not None
        assert modal["modal_results"] >= 3

        # 4. ASPIC: all arguments classified
        assert aspic is not None
        assert aspic["strict_rules"] + aspic["defeasible_rules"] == len(arg_ids)

        # 5. Belief revision: fallacies triggered contraction
        assert revision is not None

        # 6. PL analysis present
        assert len(state.propositional_analysis_results) >= 1

        # 7. FOL analysis present
        assert len(state.fol_analysis_results) >= 1

        # Summary check via state snapshot
        snapshot = state.get_state_snapshot(summarize=True)
        assert snapshot["jtms_belief_count"] >= len(arg_ids)
        assert snapshot["dung_framework_count"] >= 1
        assert snapshot["modal_analysis_count"] >= 3
        assert snapshot["aspic_result_count"] >= 1
        assert snapshot["belief_revision_result_count"] >= 1

    def test_state_snapshot_counts_all_dimensions(self):
        """State snapshot includes counts for all Sprint 4 dimensions."""
        state, _ = self._setup_realistic_state()

        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
            _build_dung_framework_from_state,
            _detect_and_run_modal_analysis,
            _run_belief_revision_from_state,
        )

        _build_dung_framework_from_state(state)
        _detect_and_run_modal_analysis(state)
        _build_aspic_from_state(state)
        _run_belief_revision_from_state(state)

        snapshot = state.get_state_snapshot(summarize=True)

        # All Sprint 4 dimensions present and non-zero
        dimensions = {
            "jtms_belief_count": snapshot.get("jtms_belief_count", 0),
            "dung_framework_count": snapshot.get("dung_framework_count", 0),
            "modal_analysis_count": snapshot.get("modal_analysis_count", 0),
            "aspic_result_count": snapshot.get("aspic_result_count", 0),
            "belief_revision_result_count": snapshot.get("belief_revision_result_count", 0),
        }
        for name, count in dimensions.items():
            assert count > 0, f"{name} is 0 — Sprint 4 wiring incomplete"
