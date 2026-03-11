"""Handler for Belief Revision via TweetyProject.

Implements AGM-style belief revision operators:
- Dalal revision (distance-based)
- Levi revision (contraction + expansion)
- Kernel contraction
- Credibility-based multi-agent revision (CrMas)

All operators work on propositional logic belief sets.
"""

import jpype
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class BeliefRevisionHandler:
    """AGM belief revision using Tweety's beliefdynamics module."""

    def __init__(self, initializer_instance=None):
        if initializer_instance and not initializer_instance.is_jvm_ready():
            raise RuntimeError("BeliefRevisionHandler instantiated before JVM is ready.")
        # PL classes
        self.PlBeliefSet = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
        self.PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
        self.PlFormula = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlFormula")
        self.Proposition = jpype.JClass("org.tweetyproject.logics.pl.syntax.Proposition")
        self.PlNegation = jpype.JClass("org.tweetyproject.logics.pl.syntax.Negation")
        # Revision operators
        self.DalalRevision = jpype.JClass(
            "org.tweetyproject.beliefdynamics.revops.DalalRevision"
        )
        self.KernelContraction = jpype.JClass(
            "org.tweetyproject.beliefdynamics.kernels.KernelContractionOperator"
        )
        self.RandomIncision = jpype.JClass(
            "org.tweetyproject.beliefdynamics.kernels.RandomIncisionFunction"
        )
        self.DefaultExpansion = jpype.JClass(
            "org.tweetyproject.beliefdynamics.DefaultMultipleBaseExpansionOperator"
        )
        self.LeviRevision = jpype.JClass(
            "org.tweetyproject.beliefdynamics.LeviMultipleBaseRevisionOperator"
        )

    def _parse_belief_set(self, formulas: List[str]) -> Any:
        """Parse a list of PL formula strings into a PlBeliefSet."""
        parser = self.PlParser()
        bs = self.PlBeliefSet()
        for formula_str in formulas:
            formula = parser.parseFormula(formula_str)
            bs.add(formula)
        return bs

    def revise(
        self,
        belief_set: List[str],
        new_belief: str,
        method: str = "dalal",
    ) -> Dict[str, Any]:
        """Revise a belief set with new information.

        Args:
            belief_set: List of PL formula strings (current beliefs).
            new_belief: Formula to incorporate.
            method: Revision method ("dalal", "levi").

        Returns:
            Dict with revised belief set and statistics.
        """
        try:
            bs = self._parse_belief_set(belief_set)
            parser = self.PlParser()
            new_formula = parser.parseFormula(new_belief)

            if method == "levi":
                contraction = self.KernelContraction(self.RandomIncision())
                expansion = self.DefaultExpansion()
                operator = self.LeviRevision(contraction, expansion)
            else:
                operator = self.DalalRevision()

            revised = operator.revise(bs, new_formula)

            revised_formulas = [str(f) for f in revised]

            return {
                "method": method,
                "original": belief_set,
                "new_belief": new_belief,
                "revised": sorted(revised_formulas),
                "statistics": {
                    "original_size": len(belief_set),
                    "revised_size": len(revised_formulas),
                },
            }
        except jpype.JException as e:
            logger.error(f"Java exception in belief revision: {e}")
            raise RuntimeError(f"Belief revision failed: {e}") from e

    def contract(
        self,
        belief_set: List[str],
        formula_to_remove: str,
    ) -> Dict[str, Any]:
        """Contract a belief set by removing a formula.

        Args:
            belief_set: List of PL formula strings.
            formula_to_remove: Formula to contract.

        Returns:
            Dict with contracted belief set.
        """
        try:
            bs = self._parse_belief_set(belief_set)
            parser = self.PlParser()
            formula = parser.parseFormula(formula_to_remove)

            contraction = self.KernelContraction(self.RandomIncision())
            contracted = contraction.contract(bs, formula)

            contracted_formulas = [str(f) for f in contracted]

            return {
                "operation": "contraction",
                "original": belief_set,
                "removed": formula_to_remove,
                "contracted": sorted(contracted_formulas),
                "statistics": {
                    "original_size": len(belief_set),
                    "contracted_size": len(contracted_formulas),
                },
            }
        except jpype.JException as e:
            logger.error(f"Java exception in belief contraction: {e}")
            raise RuntimeError(f"Belief contraction failed: {e}") from e
