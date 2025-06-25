import jpype
import re
import logging
from typing import Optional, List
# La configuration du logging (appel à setup_logging()) est supposée être faite globalement,
# par exemple au point d'entrée de l'application ou dans conftest.py pour les tests.
from argumentation_analysis.core.utils.logging_utils import setup_logging
# Import TweetyInitializer to access its static methods for parser/reasoner
from .tweety_initializer import TweetyInitializer

setup_logging() # Appel de la configuration globale du logging
logger = logging.getLogger(__name__) # Obtient le logger pour ce module

class PLHandler:
    """
    Handles Propositional Logic (PL) operations using TweetyProject.
    Relies on TweetyInitializer for JVM and PL component setup.
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        self._initializer_instance = initializer_instance
        self._pl_parser = self._initializer_instance.get_pl_parser()
        # Dans la nouvelle architecture, le handler est responsable de créer son propre reasoner.
        # Le nom correct, trouvé dans les sources, est SimplePlReasoner.
        SimplePlReasoner = jpype.JClass("org.tweetyproject.logics.pl.reasoner.SimplePlReasoner")
        self._pl_reasoner = SimplePlReasoner()

        if self._pl_parser is None or self._pl_reasoner is None:
            logger.error("PL components not initialized. Ensure TweetyBridge calls TweetyInitializer first.")
            raise RuntimeError("PLHandler initialized before TweetyInitializer completed PL setup.")

    def _normalize_formula(self, formula_str: str) -> str:
        """
        Ensures consistent spacing around logical operators and parentheses for Tweety's parser.
        This version uses regex for safer and more robust replacements.
        """
        if not isinstance(formula_str, str):
            return ""

        logger.debug(f"Original formula for normalization: '{formula_str}'")

        # Replacements for common alternative operators
        formula_str = formula_str.replace("&&", "&").replace("||", "|").replace("->", "=>").replace("<->", "<=>")
        formula_str = formula_str.replace(" NOT ", " ! ").replace(" Not ", " ! ")


        # Regex to add spaces around all operators and parentheses
        # Operators: =>, <=>, &, |, !. Parentheses: (, )
        # The regex looks for these tokens and ensures they are surrounded by spaces.
        # It avoids adding spaces if they are already present.
        # The tokens are captured and replaced with themselves surrounded by spaces.
        formula_str = re.sub(r'\s*(=>|<=<|&|\||!|\(|\))\s*', r' \1 ', formula_str)

        # Clean up any resulting multiple spaces
        formula_str = " ".join(formula_str.split())

        logger.debug(f"Normalized formula to: '{formula_str}'")
        return formula_str

    def parse_pl_formula(self, formula_str: str, constants: Optional[List[str]] = None):
        """Parses a PL formula string into a TweetyProject PlFormula object."""
        # Enhanced filtering for markdown artifacts and invalid formulas
        if not isinstance(formula_str, str):
            return None
            
        formula_str = formula_str.strip()
        
        # Filter out markdown artifacts and invalid formulas
        invalid_patterns = [
            '',  # Empty string
            '```',  # Markdown code fence
            '```plaintext',  # Markdown code fence with language
            'plaintext',  # Just the language specifier
        ]
        
        if (not formula_str or
            formula_str in invalid_patterns or
            formula_str.startswith('```') or
            formula_str.endswith('```') or
            '```' in formula_str):
            logger.debug(f"Skipping parsing of invalid/markdown formula: '{formula_str}'")
            return None

        normalized_formula = self._normalize_formula(formula_str)
        logger.debug(f"Attempting to parse normalized PL formula: {normalized_formula}")

        try:
            if constants:
                PlSignature = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature")
                signature = PlSignature()
                Proposition = jpype.JClass("org.tweetyproject.logics.pl.syntax.Proposition")
                for const_name in constants:
                    proposition = Proposition(jpype.JClass("java.lang.String")(const_name))
                    if not signature.contains(proposition):
                        signature.add(proposition)
                pl_formula = self._pl_parser.parseFormula(JString(normalized_formula), signature)
            else:
                # Using JString is a good practice to avoid ambiguity.
                pl_formula = self._pl_parser.parseFormula(jpype.JString(normalized_formula))

            logger.info(f"Successfully parsed PL formula: '{formula_str}' as '{normalized_formula}' -> {pl_formula}")
            return pl_formula
        except jpype.JException as e:
            logger.error(f"JPype JException parsing PL formula '{formula_str}' (normalized to '{normalized_formula}'): {e.getMessage()}", exc_info=True)
            raise ValueError(f"Error parsing PL formula '{formula_str}': {e.getMessage()}") from e
        except Exception as e:
            logger.error(f"Unexpected error parsing PL formula '{formula_str}' (normalized to '{normalized_formula}'): {e}", exc_info=True)
            raise

    def pl_check_consistency(self, knowledge_base_str: str, constants: Optional[List[str]] = None) -> bool:
        """
        Checks if a PL knowledge base (string of formulas, semicolon-separated) is consistent.
        """
        logger.debug(f"Checking PL consistency for: {knowledge_base_str}")
        try:
            # Parse the knowledge base string into a PlBeliefSet
            # Tweety's PlParser can parse a belief set directly if formulas are separated by ';'
            # However, it's often safer to parse individual formulas and add them to a knowledge base.
            # For simplicity here, assuming parseBeliefSet handles it or we adapt.
            
            # Let's refine this: parse individual formulas and add to a PlBeliefSet
            formulas = []
            # Handle potential empty strings or formulas correctly
            formula_strings = [f.strip() for f in knowledge_base_str.split('\n') if f.strip() and f.strip() != '```']
            
            if not formula_strings:
                logger.info("Empty knowledge base is considered consistent.")
                return True

            PlBeliefSet = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
            kb = PlBeliefSet()

            for f_str in formula_strings:
                # Remove trailing '%' if present, as it was a previous workaround
                cleaned_f_str = f_str.rstrip('%').strip()
                if cleaned_f_str:
                    parsed_formula = self.parse_pl_formula(cleaned_f_str, constants)
                    if parsed_formula:
                        kb.add(parsed_formula)
            
            logger.info(f"DEBUG: Méthodes disponibles pour _pl_reasoner: {dir(self._pl_reasoner)}")
            
            # Contournement pour le bug JPype avec isConsistent.
            # Une KB est cohérente si elle n'entraîne pas de contradiction (false).
            # On vérifie donc si la KB entraîne la formule "false".
            try:
                Contradiction = jpype.JClass("org.tweetyproject.logics.pl.syntax.Contradiction")
                parsed_false = Contradiction()
                
                # self._pl_reasoner.query(kb, formula) retourne true si kb |= formula
                entails_contradiction = self._pl_reasoner.query(kb, parsed_false)
                is_consistent = not entails_contradiction
                logger.info(f"Vérification de cohérence via query(kb, false). Entraîne contradiction: {entails_contradiction}. Cohérent: {is_consistent}")

            except Exception as query_exc:
                logger.error(f"Erreur durant le contournement de isConsistent avec query(false): {query_exc}", exc_info=True)
                # Fallback ou lever une exception ? Pour l'instant, on lève.
                raise RuntimeError("Échec de la vérification de cohérence alternative.") from query_exc

            logger.info(f"PL Knowledge base consistency for '{knowledge_base_str}': {is_consistent}")
            return bool(is_consistent)
        except ValueError as e: # Catch parsing errors from parse_pl_formula
            logger.error(f"Error parsing formula in knowledge base for consistency check: {e}", exc_info=True)
            raise
        except jpype.JException as e:
            logger.error(f"JPype JException during PL consistency check for '{knowledge_base_str}': {e.getMessage()}", exc_info=True)
            raise RuntimeError(f"PL consistency check failed: {e.getMessage()}") from e
        except Exception as e:
            logger.error(f"Unexpected error during PL consistency check for '{knowledge_base_str}': {e}", exc_info=True)
            raise

    def pl_query(self, knowledge_base_str: str, query_formula_str: str, constants: Optional[List[str]] = None) -> bool:
        """
        Checks if a query formula is entailed by a PL knowledge base.
        Knowledge base: string of formulas, semicolon-separated.
        Query: single formula string.
        """
        logger.debug(f"Performing PL query. KB: '{knowledge_base_str}', Query: '{query_formula_str}'")
        try:
            PlBeliefSet = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
            kb = PlBeliefSet()

            formula_strings = [f.strip() for f in knowledge_base_str.split('\n') if f.strip() and f.strip() != '```']
            for f_str in formula_strings:
                cleaned_f_str = f_str.rstrip('%').strip()
                if cleaned_f_str:
                    parsed_formula = self.parse_pl_formula(cleaned_f_str, constants)
                    if parsed_formula:
                        kb.add(parsed_formula)
            
            # Nettoyer également la chaîne de la requête
            cleaned_query_str = query_formula_str.rstrip('%').strip()
            if not cleaned_query_str or cleaned_query_str == '```':
                logger.warning(f"Query string is invalid or empty after cleaning: '{query_formula_str}'")
                return False # Ou une autre gestion d'erreur appropriée

            query_formula = self.parse_pl_formula(cleaned_query_str, constants)
            if not query_formula:
                logger.warning(f"Skipping empty or invalid query after parsing: '{cleaned_query_str}'")
                return False
            
            entails = self._pl_reasoner.query(kb, query_formula)
            logger.info(f"PL Query: KB entails '{query_formula_str}'? {entails}")
            return bool(entails)
        except ValueError as e: # Catch parsing errors
            logger.error(f"Error parsing formula for PL query: {e}", exc_info=True)
            raise
        except jpype.JException as e:
            logger.error(f"JPype JException during PL query (KB: '{knowledge_base_str}', Query: '{query_formula_str}'): {e.getMessage()}", exc_info=True)
            raise RuntimeError(f"PL query failed: {e.getMessage()}") from e
        except Exception as e:
            logger.error(f"Unexpected error during PL query: {e}", exc_info=True)
            raise

    # Add other PL-specific methods as needed, e.g., model finding, transformations, etc.