"""Handler for Probabilistic Argumentation via TweetyProject.

Extends Dung frameworks with probability distributions over arguments,
enabling probabilistic reasoning about argument acceptance.
"""

import jpype
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class ProbabilisticHandler:
    """Probabilistic argumentation framework analysis using Tweety."""

    def __init__(self, initializer_instance=None):
        if initializer_instance and not initializer_instance.is_jvm_ready():
            raise RuntimeError("ProbabilisticHandler instantiated before JVM is ready.")
        self.DungTheory = jpype.JClass("org.tweetyproject.arg.dung.syntax.DungTheory")
        self.Argument = jpype.JClass("org.tweetyproject.arg.dung.syntax.Argument")
        self.Attack = jpype.JClass("org.tweetyproject.arg.dung.syntax.Attack")
        self.Probability = jpype.JClass(
            "org.tweetyproject.math.probability.Probability"
        )
        self.SubgraphProbReasoner = jpype.JClass(
            "org.tweetyproject.arg.prob.reasoner.ProbabilisticReasoner"
        )

    def analyze_probabilistic_framework(
        self,
        arguments: List[str],
        attacks: List[List[str]],
        probabilities: Dict[str, float],
    ) -> Dict[str, Any]:
        """Analyze a probabilistic argumentation framework.

        Args:
            arguments: List of argument names.
            attacks: List of [source, target] attack pairs.
            probabilities: Dict mapping argument name -> probability of existence.

        Returns:
            Dict with probabilistic analysis results.
        """
        try:
            theory = self.DungTheory()
            arg_map = {name: self.Argument(name) for name in arguments}
            for arg in arg_map.values():
                theory.add(arg)
            for src, tgt in attacks:
                if src in arg_map and tgt in arg_map:
                    theory.add(self.Attack(arg_map[src], arg_map[tgt]))

            # Build probability assignment
            prob_assignment = {}
            for arg_name, prob_val in probabilities.items():
                if arg_name in arg_map:
                    prob_assignment[arg_name] = prob_val

            # Compute acceptance probabilities based on subgraph enumeration
            # For each argument, enumerate subgraphs where it's in a grounded extension
            acceptance_probs = self._compute_acceptance_probabilities(
                arguments, attacks, probabilities
            )

            return {
                "arguments": sorted(arguments),
                "probabilities": probabilities,
                "acceptance_probabilities": acceptance_probs,
                "statistics": {
                    "arguments_count": len(arguments),
                    "attacks_count": len(attacks),
                },
            }
        except jpype.JException as e:
            logger.error(f"Java exception in probabilistic analysis: {e}")
            raise RuntimeError(f"Probabilistic analysis failed: {e}") from e

    def _compute_acceptance_probabilities(
        self,
        arguments: List[str],
        attacks: List[List[str]],
        probabilities: Dict[str, float],
    ) -> Dict[str, float]:
        """Compute acceptance probability for each argument via subgraph enumeration.

        Simple approach: for each subset of arguments (weighted by probabilities),
        compute grounded extension and check if argument is in it.
        Limited to small frameworks (<15 arguments) for efficiency.
        """
        if len(arguments) > 15:
            logger.warning(
                "Framework too large for exact probabilistic computation, using approximation"
            )
            return {arg: probabilities.get(arg, 1.0) for arg in arguments}

        from itertools import combinations

        GroundedReasoner = jpype.JClass(
            "org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner"
        )

        acceptance = {arg: 0.0 for arg in arguments}
        n = len(arguments)

        # Enumerate all 2^n subsets
        for size in range(n + 1):
            for subset in combinations(arguments, size):
                subset_set = set(subset)
                # Probability of this subset occurring
                prob = 1.0
                for arg in arguments:
                    p = probabilities.get(arg, 1.0)
                    if arg in subset_set:
                        prob *= p
                    else:
                        prob *= 1.0 - p

                if prob < 1e-10:
                    continue

                # Build sub-framework
                sub_theory = self.DungTheory()
                sub_arg_map = {}
                for arg_name in subset:
                    a = self.Argument(arg_name)
                    sub_theory.add(a)
                    sub_arg_map[arg_name] = a
                for src, tgt in attacks:
                    if src in sub_arg_map and tgt in sub_arg_map:
                        sub_theory.add(self.Attack(sub_arg_map[src], sub_arg_map[tgt]))

                # Compute grounded extension
                reasoner = GroundedReasoner()
                grounded = reasoner.getModel(sub_theory)
                grounded_args = (
                    {str(a.getName()) for a in grounded} if grounded else set()
                )

                for arg in grounded_args:
                    if arg in acceptance:
                        acceptance[arg] += prob

        return acceptance
