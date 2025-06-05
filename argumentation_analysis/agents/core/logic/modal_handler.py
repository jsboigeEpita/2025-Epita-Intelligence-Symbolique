import jpype
from jpype.types import JString
import logging
from argumentation_analysis.utils.core_utils.logging_utils import setup_logging
from .tweety_initializer import TweetyInitializer # To access Modal parser

setup_logging()
logger = logging.getLogger(__name__)

class ModalHandler:
    """
    Handles Modal Logic (ML) operations using TweetyProject.
    Relies on TweetyInitializer for JVM and ML component setup.
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        self._initializer_instance = initializer_instance
        self._modal_parser = self._initializer_instance.get_modal_parser()
        # self._modal_reasoner = TweetyInitializer.get_modal_reasoner() # If a general one is set up
        # self._modal_logic_instance = TweetyInitializer.get_modal_logic_instance() # e.g., S4

        if self._modal_parser is None:
            logger.error("Modal Logic Parser not initialized. Ensure TweetyBridge calls TweetyInitializer first.")
            raise RuntimeError("ModalHandler initialized before TweetyInitializer completed Modal Logic setup.")

    def parse_modal_formula(self, formula_str: str, modal_logic_str: str = "S4"):
        """
        Parses a Modal Logic formula string into a TweetyProject MlFormula object.
        Requires specifying the modal logic type (e.g., "K", "S4", "S5").
        """
        if not self._initializer_instance.is_jvm_started():
            logger.error("JVM not started. Cannot parse modal formula.")
            # Or attempt to start it, though initializer should handle this.
            # TweetyInitializer.get_instance().start_jvm_and_initialize()
            raise RuntimeError("JVM must be started by TweetyInitializer before parsing modal formulas.")

        if not isinstance(formula_str, str):
            raise TypeError("Input formula must be a string.")
        logger.debug(f"Attempting to parse Modal Logic formula: {formula_str} (Logic: {modal_logic_str})")
        
        try:
            ModalLogic = jpype.JClass("org.tweetyproject.logics.ml.syntax.MlFormula") # Attempting to use MlFormula for ModalLogic types
            
            try:
                java_modal_logic_enum = getattr(ModalLogic, modal_logic_str.upper())
            except AttributeError:
                logger.error(f"Unsupported Modal Logic type string: {modal_logic_str}. Supported are K, D, T, S4, S5 etc.")
                raise ValueError(f"Unsupported Modal Logic type: {modal_logic_str}")

            java_formula_str = JString(formula_str)
            modal_formula = self._modal_parser.parseFormula(java_formula_str, java_modal_logic_enum)
            
            logger.info(f"Successfully parsed Modal Logic formula: {formula_str} (Logic: {modal_logic_str}) -> {modal_formula}")
            return modal_formula
        except jpype.JException as e:
            error_message = e.getMessage()
            logger.error(f"JPype JException parsing Modal Logic formula '{formula_str}' for logic '{modal_logic_str}': {error_message}", exc_info=True)
            if "Modal operator expected!" in error_message or "Proposition expected!" in error_message:
                 raise ValueError(f"Syntax error in Modal Logic formula '{formula_str}' for logic '{modal_logic_str}': {error_message}") from e
            raise ValueError(f"Error parsing Modal Logic formula '{formula_str}' for logic '{modal_logic_str}': {error_message}") from e
        except Exception as e:
            logger.error(f"Unexpected error parsing Modal Logic formula '{formula_str}' for logic '{modal_logic_str}': {e}", exc_info=True)
            raise

    def modal_check_consistency(self, knowledge_base_str: str, modal_logic_str: str = "S4", signature_declarations_str: str = None) -> bool:
        """
        Checks if a Modal Logic knowledge base is consistent for a given modal logic (e.g., S4).
        Signature handling is complex and similar to FOL.
        This is a basic implementation and may require specific reasoners for full accuracy.
        """
        if not self._initializer_instance.is_jvm_started():
            logger.error("JVM not started. Cannot check modal consistency.")
            raise RuntimeError("JVM must be started by TweetyInitializer before checking modal consistency.")

        logger.debug(f"Checking Modal Logic consistency for KB: '{knowledge_base_str}' (Logic: {modal_logic_str})")
        try:
            MlBeliefSet = jpype.JClass("org.tweetyproject.logics.ml.syntax.MlBeliefSet")
            ModalLogic = jpype.JClass("org.tweetyproject.logics.ml.syntax.ModalLogic")
            
            try:
                java_modal_logic_enum = getattr(ModalLogic, modal_logic_str.upper())
            except AttributeError:
                logger.error(f"Unsupported Modal Logic type string: {modal_logic_str}")
                raise ValueError(f"Unsupported Modal Logic type: {modal_logic_str}")

            kb = MlBeliefSet(java_modal_logic_enum)

            if signature_declarations_str:
                logger.warning("Parsing Modal Logic signature declarations from string is complex and not fully implemented here. This may affect consistency checks.")
                # This would require parsing sorts, constants, predicates specific to modal contexts if applicable.
                pass
            
            formula_strings = [f.strip() for f in knowledge_base_str.split(';') if f.strip()]
            if not formula_strings:
                logger.info("Empty Modal Logic knowledge base is considered consistent.")
                return True

            for f_str in formula_strings:
                parsed_formula = self.parse_modal_formula(f_str, modal_logic_str)
                kb.add(parsed_formula)
            
            logger.info(f"Modal Logic KB created with {kb.size()} formulas for logic {modal_logic_str}.")

            # For actual consistency checking, a reasoner specific to the modal logic is needed.
            # Example: KrHyperModalReasoner for S4
            # KrHyperModalReasoner = jpype.JClass("org.tweetyproject.logics.ml.reasoner.KrHyperModalReasoner")
            # reasoner = KrHyperModalReasoner(java_modal_logic_enum) # Or specific logic instance
            # is_consistent = reasoner.isConsistent(kb)
            
            # Placeholder logic until full reasoner integration:
            logger.warning(f"Modal Logic consistency check for {modal_logic_str} is a placeholder. "
                           "Actual check requires a specific TweetyProject reasoner (e.g., KrHyperModalReasoner). "
                           "Currently returning True as a basic check that formulas parse.")
            # A simple check could be to see if any formula failed to parse, but that's handled in parse_modal_formula.
            # For now, if all formulas parse and add to belief set, we assume "basically consistent" for this placeholder.
            return True # Placeholder - needs real ML reasoner integration

        except jpype.JException as e:
            logger.error(f"JPype JException checking Modal Logic consistency for KB '{knowledge_base_str}' (Logic: {modal_logic_str}): {e.getMessage()}", exc_info=True)
            raise ValueError(f"Error checking Modal Logic consistency: {e.getMessage()}") from e
        except Exception as e:
            logger.error(f"Unexpected error checking Modal Logic consistency for KB '{knowledge_base_str}' (Logic: {modal_logic_str}): {e}", exc_info=True)
            raise

    def modal_query(self, knowledge_base_str: str, query_formula_str: str, modal_logic_str: str = "S4", signature_declarations_str: str = None) -> bool:
        """
        Checks if a Modal Logic query formula is entailed by a knowledge base for a given modal logic.
        This is a basic implementation and may require specific reasoners.
        """
        if not self._initializer_instance.is_jvm_started():
            logger.error("JVM not started. Cannot perform modal query.")
            raise RuntimeError("JVM must be started by TweetyInitializer before performing modal queries.")

        logger.debug(f"Performing Modal Logic query. KB: '{knowledge_base_str}', Query: '{query_formula_str}', Logic: {modal_logic_str}")
        try:
            MlBeliefSet = jpype.JClass("org.tweetyproject.logics.ml.syntax.MlBeliefSet")
            ModalLogic = jpype.JClass("org.tweetyproject.logics.ml.syntax.ModalLogic")

            try:
                java_modal_logic_enum = getattr(ModalLogic, modal_logic_str.upper())
            except AttributeError:
                logger.error(f"Unsupported Modal Logic type string: {modal_logic_str}")
                raise ValueError(f"Unsupported Modal Logic type: {modal_logic_str}")

            kb = MlBeliefSet(java_modal_logic_enum)

            if signature_declarations_str:
                logger.warning("Parsing Modal Logic signature declarations from string is complex and not fully implemented here. This may affect query results.")
                pass
            
            formula_strings = [f.strip() for f in knowledge_base_str.split(';') if f.strip()]
            for f_str in formula_strings:
                parsed_formula = self.parse_modal_formula(f_str, modal_logic_str)
                kb.add(parsed_formula)

            parsed_query_formula = self.parse_modal_formula(query_formula_str, modal_logic_str)
            
            logger.info(f"Modal Logic KB created with {kb.size()} formulas, query parsed for logic {modal_logic_str}.")

            # Actual querying requires a specific reasoner.
            # Example:
            # KrHyperModalReasoner = jpype.JClass("org.tweetyproject.logics.ml.reasoner.KrHyperModalReasoner")
            # reasoner = KrHyperModalReasoner(java_modal_logic_enum)
            # entails = reasoner.query(kb, parsed_query_formula)

            # Placeholder logic:
            logger.warning(f"Modal Logic query for {modal_logic_str} is a placeholder. "
                           "Actual query requires a specific TweetyProject reasoner. "
                           "Currently returning False as a default for this basic check.")
            return False # Placeholder - needs real ML reasoner integration

        except jpype.JException as e:
            logger.error(f"JPype JException performing Modal Logic query (KB: '{knowledge_base_str}', Query: '{query_formula_str}', Logic: {modal_logic_str}): {e.getMessage()}", exc_info=True)
            raise ValueError(f"Error performing Modal Logic query: {e.getMessage()}") from e
        except Exception as e:
            logger.error(f"Unexpected error performing Modal Logic query (KB: '{knowledge_base_str}', Query: '{query_formula_str}', Logic: {modal_logic_str}): {e}", exc_info=True)
            raise

if __name__ == '__main__':
    # Basic test setup
    from argumentation_analysis.utils.core_utils.logging_utils import setup_logging
    logger = setup_logging(__name__, level=logging.DEBUG)

    try:
        # Ensure TweetyInitializer is run (simulating TweetyBridge behavior)
        initializer = TweetyInitializer.get_instance() # Get or create singleton
        if not TweetyInitializer.is_jvm_started():
            logger.info("Starting JVM and initializing TweetyProject components for ModalHandler test...")
            initializer.start_jvm_and_initialize()
            initializer.initialize_modal_components() # Specifically ensure modal components are ready
        else:
            logger.info("JVM already started. Ensuring Modal components are initialized...")
            if TweetyInitializer.get_modal_parser() is None:
                 initializer.initialize_modal_components()


        modal_handler = ModalHandler()

        # Test S4 parsing
        formula_s4 = "Box (p -> q) -> (Box p -> Box q)"
        parsed_s4 = modal_handler.parse_modal_formula(formula_s4, "S4")
        logger.info(f"Parsed S4 formula '{formula_s4}': {parsed_s4}")
        
        formula_s4_prop = "p"
        parsed_s4_prop = modal_handler.parse_modal_formula(formula_s4_prop, "S4")
        logger.info(f"Parsed S4 prop formula '{formula_s4_prop}': {parsed_s4_prop}")

        # Test K parsing
        formula_k = "Dia p"
        parsed_k = modal_handler.parse_modal_formula(formula_k, "K")
        logger.info(f"Parsed K formula '{formula_k}': {parsed_k}")

        # Test consistency (placeholder)
        kb_s4_consistent = "Box p; Dia q"
        is_consistent_s4 = modal_handler.modal_check_consistency(kb_s4_consistent, "S4")
        logger.info(f"S4 KB '{kb_s4_consistent}' consistency (placeholder): {is_consistent_s4}")

        # Test query (placeholder)
        kb_s4_query = "Box (a -> b); Box a"
        query_s4 = "Box b"
        entails_s4 = modal_handler.modal_query(kb_s4_query, query_s4, "S4")
        logger.info(f"S4 KB '{kb_s4_query}' entails '{query_s4}' (placeholder): {entails_s4}")

        # Test invalid formula
        try:
            modal_handler.parse_modal_formula("Boxx p", "S4")
        except ValueError as e:
            logger.info(f"Correctly caught error for invalid formula: {e}")

    except Exception as e:
        logger.error(f"Error in ModalHandler test: {e}", exc_info=True)
    finally:
        if TweetyInitializer.is_jvm_started() and not TweetyInitializer.get_instance().is_persistent_jvm():
            logger.info("Shutting down JVM after ModalHandler test.")
            # TweetyInitializer.get_instance().shutdown_jvm() # Only if not persistent
        else:
            logger.info("JVM was already running or is persistent; not shutting down here.")