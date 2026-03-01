"""
Debate agents and moderator — BaseAgent integration.

DebateAgent generates arguments using an SK kernel with adaptive strategies,
opponent analysis, and 8-metric scoring. Falls back to template arguments
when LLM is unavailable.

EnhancedDebateModerator orchestrates phase-based debates (utility, not BaseAgent).

Original business logic from 1_2_7_argumentation_dialogique preserved.
Agent now inherits from BaseAgent for AgentGroupChat compatibility.
LLM calls go through Semantic Kernel instead of raw OpenAI client.
"""

import json
import logging
import random
import statistics
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import PrivateAttr
from semantic_kernel import Kernel
from semantic_kernel.contents import ChatHistory
from semantic_kernel.functions import kernel_function

from ..abc.agent_bases import BaseAgent
from .debate_definitions import (
    AGENT_PERSONALITIES,
    ArgumentMetrics,
    ArgumentType,
    DebatePhase,
    DebateState,
    EnhancedArgument,
)
from .debate_scoring import ArgumentAnalyzer

logger = logging.getLogger(__name__)


class DebatePlugin:
    """Semantic Kernel plugin exposing debate analysis functions.

    Wraps ArgumentAnalyzer and logical structure analysis
    as @kernel_function methods for use through kernel.invoke().
    """

    def __init__(self):
        self.analyzer = ArgumentAnalyzer()

    @kernel_function(
        name="analyze_argument_quality",
        description="Analyze argument quality producing 8-metric scores.",
    )
    def analyze_argument_quality(self, text: str) -> str:
        """Analyze a text argument and return quality metrics as JSON."""
        arg = EnhancedArgument(
            agent_name="analysis",
            position="neutral",
            content=text,
            argument_type=ArgumentType.CLAIM,
            timestamp=datetime.now().isoformat(),
            phase=DebatePhase.MAIN_ARGUMENTS,
        )
        metrics = self.analyzer.analyze_argument(arg, [])
        return json.dumps({
            "logical_coherence": metrics.logical_coherence,
            "evidence_quality": metrics.evidence_quality,
            "relevance_score": metrics.relevance_score,
            "persuasiveness": metrics.persuasiveness,
            "emotional_appeal": metrics.emotional_appeal,
            "fact_check_score": metrics.fact_check_score,
            "novelty_score": metrics.novelty_score,
            "readability_score": metrics.readability_score,
        })

    @kernel_function(
        name="analyze_logical_structure",
        description=(
            "Extract logical structure (premises, conclusion, evidence) "
            "from argumentative text."
        ),
    )
    def analyze_logical_structure(self, text: str) -> str:
        """Analyze logical structure and return JSON representation."""
        structure = {
            "premises": [],
            "conclusion": "",
            "logical_connectors": [],
            "evidence_statements": [],
        }
        for sentence in text.split("."):
            sentence = sentence.strip()
            if not sentence:
                continue
            if any(c in sentence.lower() for c in ["therefore", "thus", "hence"]):
                structure["conclusion"] = sentence
            elif any(
                e in sentence.lower()
                for e in ["study", "research", "data", "according"]
            ):
                structure["evidence_statements"].append(sentence)
            else:
                structure["premises"].append(sentence)
        return json.dumps(structure, ensure_ascii=False)

    @kernel_function(
        name="suggest_debate_strategy",
        description=(
            "Suggest optimal debate strategy based on phase, turn number, "
            "and opponent strength."
        ),
    )
    def suggest_debate_strategy(
        self, phase: str, turn_number: str, opponent_strength: str = "0.5"
    ) -> str:
        """Suggest a debate strategy based on context."""
        turn = int(turn_number) if turn_number.isdigit() else 0
        opp = float(opponent_strength)

        if turn < 3:
            strategy = "balanced"
        elif opp > 0.7:
            strategy = "aggressive"
        elif phase == "rebuttals":
            strategy = "defensive"
        else:
            strategy = "evidence_heavy"

        return json.dumps({"strategy": strategy})


class DebateAgent(BaseAgent):
    """Agent that generates arguments in adversarial debates.

    Inherits from BaseAgent for AgentGroupChat compatibility.
    Uses SK kernel for LLM-based argument generation with template fallback.
    Preserves all business logic from student project 1.2.7.
    """

    _plugin: DebatePlugin = PrivateAttr(default=None)
    _personality: str = PrivateAttr(default="The Scholar")
    _position: str = PrivateAttr(default="for")
    _memory: List = PrivateAttr(default_factory=list)
    _strategy: str = PrivateAttr(default="balanced")
    _performance_history: Dict = PrivateAttr(
        default_factory=lambda: defaultdict(list)
    )
    _opponent_analysis: Dict = PrivateAttr(default_factory=dict)

    def __init__(
        self,
        kernel: Kernel,
        agent_name: str = "DebateAgent",
        personality: str = "The Scholar",
        position: str = "for",
        **kwargs,
    ):
        system_prompt = (
            "You are an expert debater. You analyze arguments, adapt your "
            "strategy based on opponent analysis, and generate clear, logical, "
            "persuasive arguments using evidence and sound reasoning."
        )
        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            system_prompt=system_prompt,
            description=(
                "Generates arguments in adversarial debates with 8 personality "
                "archetypes, adaptive strategies, 8-metric scoring, and "
                "phase-based orchestration."
            ),
            **kwargs,
        )
        self._plugin = DebatePlugin()
        self._personality = personality
        self._position = position
        self._memory = []
        self._strategy = "balanced"
        self._performance_history = defaultdict(list)
        self._opponent_analysis = {}

    @property
    def analyzer(self) -> ArgumentAnalyzer:
        """Access the argument analyzer."""
        return self._plugin.analyzer

    @property
    def personality(self) -> str:
        """Access the agent's personality."""
        return self._personality

    @property
    def position(self) -> str:
        """Access the agent's debate position."""
        return self._position

    @property
    def memory(self) -> List[EnhancedArgument]:
        """Access the agent's argument memory."""
        return self._memory

    @property
    def strategy(self) -> str:
        """Access the current debate strategy."""
        return self._strategy

    @strategy.setter
    def strategy(self, value: str):
        """Set the debate strategy."""
        self._strategy = value

    @property
    def opponent_analysis(self) -> Dict[str, Dict[str, Any]]:
        """Access opponent analysis data."""
        return self._opponent_analysis

    @property
    def performance_history(self) -> Dict:
        """Access performance history."""
        return self._performance_history

    def setup_agent_components(self, llm_service_id: Optional[str] = None) -> None:
        """Register the DebatePlugin with the kernel."""
        if llm_service_id:
            self._llm_service_id = llm_service_id
        self.kernel.add_plugin(self._plugin, plugin_name="debate")
        self.logger.info("DebatePlugin registered with kernel")

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Describe agent capabilities."""
        return {
            "adversarial_debate": True,
            "argument_generation": True,
            "strategy_adaptation": True,
            "opponent_analysis": True,
            "argument_scoring": True,
            "personalities": list(AGENT_PERSONALITIES.keys()),
            "phases": [p.value for p in DebatePhase],
            "argument_types": [t.value for t in ArgumentType],
        }

    async def get_response(self, *args, **kwargs):
        """Compatibility wrapper -- delegates to invoke_single."""
        if args and isinstance(args[0], str):
            return await self.invoke_single(args[0], **kwargs)
        if args and isinstance(args[0], list):
            last_msg = args[0][-1] if args[0] else None
            text = str(last_msg.content) if last_msg else ""
            return await self.invoke_single(text, **kwargs)
        return await self.invoke_single(**kwargs)

    async def invoke_single(self, text: str = "", **kwargs) -> Dict[str, Any]:
        """Run argument generation on input text.

        Args:
            text: Topic or prompt for argument generation.
            **kwargs: Optional debate_state, argument_type overrides.

        Returns:
            Dict with argument, metrics, strategy.
        """
        topic = text or kwargs.get("topic", "")
        if not topic:
            return {"error": "No topic provided"}

        argument_type = kwargs.get("argument_type", ArgumentType.CLAIM)
        debate_state = kwargs.get("debate_state")
        if debate_state is None:
            debate_state = DebateState(
                topic=topic,
                agents=[self.name],
                arguments=[],
                current_turn=0,
                max_turns=10,
                phase=DebatePhase.MAIN_ARGUMENTS,
            )

        argument = await self.generate_argument(debate_state, argument_type)
        return {
            "argument": argument,
            "metrics": argument.metrics,
            "strategy": self._strategy,
        }

    async def generate_argument(
        self, debate_state: DebateState, argument_type: ArgumentType
    ) -> EnhancedArgument:
        """Generate an argument using LLM with adaptive strategy."""
        self._analyze_opponents(debate_state)
        self._adapt_strategy(debate_state)
        context = self._build_enhanced_context(debate_state)
        prompt = self._create_enhanced_prompt(
            debate_state.topic, context, argument_type
        )

        try:
            response = await self._generate_via_kernel(prompt)
            argument = EnhancedArgument(
                agent_name=self.name,
                position=self._position,
                content=response.strip(),
                argument_type=argument_type,
                timestamp=datetime.now().isoformat(),
                phase=debate_state.phase,
                references=self._extract_references(context),
                logical_structure=self._analyze_logical_structure(response),
            )
            argument.metrics = self.analyzer.analyze_argument(
                argument, debate_state.arguments
            )
            self._memory.append(argument)
            self._update_performance_metrics(argument)
            return argument
        except Exception as e:
            self.logger.warning(f"LLM call failed for {self.name}: {e}")
            return self._create_fallback_argument(
                debate_state.topic, argument_type, debate_state.phase
            )

    async def _generate_via_kernel(self, prompt: str) -> str:
        """Generate argument content via SK kernel's chat service."""
        service = self.kernel.get_service(self._llm_service_id)
        if not hasattr(service, "get_chat_message_contents"):
            raise RuntimeError(
                f"Service {getattr(service, 'service_id', '?')} "
                f"does not support chat completion"
            )

        history = ChatHistory()
        history.add_system_message(self.instructions)
        history.add_user_message(prompt)

        try:
            settings_class = service.get_prompt_execution_settings_class()
            settings = settings_class(service_id=service.service_id)
        except Exception:
            settings = None

        results = await service.get_chat_message_contents(
            chat_history=history,
            settings=settings,
        )

        if results and results[0].content:
            return results[0].content.strip()
        raise RuntimeError("Empty LLM response")

    def _analyze_opponents(self, debate_state: DebateState):
        for agent_name in debate_state.agents:
            if agent_name != self.name:
                agent_args = [
                    arg
                    for arg in debate_state.arguments
                    if arg.agent_name == agent_name
                ]
                if agent_args:
                    avg_persuasiveness = sum(
                        arg.metrics.persuasiveness for arg in agent_args
                    ) / len(agent_args)
                    self._opponent_analysis[agent_name] = {
                        "avg_persuasiveness": avg_persuasiveness,
                        "dominant_style": self._identify_style(agent_args),
                        "weakness": self._identify_weakness(agent_args),
                    }

    def _adapt_strategy(self, debate_state: DebateState):
        if debate_state.current_turn < 3:
            self._strategy = "balanced"
        elif any(
            a["avg_persuasiveness"] > 0.7
            for a in self._opponent_analysis.values()
        ):
            self._strategy = "aggressive"
        elif debate_state.phase == DebatePhase.REBUTTALS:
            self._strategy = "defensive"
        else:
            self._strategy = "evidence_heavy"

    def _identify_style(self, arguments: List[EnhancedArgument]) -> str:
        if not arguments:
            return "unknown"
        avg_emotional = sum(
            a.metrics.emotional_appeal for a in arguments
        ) / len(arguments)
        avg_evidence = sum(
            a.metrics.evidence_quality for a in arguments
        ) / len(arguments)
        avg_logical = sum(
            a.metrics.logical_coherence for a in arguments
        ) / len(arguments)
        if avg_emotional > max(avg_evidence, avg_logical):
            return "emotional"
        elif avg_evidence > avg_logical:
            return "evidence_based"
        return "logical"

    def _identify_weakness(self, arguments: List[EnhancedArgument]) -> str:
        if not arguments:
            return "unknown"
        avg = {
            "logical_coherence": sum(
                a.metrics.logical_coherence for a in arguments
            ) / len(arguments),
            "evidence_quality": sum(
                a.metrics.evidence_quality for a in arguments
            ) / len(arguments),
            "fact_check_score": sum(
                a.metrics.fact_check_score for a in arguments
            ) / len(arguments),
            "novelty_score": sum(
                a.metrics.novelty_score for a in arguments
            ) / len(arguments),
        }
        return min(avg, key=avg.get)

    def _build_enhanced_context(
        self, debate_state: DebateState
    ) -> Dict[str, Any]:
        recent_args = debate_state.arguments[-5:]
        return {
            "recent_arguments": [
                f"{arg.agent_name} ({arg.position}): {arg.content}"
                for arg in recent_args
            ],
            "opponent_strengths": self._opponent_analysis,
            "debate_phase": debate_state.phase.value,
            "my_strategy": self._strategy,
            "turn_number": debate_state.current_turn,
        }

    def _create_enhanced_prompt(
        self,
        topic: str,
        context: Dict[str, Any],
        argument_type: ArgumentType,
    ) -> str:
        strategy_instructions = {
            "balanced": (
                "Provide a well-rounded argument balancing logic, "
                "evidence, and appeal."
            ),
            "aggressive": (
                "Create a strong, direct argument challenging opponents."
            ),
            "defensive": (
                "Focus on defending your position while addressing "
                "counterarguments."
            ),
            "evidence_heavy": (
                "Emphasize concrete evidence, data, and factual support."
            ),
        }
        phase_instructions = {
            "opening": "Make a compelling opening statement.",
            "main_arguments": (
                "Present your strongest arguments with evidence."
            ),
            "rebuttals": (
                "Directly address and refute opposing arguments."
            ),
            "closing": (
                "Summarize your position with a final persuasive appeal."
            ),
        }
        recent = "\n".join(context.get("recent_arguments", []))
        return (
            f"You are {self.name}, personality: {self._personality}\n"
            f'TOPIC: "{topic}"\n'
            f"POSITION: {self._position.upper()}\n"
            f"TYPE: {argument_type.value}\n"
            f"STRATEGY: {strategy_instructions.get(self._strategy, '')}\n"
            f"PHASE: {phase_instructions.get(context.get('debate_phase'), '')}\n"
            f"RECENT:\n{recent}\n\n"
            f"Create a {argument_type.value} (75-200 words):"
        )

    def _analyze_logical_structure(self, text: str) -> Dict[str, Any]:
        structure = {
            "premises": [],
            "conclusion": "",
            "logical_connectors": [],
            "evidence_statements": [],
        }
        for sentence in text.split("."):
            sentence = sentence.strip()
            if not sentence:
                continue
            if any(
                c in sentence.lower()
                for c in ["therefore", "thus", "hence"]
            ):
                structure["conclusion"] = sentence
            elif any(
                e in sentence.lower()
                for e in ["study", "research", "data", "according"]
            ):
                structure["evidence_statements"].append(sentence)
            else:
                structure["premises"].append(sentence)
        return structure

    def _extract_references(self, context: Dict[str, Any]) -> List[str]:
        references = []
        for arg in context.get("recent_arguments", [])[-3:]:
            if ":" in arg:
                references.append(arg.split(":")[0].strip())
        return references

    def _update_performance_metrics(self, argument: EnhancedArgument):
        self._performance_history["persuasiveness"].append(
            argument.metrics.persuasiveness
        )
        self._performance_history["evidence_quality"].append(
            argument.metrics.evidence_quality
        )
        self._performance_history["logical_coherence"].append(
            argument.metrics.logical_coherence
        )

    def _create_fallback_argument(
        self,
        topic: str,
        argument_type: ArgumentType,
        phase: DebatePhase,
    ) -> EnhancedArgument:
        content = (
            f"I maintain my {self._position} position on {topic}. "
            f"This issue requires careful consideration of all perspectives."
        )
        return EnhancedArgument(
            agent_name=self.name,
            position=self._position,
            content=content,
            argument_type=argument_type,
            timestamp=datetime.now().isoformat(),
            phase=phase,
            metrics=ArgumentMetrics(persuasiveness=0.3),
        )


# Backward compatibility alias
EnhancedArgumentationAgent = DebateAgent


class EnhancedDebateModerator:
    """Phase-based debate moderator with real-time scoring and audience simulation.

    Utility class (not a BaseAgent). Orchestrates DebateAgent instances
    through debate phases with audience simulation and winner determination.
    """

    def __init__(self):
        self.analyzer = ArgumentAnalyzer()
        self.debate_rules = {
            "max_turns_per_phase": {
                "opening": 2,
                "main_arguments": 6,
                "rebuttals": 4,
                "closing": 2,
            },
            "min_argument_length": 50,
            "max_argument_length": 200,
            "required_evidence_threshold": 0.4,
        }
        self.audience_votes = defaultdict(int)

    async def run_debate(
        self,
        topic: str,
        agents: List[DebateAgent],
        max_turns: int = 14,
    ) -> DebateState:
        """Run a complete phase-based debate."""
        debate_state = DebateState(
            topic=topic,
            agents=[agent.name for agent in agents],
            arguments=[],
            current_turn=0,
            max_turns=max_turns,
            phase=DebatePhase.OPENING,
            performance_metrics={agent.name: {} for agent in agents},
        )

        for phase_name, phase_enum, arg_types in [
            ("opening", DebatePhase.OPENING, [ArgumentType.OPENING_STATEMENT]),
            (
                "main_arguments",
                DebatePhase.MAIN_ARGUMENTS,
                [ArgumentType.CLAIM, ArgumentType.EVIDENCE],
            ),
            ("rebuttals", DebatePhase.REBUTTALS, [ArgumentType.REBUTTAL]),
            (
                "closing",
                DebatePhase.CLOSING,
                [ArgumentType.CLOSING_STATEMENT],
            ),
        ]:
            debate_state.phase = phase_enum
            turns = self.debate_rules["max_turns_per_phase"][phase_name]
            for i in range(turns):
                agent = agents[i % len(agents)]
                arg_type = arg_types[i % len(arg_types)]
                argument = await agent.generate_argument(
                    debate_state, arg_type
                )
                debate_state.arguments.append(argument)
                audience_score = self._simulate_audience_reaction(argument)
                debate_state.audience_votes[agent.name] += audience_score
                debate_state.current_turn += 1

        self._conclude_debate(debate_state, agents)
        return debate_state

    def _simulate_audience_reaction(
        self, argument: EnhancedArgument
    ) -> int:
        base_score = int(argument.metrics.persuasiveness * 10)
        if argument.metrics.evidence_quality > 0.7:
            base_score += 3
        if 0.3 < argument.metrics.emotional_appeal < 0.7:
            base_score += 2
        return max(0, base_score + random.randint(-2, 3))

    def _conclude_debate(
        self,
        debate_state: DebateState,
        agents: List[DebateAgent],
    ):
        debate_state.phase = DebatePhase.CONCLUDED
        final_scores = self._calculate_scores(debate_state, agents)
        if final_scores["overall"]:
            debate_state.winner = max(
                final_scores["overall"],
                key=final_scores["overall"].get,
            )
        self._update_performance_metrics(debate_state, agents)

    def _calculate_scores(
        self,
        debate_state: DebateState,
        agents: List[DebateAgent],
    ) -> Dict[str, Dict[str, float]]:
        scores = {
            "overall": defaultdict(float),
            "logic": defaultdict(float),
            "evidence": defaultdict(float),
            "persuasiveness": defaultdict(float),
            "consistency": defaultdict(float),
        }
        for agent in agents:
            agent_args = [
                arg
                for arg in debate_state.arguments
                if arg.agent_name == agent.name
            ]
            if not agent_args:
                continue
            logic = [a.metrics.logical_coherence for a in agent_args]
            evidence = [a.metrics.evidence_quality for a in agent_args]
            persuasion = [a.metrics.persuasiveness for a in agent_args]

            scores["logic"][agent.name] = sum(logic) / len(logic)
            scores["evidence"][agent.name] = sum(evidence) / len(evidence)
            scores["persuasiveness"][agent.name] = (
                sum(persuasion) / len(persuasion)
            )

            try:
                variance = (
                    statistics.variance(persuasion)
                    if len(persuasion) > 1
                    else 0
                )
                scores["consistency"][agent.name] = max(0, 1 - variance)
            except Exception:
                scores["consistency"][agent.name] = 0.5

            max_audience = (
                max(debate_state.audience_votes.values())
                if debate_state.audience_votes
                else 1
            )
            scores["overall"][agent.name] = (
                scores["logic"][agent.name] * 0.25
                + scores["evidence"][agent.name] * 0.25
                + scores["persuasiveness"][agent.name] * 0.25
                + scores["consistency"][agent.name] * 0.15
                + (
                    debate_state.audience_votes.get(agent.name, 0)
                    / max(1, max_audience)
                )
                * 0.10
            )
        return scores

    def _update_performance_metrics(
        self,
        debate_state: DebateState,
        agents: List[DebateAgent],
    ):
        for agent in agents:
            agent_args = [
                arg
                for arg in debate_state.arguments
                if arg.agent_name == agent.name
            ]
            if agent_args:
                debate_state.performance_metrics[agent.name] = {
                    "total_arguments": len(agent_args),
                    "avg_persuasiveness": sum(
                        a.metrics.persuasiveness for a in agent_args
                    )
                    / len(agent_args),
                    "avg_evidence_quality": sum(
                        a.metrics.evidence_quality for a in agent_args
                    )
                    / len(agent_args),
                    "avg_logical_coherence": sum(
                        a.metrics.logical_coherence for a in agent_args
                    )
                    / len(agent_args),
                    "total_words": sum(a.word_count for a in agent_args),
                }
