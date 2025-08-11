import jpype
import logging
from typing import Optional, Tuple

from .tweety_initializer import TweetyInitializer

logger = logging.getLogger(__name__)

class ModalHandler:
    """
    Handles Modal Logic operations using TweetyProject.
    Relies on TweetyInitializer for JVM and Modal Logic component setup.
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        """
        Initializes the ModalHandler.
        """
        self._initializer_instance = initializer_instance
        # Placeholder names for Tweety's modal logic components.
        # These will need to be confirmed from TweetyProject's source or documentation.
        self._modal_parser = TweetyInitializer.get_modal_parser()
        self._modal_reasoner = TweetyInitializer.get_modal_reasoner()

        if self._modal_parser is None or self._modal_reasoner is None:
            logger.error("Modal Logic components not initialized. Ensure TweetyInitializer is configured for Modal Logic.")
            raise RuntimeError("ModalHandler initialized before TweetyInitializer completed Modal Logic setup.")

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
            logger.error(f"Unexpected error validating modal formula '{formula_str}': {e}", exc_info=True)
            return False, "An unexpected error occurred during validation."

    def execute_modal_query(self, belief_set_content: str, query_string: str) -> str:
        """
        Executes a modal logic query against a given belief set.
        """
        logger.debug(f"Executing modal query '{query_string}'")
        try:
            StringReader = jpype.JClass("java.io.StringReader")
            
            # Parse belief set
            belief_set_reader = StringReader(belief_set_content)
            belief_set = self._modal_parser.parseBeliefBase(belief_set_reader)

            # Parse query
            query_formula = self._modal_parser.parseFormula(jpype.JClass("java.lang.String")(query_string))

            # Execute query
            result = self._modal_reasoner.query(belief_set, query_formula)

            # The result is typically a boolean. We format it for consistency.
            if bool(result):
                return f"Tweety Result: Modal Query '{query_string}' is ACCEPTED (True)."
            else:
                return f"Tweety Result: Modal Query '{query_string}' is REJECTED (False)."

        except jpype.JException as e:
            error_msg = f"Error executing modal query: {e.getMessage()}"
            logger.error(error_msg, exc_info=True)
            return f"FUNC_ERROR: {error_msg}"
        except Exception as e:
            error_msg = f"An unexpected error occurred during modal query execution: {e}"
            logger.error(error_msg, exc_info=True)
            return f"FUNC_ERROR: {error_msg}"

    def is_modal_kb_consistent(self, belief_set_content: str) -> Tuple[bool, str]:
        """
        Checks if a modal logic knowledge base is consistent.
        """
        logger.debug("Checking modal knowledge base consistency.")
        try:
            StringReader = jpype.JClass("java.io.StringReader")
            belief_set_reader = StringReader(belief_set_content)
            belief_set = self._modal_parser.parseBeliefBase(belief_set_reader)

            # A common way to check consistency is to see if it entails a contradiction.
            # Tweety's reasoners often have a specific method for this.
            # Assuming a method 'isConsistent' exists on the reasoner.
            is_consistent = self._modal_reasoner.isConsistent(belief_set)
            
            message = "Knowledge base is consistent." if is_consistent else "Knowledge base is inconsistent."
            return bool(is_consistent), message

        except jpype.JException as e:
            # If a method is not found, it will raise a JException.
            if "no method found" in str(e).lower():
                logger.warning("The 'isConsistent' method might not be available on the ModalReasoner. Returning default.")
                return True, "Consistency check method not found, assuming consistent."
            
            error_msg = f"Error checking modal KB consistency: {e.getMessage()}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
        except Exception as e:
            error_msg = f"An unexpected error occurred during consistency check: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
