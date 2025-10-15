import jpype
import logging
from typing import List, Dict, Any, Set

from .tweety_initializer import TweetyInitializer

logger = logging.getLogger(__name__)


class AFHandler:
    """
    Handles Abstract Argumentation Framework (AF) operations using TweetyProject,
    specifically for Dung's semantics.
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        self._initializer_instance = initializer_instance
        if not self._initializer_instance.is_jvm_ready():
            raise RuntimeError("AFHandler instantiated before JVM is ready.")

        # Import Java classes needed for this handler
        self.DungTheory = jpype.JClass("org.tweetyproject.arg.dung.syntax.DungTheory")
        self.Argument = jpype.JClass("org.tweetyproject.arg.dung.syntax.Argument")
        self.Attack = jpype.JClass("org.tweetyproject.arg.dung.syntax.Attack")
        self.SimplePreferredReasoner = jpype.JClass(
            "org.tweetyproject.arg.dung.reasoner.SimplePreferredReasoner"
        )
        self.Extension = jpype.JClass("org.tweetyproject.arg.dung.semantics.Extension")

    def analyze_dung_framework(
        self,
        arguments: List[str],
        attacks: List[List[str]],
        semantics: str = "preferred",
    ) -> Dict[str, Any]:
        """
        Analyzes a Dung-style abstract argumentation framework.

        Args:
            arguments (List[str]): A list of argument names.
            attacks (List[List[str]]): A list of attacks, where each attack is a list [source, target].
            semantics (str): The semantics to use (e.g., "preferred"). Currently only supports preferred.

        Returns:
            Dict[str, Any]: A dictionary containing the analysis results.
        """
        logger.info(
            f"Analyzing Dung framework with {len(arguments)} arguments and {len(attacks)} attacks for '{semantics}' semantics."
        )

        if semantics.lower() != "preferred":
            raise NotImplementedError(
                "Only 'preferred' semantics are currently supported."
            )

        try:
            # 1. Create the DungTheory (the argumentation framework)
            dung_theory = self.DungTheory()

            # 2. Add arguments
            arg_map = {arg_name: self.Argument(arg_name) for arg_name in arguments}
            for arg_obj in arg_map.values():
                dung_theory.add(arg_obj)

            # 3. Add attacks
            for source_name, target_name in attacks:
                if source_name in arg_map and target_name in arg_map:
                    attack = self.Attack(arg_map[source_name], arg_map[target_name])
                    dung_theory.add(attack)
                else:
                    logger.warning(
                        f"Skipping invalid attack from '{source_name}' to '{target_name}' as one or both arguments do not exist."
                    )

            # 4. Initialize the reasoner and compute extensions
            reasoner = self.SimplePreferredReasoner()
            extensions_java = reasoner.getModels(
                dung_theory
            )  # This returns a Collection<Extension>

            # 5. Convert Java Extensions to Python list of lists
            preferred_extensions = []
            for ext_java in extensions_java:
                extension_args = [str(arg.getName()) for arg in ext_java]
                preferred_extensions.append(sorted(extension_args))

            # 6. Format the result
            result = {
                "semantics": "preferred",
                "extensions": {
                    "preferred": sorted(
                        preferred_extensions
                    )  # Sort for predictable output
                },
                "statistics": {
                    "arguments_count": len(arguments),
                    "attacks_count": len(attacks),
                    "extensions_count": len(preferred_extensions),
                },
            }
            logger.info(
                f"Analysis successful. Found {len(preferred_extensions)} preferred extensions."
            )
            return result

        except jpype.JException as e:
            logger.error(
                f"A Java exception occurred during Dung framework analysis: {e.stacktrace()}",
                exc_info=True,
            )
            raise RuntimeError(f"Error during framework analysis: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected Python exception occurred: {e}", exc_info=True)
            raise
