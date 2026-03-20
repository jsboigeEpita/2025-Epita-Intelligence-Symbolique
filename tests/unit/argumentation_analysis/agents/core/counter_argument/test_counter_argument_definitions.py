# tests/unit/argumentation_analysis/agents/core/counter_argument/test_counter_argument_definitions.py
"""Tests for counter-argument data structures — enums, dataclasses."""

import pytest
from argumentation_analysis.agents.core.counter_argument.definitions import (
    CounterArgumentType,
    ArgumentStrength,
    RhetoricalStrategy,
    Argument,
    Vulnerability,
    CounterArgument,
    EvaluationResult,
    ValidationResult,
)

# ── Enums ──


class TestCounterArgumentType:
    def test_has_five_types(self):
        assert len(CounterArgumentType) == 5

    def test_values(self):
        expected = {
            "direct_refutation",
            "counter_example",
            "alternative_explanation",
            "premise_challenge",
            "reductio_ad_absurdum",
        }
        assert {t.value for t in CounterArgumentType} == expected


class TestArgumentStrength:
    def test_has_four_levels(self):
        assert len(ArgumentStrength) == 4

    def test_order(self):
        levels = [s.value for s in ArgumentStrength]
        assert "weak" in levels
        assert "decisive" in levels


class TestRhetoricalStrategy:
    def test_has_five_strategies(self):
        assert len(RhetoricalStrategy) == 5

    def test_values(self):
        expected = {
            "socratic_questioning",
            "reductio_ad_absurdum",
            "analogical_counter",
            "authority_appeal",
            "statistical_evidence",
        }
        assert {s.value for s in RhetoricalStrategy} == expected


# ── Argument ──


class TestArgument:
    def test_init(self):
        arg = Argument(
            content="Climate change is real",
            premises=["CO2 levels rising", "Temperatures increasing"],
            conclusion="We must act now",
            argument_type="deductive",
            confidence=0.9,
        )
        assert arg.content == "Climate change is real"
        assert len(arg.premises) == 2
        assert arg.conclusion == "We must act now"
        assert arg.argument_type == "deductive"
        assert arg.confidence == 0.9

    def test_minimal(self):
        arg = Argument(
            content="X",
            premises=[],
            conclusion="Y",
            argument_type="inductive",
            confidence=0.5,
        )
        assert arg.premises == []


# ── Vulnerability ──


class TestVulnerability:
    def test_init(self):
        vuln = Vulnerability(
            type="logical_gap",
            target="premise 1",
            description="Unsupported assumption",
            score=0.8,
            suggested_counter_type=CounterArgumentType.PREMISE_CHALLENGE,
        )
        assert vuln.type == "logical_gap"
        assert vuln.target == "premise 1"
        assert vuln.score == 0.8
        assert vuln.suggested_counter_type == CounterArgumentType.PREMISE_CHALLENGE


# ── CounterArgument ──


class TestCounterArgument:
    @pytest.fixture
    def original(self):
        return Argument(
            content="Taxes should increase",
            premises=["Revenue needed"],
            conclusion="Raise taxes",
            argument_type="deductive",
            confidence=0.7,
        )

    def test_init(self, original):
        ca = CounterArgument(
            original_argument=original,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Tax increases harm the economy",
            target_component="conclusion",
            strength=ArgumentStrength.STRONG,
            confidence=0.85,
        )
        assert ca.original_argument is original
        assert ca.counter_type == CounterArgumentType.DIRECT_REFUTATION
        assert ca.strength == ArgumentStrength.STRONG
        assert ca.confidence == 0.85
        assert ca.supporting_evidence == []
        assert ca.rhetorical_strategy == ""

    def test_with_evidence(self, original):
        ca = CounterArgument(
            original_argument=original,
            counter_type=CounterArgumentType.COUNTER_EXAMPLE,
            counter_content="Sweden lowered taxes and grew",
            target_component="premise",
            strength=ArgumentStrength.MODERATE,
            confidence=0.6,
            supporting_evidence=["GDP data", "Tax records"],
            rhetorical_strategy="statistical",
        )
        assert len(ca.supporting_evidence) == 2
        assert ca.rhetorical_strategy == "statistical"


# ── EvaluationResult ──


class TestEvaluationResult:
    def test_init(self):
        ev = EvaluationResult(
            relevance=0.9,
            logical_strength=0.8,
            persuasiveness=0.7,
            originality=0.6,
            clarity=0.85,
            overall_score=0.77,
        )
        assert ev.relevance == 0.9
        assert ev.overall_score == 0.77
        assert ev.recommendations == []

    def test_with_recommendations(self):
        ev = EvaluationResult(
            relevance=0.5,
            logical_strength=0.3,
            persuasiveness=0.4,
            originality=0.2,
            clarity=0.6,
            overall_score=0.4,
            recommendations=["Add evidence", "Improve logic"],
        )
        assert len(ev.recommendations) == 2


# ── ValidationResult ──


class TestValidationResult:
    def test_valid_attack(self):
        vr = ValidationResult(
            is_valid_attack=True,
            original_survives=False,
            counter_succeeds=True,
            logical_consistency=True,
        )
        assert vr.is_valid_attack is True
        assert vr.original_survives is False
        assert vr.formal_representation is None

    def test_with_formal_rep(self):
        vr = ValidationResult(
            is_valid_attack=True,
            original_survives=True,
            counter_succeeds=False,
            logical_consistency=True,
            formal_representation="P -> Q, ~Q |- ~P",
        )
        assert vr.formal_representation == "P -> Q, ~Q |- ~P"

    def test_invalid_attack(self):
        vr = ValidationResult(
            is_valid_attack=False,
            original_survives=True,
            counter_succeeds=False,
            logical_consistency=False,
        )
        assert vr.logical_consistency is False
