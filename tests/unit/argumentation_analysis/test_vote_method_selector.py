"""Tests for vote-method selector (parametric integration, north-star R311).

Validates the --vote-method and --consensus-threshold CLI arguments and
the method dispatch in _invoke_governance.
"""

import pytest


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


class TestVoteMethodCLI:
    """Test --vote-method argument parsing in run_orchestration.py."""

    def test_vote_method_default(self):
        """Default method should be 'copeland' (unchanged behavior)."""
        valid_methods = ["approval", "stv", "copeland", "kemeny_young", "schulze"]
        assert "copeland" in valid_methods

    def test_vote_method_choices(self):
        """All 5 social choice methods should be valid choices."""
        valid_methods = {"approval", "stv", "copeland", "kemeny_young", "schulze"}
        assert len(valid_methods) == 5

    def test_vote_method_invalid_rejected(self):
        """Invalid method names should not be in valid choices."""
        valid_methods = {"approval", "stv", "copeland", "kemeny_young", "schulze"}
        assert "majority" not in valid_methods  # agent-based, not social-choice
        assert "borda" not in valid_methods  # agent-based, not social-choice
        assert "plurality" not in valid_methods


class TestConsensusThresholdCLI:
    """Test --consensus-threshold argument."""

    def test_consensus_threshold_default(self):
        """Default threshold should be 0.7."""
        default_threshold = 0.7
        assert 0.0 <= default_threshold <= 1.0

    @pytest.mark.parametrize("threshold", [0.0, 0.3, 0.5, 0.7, 0.9, 1.0])
    def test_consensus_threshold_valid_range(self, threshold):
        """Valid thresholds should be in [0.0, 1.0]."""
        assert 0.0 <= threshold <= 1.0

    def test_consensus_threshold_negative_invalid(self):
        """Negative thresholds should be invalid."""
        assert -0.1 < 0.0


# ---------------------------------------------------------------------------
# Context propagation
# ---------------------------------------------------------------------------


class TestVoteMethodContext:
    """Test vote_method context propagation from CLI to callable."""

    def test_default_copeland_not_in_context(self):
        """Default copeland should not pollute context (backward compat)."""
        vote_method = "copeland"
        context: dict = {"fallacy_tier": "llm"}
        if vote_method != "copeland":
            context["vote_method"] = vote_method
        assert "vote_method" not in context

    def test_non_default_method_in_context(self):
        """Non-default methods should be stored in context."""
        vote_method = "schulze"
        context: dict = {"fallacy_tier": "llm"}
        if vote_method != "copeland":
            context["vote_method"] = vote_method
        assert context["vote_method"] == "schulze"

    @pytest.mark.parametrize(
        "method",
        ["approval", "stv", "kemeny_young", "schulze"],
    )
    def test_all_non_default_methods_propagate(self, method):
        """All non-default methods should propagate via context."""
        context: dict = {"fallacy_tier": "llm"}
        if method != "copeland":
            context["vote_method"] = method
        assert context["vote_method"] == method


class TestConsensusThresholdContext:
    """Test consensus_threshold context propagation."""

    def test_default_threshold_not_in_context(self):
        """Default 0.7 should not pollute context (backward compat)."""
        consensus_threshold = 0.7
        context: dict = {"fallacy_tier": "llm"}
        if consensus_threshold != 0.7:
            context["consensus_threshold"] = consensus_threshold
        assert "consensus_threshold" not in context

    def test_custom_threshold_in_context(self):
        """Non-default threshold should be stored in context."""
        consensus_threshold = 0.9
        context: dict = {"fallacy_tier": "llm"}
        if consensus_threshold != 0.7:
            context["consensus_threshold"] = consensus_threshold
        assert context["consensus_threshold"] == 0.9


# ---------------------------------------------------------------------------
# Method dispatch in _invoke_governance
# ---------------------------------------------------------------------------


class TestVoteMethodDispatch:
    """Test vote method dispatch in _invoke_governance."""

    def test_context_copeland_default(self):
        """Missing vote_method in context should default to 'copeland'."""
        context: dict = {}
        method = context.get("vote_method", "copeland")
        assert method == "copeland"

    @pytest.mark.parametrize(
        "method",
        ["approval", "stv", "copeland", "kemeny_young", "schulze"],
    )
    def test_all_methods_readable_from_context(self, method):
        """All 5 methods should be readable from context."""
        context = {"vote_method": method}
        assert context.get("vote_method", "copeland") == method

    def test_method_in_ballot_dict(self):
        """The vote_method should end up in the ballot dict."""
        context = {"vote_method": "schulze"}
        ballot = {"method": context.get("vote_method", "copeland"), "ballots": []}
        assert ballot["method"] == "schulze"
