"""
Tests for agents/watson_jtms/models.py and agents/watson_jtms/validation.py.

Covers ValidationResult, ConflictResolution dataclasses,
and FormalValidator with mocked JTMS session.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from argumentation_analysis.agents.watson_jtms.models import (
    ValidationResult,
    ConflictResolution,
)
from argumentation_analysis.agents.watson_jtms.validation import FormalValidator


# =============================================================================
# ValidationResult tests
# =============================================================================


class TestValidationResult:
    """Tests for the ValidationResult dataclass."""

    def test_basic_construction(self):
        vr = ValidationResult(
            belief_name="belief_a",
            is_valid=True,
            confidence_score=0.95,
            validation_method="direct",
        )
        assert vr.belief_name == "belief_a"
        assert vr.is_valid is True
        assert vr.confidence_score == 0.95
        assert vr.validation_method == "direct"

    def test_defaults(self):
        vr = ValidationResult(
            belief_name="b",
            is_valid=False,
            confidence_score=0.0,
            validation_method="m",
        )
        assert vr.issues_found == []
        assert vr.suggestions == []
        assert vr.formal_proof is None
        assert isinstance(vr.timestamp, datetime)

    def test_with_issues_and_suggestions(self):
        vr = ValidationResult(
            belief_name="b",
            is_valid=False,
            confidence_score=0.3,
            validation_method="formal",
            issues_found=["Missing premise", "Circular"],
            suggestions=["Add evidence"],
            formal_proof="Proof text",
        )
        assert len(vr.issues_found) == 2
        assert "Missing premise" in vr.issues_found
        assert vr.formal_proof == "Proof text"


# =============================================================================
# ConflictResolution tests
# =============================================================================


class TestConflictResolution:
    """Tests for the ConflictResolution dataclass."""

    def test_basic_construction(self):
        cr = ConflictResolution(
            conflict_id="c1",
            conflicting_beliefs=["a", "not_a"],
            resolution_strategy="priority",
            chosen_belief="a",
            reasoning="a has higher confidence",
            confidence=0.8,
        )
        assert cr.conflict_id == "c1"
        assert cr.conflicting_beliefs == ["a", "not_a"]
        assert cr.chosen_belief == "a"
        assert cr.confidence == 0.8
        assert isinstance(cr.timestamp, datetime)

    def test_no_chosen_belief(self):
        cr = ConflictResolution(
            conflict_id="c2",
            conflicting_beliefs=["x", "y"],
            resolution_strategy="undecided",
            chosen_belief=None,
            reasoning="Insufficient evidence",
            confidence=0.0,
        )
        assert cr.chosen_belief is None


# =============================================================================
# FormalValidator tests
# =============================================================================


class TestFormalValidator:
    """Tests for the FormalValidator class."""

    def _make_validator(self, beliefs=None):
        jtms_session = MagicMock()
        jtms_session.extended_beliefs = beliefs or {}
        jtms_session.jtms = MagicMock()
        jtms_session.jtms.beliefs = {}
        watson_tools = MagicMock()
        return FormalValidator(jtms_session, watson_tools)

    async def test_unknown_belief_returns_error(self):
        validator = self._make_validator()
        result = await validator.prove_belief("unknown")
        assert result["provable"] is False
        assert result["error"] == "Croyance inconnue"

    async def test_prove_belief_with_valid_justification(self):
        """Belief with valid justification is provable."""
        # Setup belief with justification
        justification = MagicMock()
        justification.in_list = ["premise_a"]
        justification.out_list = []

        belief = MagicMock()
        belief.justifications = [justification]

        jtms_beliefs = {
            "premise_a": MagicMock(valid=True),
        }

        validator = self._make_validator(beliefs={"target": belief})
        validator.jtms_session.jtms.beliefs = jtms_beliefs

        result = await validator.prove_belief("target")
        assert result["provable"] is True
        assert result["proof_method"] == "direct_justification"
        assert result["confidence"] > 0

    async def test_prove_belief_cached(self):
        """Second call returns cached result."""
        validator = self._make_validator()
        # Pre-populate cache
        validator.validation_cache["test_belief"] = {"provable": True, "cached": True}
        result = await validator.prove_belief("test_belief")
        assert result["cached"] is True

    async def test_prove_belief_no_justifications(self):
        """Belief without valid justifications falls through to deductive proof."""
        belief = MagicMock()
        belief.justifications = []  # No justifications

        validator = self._make_validator(beliefs={"target": belief})
        result = await validator.prove_belief("target")
        assert result["provable"] is False
        assert "consistency_check" in result

    async def test_deductive_proof_stub(self):
        validator = self._make_validator()
        result = await validator._attempt_deductive_proof("x")
        assert result["provable"] is False
        assert result["proof_method"] == "deductive_attempt"

    async def test_consistency_check_stub(self):
        validator = self._make_validator()
        result = await validator._check_belief_consistency("x")
        assert result["consistent"] is True
        assert result["conflicts"] == []

    def test_construct_formal_proof(self):
        validator = self._make_validator()
        steps = [
            {"valid": True, "logical_structure": "modus_ponens",
             "premises_valid": True, "negatives_invalid": True, "confidence": 0.8},
            {"valid": False, "logical_structure": "unknown"},
        ]
        proof = validator._construct_formal_proof("belief_x", steps)
        assert "belief_x" in proof
        assert "modus_ponens" in proof
        assert "QED" in proof

    def test_construct_formal_proof_empty_steps(self):
        validator = self._make_validator()
        proof = validator._construct_formal_proof("b", [])
        assert "QED" in proof

    def test_get_validation_summary_empty(self):
        validator = self._make_validator()
        summary = validator.get_validation_summary()
        assert summary["total_validations"] == 0

    def test_get_validation_summary_with_cache(self):
        validator = self._make_validator()
        validator.validation_cache["a"] = {"provable": True}
        validator.validation_cache["b"] = {"provable": False}
        summary = validator.get_validation_summary()
        assert summary["total_validations"] == 2

    async def test_validate_justification_modus_ponens(self):
        """Justification with only in_list has modus_ponens structure."""
        justification = MagicMock()
        justification.in_list = ["p1"]
        justification.out_list = []

        validator = self._make_validator()
        validator.jtms_session.jtms.beliefs = {"p1": MagicMock(valid=True)}

        result = await validator._validate_justification_formally(justification, 0)
        assert result["logical_structure"] == "modus_ponens"
        assert result["valid"] is True

    async def test_validate_justification_modus_tollens(self):
        """Justification with out_list has modus_tollens structure."""
        justification = MagicMock()
        justification.in_list = []
        justification.out_list = ["neg1"]

        validator = self._make_validator()
        validator.jtms_session.jtms.beliefs = {"neg1": MagicMock(valid=False)}

        result = await validator._validate_justification_formally(justification, 0)
        assert result["logical_structure"] == "modus_tollens"

    async def test_validate_justification_axiom(self):
        """Justification with no in/out list is an axiom."""
        justification = MagicMock()
        justification.in_list = []
        justification.out_list = []

        validator = self._make_validator()
        result = await validator._validate_justification_formally(justification, 0)
        assert result["logical_structure"] == "axiom"
