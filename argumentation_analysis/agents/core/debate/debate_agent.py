"""
Debate agents and moderator — LLM-powered debate with adaptive strategies.

EnhancedArgumentationAgent generates arguments using an LLM service
(via ServiceDiscovery) while adapting strategy based on opponent analysis.

EnhancedDebateModerator orchestrates phase-based debates with real-time
scoring and audience simulation.

Extracted and adapted from enhanced_argumentation_main.py.
LLM calls abstracted through ServiceDiscovery (replaces hardcoded gpt-3.5-turbo).
"""

import asyncio
import json
import logging
import random
import statistics
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

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


class EnhancedArgumentationAgent:
    """AI debate agent with adaptive strategies and performance tracking.

    Uses ServiceDiscovery for LLM access (replacing hardcoded gpt-3.5-turbo).
    Falls back to generic arguments when LLM is unavailable.
    """

    def __init__(
        self,
        name: str,
        personality: str,
        position: str,
        llm_client=None,
    ):
        self.name = name
        self.personality = personality
        self.position = position
        self.memory: List[EnhancedArgument] = []
        self.strategy = "balanced"
        self.performance_history = defaultdict(list)
        self.opponent_analysis: Dict[str, Dict[str, Any]] = {}
        self.analyzer = ArgumentAnalyzer()
        self._llm_client = llm_client

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
            response = await self._call_llm(prompt)
            argument = EnhancedArgument(
                agent_name=self.name,
                position=self.position,
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
            self.memory.append(argument)
            self._update_performance_metrics(argument)
            return argument
        except Exception as e:
            logger.warning(f"LLM call failed for {self.name}: {e}")
            return self._create_fallback_argument(
                debate_state.topic, argument_type, debate_state.phase
            )

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
                    self.opponent_analysis[agent_name] = {
                        "avg_persuasiveness": avg_persuasiveness,
                        "dominant_style": self._identify_style(agent_args),
                        "weakness": self._identify_weakness(agent_args),
                    }

    def _adapt_strategy(self, debate_state: DebateState):
        if debate_state.current_turn < 3:
            self.strategy = "balanced"
        elif any(
            a["avg_persuasiveness"] > 0.7 for a in self.opponent_analysis.values()
        ):
            self.strategy = "aggressive"
        elif debate_state.phase == DebatePhase.REBUTTALS:
            self.strategy = "defensive"
        else:
            self.strategy = "evidence_heavy"

    def _identify_style(self, arguments: List[EnhancedArgument]) -> str:
        if not arguments:
            return "unknown"
        avg_emotional = sum(a.metrics.emotional_appeal for a in arguments) / len(
            arguments
        )
        avg_evidence = sum(a.metrics.evidence_quality for a in arguments) / len(
            arguments
        )
        avg_logical = sum(a.metrics.logical_coherence for a in arguments) / len(
            arguments
        )
        if avg_emotional > max(avg_evidence, avg_logical):
            return "emotional"
        elif avg_evidence > avg_logical:
            return "evidence_based"
        return "logical"

    def _identify_weakness(self, arguments: List[EnhancedArgument]) -> str:
        if not arguments:
            return "unknown"
        avg = {
            "logical_coherence": sum(a.metrics.logical_coherence for a in arguments)
            / len(arguments),
            "evidence_quality": sum(a.metrics.evidence_quality for a in arguments)
            / len(arguments),
            "fact_check_score": sum(a.metrics.fact_check_score for a in arguments)
            / len(arguments),
            "novelty_score": sum(a.metrics.novelty_score for a in arguments)
            / len(arguments),
        }
        return min(avg, key=avg.get)

    def _build_enhanced_context(self, debate_state: DebateState) -> Dict[str, Any]:
        recent_args = debate_state.arguments[-5:]
        return {
            "recent_arguments": [
                f"{arg.agent_name} ({arg.position}): {arg.content}"
                for arg in recent_args
            ],
            "opponent_strengths": self.opponent_analysis,
            "debate_phase": debate_state.phase.value,
            "my_strategy": self.strategy,
            "turn_number": debate_state.current_turn,
        }

    def _create_enhanced_prompt(
        self, topic: str, context: Dict[str, Any], argument_type: ArgumentType
    ) -> str:
        strategy_instructions = {
            "balanced": "Provide a well-rounded argument balancing logic, evidence, and appeal.",
            "aggressive": "Create a strong, direct argument challenging opponents.",
            "defensive": "Focus on defending your position while addressing counterarguments.",
            "evidence_heavy": "Emphasize concrete evidence, data, and factual support.",
        }
        phase_instructions = {
            "opening": "Make a compelling opening statement.",
            "main_arguments": "Present your strongest arguments with evidence.",
            "rebuttals": "Directly address and refute opposing arguments.",
            "closing": "Summarize your position with a final persuasive appeal.",
        }
        recent = "\n".join(context.get("recent_arguments", []))
        return (
            f"You are {self.name}, personality: {self.personality}\n"
            f'TOPIC: "{topic}"\n'
            f"POSITION: {self.position.upper()}\n"
            f"TYPE: {argument_type.value}\n"
            f"STRATEGY: {strategy_instructions.get(self.strategy, '')}\n"
            f"PHASE: {phase_instructions.get(context.get('debate_phase'), '')}\n"
            f"RECENT:\n{recent}\n\n"
            f"Create a {argument_type.value} (75-200 words):"
        )

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM via injected client or raise if unavailable."""
        if self._llm_client is None:
            raise RuntimeError("No LLM client available")
        # Support both sync and async clients
        if asyncio.iscoroutinefunction(
            getattr(self._llm_client, "chat_completion", None)
        ):
            response = await self._llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert debater. Provide clear, logical, persuasive arguments.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            return response
        # Sync fallback (openai-compatible client)
        try:
            response = self._llm_client.chat.completions.create(
                model=getattr(self._llm_client, "_model", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert debater. Provide clear, logical, persuasive arguments.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"LLM call failed: {e}") from e

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
            if any(c in sentence.lower() for c in ["therefore", "thus", "hence"]):
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
        self.performance_history["persuasiveness"].append(
            argument.metrics.persuasiveness
        )
        self.performance_history["evidence_quality"].append(
            argument.metrics.evidence_quality
        )
        self.performance_history["logical_coherence"].append(
            argument.metrics.logical_coherence
        )

    def _create_fallback_argument(
        self, topic: str, argument_type: ArgumentType, phase: DebatePhase
    ) -> EnhancedArgument:
        content = (
            f"I maintain my {self.position} position on {topic}. "
            f"This issue requires careful consideration of all perspectives."
        )
        return EnhancedArgument(
            agent_name=self.name,
            position=self.position,
            content=content,
            argument_type=argument_type,
            timestamp=datetime.now().isoformat(),
            phase=phase,
            metrics=ArgumentMetrics(persuasiveness=0.3),
        )


class EnhancedDebateModerator:
    """Phase-based debate moderator with real-time scoring and audience simulation."""

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
        agents: List[EnhancedArgumentationAgent],
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
            ("closing", DebatePhase.CLOSING, [ArgumentType.CLOSING_STATEMENT]),
        ]:
            debate_state.phase = phase_enum
            turns = self.debate_rules["max_turns_per_phase"][phase_name]
            for i in range(turns):
                agent = agents[i % len(agents)]
                arg_type = arg_types[i % len(arg_types)]
                argument = await agent.generate_argument(debate_state, arg_type)
                debate_state.arguments.append(argument)
                audience_score = self._simulate_audience_reaction(argument)
                debate_state.audience_votes[agent.name] += audience_score
                debate_state.current_turn += 1

        self._conclude_debate(debate_state, agents)
        return debate_state

    def _simulate_audience_reaction(self, argument: EnhancedArgument) -> int:
        base_score = int(argument.metrics.persuasiveness * 10)
        if argument.metrics.evidence_quality > 0.7:
            base_score += 3
        if 0.3 < argument.metrics.emotional_appeal < 0.7:
            base_score += 2
        return max(0, base_score + random.randint(-2, 3))

    def _conclude_debate(
        self,
        debate_state: DebateState,
        agents: List[EnhancedArgumentationAgent],
    ):
        debate_state.phase = DebatePhase.CONCLUDED
        final_scores = self._calculate_scores(debate_state, agents)
        if final_scores["overall"]:
            debate_state.winner = max(
                final_scores["overall"], key=final_scores["overall"].get
            )
        self._update_performance_metrics(debate_state, agents)

    def _calculate_scores(
        self, debate_state: DebateState, agents: List[EnhancedArgumentationAgent]
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
                arg for arg in debate_state.arguments if arg.agent_name == agent.name
            ]
            if not agent_args:
                continue
            logic = [a.metrics.logical_coherence for a in agent_args]
            evidence = [a.metrics.evidence_quality for a in agent_args]
            persuasion = [a.metrics.persuasiveness for a in agent_args]

            scores["logic"][agent.name] = sum(logic) / len(logic)
            scores["evidence"][agent.name] = sum(evidence) / len(evidence)
            scores["persuasiveness"][agent.name] = sum(persuasion) / len(persuasion)

            try:
                variance = statistics.variance(persuasion) if len(persuasion) > 1 else 0
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
        self, debate_state: DebateState, agents: List[EnhancedArgumentationAgent]
    ):
        for agent in agents:
            agent_args = [
                arg for arg in debate_state.arguments if arg.agent_name == agent.name
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
