# argumentation_analysis/agents/core/logic/propositional_logic_agent.py
"""
Agent spécialisé pour la logique propositionnelle (PL).

Ce module définit `PropositionalLogicAgent`, une classe qui hérite de
`BaseLogicAgent` et implémente les fonctionnalités spécifiques pour interagir
avec la logique propositionnelle. Il utilise `TweetyBridge` pour la communication
avec TweetyProject et s'appuie sur des prompts sémantiques définis dans
`argumentation_analysis.agents.core.pl.prompts` pour la conversion
texte-vers-PL, la génération de requêtes et l'interprétation des résultats.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple

from semantic_kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments 

from ..abc.agent_bases import BaseLogicAgent 
from .belief_set import BeliefSet, PropositionalBeliefSet
from .tweety_bridge import TweetyBridge

# Importer les prompts depuis le module pl existant
from ..pl.prompts import (
    prompt_text_to_pl_v8 as PROMPT_TEXT_TO_PL,
    prompt_gen_pl_queries_v8 as PROMPT_GEN_PL_QUERIES,
    prompt_interpret_pl_v8 as PROMPT_INTERPRET_PL
)
# Importer les instructions système
from ..pl.pl_definitions import PL_AGENT_INSTRUCTIONS 

# Configuration du logger
logger = logging.getLogger(__name__) 

class PropositionalLogicAgent(BaseLogicAgent): 
    """
    Agent spécialisé pour la logique propositionnelle (PL).

    Cet agent étend `BaseLogicAgent` pour fournir des capacités de traitement
    spécifiques à la logique propositionnelle. Il intègre des fonctions sémantiques
    pour traduire le langage naturel en ensembles de croyances PL, générer des
    requêtes PL pertinentes, exécuter ces requêtes via `TweetyBridge`, et
    interpréter les résultats en langage naturel.

    Attributes:
        _tweety_bridge (TweetyBridge): Instance de `TweetyBridge` configurée pour la PL.
    """
    
    def __init__(self, kernel: Kernel, agent_name: str = "PropositionalLogicAgent"): 
        """
        Initialise une instance de `PropositionalLogicAgent`.

        :param kernel: Le kernel Semantic Kernel à utiliser pour les fonctions sémantiques.
        :type kernel: Kernel
        :param agent_name: Le nom de l'agent, par défaut "PropositionalLogicAgent".
        :type agent_name: str
        """
        super().__init__(kernel,
                         agent_name=agent_name,
                         logic_type_name="PL",
                         system_prompt=PL_AGENT_INSTRUCTIONS)
    
    def get_agent_capabilities(self) -> Dict[str, Any]: 
        """
        Retourne un dictionnaire décrivant les capacités spécifiques de cet agent PL.

        :return: Un dictionnaire mappant les noms des capacités à leurs descriptions.
        :rtype: Dict[str, Any]
        """
        return {
            "text_to_belief_set": "Translates natural language text to a Propositional Logic belief set.",
            "generate_queries": "Generates relevant PL queries based on text and a belief set.",
            "execute_query": "Executes a PL query against a belief set using Tweety.",
            "interpret_results": "Interprets the results of PL queries in natural language.",
            "validate_formula": "Validates the syntax of a PL formula."
        }

    def setup_agent_components(self, llm_service_id: str) -> None: 
        """
        Configure les composants spécifiques de l'agent de logique propositionnelle.

        Initialise `TweetyBridge` pour la logique propositionnelle et enregistre
        les fonctions sémantiques nécessaires (TextToPLBeliefSet, GeneratePLQueries,
        InterpretPLResults) dans le kernel Semantic Kernel.

        :param llm_service_id: L'ID du service LLM à utiliser pour les fonctions sémantiques.
        :type llm_service_id: str
        """
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants pour {self.name}...")

        self._tweety_bridge = TweetyBridge(logic_type="pl")
        self.logger.info(f"TweetyBridge initialisé pour la logique : {self.logic_type}")

        if not self.tweety_bridge.is_jvm_ready(): 
            self.logger.error("La JVM n'est pas prête. Les fonctionnalités de TweetyBridge pourraient ne pas fonctionner.")
            
        prompt_execution_settings = None
        if self._llm_service_id:
            try:
                prompt_execution_settings = self.sk_kernel.get_prompt_execution_settings_from_service_id(
                    self._llm_service_id
                )
                self.logger.debug(f"Settings LLM récupérés pour {self.name}.")
            except Exception as e:
                self.logger.warning(f"Impossible de récupérer les settings LLM pour {self.name}: {e}")
        
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

    async def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[BeliefSet], str]: 
        """
        Convertit un texte en langage naturel en un ensemble de croyances propositionnelles.

        Utilise la fonction sémantique "TextToPLBeliefSet" pour la conversion,
        puis valide l'ensemble de croyances généré avec `TweetyBridge`.

        :param text: Le texte en langage naturel à convertir.
        :type text: str
        :param context: Un dictionnaire optionnel de contexte (non utilisé actuellement).
        :type context: Optional[Dict[str, Any]]
        :return: Un tuple contenant l'objet `PropositionalBeliefSet` si la conversion
                 et la validation réussissent, et un message de statut.
                 Retourne (None, message_erreur) en cas d'échec.
        :rtype: Tuple[Optional[BeliefSet], str]
        """
        self.logger.info(f"Conversion de texte en ensemble de croyances propositionnelles pour le texte : '{text[:100]}...'")
        
        try:
            arguments = KernelArguments(input=text) 
            result = await self.sk_kernel.invoke( 
                plugin_name=self.name, 
                function_name="TextToPLBeliefSet", 
                arguments=arguments
            )
            belief_set_content = str(result) 
            
            if not belief_set_content or len(belief_set_content.strip()) == 0:
                self.logger.error("La conversion a produit un ensemble de croyances vide.") 
                return None, "La conversion a produit un ensemble de croyances vide."
            
            is_valid, validation_msg = self.tweety_bridge.validate_belief_set(belief_set_content, logic_type=self.logic_type) 
            if not is_valid:
                self.logger.error(f"Ensemble de croyances invalide: {validation_msg}") 
                return None, f"Ensemble de croyances invalide: {validation_msg}"
            
            belief_set = PropositionalBeliefSet(belief_set_content) 
            
            self.logger.info("Conversion en BeliefSet réussie.") 
            return belief_set, "Conversion réussie."
        
        except Exception as e:
            error_msg = f"Erreur lors de la conversion du texte en ensemble de croyances: {str(e)}"
            self.logger.error(error_msg, exc_info=True) 
            return None, error_msg
    
    async def generate_queries(self, text: str, belief_set: BeliefSet, context: Optional[Dict[str, Any]] = None) -> List[str]: 
        """
        Génère des requêtes logiques propositionnelles pertinentes à partir d'un texte et d'un ensemble de croyances.

        Utilise la fonction sémantique "GeneratePLQueries". Les requêtes générées
        sont ensuite validées syntaxiquement.

        :param text: Le texte en langage naturel source.
        :type text: str
        :param belief_set: L'ensemble de croyances PL associé.
        :type belief_set: BeliefSet
        :param context: Un dictionnaire optionnel de contexte (non utilisé actuellement).
        :type context: Optional[Dict[str, Any]]
        :return: Une liste de chaînes de caractères, chacune étant une requête PL valide.
                 Retourne une liste vide en cas d'erreur.
        :rtype: List[str]
        """
        self.logger.info(f"Génération de requêtes PL pour le texte : '{text[:100]}...'") 
        
        try:
            arguments = KernelArguments(input=text, belief_set=belief_set.content) 
            result = await self.sk_kernel.invoke( 
                plugin_name=self.name, 
                function_name="GeneratePLQueries", 
                arguments=arguments
            )
            queries_text = str(result) 
            
            queries = [q.strip() for q in queries_text.split('\n') if q.strip()]
            
            valid_queries = []
            for query in queries:
                if self.validate_formula(query): 
                    valid_queries.append(query)
                else:
                    self.logger.warning(f"Requête invalide générée et ignorée: {query}") 
            
            self.logger.info(f"Génération de {len(valid_queries)} requêtes PL valides.") 
            return valid_queries
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération des requêtes PL: {str(e)}", exc_info=True) 
            return []
    
    def execute_query(self, belief_set: BeliefSet, query: str) -> Tuple[Optional[bool], str]: 
        """
        Exécute une requête logique propositionnelle sur un ensemble de croyances donné.

        Valide d'abord la syntaxe de la requête, puis utilise `TweetyBridge`
        pour exécuter la requête contre le contenu de `belief_set`.

        :param belief_set: L'ensemble de croyances PL sur lequel exécuter la requête.
        :type belief_set: BeliefSet
        :param query: La requête PL à exécuter.
        :type query: str
        :return: Un tuple contenant le résultat booléen de la requête (`True` si conséquence,
                 `False` sinon, `None` si indéterminé ou erreur) et la sortie brute
                 de `TweetyBridge` (ou un message d'erreur).
        :rtype: Tuple[Optional[bool], str]
        """
        self.logger.info(f"Exécution de la requête PL: '{query}' sur le BeliefSet.") 
        
        try:
            bs_str = belief_set.content
            
            if not self.validate_formula(query): 
                msg = f"Requête invalide: {query}"
                self.logger.error(msg)
                return None, f"FUNC_ERROR: {msg}"

            is_entailed, raw_output = self.tweety_bridge.execute_pl_query( 
                belief_set_str=bs_str,
                query_str=query
                # logic_type est géré par execute_pl_query
            )
            
            self.logger.info(f"Résultat de l'exécution pour '{query}': {is_entailed}, Output: '{raw_output}'") 
            return is_entailed, raw_output
        
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête PL '{query}': {str(e)}"
            self.logger.error(error_msg, exc_info=True) 
            return None, f"FUNC_ERROR: {error_msg}"
    
    async def interpret_results(self, text: str, belief_set: BeliefSet,
                                queries: List[str], results: List[Tuple[Optional[bool], str]],
                                context: Optional[Dict[str, Any]] = None) -> str: 
        """
        Interprète les résultats d'une série de requêtes logiques propositionnelles en langage naturel.

        Utilise la fonction sémantique "InterpretPLResults" pour générer une explication
        basée sur le texte original, l'ensemble de croyances, les requêtes posées et
        les résultats obtenus de Tweety.

        :param text: Le texte original en langage naturel.
        :type text: str
        :param belief_set: L'ensemble de croyances PL utilisé.
        :type belief_set: BeliefSet
        :param queries: La liste des requêtes PL qui ont été exécutées.
        :type queries: List[str]
        :param results: La liste des résultats (tuples booléen/None, message_brut)
                        correspondant à chaque requête.
        :type results: List[Tuple[Optional[bool], str]]
        :param context: Un dictionnaire optionnel de contexte (non utilisé actuellement).
        :type context: Optional[Dict[str, Any]]
        :return: Une chaîne de caractères contenant l'interprétation en langage naturel
                 des résultats, ou un message d'erreur.
        :rtype: str
        """
        self.logger.info("Interprétation des résultats des requêtes PL...") 
        
        try:
            queries_str = "\n".join(queries)
            results_messages_str = "\n".join([res_tuple[1] for res_tuple in results]) 

            arguments = KernelArguments( 
                input=text,
                belief_set=belief_set.content,
                queries=queries_str,
                tweety_result=results_messages_str
            )
            
            result = await self.sk_kernel.invoke( 
                plugin_name=self.name, 
                function_name="InterpretPLResults", 
                arguments=arguments
            )
            interpretation = str(result) 
            
            self.logger.info("Interprétation des résultats PL terminée.") 
            return interpretation
        
        except Exception as e:
            error_msg = f"Erreur lors de l'interprétation des résultats PL: {str(e)}"
            self.logger.error(error_msg, exc_info=True) 
            return f"Erreur d'interprétation: {error_msg}"

    def validate_formula(self, formula: str) -> bool: 
        """
        Valide la syntaxe d'une formule propositionnelle.

        Utilise la méthode `validate_formula` de `TweetyBridge` configurée pour la PL.

        :param formula: La formule PL à valider.
        :type formula: str
        :return: `True` si la formule est syntaxiquement valide, `False` sinon.
        :rtype: bool
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