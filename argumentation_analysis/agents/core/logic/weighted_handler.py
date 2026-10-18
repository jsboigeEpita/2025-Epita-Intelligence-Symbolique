"""Handler for Weighted Argumentation Frameworks via TweetyProject.

Weighted AF extends Dung's abstract argumentation with numeric weights on
attacks. The weight represents the strength/cost of an attack, allowing
for quantitative reasoning about argument acceptability.

Uses Tweety's arg.weighted module: org.tweetyproject.arg.weighted
"""

import itertools
import jpype
import logging
from typing import Dict, List, Any, Optional, Tuple

from .af_handler import (
    _DUNG_COMPONENT_MAX_NODES,
    _DUNG_ENUMERATION_CEILING,
    weak_components,
)
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

        # #1178: WeightedArgumentationFramework is generic over the weight type T.
        # The no-arg ctor instantiates <Boolean> (trivial order), but the
        # reasoners' getModels(WAF, T, T) requires the bounds to match T. Since
        # we model numeric attack weights in [0.0, 1.0], the correct algebra is
        # the FuzzySemiring (Double-typed, standard order). This makes
        # setWeight(JDouble) and getModels(min, max) type-consistent.
        self._FuzzySemiring = jpype.JClass(
            "org.tweetyproject.math.algebra.FuzzySemiring"
        )

        # Dung classes shared across AF variants
        self._Argument = jpype.JClass("org.tweetyproject.arg.dung.syntax.Argument")
        self._Attack = jpype.JClass("org.tweetyproject.arg.dung.syntax.Attack")

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
            Dict with extensions and weight statistics. The models are
            computed through the #3050 sized path: per weakly-connected
            component (attack weights ride the edges, so components compose
            exactly like the Dung side), product-gated by the same ceiling —
            an over-ceiling count is reported exactly with a named refusal
            instead of being materialized.
        """
        try:
            # Create arguments
            arg_map = {}
            for name in arguments:
                arg_map[name] = self._Argument(name)

            # Weighted attacks with both endpoints present (the full-framework
            # build below skips the others exactly like this).
            kept_attacks: List[Tuple[str, str, float]] = []
            weights = []
            for src, tgt, weight in attacks:
                if src in arg_map and tgt in arg_map:
                    kept_attacks.append((src, tgt, weight))
                    weights.append(weight)

            lower = weight_threshold if weight_threshold is not None else 0.0

            def _solve(
                comp_args: List[str], comp_attacks: List[Tuple[str, str, float]]
            ) -> List[List[str]]:
                # #1178: build a Fuzzy (Double-typed) framework so numeric
                # weights and the (min, max) bounds passed to getModels are
                # type-consistent.
                framework = self._WeightedAF(self._FuzzySemiring())
                comp_set = set(comp_args)
                for name in comp_args:
                    framework.add(arg_map[name])
                for src, tgt, weight in comp_attacks:
                    if src in comp_set and tgt in comp_set:
                        attack = self._Attack(arg_map[src], arg_map[tgt])
                        framework.setWeight(attack, jpype.JDouble(weight))
                reasoner = self._reasoners[semantics]()
                models = reasoner.getModels(
                    framework, jpype.JDouble(lower), jpype.JDouble(1.0)
                )
                return sorted(sorted(str(a) for a in ext) for ext in models)

            extensions: List[List[str]] = []
            refused: Optional[Dict[str, Any]] = None
            if semantics in self._reasoners:
                # #3050: decompose over weakly-connected components; the
                # weights ride the edges, so the compositional argument is
                # the Dung one verbatim.
                pairs = weak_components(
                    arguments, [[src, tgt] for src, tgt, _ in kept_attacks]
                )
                components = [
                    (
                        comp_args,
                        [
                            (src, tgt, weight)
                            for src, tgt, weight in kept_attacks
                            if src in set(comp_args) and tgt in set(comp_args)
                        ],
                    )
                    for comp_args, _ in pairs
                ]
                largest = max(
                    (len(comp_args) for comp_args, _ in components), default=0
                )
                if largest > _DUNG_COMPONENT_MAX_NODES:
                    refused = {
                        "refusal_reason": (
                            f"enumeration refused (#3050): the largest "
                            f"weakly-connected component holds {largest} "
                            f"nodes, over the {_DUNG_COMPONENT_MAX_NODES}-node "
                            f"enumerable bound — the {semantics} weighted "
                            f"reasoner would walk its search space unbounded"
                        ),
                        "extensions_count": None,
                        "largest_component_nodes": largest,
                    }
                else:
                    per_component = [
                        _solve(comp_args, comp_attacks)
                        for comp_args, comp_attacks in components
                    ]
                    total = 1
                    for models in per_component:
                        total *= len(models)
                    if total == 0:
                        extensions = []
                    elif total > _DUNG_ENUMERATION_CEILING:
                        refused = {
                            "refusal_reason": (
                                f"enumeration refused (#3050): the weighted "
                                f"frame admits exactly {total} {semantics} "
                                f"extensions (product over "
                                f"{len(per_component)} components), over the "
                                f"{_DUNG_ENUMERATION_CEILING}-model ceiling — "
                                f"the count is exact, the extensions are not "
                                f"materialized"
                            ),
                            "extensions_count": total,
                            "per_component_counts": [len(m) for m in per_component],
                        }
                    else:
                        extensions = sorted(
                            sorted(arg for combo in combos for arg in combo)
                            for combos in itertools.product(*per_component)
                        )

            # Weight statistics
            weight_stats = {}
            if weights:
                weight_stats = {
                    "min_weight": min(weights),
                    "max_weight": max(weights),
                    "avg_weight": sum(weights) / len(weights),
                }

            result: Dict[str, Any] = {
                "semantics": semantics,
                "arguments": sorted(arguments),
                "attacks": [
                    {"source": s, "target": t, "weight": w} for s, t, w in attacks
                ],
                "extensions": extensions,
                "extensions_count": (
                    refused["extensions_count"] if refused else len(extensions)
                ),
                "weight_statistics": weight_stats,
                "statistics": {
                    "arguments_count": len(arguments),
                    "attacks_count": len(attacks),
                    "handler": "WeightedHandler",
                },
            }
            if refused is not None:
                result["refused"] = True
                result["refusal_reason"] = refused["refusal_reason"]
            return result
        except jpype.JException as e:
            logger.error(f"Java exception in weighted AF analysis: {e}")
            raise RuntimeError(f"Weighted AF analysis failed: {e}") from e

    @staticmethod
    def supported_semantics() -> List[str]:
        """Return list of supported semantics."""
        return list(_WEIGHTED_REASONERS.keys())
