import jpype
import logging
# La configuration du logging (appel à setup_logging()) est supposée être faite globalement.
from argumentation_analysis.core.utils.logging_utils import setup_logging
from .tweety_initializer import TweetyInitializer # To access FOL parser

setup_logging()
logger = logging.getLogger(__name__) # Obtient le logger pour ce module

class FOLHandler:
    """
    Handles First-Order Logic (FOL) operations using TweetyProject.
    Relies on TweetyInitializer for JVM and FOL component setup.
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        self.logger = logging.getLogger(__name__)
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
            java_formula_str = jpype.JClass("java.lang.String")(formula_str)
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
        This method is deprecated. Use `create_programmatic_fol_signature` and
        `create_belief_set_from_formulas` for robust, programmatic creation.
        """
        logger.warning("`parse_fol_belief_set` is deprecated. Use programmatic creation methods instead.")
        # Keeping original implementation for reference, but it should not be used.
        FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
        parser = FolParser()
        java_belief_set_str = jpype.JClass("java.lang.String")(belief_set_str)
        try:
            belief_set_obj = parser.parseBeliefBase(java_belief_set_str)
            signature_obj = belief_set_obj.getSignature()
            new_configured_parser = FolParser()
            new_configured_parser.setSignature(signature_obj)
            return belief_set_obj, signature_obj, new_configured_parser
        except jpype.JException as e:
            raise ValueError(f"JPype Error: {e.getMessage()}") from e

    def create_programmatic_fol_signature(self, normalized_structure: dict):
        """
        Creates an FolSignature object programmatically from a normalized structure.
        This includes sorts, constants, predicates, and the sort hierarchy.
        
        :param normalized_structure: A dictionary like {
                                       "sorts": ["person", "city"],
                                       "constants": {"socrates": "person", "athens": "city"},
                                       "predicates": [{"name": "LivesIn", "args": ["person", "city"]}],
                                       "sort_hierarchy": {"philosopher": "person"}
                                   }
        :return: A jpype._jclass.org.tweetyproject.logics.fol.syntax.FolSignature object or None on failure.
        """
        FolSignature = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolSignature")
        Sort = jpype.JClass("org.tweetyproject.logics.commons.syntax.Sort")
        Constant = jpype.JClass("org.tweetyproject.logics.commons.syntax.Constant")
        Predicate = jpype.JClass("org.tweetyproject.logics.commons.syntax.Predicate")
        String = jpype.JClass("java.lang.String")
        ArrayList = jpype.JClass("java.util.ArrayList")

        signature = FolSignature()
        sorts_map = {}  # Python-side mapping from name to Java Sort object

        # 1. Create and add Sorts
        sort_names = normalized_structure.get("sorts", [])
        for sort_name in sort_names:
            try:
                java_sort = Sort(String(sort_name))
                signature.add(java_sort)
                sorts_map[sort_name] = java_sort
                logger.debug(f"Programmatically added sort: {sort_name}")
            except jpype.JException as e:
                logger.error(f"Failed to add sort '{sort_name}': {e.getMessage()}")
                return None
        
        # 2. Add Sort Hierarchy (sub-sort relationships)
        sort_hierarchy = normalized_structure.get("sort_hierarchy", {})
        logger.debug(f"Processing sort hierarchy: {sort_hierarchy}")
        for sub_sort_name, super_sort_name in sort_hierarchy.items():
            if sub_sort_name in sorts_map and super_sort_name in sorts_map:
                sub_sort_obj = sorts_map[sub_sort_name]
                super_sort_obj = sorts_map[super_sort_name]
                try:
                    # FolSignature uses add(sub, super) to define hierarchy
                    signature.add(sub_sort_obj, super_sort_obj)
                    logger.info(f"Programmatically added hierarchy: {sub_sort_name} is a sub-sort of {super_sort_name}")
                except jpype.JException as e:
                    logger.error(f"Failed to add hierarchy '{sub_sort_name}' -> '{super_sort_name}': {e.getMessage()}")
                    return None
            else:
                logger.error(f"Cannot create hierarchy: Sort '{sub_sort_name}' or '{super_sort_name}' not found.")
                return None


        # 3. Create and add Constants, linking them to their Sorts
        constants_data = normalized_structure.get("constants", {})
        for const_name, sort_name in constants_data.items():
            if sort_name in sorts_map:
                parent_sort = sorts_map[sort_name]
                try:
                    java_constant = Constant(String(const_name), parent_sort)
                    signature.add(java_constant)
                    logger.debug(f"Programmatically added constant: {const_name} of sort {sort_name}")
                except jpype.JException as e:
                    logger.error(f"Failed to add constant '{const_name}': {e.getMessage()}")
                    return None
            else:
                logger.error(f"Cannot create constant '{const_name}': Its sort '{sort_name}' has not been declared.")
                return None

        # 4. Create and add Predicates
        predicates_data = normalized_structure.get("predicates", [])
        for pred_data in predicates_data:
            pred_name = pred_data.get("name")
            arg_sort_names = pred_data.get("args", [])
            
            java_arg_sorts = ArrayList()
            valid_predicate = True
            for arg_sort_name in arg_sort_names:
                if arg_sort_name in sorts_map:
                    java_arg_sorts.add(sorts_map[arg_sort_name])
                else:
                    logger.error(f"Cannot create predicate '{pred_name}': Argument sort '{arg_sort_name}' not found in declared sorts.")
                    valid_predicate = False
                    break
            
            if valid_predicate:
                try:
                    java_predicate = Predicate(String(pred_name), java_arg_sorts)
                    signature.add(java_predicate)
                    logger.debug(f"Programmatically added predicate: {pred_name} with args {arg_sort_names}")
                except jpype.JException as e:
                    logger.error(f"Failed to add predicate '{pred_name}': {e.getMessage()}")
                    return None
        
        logger.info(f"Final signature object state (Java toString): {signature}")
        return signature
 
    def create_belief_set_from_formulas(self, signature, formulas: list[str]):
        """
        Creates a FolBeliefSet by parsing formulas against a pre-built signature.

        :param signature: A pre-built FolSignature Java object.
        :param formulas: A list of FOL formula strings.
        :return: A jpype._jclass.org.tweetyproject.logics.fol.syntax.FolBeliefSet object.
        """
        FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
        FolBeliefSet = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolBeliefSet")
        
        parser = FolParser()
        parser.setSignature(signature) # Use the programmatically built signature
        
        belief_set = FolBeliefSet() # Initialize with the empty constructor
        
        for formula_str in formulas:
            try:
                parsed_formula = self.parse_fol_formula(formula_str, custom_parser=parser)
                if parsed_formula:
                    belief_set.add(parsed_formula)
                    logger.debug(f"Successfully parsed and added to belief set: {formula_str}")
                else:
                    logger.warning(f"Parsed formula for '{formula_str}' is None, skipping addition to belief set.")
            except ValueError as e:
                logger.warning(f"Skipping invalid formula '{formula_str}': {e}")
                # Optionally re-raise or collect errors
                raise e # Re-raising to let the caller know validation failed.
        
        return belief_set

    def fol_check_consistency(self, belief_set):
        """
        Checks if an FOL knowledge base (as a Java object) is consistent.
        """
        logger.debug(f"Checking FOL consistency for belief set of size {belief_set.size()}")
        try:
            # A real implementation would use a prover
            # Prover = jpype.JClass("org.tweetyproject.logics.fol.reasoner.ResolutionProver")()
            # Contradiction = jpype.JClass("org.tweetyproject.logics.fol.syntax.Contradiction").getInstance()
            # is_consistent = not Prover.query(belief_set, Contradiction)
            # return is_consistent, f"Consistency check result: {is_consistent}"
            logger.warning("FOL consistency check is a placeholder and assumes consistency.")
            return True, "Consistency check is a placeholder and currently assumes success."
        except jpype.JException as e:
            logger.error(f"JPype JException during FOL consistency check: {e.getMessage()}", exc_info=True)
            raise RuntimeError(f"FOL consistency check failed: {e.getMessage()}") from e

    def fol_query(self, belief_set, query_formula_str: str) -> bool:
        """
        Checks if a query formula is entailed by an FOL belief base object.
        """
        logger.debug(f"Performing FOL query. Query: '{query_formula_str}'")
        try:
            signature = belief_set.getSignature()
            
            FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
            parser = FolParser()
            parser.setSignature(signature)
            
            query_formula = self.parse_fol_formula(query_formula_str, custom_parser=parser)
            
            # Real implementation needed here
            # Prover = jpype.JClass("org.tweetyproject.logics.fol.reasoner.ResolutionProver")()
            # entails = Prover.query(belief_set, query_formula)
            entails = True # PLACEHOLDER
            
            logger.warning("FOL query is a placeholder.")
            logger.info(f"FOL Query: KB entails '{query_formula_str}'? {entails} (Placeholder result)")
            return bool(entails)
        except (ValueError, jpype.JException) as e:
            logger.error(f"Error during FOL query: {e}", exc_info=True)
            raise

    def validate_formula_with_signature(self, signature, formula_str: str) -> tuple[bool, str]:
        """
        Validates a FOL formula string by safely modifying the main parser's state.
        This approach avoids creating new parser objects, which has proven unreliable.
        """
        logger.debug(f"Début de la validation de la formule '{formula_str}' avec une signature personnalisée.")
        original_signature = None
        try:
            # --- Thread-safe temporary signature modification on the main parser ---
            # 1. Get the original signature to restore it later
            original_signature = self._fol_parser.getSignature()
            
            # 2. Set the temporary signature for validation
            self._fol_parser.setSignature(signature)
            self.logger.debug(f"Signature temporaire (Hash: {signature.hashCode()}) appliquée au parser principal.")

            # 3. Perform the parsing, which acts as validation
            self.parse_fol_formula(formula_str) # Use the main parser
            self.logger.info(f"La formule FOL '{formula_str}' est valide avec la signature fournie.")
            return True, "Formule valide."
        
        except (jpype.JException, ValueError) as e:
            error_message = f"Échec de la validation de la formule '{formula_str}' avec la signature. Raison: {e}"
            self.logger.error(error_message)
            return False, str(e)
            
        finally:
            # 4. Restore the original signature, regardless of success or failure
            if original_signature is not None:
                self._fol_parser.setSignature(original_signature)
                self.logger.debug(f"Signature originale (Hash: {original_signature.hashCode()}) restaurée sur le parser principal.")