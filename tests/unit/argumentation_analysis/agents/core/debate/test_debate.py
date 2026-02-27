"""
Tests for the Debate module (integrated from 1.2.7 Dialogique).

Tests validate:
- Module import without errors
- CapabilityRegistry registration
- Debate definitions (enums, dataclasses)
- Argument scoring (8 metrics)
- Walton-Krabbe protocols (transitions, termination)
- Knowledge base (propositions, arguments, consistency)
- Debate agent (fallback, LLM abstraction)
- Debate moderator (phase-based orchestration)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


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
            DialogueType,
            SpeechAct,
            Proposition,
            InquiryProtocol,
            PersuasionProtocol,
        )
        from argumentation_analysis.agents.core.debate.protocols import FormalArgument

        assert ArgumentType is not None
        assert len(AGENT_PERSONALITIES) == 8
        assert len(DialogueType) == 6
        assert len(SpeechAct) == 9
        assert FormalArgument is not None

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
        """Agent module imports."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            EnhancedArgumentationAgent,
            EnhancedDebateModerator,
        )

        assert callable(EnhancedArgumentationAgent)
        assert callable(EnhancedDebateModerator)

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


class TestDebateRegistration:
    """Test CapabilityRegistry registration."""

    def test_register_debate_agent(self):
        """Debate agent registers correctly in CapabilityRegistry."""
        from argumentation_analysis.core.capability_registry import CapabilityRegistry
        from argumentation_analysis.agents.core.debate.debate_agent import (
            EnhancedArgumentationAgent,
        )

        registry = CapabilityRegistry()
        registry.register_agent(
            "debate_agent",
            EnhancedArgumentationAgent,
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
        from argumentation_analysis.core.capability_registry import CapabilityRegistry
        from argumentation_analysis.agents.core.debate.debate_agent import (
            EnhancedArgumentationAgent,
        )

        registry = CapabilityRegistry()
        registry.register_agent(
            "debate_agent",
            EnhancedArgumentationAgent,
            capabilities=["adversarial_debate", "argument_generation"],
        )

        all_caps = registry.get_all_capabilities()
        assert "adversarial_debate" in all_caps
        assert "argument_generation" in all_caps


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


class TestWaltonKrabbeProtocols:
    """Test Walton-Krabbe dialogue protocols."""

    def test_inquiry_protocol_transitions(self):
        """Inquiry protocol has correct transition rules."""
        from argumentation_analysis.agents.core.debate.protocols import (
            InquiryProtocol,
            SpeechAct,
        )

        protocol = InquiryProtocol()
        # QUESTION → CLAIM is allowed
        assert protocol.is_valid_move(SpeechAct.QUESTION, SpeechAct.CLAIM)
        # CLAIM → SUPPORT is allowed
        assert protocol.is_valid_move(SpeechAct.CLAIM, SpeechAct.SUPPORT)
        # CLAIM → RETRACT is NOT allowed in inquiry
        assert not protocol.is_valid_move(SpeechAct.CLAIM, SpeechAct.RETRACT)

    def test_persuasion_protocol_transitions(self):
        """Persuasion protocol has correct transition rules."""
        from argumentation_analysis.agents.core.debate.protocols import (
            PersuasionProtocol,
            SpeechAct,
        )

        protocol = PersuasionProtocol()
        # CLAIM → CHALLENGE is allowed
        assert protocol.is_valid_move(SpeechAct.CLAIM, SpeechAct.CHALLENGE)
        # CHALLENGE → ARGUE is allowed
        assert protocol.is_valid_move(SpeechAct.CHALLENGE, SpeechAct.ARGUE)
        # CHALLENGE → RETRACT is allowed (withdraw claim under challenge)
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
        from argumentation_analysis.agents.core.debate.protocols import DialogueType

        assert DialogueType.INQUIRY.value == "inquiry"
        assert DialogueType.PERSUASION.value == "persuasion"
        assert DialogueType.NEGOTIATION.value == "negotiation"
        assert DialogueType.DELIBERATION.value == "deliberation"
        assert DialogueType.INFORMATION_SEEKING.value == "information_seeking"
        assert DialogueType.ERISTIC.value == "eristic"

    def test_proposition_equality(self):
        """Propositions with same content are equal."""
        from argumentation_analysis.agents.core.debate.protocols import Proposition

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


class TestKnowledgeBase:
    """Test the knowledge base for argumentation."""

    def test_add_proposition(self):
        """Add proposition to knowledge base."""
        from argumentation_analysis.agents.core.debate.knowledge_base import (
            KnowledgeBase,
        )
        from argumentation_analysis.agents.core.debate.protocols import Proposition

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
        from argumentation_analysis.agents.core.debate.protocols import Proposition

        kb = KnowledgeBase()
        kb.add_proposition(Proposition(content="A"))
        kb.add_proposition(Proposition(content="B"))
        assert kb.is_consistent()

    def test_inconsistency_detected(self):
        """Inconsistent KB detects contradiction (P and not-P)."""
        from argumentation_analysis.agents.core.debate.knowledge_base import (
            KnowledgeBase,
        )
        from argumentation_analysis.agents.core.debate.protocols import Proposition

        kb = KnowledgeBase()
        kb.add_proposition(Proposition(content="A"))
        kb.add_proposition(Proposition(content="\u00acA"))
        assert not kb.is_consistent()


class TestDebateAgent:
    """Test debate agent behavior."""

    def test_agent_creation(self):
        """Create agent with personality and position."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            EnhancedArgumentationAgent,
        )

        agent = EnhancedArgumentationAgent(
            name="Scholar",
            personality="Academic and methodical",
            position="for",
        )
        assert agent.name == "Scholar"
        assert agent.position == "for"
        assert agent._llm_client is None

    def test_fallback_argument(self):
        """Agent produces fallback when no LLM available."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            EnhancedArgumentationAgent,
        )
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            ArgumentType,
            DebatePhase,
            DebateState,
        )

        agent = EnhancedArgumentationAgent(
            name="Test", personality="test", position="for"
        )
        state = DebateState(
            topic="Climate change",
            agents=["Test"],
            arguments=[],
            current_turn=0,
            max_turns=10,
            phase=DebatePhase.OPENING,
        )

        import asyncio

        arg = asyncio.get_event_loop().run_until_complete(
            agent.generate_argument(state, ArgumentType.OPENING_STATEMENT)
        )
        assert arg.agent_name == "Test"
        assert arg.content != ""
        assert arg.metrics.persuasiveness == 0.3  # Fallback metric

    def test_agent_with_mock_llm(self):
        """Agent uses injected LLM client."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            EnhancedArgumentationAgent,
        )
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            ArgumentType,
            DebatePhase,
            DebateState,
        )

        mock_client = MagicMock()
        mock_client.chat_completion = AsyncMock(
            return_value="Renewable energy is the future because studies show declining costs."
        )

        agent = EnhancedArgumentationAgent(
            name="Scholar",
            personality="Academic",
            position="for",
            llm_client=mock_client,
        )
        state = DebateState(
            topic="Renewable energy",
            agents=["Scholar"],
            arguments=[],
            current_turn=0,
            max_turns=10,
            phase=DebatePhase.MAIN_ARGUMENTS,
        )

        import asyncio

        arg = asyncio.get_event_loop().run_until_complete(
            agent.generate_argument(state, ArgumentType.EVIDENCE)
        )
        assert "Renewable" in arg.content or "energy" in arg.content
        mock_client.chat_completion.assert_called_once()

    def test_strategy_adaptation(self):
        """Agent adapts strategy based on debate phase."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            EnhancedArgumentationAgent,
        )
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            DebatePhase,
            DebateState,
        )

        agent = EnhancedArgumentationAgent(
            name="Test", personality="test", position="for"
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
        from argumentation_analysis.agents.core.debate.debate_agent import (
            EnhancedArgumentationAgent,
        )

        agent = EnhancedArgumentationAgent(
            name="Test", personality="test", position="for"
        )
        structure = agent._analyze_logical_structure(
            "Energy costs are declining. Research shows rapid adoption. "
            "Therefore we should invest now."
        )
        assert "premises" in structure
        assert "conclusion" in structure
        assert "therefore" in structure["conclusion"].lower()


class TestDebateModerator:
    """Test the debate moderator."""

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

    def test_run_debate_full(self):
        """Full debate runs with fallback agents (no LLM)."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            EnhancedArgumentationAgent,
            EnhancedDebateModerator,
        )
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            DebatePhase,
        )

        agents = [
            EnhancedArgumentationAgent("Alice", "Scholar", "for"),
            EnhancedArgumentationAgent("Bob", "Skeptic", "against"),
        ]
        moderator = EnhancedDebateModerator()

        import asyncio

        state = asyncio.get_event_loop().run_until_complete(
            moderator.run_debate("Should we invest in renewable energy?", agents)
        )
        assert state.phase == DebatePhase.CONCLUDED
        assert len(state.arguments) == 14  # 2+6+4+2
        assert state.winner is not None
