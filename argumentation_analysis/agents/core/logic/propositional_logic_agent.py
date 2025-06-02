# argumentation_analysis/agents/core/logic/propositional_logic_agent.py
"""
Agent spécialisé pour la logique propositionnelle.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple

from semantic_kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments # ADDED

from ..abc.agent_bases import BaseLogicAgent # MODIFIED
from .belief_set import BeliefSet, PropositionalBeliefSet
from .tweety_bridge import TweetyBridge

# Importer les prompts depuis le module pl existant
from ..pl.prompts import (
    prompt_text_to_pl_v8 as PROMPT_TEXT_TO_PL,
    prompt_gen_pl_queries_v8 as PROMPT_GEN_PL_QUERIES,
    prompt_interpret_pl_v8 as PROMPT_INTERPRET_PL
)
# Importer les instructions système
from ..pl.pl_definitions import PL_AGENT_INSTRUCTIONS # ADDED

# Configuration du logger
logger = logging.getLogger(__name__) # MODIFIED

class PropositionalLogicAgent(BaseLogicAgent): # MODIFIED
    """
    Agent spécialisé pour la logique propositionnelle, héritant de BaseLogicAgent.
    Utilise TweetyProject via TweetyBridge pour les opérations logiques.
    """
    
    def __init__(self, kernel: Kernel, agent_name: str = "PropositionalLogicAgent"): # MODIFIED
        """
        Initialise un agent de logique propositionnelle.
        
        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            agent_name: Le nom de l'agent.
        """
        super().__init__(kernel,
                         agent_name=agent_name,
                         logic_type_name="PL",
                         system_prompt=PL_AGENT_INSTRUCTIONS)
        # _tweety_bridge sera initialisé dans setup_agent_components
        # _plugin_name est maintenant self.name, hérité de BaseAgent
    
    def get_agent_capabilities(self) -> Dict[str, Any]: # ADDED
        """Retourne les capacités spécifiques de l'agent PL."""
        return {
            "text_to_belief_set": "Translates natural language text to a Propositional Logic belief set.",
            "generate_queries": "Generates relevant PL queries based on text and a belief set.",
            "execute_query": "Executes a PL query against a belief set using Tweety.",
            "interpret_results": "Interprets the results of PL queries in natural language.",
            "validate_formula": "Validates the syntax of a PL formula."
        }

    def setup_agent_components(self, llm_service_id: str) -> None: # ADDED
        """
        Configure les composants spécifiques de l'agent PL dans le kernel SK.
        """
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants pour {self.name}...")

        # Initialisation de TweetyBridge
        self._tweety_bridge = TweetyBridge(logic_type="pl")
        self.logger.info(f"TweetyBridge initialisé pour la logique : {self.logic_type}")

        # Vérifier si la JVM est prête (TweetyBridge devrait le gérer ou exposer une méthode)
        if not self.tweety_bridge.is_jvm_ready(): # Supposant que TweetyBridge a cette méthode
            self.logger.error("La JVM n'est pas prête. Les fonctionnalités de TweetyBridge pourraient ne pas fonctionner.")
            # On pourrait lever une exception ici ou permettre à l'agent de continuer avec des capacités limitées.
            # Pour l'instant, on logue une erreur.

        # Configuration des settings LLM
        prompt_execution_settings = None
        if self._llm_service_id:
            try:
                prompt_execution_settings = self.sk_kernel.get_prompt_execution_settings_from_service_id(
                    self._llm_service_id
                )
                self.logger.debug(f"Settings LLM récupérés pour {self.name}.")
            except Exception as e:
                self.logger.warning(f"Impossible de récupérer les settings LLM pour {self.name}: {e}")
        
        # Enregistrement des Fonctions Sémantiques PL
        semantic_functions_map = {
            "TextToPLBeliefSet": PROMPT_TEXT_TO_PL,
            "GeneratePLQueries": PROMPT_GEN_PL_QUERIES,
            "InterpretPLResults": PROMPT_INTERPRET_PL
        }
        
        descriptions_map = {
            "TextToPLBeliefSet": "Translates natural language text to a Propositional Logic belief set (Tweety syntax).",
            "GeneratePLQueries": "Generates relevant Propositional Logic queries based on text and a belief set (Tweety syntax).",
            "InterpretPLResults": "Interprets the results of Propositional Logic queries in natural language."
        }

        for func_name, prompt_template in semantic_functions_map.items():
            try:
                if not prompt_template or not isinstance(prompt_template, str):
                    self.logger.error(f"Prompt invalide pour {self.name}.{func_name}. Skipping.")
                    continue
                
                self.sk_kernel.add_function(
                    prompt=prompt_template,
                    plugin_name=self.name,
                    function_name=func_name,
                    description=descriptions_map.get(func_name, f"{func_name} function"),
                    prompt_execution_settings=prompt_execution_settings
                )
                self.logger.info(f"Fonction sémantique {self.name}.{func_name} ajoutée.")
            except Exception as e:
                self.logger.error(f"Erreur lors de l'ajout de la fonction sémantique {self.name}.{func_name}: {e}", exc_info=True)
        
        self.logger.info(f"Composants pour {self.name} configurés.")

    async def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[BeliefSet], str]: # MODIFIED (async, signature)
        """
        Convertit un texte en ensemble de croyances propositionnelles.
        """
        self.logger.info(f"Conversion de texte en ensemble de croyances propositionnelles pour le texte : '{text[:100]}...'")
        
        try:
            arguments = KernelArguments(input=text) # MODIFIED
            result = await self.sk_kernel.invoke( # MODIFIED (await)
                plugin_name=self.name, # MODIFIED
                function_name="TextToPLBeliefSet", # MODIFIED
                arguments=arguments
            )
            belief_set_content = str(result) # MODIFIED (SK result to str)
            
            if not belief_set_content or len(belief_set_content.strip()) == 0:
                self.logger.error("La conversion a produit un ensemble de croyances vide.") # MODIFIED (logger)
                return None, "La conversion a produit un ensemble de croyances vide."
            
            # Valider l'ensemble de croyances avec TweetyBridge
            is_valid, validation_msg = self.tweety_bridge.validate_belief_set(belief_set_content, logic_type=self.logic_type) # MODIFIED
            if not is_valid:
                self.logger.error(f"Ensemble de croyances invalide: {validation_msg}") # MODIFIED (logger)
                return None, f"Ensemble de croyances invalide: {validation_msg}"
            
            belief_set = PropositionalBeliefSet(belief_set_content) # MODIFIED (moved after validation)
            
            self.logger.info("Conversion en BeliefSet réussie.") # MODIFIED (logger)
            return belief_set, "Conversion réussie."
        
        except Exception as e:
            error_msg = f"Erreur lors de la conversion du texte en ensemble de croyances: {str(e)}"
            self.logger.error(error_msg, exc_info=True) # MODIFIED (logger)
            return None, error_msg
    
    async def generate_queries(self, text: str, belief_set: BeliefSet, context: Optional[Dict[str, Any]] = None) -> List[str]: # MODIFIED (async, signature)
        """
        Génère des requêtes logiques propositionnelles pertinentes.
        """
        self.logger.info(f"Génération de requêtes PL pour le texte : '{text[:100]}...'") # MODIFIED (logger)
        
        try:
            arguments = KernelArguments(input=text, belief_set=belief_set.to_string_representation()) # MODIFIED
            result = await self.sk_kernel.invoke( # MODIFIED (await)
                plugin_name=self.name, # MODIFIED
                function_name="GeneratePLQueries", # MODIFIED
                arguments=arguments
            )
            queries_text = str(result) # MODIFIED (SK result to str)
            
            queries = [q.strip() for q in queries_text.split('\n') if q.strip()]
            
            valid_queries = []
            for query in queries:
                if self.validate_formula(query): # MODIFIED (use agent's method)
                    valid_queries.append(query)
                else:
                    self.logger.warning(f"Requête invalide générée et ignorée: {query}") # MODIFIED (logger)
            
            self.logger.info(f"Génération de {len(valid_queries)} requêtes PL valides.") # MODIFIED (logger)
            return valid_queries
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération des requêtes PL: {str(e)}", exc_info=True) # MODIFIED (logger)
            return []
    
    def execute_query(self, belief_set: BeliefSet, query: str) -> Tuple[Optional[bool], str]: # Signature OK
        """
        Exécute une requête logique propositionnelle sur un ensemble de croyances.
        """
        self.logger.info(f"Exécution de la requête PL: '{query}' sur le BeliefSet.") # MODIFIED (logger)
        
        try:
            bs_str = belief_set.to_string_representation()
            
            if not self.validate_formula(query): # ADDED validation
                msg = f"Requête invalide: {query}"
                self.logger.error(msg)
                return None, f"FUNC_ERROR: {msg}"

            is_entailed, raw_output = self.tweety_bridge.execute_query( # MODIFIED (direct call to tweety_bridge)
                belief_set_str=bs_str,
                query_str=query,
                logic_type=self.logic_type
            )
            
            self.logger.info(f"Résultat de l'exécution pour '{query}': {is_entailed}, Output: '{raw_output}'") # MODIFIED (logger)
            return is_entailed, raw_output
        
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête PL '{query}': {str(e)}"
            self.logger.error(error_msg, exc_info=True) # MODIFIED (logger)
            return None, f"FUNC_ERROR: {error_msg}"
    
    async def interpret_results(self, text: str, belief_set: BeliefSet,
                                queries: List[str], results: List[Tuple[Optional[bool], str]],
                                context: Optional[Dict[str, Any]] = None) -> str: # MODIFIED (async, signature)
        """
        Interprète les résultats des requêtes logiques propositionnelles.
        """
        self.logger.info("Interprétation des résultats des requêtes PL...") # MODIFIED (logger)
        
        try:
            queries_str = "\n".join(queries)
            results_messages_str = "\n".join([res_tuple[1] for res_tuple in results]) # MODIFIED (extract messages)

            arguments = KernelArguments( # MODIFIED
                input=text,
                belief_set=belief_set.to_string_representation(),
                queries=queries_str,
                tweety_result=results_messages_str
            )
            
            result = await self.sk_kernel.invoke( # MODIFIED (await)
                plugin_name=self.name, # MODIFIED
                function_name="InterpretPLResults", # MODIFIED
                arguments=arguments
            )
            interpretation = str(result) # MODIFIED (SK result to str)
            
            self.logger.info("Interprétation des résultats PL terminée.") # MODIFIED (logger)
            return interpretation
        
        except Exception as e:
            error_msg = f"Erreur lors de l'interprétation des résultats PL: {str(e)}"
            self.logger.error(error_msg, exc_info=True) # MODIFIED (logger)
            return f"Erreur d'interprétation: {error_msg}"

    def validate_formula(self, formula: str) -> bool: # ADDED
        """
        Valide la syntaxe d'une formule propositionnelle en utilisant TweetyBridge.
        """
        self.logger.debug(f"Validation de la formule PL: '{formula}'")
        try:
            is_valid, message = self.tweety_bridge.validate_formula(formula_str=formula, logic_type=self.logic_type)
            if not is_valid:
                self.logger.warning(f"Formule PL invalide: '{formula}'. Message: {message}")
            return is_valid
        except Exception as e:
            self.logger.error(f"Erreur lors de la validation de la formule PL '{formula}': {e}", exc_info=True)
            return False