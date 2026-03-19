import jpype
import logging
from typing import Optional, Tuple

from .tweety_initializer import TweetyInitializer
from argumentation_analysis.core.config import settings, ModalSolverChoice

logger = logging.getLogger(__name__)


class ModalHandler:
    """
    Handles Modal Logic operations using TweetyProject.
    Supports two reasoners:
    - SimpleMlReasoner (default, pure Tweety)
    - SPASSMlReasoner (backed by external SPASS binary, more powerful)
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        """
        Initializes the ModalHandler.
        """
        self._initializer_instance = initializer_instance
        self._modal_parser = initializer_instance.get_modal_parser()
        self._modal_reasoner = initializer_instance.get_modal_reasoner()
        self._spass_reasoner = None  # Lazy-loaded

        if self._modal_parser is None or self._modal_reasoner is None:
            logger.error(
                "Modal Logic components not initialized. Ensure TweetyInitializer is configured for Modal Logic."
            )
            raise RuntimeError(
                "ModalHandler initialized before TweetyInitializer completed Modal Logic setup."
            )

    def _get_spass_reasoner(self):
        """Lazy-load SPASSMlReasoner if available."""
        if self._spass_reasoner is None:
            try:
                SPASSMlReasoner = jpype.JClass(
                    "org.tweetyproject.logics.ml.reasoner.SPASSMlReasoner"
                )
                self._spass_reasoner = SPASSMlReasoner()
                logger.info("SPASSMlReasoner loaded successfully.")
            except Exception as e:
                logger.warning(f"Failed to load SPASSMlReasoner: {e}")
                raise RuntimeError(f"SPASS reasoner not available: {e}") from e
        return self._spass_reasoner

    def _get_active_reasoner(self):
        """Returns the active reasoner based on configuration."""
        if settings.modal_solver == ModalSolverChoice.SPASS:
            return self._get_spass_reasoner()
        return self._modal_reasoner

    def validate_modal_formula(self, formula_str: str) -> Tuple[bool, str]:
        """
        Validates the syntax of a modal logic formula by attempting to parse it.
        """
        logger.debug(f"Validating modal formula: '{formula_str}'")
        try:
            java_formula_str = jpype.JClass("java.lang.String")(formula_str)
            self._modal_parser.parseFormula(java_formula_str)
            return True, "Formula syntax is valid."
        except jpype.JException as e:
            error_message = f"Invalid modal formula syntax: {e.getMessage()}"
            logger.warning(error_message)
            return False, error_message
        except Exception as e:
            logger.error(
                f"Unexpected error validating modal formula '{formula_str}': {e}",
                exc_info=True,
            )
            return False, "An unexpected error occurred during validation."

    def execute_modal_query(self, belief_set_content: str, query_string: str) -> str:
        """
        Executes a modal logic query against a given belief set.
        Uses the configured reasoner (SimpleMlReasoner or SPASSMlReasoner).
        """
        reasoner = self._get_active_reasoner()
        reasoner_name = (
            type(reasoner).__name__
            if hasattr(reasoner, "__class__")
            else settings.modal_solver.value
        )
        logger.debug(f"Executing modal query '{query_string}' with {reasoner_name}")
        try:
            StringReader = jpype.JClass("java.io.StringReader")

            # Parse belief set
            belief_set_reader = StringReader(belief_set_content)
            belief_set = self._modal_parser.parseBeliefBase(belief_set_reader)

            # Parse query
            query_formula = self._modal_parser.parseFormula(
                jpype.JClass("java.lang.String")(query_string)
            )

            # Execute query
            result = reasoner.query(belief_set, query_formula)

            if bool(result):
                return f"Tweety Result ({reasoner_name}): Modal Query '{query_string}' is ACCEPTED (True)."
            else:
                return f"Tweety Result ({reasoner_name}): Modal Query '{query_string}' is REJECTED (False)."

        except jpype.JException as e:
            error_msg = f"Error executing modal query: {e.getMessage()}"
            logger.error(error_msg, exc_info=True)
            return f"FUNC_ERROR: {error_msg}"
        except Exception as e:
            error_msg = (
                f"An unexpected error occurred during modal query execution: {e}"
            )
            logger.error(error_msg, exc_info=True)
            return f"FUNC_ERROR: {error_msg}"

    def is_modal_kb_consistent(self, belief_set_content: str) -> Tuple[bool, str]:
        """
        Checks if a modal logic knowledge base is consistent.
        Uses the configured reasoner (SimpleMlReasoner or SPASSMlReasoner).
        """
        reasoner = self._get_active_reasoner()
        logger.debug(
            f"Checking modal KB consistency with {settings.modal_solver.value}."
        )
        try:
            StringReader = jpype.JClass("java.io.StringReader")
            belief_set_reader = StringReader(belief_set_content)
            belief_set = self._modal_parser.parseBeliefBase(belief_set_reader)

            is_consistent = reasoner.isConsistent(belief_set)

            message = (
                "Knowledge base is consistent."
                if is_consistent
                else "Knowledge base is inconsistent."
            )
            return bool(is_consistent), message

        except jpype.JException as e:
            if "no method found" in str(e).lower():
                logger.warning(
                    "The 'isConsistent' method might not be available on the ModalReasoner. Returning default."
                )
                return True, "Consistency check method not found, assuming consistent."

            error_msg = f"Error checking modal KB consistency: {e.getMessage()}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
        except Exception as e:
            error_msg = f"An unexpected error occurred during consistency check: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
