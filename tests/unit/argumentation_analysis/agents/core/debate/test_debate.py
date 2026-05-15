"""
Tests for the Debate module (integrated from 1.2.7 Dialogique).

Tests validate:
- Module import without errors (including new DebatePlugin, DebateAgent)
- CapabilityRegistry registration
- Debate definitions (enums, dataclasses)
- Argument scoring (8 metrics)
- Walton-Krabbe protocols (transitions, termination)
- Knowledge base (propositions, arguments, consistency)
- DebatePlugin (@kernel_function methods)
- DebateAgent BaseAgent interface (setup_agent_components, capabilities)
- Debate agent (fallback, LLM abstraction via SK kernel)
- Debate moderator (phase-based orchestration)
"""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_kernel():
    """Create a Kernel with a mock OpenAI service for testing."""
    kernel = Kernel()
    service = OpenAIChatCompletion(service_id="default", api_key="test-key")
    kernel.add_service(service)
    return kernel


# ---------------------------------------------------------------------------
# Import tests
# ---------------------------------------------------------------------------


class TestDebateImport:
    """Test that the debate module can be imported."""

    def test_import_package(self):
        """Debate package imports without errors."""
        from argumentation_analysis.agents.core.debate import (
            ArgumentType,
            DebatePhase,
            ArgumentMetrics,
            EnhancedArgument,
            DebateState,
            AGENT_PERSONALITIES,
            ArgumentAnalyzer,
            DebateAgent,
            DebatePlugin,
            DialogueType,
            SpeechAct,
            Proposition,
            InquiryProtocol,
            PersuasionProtocol,
        )
        from argumentation_analysis.agents.core.debate.protocols import (
            FormalArgument,
        )

        assert ArgumentType is not None
        assert len(AGENT_PERSONALITIES) == 8
        assert len(DialogueType) == 6
        assert len(SpeechAct) == 9
        assert FormalArgument is not None
        assert DebateAgent is not None
        assert DebatePlugin is not None

    def test_import_definitions(self):
        """Definitions module has all expected types."""
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            ArgumentType,
            DebatePhase,
            ArgumentMetrics,
            EnhancedArgument,
            DebateState,
            AGENT_PERSONALITIES,
        )

        assert len(ArgumentType) == 6
        assert len(DebatePhase) == 5

    def test_import_scoring(self):
        """Scoring module imports."""
        from argumentation_analysis.agents.core.debate.debate_scoring import (
            ArgumentAnalyzer,
        )

        assert callable(ArgumentAnalyzer)

    def test_import_agent(self):
        """Agent module imports DebateAgent and backward-compat alias."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
            DebatePlugin,
            EnhancedArgumentationAgent,
            EnhancedDebateModerator,
        )

        assert callable(DebateAgent)
        assert callable(DebatePlugin)
        assert callable(EnhancedDebateModerator)
        # Backward compat alias
        assert EnhancedArgumentationAgent is DebateAgent

    def test_import_protocols(self):
        """Protocols module imports all Walton-Krabbe types."""
        from argumentation_analysis.agents.core.debate.protocols import (
            DialogueType,
            SpeechAct,
            Proposition,
            FormalArgument,
            DialogueMove,
            DialogueProtocol,
            InquiryProtocol,
            PersuasionProtocol,
        )

        assert len(DialogueType) == 6
        assert len(SpeechAct) == 9

    def test_import_knowledge_base(self):
        """Knowledge base imports."""
        from argumentation_analysis.agents.core.debate.knowledge_base import (
            KnowledgeBase,
        )

        assert callable(KnowledgeBase)


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestDebateRegistration:
    """Test CapabilityRegistry registration."""

    def test_register_debate_agent(self):
        """Debate agent registers correctly in CapabilityRegistry."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
        )

        registry = CapabilityRegistry()
        registry.register_agent(
            "debate_agent",
            DebateAgent,
            capabilities=[
                "adversarial_debate",
                "argument_generation",
                "strategy_adaptation",
            ],
        )

        agents = registry.find_agents_for_capability("adversarial_debate")
        assert len(agents) == 1
        assert agents[0].name == "debate_agent"

    def test_provides_declared_capabilities(self):
        """Debate provides the capabilities it declares."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
        )

        registry = CapabilityRegistry()
        registry.register_agent(
            "debate_agent",
            DebateAgent,
            capabilities=["adversarial_debate", "argument_generation"],
        )

        all_caps = registry.get_all_capabilities()
        assert "adversarial_debate" in all_caps
        assert "argument_generation" in all_caps

    def test_register_with_convenience_function(self):
        """register_with_capability_registry() works."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.agents.core.debate import (
            register_with_capability_registry,
        )

        registry = CapabilityRegistry()
        register_with_capability_registry(registry)

        agents = registry.find_agents_for_capability("adversarial_debate")
        assert len(agents) == 1
        assert agents[0].name == "debate_agent"


# ---------------------------------------------------------------------------
# Plugin tests
# ---------------------------------------------------------------------------


class TestDebatePlugin:
    """Test DebatePlugin @kernel_function methods."""

    def test_plugin_creation(self):
        """DebatePlugin can be created."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebatePlugin,
        )

        plugin = DebatePlugin()
        assert plugin.analyzer is not None

    def test_analyze_argument_quality(self):
        """analyze_argument_quality returns valid JSON with 8 metrics."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebatePlugin,
        )

        plugin = DebatePlugin()
        result = plugin.analyze_argument_quality(
            text="Research shows that renewable energy reduces costs. "
            "Studies demonstrate a 40% improvement."
        )
        data = json.loads(result)
        assert "logical_coherence" in data
        assert "evidence_quality" in data
        assert "persuasiveness" in data
        assert len(data) == 8

    def test_analyze_logical_structure(self):
        """analyze_logical_structure extracts premises and conclusion."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebatePlugin,
        )

        plugin = DebatePlugin()
        result = plugin.analyze_logical_structure(
            text="Energy costs are declining. Research shows rapid adoption. "
            "Therefore we should invest now."
        )
        data = json.loads(result)
        assert "premises" in data
        assert "conclusion" in data
        assert "therefore" in data["conclusion"].lower()

    def test_suggest_debate_strategy(self):
        """suggest_debate_strategy returns valid strategy."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebatePlugin,
        )

        plugin = DebatePlugin()
        result = plugin.suggest_debate_strategy(phase="opening", turn_number="1")
        data = json.loads(result)
        assert data["strategy"] == "balanced"

    def test_suggest_strategy_aggressive(self):
        """High opponent strength triggers aggressive strategy."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebatePlugin,
        )

        plugin = DebatePlugin()
        result = plugin.suggest_debate_strategy(
            phase="main_arguments",
            turn_number="5",
            opponent_strength="0.9",
        )
        data = json.loads(result)
        assert data["strategy"] == "aggressive"


# ---------------------------------------------------------------------------
# BaseAgent interface tests
# ---------------------------------------------------------------------------


class TestDebateBaseAgentInterface:
    """Test that DebateAgent properly implements BaseAgent interface."""

    def test_inherits_from_base_agent(self, mock_kernel):
        """DebateAgent inherits from BaseAgent."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
        )
        from argumentation_analysis.agents.core.abc.agent_bases import (
            BaseAgent,
        )

        agent = DebateAgent(kernel=mock_kernel)
        assert isinstance(agent, BaseAgent)

    def test_setup_agent_components(self, mock_kernel):
        """setup_agent_components registers plugin with kernel."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
        )

        agent = DebateAgent(kernel=mock_kernel)
        agent.setup_agent_components()
        # Plugin should be registered
        plugins = mock_kernel.plugins
        assert "debate" in plugins


class TestDebateCapabilities:
    """Test agent capabilities declaration."""

    def test_capabilities_dict(self, mock_kernel):
        """get_agent_capabilities returns expected capabilities."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
        )

        agent = DebateAgent(kernel=mock_kernel)
        caps = agent.get_agent_capabilities()
        assert caps["adversarial_debate"] is True
        assert caps["argument_generation"] is True
        assert caps["strategy_adaptation"] is True
        assert "personalities" in caps
        assert len(caps["personalities"]) == 8
        assert "phases" in caps
        assert "argument_types" in caps

    def test_capabilities_include_all_phases(self, mock_kernel):
        """Capabilities include all 5 debate phases."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
        )

        agent = DebateAgent(kernel=mock_kernel)
        caps = agent.get_agent_capabilities()
        assert len(caps["phases"]) == 5


# ---------------------------------------------------------------------------
# Definitions tests (unchanged)
# ---------------------------------------------------------------------------


class TestDebateDefinitions:
    """Test debate definitions (enums, dataclasses)."""

    def test_argument_type_values(self):
        """All 6 argument types have correct values."""
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            ArgumentType,
        )

        assert ArgumentType.CLAIM.value == "claim"
        assert ArgumentType.EVIDENCE.value == "evidence"
        assert ArgumentType.REBUTTAL.value == "rebuttal"
        assert ArgumentType.OPENING_STATEMENT.value == "opening_statement"
        assert ArgumentType.CLOSING_STATEMENT.value == "closing_statement"
        assert ArgumentType.COUNTER_REBUTTAL.value == "counter_rebuttal"

    def test_debate_phase_values(self):
        """All 5 debate phases exist."""
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            DebatePhase,
        )

        phases = [
            DebatePhase.OPENING,
            DebatePhase.MAIN_ARGUMENTS,
            DebatePhase.REBUTTALS,
            DebatePhase.CLOSING,
            DebatePhase.CONCLUDED,
        ]
        assert len(phases) == 5

    def test_argument_metrics_defaults(self):
        """ArgumentMetrics has sensible defaults."""
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            ArgumentMetrics,
        )

        m = ArgumentMetrics()
        assert m.logical_coherence == 0.0
        assert m.evidence_quality == 0.0
        assert m.persuasiveness == 0.0

    def test_enhanced_argument_creation(self):
        """EnhancedArgument auto-generates id and word count."""
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            EnhancedArgument,
            ArgumentType,
            DebatePhase,
        )

        arg = EnhancedArgument(
            agent_name="test_agent",
            position="for",
            content="This is a test argument with several words.",
            argument_type=ArgumentType.CLAIM,
            timestamp="2026-01-01",
            phase=DebatePhase.OPENING,
        )
        assert arg.id != ""
        assert arg.word_count == 8

    def test_debate_state_creation(self):
        """DebateState tracks full debate state."""
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            DebateState,
            DebatePhase,
        )

        state = DebateState(
            topic="Test topic",
            agents=["agent1", "agent2"],
            arguments=[],
            current_turn=0,
            max_turns=10,
            phase=DebatePhase.OPENING,
        )
        assert state.topic == "Test topic"
        assert len(state.agents) == 2

    def test_agent_personalities(self):
        """All 8 personalities have description, strengths, weaknesses."""
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            AGENT_PERSONALITIES,
        )

        assert len(AGENT_PERSONALITIES) == 8
        for name, profile in AGENT_PERSONALITIES.items():
            assert "description" in profile
            assert "strengths" in profile
            assert "weaknesses" in profile


# ---------------------------------------------------------------------------
# Argument scoring tests (unchanged)
# ---------------------------------------------------------------------------


class TestArgumentAnalyzer:
    """Test the argument scoring system."""

    def test_analyzer_creation(self):
        """ArgumentAnalyzer can be created."""
        from argumentation_analysis.agents.core.debate.debate_scoring import (
            ArgumentAnalyzer,
        )

        analyzer = ArgumentAnalyzer()
        assert analyzer is not None

    def test_analyze_argument(self):
        """Analyzing an argument produces metrics."""
        from argumentation_analysis.agents.core.debate.debate_scoring import (
            ArgumentAnalyzer,
        )
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            EnhancedArgument,
            ArgumentType,
            DebatePhase,
            ArgumentMetrics,
        )

        analyzer = ArgumentAnalyzer()
        arg = EnhancedArgument(
            agent_name="test",
            position="for",
            content=(
                "Research shows that renewable energy is cost-effective. "
                "Studies by the IEA demonstrate decreasing costs. "
                "Therefore, transitioning to renewables is economically sound."
            ),
            argument_type=ArgumentType.EVIDENCE,
            timestamp="2026-01-01",
            phase=DebatePhase.MAIN_ARGUMENTS,
        )
        metrics = analyzer.analyze_argument(arg, [])
        assert isinstance(metrics, ArgumentMetrics)
        assert 0 <= metrics.logical_coherence <= 1
        assert 0 <= metrics.evidence_quality <= 1
        assert 0 <= metrics.persuasiveness <= 1

    def test_novelty_decreases_with_repetition(self):
        """Novelty score decreases when arguments repeat content."""
        from argumentation_analysis.agents.core.debate.debate_scoring import (
            ArgumentAnalyzer,
        )
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            EnhancedArgument,
            ArgumentType,
            DebatePhase,
        )

        analyzer = ArgumentAnalyzer()
        first = EnhancedArgument(
            agent_name="a",
            position="for",
            content="Renewable energy reduces carbon emissions significantly.",
            argument_type=ArgumentType.CLAIM,
            timestamp="t1",
            phase=DebatePhase.MAIN_ARGUMENTS,
        )
        second = EnhancedArgument(
            agent_name="b",
            position="for",
            content="Renewable energy reduces carbon emissions significantly.",
            argument_type=ArgumentType.CLAIM,
            timestamp="t2",
            phase=DebatePhase.MAIN_ARGUMENTS,
        )
        m1 = analyzer.analyze_argument(first, [])
        m2 = analyzer.analyze_argument(second, [first])
        assert m2.novelty_score <= m1.novelty_score

    def test_evidence_quality_keywords(self):
        """Evidence quality increases with evidence keywords."""
        from argumentation_analysis.agents.core.debate.debate_scoring import (
            ArgumentAnalyzer,
        )
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            EnhancedArgument,
            ArgumentType,
            DebatePhase,
        )

        analyzer = ArgumentAnalyzer()
        evidence_rich = EnhancedArgument(
            agent_name="a",
            position="for",
            content=(
                "According to research published in Nature, studies show that "
                "data from controlled experiments demonstrate a 40% improvement. "
                "Statistics confirm the trend with a p-value of 0.001."
            ),
            argument_type=ArgumentType.EVIDENCE,
            timestamp="t1",
            phase=DebatePhase.MAIN_ARGUMENTS,
        )
        evidence_poor = EnhancedArgument(
            agent_name="b",
            position="for",
            content="I think this is good because it seems nice.",
            argument_type=ArgumentType.CLAIM,
            timestamp="t2",
            phase=DebatePhase.MAIN_ARGUMENTS,
        )
        m1 = analyzer.analyze_argument(evidence_rich, [])
        m2 = analyzer.analyze_argument(evidence_poor, [])
        assert m1.evidence_quality > m2.evidence_quality


# ---------------------------------------------------------------------------
# Walton-Krabbe protocol tests (unchanged)
# ---------------------------------------------------------------------------


class TestWaltonKrabbeProtocols:
    """Test Walton-Krabbe dialogue protocols."""

    def test_inquiry_protocol_transitions(self):
        """Inquiry protocol has correct transition rules."""
        from argumentation_analysis.agents.core.debate.protocols import (
            InquiryProtocol,
            SpeechAct,
        )

        protocol = InquiryProtocol()
        # QUESTION -> CLAIM is allowed
        assert protocol.is_valid_move(SpeechAct.QUESTION, SpeechAct.CLAIM)
        # CLAIM -> SUPPORT is allowed
        assert protocol.is_valid_move(SpeechAct.CLAIM, SpeechAct.SUPPORT)
        # CLAIM -> RETRACT is NOT allowed in inquiry
        assert not protocol.is_valid_move(SpeechAct.CLAIM, SpeechAct.RETRACT)

    def test_persuasion_protocol_transitions(self):
        """Persuasion protocol has correct transition rules."""
        from argumentation_analysis.agents.core.debate.protocols import (
            PersuasionProtocol,
            SpeechAct,
        )

        protocol = PersuasionProtocol()
        # CLAIM -> CHALLENGE is allowed
        assert protocol.is_valid_move(SpeechAct.CLAIM, SpeechAct.CHALLENGE)
        # CHALLENGE -> ARGUE is allowed
        assert protocol.is_valid_move(SpeechAct.CHALLENGE, SpeechAct.ARGUE)
        # CHALLENGE -> RETRACT is allowed (withdraw claim under challenge)
        assert protocol.is_valid_move(SpeechAct.CHALLENGE, SpeechAct.RETRACT)

    def test_inquiry_termination_consensus(self):
        """Inquiry terminates when last 3 moves are UNDERSTAND/CONCEDE."""
        from argumentation_analysis.agents.core.debate.protocols import (
            InquiryProtocol,
            SpeechAct,
            DialogueMove,
            Proposition,
        )

        protocol = InquiryProtocol()
        prop = Proposition(content="Test")
        history = [
            DialogueMove(speaker="a", act=SpeechAct.CLAIM, content=prop),
            DialogueMove(speaker="b", act=SpeechAct.UNDERSTAND, content=prop),
            DialogueMove(speaker="a", act=SpeechAct.UNDERSTAND, content=prop),
            DialogueMove(speaker="b", act=SpeechAct.UNDERSTAND, content=prop),
        ]
        assert protocol.is_terminal_state(history)

    def test_persuasion_termination_concede(self):
        """Persuasion terminates on CONCEDE."""
        from argumentation_analysis.agents.core.debate.protocols import (
            PersuasionProtocol,
            SpeechAct,
            DialogueMove,
            Proposition,
        )

        protocol = PersuasionProtocol()
        prop = Proposition(content="Test")
        history = [
            DialogueMove(speaker="a", act=SpeechAct.CLAIM, content=prop),
            DialogueMove(speaker="b", act=SpeechAct.CONCEDE, content=prop),
        ]
        assert protocol.is_terminal_state(history)

    def test_get_allowed_responses(self):
        """Get allowed responses for a given speech act."""
        from argumentation_analysis.agents.core.debate.protocols import (
            InquiryProtocol,
            SpeechAct,
        )

        protocol = InquiryProtocol()
        responses = protocol.get_allowed_responses(SpeechAct.QUESTION)
        assert SpeechAct.CLAIM in responses
        assert SpeechAct.ARGUE in responses

    def test_dialogue_type_enum(self):
        """All 6 dialogue types exist."""
        from argumentation_analysis.agents.core.debate.protocols import (
            DialogueType,
        )

        assert DialogueType.INQUIRY.value == "inquiry"
        assert DialogueType.PERSUASION.value == "persuasion"
        assert DialogueType.NEGOTIATION.value == "negotiation"
        assert DialogueType.DELIBERATION.value == "deliberation"
        assert DialogueType.INFORMATION_SEEKING.value == "information_seeking"
        assert DialogueType.ERISTIC.value == "eristic"

    def test_proposition_equality(self):
        """Propositions with same content are equal."""
        from argumentation_analysis.agents.core.debate.protocols import (
            Proposition,
        )

        p1 = Proposition(content="It is raining")
        p2 = Proposition(content="It is raining")
        assert p1 == p2
        assert hash(p1) == hash(p2)

    def test_formal_argument_str(self):
        """FormalArgument string representation."""
        from argumentation_analysis.agents.core.debate.protocols import (
            Proposition,
            FormalArgument,
        )

        arg = FormalArgument(
            premises=[Proposition(content="A"), Proposition(content="B")],
            conclusion=Proposition(content="C"),
        )
        s = str(arg)
        assert "A" in s
        assert "B" in s
        assert "C" in s


# ---------------------------------------------------------------------------
# Knowledge base tests (unchanged)
# ---------------------------------------------------------------------------


class TestKnowledgeBase:
    """Test the knowledge base for argumentation."""

    def test_add_proposition(self):
        """Add proposition to knowledge base."""
        from argumentation_analysis.agents.core.debate.knowledge_base import (
            KnowledgeBase,
        )
        from argumentation_analysis.agents.core.debate.protocols import (
            Proposition,
        )

        kb = KnowledgeBase()
        p = Proposition(content="It is raining")
        kb.add_proposition(p)
        assert kb.entails(p)

    def test_add_argument_registers_premises(self):
        """Adding argument auto-registers premises and conclusion."""
        from argumentation_analysis.agents.core.debate.knowledge_base import (
            KnowledgeBase,
        )
        from argumentation_analysis.agents.core.debate.protocols import (
            Proposition,
            FormalArgument,
        )

        kb = KnowledgeBase()
        p1 = Proposition(content="Clouds are dark")
        p2 = Proposition(content="It is raining")
        arg = FormalArgument(premises=[p1], conclusion=p2)
        kb.add_argument(arg)

        assert kb.entails(p1)
        assert kb.entails(p2)
        assert len(kb.get_all_arguments()) == 1

    def test_find_supporting_arguments(self):
        """Find arguments supporting a proposition."""
        from argumentation_analysis.agents.core.debate.knowledge_base import (
            KnowledgeBase,
        )
        from argumentation_analysis.agents.core.debate.protocols import (
            Proposition,
            FormalArgument,
        )

        kb = KnowledgeBase()
        p1 = Proposition(content="Evidence")
        p2 = Proposition(content="Conclusion")
        arg = FormalArgument(premises=[p1], conclusion=p2)
        kb.add_argument(arg)

        supporters = kb.find_supporting_arguments(p2)
        assert len(supporters) == 1

    def test_find_attacking_arguments(self):
        """Find arguments negating a proposition."""
        from argumentation_analysis.agents.core.debate.knowledge_base import (
            KnowledgeBase,
        )
        from argumentation_analysis.agents.core.debate.protocols import (
            Proposition,
            FormalArgument,
        )

        kb = KnowledgeBase()
        target = Proposition(content="It is sunny")
        neg = Proposition(content="\u00acIt is sunny")
        arg = FormalArgument(premises=[Proposition(content="Clouds")], conclusion=neg)
        kb.add_argument(arg)

        attackers = kb.find_attacking_arguments(target)
        assert len(attackers) == 1

    def test_consistency_check(self):
        """Consistent KB has no contradictions."""
        from argumentation_analysis.agents.core.debate.knowledge_base import (
            KnowledgeBase,
        )
        from argumentation_analysis.agents.core.debate.protocols import (
            Proposition,
        )

        kb = KnowledgeBase()
        kb.add_proposition(Proposition(content="A"))
        kb.add_proposition(Proposition(content="B"))
        assert kb.is_consistent()

    def test_inconsistency_detected(self):
        """Inconsistent KB detects contradiction (P and not-P)."""
        from argumentation_analysis.agents.core.debate.knowledge_base import (
            KnowledgeBase,
        )
        from argumentation_analysis.agents.core.debate.protocols import (
            Proposition,
        )

        kb = KnowledgeBase()
        kb.add_proposition(Proposition(content="A"))
        kb.add_proposition(Proposition(content="\u00acA"))
        assert not kb.is_consistent()


# ---------------------------------------------------------------------------
# Debate agent tests (adapted for BaseAgent)
# ---------------------------------------------------------------------------


class TestDebateAgent:
    """Test debate agent behavior."""

    def setup_method(self):
        """Set up kernel for each test."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
        )

        self.AgentClass = DebateAgent
        self.kernel = Kernel()
        service = OpenAIChatCompletion(service_id="default", api_key="test-key")
        self.kernel.add_service(service)

    def _create_agent(self, **kwargs):
        """Helper to create a DebateAgent with the test kernel."""
        return self.AgentClass(kernel=self.kernel, **kwargs)

    def test_agent_creation(self):
        """Create agent with personality and position."""
        agent = self._create_agent(
            agent_name="Scholar",
            personality="Academic and methodical",
            position="for",
        )
        assert agent.name == "Scholar"
        assert agent.position == "for"
        assert agent.personality == "Academic and methodical"

    async def test_fallback_argument(self):
        """Agent produces fallback when LLM unavailable."""
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            ArgumentType,
            DebatePhase,
            DebateState,
        )

        agent = self._create_agent(
            agent_name="Test", personality="test", position="for"
        )
        state = DebateState(
            topic="Climate change",
            agents=["Test"],
            arguments=[],
            current_turn=0,
            max_turns=10,
            phase=DebatePhase.OPENING,
        )

        with patch.object(
            agent,
            "_generate_via_kernel",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM unavailable"),
        ):
            arg = await agent.generate_argument(state, ArgumentType.OPENING_STATEMENT)

        assert arg.agent_name == "Test"
        assert arg.content != ""
        assert arg.metrics.persuasiveness == 0.3  # Fallback metric

    async def test_agent_with_mock_llm(self):
        """Agent uses SK kernel for LLM generation."""
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            ArgumentType,
            DebatePhase,
            DebateState,
        )

        agent = self._create_agent(
            agent_name="Scholar", personality="Academic", position="for"
        )
        state = DebateState(
            topic="Renewable energy",
            agents=["Scholar"],
            arguments=[],
            current_turn=0,
            max_turns=10,
            phase=DebatePhase.MAIN_ARGUMENTS,
        )

        mock_response = (
            "Renewable energy is the future because studies show " "declining costs."
        )
        with patch.object(
            agent,
            "_generate_via_kernel",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            arg = await agent.generate_argument(state, ArgumentType.EVIDENCE)

        assert "Renewable" in arg.content or "energy" in arg.content

    def test_strategy_adaptation(self):
        """Agent adapts strategy based on debate phase."""
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            DebatePhase,
            DebateState,
        )

        agent = self._create_agent(
            agent_name="Test", personality="test", position="for"
        )
        state = DebateState(
            topic="Test",
            agents=["Test"],
            arguments=[],
            current_turn=0,
            max_turns=10,
            phase=DebatePhase.OPENING,
        )
        agent._adapt_strategy(state)
        assert agent.strategy == "balanced"  # Early game

    def test_logical_structure_analysis(self):
        """Agent extracts logical structure from text."""
        agent = self._create_agent(
            agent_name="Test", personality="test", position="for"
        )
        structure = agent._analyze_logical_structure(
            "Energy costs are declining. Research shows rapid adoption. "
            "Therefore we should invest now."
        )
        assert "premises" in structure
        assert "conclusion" in structure
        assert "therefore" in structure["conclusion"].lower()

    async def test_invoke_single(self):
        """invoke_single creates a debate state and generates argument."""
        agent = self._create_agent(
            agent_name="Test", personality="test", position="for"
        )
        with patch.object(
            agent,
            "_generate_via_kernel",
            new_callable=AsyncMock,
            side_effect=RuntimeError("No LLM"),
        ):
            result = await agent.invoke_single("Climate change debate")

        assert "argument" in result
        assert "metrics" in result
        assert "strategy" in result

    async def test_invoke_single_empty_topic(self):
        """invoke_single returns error for empty topic."""
        agent = self._create_agent()
        result = await agent.invoke_single("")
        assert "error" in result


# ---------------------------------------------------------------------------
# Debate moderator tests (adapted for BaseAgent agents)
# ---------------------------------------------------------------------------


class TestDebateModerator:
    """Test the debate moderator."""

    def setup_method(self):
        """Set up kernel for agent creation."""
        self.kernel = Kernel()
        service = OpenAIChatCompletion(service_id="default", api_key="test-key")
        self.kernel.add_service(service)

    def test_moderator_creation(self):
        """Moderator can be created with rules."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            EnhancedDebateModerator,
        )

        mod = EnhancedDebateModerator()
        assert mod.debate_rules["max_turns_per_phase"]["opening"] == 2
        assert mod.debate_rules["max_turns_per_phase"]["main_arguments"] == 6

    def test_audience_simulation(self):
        """Audience reaction produces non-negative scores."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            EnhancedDebateModerator,
        )
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            EnhancedArgument,
            ArgumentType,
            DebatePhase,
            ArgumentMetrics,
        )

        mod = EnhancedDebateModerator()
        arg = EnhancedArgument(
            agent_name="test",
            position="for",
            content="Test argument content here.",
            argument_type=ArgumentType.CLAIM,
            timestamp="t1",
            phase=DebatePhase.MAIN_ARGUMENTS,
            metrics=ArgumentMetrics(
                persuasiveness=0.8,
                evidence_quality=0.9,
                emotional_appeal=0.5,
            ),
        )
        score = mod._simulate_audience_reaction(arg)
        assert score >= 0

    async def test_run_debate_full(self):
        """Full debate runs with fallback agents (no LLM)."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
            EnhancedDebateModerator,
        )
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            DebatePhase,
        )

        agents = [
            DebateAgent(
                kernel=self.kernel,
                agent_name="Alice",
                personality="Scholar",
                position="for",
            ),
            DebateAgent(
                kernel=self.kernel,
                agent_name="Bob",
                personality="Skeptic",
                position="against",
            ),
        ]
        moderator = EnhancedDebateModerator()

        # Mock LLM for both agents to force fallback
        with patch.object(
            agents[0],
            "_generate_via_kernel",
            new_callable=AsyncMock,
            side_effect=RuntimeError("No LLM"),
        ), patch.object(
            agents[1],
            "_generate_via_kernel",
            new_callable=AsyncMock,
            side_effect=RuntimeError("No LLM"),
        ):
            state = await moderator.run_debate(
                "Should we invest in renewable energy?", agents
            )

        assert state.phase == DebatePhase.CONCLUDED
        assert len(state.arguments) == 14  # 2+6+4+2
        assert state.winner is not None


# ---------------------------------------------------------------------------
# _coerce_score tests (SCDA Sprint 2 — #538)
# ---------------------------------------------------------------------------


class TestCoerceScore:
    """Test _coerce_score handles string quality descriptors robustly."""

    def test_numeric_int(self):
        """Integer input converts to float."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            _coerce_score,
        )

        assert _coerce_score(1) == 1.0
        assert _coerce_score(0) == 0.0

    def test_numeric_float(self):
        """Float input passes through."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            _coerce_score,
        )

        assert _coerce_score(0.85) == 0.85
        assert _coerce_score(0.0) == 0.0

    def test_high_descriptor(self):
        """'high' maps to 0.85."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            _coerce_score,
        )

        assert _coerce_score("high") == 0.85

    def test_elevé_descriptor(self):
        """French 'élevé' maps to 0.85."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            _coerce_score,
        )

        assert _coerce_score("élevé") == 0.85

    def test_medium_descriptor(self):
        """'medium' maps to 0.5."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            _coerce_score,
        )

        assert _coerce_score("medium") == 0.5

    def test_mixed_descriptor(self):
        """'mixed' maps to 0.5 — the original crash case."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            _coerce_score,
        )

        assert _coerce_score("mixed") == 0.5

    def test_moyen_descriptor(self):
        """French 'moyen' maps to 0.5."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            _coerce_score,
        )

        assert _coerce_score("moyen") == 0.5

    def test_low_descriptor(self):
        """'low' maps to 0.2."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            _coerce_score,
        )

        assert _coerce_score("low") == 0.2

    def test_faible_descriptor(self):
        """French 'faible' maps to 0.2."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            _coerce_score,
        )

        assert _coerce_score("faible") == 0.2

    def test_unknown_string_defaults_neutral(self):
        """Unknown descriptor defaults to 0.5 with warning."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            _coerce_score,
        )

        assert _coerce_score("inconclusive") == 0.5
        assert _coerce_score("N/A") == 0.5

    def test_numeric_string(self):
        """String containing a number converts correctly."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            _coerce_score,
        )

        assert _coerce_score("0.75") == 0.75
        assert _coerce_score("0.3") == 0.3

    def test_whitespace_trimmed(self):
        """Whitespace around descriptor is trimmed."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            _coerce_score,
        )

        assert _coerce_score("  high  ") == 0.85
        assert _coerce_score(" mixed ") == 0.5

    def test_case_insensitive(self):
        """Descriptor matching is case-insensitive."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            _coerce_score,
        )

        assert _coerce_score("High") == 0.85
        assert _coerce_score("MIXED") == 0.5
        assert _coerce_score("Low") == 0.2

    def test_non_string_non_numeric_defaults(self):
        """Non-string, non-numeric input defaults to 0.5."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            _coerce_score,
        )

        assert _coerce_score(None) == 0.5


class TestSuggestDebateStrategyWithDescriptors:
    """Test suggest_debate_strategy with string descriptors."""

    def test_mixed_strength_no_crash(self):
        """'mixed' opponent strength does not raise ValueError."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebatePlugin,
        )

        plugin = DebatePlugin()
        result = plugin.suggest_debate_strategy(
            phase="main_arguments", turn_number="5", opponent_strength="mixed"
        )
        data = json.loads(result)
        assert "strategy" in data

    def test_high_strength_aggressive(self):
        """'high' opponent strength triggers aggressive strategy."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebatePlugin,
        )

        plugin = DebatePlugin()
        result = plugin.suggest_debate_strategy(
            phase="main_arguments", turn_number="5", opponent_strength="high"
        )
        data = json.loads(result)
        assert data["strategy"] == "aggressive"

    def test_low_strength_evidence_heavy(self):
        """'low' opponent strength after turn 3 triggers evidence_heavy."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebatePlugin,
        )

        plugin = DebatePlugin()
        result = plugin.suggest_debate_strategy(
            phase="main_arguments", turn_number="5", opponent_strength="low"
        )
        data = json.loads(result)
        assert data["strategy"] == "evidence_heavy"
