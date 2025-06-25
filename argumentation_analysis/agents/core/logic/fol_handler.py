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

    def create_belief_set_from_string(self, tweety_syntax: str):
        """
        Crée un FolBeliefSet directement à partir d'une chaîne de caractères
        utilisant la syntaxe native de Tweety.
        C'est la nouvelle approche privilégiée.

        :param tweety_syntax: Une chaîne contenant la base de connaissances complète.
        :return: Un objet FolBeliefSet de jpype.
        """
        logger.info("Parsing de la base de connaissances FOL à partir de la syntaxe native.")
        StringReader = jpype.JClass("java.io.StringReader")
        FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")

        try:
            # CRUCIAL : Créer une instance de parser locale et isolée pour chaque appel.
            # Cela empêche la contamination de la signature entre les tests ou les appels.
            # L'instance partagée self._fol_parser conserve son état, ce qui cause des erreurs
            # de "redéclaration" lors d'appels successifs avec des données similaires.
            local_parser = FolParser()
            reader = StringReader(tweety_syntax)
            belief_set = local_parser.parseBeliefBase(reader)
            logger.info(f"Parsing réussi avec un parser local. {belief_set.size()} formules chargées.")
            return belief_set
        except jpype.JException as e:
            # Il est crucial de remonter l'exception de parsing pour le feedback au LLM.
            self.logger.error(f"Erreur de parsing dans Tweety: {e.getMessage()}", exc_info=True)
            raise ValueError(f"Erreur de parsing Tweety: {e.getMessage()}") from e

    def create_belief_set_programmatically(self, builder_plugin_data: dict):
        """
        Crée un FolBeliefSet Java en mémoire à partir des données accumulées
        par le BeliefSetBuilderPlugin.
        C'est la nouvelle approche robuste qui contourne les bizarreries du
        parseur de fichier .fologic.
        """
        from argumentation_analysis.agents.core.logic.first_order_logic_agent import BeliefSetBuilderPlugin
        
        sorts_data = builder_plugin_data.get("_sorts", {})
        predicates_data = builder_plugin_data.get("_predicates", {})
        formulas = builder_plugin_data.get("_formulas", [])

        FolSignature = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolSignature")
        FolBeliefSet = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolBeliefSet")
        Sort = jpype.JClass("org.tweetyproject.logics.commons.syntax.Sort")
        Constant = jpype.JClass("org.tweetyproject.logics.commons.syntax.Constant")
        Predicate = jpype.JClass("org.tweetyproject.logics.commons.syntax.Predicate")
        String = jpype.JClass("java.lang.String")
        ArrayList = jpype.JClass("java.util.ArrayList")

        import re
        
        signature = FolSignature()
        sorts_map = {}  # Python-side mapping from name to Java Sort object

        # Étape 1: Collecter tous les sorts, constantes, et prédicats (déclarés et défensifs) en Python d'abord.
        
        # 1a. Collecter les prédicats déclarés par le LLM.
        # On fait une copie pour pouvoir la modifier sans affecter l'original.
        final_predicates_data = dict(predicates_data)

        # 1b. Scan défensif pour trouver les prédicats utilisés mais non déclarés.
        for formula_str in formulas:
            potential_preds = re.findall(r'([a-zA-Z][a-zA-Z0-9_]*)\(', formula_str)
            for pred_name in potential_preds:
                if pred_name not in final_predicates_data:
                    self.logger.warning(f"Prédicat '{pred_name}' utilisé mais non déclaré. Ajout défensif.")
                    # Estimation de l'arité
                    try:
                        inner_content_match = re.search(re.escape(pred_name) + r'\((.*?)\)', formula_str)
                        if inner_content_match:
                            inner_content = inner_content_match.group(1)
                            arity = inner_content.count(',') + 1 if inner_content else 0
                        else:
                            arity = 0 # Cas comme 'pred()'.
                    except Exception:
                        arity = 1 # Fallback sûr.
                    
                    # Stratégie : tout prédicat non déclaré est de type (thing, thing, ...)
                    thing_sort_name = "thing"
                    final_predicates_data[pred_name] = [thing_sort_name] * arity
                    
                    # S'assurer que 'thing' est bien dans la liste des sorts à créer.
                    if thing_sort_name not in sorts_data:
                        sorts_data[thing_sort_name] = []


        # Étape 2: Construire la signature Java complète en une seule passe.

        # 2a. Créer et ajouter tous les sorts.
        for sort_name in sorts_data.keys():
            try:
                java_sort = Sort(String(sort_name))
                signature.add(java_sort)
                sorts_map[sort_name] = java_sort
                self.logger.debug(f"Sort ajouté par programmation : {sort_name}")
            except jpype.JException as e:
                raise ValueError(f"Échec de la création du sort Java '{sort_name}': {e.getMessage()}") from e

        # 2b. Créer et ajouter les constantes.
        for sort_name, constants_list in sorts_data.items():
            parent_sort = sorts_map.get(sort_name)
            if parent_sort:
                for const_name in constants_list:
                    try:
                        java_constant = Constant(String(const_name), parent_sort)
                        signature.add(java_constant)
                        self.logger.debug(f"Constante ajoutée: {const_name} de type {sort_name}")
                    except jpype.JException as e:
                        raise ValueError(f"Échec de la création de la constante '{const_name}': {e.getMessage()}") from e

        # 2c. Créer et ajouter la liste COMPLÈTE des prédicats.
        for pred_name, arg_sort_names in final_predicates_data.items():
            java_arg_sorts = ArrayList()
            for arg_sort_name in arg_sort_names:
                java_sort = sorts_map.get(arg_sort_name)
                if not java_sort:
                    raise ValueError(f"Incohérence: Le sort '{arg_sort_name}' du prédicat '{pred_name}' n'a pas été trouvé.")
                java_arg_sorts.add(java_sort)
            
            try:
                java_predicate = Predicate(String(pred_name), java_arg_sorts)
                signature.add(java_predicate)
                self.logger.debug(f"Prédicat ajouté: {pred_name} avec args {arg_sort_names}")
            except jpype.JException as e:
                raise ValueError(f"Échec de la création du prédicat '{pred_name}': {e.getMessage()}") from e

        # Étape 3: Créer le parser avec la signature finale et l'utiliser pour parser les formules.
        belief_set = FolBeliefSet()
        belief_set.setSignature(signature)
        
        FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
        parser = FolParser()
        parser.setSignature(signature)

        for formula_str in formulas:
            try:
                parsed_formula = self.parse_fol_formula(formula_str, custom_parser=parser)
                if parsed_formula:
                    belief_set.add(parsed_formula)
                    self.logger.debug(f"Formule ajoutée: {formula_str}")
                else:
                    self.logger.warning(f"Le parsing de '{formula_str}' a retourné None.")
            except ValueError as e:
                self.logger.error(f"Échec final du parsing de '{formula_str}' avec la signature construite : {e}")
                raise e
        
        self.logger.info(f"Base de connaissances FOL créée par programmation avec {belief_set.size()} formules.")
        return belief_set, signature

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
        Validates a FOL formula string by creating a dedicated, temporary parser
        configured with the provided signature. This approach is thread-safe and
        avoids state-related issues with a shared parser.
        """
        FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
        
        logger.debug(f"Validation de la formule '{formula_str}' avec une nouvelle instance de parser.")

        try:
            # 1. Create a new, isolated parser instance for this validation task.
            validation_parser = FolParser()
            
            # 2. Set the provided signature on this isolated parser.
            validation_parser.setSignature(signature)
            self.logger.debug(f"Signature (Hash: {signature.hashCode()}) appliquée au parser de validation.")

            # 3. Perform the parsing using the dedicated parser. If it succeeds, the formula is valid.
            self.parse_fol_formula(formula_str, custom_parser=validation_parser)
            self.logger.info(f"La formule FOL '{formula_str}' est valide avec la signature fournie.")
            return True, "Formule valide."
        
        except (jpype.JException, ValueError) as e:
            # If parse_fol_formula throws an exception, it means the formula is invalid
            # with respect to the given signature.
            error_message = f"Error parsing FOL formula '{formula_str}': {e}"
            self.logger.warning(error_message)
            return False, str(e)