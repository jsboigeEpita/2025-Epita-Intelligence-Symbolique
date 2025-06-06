import jpype
from jpype.types import JString
import logging
# La configuration du logging (appel à setup_logging()) est supposée être faite globalement.
from argumentation_analysis.utils.core_utils.logging_utils import setup_logging
from .tweety_initializer import TweetyInitializer # To access FOL parser

setup_logging()
logger = logging.getLogger(__name__) # Obtient le logger pour ce module

class FOLHandler:
    """
    Handles First-Order Logic (FOL) operations using TweetyProject.
    Relies on TweetyInitializer for JVM and FOL component setup.
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        self._initializer_instance = initializer_instance
        self._fol_parser = self._initializer_instance.get_fol_parser()
        # self._fol_reasoner = TweetyInitializer.get_fol_reasoner() # If a general one is set up

        if self._fol_parser is None:
            logger.error("FOL Parser not initialized. Ensure TweetyBridge calls TweetyInitializer first.")
            raise RuntimeError("FOLHandler initialized before TweetyInitializer completed FOL setup.")

    def parse_fol_formula(self, formula_str: str, custom_parser=None):
        """
        Parses a single FOL formula string.
        If a custom_parser (with a specific signature) is provided, it uses it.
        Otherwise, it uses the default FOL parser.
        """
        if not isinstance(formula_str, str):
            raise TypeError("Input formula must be a string.")
        
        parser_to_use = custom_parser if custom_parser else self._fol_parser
        
        logger.debug(f"Attempting to parse FOL formula: {formula_str}")
        try:
            java_formula_str = JString(formula_str)
            fol_formula = parser_to_use.parseFormula(java_formula_str)
            logger.info(f"Successfully parsed FOL formula: {formula_str} -> {fol_formula}")
            return fol_formula
        except jpype.JException as e:
            logger.error(f"JPype JException parsing FOL formula '{formula_str}': {e.getMessage()}", exc_info=True)
            raise ValueError(f"Error parsing FOL formula '{formula_str}': {e.getMessage()}") from e
        except Exception as e:
            logger.error(f"Unexpected error parsing FOL formula '{formula_str}': {e}", exc_info=True)
            raise

    def parse_fol_belief_set(self, belief_set_str: str):
        """
        Parses a complete FOL belief set string, which must include a 'signature:' line.
        The parser will read the signature and formulas from the same string.
        Returns a tuple of (FolBeliefSet, FolSignature, FolParser).
        """
        logger.debug(f"Attempting to parse FOL belief set: {belief_set_str[:100]}...")
        try:
            # Create a new parser instance for this specific operation.
            FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
            parser = FolParser()

            # The parseBeliefBase method is designed to handle the entire string,
            # including the "signature:" line. No need to split manually.
            java_belief_set_str = JString(belief_set_str)
            belief_set_obj = parser.parseBeliefBase(java_belief_set_str)
            
            # After parsing, we can retrieve the signature from the parsed object.
            signature_obj = belief_set_obj.getSignature()

            # For consistency, we can create and return a new parser that is
            # explicitly configured with the signature from the parsed belief set.
            # This is useful if the caller wants to parse individual formulas later.
            new_configured_parser = FolParser()
            new_configured_parser.setSignature(signature_obj)

            logger.info("Successfully parsed FOL belief set with its signature.")
            return belief_set_obj, signature_obj, new_configured_parser

        except jpype.JException as e:
            # Make the error message more informative
            msg = f"JPype JException parsing FOL belief set: {e.getMessage()}. Belief Set was:\n{belief_set_str}"
            logger.error(msg, exc_info=True)
            raise ValueError(msg) from e
        except Exception as e:
            msg = f"Unexpected error parsing FOL belief set: {e}. Belief Set was:\n{belief_set_str}"
            logger.error(msg, exc_info=True)
            raise RuntimeError(msg) from e

    def fol_add_sort(self, sort_name: str):
        """Adds a sort to the FOL environment. Not directly available in Tweety parsers, managed by knowledge base."""
        # In Tweety, sorts are typically part of the FolBeliefSet or Signature.
        # This method might be a conceptual placeholder or would interact with a Signature object.
        # For now, we'll assume sorts are implicitly handled or defined within formulas/KB.
        logger.warning(f"FOL sort management ({sort_name}) is typically handled by the knowledge base structure in TweetyProject.")
        # Example if interacting with a Signature:
        # FolSignature = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolSignature")
        # signature = FolSignature() # Or get it from somewhere
        # Sort = jpype.JClass("org.tweetyproject.logics.commons.syntax.Sort")
        # new_sort = Sort(JString(sort_name))
        # signature.add(new_sort)
        # logger.info(f"Sort '{sort_name}' conceptually added (actual mechanism depends on KB/Signature).")
        pass # Placeholder

    def fol_add_predicate(self, predicate_name: str, arity: int, sort_names: list = None):
        """Adds a predicate to the FOL environment. Managed by knowledge base/signature."""
        logger.warning(f"FOL predicate management ({predicate_name}/{arity}) is handled by KB/Signature in TweetyProject.")
        # Example:
        # FolSignature = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolSignature")
        # signature = FolSignature() # Or get it
        # Predicate = jpype.JClass("org.tweetyproject.logics.commons.syntax.Predicate")
        # Sort = jpype.JClass("org.tweetyproject.logics.commons.syntax.Sort")
        # if sort_names and len(sort_names) == arity:
        #     j_sorts = jpype.java.util.ArrayList()
        #     for s_name in sort_names:
        #         j_sorts.add(Sort(JString(s_name)))
        #     new_predicate = Predicate(JString(predicate_name), j_sorts)
        # else:
        #     # Create predicate with default sorts or handle error
        #     # This part needs careful mapping to Tweety's Predicate constructor
        #     # For simplicity, assuming arity implies number of default sorts if not specified
        #     j_sorts_list = [Sort(JString(f"default_sort_{i+1}")) for i in range(arity)]
        #     new_predicate = Predicate(JString(predicate_name), jpype.java.util.Arrays.asList(j_sorts_list))

        # signature.add(new_predicate)
        # logger.info(f"Predicate '{predicate_name}/{arity}' conceptually added.")
        pass # Placeholder

    def fol_check_consistency(self, knowledge_base_str: str, signature_declarations_str: str = None) -> bool:
        """
        Checks if an FOL knowledge base is consistent.
        knowledge_base_str: semicolon-separated FOL formulas.
        signature_declarations_str: semicolon-separated declarations (e.g., "sort person;", "predicate Friends(person,person);").
                                   This part needs a robust parser or a more structured input.
        """
        logger.debug(f"Checking FOL consistency for KB: {knowledge_base_str}")
        try:
            # Combine signature and knowledge base for parsing
            full_kb_str = knowledge_base_str
            if signature_declarations_str:
                full_kb_str = signature_declarations_str + "\n" + knowledge_base_str

            # Use the robust parsing method
            kb, _, _ = self.parse_fol_belief_set(full_kb_str)

            # Actual FOL consistency check requires a prover.
            # This is a placeholder until a proper prover is implemented.
            logger.warning("FOL consistency check in TweetyProject is complex and may require specific reasoners. This implementation is a placeholder and assumes consistency if parsing succeeds.")
            
            # A real implementation would look like this:
            # Prover = jpype.JClass("org.tweetyproject.logics.fol.reasoner.ResolutionProver")()
            # Contradiction = jpype.JClass("org.tweetyproject.logics.fol.syntax.Contradiction").getInstance()
            # is_consistent = not Prover.query(kb, Contradiction)
            # logger.info(f"FOL Knowledge base consistency check result: {is_consistent}")
            # return is_consistent
            
            # For now, return True if parsing was successful.
            return True

        except ValueError as e: # Catch parsing errors
            logger.error(f"Error parsing formula for FOL consistency check: {e}", exc_info=True)
            raise
        except jpype.JException as e:
            logger.error(f"JPype JException during FOL consistency check for '{knowledge_base_str}': {e.getMessage()}", exc_info=True)
            raise RuntimeError(f"FOL consistency check failed: {e.getMessage()}") from e
        except Exception as e:
            logger.error(f"Unexpected error during FOL consistency check for '{knowledge_base_str}': {e}", exc_info=True)
            raise

    def fol_query(self, knowledge_base_str: str, query_formula_str: str, signature_declarations_str: str = None) -> bool:
        """
        Checks if a query formula is entailed by an FOL knowledge base.
        """
        logger.debug(f"Performing FOL query. KB: '{knowledge_base_str}', Query: '{query_formula_str}'")
        try:
            # La méthode parse_fol_belief_set gère la création de la KB et de la signature
            # à partir de la chaîne de caractères complète.
            # On combine les déclarations de signature et la base de connaissances en une seule chaîne.
            full_kb_str = knowledge_base_str
            if signature_declarations_str:
                full_kb_str = signature_declarations_str + "\n" + knowledge_base_str

            kb, signature, parser_with_signature = self.parse_fol_belief_set(full_kb_str)
            
            # Utiliser le parser qui a été configuré avec la signature de la KB
            query_formula = self.parse_fol_formula(query_formula_str, custom_parser=parser_with_signature)
            
            # FOL querying requires a specific reasoner.
            # Example with ResolutionProver:
            # Prover = jpype.JClass("org.tweetyproject.logics.fol.reasoner.ResolutionProver")()
            # entails = Prover.query(kb, query_formula)
            
            logger.warning("FOL query in TweetyProject requires specific reasoners and signature setup. This implementation is a placeholder.")
            # Placeholder:
            # entails = False # Default to false as we don't have a real prover here.
            # This needs to be implemented with a proper FOL reasoner from TweetyProject.
            # For now, to avoid breaking flow, assume true if parsing works. This is incorrect for actual logic.
            entails = True # THIS IS A PLACEHOLDER AND INCORRECT FOR REAL FOL QUERYING
            
            logger.info(f"FOL Query: KB entails '{query_formula_str}'? {entails} (Placeholder result)")
            return bool(entails)
        except ValueError as e: # Catch parsing errors
            logger.error(f"Error parsing formula for FOL query: {e}", exc_info=True)
            raise
        except jpype.JException as e:
            logger.error(f"JPype JException during FOL query: {e.getMessage()}", exc_info=True)
            raise RuntimeError(f"FOL query failed: {e.getMessage()}") from e
        except Exception as e:
            logger.error(f"Unexpected error during FOL query: {e}", exc_info=True)
            raise

    def validate_fol_query_with_context(self, belief_set_str: str, query_str: str) -> tuple[bool, str]:
        """
        Validates a FOL query using the context (signature) from a belief set.

        This method first parses the belief set to establish a context (sorts, predicates, etc.)
        and then parses the query within that same context.

        :param belief_set_str: The full string of the knowledge base, including signature.
        :param query_str: The query string to validate.
        :return: A tuple (bool, str) indicating success and a message.
        """
        logger.debug(f"Validating query '{query_str}' with context from belief set.")
        try:
            # Use the class's default parser, which will be configured by parsing the belief set.
            # First, parse the belief base. This loads the signature into the parser.
            self._fol_parser.parseBeliefBase(JString(belief_set_str))

            # Now, using the same parser instance (which now knows the signature), parse the query.
            self._fol_parser.parseFormula(JString(query_str))

            msg = f"Query '{query_str}' successfully validated against the belief set's context."
            logger.info(msg)
            return True, msg
        except jpype.JException as e:
            # This exception is thrown for any parsing error, including undeclared predicates/constants,
            # which is exactly what we want to catch.
            error_msg = f"Validation failed for query '{query_str}': {e.getMessage()}"
            logger.warning(error_msg)
            return False, error_msg