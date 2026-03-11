"""
Counter-argument generation agent -- BaseAgent integration.

Orchestrates the counter-argument pipeline: parse argument structure,
identify vulnerabilities, select rhetorical strategy, generate counter-argument
(via SK kernel or template fallback), and evaluate quality.

Original business logic from 2.3.3-generation-contre-argument preserved.
Agent now inherits from BaseAgent for AgentGroupChat compatibility.
LLM calls go through Semantic Kernel instead of raw OpenAI client.
"""

import json
import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from pydantic import PrivateAttr
from semantic_kernel import Kernel
from semantic_kernel.contents import ChatHistory
from semantic_kernel.functions import kernel_function

from ..abc.agent_bases import BaseAgent
from .definitions import (
    Argument,
    ArgumentStrength,
    CounterArgument,
    CounterArgumentType,
    EvaluationResult,
    RhetoricalStrategy,
    Vulnerability,
)
from .evaluator import CounterArgumentEvaluator
from .parser import ArgumentParser
from .strategies import RhetoricalStrategies

logger = logging.getLogger(__name__)


def _json_default(obj):
    """JSON serializer for enums and other non-serializable types."""
    if hasattr(obj, "value"):
        return obj.value
    return str(obj)


class CounterArgumentPlugin:
    """Semantic Kernel plugin exposing counter-argument analysis functions.

    Wraps ArgumentParser, RhetoricalStrategies, and CounterArgumentEvaluator
    as @kernel_function methods for use through kernel.invoke().
    """

    def __init__(self):
        self.parser = ArgumentParser()
        self.strategies = RhetoricalStrategies()
        self.evaluator = CounterArgumentEvaluator()

    @kernel_function(
        name="parse_argument",
        description=(
            "Parse French argumentative text into structured components "
            "(premises, conclusion, type, confidence)."
        ),
    )
    def parse_argument(self, text: str) -> str:
        """Parse argument and return JSON representation."""
        argument = self.parser.parse_argument(text)
        return json.dumps(asdict(argument), ensure_ascii=False)

    @kernel_function(
        name="identify_vulnerabilities",
        description="Identify logical vulnerabilities in argumentative text.",
    )
    def identify_vulnerabilities(self, text: str) -> str:
        """Parse text, analyze for vulnerabilities, return JSON list."""
        argument = self.parser.parse_argument(text)
        vulns = self.parser.identify_vulnerabilities(argument)
        return json.dumps(
            [asdict(v) for v in vulns], ensure_ascii=False, default=_json_default
        )

    @kernel_function(
        name="suggest_strategy",
        description="Suggest best rhetorical strategy for countering an argument.",
    )
    def suggest_strategy(self, text: str) -> str:
        """Analyze text and suggest optimal counter-argument strategy."""
        argument = self.parser.parse_argument(text)
        strategy = self.strategies.suggest_strategy(
            argument.argument_type, argument.content
        )
        return json.dumps({"strategy": strategy.value}, ensure_ascii=False)


class CounterArgumentAgent(BaseAgent):
    """Agent that generates and evaluates counter-arguments.

    Inherits from BaseAgent for AgentGroupChat compatibility.
    Uses SK kernel for LLM-based generation with template fallback.
    Preserves all business logic from student project 2.3.3.
    """

    _plugin: CounterArgumentPlugin = PrivateAttr(default=None)

    def __init__(
        self,
        kernel: Kernel,
        agent_name: str = "CounterArgumentAgent",
        **kwargs,
    ):
        system_prompt = (
            "You are an expert in argumentation and critical thinking. "
            "You analyze arguments, identify logical vulnerabilities, "
            "and generate precise, well-structured counter-arguments "
            "using appropriate rhetorical strategies."
        )
        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            system_prompt=system_prompt,
            description=(
                "Generates counter-arguments using 5 rhetorical strategies, "
                "with argument parsing, vulnerability analysis, and quality "
                "evaluation."
            ),
            **kwargs,
        )
        self._plugin = CounterArgumentPlugin()

    @property
    def parser(self) -> ArgumentParser:
        """Access the argument parser."""
        return self._plugin.parser

    @property
    def strategies(self) -> RhetoricalStrategies:
        """Access the rhetorical strategies manager."""
        return self._plugin.strategies

    @property
    def evaluator(self) -> CounterArgumentEvaluator:
        """Access the quality evaluator."""
        return self._plugin.evaluator

    def setup_agent_components(self, llm_service_id: Optional[str] = None) -> None:
        """Register the CounterArgumentPlugin with the kernel."""
        if llm_service_id:
            self._llm_service_id = llm_service_id
        self.kernel.add_plugin(self._plugin, plugin_name="counter_argument")
        self.logger.info("CounterArgumentPlugin registered with kernel")

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Describe agent capabilities."""
        return {
            "counter_argument_generation": True,
            "argument_parsing": True,
            "vulnerability_analysis": True,
            "rhetorical_strategy_selection": True,
            "counter_argument_evaluation": True,
            "strategies": [s.value for s in RhetoricalStrategy],
            "counter_types": [t.value for t in CounterArgumentType],
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
        """Run the full counter-argument pipeline on input text.

        Args:
            text: Argument text to analyze and counter.
            **kwargs: Optional counter_type, strategy overrides.

        Returns:
            Dict with argument, vulnerabilities, counter_argument, evaluation.
        """
        argument_text = text or kwargs.get("argument_text", "")
        if not argument_text:
            return {"error": "No argument text provided"}

        return await self.generate_counter_argument(
            argument_text,
            counter_type=kwargs.get("counter_type"),
            strategy=kwargs.get("strategy"),
        )

    async def generate_counter_argument(
        self,
        argument_text: str,
        counter_type: Optional[CounterArgumentType] = None,
        strategy: Optional[RhetoricalStrategy] = None,
    ) -> Dict[str, Any]:
        """Generate a counter-argument for the given text.

        Args:
            argument_text: The argument text to counter.
            counter_type: Specific counter-argument type, or auto-select.
            strategy: Specific rhetorical strategy, or auto-select.

        Returns:
            Dict with keys: argument, vulnerabilities, counter_argument,
            evaluation.
        """
        # 1. Parse argument structure
        argument = self.parser.parse_argument(argument_text)

        # 2. Identify vulnerabilities
        vulnerabilities = self.parser.identify_vulnerabilities(argument)

        # 3. Select counter type from best vulnerability
        if counter_type is None:
            counter_type = self._select_counter_type(vulnerabilities)

        # 4. Select strategy
        if strategy is None:
            strategy = self.strategies.get_best_strategy(argument, counter_type)

        # 5. Generate counter-argument content (LLM or template fallback)
        counter_content = await self._generate_content(
            argument, vulnerabilities, counter_type, strategy
        )

        # 6. Build CounterArgument object
        counter_arg = CounterArgument(
            original_argument=argument,
            counter_type=counter_type,
            counter_content=counter_content,
            target_component=self._get_target(vulnerabilities),
            strength=self._assess_strength(counter_content),
            confidence=argument.confidence * 0.8,
            supporting_evidence=[],
            rhetorical_strategy=strategy.value,
        )

        # 7. Evaluate quality
        evaluation = self.evaluator.evaluate(argument, counter_arg)

        return {
            "argument": argument,
            "vulnerabilities": vulnerabilities,
            "counter_argument": counter_arg,
            "evaluation": evaluation,
        }

    async def generate_multiple(
        self,
        argument_text: str,
        count: int = 3,
    ) -> List[Dict[str, Any]]:
        """Generate multiple counter-arguments with different strategies."""
        argument = self.parser.parse_argument(argument_text)
        vulnerabilities = self.parser.identify_vulnerabilities(argument)

        all_strategies = [
            RhetoricalStrategy.SOCRATIC_QUESTIONING,
            RhetoricalStrategy.REDUCTIO_AD_ABSURDUM,
            RhetoricalStrategy.STATISTICAL_EVIDENCE,
            RhetoricalStrategy.ANALOGICAL_COUNTER,
            RhetoricalStrategy.AUTHORITY_APPEAL,
        ]

        results = []
        for i in range(min(count, len(all_strategies))):
            strat = all_strategies[i]
            counter_type = self._select_counter_type(vulnerabilities)
            content = await self._generate_content(
                argument, vulnerabilities, counter_type, strat
            )
            counter_arg = CounterArgument(
                original_argument=argument,
                counter_type=counter_type,
                counter_content=content,
                target_component=self._get_target(vulnerabilities),
                strength=self._assess_strength(content),
                confidence=argument.confidence * 0.8,
                rhetorical_strategy=strat.value,
            )
            evaluation = self.evaluator.evaluate(argument, counter_arg)
            results.append(
                {
                    "argument": argument,
                    "vulnerabilities": vulnerabilities,
                    "counter_argument": counter_arg,
                    "evaluation": evaluation,
                }
            )

        results.sort(key=lambda r: r["evaluation"].overall_score, reverse=True)
        return results

    async def _generate_content(
        self,
        argument: Argument,
        vulnerabilities: List[Vulnerability],
        counter_type: CounterArgumentType,
        strategy: RhetoricalStrategy,
    ) -> str:
        """Generate counter-argument content via SK kernel or template."""
        try:
            return await self._generate_via_kernel(
                argument, vulnerabilities, counter_type, strategy
            )
        except Exception as e:
            self.logger.warning(f"LLM generation failed, using template: {e}")
        return self.strategies.apply_strategy(strategy, argument, counter_type)

    async def _generate_via_kernel(
        self,
        argument: Argument,
        vulnerabilities: List[Vulnerability],
        counter_type: CounterArgumentType,
        strategy: RhetoricalStrategy,
    ) -> str:
        """Generate counter-argument content via SK kernel's chat service."""
        vuln_desc = (
            "; ".join(f"{v.type} ({v.target})" for v in vulnerabilities[:3])
            if vulnerabilities
            else "none identified"
        )
        strategy_prompt = self.strategies.get_strategy_prompt(strategy)
        prompt = (
            f"Generate a {counter_type.value} counter-argument.\n"
            f"Original argument: {argument.content}\n"
            f"Premises: {'; '.join(argument.premises)}\n"
            f"Conclusion: {argument.conclusion}\n"
            f"Vulnerabilities: {vuln_desc}\n"
            f"Strategy: {strategy_prompt}\n\n"
            f"Write a concise counter-argument (50-150 words):"
        )

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

    def _select_counter_type(
        self, vulnerabilities: List[Vulnerability]
    ) -> CounterArgumentType:
        """Select best counter type from vulnerabilities."""
        if vulnerabilities:
            return vulnerabilities[0].suggested_counter_type
        return CounterArgumentType.DIRECT_REFUTATION

    def _get_target(self, vulnerabilities: List[Vulnerability]) -> str:
        """Get primary target from vulnerabilities."""
        if vulnerabilities:
            return vulnerabilities[0].target
        return "general"

    def _assess_strength(self, content: str) -> ArgumentStrength:
        """Simple strength assessment based on content length and markers."""
        words = len(content.split())
        has_evidence = any(
            w in content.lower()
            for w in [
                "preuve",
                "étude",
                "données",
                "exemple",
                "research",
                "evidence",
            ]
        )
        if words > 100 and has_evidence:
            return ArgumentStrength.STRONG
        if words > 50 or has_evidence:
            return ArgumentStrength.MODERATE
        return ArgumentStrength.WEAK
