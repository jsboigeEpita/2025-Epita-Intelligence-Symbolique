"""Handler for Abstract Dialectical Frameworks (ADF) via TweetyProject.

ADFs generalize Dung's abstract argumentation by replacing attack/no-attack
with acceptance conditions — Boolean functions determining when a statement
is accepted based on its parents.

Supports:
- Grounded, Complete, Preferred, Admissible, Model, Stable semantics
- KppADF file format parsing
"""

import jpype
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ADFHandler:
    """Abstract Dialectical Framework analysis using Tweety."""

    REASONERS = {
        "grounded": "org.tweetyproject.arg.adf.reasoner.GroundReasoner",
        "complete": "org.tweetyproject.arg.adf.reasoner.CompleteReasoner",
        "preferred": "org.tweetyproject.arg.adf.reasoner.PreferredReasoner",
        "admissible": "org.tweetyproject.arg.adf.reasoner.AdmissibleReasoner",
        "model": "org.tweetyproject.arg.adf.reasoner.ModelReasoner",
        "naive": "org.tweetyproject.arg.adf.reasoner.NaiveReasoner",
        "conflict_free": "org.tweetyproject.arg.adf.reasoner.ConflictFreeReasoner",
    }

    def __init__(self, initializer_instance=None):
        if initializer_instance and not initializer_instance.is_jvm_ready():
            raise RuntimeError("ADFHandler instantiated before JVM is ready.")
        self.ADF = jpype.JClass(
            "org.tweetyproject.arg.adf.syntax.adf.GraphAbstractDialecticalFramework"
        )
        self.ADFArgument = jpype.JClass("org.tweetyproject.arg.adf.syntax.Argument")
        self.TautologyAcc = jpype.JClass(
            "org.tweetyproject.arg.adf.syntax.acc.TautologyAcceptanceCondition"
        )
        self.ContradictionAcc = jpype.JClass(
            "org.tweetyproject.arg.adf.syntax.acc.ContradictionAcceptanceCondition"
        )
        self.NegationAcc = jpype.JClass(
            "org.tweetyproject.arg.adf.syntax.acc.NegationAcceptanceCondition"
        )
        self.KppParser = jpype.JClass("org.tweetyproject.arg.adf.io.KppADFFormatParser")
        self._reasoner_cache = {}

    def _get_reasoner(self, semantics: str):
        if semantics not in self._reasoner_cache:
            if semantics not in self.REASONERS:
                raise ValueError(
                    f"Unknown ADF semantics: {semantics}. Available: {list(self.REASONERS.keys())}"
                )
            cls = jpype.JClass(self.REASONERS[semantics])
            self._reasoner_cache[semantics] = cls()
        return self._reasoner_cache[semantics]

    def analyze_adf(
        self,
        statements: List[str],
        acceptance_conditions: Dict[str, str],
        semantics: str = "grounded",
    ) -> Dict[str, Any]:
        """Analyze an ADF programmatically.

        Args:
            statements: List of statement names.
            acceptance_conditions: Dict mapping statement -> acceptance type
                ("tautology", "contradiction", "negation:other_stmt").
            semantics: Semantics to use.

        Returns:
            Dict with interpretations and statistics.
        """
        try:
            builder = self.ADF.builder()

            # Add statements
            arg_map = {}
            for stmt in statements:
                arg = self.ADFArgument(stmt)
                arg_map[stmt] = arg
                builder.add(arg)

            # Add acceptance conditions
            for stmt, condition in acceptance_conditions.items():
                arg = arg_map[stmt]
                if condition == "tautology":
                    acc = self.TautologyAcc()
                elif condition == "contradiction":
                    acc = self.ContradictionAcc()
                elif condition.startswith("negation:"):
                    other = condition.split(":", 1)[1]
                    if other in arg_map:
                        acc = self.NegationAcc(arg_map[other])
                    else:
                        acc = self.TautologyAcc()
                else:
                    acc = self.TautologyAcc()
                builder.add(arg, acc)

            adf = builder.build()

            reasoner = self._get_reasoner(semantics)
            interpretations = reasoner.getModels(adf)

            interp_list = []
            for interp in interpretations:
                interp_list.append(str(interp))

            return {
                "semantics": semantics,
                "statements": sorted(statements),
                "interpretations": interp_list,
                "statistics": {
                    "statements_count": len(statements),
                    "conditions_count": len(acceptance_conditions),
                    "interpretations_count": len(interp_list),
                },
            }
        except jpype.JException as e:
            logger.error(f"Java exception in ADF analysis: {e}")
            raise RuntimeError(f"ADF analysis failed: {e}") from e

    def parse_adf_file(self, file_path: str, semantics: str = "grounded") -> Dict[str, Any]:
        """Parse an ADF from a KppADF format file and analyze it.

        Args:
            file_path: Path to ADF file.
            semantics: Semantics to use.

        Returns:
            Dict with analysis results.
        """
        try:
            parser = self.KppParser()
            adf = parser.parse(file_path)

            reasoner = self._get_reasoner(semantics)
            interpretations = reasoner.getModels(adf)

            interp_list = []
            for interp in interpretations:
                interp_list.append(str(interp))

            return {
                "semantics": semantics,
                "source": file_path,
                "interpretations": interp_list,
                "statistics": {
                    "interpretations_count": len(interp_list),
                },
            }
        except jpype.JException as e:
            logger.error(f"Java exception parsing ADF file: {e}")
            raise RuntimeError(f"ADF file parsing failed: {e}") from e
