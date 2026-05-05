"""Tests for PM re-prompting mechanism: iterative enrichment loops (#305).

Part A: Sequential pipeline — _should_rerun_fallacy + build_iterative_analysis_workflow
Part B: Conversational mode — _should_add_reanalysis_phase
"""

import pytest
from unittest.mock import MagicMock

# These tests do not need JVM/Tweety
pytestmark = pytest.mark.no_jvm_session


# ---------------------------------------------------------------------------
# Part A: Sequential pipeline tests
# ---------------------------------------------------------------------------


class TestShouldRerunFallacy:
    """Tests for _should_rerun_fallacy() condition function."""

    def _get_fn(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _should_rerun_fallacy,
        )

        return _should_rerun_fallacy

    def test_returns_true_when_retracted_beliefs_via_undermined_count(self):
        """Should return True when JTMS output has undermined_count > 0."""
        fn = self._get_fn()
        context = {
            "phase_jtms_output": {
                "beliefs": {},
                "undermined_count": 3,
                "valid_count": 5,
            },
            "_fallacy_rerun_count": 0,
        }
        assert fn(context) is True

    def test_returns_true_when_beliefs_dict_has_invalid_entries(self):
        """Should return True when beliefs dict contains valid=False entries."""
        fn = self._get_fn()
        context = {
            "phase_jtms_output": {
                "beliefs": {
                    "arg_1": {"valid": True, "content": "premise 1"},
                    "arg_2": {"valid": False, "content": "retracted premise"},
                },
                "undermined_count": 0,  # Even if this is 0, scan beliefs
            },
        }
        assert fn(context) is True

    def test_returns_false_when_no_retractions(self):
        """Should return False when JTMS output has no retracted beliefs."""
        fn = self._get_fn()
        context = {
            "phase_jtms_output": {
                "beliefs": {
                    "arg_1": {"valid": True},
                    "arg_2": {"valid": True},
                },
                "undermined_count": 0,
            },
        }
        assert fn(context) is False

    def test_returns_false_when_rerun_count_at_limit(self):
        """Should return False when _fallacy_rerun_count >= 2."""
        fn = self._get_fn()
        context = {
            "phase_jtms_output": {
                "beliefs": {"arg_1": {"valid": False}},
                "undermined_count": 1,
            },
            "_fallacy_rerun_count": 2,
        }
        assert fn(context) is False

    def test_returns_false_when_rerun_count_exceeds_limit(self):
        """Should return False when _fallacy_rerun_count > 2."""
        fn = self._get_fn()
        context = {
            "phase_jtms_output": {"undermined_count": 5},
            "_fallacy_rerun_count": 10,
        }
        assert fn(context) is False

    def test_returns_false_when_no_jtms_output(self):
        """Should return False when phase_jtms_output is missing."""
        fn = self._get_fn()
        assert fn({}) is False

    def test_returns_false_when_jtms_output_not_dict(self):
        """Should return False when phase_jtms_output is not a dict."""
        fn = self._get_fn()
        assert fn({"phase_jtms_output": "error string"}) is False

    def test_default_rerun_count_is_zero(self):
        """When _fallacy_rerun_count is not set, it defaults to 0 (allows rerun)."""
        fn = self._get_fn()
        context = {
            "phase_jtms_output": {"undermined_count": 1},
        }
        assert fn(context) is True


class TestIncrementFallacyRerun:
    """Tests for _increment_fallacy_rerun() helper."""

    def test_increments_from_zero(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _increment_fallacy_rerun,
        )

        ctx = {}
        _increment_fallacy_rerun(ctx)
        assert ctx["_fallacy_rerun_count"] == 1

    def test_increments_existing_count(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _increment_fallacy_rerun,
        )

        ctx = {"_fallacy_rerun_count": 1}
        _increment_fallacy_rerun(ctx)
        assert ctx["_fallacy_rerun_count"] == 2


class TestBuildIterativeWorkflow:
    """Tests for build_iterative_analysis_workflow()."""

    def test_produces_valid_workflow_definition(self):
        """The workflow should build without validation errors."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_iterative_analysis_workflow,
        )
        from argumentation_analysis.orchestration.workflow_dsl import (
            WorkflowDefinition,
        )

        wf = build_iterative_analysis_workflow()
        assert isinstance(wf, WorkflowDefinition)
        assert wf.name == "iterative_analysis"
        errors = wf.validate()
        assert errors == [], f"Workflow validation errors: {errors}"

    def test_has_fallacy_reanalysis_phase(self):
        """The workflow should contain a 'fallacy_reanalysis' conditional phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_iterative_analysis_workflow,
        )

        wf = build_iterative_analysis_workflow()
        phase = wf.get_phase("fallacy_reanalysis")
        assert phase is not None, "Missing 'fallacy_reanalysis' phase"
        assert phase.condition is not None, "fallacy_reanalysis should have a condition"
        assert phase.capability == "hierarchical_fallacy_detection"

    def test_has_standard_phases(self):
        """The workflow should contain all standard pipeline phases."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_iterative_analysis_workflow,
        )

        wf = build_iterative_analysis_workflow()
        phase_names = [p.name for p in wf.phases]
        for expected in [
            "extract",
            "hierarchical_fallacy",
            "quality",
            "counter",
            "jtms",
        ]:
            assert expected in phase_names, f"Missing phase: {expected}"

    def test_fallacy_reanalysis_depends_on_jtms(self):
        """The reanalysis phase should depend on JTMS phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_iterative_analysis_workflow,
        )

        wf = build_iterative_analysis_workflow()
        phase = wf.get_phase("fallacy_reanalysis")
        assert "jtms" in phase.depends_on

    def test_iterative_workflow_in_catalog(self):
        """The iterative workflow should be registered in the workflow catalog."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
            reset_workflow_catalog,
        )

        reset_workflow_catalog()
        catalog = get_workflow_catalog()
        assert (
            "iterative" in catalog
        ), f"'iterative' not in catalog keys: {list(catalog.keys())}"
        assert catalog["iterative"].name == "iterative_analysis"
        reset_workflow_catalog()

    def test_execution_order_respects_dependencies(self):
        """The execution order should place reanalysis after JTMS."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_iterative_analysis_workflow,
        )

        wf = build_iterative_analysis_workflow()
        order = wf.get_execution_order()
        # Flatten to find positions
        flat_order = []
        for level in order:
            flat_order.extend(level)

        jtms_pos = flat_order.index("jtms")
        reanalysis_pos = flat_order.index("fallacy_reanalysis")
        assert (
            reanalysis_pos > jtms_pos
        ), f"fallacy_reanalysis ({reanalysis_pos}) should come after jtms ({jtms_pos})"


# ---------------------------------------------------------------------------
# Part B: Conversational mode tests
# ---------------------------------------------------------------------------


class TestShouldAddReanalysisPhase:
    """Tests for _should_add_reanalysis_phase() in conversational mode."""

    def _get_fn(self):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _should_add_reanalysis_phase,
        )

        return _should_add_reanalysis_phase

    def test_returns_true_when_low_fallacy_coverage(self):
        """Should trigger re-analysis when < 50% arguments have fallacy analysis."""
        fn = self._get_fn()
        enrichment = {
            "total_arguments": 6,
            "with_fallacy_analysis": 1,
            "with_quality_score": 6,
            "with_counter_argument": 3,
            "with_formal_verification": 0,
            "with_jtms_belief": 0,
            "gaps": [],
        }
        state = MagicMock()
        state.jtms_beliefs = {}
        assert fn(enrichment, state) is True

    def test_returns_true_when_jtms_retractions_in_beliefs_dict(self):
        """Should trigger re-analysis when JTMS beliefs have been retracted."""
        fn = self._get_fn()
        enrichment = {
            "total_arguments": 4,
            "with_fallacy_analysis": 4,
            "with_quality_score": 4,
            "with_counter_argument": 2,
            "with_formal_verification": 0,
            "with_jtms_belief": 2,
            "gaps": [],
        }
        state = MagicMock()
        state.jtms_beliefs = {
            "belief_1": {"valid": True},
            "belief_2": {"valid": False},  # retracted
        }
        # No _jtms_session needed since jtms_beliefs already has retraction
        del state._jtms_session
        assert fn(enrichment, state) is True

    def test_returns_true_when_many_gaps(self):
        """Should trigger re-analysis when 3+ gaps exist."""
        fn = self._get_fn()
        enrichment = {
            "total_arguments": 5,
            "with_fallacy_analysis": 3,
            "with_quality_score": 2,
            "with_counter_argument": 1,
            "with_formal_verification": 0,
            "with_jtms_belief": 0,
            "gaps": [
                "arg_1 has no quality score",
                "arg_2 has no formal verification",
                "arg_3 has no formal verification",
            ],
        }
        state = MagicMock()
        state.jtms_beliefs = {}
        del state._jtms_session
        assert fn(enrichment, state) is True

    def test_returns_false_when_well_covered(self):
        """Should not trigger re-analysis when coverage is good."""
        fn = self._get_fn()
        enrichment = {
            "total_arguments": 4,
            "with_fallacy_analysis": 3,
            "with_quality_score": 4,
            "with_counter_argument": 4,
            "with_formal_verification": 2,
            "with_jtms_belief": 4,
            "gaps": ["arg_1 has no formal verification"],
        }
        state = MagicMock()
        state.jtms_beliefs = {"b1": {"valid": True}, "b2": {"valid": True}}
        del state._jtms_session
        assert fn(enrichment, state) is False

    def test_returns_false_when_no_arguments(self):
        """Should not trigger when there are 0 arguments."""
        fn = self._get_fn()
        enrichment = {
            "total_arguments": 0,
            "with_fallacy_analysis": 0,
            "gaps": [],
        }
        state = MagicMock()
        state.jtms_beliefs = {}
        assert fn(enrichment, state) is False

    def test_returns_true_with_jtms_session_retractions(self):
        """Should detect retractions via state._jtms_session.extended_beliefs."""
        fn = self._get_fn()
        enrichment = {
            "total_arguments": 4,
            "with_fallacy_analysis": 4,
            "with_quality_score": 4,
            "with_counter_argument": 2,
            "with_formal_verification": 0,
            "with_jtms_belief": 2,
            "gaps": [],
        }
        state = MagicMock()
        state.jtms_beliefs = {}  # Empty dict — no retractions here

        # But _jtms_session has retracted beliefs
        mock_ext_belief = MagicMock()
        mock_ext_belief.valid = False
        state._jtms_session.extended_beliefs = {"retracted_arg": mock_ext_belief}

        assert fn(enrichment, state) is True
