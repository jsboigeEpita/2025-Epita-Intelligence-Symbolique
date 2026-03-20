# tests/unit/argumentation_analysis/agents/core/debate/test_debate_definitions.py
"""Tests for debate data structures — enums, dataclasses, and personalities."""

import pytest
from collections import defaultdict
from datetime import datetime

from argumentation_analysis.agents.core.debate.debate_definitions import (
    ArgumentType,
    DebatePhase,
    ArgumentMetrics,
    EnhancedArgument,
    DebateState,
    AGENT_PERSONALITIES,
)

# ── Enums ──


class TestArgumentType:
    def test_all_values(self):
        assert ArgumentType.OPENING_STATEMENT.value == "opening_statement"
        assert ArgumentType.CLAIM.value == "claim"
        assert ArgumentType.EVIDENCE.value == "evidence"
        assert ArgumentType.REBUTTAL.value == "rebuttal"
        assert ArgumentType.COUNTER_REBUTTAL.value == "counter_rebuttal"
        assert ArgumentType.CLOSING_STATEMENT.value == "closing_statement"

    def test_member_count(self):
        assert len(ArgumentType) == 6


class TestDebatePhase:
    def test_all_values(self):
        assert DebatePhase.OPENING.value == "opening"
        assert DebatePhase.MAIN_ARGUMENTS.value == "main_arguments"
        assert DebatePhase.REBUTTALS.value == "rebuttals"
        assert DebatePhase.CLOSING.value == "closing"
        assert DebatePhase.CONCLUDED.value == "concluded"

    def test_member_count(self):
        assert len(DebatePhase) == 5


# ── ArgumentMetrics ──


class TestArgumentMetrics:
    def test_defaults_all_zero(self):
        m = ArgumentMetrics()
        assert m.logical_coherence == 0.0
        assert m.evidence_quality == 0.0
        assert m.relevance_score == 0.0
        assert m.emotional_appeal == 0.0
        assert m.readability_score == 0.0
        assert m.fact_check_score == 0.0
        assert m.novelty_score == 0.0
        assert m.persuasiveness == 0.0

    def test_custom_values(self):
        m = ArgumentMetrics(
            logical_coherence=0.9,
            evidence_quality=0.8,
            relevance_score=0.7,
        )
        assert m.logical_coherence == 0.9
        assert m.evidence_quality == 0.8
        assert m.relevance_score == 0.7
        assert m.emotional_appeal == 0.0  # still default

    def test_field_count(self):
        m = ArgumentMetrics()
        fields = [f for f in vars(m)]
        assert len(fields) == 8


# ── EnhancedArgument ──


class TestEnhancedArgument:
    @pytest.fixture
    def basic_arg(self):
        return EnhancedArgument(
            agent_name="scholar",
            position="for",
            content="This is a test argument with several words",
            argument_type=ArgumentType.CLAIM,
            timestamp="2026-01-01T12:00:00",
            phase=DebatePhase.MAIN_ARGUMENTS,
        )

    def test_word_count_computed(self, basic_arg):
        assert basic_arg.word_count == 8

    def test_id_generated(self, basic_arg):
        assert basic_arg.id.startswith("scholar_2026-01-01T12:00:00_")

    def test_empty_defaults(self, basic_arg):
        assert basic_arg.references == []
        assert basic_arg.citations == []
        assert isinstance(basic_arg.metrics, ArgumentMetrics)
        assert basic_arg.logical_structure == {}
        assert basic_arg.response_to is None

    def test_custom_metrics(self):
        metrics = ArgumentMetrics(logical_coherence=0.9, evidence_quality=0.8)
        arg = EnhancedArgument(
            agent_name="philosopher",
            position="against",
            content="Counter-point",
            argument_type=ArgumentType.REBUTTAL,
            timestamp="2026-01-01T13:00:00",
            phase=DebatePhase.REBUTTALS,
            metrics=metrics,
        )
        assert arg.metrics.logical_coherence == 0.9

    def test_references_and_citations(self):
        arg = EnhancedArgument(
            agent_name="scholar",
            position="for",
            content="Evidence shows",
            argument_type=ArgumentType.EVIDENCE,
            timestamp="t1",
            phase=DebatePhase.MAIN_ARGUMENTS,
            references=["ref1", "ref2"],
            citations=[{"source": "paper1", "page": "42"}],
        )
        assert len(arg.references) == 2
        assert arg.citations[0]["source"] == "paper1"

    def test_response_to(self):
        arg = EnhancedArgument(
            agent_name="devil",
            position="against",
            content="I disagree",
            argument_type=ArgumentType.REBUTTAL,
            timestamp="t2",
            phase=DebatePhase.REBUTTALS,
            response_to="scholar_t1_1234",
        )
        assert arg.response_to == "scholar_t1_1234"

    def test_word_count_empty_content(self):
        arg = EnhancedArgument(
            agent_name="a",
            position="for",
            content="",
            argument_type=ArgumentType.CLAIM,
            timestamp="t",
            phase=DebatePhase.OPENING,
        )
        # "".split() = [], len = 0, but word_count = 1 because split of empty
        # Actually: "".split() => [], len([]) = 0
        assert arg.word_count == 0

    def test_word_count_single_word(self):
        arg = EnhancedArgument(
            agent_name="a",
            position="for",
            content="hello",
            argument_type=ArgumentType.CLAIM,
            timestamp="t",
            phase=DebatePhase.OPENING,
        )
        assert arg.word_count == 1

    def test_all_argument_types(self):
        for at in ArgumentType:
            arg = EnhancedArgument(
                agent_name="test",
                position="for",
                content="content",
                argument_type=at,
                timestamp="t",
                phase=DebatePhase.OPENING,
            )
            assert arg.argument_type == at

    def test_all_phases(self):
        for phase in DebatePhase:
            arg = EnhancedArgument(
                agent_name="test",
                position="against",
                content="content",
                argument_type=ArgumentType.CLAIM,
                timestamp="t",
                phase=phase,
            )
            assert arg.phase == phase


# ── DebateState ──


class TestDebateState:
    @pytest.fixture
    def basic_state(self):
        return DebateState(
            topic="Should AI be regulated?",
            agents=["scholar", "pragmatist"],
            arguments=[],
            current_turn=0,
            max_turns=10,
            phase=DebatePhase.OPENING,
        )

    def test_basic_init(self, basic_state):
        assert basic_state.topic == "Should AI be regulated?"
        assert len(basic_state.agents) == 2
        assert basic_state.current_turn == 0
        assert basic_state.max_turns == 10
        assert basic_state.phase == DebatePhase.OPENING

    def test_defaults(self, basic_state):
        assert basic_state.winner is None
        assert isinstance(basic_state.audience_votes, defaultdict)
        assert basic_state.performance_metrics == {}
        assert basic_state.argument_network == {}
        assert basic_state.debate_summary == ""

    def test_start_time_auto_generated(self, basic_state):
        assert basic_state.start_time is not None
        assert len(basic_state.start_time) > 10  # ISO format

    def test_audience_votes_defaultdict(self, basic_state):
        basic_state.audience_votes["scholar"] += 3
        basic_state.audience_votes["pragmatist"] += 1
        assert basic_state.audience_votes["scholar"] == 3
        assert basic_state.audience_votes["unknown"] == 0  # defaultdict returns 0

    def test_with_arguments(self):
        arg = EnhancedArgument(
            agent_name="scholar",
            position="for",
            content="AI should be regulated",
            argument_type=ArgumentType.OPENING_STATEMENT,
            timestamp="t1",
            phase=DebatePhase.OPENING,
        )
        state = DebateState(
            topic="AI regulation",
            agents=["scholar"],
            arguments=[arg],
            current_turn=1,
            max_turns=5,
            phase=DebatePhase.MAIN_ARGUMENTS,
        )
        assert len(state.arguments) == 1
        assert state.arguments[0].agent_name == "scholar"

    def test_winner_set(self):
        state = DebateState(
            topic="test",
            agents=["a", "b"],
            arguments=[],
            current_turn=5,
            max_turns=5,
            phase=DebatePhase.CONCLUDED,
            winner="a",
        )
        assert state.winner == "a"

    def test_performance_metrics(self):
        state = DebateState(
            topic="test",
            agents=["a"],
            arguments=[],
            current_turn=0,
            max_turns=5,
            phase=DebatePhase.OPENING,
            performance_metrics={
                "a": {"score": 0.8, "arguments_made": 3.0},
            },
        )
        assert state.performance_metrics["a"]["score"] == 0.8

    def test_argument_network(self):
        state = DebateState(
            topic="test",
            agents=["a", "b"],
            arguments=[],
            current_turn=0,
            max_turns=5,
            phase=DebatePhase.OPENING,
            argument_network={
                "arg1": ["arg2", "arg3"],
                "arg2": [],
            },
        )
        assert len(state.argument_network["arg1"]) == 2


# ── AGENT_PERSONALITIES ──


class TestAgentPersonalities:
    def test_eight_personalities(self):
        assert len(AGENT_PERSONALITIES) == 8

    def test_all_have_required_keys(self):
        for name, personality in AGENT_PERSONALITIES.items():
            assert "description" in personality, f"{name} missing description"
            assert "strengths" in personality, f"{name} missing strengths"
            assert "weaknesses" in personality, f"{name} missing weaknesses"

    def test_descriptions_nonempty(self):
        for name, personality in AGENT_PERSONALITIES.items():
            assert len(personality["description"]) > 10, f"{name} has short description"

    def test_strengths_are_valid_metric_names(self):
        valid_metrics = {f.name for f in ArgumentMetrics.__dataclass_fields__.values()}
        for name, personality in AGENT_PERSONALITIES.items():
            for strength in personality["strengths"]:
                assert (
                    strength in valid_metrics
                ), f"{name} has invalid strength '{strength}'"

    def test_weaknesses_are_valid_metric_names(self):
        valid_metrics = {f.name for f in ArgumentMetrics.__dataclass_fields__.values()}
        for name, personality in AGENT_PERSONALITIES.items():
            for weakness in personality["weaknesses"]:
                assert (
                    weakness in valid_metrics
                ), f"{name} has invalid weakness '{weakness}'"

    def test_known_personalities(self):
        expected = [
            "The Scholar",
            "The Pragmatist",
            "The Devil's Advocate",
            "The Idealist",
            "The Skeptic",
            "The Populist",
            "The Economist",
            "The Philosopher",
        ]
        for name in expected:
            assert name in AGENT_PERSONALITIES

    def test_each_has_at_least_one_strength(self):
        for name, personality in AGENT_PERSONALITIES.items():
            assert len(personality["strengths"]) >= 1

    def test_each_has_at_least_one_weakness(self):
        for name, personality in AGENT_PERSONALITIES.items():
            assert len(personality["weaknesses"]) >= 1
