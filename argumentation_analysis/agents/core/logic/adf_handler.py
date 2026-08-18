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
        self.Link = jpype.JClass("org.tweetyproject.arg.adf.semantics.link.Link")
        self.LinkType = jpype.JClass(
            "org.tweetyproject.arg.adf.semantics.link.LinkType"
        )
        self.KppParser = jpype.JClass("org.tweetyproject.arg.adf.io.KppADFFormatParser")
        self._reasoner_cache = {}
        self._solver = None
        self._solver_probed = False

    def _get_solver(self) -> Any:
        """#1796: every ADF reasoner takes an IncrementalSatSolver in its
        constructor. The only implementations in the JARs are the JNI trio;
        they decide when the DLL sits in a classpath *directory* (a jar URL
        cannot be passed to System.load — that is what made #1244 conclude
        they never decide). Probe once, honestly: if instantiation fails, the
        axis degrades instead of crashing.
        """
        if not self._solver_probed:
            self._solver_probed = True
            try:
                NativeMinisat = jpype.JClass(
                    "org.tweetyproject.arg.adf.sat.solver.NativeMinisatSolver"
                )
                self._solver = NativeMinisat()
            except Exception as e:
                logger.warning(
                    "ADF native SAT solver unavailable (%s) — axis will degrade.",
                    str(e)[:120],
                )
                self._solver = None
        return self._solver

    def _get_reasoner(self, semantics: str):
        if semantics not in self._reasoner_cache:
            if semantics not in self.REASONERS:
                raise ValueError(
                    f"Unknown ADF semantics: {semantics}. Available: {list(self.REASONERS.keys())}"
                )
            solver = self._get_solver()
            if solver is None:
                return None
            cls = jpype.JClass(self.REASONERS[semantics])
            self._reasoner_cache[semantics] = cls(solver)
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
            # #1796: default builder mode is eager with no LinkStrategy, which
            # throws "missing links" as soon as a condition references a
            # parent. We know each link's type (negation -> attacking), so we
            # provide them explicitly — no SAT-based link strategy needed.
            builder = self.ADF.builder().provided()

            # #1796: the JAR's AbstractBuilder has no add(Argument) overload —
            # only add(Argument, AcceptanceCondition) and add(Link). Every
            # statement is added exactly once, with its condition.
            arg_map = {stmt: self.ADFArgument(stmt) for stmt in statements}

            def _acc_of(condition: str) -> Any:
                if condition == "contradiction":
                    return self.ContradictionAcc.INSTANCE
                if condition.startswith("negation:"):
                    other = condition.split(":", 1)[1]
                    if other in arg_map:
                        # Argument implements AcceptanceCondition, so the bare
                        # argument is the literal for its own acceptance.
                        return self.NegationAcc(arg_map[other])
                return self.TautologyAcc.INSTANCE

            for stmt, condition in acceptance_conditions.items():
                builder.add(arg_map[stmt], _acc_of(condition))
            for stmt in statements:
                if stmt not in acceptance_conditions:
                    builder.add(arg_map[stmt], self.TautologyAcc.INSTANCE)
            for stmt, condition in acceptance_conditions.items():
                if condition.startswith("negation:"):
                    other = condition.split(":", 1)[1]
                    if other in arg_map:
                        builder.add(
                            self.Link.of(
                                arg_map[other], arg_map[stmt], self.LinkType.ATTACKING
                            )
                        )

            adf = builder.build()

            reasoner = self._get_reasoner(semantics)
            if reasoner is None:
                return {
                    "semantics": semantics,
                    "statements": sorted(statements),
                    "interpretations": [],
                    "degraded": True,
                    "note": "ADF native SAT solver unavailable (see libs/native/README.md).",
                    "statistics": {
                        "statements_count": len(statements),
                        "conditions_count": len(acceptance_conditions),
                        "interpretations_count": 0,
                    },
                }
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

    def parse_adf_file(
        self, file_path: str, semantics: str = "grounded"
    ) -> Dict[str, Any]:
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
