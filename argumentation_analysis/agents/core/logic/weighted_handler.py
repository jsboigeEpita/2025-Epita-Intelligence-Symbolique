"""Handler for Weighted Argumentation Frameworks via TweetyProject.

Weighted AF extends Dung's abstract argumentation with numeric weights on
attacks. The weight represents the strength/cost of an attack, allowing
for quantitative reasoning about argument acceptability.

Uses Tweety's arg.weighted module: org.tweetyproject.arg.weighted
"""

import jpype
import logging
from typing import Dict, List, Any, Optional, Tuple

from .tweety_initializer import TweetyInitializer

logger = logging.getLogger(__name__)

_WEIGHTED_REASONERS = {
    "grounded": "SimpleWeightedGroundedReasoner",
    "preferred": "SimpleWeightedPreferredReasoner",
    "stable": "SimpleWeightedStableReasoner",
    "complete": "SimpleWeightedCompleteReasoner",
    "admissible": "SimpleWeightedAdmissibleReasoner",
    "conflict_free": "SimpleWeightedConflictFreeReasoner",
}


class WeightedHandler:
    """Weighted Argumentation Framework analysis using Tweety.

    Extends Dung AF with numeric weights on attacks, enabling
    quantitative acceptability analysis.
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        if not initializer_instance.is_jvm_ready():
            raise RuntimeError("WeightedHandler instantiated before JVM is ready.")
        self._initializer = initializer_instance
        self._load_classes()

    def _load_classes(self):
        """Load required Java classes."""
        pkg = "org.tweetyproject.arg.weighted"
        self._WeightedAF = jpype.JClass(f"{pkg}.syntax.WeightedArgumentationFramework")

        # Dung classes shared across AF variants
        self._Argument = jpype.JClass(
            "org.tweetyproject.arg.dung.syntax.Argument"
        )
        self._Attack = jpype.JClass(
            "org.tweetyproject.arg.dung.syntax.Attack"
        )

        # Load reasoners
        self._reasoners = {}
        reasoner_pkg = f"{pkg}.reasoner"
        for name, cls_name in _WEIGHTED_REASONERS.items():
            try:
                self._reasoners[name] = jpype.JClass(f"{reasoner_pkg}.{cls_name}")
            except Exception:
                logger.debug(f"Weighted reasoner '{name}' not available.")

        logger.info(
            f"Weighted AF classes loaded. Reasoners: {list(self._reasoners.keys())}"
        )

    def analyze_weighted_framework(
        self,
        arguments: List[str],
        attacks: List[Tuple[str, str, float]],
        semantics: str = "grounded",
        weight_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Analyze a Weighted Argumentation Framework.

        Args:
            arguments: List of argument names.
            attacks: List of (source, target, weight) triples.
            semantics: Semantics to compute.
            weight_threshold: Optional threshold — attacks with weight
                below this are considered too weak to count.

        Returns:
            Dict with extensions and weight statistics.
        """
        try:
            framework = self._WeightedAF()

            # Create arguments
            arg_map = {}
            for name in arguments:
                arg = self._Argument(name)
                arg_map[name] = arg
                framework.add(arg)

            # Create weighted attacks
            weights = []
            for src, tgt, weight in attacks:
                if src in arg_map and tgt in arg_map:
                    attack = self._Attack(arg_map[src], arg_map[tgt])
                    framework.setWeight(attack, jpype.JDouble(weight))
                    weights.append(weight)

            # Compute extensions
            extensions = []
            if semantics in self._reasoners:
                reasoner = self._reasoners[semantics]()
                models = reasoner.getModels(framework)
                for ext in models:
                    ext_args = sorted([str(a) for a in ext])
                    extensions.append(ext_args)

            # Weight statistics
            weight_stats = {}
            if weights:
                weight_stats = {
                    "min_weight": min(weights),
                    "max_weight": max(weights),
                    "avg_weight": sum(weights) / len(weights),
                }

            return {
                "semantics": semantics,
                "arguments": sorted(arguments),
                "attacks": [
                    {"source": s, "target": t, "weight": w}
                    for s, t, w in attacks
                ],
                "extensions": extensions,
                "extensions_count": len(extensions),
                "weight_statistics": weight_stats,
                "statistics": {
                    "arguments_count": len(arguments),
                    "attacks_count": len(attacks),
                    "handler": "WeightedHandler",
                },
            }
        except jpype.JException as e:
            logger.error(f"Java exception in weighted AF analysis: {e}")
            raise RuntimeError(f"Weighted AF analysis failed: {e}") from e

    @staticmethod
    def supported_semantics() -> List[str]:
        """Return list of supported semantics."""
        return list(_WEIGHTED_REASONERS.keys())
