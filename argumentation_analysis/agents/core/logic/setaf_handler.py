"""Handler for Set Argumentation Frameworks (SetAF) via TweetyProject.

SetAF extends Dung's abstract argumentation with collective (set) attacks:
instead of a single argument attacking another, a *set* of arguments can
collectively attack a target. Supports the same semantics as Dung AF
(grounded, preferred, stable, complete, etc.).

Uses Tweety's arg.setaf module: org.tweetyproject.arg.setaf
"""

import jpype
import logging
from typing import Dict, List, Any, Optional

from .tweety_initializer import TweetyInitializer

logger = logging.getLogger(__name__)

# Mapping from semantics name to reasoner class
_SETAF_REASONERS = {
    "grounded": "SimpleGroundedSetAfReasoner",
    "preferred": "SimplePreferredSetAfReasoner",
    "stable": "SimpleStableSetAfReasoner",
    "complete": "SimpleCompleteSetAfReasoner",
    "admissible": "SimpleAdmissibleSetAfReasoner",
    "conflict_free": "SimpleConflictFreeSetAfReasoner",
    "eager": "SimpleEagerSetAfReasoner",
    "ideal": "SimpleIdealSetAfReasoner",
    "semi_stable": "SimpleSemiStableSetAfReasoner",
    "stage": "SimpleStageSetAfReasoner",
}


class SetAFHandler:
    """Set Argumentation Framework analysis using Tweety.

    Extends Dung AF with collective attacks: a set of arguments
    can jointly attack a target argument.
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        if not initializer_instance.is_jvm_ready():
            raise RuntimeError("SetAFHandler instantiated before JVM is ready.")
        self._initializer = initializer_instance
        self._load_classes()

    def _load_classes(self):
        """Load required Java classes."""
        pkg = "org.tweetyproject.arg.setaf"
        self._SetAf = jpype.JClass(f"{pkg}.syntax.SetAf")
        self._SetAttack = jpype.JClass(f"{pkg}.syntax.SetAttack")

        # Dung Argument is shared
        self._Argument = jpype.JClass("org.tweetyproject.arg.dung.syntax.Argument")

        # Load reasoners
        self._reasoners = {}
        reasoner_pkg = f"{pkg}.reasoners"
        for name, cls_name in _SETAF_REASONERS.items():
            try:
                self._reasoners[name] = jpype.JClass(f"{reasoner_pkg}.{cls_name}")
            except Exception:
                logger.debug(f"SetAF reasoner '{name}' not available.")

        logger.info(
            f"SetAF classes loaded. Reasoners available: {list(self._reasoners.keys())}"
        )

    def analyze_setaf(
        self,
        arguments: List[str],
        attacks: List[Dict[str, Any]],
        semantics: str = "grounded",
    ) -> Dict[str, Any]:
        """Analyze a Set Argumentation Framework.

        Args:
            arguments: List of argument names.
            attacks: List of dicts with keys:
                - "attackers": list of argument names (the attacking set)
                - "target": argument name (the attacked argument)
            semantics: Semantics to compute (grounded, preferred, stable, etc.).

        Returns:
            Dict with extensions and statistics.
        """
        try:
            framework = self._SetAf()

            # Create arguments
            arg_map = {}
            for name in arguments:
                arg = self._Argument(name)
                arg_map[name] = arg
                framework.add(arg)

            # Create set attacks
            HashSet = jpype.JClass("java.util.HashSet")
            for attack_spec in attacks:
                attackers = attack_spec.get("attackers", [])
                target = attack_spec.get("target", "")
                if target not in arg_map:
                    continue
                attacker_set = HashSet()
                for a_name in attackers:
                    if a_name in arg_map:
                        attacker_set.add(arg_map[a_name])
                if not attacker_set.isEmpty():
                    framework.add(self._SetAttack(attacker_set, arg_map[target]))

            # Compute extensions
            extensions = []
            if semantics in self._reasoners:
                reasoner = self._reasoners[semantics]()
                models = reasoner.getModels(framework)
                for ext in models:
                    ext_args = sorted([str(a) for a in ext])
                    extensions.append(ext_args)

            return {
                "semantics": semantics,
                "arguments": sorted(arguments),
                "attacks": attacks,
                "extensions": extensions,
                "extensions_count": len(extensions),
                "statistics": {
                    "arguments_count": len(arguments),
                    "attacks_count": len(attacks),
                    "handler": "SetAFHandler",
                },
            }
        except jpype.JException as e:
            logger.error(f"Java exception in SetAF analysis: {e}")
            raise RuntimeError(f"SetAF analysis failed: {e}") from e

    @staticmethod
    def supported_semantics() -> List[str]:
        """Return list of supported semantics."""
        return list(_SETAF_REASONERS.keys())
