"""Handler for Social Abstract Argumentation Frameworks via TweetyProject.

Social AF extends Dung's abstract argumentation with social voting:
arguments receive positive/negative votes from agents, and acceptability
is determined by combining attack structure with social support.

Uses Tweety's arg.social module: org.tweetyproject.arg.social
"""

import jpype
import logging
from typing import Dict, List, Any, Optional, Tuple

from .tweety_initializer import TweetyInitializer

logger = logging.getLogger(__name__)


class SocialHandler:
    """Social Abstract Argumentation Framework analysis using Tweety.

    Arguments have (positive, negative) vote counts. The IssReasoner
    computes iterative social strength scores combining structural
    (attack graph) and social (voting) information.
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        if not initializer_instance.is_jvm_ready():
            raise RuntimeError("SocialHandler instantiated before JVM is ready.")
        self._initializer = initializer_instance
        self._load_classes()

    def _load_classes(self):
        """Load required Java classes."""
        pkg = "org.tweetyproject.arg.social"
        self._SocialAF = jpype.JClass(
            f"{pkg}.syntax.SocialAbstractArgumentationFramework"
        )
        self._SimpleProductSemantics = jpype.JClass(
            f"{pkg}.semantics.SimpleProductSemantics"
        )
        self._IssReasoner = jpype.JClass(f"{pkg}.reasoner.IssReasoner")

        # Dung classes
        self._Argument = jpype.JClass("org.tweetyproject.arg.dung.syntax.Argument")
        self._Attack = jpype.JClass("org.tweetyproject.arg.dung.syntax.Attack")
        # #1178: SocialAF inherits DungTheory.add, whose add(Attack) overload is
        # ambiguous against add(Formula)/add(Object) on the social subclass.
        # Resolving via the explicit DungTheory.add(Attack) static dispatch.
        self._DungTheory = jpype.JClass(
            "org.tweetyproject.arg.dung.syntax.DungTheory"
        )

        logger.info("Social AF classes loaded successfully.")

    def analyze_social_framework(
        self,
        arguments: List[str],
        attacks: List[List[str]],
        votes: Optional[Dict[str, Tuple[int, int]]] = None,
        precision: float = 0.001,
        max_iterations: int = 100,
    ) -> Dict[str, Any]:
        """Analyze a Social Abstract Argumentation Framework.

        Args:
            arguments: List of argument names.
            attacks: List of [source, target] attack pairs.
            votes: Dict mapping argument name to (positive, negative) vote counts.
                  If None, defaults to (0, 0) for all arguments.
            precision: Convergence threshold for iterative computation.
            max_iterations: Maximum iterations for ISS reasoner.

        Returns:
            Dict with social strength scores and ranking.
        """
        try:
            framework = self._SocialAF()

            # Create arguments
            arg_map = {}
            for name in arguments:
                arg = self._Argument(name)
                arg_map[name] = arg
                framework.add(arg)

            # Set votes (#1178: SocialAF API is voteUp/voteDown, not vpiPlus).
            if votes:
                for name, (pos, neg) in votes.items():
                    if name in arg_map:
                        framework.voteUp(arg_map[name], jpype.JInt(pos))
                        framework.voteDown(arg_map[name], jpype.JInt(neg))

            # Create attacks — explicit DungTheory.add(Attack) to avoid the
            # add(Formula)/add(Object) ambiguity on SocialAbstractAF (#1178).
            for src, tgt in attacks:
                if src in arg_map and tgt in arg_map:
                    self._DungTheory.add(
                        framework, self._Attack(arg_map[src], arg_map[tgt])
                    )

            # Compute social strength via ISS reasoner
            semantics = self._SimpleProductSemantics(precision)
            reasoner = self._IssReasoner(semantics, max_iterations)

            model = reasoner.getModel(framework)

            # Extract scores
            scores = {}
            if model is not None:
                for name, arg in arg_map.items():
                    val = model.get(arg)
                    scores[name] = float(val) if val is not None else 0.0

            # Rank by score (descending)
            ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)

            return {
                "arguments": sorted(arguments),
                "attacks": attacks,
                "votes": votes or {},
                "scores": scores,
                "ranking": [
                    {"argument": name, "score": score} for name, score in ranking
                ],
                "statistics": {
                    "arguments_count": len(arguments),
                    "attacks_count": len(attacks),
                    "voters": sum((p + n) for p, n in (votes or {}).values()),
                    "handler": "SocialHandler",
                },
            }
        except jpype.JException as e:
            logger.error(f"Java exception in social AF analysis: {e}")
            raise RuntimeError(f"Social AF analysis failed: {e}") from e
