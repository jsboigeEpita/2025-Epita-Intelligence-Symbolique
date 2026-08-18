"""Handler for Epistemic Argumentation Frameworks (EAF) via TweetyProject.

EAF extends Dung's abstract argumentation with epistemic states:
arguments can be believed/disbelieved by agents, enabling multi-agent
argumentation with different belief states. New in Tweety 1.29.

Uses Tweety's arg.eaf module: org.tweetyproject.arg.eaf
"""

import jpype
import logging
from typing import Dict, List, Any, Optional

from .tweety_initializer import TweetyInitializer

logger = logging.getLogger(__name__)

_EAF_REASONERS = {
    "grounded": "SimpleEAFGroundedReasoner",
    "preferred": "SimpleEAFPreferredReasoner",
    "stable": "SimpleEAFStableReasoner",
    "complete": "SimpleEAFCompleteReasoner",
    "admissible": "SimpleEAFAdmissibleReasoner",
}


def _trivial_constraint(handler: "EAFHandler", arg_name: str) -> Any:
    """#1796: the JAR's no-arg constructor defaults the epistemic constraint to
    ``Possibility(Tautology)`` — the one formula its own evaluator rejects
    (``satisfiesClassicalFormula`` handles FolAtom/Conjunction/Disjunction/
    Negation, not Tautology), so every EAF query dies with
    ``IllegalArgumentException``. This builds the equivalent always-true
    constraint the evaluator supports: the disjunction of the three labelled
    statuses of one argument (every argument has exactly one status per
    labeling, so the disjunction always holds).
    """
    from java.util import ArrayList

    disjuncts = ArrayList()
    for predicate in ("in", "out", "und"):
        disjuncts.add(
            handler._Possibility(
                handler._FolAtom(
                    handler._Predicate(predicate, 1), handler._Constant(arg_name)
                )
            )
        )
    return handler._Disjunction(disjuncts)


class EAFHandler:
    """Epistemic Argumentation Framework analysis using Tweety.

    Extends Dung AF with epistemic states per agent, allowing
    multi-agent belief-aware argumentation.
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        if not initializer_instance.is_jvm_ready():
            raise RuntimeError("EAFHandler instantiated before JVM is ready.")
        self._initializer = initializer_instance
        self._load_classes()

    def _load_classes(self):
        """Load required Java classes."""
        pkg = "org.tweetyproject.arg.eaf"
        self._EpistemicAF = jpype.JClass(
            f"{pkg}.syntax.EpistemicArgumentationFramework"
        )

        # Dung classes shared
        self._Argument = jpype.JClass("org.tweetyproject.arg.dung.syntax.Argument")
        self._Attack = jpype.JClass("org.tweetyproject.arg.dung.syntax.Attack")

        # #1796: constraint-building classes (see _trivial_constraint)
        self._Predicate = jpype.JClass(
            "org.tweetyproject.logics.commons.syntax.Predicate"
        )
        self._Constant = jpype.JClass(
            "org.tweetyproject.logics.commons.syntax.Constant"
        )
        self._FolAtom = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolAtom")
        self._Possibility = jpype.JClass(
            "org.tweetyproject.logics.ml.syntax.Possibility"
        )
        self._Disjunction = jpype.JClass(
            "org.tweetyproject.logics.fol.syntax.Disjunction"
        )

        # Load reasoners
        self._reasoners = {}
        reasoner_pkg = f"{pkg}.reasoner"
        for name, cls_name in _EAF_REASONERS.items():
            try:
                self._reasoners[name] = jpype.JClass(f"{reasoner_pkg}.{cls_name}")
            except Exception:
                logger.debug(f"EAF reasoner '{name}' not available.")

        # Agreement reasoner (special)
        try:
            self._AgreementReasoner = jpype.JClass(
                f"{reasoner_pkg}.EAFAgreementReasoner"
            )
        except Exception:
            self._AgreementReasoner = None
            logger.debug("EAFAgreementReasoner not available.")

        logger.info(f"EAF classes loaded. Reasoners: {list(self._reasoners.keys())}")

    def analyze_epistemic_framework(
        self,
        arguments: List[str],
        attacks: List[List[str]],
        epistemic_beliefs: Optional[Dict[str, List[str]]] = None,
        semantics: str = "grounded",
    ) -> Dict[str, Any]:
        """Analyze an Epistemic Argumentation Framework.

        Args:
            arguments: List of argument names.
            attacks: List of [source, target] attack pairs.
            epistemic_beliefs: Dict mapping agent name to list of believed arguments.
                             If None, all arguments are believed by all agents.
            semantics: Semantics to compute (grounded, preferred, stable, etc.).

        Returns:
            Dict with extensions and epistemic analysis.
        """
        try:
            framework = self._EpistemicAF()

            # Create arguments
            arg_map = {}
            for name in arguments:
                arg = self._Argument(name)
                arg_map[name] = arg
                framework.add(arg)

            # #1796: replace the default constraint (unsupported Tautology)
            # with an equivalent, evaluable always-true constraint.
            if arguments:
                framework.setConstraint(_trivial_constraint(self, arguments[0]))

            # Create attacks
            for src, tgt in attacks:
                if src in arg_map and tgt in arg_map:
                    framework.add(self._Attack(arg_map[src], arg_map[tgt]))

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
                "epistemic_beliefs": epistemic_beliefs or {},
                "extensions": extensions,
                "extensions_count": len(extensions),
                "statistics": {
                    "arguments_count": len(arguments),
                    "attacks_count": len(attacks),
                    "agents_count": len(epistemic_beliefs) if epistemic_beliefs else 0,
                    "handler": "EAFHandler",
                },
            }
        except jpype.JException as e:
            logger.error(f"Java exception in EAF analysis: {e}")
            raise RuntimeError(f"EAF analysis failed: {e}") from e

    @staticmethod
    def supported_semantics() -> List[str]:
        """Return list of supported semantics."""
        return list(_EAF_REASONERS.keys())
