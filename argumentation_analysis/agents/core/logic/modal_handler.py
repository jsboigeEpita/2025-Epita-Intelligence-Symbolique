import jpype
import logging
# La configuration du logging (appel à setup_logging()) est supposée être faite globalement.
from argumentation_analysis.core.utils.logging_utils import setup_logging
from .tweety_initializer import TweetyInitializer # To access Modal parser

setup_logging()
logger = logging.getLogger(__name__) # Obtient le logger pour ce module

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

    import re
    
    def parse_modal_belief_set(self, belief_set_str: str, modal_logic_str: str = "S4"):
        """
        Parses a complete Modal Logic belief set from a string by building it programmatically.
        This avoids complex string parsing issues by handling constants and formulas separately.
        """
        if not self._initializer_instance.is_jvm_started():
            logger.error("JVM not started. Cannot parse modal belief set.")
            raise RuntimeError("JVM must be started by TweetyInitializer.")
        
        logger.debug(f"Programmatically building Modal Logic belief set (Logic: {modal_logic_str})...")
        
        try:
            Signature = jpype.JClass("org.tweetyproject.logics.commons.syntax.Signature")
            MlBeliefSet = jpype.JClass("org.tweetyproject.logics.ml.syntax.MlBeliefSet")
            
            signature = Signature()
            belief_set = MlBeliefSet()
    
            # 1. Extraire et déclarer les constantes
            # Le format est 'constant my_constant'
            constants = re.findall(r'^\s*constant\s+([a-zA-Z0-9_]+)', belief_set_str, re.MULTILINE)
            for const_name in constants:
                signature.add(jpype.JClass("org.tweetyproject.logics.commons.syntax.Constant")(const_name))
            logger.debug(f"Added constants to signature: {constants}")
            
            # 2. Extraire et parser les formules
            # Ignorer les lignes de constantes et les lignes vides
            formulas = [
                line.strip() for line in belief_set_str.splitlines()
                if line.strip() and not line.strip().startswith('constant')
            ]
            
            for f_str in formulas:
                # Pour chaque formule, la parser avec la signature contenant les constantes
                java_formula_str = jpype.JClass("java.lang.String")(f_str)
                parsed_formula = self._modal_parser.parseFormula(java_formula_str, signature)
                belief_set.add(parsed_formula)
            
            logger.info(f"Successfully built Modal Logic belief set with {belief_set.size()} formulas.")
            return belief_set
    
        except jpype.JException as e:
            error_message = e.getMessage()
            logger.error(f"JPype JException building Modal Logic belief set for logic '{modal_logic_str}': {error_message}", exc_info=True)
            raise ValueError(f"Error building Modal Logic belief set for logic '{modal_logic_str}': {error_message}") from e
        except Exception as e:
            logger.error(f"Unexpected error building Modal Logic belief set for logic '{modal_logic_str}': {e}", exc_info=True)
            raise
    
    def parse_modal_formula(self, formula_str: str, modal_logic_str: str = "S4"):
        """
        Parses a single Modal Logic formula string.
        Note: This does not handle context like constant declarations. For belief sets, use parse_modal_belief_set.
        """
        if not self._initializer_instance.is_jvm_started():
            logger.error("JVM not started. Cannot parse modal formula.")
            raise RuntimeError("JVM must be started by TweetyInitializer before parsing modal formulas.")
    
        if not isinstance(formula_str, str):
            raise TypeError("Input formula must be a string.")
        
        # Les déclarations de constantes ne sont pas des formules valides en elles-mêmes.
        if formula_str.strip().startswith("constant"):
            raise ValueError("Constant declarations are not valid formulas to be parsed in isolation.")
    
        logger.debug(f"Attempting to parse single Modal Logic formula: {formula_str} (Logic: {modal_logic_str})")
        
        try:
            java_formula_str = jpype.JClass("java.lang.String")(formula_str)
            # Créer une signature vide car parseFormula requiert une signature.
            Signature = jpype.JClass("org.tweetyproject.logics.commons.syntax.Signature")
            signature = Signature()
            modal_formula = self._modal_parser.parseFormula(java_formula_str, signature)
            
            logger.info(f"Successfully parsed single Modal Logic formula: {formula_str} -> {modal_formula}")
            return modal_formula
        except jpype.JException as e:
            error_message = e.getMessage()
            logger.error(f"JPype JException parsing single Modal Logic formula '{formula_str}' for logic '{modal_logic_str}': {error_message}", exc_info=True)
            raise ValueError(f"Error parsing Modal Logic formula '{formula_str}': {error_message}") from e
        except Exception as e:
            logger.error(f"Unexpected error parsing single Modal Logic formula '{formula_str}': {e}", exc_info=True)
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
            # ModalLogic = jpype.JClass("org.tweetyproject.logics.ml.syntax.ModalLogic") # Incorrect
            
            # Supposons que MlBeliefSet attend une chaîne pour le type de logique, ou que le parser s'en charge.
            # Le constructeur de MlBeliefSet(ModalLogic) est probablement pour un objet ModalLogic spécifique,
            # pas juste l'enum. Si le parser est responsable de la logique, le KB n'a peut-être pas besoin de la logique au constructeur.
            # Pour l'instant, on va supposer que le constructeur par défaut de MlBeliefSet est suffisant
            # et que la logique est gérée au niveau du parsing de chaque formule ou par le reasoner.
            # try:
            #     java_modal_logic_enum = getattr(ModalLogic, modal_logic_str.upper())
            # except AttributeError:
            #     logger.error(f"Unsupported Modal Logic type string: {modal_logic_str}")
            #     raise ValueError(f"Unsupported Modal Logic type: {modal_logic_str}")

            # kb = MlBeliefSet(java_modal_logic_enum) # Cela échouerait si java_modal_logic_enum n'est pas un objet ModalLogic
            kb = MlBeliefSet() # Utiliser le constructeur par défaut

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
            # ModalLogic = jpype.JClass("org.tweetyproject.logics.ml.syntax.ModalLogic") # Incorrect

            # Comme pour modal_check_consistency, utilisons le constructeur par défaut pour MlBeliefSet.
            # La logique modale sera spécifiée lors du parsing des formules individuelles.
            # try:
            #    java_modal_logic_enum = getattr(ModalLogic, modal_logic_str.upper())
            # except AttributeError:
            #    logger.error(f"Unsupported Modal Logic type string: {modal_logic_str}")
            #    raise ValueError(f"Unsupported Modal Logic type: {modal_logic_str}")

            # kb = MlBeliefSet(java_modal_logic_enum)
            kb = MlBeliefSet() # Utiliser le constructeur par défaut

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
    from argumentation_analysis.core.utils.logging_utils import setup_logging
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