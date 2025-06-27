#!/usr/bin/env python3
"""
Enhanced Dialogical Argumentation System
A sophisticated multi-agent debate system with advanced argument analysis,
fact-checking, dynamic scoring, and interactive features.
"""

from openai import OpenAI
import asyncio
import json
import random
import time
import sys
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from collections import defaultdict, Counter
import os
from enum import Enum
import matplotlib.pyplot as plt
import networkx as nx
from textstat import flesch_reading_ease, flesch_kincaid_grade
from collections import defaultdict, Counter

# Enhanced logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# OpenAI client setup with error handling
try:
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
except Exception as e:
    logger.warning(f"OpenAI client initialization failed: {e}")
    client = None

class ArgumentType(Enum):
    """Enumeration of argument types"""
    OPENING_STATEMENT = "opening_statement"
    CLAIM = "claim"
    EVIDENCE = "evidence"
    REBUTTAL = "rebuttal"
    COUNTER_REBUTTAL = "counter_rebuttal"
    CLOSING_STATEMENT = "closing_statement"

class DebatePhase(Enum):
    """Enumeration of debate phases"""
    OPENING = "opening"
    MAIN_ARGUMENTS = "main_arguments"
    REBUTTALS = "rebuttals"
    CLOSING = "closing"
    CONCLUDED = "concluded"

@dataclass
class ArgumentMetrics:
    """Advanced metrics for argument evaluation"""
    logical_coherence: float = 0.0
    evidence_quality: float = 0.0
    relevance_score: float = 0.0
    emotional_appeal: float = 0.0
    readability_score: float = 0.0
    fact_check_score: float = 0.0
    novelty_score: float = 0.0
    persuasiveness: float = 0.0

@dataclass
class EnhancedArgument:
    """Enhanced argument structure with comprehensive metadata"""
    agent_name: str
    position: str  # "for" or "against"
    content: str
    argument_type: ArgumentType
    timestamp: str
    phase: DebatePhase
    references: List[str] = field(default_factory=list)
    citations: List[Dict[str, str]] = field(default_factory=list)
    metrics: ArgumentMetrics = field(default_factory=ArgumentMetrics)
    logical_structure: Dict[str, Any] = field(default_factory=dict)
    word_count: int = 0
    response_to: Optional[str] = None  # ID of argument being responded to

    def __post_init__(self):
        self.word_count = len(self.content.split())
        self.id = f"{self.agent_name}_{self.timestamp}_{hash(self.content) % 10000}"

@dataclass
class DebateState:
    """Enhanced debate state tracking"""
    topic: str
    agents: List[str]
    arguments: List[EnhancedArgument]
    current_turn: int
    max_turns: int
    phase: DebatePhase
    winner: Optional[str] = None
    audience_votes: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    performance_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    argument_network: Dict[str, List[str]] = field(default_factory=dict)
    debate_summary: str = ""
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())

class ArgumentAnalyzer:
    """Advanced argument analysis and scoring system"""
    
    def __init__(self):
        self.logical_indicators = [
            "therefore", "because", "since", "thus", "hence", "consequently",
            "as a result", "it follows that", "given that", "due to"
        ]
        self.evidence_indicators = [
            "studies show", "research indicates", "data suggests", "according to",
            "evidence", "statistics", "findings", "survey", "analysis", "report"
        ]
        self.emotional_indicators = [
            "feel", "believe", "think", "important", "crucial", "vital",
            "devastating", "wonderful", "terrible", "amazing"
        ]
    
    def analyze_argument(self, argument: EnhancedArgument, context: List[EnhancedArgument]) -> ArgumentMetrics:
        """Comprehensive argument analysis"""
        metrics = ArgumentMetrics()
        
        # Logical coherence analysis
        metrics.logical_coherence = self._assess_logical_coherence(argument.content)
        
        # Evidence quality assessment
        metrics.evidence_quality = self._assess_evidence_quality(argument.content)
        
        # Relevance to topic and context
        metrics.relevance_score = self._assess_relevance(argument, context)
        
        # Emotional appeal detection
        metrics.emotional_appeal = self._assess_emotional_appeal(argument.content)
        
        # Readability analysis
        metrics.readability_score = self._assess_readability(argument.content)
        
        # Fact-checking placeholder (would integrate with real fact-checking APIs)
        metrics.fact_check_score = self._basic_fact_check(argument.content)
        
        # Novelty assessment
        metrics.novelty_score = self._assess_novelty(argument, context)
        
        # Overall persuasiveness
        metrics.persuasiveness = self._calculate_persuasiveness(metrics)
        
        return metrics
    
    def _assess_logical_coherence(self, content: str) -> float:
        """Assess logical structure and coherence"""
        score = 0.5  # Base score
        
        # Check for logical connectors
        logical_count = sum(1 for indicator in self.logical_indicators 
                          if indicator.lower() in content.lower())
        score += min(logical_count * 0.1, 0.3)
        
        # Check for structured argumentation patterns
        if "first" in content.lower() and "second" in content.lower():
            score += 0.1
        if any(word in content.lower() for word in ["premise", "conclusion", "assumption"]):
            score += 0.1
        
        return min(score, 1.0)
    
    def _assess_evidence_quality(self, content: str) -> float:
        """Assess quality and presence of evidence"""
        score = 0.3  # Base score
        
        # Check for evidence indicators
        evidence_count = sum(1 for indicator in self.evidence_indicators 
                           if indicator.lower() in content.lower())
        score += min(evidence_count * 0.15, 0.4)
        
        # Check for specific data (numbers, percentages)
        numbers = re.findall(r'\d+(?:\.\d+)?%?', content)
        if numbers:
            score += min(len(numbers) * 0.05, 0.2)
        
        # Check for citations or references
        if any(word in content.lower() for word in ["study", "university", "journal", "published"]):
            score += 0.1
        
        return min(score, 1.0)
    
    def _assess_relevance(self, argument: EnhancedArgument, context: List[EnhancedArgument]) -> float:
        """Assess relevance to topic and debate context"""
        # Simple keyword-based relevance (could be enhanced with NLP)
        if not context:
            return 0.8  # Default for first arguments
        
        # Count common words with recent arguments
        recent_args = context[-3:] if len(context) >= 3 else context
        arg_words = set(argument.content.lower().split())
        
        relevance_scores = []
        for prev_arg in recent_args:
            prev_words = set(prev_arg.content.lower().split())
            overlap = len(arg_words.intersection(prev_words))
            relevance_scores.append(overlap / max(len(arg_words), len(prev_words)))
        
        return max(relevance_scores) if relevance_scores else 0.5
    
    def _assess_emotional_appeal(self, content: str) -> float:
        """Detect emotional language and appeal"""
        emotional_count = sum(1 for indicator in self.emotional_indicators 
                            if indicator.lower() in content.lower())
        
        # Check for exclamation marks and all caps
        exclamations = content.count('!')
        caps_words = sum(1 for word in content.split() if word.isupper() and len(word) > 2)
        
        score = min((emotional_count * 0.1) + (exclamations * 0.05) + (caps_words * 0.05), 1.0)
        return score
    
    def _assess_readability(self, content: str) -> float:
        """Assess readability and clarity"""
        try:
            # Flesch Reading Ease score (higher = more readable)
            flesch_score = flesch_reading_ease(content)
            # Normalize to 0-1 scale
            normalized_score = max(0, min(1, flesch_score / 100))
            return normalized_score
        except:
            # Fallback: simple sentence length analysis
            sentences = content.split('.')
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            return max(0, min(1, 1 - (avg_sentence_length - 15) / 20))
    
    def _basic_fact_check(self, content: str) -> float:
        """Basic fact-checking (placeholder for real implementation)"""
        # This would integrate with fact-checking APIs in a real system
        # For now, check for hedging language vs absolute statements
        hedging_words = ["might", "could", "possibly", "perhaps", "likely", "probably"]
        absolute_words = ["always", "never", "all", "none", "definitely", "certainly"]
        
        hedging_count = sum(1 for word in hedging_words if word in content.lower())
        absolute_count = sum(1 for word in absolute_words if word in content.lower())
        
        # Moderate claims are generally more fact-checkable
        if hedging_count > absolute_count:
            return 0.7
        elif absolute_count > hedging_count:
            return 0.4
        else:
            return 0.6
    
    def _assess_novelty(self, argument: EnhancedArgument, context: List[EnhancedArgument]) -> float:
        """Assess how novel/original the argument is"""
        if not context:
            return 0.8
        
        # Simple approach: check for repeated phrases
        arg_phrases = set(argument.content.lower().split())
        
        similarity_scores = []
        for prev_arg in context:
            if prev_arg.agent_name != argument.agent_name:  # Compare with opponents
                prev_phrases = set(prev_arg.content.lower().split())
                overlap = len(arg_phrases.intersection(prev_phrases))
                similarity = overlap / max(len(arg_phrases), len(prev_phrases))
                similarity_scores.append(similarity)
        
        avg_similarity = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0
        return max(0, 1 - avg_similarity)
    
    def _calculate_persuasiveness(self, metrics: ArgumentMetrics) -> float:
        """Calculate overall persuasiveness score"""
        weights = {
            'logical_coherence': 0.25,
            'evidence_quality': 0.25,
            'relevance_score': 0.15,
            'readability_score': 0.15,
            'fact_check_score': 0.10,
            'novelty_score': 0.10
        }
        
        score = (
            metrics.logical_coherence * weights['logical_coherence'] +
            metrics.evidence_quality * weights['evidence_quality'] +
            metrics.relevance_score * weights['relevance_score'] +
            metrics.readability_score * weights['readability_score'] +
            metrics.fact_check_score * weights['fact_check_score'] +
            metrics.novelty_score * weights['novelty_score']
        )
        
        return min(score, 1.0)

class EnhancedArgumentationAgent:
    """Enhanced AI agent with adaptive strategies and memory"""
    
    def __init__(self, name: str, personality: str, position: str):
        self.name = name
        self.personality = personality
        self.position = position
        self.memory = []
        self.strategy = "balanced"  # balanced, aggressive, defensive, evidence_heavy
        self.performance_history = defaultdict(list)
        self.opponent_analysis = {}
        self.analyzer = ArgumentAnalyzer()
    
    async def generate_argument(self, debate_state: DebateState, argument_type: ArgumentType) -> EnhancedArgument:
        """Generate enhanced argument with adaptive strategy"""
        
        # Analyze opponents and adapt strategy
        self._analyze_opponents(debate_state)
        self._adapt_strategy(debate_state)
        
        # Build comprehensive context
        context = self._build_enhanced_context(debate_state)
        
        # Create sophisticated prompt
        prompt = self._create_enhanced_prompt(debate_state.topic, context, argument_type)
        
        try:
            response = await self._call_gpt_with_retry(prompt)
            
            argument = EnhancedArgument(
                agent_name=self.name,
                position=self.position,
                content=response.strip(),
                argument_type=argument_type,
                timestamp=datetime.now().isoformat(),
                phase=debate_state.phase,
                references=self._extract_references(context),
                logical_structure=self._analyze_logical_structure(response)
            )
            
            # Analyze the argument
            argument.metrics = self.analyzer.analyze_argument(argument, debate_state.arguments)
            
            # Update memory and performance tracking
            self.memory.append(argument)
            self._update_performance_metrics(argument)
            
            return argument
            
        except Exception as e:
            logger.error(f"Error generating argument for {self.name}: {e}")
            return self._create_fallback_argument(debate_state.topic, argument_type, debate_state.phase)
    
    def _analyze_opponents(self, debate_state: DebateState):
        """Analyze opponent patterns and strengths"""
        for agent_name in debate_state.agents:
            if agent_name != self.name:
                agent_args = [arg for arg in debate_state.arguments if arg.agent_name == agent_name]
                if agent_args:
                    # Analyze opponent's average performance
                    avg_persuasiveness = sum(arg.metrics.persuasiveness for arg in agent_args) / len(agent_args)
                    dominant_style = self._identify_argument_style(agent_args)
                    
                    self.opponent_analysis[agent_name] = {
                        'avg_persuasiveness': avg_persuasiveness,
                        'dominant_style': dominant_style,
                        'weakness': self._identify_weakness(agent_args)
                    }
    
    def _adapt_strategy(self, debate_state: DebateState):
        """Adapt arguing strategy based on debate progress"""
        if debate_state.current_turn < 3:
            self.strategy = "balanced"
        elif any(analysis['avg_persuasiveness'] > 0.7 for analysis in self.opponent_analysis.values()):
            self.strategy = "aggressive"
        elif debate_state.phase == DebatePhase.REBUTTALS:
            self.strategy = "defensive"
        else:
            self.strategy = "evidence_heavy"
    
    def _identify_argument_style(self, arguments: List[EnhancedArgument]) -> str:
        """Identify opponent's dominant argument style"""
        if not arguments:
            return "unknown"
        
        avg_emotional = sum(arg.metrics.emotional_appeal for arg in arguments) / len(arguments)
        avg_evidence = sum(arg.metrics.evidence_quality for arg in arguments) / len(arguments)
        avg_logical = sum(arg.metrics.logical_coherence for arg in arguments) / len(arguments)
        
        if avg_emotional > max(avg_evidence, avg_logical):
            return "emotional"
        elif avg_evidence > avg_logical:
            return "evidence_based"
        else:
            return "logical"
    
    def _identify_weakness(self, arguments: List[EnhancedArgument]) -> str:
        """Identify opponent's primary weakness"""
        if not arguments:
            return "unknown"
        
        avg_metrics = {
            'logical_coherence': sum(arg.metrics.logical_coherence for arg in arguments) / len(arguments),
            'evidence_quality': sum(arg.metrics.evidence_quality for arg in arguments) / len(arguments),
            'fact_check_score': sum(arg.metrics.fact_check_score for arg in arguments) / len(arguments),
            'novelty_score': sum(arg.metrics.novelty_score for arg in arguments) / len(arguments)
        }
        
        return min(avg_metrics, key=avg_metrics.get)
    
    def _build_enhanced_context(self, debate_state: DebateState) -> Dict[str, Any]:
        """Build comprehensive context for argument generation"""
        recent_args = debate_state.arguments[-5:]
        opponent_args = [arg for arg in debate_state.arguments if arg.agent_name != self.name]
        
        return {
            'recent_arguments': [f"{arg.agent_name} ({arg.position}): {arg.content}" for arg in recent_args],
            'opponent_strengths': self.opponent_analysis,
            'debate_phase': debate_state.phase.value,
            'my_strategy': self.strategy,
            'turn_number': debate_state.current_turn
        }
    
    def _create_enhanced_prompt(self, topic: str, context: Dict[str, Any], argument_type: ArgumentType) -> str:
        """Create sophisticated prompt with strategy adaptation"""
        
        strategy_instructions = {
            "balanced": "Provide a well-rounded argument that balances logic, evidence, and appeal.",
            "aggressive": "Create a strong, direct argument that challenges opponents' positions firmly.",
            "defensive": "Focus on defending your position while addressing counterarguments.",
            "evidence_heavy": "Emphasize concrete evidence, data, and factual support."
        }
        
        phase_instructions = {
            DebatePhase.OPENING: "Make a compelling opening statement that establishes your position clearly.",
            DebatePhase.MAIN_ARGUMENTS: "Present your strongest arguments with supporting evidence.",
            DebatePhase.REBUTTALS: "Directly address and refute opposing arguments.",
            DebatePhase.CLOSING: "Summarize your position and make a final persuasive appeal."
        }
        
        prompt = f"""You are {self.name}, an AI agent with this personality: {self.personality}

DEBATE TOPIC: "{topic}"
YOUR POSITION: {self.position.upper()}
ARGUMENT TYPE: {argument_type.value}
CURRENT STRATEGY: {strategy_instructions.get(self.strategy, "")}
DEBATE PHASE: {phase_instructions.get(context.get('debate_phase'), "")}

RECENT DEBATE CONTEXT:
{chr(10).join(context.get('recent_arguments', []))}

OPPONENT ANALYSIS:
{json.dumps(context.get('opponent_strengths', {}), indent=2)}

Create a {argument_type.value} that:
1. Reflects your personality and strategic approach
2. Is logically structured and well-evidenced
3. Addresses recent arguments appropriately
4. Is between 75-200 words
5. Uses persuasive but professional language

Your argument:"""

        return prompt
    
    async def _call_gpt_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Call GPT with retry logic and error handling"""
        if client is None:
            raise Exception("OpenAI client not initialized")
        
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert debater participating in a structured academic debate. Provide clear, logical, and persuasive arguments."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.7,
                    presence_penalty=0.1,
                    frequency_penalty=0.1
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"GPT call attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise e
    
    def _analyze_logical_structure(self, argument_text: str) -> Dict[str, Any]:
        """Analyze the logical structure of an argument"""
        structure = {
            'premises': [],
            'conclusion': '',
            'logical_connectors': [],
            'evidence_statements': []
        }
        
        sentences = argument_text.split('.')
        
        for sentence in sentences:
            sentence = sentence.strip()
            if any(connector in sentence.lower() for connector in ['therefore', 'thus', 'hence', 'consequently']):
                structure['conclusion'] = sentence
            elif any(evidence in sentence.lower() for evidence in ['study', 'research', 'data', 'according to']):
                structure['evidence_statements'].append(sentence)
            else:
                structure['premises'].append(sentence)
        
        return structure
    
    def _extract_references(self, context: Dict[str, Any]) -> List[str]:
        """Extract references to previous arguments"""
        references = []
        recent_args = context.get('recent_arguments', [])
        
        for arg in recent_args[-3:]:  # Reference last 3 arguments
            if ":" in arg:
                agent_part = arg.split(":")[0]
                references.append(agent_part.strip())
        
        return references
    
    def _update_performance_metrics(self, argument: EnhancedArgument):
        """Track performance metrics over time"""
        self.performance_history['persuasiveness'].append(argument.metrics.persuasiveness)
        self.performance_history['evidence_quality'].append(argument.metrics.evidence_quality)
        self.performance_history['logical_coherence'].append(argument.metrics.logical_coherence)
    
    def _create_fallback_argument(self, topic: str, argument_type: ArgumentType, phase: DebatePhase) -> EnhancedArgument:
        """Create fallback argument when GPT fails"""
        fallback_content = f"I maintain my {self.position} position on {topic}. This issue requires careful consideration of all perspectives and evidence."
        
        return EnhancedArgument(
            agent_name=self.name,
            position=self.position,
            content=fallback_content,
            argument_type=argument_type,
            timestamp=datetime.now().isoformat(),
            phase=phase,
            metrics=ArgumentMetrics(persuasiveness=0.3)
        )

class EnhancedDebateModerator:
    """Advanced debate moderator with phase management and real-time analysis"""
    
    def __init__(self):
        self.analyzer = ArgumentAnalyzer()
        self.debate_rules = {
            "max_turns_per_phase": {"opening": 2, "main_arguments": 6, "rebuttals": 4, "closing": 2},
            "min_argument_length": 50,
            "max_argument_length": 200,
            "required_evidence_threshold": 0.4
        }
        self.audience_votes = defaultdict(int)
    
    async def run_enhanced_debate(self, topic: str, agents: List[EnhancedArgumentationAgent], 
                                 max_turns: int = 14) -> DebateState:
        """Run comprehensive debate with phase management"""
        
        debate_state = DebateState(
            topic=topic,
            agents=[agent.name for agent in agents],
            arguments=[],
            current_turn=0,
            max_turns=max_turns,
            phase=DebatePhase.OPENING,
            performance_metrics={agent.name: {} for agent in agents}
        )
        
        print(f"\n🎭 ENHANCED DEBATE SYSTEM")
        print(f"📋 Topic: {topic}")
        print(f"👥 Participants: {', '.join([f'{agent.name} ({agent.position})' for agent in agents])}")
        print("=" * 80)
        
        # Phase-based debate execution
        await self._run_opening_phase(debate_state, agents)
        await self._run_main_arguments_phase(debate_state, agents)
        await self._run_rebuttals_phase(debate_state, agents)
        await self._run_closing_phase(debate_state, agents)
        
        # Comprehensive analysis and winner determination
        await self._conclude_debate(debate_state, agents)
        
        return debate_state
    
    async def _run_opening_phase(self, debate_state: DebateState, agents: List[EnhancedArgumentationAgent]):
        """Opening statements phase"""
        print(f"\n🎬 OPENING PHASE")
        print("-" * 40)
        
        debate_state.phase = DebatePhase.OPENING
        max_turns = self.debate_rules["max_turns_per_phase"]["opening"]
        
        for i in range(max_turns):
            agent = agents[i % len(agents)]
            await self._execute_turn(debate_state, agent, ArgumentType.OPENING_STATEMENT)
    
    async def _run_main_arguments_phase(self, debate_state: DebateState, agents: List[EnhancedArgumentationAgent]):
        """Main arguments phase"""
        print(f"\n💪 MAIN ARGUMENTS PHASE")
        print("-" * 40)
        
        debate_state.phase = DebatePhase.MAIN_ARGUMENTS
        max_turns = self.debate_rules["max_turns_per_phase"]["main_arguments"]
        
        for i in range(max_turns):
            agent = agents[i % len(agents)]
            arg_type = ArgumentType.CLAIM if i % 2 == 0 else ArgumentType.EVIDENCE
            await self._execute_turn(debate_state, agent, arg_type)
    
    async def _run_rebuttals_phase(self, debate_state: DebateState, agents: List[EnhancedArgumentationAgent]):
        """Rebuttals phase"""
        print(f"\n⚔️ REBUTTALS PHASE")
        print("-" * 40)
        
        debate_state.phase = DebatePhase.REBUTTALS
        max_turns = self.debate_rules["max_turns_per_phase"]["rebuttals"]
        
        for i in range(max_turns):
            agent = agents[i % len(agents)]
            await self._execute_turn(debate_state, agent, ArgumentType.REBUTTAL)
    
    async def _run_closing_phase(self, debate_state: DebateState, agents: List[EnhancedArgumentationAgent]):
        """Closing statements phase"""
        print(f"\n🎯 CLOSING PHASE")
        print("-" * 40)
        
        debate_state.phase = DebatePhase.CLOSING
        max_turns = self.debate_rules["max_turns_per_phase"]["closing"]
        
        for i in range(max_turns):
            agent = agents[i % len(agents)]
            await self._execute_turn(debate_state, agent, ArgumentType.CLOSING_STATEMENT)
    
    async def _execute_turn(self, debate_state: DebateState, agent: EnhancedArgumentationAgent, 
                          arg_type: ArgumentType):
        """Execute a single debate turn with real-time analysis"""
        print(f"\n🗣️  Turn {debate_state.current_turn + 1}: {agent.name} ({agent.position}) - {arg_type.value}")
        
        # Generate argument
        argument = await agent.generate_argument(debate_state, arg_type)
        debate_state.arguments.append(argument)
        
        # Display argument with analysis
        print(f"📝 {argument.content}")
        print(f"📊 Analysis:")
        print(f"   • Persuasiveness: {argument.metrics.persuasiveness:.2f}")
        print(f"   • Evidence Quality: {argument.metrics.evidence_quality:.2f}")
        print(f"   • Logic Score: {argument.metrics.logical_coherence:.2f}")
        print(f"   • Readability: {argument.metrics.readability_score:.2f}")
        
        # Simulate audience reaction
        audience_score = self._simulate_audience_reaction(argument)
        debate_state.audience_votes[agent.name] += audience_score
        print(f"👏 Audience Impact: +{audience_score} points")
        
        debate_state.current_turn += 1
        await asyncio.sleep(1.5)  # Pause for readability
    
    def _simulate_audience_reaction(self, argument: EnhancedArgument) -> int:
        """Simulate audience reaction based on argument quality"""
        base_score = int(argument.metrics.persuasiveness * 10)
        
        # Bonus for high-quality evidence
        if argument.metrics.evidence_quality > 0.7:
            base_score += 3
        
        # Bonus for emotional appeal (audiences like some emotion)
        if 0.3 < argument.metrics.emotional_appeal < 0.7:
            base_score += 2
        
        # Add some randomness
        return max(0, base_score + random.randint(-2, 3))
    
    async def _conclude_debate(self, debate_state: DebateState, agents: List[EnhancedArgumentationAgent]):
        """Comprehensive debate conclusion with multiple winner criteria"""
        print(f"\n🏁 DEBATE CONCLUSION")
        print("=" * 80)
        
        debate_state.phase = DebatePhase.CONCLUDED
        
        # Calculate comprehensive scores
        final_scores = self._calculate_comprehensive_scores(debate_state, agents)
        
        # Determine winners by different criteria
        winners = {
            'overall': max(final_scores['overall'], key=final_scores['overall'].get),
            'audience_favorite': max(debate_state.audience_votes, key=debate_state.audience_votes.get) if debate_state.audience_votes else "None",
            'most_logical': max(final_scores['logic'], key=final_scores['logic'].get),
            'best_evidence': max(final_scores['evidence'], key=final_scores['evidence'].get)
        }
        
        debate_state.winner = winners['overall']
        
        # Display comprehensive results
        print(f"🏆 OVERALL WINNER: {winners['overall']}")
        print(f"👏 AUDIENCE FAVORITE: {winners['audience_favorite']}")
        print(f"🧠 MOST LOGICAL: {winners['most_logical']}")
        print(f"📚 BEST EVIDENCE: {winners['best_evidence']}")
        
        print(f"\n📈 FINAL SCORES:")
        for agent_name in debate_state.agents:
            print(f"   {agent_name}:")
            print(f"     Overall Score: {final_scores['overall'][agent_name]:.2f}")
            print(f"     Audience Votes: {debate_state.audience_votes[agent_name]}")
            print(f"     Logic Average: {final_scores['logic'][agent_name]:.2f}")
            print(f"     Evidence Average: {final_scores['evidence'][agent_name]:.2f}")
        
        # Generate debate summary
        debate_state.debate_summary = self._generate_debate_summary(debate_state, winners)
        
        # Update performance metrics
        self._update_final_performance_metrics(debate_state, agents)
    
    def _calculate_comprehensive_scores(self, debate_state: DebateState, agents: List[EnhancedArgumentationAgent]) -> Dict[str, Dict[str, float]]:
        """Calculate comprehensive scoring across multiple dimensions"""
        scores = {
            'overall': defaultdict(float),
            'logic': defaultdict(list),
            'evidence': defaultdict(list),
            'persuasiveness': defaultdict(list),
            'consistency': defaultdict(float)
        }
        
        for agent in agents:
            agent_args = [arg for arg in debate_state.arguments if arg.agent_name == agent.name]
            
            if agent_args:
                # Collect metrics
                logic_scores = [arg.metrics.logical_coherence for arg in agent_args]
                evidence_scores = [arg.metrics.evidence_quality for arg in agent_args]
                persuasion_scores = [arg.metrics.persuasiveness for arg in agent_args]
                
                scores['logic'][agent.name] = sum(logic_scores) / len(logic_scores)
                scores['evidence'][agent.name] = sum(evidence_scores) / len(evidence_scores)
                scores['persuasiveness'][agent.name] = sum(persuasion_scores) / len(persuasion_scores)
                
                # Calculate consistency (lower variance = higher consistency)
                import statistics
                try:
                    persuasion_variance = statistics.variance(persuasion_scores) if len(persuasion_scores) > 1 else 0
                    scores['consistency'][agent.name] = max(0, 1 - persuasion_variance)
                except:
                    scores['consistency'][agent.name] = 0.5
                
                # Overall score (weighted combination)
                scores['overall'][agent.name] = (
                    scores['logic'][agent.name] * 0.25 +
                    scores['evidence'][agent.name] * 0.25 +
                    scores['persuasiveness'][agent.name] * 0.25 +
                    scores['consistency'][agent.name] * 0.15 +
                    (debate_state.audience_votes[agent.name] / max(1, max(debate_state.audience_votes.values()))) * 0.10
                )
        
        return scores
    
    def _generate_debate_summary(self, debate_state: DebateState, winners: Dict[str, str]) -> str:
        """Generate comprehensive debate summary"""
        summary_parts = [
            f"DEBATE SUMMARY: {debate_state.topic}",
            f"Duration: {debate_state.current_turn} turns",
            f"Total Arguments: {len(debate_state.arguments)}",
            f"Winner: {winners['overall']}",
            "",
            "KEY MOMENTS:",
        ]
        
        # Find strongest arguments
        strongest_args = sorted(debate_state.arguments, 
                              key=lambda x: x.metrics.persuasiveness, reverse=True)[:3]
        
        for i, arg in enumerate(strongest_args, 1):
            summary_parts.append(f"{i}. {arg.agent_name}: {arg.content[:100]}...")
        
        return "\n".join(summary_parts)
    
    def _update_final_performance_metrics(self, debate_state: DebateState, agents: List[EnhancedArgumentationAgent]):
        """Update final performance metrics in debate state"""
        for agent in agents:
            agent_args = [arg for arg in debate_state.arguments if arg.agent_name == agent.name]
            
            if agent_args:
                metrics = {
                    'total_arguments': len(agent_args),
                    'avg_persuasiveness': sum(arg.metrics.persuasiveness for arg in agent_args) / len(agent_args),
                    'avg_evidence_quality': sum(arg.metrics.evidence_quality for arg in agent_args) / len(agent_args),
                    'avg_logical_coherence': sum(arg.metrics.logical_coherence for arg in agent_args) / len(agent_args),
                    'total_words': sum(arg.word_count for arg in agent_args),
                    'audience_impact': debate_state.audience_votes[agent.name]
                }
                
                debate_state.performance_metrics[agent.name] = metrics

class VisualizationEngine:
    """Generate visualizations for debate analysis"""
    
    @staticmethod
    def create_argument_network(debate_state: DebateState) -> str:
        """Create network visualization of argument relationships"""
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
            
            G = nx.DiGraph()
            
            # Add nodes for each argument
            for i, arg in enumerate(debate_state.arguments):
                G.add_node(i, 
                          label=f"{arg.agent_name[:3]}-{i}", 
                          agent=arg.agent_name,
                          persuasiveness=arg.metrics.persuasiveness)
            
            # Add edges for references (simplified)
            for i, arg in enumerate(debate_state.arguments):
                if i > 0:  # Connect to previous argument as a simple relationship
                    G.add_edge(i-1, i, weight=0.5)
            
            # Create visualization
            plt.figure(figsize=(12, 8))
            pos = nx.spring_layout(G)
            
            # Color nodes by agent
            colors = ['red' if G.nodes[node]['agent'] == debate_state.agents[0] else 'blue' 
                     for node in G.nodes()]
            
            # Size nodes by persuasiveness
            sizes = [G.nodes[node]['persuasiveness'] * 1000 + 200 for node in G.nodes()]
            
            nx.draw(G, pos, node_color=colors, node_size=sizes, 
                   with_labels=True, labels={i: G.nodes[i]['label'] for i in G.nodes()},
                   arrows=True, edge_color='gray', alpha=0.7)
            
            plt.title(f"Argument Network: {debate_state.topic}")
            plt.legend([f"{agent} ({pos})" for agent, pos in 
                       zip(debate_state.agents, ['Against', 'For'])])
            
            filename = f"debate_network_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            return filename
        except ImportError:
            logger.warning("Matplotlib/NetworkX not available for visualization")
            return "Visualization not available (missing dependencies)"
        except Exception as e:
            logger.error(f"Visualization error: {e}")
            return f"Visualization error: {e}"
    
    @staticmethod
    def create_performance_chart(debate_state: DebateState) -> str:
        """Create performance comparison chart"""
        try:
            import matplotlib.pyplot as plt
            
            agents = list(debate_state.performance_metrics.keys())
            metrics = ['avg_persuasiveness', 'avg_evidence_quality', 'avg_logical_coherence']
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            x = range(len(metrics))
            width = 0.35
            
            for i, agent in enumerate(agents):
                values = [debate_state.performance_metrics[agent].get(metric, 0) for metric in metrics]
                ax.bar([j + i * width for j in x], values, width, label=agent)
            
            ax.set_xlabel('Metrics')
            ax.set_ylabel('Scores')
            ax.set_title('Debate Performance Comparison')
            ax.set_xticks([j + width/2 for j in x])
            ax.set_xticklabels(['Persuasiveness', 'Evidence Quality', 'Logic'])
            ax.legend()
            ax.set_ylim(0, 1)
            
            filename = f"performance_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            return filename
        except ImportError:
            return "Performance chart not available (missing matplotlib)"
        except Exception as e:
            return f"Chart error: {e}"

class EnhancedArgumentationSystem:
    """Main enhanced system with comprehensive features"""
    
    def __init__(self):
        self.moderator = EnhancedDebateModerator()
        self.visualizer = VisualizationEngine()
        self.debate_history = []
        
        # Enhanced personality profiles
        self.agent_personalities = {
            "The Scholar": {
                "description": "Academic and evidence-based. Relies on research, studies, and peer-reviewed sources. Speaks formally and values intellectual rigor.",
                "strengths": ["evidence_quality", "logical_coherence"],
                "weaknesses": ["emotional_appeal"]
            },
            "The Pragmatist": {
                "description": "Focuses on practical implications and real-world consequences. Values what works over what sounds good in theory.",
                "strengths": ["relevance_score", "readability_score"],
                "weaknesses": ["novelty_score"]
            },
            "The Devil's Advocate": {
                "description": "Challenges assumptions and conventional wisdom. Enjoys pointing out contradictions and logical flaws.",
                "strengths": ["novelty_score", "logical_coherence"],
                "weaknesses": ["emotional_appeal"]
            },
            "The Idealist": {
                "description": "Argues from moral principles and ethical foundations. Believes in doing what's right regardless of practical concerns.",
                "strengths": ["emotional_appeal", "persuasiveness"],
                "weaknesses": ["evidence_quality"]
            },
            "The Skeptic": {
                "description": "Questions everything and demands rigorous proof. Naturally suspicious of claims and prefers hard evidence.",
                "strengths": ["fact_check_score", "logical_coherence"],
                "weaknesses": ["emotional_appeal"]
            },
            "The Populist": {
                "description": "Represents common sense and popular opinion. Speaks in accessible language and focuses on everyday concerns.",
                "strengths": ["readability_score", "emotional_appeal"],
                "weaknesses": ["evidence_quality"]
            },
            "The Economist": {
                "description": "Analyzes issues through cost-benefit analysis and market principles. Focuses on efficiency and quantifiable outcomes.",
                "strengths": ["evidence_quality", "logical_coherence"],
                "weaknesses": ["emotional_appeal"]
            },
            "The Philosopher": {
                "description": "Explores deep questions about meaning, ethics, and fundamental assumptions. Uses thought experiments and abstract reasoning.",
                "strengths": ["novelty_score", "logical_coherence"],
                "weaknesses": ["readability_score"]
            }
        }
    
    def create_enhanced_agents(self, topic: str, num_agents: int = 2) -> List[EnhancedArgumentationAgent]:
        """Create agents with enhanced personality profiles"""
        available_personalities = list(self.agent_personalities.keys())
        selected_personalities = random.sample(available_personalities, min(num_agents, len(available_personalities)))
        
        agents = []
        positions = ["for", "against"] * (num_agents // 2 + 1)
        
        for i, personality in enumerate(selected_personalities):
            personality_data = self.agent_personalities[personality]
            agent = EnhancedArgumentationAgent(
                name=personality,
                personality=personality_data["description"],
                position=positions[i]
            )
            agents.append(agent)
        
        return agents
    
    async def start_enhanced_debate(self, topic: str, num_agents: int = 2, 
                                  max_turns: int = 14, save_results: bool = True,
                                  create_visualizations: bool = True) -> DebateState:
        """Start comprehensive debate with all features"""
        
        # Validate setup
        if not self._validate_setup():
            return None
        
        print(f"🚀 INITIALIZING ENHANCED DEBATE SYSTEM")
        print(f"📊 Features: Advanced Analysis, Real-time Scoring, Visualization")
        
        # Create enhanced agents
        agents = self.create_enhanced_agents(topic, num_agents)
        
        print(f"\n👥 AGENT PROFILES:")
        for agent in agents:
            personality_data = self.agent_personalities[agent.name]
            print(f"   {agent.name} ({agent.position}):")
            print(f"     Strengths: {', '.join(personality_data['strengths'])}")
            print(f"     Focus: {personality_data['description'][:60]}...")
        
        # Run enhanced debate
        debate_state = await self.moderator.run_enhanced_debate(topic, agents, max_turns)
        
        # Post-debate analysis
        await self._post_debate_analysis(debate_state, create_visualizations)
        
        # Save results
        if save_results:
            self._save_enhanced_results(debate_state)
        
        # Update history
        self.debate_history.append(debate_state)
        
        return debate_state
    
    def _validate_setup(self) -> bool:
        """Validate system setup and requirements"""
        if not os.getenv('OPENAI_API_KEY'):
            print("❌ Error: OPENAI_API_KEY environment variable not set!")
            print("Please set your OpenAI API key:")
            print("export OPENAI_API_KEY='your-api-key-here'")
            return False
        
        if client is None:
            print("❌ Error: OpenAI client could not be initialized!")
            return False
        
        return True
    
    async def _post_debate_analysis(self, debate_state: DebateState, create_visualizations: bool = True):
        """Comprehensive post-debate analysis"""
        print(f"\n🔍 POST-DEBATE ANALYSIS")
        print("-" * 50)
        
        # Argument quality distribution
        all_persuasiveness = [arg.metrics.persuasiveness for arg in debate_state.arguments]
        print(f"📈 Argument Quality Distribution:")
        print(f"   Average Persuasiveness: {sum(all_persuasiveness)/len(all_persuasiveness):.2f}")
        print(f"   Highest Quality: {max(all_persuasiveness):.2f}")
        print(f"   Quality Range: {max(all_persuasiveness) - min(all_persuasiveness):.2f}")
        
        # Debate dynamics
        phase_stats = defaultdict(list)
        for arg in debate_state.arguments:
            phase_stats[arg.phase.value].append(arg.metrics.persuasiveness)
        
        print(f"\n📊 Phase Analysis:")
        for phase, scores in phase_stats.items():
            if scores:
                print(f"   {phase.title()}: Avg {sum(scores)/len(scores):.2f} ({len(scores)} arguments)")
        
        # Agent evolution tracking
        print(f"\n🎯 Agent Performance Evolution:")
        for agent_name in debate_state.agents:
            agent_args = [arg for arg in debate_state.arguments if arg.agent_name == agent_name]
            if len(agent_args) >= 2:
                early_avg = sum(arg.metrics.persuasiveness for arg in agent_args[:len(agent_args)//2]) / (len(agent_args)//2)
                late_avg = sum(arg.metrics.persuasiveness for arg in agent_args[len(agent_args)//2:]) / (len(agent_args) - len(agent_args)//2)
                improvement = late_avg - early_avg
                print(f"   {agent_name}: {'📈' if improvement > 0 else '📉'} {improvement:+.2f} improvement")
        
        # Create visualizations
        if create_visualizations:
            print(f"\n🎨 Generating Visualizations...")
            network_file = self.visualizer.create_argument_network(debate_state)
            performance_file = self.visualizer.create_performance_chart(debate_state)
            print(f"   Network diagram: {network_file}")
            print(f"   Performance chart: {performance_file}")
    
    def _save_enhanced_results(self, debate_state: DebateState):
        """Save comprehensive debate results"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Main debate file
        main_filename = f"enhanced_debate_{timestamp}.json"
        debate_dict = asdict(debate_state)
        
        # Convert enums to strings for JSON serialization
        def convert_enums(obj):
            if isinstance(obj, dict):
                return {key: convert_enums(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_enums(item) for item in obj]
            elif hasattr(obj, 'value'):  # Enum
                return obj.value
            else:
                return obj
        
        debate_dict = convert_enums(debate_dict)
        
        try:
            with open(main_filename, 'w') as f:
                json.dump(debate_dict, f, indent=2, default=str)
            
            # Create summary report
            summary_filename = f"debate_summary_{timestamp}.txt"
            with open(summary_filename, 'w') as f:
                f.write(debate_state.debate_summary)
                f.write(f"\n\nGenerated by Enhanced Dialogical Argumentation System")
                f.write(f"\nTimestamp: {datetime.now()}")
            
            print(f"💾 Results saved:")
            print(f"   Full data: {main_filename}")
            print(f"   Summary: {summary_filename}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            print(f"❌ Error saving results: {e}")
    
    def get_debate_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics across all debates"""
        if not self.debate_history:
            return {"message": "No debates completed yet"}
        
        stats = {
            "total_debates": len(self.debate_history),
            "total_arguments": sum(len(debate.arguments) for debate in self.debate_history),
            "average_debate_length": sum(debate.current_turn for debate in self.debate_history) / len(self.debate_history),
            "most_common_winner_traits": self._analyze_winner_patterns(),
            "personality_performance": self._analyze_personality_performance()
        }
        
        return stats
    
    def _analyze_winner_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in debate winners"""
        winners = [debate.winner for debate in self.debate_history if debate.winner]
        winner_counts = Counter(winners)
        
        return {
            "most_successful_personality": winner_counts.most_common(1)[0] if winner_counts else None,
            "win_distribution": dict(winner_counts)
        }
    
    def _analyze_personality_performance(self) -> Dict[str, Dict[str, float]]:
        """Analyze performance by personality type across all debates"""
        personality_stats = defaultdict(lambda: defaultdict(list))
        
        for debate in self.debate_history:
            for agent_name, metrics in debate.performance_metrics.items():
                for metric_name, value in metrics.items():
                    if isinstance(value, (int, float)):
                        personality_stats[agent_name][metric_name].append(value)
        
        # Calculate averages
        averaged_stats = {}
        for personality, metrics in personality_stats.items():
            averaged_stats[personality] = {
                metric: sum(values) / len(values) 
                for metric, values in metrics.items()
            }
        
        return averaged_stats

# Interactive and utility functions
def get_enhanced_user_input():
    """Get comprehensive user input for debate setup"""
    print("🎭 ENHANCED DIALOGICAL ARGUMENTATION SYSTEM")
    print("=" * 60)
    print("Features: Advanced AI Analysis • Real-time Scoring • Visualizations")
    print()
    
    topic = input("🤔 Debate topic: ")
    
    try:
        num_agents = int(input("👥 Number of agents (2-8, default 2): ") or "2")
        num_agents = max(2, min(8, num_agents))
    except ValueError:
        num_agents = 2
    
    try:
        max_turns = int(input("🔄 Maximum turns (8-20, default 14): ") or "14")
        max_turns = max(8, min(20, max_turns))
    except ValueError:
        max_turns = 14
    
    create_viz = input("🎨 Create visualizations? (y/n, default y): ").lower() != 'n'
    save_results = input("💾 Save results? (y/n, default y): ").lower() != 'n'
    
    return topic, num_agents, max_turns, create_viz, save_results

def display_system_info():
    """Display system capabilities and information"""
    print("🎭 ENHANCED DIALOGICAL ARGUMENTATION SYSTEM")
    print("=" * 60)
    print("CAPABILITIES:")
    print("• 8 Unique AI Personalities with distinct arguing styles")
    print("• Real-time Argument Quality Analysis (7 metrics)")
    print("• Phase-based Debate Structure (Opening → Arguments → Rebuttals → Closing)")
    print("• Adaptive Agent Strategies based on opponent analysis")
    print("• Live Audience Reaction Simulation")
    print("• Comprehensive Winner Determination (4 categories)")
    print("• Argument Network Visualization")
    print("• Performance Analytics and Reporting")
    print("• Debate History and Pattern Analysis")
    print()
    print("ANALYSIS METRICS:")
    print("• Logical Coherence • Evidence Quality • Relevance Score")
    print("• Emotional Appeal • Readability • Fact-check Score")
    print("• Novelty Assessment • Overall Persuasiveness")
    print()

async def run_demo_debate():
    """Run a demonstration debate with preset parameters"""
    print("🎯 RUNNING DEMONSTRATION DEBATE")
    print("Topic: 'Should artificial intelligence be regulated by government?'")
    
    system = EnhancedArgumentationSystem()
    await system.start_enhanced_debate(
        topic="Should artificial intelligence be regulated by government?",
        num_agents=4,
        max_turns=16,
        save_results=True,
        create_visualizations=True
    )

async def main():
    """Enhanced main function with multiple modes"""
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--demo":
            await run_demo_debate()
            return
        elif sys.argv[1] == "--info":
            display_system_info()
            return
        else:
            # Command line topic
            topic = " ".join(sys.argv[1:])
            num_agents, max_turns, create_viz, save_results = 2, 14, True, True
    else:
        # Interactive mode
        topic, num_agents, max_turns, create_viz, save_results = get_enhanced_user_input()
    
    # Create and run enhanced system
    system = EnhancedArgumentationSystem()
    
    debate_state = await system.start_enhanced_debate(
        topic=topic,
        num_agents=num_agents,
        max_turns=max_turns,
        save_results=save_results,
        create_visualizations=create_viz
    )
    
    if debate_state:
        print(f"\n📊 SYSTEM STATISTICS:")
        stats = system.get_debate_statistics()
        for key, value in stats.items():
            if isinstance(value, dict):
                print(f"   {key}:")
                for subkey, subvalue in value.items():
                    print(f"     {subkey}: {subvalue}")
            else:
                print(f"   {key}: {value}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Debate interrupted by user. Goodbye!")
    except Exception as e:
        logger.error(f"System error: {e}")
        print(f"\n❌ System error: {e}")
        print("Please ensure all dependencies are installed and OpenAI API key is set.")
