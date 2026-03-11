"""Handler for Defeasible Logic Programming (DeLP) via TweetyProject.

DeLP combines logic programming with argumentation: defeasible rules can be
defeated by counter-arguments. It's the bridge between logic programming
and argumentation, distinct from ASPIC+ and ABA.

Uses Tweety's arg.delp module: org.tweetyproject.arg.delp
"""

import jpype
import logging
from typing import Dict, List, Any, Optional, Tuple

from .tweety_initializer import TweetyInitializer

logger = logging.getLogger(__name__)


class DeLPHandler:
    """Defeasible Logic Programming analysis using Tweety.

    Supports:
    - Defeasible and strict rules
    - Query answering via dialectical trees
    - Comparison criteria (generalized specificity)
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        if not initializer_instance.is_jvm_ready():
            raise RuntimeError("DeLPHandler instantiated before JVM is ready.")
        self._initializer = initializer_instance
        self._load_classes()

    def _load_classes(self):
        """Load required Java classes."""
        pkg = "org.tweetyproject.arg.delp"
        self._DefeasibleLogicProgram = jpype.JClass(
            f"{pkg}.syntax.DefeasibleLogicProgram"
        )
        self._DelpParser = jpype.JClass(f"{pkg}.parser.DelpParser")
        self._DelpReasoner = jpype.JClass(f"{pkg}.reasoner.DelpReasoner")
        self._GeneralizedSpecificity = jpype.JClass(
            f"{pkg}.semantics.GeneralizedSpecificity"
        )
        self._DelpAnswer = jpype.JClass(f"{pkg}.semantics.DelpAnswer")

        # FOL classes for queries
        self._FolParser = jpype.JClass(
            "org.tweetyproject.logics.fol.parser.FolParser"
        )

        logger.info("DeLP classes loaded successfully.")

    def parse_program(self, program_text: str) -> object:
        """Parse a DeLP program from string.

        DeLP syntax:
          fact.                    → strict fact
          head <- body.            → strict rule
          head -< body.            → defeasible rule

        Example:
          bird(tweety).
          flies(X) -< bird(X).
          ~flies(X) <- penguin(X).
        """
        try:
            parser = self._DelpParser()
            StringReader = jpype.JClass("java.io.StringReader")
            program = parser.parseBeliefBase(StringReader(program_text))
            return program
        except jpype.JException as e:
            logger.error(f"DeLP parse error: {e}")
            raise RuntimeError(f"DeLP parse error: {e}") from e

    def query(
        self, program, query_string: str, criterion: str = "generalized_specificity"
    ) -> Tuple[str, str]:
        """Query a DeLP program.

        Args:
            program: Parsed DefeasibleLogicProgram.
            query_string: The literal to query (e.g., "flies(tweety)").
            criterion: Comparison criterion ("generalized_specificity" or "empty").

        Returns:
            (answer, message) where answer is YES/NO/UNDECIDED/UNKNOWN.
        """
        try:
            if criterion == "generalized_specificity":
                comp = self._GeneralizedSpecificity()
            else:
                EmptyCriterion = jpype.JClass(
                    "org.tweetyproject.arg.delp.semantics.EmptyCriterion"
                )
                comp = EmptyCriterion()

            reasoner = self._DelpReasoner(comp)

            # Parse the query formula
            parser = self._DelpParser()
            StringReader = jpype.JClass("java.io.StringReader")
            # Re-parse to get the FOL signature
            temp_program = parser.parseBeliefBase(StringReader(str(program)))
            formula = parser.parseFormula(jpype.JString(query_string))

            result = reasoner.query(temp_program, formula)
            answer_str = str(result)

            return answer_str, f"DeLP query '{query_string}': {answer_str}"
        except jpype.JException as e:
            error_msg = f"DeLP query error: {e.getMessage()}"
            logger.error(error_msg)
            return "UNKNOWN", f"FUNC_ERROR: {error_msg}"
        except Exception as e:
            logger.error(f"Unexpected DeLP error: {e}")
            return "UNKNOWN", f"FUNC_ERROR: {e}"

    def analyze_delp(
        self,
        program_text: str,
        queries: Optional[List[str]] = None,
        criterion: str = "generalized_specificity",
    ) -> Dict[str, Any]:
        """Full DeLP analysis: parse program and answer queries.

        Args:
            program_text: DeLP program source.
            queries: List of queries to answer. If None, only parses.
            criterion: Comparison criterion for reasoning.

        Returns:
            Dict with parse info and query results.
        """
        try:
            program = self.parse_program(program_text)
            program_str = str(program)

            results = []
            if queries:
                for q in queries:
                    answer, msg = self.query(program, q, criterion)
                    results.append({
                        "query": q,
                        "answer": answer,
                        "message": msg,
                    })

            return {
                "program": program_text,
                "program_size": len(program_text.strip().split("\n")),
                "criterion": criterion,
                "query_results": results,
                "statistics": {
                    "queries_count": len(results),
                    "handler": "DeLPHandler",
                },
            }
        except Exception as e:
            return {
                "error": str(e),
                "program": program_text,
                "statistics": {"handler": "DeLPHandler"},
            }
