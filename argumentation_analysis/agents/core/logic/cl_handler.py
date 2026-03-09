"""Conditional Logic (CL) handler — TweetyProject integration.

Provides non-monotonic reasoning with conditional logic:
- Conditional statements: (B|A) meaning "if A then normally B"
- Knowledge base construction with defaults and exceptions
- Reasoning via System Z / ranking functions
- Consistency checking

Uses Tweety's CL module: org.tweetyproject.logics.cl
"""

import jpype
import logging
from typing import Dict, List, Optional, Tuple

from .tweety_initializer import TweetyInitializer

logger = logging.getLogger(__name__)


class CLHandler:
    """Handles Conditional Logic operations using TweetyProject.

    Supports non-monotonic reasoning with:
    - Conditional statements (B|A): "if A then normally B"
    - System Z ranking
    - Default reasoning with exceptions
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        if not initializer_instance.is_jvm_ready():
            raise RuntimeError("JVM not ready — cannot initialize CLHandler.")
        self._initializer_instance = initializer_instance
        self._reasoner = None  # Lazy-loaded
        self._z_reasoner = None  # Lazy-loaded
        self._load_classes()

    def _load_classes(self):
        """Load all required CL Java classes."""
        try:
            cl_pkg = "org.tweetyproject.logics.cl.syntax"
            self._Conditional = jpype.JClass(f"{cl_pkg}.Conditional")
            self._ClBeliefSet = jpype.JClass(f"{cl_pkg}.ClBeliefSet")

            self._ClParser = jpype.JClass(
                "org.tweetyproject.logics.cl.parser.ClParser"
            )
            self._SimpleCReasoner = jpype.JClass(
                "org.tweetyproject.logics.cl.reasoner.SimpleCReasoner"
            )

            # PL classes needed for conditional formulas
            pl_pkg = "org.tweetyproject.logics.pl.syntax"
            self._Proposition = jpype.JClass(f"{pl_pkg}.Proposition")
            self._Negation = jpype.JClass(f"{pl_pkg}.Negation")
            self._Conjunction = jpype.JClass(f"{pl_pkg}.Conjunction")
            self._Disjunction = jpype.JClass(f"{pl_pkg}.Disjunction")

            logger.info("CL classes loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load CL classes: {e}")
            raise RuntimeError(f"CL classes not available in Tweety: {e}") from e

    def _get_reasoner(self):
        """Lazy-load the SimpleCReasoner."""
        if self._reasoner is None:
            self._reasoner = self._SimpleCReasoner()
            logger.info("SimpleCReasoner initialized.")
        return self._reasoner

    def _try_load_z_reasoner(self):
        """Try to load ZReasoner (System Z) if available."""
        if self._z_reasoner is None:
            try:
                ZReasoner = jpype.JClass(
                    "org.tweetyproject.logics.cl.reasoner.ZReasoner"
                )
                self._z_reasoner = ZReasoner()
                logger.info("ZReasoner (System Z) loaded.")
            except Exception as e:
                logger.warning(f"ZReasoner not available: {e}")
                raise RuntimeError(f"ZReasoner not available: {e}") from e
        return self._z_reasoner

    # ── Formula builders ─────────────────────────────────────────────

    def proposition(self, name: str):
        """Create a propositional atom."""
        return self._Proposition(name)

    def negation(self, formula):
        """Negate a formula."""
        return self._Negation(formula)

    def conjunction(self, *formulas):
        """Conjunction of formulas."""
        result = formulas[0]
        for f in formulas[1:]:
            result = self._Conjunction(result, f)
        return result

    def disjunction(self, *formulas):
        """Disjunction of formulas."""
        result = formulas[0]
        for f in formulas[1:]:
            result = self._Disjunction(result, f)
        return result

    def conditional(self, conclusion, premise=None):
        """Create a conditional (conclusion | premise).

        If premise is None, creates a fact (unconditional).
        """
        if premise is None:
            return self._Conditional(conclusion)
        return self._Conditional(conclusion, premise)

    # ── KB construction ──────────────────────────────────────────────

    def create_knowledge_base(
        self,
        conditionals: Optional[List[Tuple[str, Optional[str]]]] = None,
    ) -> object:
        """Build a CL knowledge base from simplified specification.

        Args:
            conditionals: List of (conclusion, premise) pairs.
                         premise=None for unconditional facts.
                         Example: [("flies", "bird"), ("!flies", "penguin")]

        Returns:
            ClBeliefSet Java object.
        """
        kb = self._ClBeliefSet()

        if conditionals:
            for conclusion_str, premise_str in conditionals:
                conclusion = self._parse_simple_formula(conclusion_str)
                if premise_str:
                    premise = self._parse_simple_formula(premise_str)
                    cond = self._Conditional(conclusion, premise)
                else:
                    cond = self._Conditional(conclusion)
                kb.add(cond)

        return kb

    def _parse_simple_formula(self, formula_str: str):
        """Parse a simple PL formula string (supports !, &, |)."""
        formula_str = formula_str.strip()
        if formula_str.startswith("!"):
            inner = self._parse_simple_formula(formula_str[1:])
            return self._Negation(inner)
        if "&" in formula_str:
            parts = formula_str.split("&")
            formulas = [self._parse_simple_formula(p) for p in parts]
            return self.conjunction(*formulas)
        if "|" in formula_str:
            parts = formula_str.split("|")
            formulas = [self._parse_simple_formula(p) for p in parts]
            return self.disjunction(*formulas)
        return self._Proposition(formula_str.strip())

    # ── Reasoning ────────────────────────────────────────────────────

    def query(self, kb, conclusion_str: str, premise_str: Optional[str] = None) -> Tuple[bool, str]:
        """Query a conditional from the knowledge base.

        Args:
            kb: ClBeliefSet
            conclusion_str: The conclusion to check
            premise_str: The premise (None for unconditional)

        Returns:
            (entailed, message)
        """
        reasoner = self._get_reasoner()
        try:
            conclusion = self._parse_simple_formula(conclusion_str)
            if premise_str:
                premise = self._parse_simple_formula(premise_str)
                cond = self._Conditional(conclusion, premise)
            else:
                cond = self._Conditional(conclusion)

            result = reasoner.query(kb, cond)
            entailed = bool(result)
            query_repr = f"({conclusion_str} | {premise_str})" if premise_str else conclusion_str
            msg = f"CL query {query_repr}: {'ACCEPTED' if entailed else 'REJECTED'}"
            return entailed, msg
        except jpype.JException as e:
            error_msg = f"CL query error: {e.getMessage()}"
            logger.error(error_msg)
            return False, f"FUNC_ERROR: {error_msg}"
        except Exception as e:
            logger.error(f"Unexpected CL error: {e}")
            return False, f"FUNC_ERROR: {e}"

    def parse_and_query(self, kb_string: str, query_string: str) -> Tuple[bool, str]:
        """Parse a CL knowledge base and query from strings."""
        try:
            parser = self._ClParser()
            StringReader = jpype.JClass("java.io.StringReader")

            kb = parser.parseBeliefBase(StringReader(kb_string))
            query = parser.parseFormula(jpype.JString(query_string))

            reasoner = self._get_reasoner()
            result = reasoner.query(kb, query)

            if bool(result):
                return True, f"CL query '{query_string}' is ACCEPTED."
            else:
                return False, f"CL query '{query_string}' is REJECTED."
        except jpype.JException as e:
            error_msg = f"CL parse/query error: {e.getMessage()}"
            logger.error(error_msg)
            return False, f"FUNC_ERROR: {error_msg}"
        except Exception as e:
            logger.error(f"Unexpected CL error: {e}")
            return False, f"FUNC_ERROR: {e}"

    @staticmethod
    def supported_reasoners() -> List[str]:
        """List available CL reasoners."""
        return ["simple", "z_reasoner"]
