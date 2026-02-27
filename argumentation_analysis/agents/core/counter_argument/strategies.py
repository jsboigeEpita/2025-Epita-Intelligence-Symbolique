"""
Rhetorical strategies for counter-argument generation.

Provides 5 strategy types (Socratic questioning, reductio ad absurdum,
analogical counter, authority appeal, statistical evidence) with template-based
generation and strategy recommendation logic.

Adapted from 2.3.3-generation-contre-argument/counter_agent/agent/strategies.py.
LLM-dependent generation replaced with template fallbacks.
"""

import logging
from typing import Dict, Any, List

from .definitions import (
    Argument,
    CounterArgumentType,
    RhetoricalStrategy,
)

logger = logging.getLogger(__name__)


class RhetoricalStrategies:
    """Manager for rhetorical counter-argument strategies."""

    def __init__(self):
        self.strategies = {
            RhetoricalStrategy.SOCRATIC_QUESTIONING: {
                "name": "Socratic Questioning",
                "apply": self._apply_socratic_questioning,
            },
            RhetoricalStrategy.REDUCTIO_AD_ABSURDUM: {
                "name": "Reductio ad Absurdum",
                "apply": self._apply_reductio_ad_absurdum,
            },
            RhetoricalStrategy.ANALOGICAL_COUNTER: {
                "name": "Analogical Counter",
                "apply": self._apply_analogical_counter,
            },
            RhetoricalStrategy.AUTHORITY_APPEAL: {
                "name": "Authority Appeal",
                "apply": self._apply_authority_appeal,
            },
            RhetoricalStrategy.STATISTICAL_EVIDENCE: {
                "name": "Statistical Evidence",
                "apply": self._apply_statistical_evidence,
            },
        }

    def get_strategy_prompt(self, strategy: RhetoricalStrategy) -> str:
        """Return LLM prompt instruction for a strategy."""
        prompts = {
            RhetoricalStrategy.SOCRATIC_QUESTIONING: (
                "Use the Socratic method: ask questions that challenge "
                "the argument's assumptions."
            ),
            RhetoricalStrategy.REDUCTIO_AD_ABSURDUM: (
                "Show that the argument leads to absurd or contradictory "
                "consequences."
            ),
            RhetoricalStrategy.ANALOGICAL_COUNTER: (
                "Use a relevant analogy to illustrate the argument's flaws."
            ),
            RhetoricalStrategy.AUTHORITY_APPEAL: (
                "Appeal to recognized authorities or experts to contradict "
                "the argument."
            ),
            RhetoricalStrategy.STATISTICAL_EVIDENCE: (
                "Use statistical data or studies to contradict the argument."
            ),
        }
        return prompts.get(strategy, "Use the most appropriate strategy.")

    def apply_strategy(
        self,
        strategy: RhetoricalStrategy,
        argument: Argument,
        counter_type: CounterArgumentType,
    ) -> str:
        """Apply a rhetorical strategy to generate counter-argument text."""
        info = self.strategies.get(strategy)
        if info and "apply" in info:
            return info["apply"](argument, counter_type)
        return self._fallback_counter_argument(argument, counter_type)

    def suggest_strategy(self, argument_type: str, content: str) -> RhetoricalStrategy:
        """Suggest best strategy for argument type and content."""
        content_lower = content.lower()

        if "statistique" in content_lower or "données" in content_lower:
            return RhetoricalStrategy.STATISTICAL_EVIDENCE
        if "tous" in content_lower or "chaque" in content_lower:
            return RhetoricalStrategy.ANALOGICAL_COUNTER

        type_map = {
            "deductive": RhetoricalStrategy.REDUCTIO_AD_ABSURDUM,
            "inductive": RhetoricalStrategy.AUTHORITY_APPEAL,
            "abductive": RhetoricalStrategy.ANALOGICAL_COUNTER,
        }
        return type_map.get(argument_type, RhetoricalStrategy.SOCRATIC_QUESTIONING)

    def get_best_strategy(
        self, argument: Argument, counter_type: CounterArgumentType
    ) -> RhetoricalStrategy:
        """Determine best strategy for a counter-argument type."""
        strategy_mapping = {
            CounterArgumentType.DIRECT_REFUTATION: [
                RhetoricalStrategy.STATISTICAL_EVIDENCE,
                RhetoricalStrategy.AUTHORITY_APPEAL,
            ],
            CounterArgumentType.COUNTER_EXAMPLE: [
                RhetoricalStrategy.ANALOGICAL_COUNTER,
                RhetoricalStrategy.SOCRATIC_QUESTIONING,
            ],
            CounterArgumentType.ALTERNATIVE_EXPLANATION: [
                RhetoricalStrategy.ANALOGICAL_COUNTER,
                RhetoricalStrategy.AUTHORITY_APPEAL,
            ],
            CounterArgumentType.PREMISE_CHALLENGE: [
                RhetoricalStrategy.SOCRATIC_QUESTIONING,
                RhetoricalStrategy.STATISTICAL_EVIDENCE,
            ],
            CounterArgumentType.REDUCTIO_AD_ABSURDUM: [
                RhetoricalStrategy.REDUCTIO_AD_ABSURDUM,
            ],
        }
        candidates = strategy_mapping.get(
            counter_type, [RhetoricalStrategy.SOCRATIC_QUESTIONING]
        )
        return candidates[0]

    # --- Strategy implementations ---

    def _apply_socratic_questioning(
        self, argument: Argument, counter_type: CounterArgumentType
    ) -> str:
        if not argument.premises:
            return "What evidence supports this claim?"

        premise = argument.premises[0]
        if counter_type == CounterArgumentType.PREMISE_CHALLENGE:
            generalization_words = ["tous", "toujours", "jamais", "chaque"]
            if any(word in premise.lower() for word in generalization_words):
                return (
                    f"Are you certain there are no exceptions to '{premise}'? "
                    f"A single counter-example would invalidate this premise."
                )
            return (
                f"On what basis do you establish that '{premise}'? "
                f"This premise deserves questioning."
            )

        if counter_type == CounterArgumentType.DIRECT_REFUTATION:
            return (
                f"How can you reconcile your conclusion '{argument.conclusion}' "
                f"with well-documented cases where the opposite occurred?"
            )

        return (
            "Does this conclusion seem truly inevitable, "
            "even considering other perspectives?"
        )

    def _apply_reductio_ad_absurdum(
        self, argument: Argument, counter_type: CounterArgumentType
    ) -> str:
        conclusion = argument.conclusion.lower()
        absurd = self._generate_absurd_consequence(argument)

        if "tous" in conclusion or "toujours" in conclusion:
            return (
                f"If we accept that {argument.conclusion}, we should also accept "
                f"that {absurd}, which is manifestly absurd."
            )
        if "doit" in conclusion or "nécessairement" in conclusion:
            return (
                f"If this obligation were universal, it would lead to untenable "
                f"situations such as {absurd}."
            )
        return (
            f"Pushing this logic to its extreme, we would arrive at {absurd}, "
            f"which shows the limits of this reasoning."
        )

    def _apply_analogical_counter(
        self, argument: Argument, counter_type: CounterArgumentType
    ) -> str:
        analogy = self._generate_analogy(argument)

        if counter_type == CounterArgumentType.COUNTER_EXAMPLE:
            return (
                f"This argument is similar to saying that {analogy}. "
                f"In that case, the same reasoning clearly fails."
            )
        if counter_type == CounterArgumentType.ALTERNATIVE_EXPLANATION:
            return (
                f"Consider an analogous situation: {analogy}. "
                f"A more plausible alternative explanation exists."
            )
        return (
            f"It's like saying that {analogy}, "
            f"which reveals the limits of this reasoning."
        )

    def _apply_authority_appeal(
        self, argument: Argument, counter_type: CounterArgumentType
    ) -> str:
        if counter_type == CounterArgumentType.DIRECT_REFUTATION:
            return (
                f"According to domain experts, this conclusion is incorrect "
                f"because the reality is more nuanced than the argument suggests."
            )
        if counter_type == CounterArgumentType.PREMISE_CHALLENGE:
            return (
                f"Recent research by reputable specialists questions this premise, "
                f"demonstrating that more complex factors are at play."
            )
        return (
            "The scientific consensus contradicts this claim, "
            "as shown by studies indicating otherwise."
        )

    def _apply_statistical_evidence(
        self, argument: Argument, counter_type: CounterArgumentType
    ) -> str:
        stat = self._generate_statistical_counter(argument)
        if counter_type == CounterArgumentType.DIRECT_REFUTATION:
            return f"Statistics directly contradict this conclusion: {stat}."
        if counter_type == CounterArgumentType.PREMISE_CHALLENGE:
            return f"Empirical data does not support this premise. In fact, {stat}."
        return f"The numbers tell a different story: {stat}."

    # --- Helper generators (template-based, no LLM required) ---

    def _generate_absurd_consequence(self, argument: Argument) -> str:
        conclusion = argument.conclusion.lower()
        if "toujours" in conclusion or "tous" in conclusion:
            return "all exceptions would be impossible, contrary to common experience"
        if "jamais" in conclusion or "aucun" in conclusion:
            return "any occurrence would be logically impossible, contradicting observations"
        if "doit" in conclusion or "nécessairement" in conclusion:
            return "there would be no room for freedom of choice or mitigating circumstances"
        return "we would have to accept contradictory or manifestly false consequences"

    def _generate_analogy(self, argument: Argument) -> str:
        if "tous" in argument.content.lower() or "chaque" in argument.content.lower():
            return "all birds can fly, yet penguins are birds and cannot fly"
        if "toujours" in argument.content.lower():
            return "the sun always rises in the east, ignoring different perspectives at the poles"
        return (
            "one should always take the shortest path, yet sometimes a detour is safer"
        )

    def _generate_statistical_counter(self, argument: Argument) -> str:
        return (
            "in only 15% of studied cases was this cause-effect relationship observed, "
            "far from a general rule"
        )

    def _fallback_counter_argument(
        self, argument: Argument, counter_type: CounterArgumentType
    ) -> str:
        fallbacks = {
            CounterArgumentType.DIRECT_REFUTATION: (
                "This conclusion is incorrect as it fails to account "
                "for important factors."
            ),
            CounterArgumentType.COUNTER_EXAMPLE: (
                "Cases exist that contradict this argument, "
                "for instance when circumstances differ."
            ),
            CounterArgumentType.PREMISE_CHALLENGE: (
                f"The premise "
                f"'{argument.premises[0] if argument.premises else 'main'}' "
                f"is not sufficiently supported."
            ),
            CounterArgumentType.ALTERNATIVE_EXPLANATION: (
                "A more plausible alternative explanation would be "
                "that other factors are at play."
            ),
            CounterArgumentType.REDUCTIO_AD_ABSURDUM: (
                "This logic leads to absurd conclusions " "if taken to its logical end."
            ),
        }
        return fallbacks.get(
            counter_type,
            "This argument has several flaws that question its validity.",
        )
