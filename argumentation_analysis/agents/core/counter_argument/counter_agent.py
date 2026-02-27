"""
Counter-argument generation agent.

Orchestrates the counter-argument pipeline: parse argument structure,
identify vulnerabilities, select rhetorical strategy, generate counter-argument
(via LLM or template fallback), and evaluate quality.

Adapted from 2.3.3-generation-contre-argument/counter_agent/.
LLM calls abstracted through injectable client (replaces hardcoded gpt-3.5-turbo).
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

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


class CounterArgumentAgent:
    """Agent that generates and evaluates counter-arguments.

    Uses injectable LLM client for generation (replacing hardcoded gpt-3.5-turbo).
    Falls back to template-based generation when LLM is unavailable.
    """

    def __init__(self, llm_client=None):
        """Initialize the counter-argument agent.

        Args:
            llm_client: Optional LLM client with async chat_completion(messages=...)
                        method. If None, uses template-based fallback.
        """
        self.parser = ArgumentParser()
        self.strategies = RhetoricalStrategies()
        self.evaluator = CounterArgumentEvaluator()
        self._llm_client = llm_client

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
            Dict with keys: argument, vulnerabilities, counter_argument, evaluation.
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

        # 5. Generate counter-argument content
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
        """Generate multiple counter-arguments with different strategies.

        Args:
            argument_text: The argument text to counter.
            count: Number of counter-arguments to generate.

        Returns:
            List of counter-argument result dicts, sorted by evaluation score.
        """
        argument = self.parser.parse_argument(argument_text)
        vulnerabilities = self.parser.identify_vulnerabilities(argument)

        strategies = [
            RhetoricalStrategy.SOCRATIC_QUESTIONING,
            RhetoricalStrategy.REDUCTIO_AD_ABSURDUM,
            RhetoricalStrategy.STATISTICAL_EVIDENCE,
            RhetoricalStrategy.ANALOGICAL_COUNTER,
            RhetoricalStrategy.AUTHORITY_APPEAL,
        ]

        results = []
        for i in range(min(count, len(strategies))):
            strat = strategies[i]
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
        """Generate counter-argument content via LLM or template fallback."""
        if self._llm_client is not None:
            try:
                return await self._generate_via_llm(
                    argument, vulnerabilities, counter_type, strategy
                )
            except Exception as e:
                logger.warning(f"LLM generation failed, using template: {e}")

        return self.strategies.apply_strategy(strategy, argument, counter_type)

    async def _generate_via_llm(
        self,
        argument: Argument,
        vulnerabilities: List[Vulnerability],
        counter_type: CounterArgumentType,
        strategy: RhetoricalStrategy,
    ) -> str:
        """Generate via LLM client."""
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

        if asyncio.iscoroutinefunction(
            getattr(self._llm_client, "chat_completion", None)
        ):
            response = await self._llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert in argumentation and critical thinking. "
                            "Generate precise, well-structured counter-arguments."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            return response.strip()

        # Sync fallback
        try:
            response = self._llm_client.chat.completions.create(
                model=getattr(self._llm_client, "_model", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert in argumentation and critical thinking. "
                            "Generate precise, well-structured counter-arguments."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"LLM call failed: {e}") from e

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
            for w in ["preuve", "étude", "données", "exemple", "research", "evidence"]
        )
        if words > 100 and has_evidence:
            return ArgumentStrength.STRONG
        if words > 50 or has_evidence:
            return ArgumentStrength.MODERATE
        return ArgumentStrength.WEAK
