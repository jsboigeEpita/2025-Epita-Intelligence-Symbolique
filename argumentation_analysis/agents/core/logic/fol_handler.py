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

    def create_belief_set_from_signature_and_formulas(self, signature, formulas):
        """
        Crée un FolBeliefSet Java en mémoire à partir d'une signature et de formules.

        :param signature: L'objet FolSignature Java déjà construit.
        :param formulas: Une liste de chaînes de formules FOL.
        :return: Un objet FolBeliefSet de jpype.
        """
        FolBeliefSet = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolBeliefSet")
        FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
        
        # Étape 1: Créer le parser avec la signature finale et l'utiliser pour parser les formules.
        belief_set = FolBeliefSet()
        belief_set.setSignature(signature)
        
        parser = FolParser()
        parser.setSignature(signature)

        for formula_str in formulas:
            try:
                parsed_formula = self.parse_fol_formula(formula_str, custom_parser=parser)
                if parsed_formula:
                    belief_set.add(parsed_formula)
                    self.logger.debug(f"Formule ajoutée par programmation: {formula_str}")
                else:
                    self.logger.warning(f"Le parsing de '{formula_str}' avec la signature a retourné None.")
            except ValueError as e:
                self.logger.error(f"Échec final du parsing de la formule '{formula_str}' avec la signature construite : {e}")
                # Nous remontons l'exception pour que l'appelant sache que la construction a échoué.
                raise e
        
        self.logger.info(f"Base de connaissances FOL créée par programmation avec {belief_set.size()} formules.")
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
        Valide une formule FOL contre une signature donnée.
        """
        if signature is None:
            # Validation de syntaxe pure si aucune signature n'est fournie.
            try:
                self.parse_fol_formula(formula_str)
                return True, "Syntaxe valide (sans signature)."
            except ValueError as e:
                return False, str(e)

        FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
        parser = FolParser()
        parser.setSignature(signature)
        
        try:
            self.parse_fol_formula(formula_str, custom_parser=parser)
            return True, "Formule valide."
        except ValueError as e:
            return False, str(e)