"""Handler for Bipolar Argumentation Frameworks via TweetyProject.

Bipolar frameworks extend Dung's abstract argumentation with support relations
in addition to attack relations. Supports:
- Evidential Argumentation Frameworks (EAF)
- Necessity Argumentation Frameworks (NAF)
- Deductive Argumentation Frameworks
"""

import jpype
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class BipolarHandler:
    """Bipolar argumentation framework analysis using Tweety."""

    def __init__(self, initializer_instance=None):
        if initializer_instance and not initializer_instance.is_jvm_ready():
            raise RuntimeError("BipolarHandler instantiated before JVM is ready.")
        self.NecessityAF = jpype.JClass(
            "org.tweetyproject.arg.bipolar.syntax.NecessityArgumentationFramework"
        )
        self.EvidentialAF = jpype.JClass(
            "org.tweetyproject.arg.bipolar.syntax.EvidentialArgumentationFramework"
        )
        self.BArgument = jpype.JClass("org.tweetyproject.arg.bipolar.syntax.BArgument")
        self.BinaryAttack = jpype.JClass("org.tweetyproject.arg.bipolar.syntax.BinaryAttack")
        self.BinarySupport = jpype.JClass("org.tweetyproject.arg.bipolar.syntax.BinarySupport")

    def analyze_bipolar_framework(
        self,
        arguments: List[str],
        attacks: List[List[str]],
        supports: List[List[str]],
        framework_type: str = "necessity",
    ) -> Dict[str, Any]:
        """Analyze a bipolar argumentation framework.

        Args:
            arguments: List of argument names.
            attacks: List of [source, target] attack pairs.
            supports: List of [source, target] support pairs.
            framework_type: "necessity" or "evidential".

        Returns:
            Dict with analysis results.
        """
        try:
            if framework_type == "evidential":
                framework = self.EvidentialAF()
            else:
                framework = self.NecessityAF()

            arg_map = {name: self.BArgument(name) for name in arguments}
            for arg in arg_map.values():
                framework.add(arg)

            for src, tgt in attacks:
                if src in arg_map and tgt in arg_map:
                    framework.add(self.BinaryAttack(arg_map[src], arg_map[tgt]))

            for src, tgt in supports:
                if src in arg_map and tgt in arg_map:
                    framework.add(self.BinarySupport(arg_map[src], arg_map[tgt]))

            # Get attacks and supports count from the framework
            attack_count = len(attacks)
            support_count = len(supports)

            result = {
                "framework_type": framework_type,
                "arguments": sorted(arguments),
                "attacks": [[s, t] for s, t in attacks],
                "supports": [[s, t] for s, t in supports],
                "statistics": {
                    "arguments_count": len(arguments),
                    "attacks_count": attack_count,
                    "supports_count": support_count,
                },
            }

            return result
        except jpype.JException as e:
            logger.error(f"Java exception in bipolar analysis: {e}")
            raise RuntimeError(f"Bipolar analysis failed: {e}") from e
