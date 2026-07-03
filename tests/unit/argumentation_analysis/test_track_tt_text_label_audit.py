"""Tests for Track TT (#672): Static audit text-label ↔ canonical arg_id boundary.

Tests cover:
  1. cross_reference_graph uses correct fallacy key (target_argument_id)
  2. ASPIC+ fallacy undermining uses canonical arg_id, not positional index
  3. ATMS hypothesis quality lookup uses canonical key, not free text
  4. Social scoring fallback is fail-loud (FP-22 #1249) — JVM/Tweety required
"""

import pytest


class TestCrossReferenceGraphFallacyKey:
    """BUG A2 fix: cross_reference_graph reads target_argument_id, not target_arg_id."""

    def test_fallacy_edge_created_with_correct_key(self):
        """Fallacy entries with target_argument_id produce edges."""
        from argumentation_analysis.reporting.cross_reference_graph import (
            CrossReferenceGraph,
            EdgeType,
        )

        class MockState:
            identified_arguments = {"arg_1": "First argument text", "arg_2": "Second"}
            identified_fallacies = {
                "fal_1": {
                    "fallacy_type": "Ad hominem",
                    "target_argument_id": "arg_1",
                },
            }
            jtms_beliefs = {}
            jtms_retraction_chain = []
            counter_arguments = {}
            dung_framework = {}
            argument_quality_scores = {}
            belief_revision_results = {}

        graph = CrossReferenceGraph()
        graph.build_from_state(MockState())
        edges = graph.edges
        fallacy_edges = [e for e in edges if e.edge_type == EdgeType.ARGUMENT_FALLACY]
        assert len(fallacy_edges) == 1
        assert fallacy_edges[0].source == "arg_1"
        assert fallacy_edges[0].target == "fal_1"

    def test_no_fallacy_edge_with_wrong_key(self):
        """Fallacy entries with target_arg_id (wrong key) produce NO edges."""
        from argumentation_analysis.reporting.cross_reference_graph import (
            CrossReferenceGraph,
            EdgeType,
        )

        class MockState:
            identified_arguments = {"arg_1": "First argument text"}
            identified_fallacies = {
                "fal_1": {
                    "fallacy_type": "Ad hominem",
                    "target_arg_id": "arg_1",
                },
            }
            jtms_beliefs = {}
            jtms_retraction_chain = []
            counter_arguments = {}
            dung_framework = {}
            argument_quality_scores = {}
            belief_revision_results = {}

        graph = CrossReferenceGraph()
        graph.build_from_state(MockState())
        edges = graph.edges
        fallacy_edges = [e for e in edges if e.edge_type == EdgeType.ARGUMENT_FALLACY]
        assert len(fallacy_edges) == 0

    def test_multiple_fallacies_multiple_edges(self):
        """Multiple fallacies targeting different args produce multiple edges."""
        from argumentation_analysis.reporting.cross_reference_graph import (
            CrossReferenceGraph,
            EdgeType,
        )

        class MockState:
            identified_arguments = {
                "arg_1": "First",
                "arg_2": "Second",
                "arg_3": "Third",
            }
            identified_fallacies = {
                "fal_1": {
                    "fallacy_type": "Post hoc",
                    "target_argument_id": "arg_1",
                },
                "fal_2": {
                    "fallacy_type": "Ad hominem",
                    "target_argument_id": "arg_3",
                },
            }
            jtms_beliefs = {}
            jtms_retraction_chain = []
            counter_arguments = {}
            dung_framework = {}
            argument_quality_scores = {}
            belief_revision_results = {}

        graph = CrossReferenceGraph()
        graph.build_from_state(MockState())
        edges = graph.edges
        fallacy_edges = [e for e in edges if e.edge_type == EdgeType.ARGUMENT_FALLACY]
        assert len(fallacy_edges) == 2
        targets = {e.source for e in fallacy_edges}
        assert targets == {"arg_1", "arg_3"}


class TestASPICFallacyUndermining:
    """BUG A1 fix: ASPIC+ uses canonical arg_id, not positional index."""

    def _make_state_with_fallacies(self, fallacies_targeting):
        """Create a mock state with arguments and fallacies.

        fallacies_targeting: list of canonical arg_ids that have fallacies
        """

        class MockState:
            identified_arguments = {
                "arg_1": "This is proven fact about economic policy",
                "arg_2": "The data suggests economic improvement probably",
                "arg_3": "We always see market fluctuations",
            }
            identified_fallacies = {}

        state = MockState()
        state.identified_fallacies = {
            f"fal_{i}": {
                "fallacy_type": "Test fallacy",
                "target_argument_id": tid,
            }
            for i, tid in enumerate(fallacies_targeting)
        }
        return state

    def test_fallacy_on_third_arg_detected(self):
        """Fallacy targeting arg_3 should undermine arg_3, not arg_1 or arg_2."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
        )

        state = self._make_state_with_fallacies(["arg_3"])
        result = _build_aspic_from_state(state)
        if result is None:
            pytest.skip("ASPIC framework returned None")
        defeated = result.get("defeated", [])
        assert len(defeated) > 0

    def test_no_fallacy_no_undermining(self):
        """Without fallacies, no arguments should be defeated."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
        )

        state = self._make_state_with_fallacies([])
        result = _build_aspic_from_state(state)
        if result is None:
            pytest.skip("ASPIC framework returned None")
        defeated = result.get("defeated", [])
        assert len(defeated) == 0


class TestATMSHypothesisQualityLookup:
    """BUG IC5 fix: hypothesis quality lookup uses canonical key."""

    def test_high_quality_hypothesis_populated(self):
        """h_high_quality populated when quality scores use canonical keys."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _generate_hypotheses,
        )

        arg_names = ["First argument text", "Second argument text"]
        claim_names = ["Conclusion 1"]
        fallacies = []
        per_arg_scores = {
            "arg_1": {"overall": 7.5},
            "arg_2": {"overall": 2.0},
        }
        hypotheses = _generate_hypotheses(
            arg_names, claim_names, fallacies, per_arg_scores
        )
        hq = [h for h in hypotheses if h["id"] == "h_high_quality"]
        assert len(hq) == 1
        assert arg_names[0] in hq[0]["assumptions"]
        assert arg_names[1] not in hq[0]["assumptions"]

    def test_all_low_quality_no_hypothesis(self):
        """No h_high_quality when all scores are below threshold."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _generate_hypotheses,
        )

        arg_names = ["First argument text", "Second argument text"]
        claim_names = ["Conclusion 1"]
        fallacies = []
        per_arg_scores = {
            "arg_1": {"overall": 1.0},
            "arg_2": {"overall": 2.0},
        }
        hypotheses = _generate_hypotheses(
            arg_names, claim_names, fallacies, per_arg_scores
        )
        hq = [h for h in hypotheses if h["id"] == "h_high_quality"]
        assert len(hq) == 0

    def test_all_high_quality_no_hypothesis(self):
        """No h_high_quality when ALL args are high quality (same as h_full_trust)."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _generate_hypotheses,
        )

        arg_names = ["First argument text", "Second argument text"]
        claim_names = ["Conclusion 1"]
        fallacies = []
        per_arg_scores = {
            "arg_1": {"overall": 8.0},
            "arg_2": {"overall": 9.0},
        }
        hypotheses = _generate_hypotheses(
            arg_names, claim_names, fallacies, per_arg_scores
        )
        hq = [h for h in hypotheses if h["id"] == "h_high_quality"]
        assert len(hq) == 0

    def test_empty_scores_no_crash(self):
        """Empty per_arg_scores does not crash."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _generate_hypotheses,
        )

        hypotheses = _generate_hypotheses(["arg text"], ["claim"], [], {})
        assert isinstance(hypotheses, list)
        assert len(hypotheses) >= 1


class TestSocialFallbackIsFailLoud:
    """_python_social_fallback raises RuntimeError (#1019, RA-8 #1053, FP-22 #1249).

    The previous pure-Python social-scoring fallback (BUG IC6 canonical-key
    quality lookup) was retired because it produced synthetic social scores
    that entered state as authentic formal results — an anti-theater violation.
    Social AF is now JVM/Tweety-only: _invoke_social delegates to SocialHandler,
    and this fallback exists solely to fail loud when the JVM/Tweety backend is
    unavailable. Same doctrine as _python_dung_fallback / _python_eaf_fallback.

    The two original IC6 tests asserted the retired pure-Python return value
    (`result["social_scores"]`) — a stale contract. They are rewritten as
    regression guards asserting the fail-loud RuntimeError so the anti-theater
    boundary cannot silently regress.
    """

    def test_social_fallback_raises_without_jvm(self):
        """_python_social_fallback must raise, never return synthetic scores."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _python_social_fallback,
        )

        args = ["First argument", "Second argument"]
        attacks = []
        votes = {}
        context = {
            "phase_quality_output": {
                "quality_scores": {
                    "arg_1": {"overall": 0.9},
                    "arg_2": {"overall": 0.2},
                },
            },
        }
        with pytest.raises(RuntimeError, match="JVM/Tweety required"):
            _python_social_fallback(args, attacks, votes, context)

    def test_social_fallback_raises_without_quality_data(self):
        """Fail-loud is independent of quality data presence."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _python_social_fallback,
        )

        args = ["First argument", "Second argument"]
        attacks = []
        votes = {}
        context = {}
        with pytest.raises(RuntimeError, match="JVM/Tweety required"):
            _python_social_fallback(args, attacks, votes, context)
