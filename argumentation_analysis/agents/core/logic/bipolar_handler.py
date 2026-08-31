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
        # #1959 (1.31 migration, R896 rework): Tweety 1.31 reduced the bipolar
        # module from 86 to 16 classes. Three AF classes were unified into a
        # single ``BipolarArgumentationFramework`` parameterised by ``Support.Type``
        # (EVIDENTIAL / NECESSITY / DEDUCTIVE / etc.), AND the whole argument/edge
        # vocabulary was replaced by Dung's. The five names the handler resolves
        # here migrate as follows (measured in #1959, table in
        # ``core/tweety_assembly.py``):
        #   - ``EvidentialArgumentationFramework`` /
        #     ``NecessityArgumentationFramework`` -> ``BipolarArgumentationFramework``
        #   - ``BArgument``           -> ``dung.syntax.Argument``
        #   - ``BinaryAttack`` / bipolar's ``Attack``
        #                              -> ``dung.syntax.Attack``
        #   - ``BinarySupport``       -> ``bipolar.syntax.Support(Argument, Argument)``
        #
        # The 1:1 migration initially kept both ``framework_type`` values as
        # behavioural no-ops (construct, discard, never query) -- #1965 closed
        # that gap: the handler now reduces the framework to its associated
        # Dung theory per support type and returns the grounded model.
        self.BipolarAF = jpype.JClass(
            "org.tweetyproject.arg.bipolar.syntax.BipolarArgumentationFramework"
        )
        self.Support = jpype.JClass("org.tweetyproject.arg.bipolar.syntax.Support")
        self.Argument = jpype.JClass("org.tweetyproject.arg.dung.syntax.Argument")
        self.Attack = jpype.JClass("org.tweetyproject.arg.dung.syntax.Attack")
        # #1965: the handler used to construct the framework and return an echo
        # of its inputs. The canonical query per Tweety 1.31 is: reduce the
        # bipolar framework to a Dung theory via getAssociatedTheory(Support.Type),
        # then run the grounded Dung reasoner (the 1.31 evidential reasoner
        # family was retired; this is the same reduction the non-vacuity
        # control test_tweety_evidential_nonvacuous_1874 performs by hand).
        self.SimpleGroundedReasoner = jpype.JClass(
            "org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner"
        )

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
            # #1959 (1.31 migration, R896 rework): single BipolarArgumentationFramework
            # replaces the three 1.28 AF classes; the whole argument/edge vocabulary
            # was replaced by Dung's. #1965 then closed the no-op the migration
            # had preserved: the framework is now queried (see below).
            framework = self.BipolarAF()

            arg_map = {name: self.Argument(name) for name in arguments}
            for arg in arg_map.values():
                framework.add(arg)

            for src, tgt in attacks:
                if src in arg_map and tgt in arg_map:
                    # #1959 (R896 rework): the old JPype-JObject cast to the
                    # Attack static type was needed in 1.29 because BinaryAttack
                    # was assignable to GeneralEdge AND Attack (overload
                    # ambiguity on framework.add). In 1.31 ``dung.syntax.Attack``
                    # is the sole attack type -- there is no sibling -- so the
                    # most-specific overload is selected without a cast.
                    framework.add(self.Attack(arg_map[src], arg_map[tgt]))

            for src, tgt in supports:
                if src in arg_map and tgt in arg_map:
                    # #1959 (R896 rework): bipolar.Support now has a binary
                    # constructor ``Support(Argument, Argument)`` and inherits
                    # from DirectedEdge<Argument> (not from Attack), so the
                    # cast needed in 1.29 is no longer necessary here either.
                    framework.add(self.Support(arg_map[src], arg_map[tgt]))

            # #1965: count from the framework, not from the input lists. An
            # edge referencing an argument absent from ``arguments`` is
            # filtered above, so the two counts diverge on such an input --
            # that divergence is the falsifiable control that the handler
            # really built and consulted the framework.
            attack_count = len(framework.getAttacks())
            support_count = len(framework.getSupports())

            # #1965: query the framework -- grounded model of the associated
            # Dung theory, one canonical reasoner per support type. ``None``
            # means nothing was computed (unknown framework_type), distinct
            # from a computed empty model (0 / []).
            support_type = self.Support.Type
            assoc_type = {
                "necessity": support_type.NECESSITY,
                "evidential": support_type.EVIDENTIAL,
            }.get(framework_type)
            extensions: Optional[List[List[str]]] = None
            model_size: Optional[int] = None
            semantic: Optional[str] = None
            if assoc_type is not None:
                dung_theory = framework.getAssociatedTheory(assoc_type)
                grounded = self.SimpleGroundedReasoner()
                model = grounded.getModel(dung_theory)
                model_size = int(model.size())
                extensions = [sorted(str(arg.getName()) for arg in model)]
                semantic = "grounded"

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
                # #1965: fields derived from the constructed framework.
                "extensions": extensions,
                "model_size": model_size,
                "semantic": semantic,
            }

            return result
        except jpype.JException as e:
            logger.error(f"Java exception in bipolar analysis: {e}")
            raise RuntimeError(f"Bipolar analysis failed: {e}") from e
