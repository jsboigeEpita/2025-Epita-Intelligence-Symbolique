"""Handler for Quantified Boolean Formulas (QBF) via TweetyProject.

QBF extends propositional logic with universal (∀) and existential (∃)
quantification over Boolean variables. Useful for formal verification:
checking whether a property holds for ALL possible inputs or EXISTS
a satisfying assignment.

Uses Tweety's logics.qbf module: org.tweetyproject.logics.qbf
"""

import jpype
import logging
from typing import Dict, List, Any, Optional, Tuple

from .tweety_initializer import TweetyInitializer

logger = logging.getLogger(__name__)


class QBFHandler:
    """Quantified Boolean Formula analysis using Tweety.

    Supports:
    - QBF formula construction (∀/∃ quantifiers over PL formulas)
    - Naive QBF reasoning (truth-table enumeration)
    - External QBF solvers (if configured)
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        if not initializer_instance.is_jvm_ready():
            raise RuntimeError("QBFHandler instantiated before JVM is ready.")
        self._initializer = initializer_instance
        self._load_classes()

    def _load_classes(self):
        """Load required Java classes."""
        qbf_pkg = "org.tweetyproject.logics.qbf"
        self._ExistsQuantifiedFormula = jpype.JClass(
            f"{qbf_pkg}.syntax.ExistsQuantifiedFormula"
        )
        self._ForallQuantifiedFormula = jpype.JClass(
            f"{qbf_pkg}.syntax.ForallQuantifiedFormula"
        )
        self._NaiveQbfReasoner = jpype.JClass(
            f"{qbf_pkg}.reasoner.NaiveQbfReasoner"
        )

        # PL classes for building formulas
        pl_pkg = "org.tweetyproject.logics.pl.syntax"
        self._Proposition = jpype.JClass(f"{pl_pkg}.Proposition")
        self._Negation = jpype.JClass(f"{pl_pkg}.Negation")
        self._Conjunction = jpype.JClass(f"{pl_pkg}.Conjunction")
        self._Disjunction = jpype.JClass(f"{pl_pkg}.Disjunction")
        self._Implication = jpype.JClass(f"{pl_pkg}.Implication")
        self._PlBeliefSet = jpype.JClass(f"{pl_pkg}.PlBeliefSet")

        # QBF parser
        try:
            self._QbfParser = jpype.JClass(f"{qbf_pkg}.parser.QbfParser")
        except Exception:
            self._QbfParser = None
            logger.debug("QbfParser not available.")

        logger.info("QBF classes loaded successfully.")

    def _parse_simple_formula(self, formula_str: str):
        """Parse a simple PL formula string (supports !, &, |, =>)."""
        formula_str = formula_str.strip()
        if formula_str.startswith("!"):
            inner = self._parse_simple_formula(formula_str[1:])
            return self._Negation(inner)
        if "=>" in formula_str:
            parts = formula_str.split("=>", 1)
            left = self._parse_simple_formula(parts[0])
            right = self._parse_simple_formula(parts[1])
            return self._Implication(left, right)
        if "&" in formula_str:
            parts = formula_str.split("&")
            formulas = [self._parse_simple_formula(p) for p in parts]
            result = formulas[0]
            for f in formulas[1:]:
                result = self._Conjunction(result, f)
            return result
        if "|" in formula_str:
            parts = formula_str.split("|")
            formulas = [self._parse_simple_formula(p) for p in parts]
            result = formulas[0]
            for f in formulas[1:]:
                result = self._Disjunction(result, f)
            return result
        return self._Proposition(formula_str.strip())

    def check_validity(
        self,
        quantifiers: List[Dict[str, Any]],
        formula_str: str,
    ) -> Tuple[bool, str]:
        """Check QBF validity.

        Args:
            quantifiers: List of {"type": "forall"|"exists", "vars": ["x","y"]}.
            formula_str: The matrix formula (propositional, using var names).

        Returns:
            (is_valid, message)
        """
        try:
            # Build the matrix formula
            matrix = self._parse_simple_formula(formula_str)

            # Wrap with quantifiers (innermost first)
            quantified = matrix
            for q in reversed(quantifiers):
                q_type = q.get("type", "forall")
                variables = q.get("vars", [])
                HashSet = jpype.JClass("java.util.HashSet")
                var_set = HashSet()
                for v in variables:
                    var_set.add(self._Proposition(v))
                if q_type == "exists":
                    quantified = self._ExistsQuantifiedFormula(quantified, var_set)
                else:
                    quantified = self._ForallQuantifiedFormula(quantified, var_set)

            # Create belief set and reason
            bs = self._PlBeliefSet()
            bs.add(quantified)
            reasoner = self._NaiveQbfReasoner()
            result = reasoner.query(bs, quantified)
            is_valid = bool(result)

            return is_valid, f"QBF {'VALID' if is_valid else 'INVALID'}: {formula_str}"
        except jpype.JException as e:
            error_msg = f"QBF error: {e.getMessage()}"
            logger.error(error_msg)
            return False, f"FUNC_ERROR: {error_msg}"
        except Exception as e:
            logger.error(f"Unexpected QBF error: {e}")
            return False, f"FUNC_ERROR: {e}"

    def analyze_qbf(
        self,
        quantifiers: List[Dict[str, Any]],
        formula_str: str,
    ) -> Dict[str, Any]:
        """Full QBF analysis.

        Args:
            quantifiers: List of {"type": "forall"|"exists", "vars": ["x","y"]}.
            formula_str: The matrix formula.

        Returns:
            Dict with validity result and statistics.
        """
        is_valid, message = self.check_validity(quantifiers, formula_str)
        return {
            "formula": formula_str,
            "quantifiers": quantifiers,
            "valid": is_valid,
            "message": message,
            "statistics": {
                "quantifier_count": len(quantifiers),
                "handler": "QBFHandler",
                "reasoner": "NaiveQbfReasoner",
            },
        }

    @staticmethod
    def supported_reasoners() -> List[str]:
        """Return list of supported QBF reasoners."""
        return ["naive"]
