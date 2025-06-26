# argumentation_analysis/agents/core/logic/first_order_logic_agent.py
import logging
import re
import json
import unicodedata
from typing import Dict, List, Optional, Any, Tuple, NamedTuple

import jpype
from semantic_kernel import Kernel
from semantic_kernel.contents import ChatHistory, ChatMessageContent
from semantic_kernel.functions import kernel_function
# This import path is for modern semantic-kernel versions.
# The environment seems to be stuck on an old version, but I'm writing the code
# for a modern one, as this is the only path forward.
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior

from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent
from .tweety_bridge import TweetyBridge

logger = logging.getLogger(__name__)

class AtomicFact(NamedTuple):
    predicate_name: str
    arguments: List[str]

class UniversalImplication(NamedTuple):
    antecedent_predicate: str
    consequent_predicate: str
    sort_of_variable: str

class ExistentialConjunction(NamedTuple):
    predicate1: str
    predicate2: str
    sort_of_variable: str

class BeliefSetBuilderPlugin:
    def __init__(self):
        self.reset()

    def reset(self):
        self._sorts: Dict[str, List[str]] = {}
        self._predicates: Dict[str, List[str]] = {}
        self._atomic_facts: List[AtomicFact] = []
        self._universal_implications: List[UniversalImplication] = []
        self._existential_conjunctions: List[ExistentialConjunction] = []

    def _normalize(self, name: str) -> str:
        # Normalize by removing spaces and also stripping any trailing parenthesized expressions,
        # which the LLM sometimes mistakenly includes.
        # e.g., "EtudiantFrançais(x)" becomes "EtudiantFrancais"
        base_name = re.sub(r'\(.*\)', '', name).strip()
        return base_name.replace(" ", "_")

    @kernel_function(description="Declare a new sort.", name="add_sort")
    def add_sort(self, sort_name: str):
        norm_sort = self._normalize(sort_name)
        if norm_sort not in self._sorts:
            self._sorts[norm_sort] = []
        return f"Sort '{norm_sort}' added."

    @kernel_function(description="Define a predicate schema.", name="add_predicate_schema")
    def add_predicate_schema(self, predicate_name: str, argument_sorts: List[str]):
        norm_pred = self._normalize(predicate_name)
        norm_args = [self._normalize(s) for s in argument_sorts]
        # Auto-create sorts if they don't exist, to make the agent more robust
        # to LLM failures to follow the strict declaration order.
        for sort_name in norm_args:
            if sort_name not in self._sorts:
                self.add_sort(sort_name)
        self._predicates[norm_pred] = norm_args
        return f"Predicate schema '{norm_pred}' declared."

    @kernel_function(description="Add an atomic fact, e.g., 'Socrates is a man'.", name="add_atomic_fact")
    def add_atomic_fact(self, fact_predicate_name: str, fact_arguments: List[str]):
        p_name = self._normalize(fact_predicate_name)
        arg_list = [self._normalize(arg) for arg in fact_arguments]

        # --- Enhanced Robustness ---
        # If the predicate schema is not defined, create it dynamically.
        # This assumes a simple 1-to-1 mapping from predicate to a sort of the same name.
        if p_name not in self._predicates:
            # We derive the sort name from the predicate name, as is common.
            # e.g., predicate 'Etudiant' implies sort 'Etudiant'.
            # This is a heuristic that works well for many simple cases.
            sort_name_for_predicate = p_name
            self.add_predicate_schema(p_name, [sort_name_for_predicate])

        # Ensure all constants and their respective sorts exist.
        expected_sorts = self._predicates[p_name]
        for i, arg_name in enumerate(arg_list):
            if i < len(expected_sorts):
                sort_name = expected_sorts[i]
                # Ensure the sort exists.
                if sort_name not in self._sorts:
                    self.add_sort(sort_name)
                # Ensure the constant is in the sort.
                if arg_name not in self._sorts[sort_name]:
                    self._sorts[sort_name].append(arg_name)

        self._atomic_facts.append(AtomicFact(p_name, arg_list))
        return f"Atomic fact '{p_name}({', '.join(arg_list)})' added."

    @kernel_function(description="Add a universal implication.", name="add_universal_implication")
    def add_universal_implication(self, impl_antecedent_predicate: str, impl_consequent_predicate: str, impl_sort_of_variable: str):
        norm_sort = self._normalize(impl_sort_of_variable)
        norm_antecedent = self._normalize(impl_antecedent_predicate)
        norm_consequent = self._normalize(impl_consequent_predicate)

        # Auto-create sort if it does not exist
        if norm_sort not in self._sorts:
            self.add_sort(norm_sort)

        # Auto-create predicate schemas if they don't exist, using the variable's sort as a default.
        if norm_antecedent not in self._predicates:
            self.add_predicate_schema(norm_antecedent, [norm_sort])
        if norm_consequent not in self._predicates:
            self.add_predicate_schema(norm_consequent, [norm_sort])

        self._universal_implications.append(UniversalImplication(
            norm_antecedent,
            norm_consequent,
            norm_sort
        ))
        return "Universal implication added."

    @kernel_function(description="Add an existential conjunction, e.g., 'Some A are B'.", name="add_existential_conjunction")
    def add_existential_conjunction(self, predicate1: str, predicate2: str, sort_of_variable: str):
        norm_sort = self._normalize(sort_of_variable)
        norm_p1 = self._normalize(predicate1)
        norm_p2 = self._normalize(predicate2)

        if norm_sort not in self._sorts:
            self.add_sort(norm_sort)
        if norm_p1 not in self._predicates:
            self.add_predicate_schema(norm_p1, [norm_sort])
        if norm_p2 not in self._predicates:
            self.add_predicate_schema(norm_p2, [norm_sort])

        self._existential_conjunctions.append(ExistentialConjunction(norm_p1, norm_p2, norm_sort))
        return "Existential conjunction added."
        
    def build_tweety_belief_set(self, tweety_bridge: "TweetyBridge") -> Optional[Any]:
        """
        Builds a FolBeliefSet programmatically by directly instantiating Java objects,
        bypassing the string parser.
        """
        try:
            if not jpype or not jpype.isJVMStarted():
                logger.error("JVM not started. Cannot build belief set.")
                return None

            # Retrieve cached Java classes from the initializer
            initializer = tweety_bridge._initializer
            FolBeliefSet = initializer.FolBeliefSet
            FolSignature = initializer.FolSignature
            Sort = initializer.Sort
            Constant = initializer.Constant
            Predicate = initializer.Predicate
            FolAtom = initializer.FolAtom
            Variable = initializer.Variable
            ForallQuantifiedFormula = initializer.ForallQuantifiedFormula
            ExistsQuantifiedFormula = initializer.ExistsQuantifiedFormula
            Implication = initializer.Implication
            Conjunction = initializer.Conjunction
            ArrayList = jpype.JClass("java.util.ArrayList")

            # 1. Create signature
            signature = FolSignature()
            
            # Add sorts and constants
            java_sorts = {}
            java_constants = {}
            for sort_name, constants in self._sorts.items():
                jsort = Sort(sort_name)
                signature.add(jsort)
                java_sorts[sort_name] = jsort
                for const_name in constants:
                    # Create the constant directly with its sort
                    jconst = Constant(const_name, jsort)
                    # The signature add method for a constant might just take the constant,
                    # as the sort is now part of the constant object itself.
                    signature.add(jconst)
                    java_constants[const_name] = jconst

            # Add predicates
            java_predicates = {}
            for pred_name, arg_sort_names in self._predicates.items():
                j_arg_sorts = ArrayList()
                for s_name in arg_sort_names:
                    if s_name in java_sorts:
                        j_arg_sorts.add(java_sorts[s_name])
                    else:
                        logger.warning(f"Sort '{s_name}' for predicate '{pred_name}' not found. Skipping.")
                jpred = Predicate(pred_name, j_arg_sorts)
                signature.add(jpred)
                java_predicates[pred_name] = jpred

            # 2. Create belief set with the signature
            # The constructor FolBeliefSet(signature) does not exist.
            # We create an empty belief set and add formulas to it. The signature is managed internally.
            belief_set = FolBeliefSet()
            # The signature is implicitly part of the formulas added below.
            # However, we must explicitly add all signature elements (sorts, constants, predicates)
            # to the signature object that will passed to the parser later if needed.
            # For programmatic creation, the signature object is built first, and then the belief set.
            # Let's add all signature elements to the belief set an other way.
            # It seems that signature.add() returns void, so it modifies the signature in place.
            # The belief set might be taking formulas, and that's all.

            # 3. Add formulas
            # Add atomic facts
            for fact in self._atomic_facts:
                if fact.predicate_name in java_predicates:
                    j_pred = java_predicates[fact.predicate_name]
                    j_args = ArrayList()
                    for arg_name in fact.arguments:
                        if arg_name in java_constants:
                            j_args.add(java_constants[arg_name])
                        else:
                            # It might be a variable if we extend this later
                            logger.warning(f"Constant '{arg_name}' not found for fact '{fact.predicate_name}'. Skipping argument.")
                    
                    if j_args.size() == len(fact.arguments):
                         belief_set.add(FolAtom(j_pred, j_args))

            # Add universal implications
            for impl in self._universal_implications:
                # Normalize the variable name to be an ASCII upper-case character
                base_char = impl.sort_of_variable[0]
                normalized_char = unicodedata.normalize('NFKD', base_char).encode('ascii', 'ignore').decode('ascii')
                var_name = normalized_char.upper() if normalized_char else 'X' # Default to X if char is exotic

                # Retrieve the corresponding Sort object
                j_sort = java_sorts.get(impl.sort_of_variable)
                if not j_sort:
                    logger.error(f"Sort '{impl.sort_of_variable}' not found for universal implication. Cannot create typed variable.")
                    continue # Skip this implication
                
                j_var = Variable(var_name, j_sort)
                
                # Antecedent
                ante_pred = java_predicates.get(impl.antecedent_predicate)
                ante_args = ArrayList()
                ante_args.add(j_var)
                antecedent = FolAtom(ante_pred, ante_args)
                
                # Consequent
                cons_pred = java_predicates.get(impl.consequent_predicate)
                cons_args = ArrayList()
                cons_args.add(j_var)
                consequent = FolAtom(cons_pred, cons_args)

                implication = Implication(antecedent, consequent)
                
                quantified_formula = ForallQuantifiedFormula(implication, j_var)
                belief_set.add(quantified_formula)

            # Add existential conjunctions
            for ex in self._existential_conjunctions:
                base_char = ex.sort_of_variable[0]
                normalized_char = unicodedata.normalize('NFKD', base_char).encode('ascii', 'ignore').decode('ascii')
                var_name = normalized_char.upper() if normalized_char else 'X'

                j_sort = java_sorts.get(ex.sort_of_variable)
                if not j_sort:
                    logger.error(f"Sort '{ex.sort_of_variable}' not found for existential conjunction.")
                    continue
                
                j_var = Variable(var_name, j_sort)

                p1 = java_predicates.get(ex.predicate1)
                p1_args = ArrayList()
                p1_args.add(j_var)
                atom1 = FolAtom(p1, p1_args)
                
                p2 = java_predicates.get(ex.predicate2)
                p2_args = ArrayList()
                p2_args.add(j_var)
                atom2 = FolAtom(p2, p2_args)

                conjunction = Conjunction(atom1, atom2)
                quantified_formula = ExistsQuantifiedFormula(conjunction, j_var)
                belief_set.add(quantified_formula)

            logger.info(f"Programmatically built belief set: {belief_set.toString()}")
            return belief_set

        except Exception as e:
            logger.error(f"Error programmatically building belief set: {e}", exc_info=True)
            raise

class FirstOrderLogicAgent(BaseLogicAgent):
    def __init__(self, kernel: Kernel, tweety_bridge: "TweetyBridge"):
        super().__init__(kernel, "FirstOrderLogicAgent", "FOL", "SYSTEM PROMPT")
        self._tweety_bridge = tweety_bridge
        self._builder_plugin = BeliefSetBuilderPlugin()
        self.service = None  # Will be set in setup_agent_components
        
    async def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None):
        self._builder_plugin.reset()
        chat = ChatHistory(system_message=self.system_prompt)
        chat.add_user_message(text)
        
        settings_class = self.service.get_prompt_execution_settings_class()
        execution_settings = settings_class(
            service_id=self._llm_service_id,
            function_choice_behavior=FunctionChoiceBehavior.Auto()
        )

        try:
            # This is the modern API call I'm aiming for.
            result = await self.service.get_chat_message_content(
                chat_history=chat,
                settings=execution_settings,
                kernel=self._kernel
            )
            
            java_belief_set = self._builder_plugin.build_tweety_belief_set(self.tweety_bridge)
            
            if java_belief_set is None:
                return None, "Failed to build belief set during Java object construction."
            
            # If no formulas were added (e.g., LLM returned no tool calls), it's not an error,
            # but the resulting belief set is empty and should be treated as a failure to extract.
            if java_belief_set.size() == 0:
                logger.warning("Belief set construction resulted in an empty set. Likely no logical structure was found in the text.")
                return None, "Could not extract any logical structure from the input text."

            belief_set_content = java_belief_set.toString()
            from .belief_set import FirstOrderBeliefSet
            return FirstOrderBeliefSet(content=belief_set_content, java_object=java_belief_set), "Success"

        except Exception as e:
            logger.error(f"Error in text_to_belief_set: {e}", exc_info=True)
            raise e

    def _create_belief_set_from_data(self, data, context: Optional[Dict[str, Any]] = None):
        raise NotImplementedError

    async def generate_queries(self, text: str, belief_set: "FirstOrderBeliefSet", num_queries: int = 3) -> List[str]:
        """
        Génère des requêtes logiques pertinentes en utilisant le LLM.
        """
        logger.info("Génération de requêtes FOL...")

        prompt = f"""
        Vous êtes un expert en logique du premier ordre. Votre tâche est de générer des requêtes pertinentes en
        logique du premier ordre pour interroger un ensemble de croyances (belief set) donné.

        Voici le texte source:
        {text}

        Voici l'ensemble de croyances en logique du premier ordre:
        {belief_set.content}

        Générez {num_queries} requêtes pertinentes en logique du premier ordre qui permettraient de vérifier des implications
        importantes ou des conclusions intéressantes à partir de cet ensemble de croyances. Utilisez la syntaxe de TweetyProject.

        Règles importantes:
        1. Les requêtes doivent être des formules bien formées en logique du premier ordre.
        2. Utilisez un vocabulaire (prédicats, constantes) cohérent avec l'ensemble de croyances.
        3. Chaque requête doit être sur une ligne séparée.
        4. N'incluez AUCUN commentaire ou texte superflu, seulement les requêtes.

        Répondez uniquement avec les requêtes.
        """

        try:
            # Création d'un historique de chat simple pour l'appel
            chat_history = ChatHistory()
            chat_history.add_user_message(prompt)

            # Création des settings pour l'appel
            settings_class = self.service.get_prompt_execution_settings_class()
            execution_settings = settings_class(
                service_id=self._llm_service_id
            )

            # Appel direct au service LLM
            result = await self.service.get_chat_message_content(
                chat_history=chat_history,
                settings=execution_settings,
                kernel=self._kernel
            )

            # Le résultat est un ChatMessageContent, on prend son contenu.
            queries_text = str(result)
            
            if not queries_text:
                logger.warning("Le LLM n'a retourné aucune requête.")
                return []

            # Extraire les requêtes individuelles, ignorer les lignes vides et nettoyer chaque requête.
            raw_queries = [q.strip() for q in queries_text.split('\n') if q.strip()]
            
            # Nettoyer les-préfixes numériques (ex: "1. ", "2. ") et les blocs de code markdown.
            temp_queries = [re.sub(r'^\s*\d+\.\s*', '', q) for q in raw_queries]
            # Supprimer les ``` au début et à la fin
            cleaned_queries = [q.replace('```', '').strip() for q in temp_queries if q.strip() and q.strip() != '```']

            logger.info(f"Génération de {len(cleaned_queries)} requêtes candidates après nettoyage.")
            queries = cleaned_queries
            return queries

        except Exception as e:
            logger.error(f"Erreur lors de la génération des requêtes FOL: {e}", exc_info=True)
            return []

    def get_agent_capabilities(self):
        raise NotImplementedError

    def get_response(self, query, context):
        raise NotImplementedError

    def interpret_results(self, results, context: Optional[Dict[str, Any]] = None):
        raise NotImplementedError

    def invoke_single(self, argument, context):
        raise NotImplementedError

    def setup_agent_components(self, llm_service_id: str):
        """
        Configure les composants de l'agent, y compris le service LLM et les plugins.
        """
        super().setup_agent_components(llm_service_id)
        self.service = self._kernel.get_service(llm_service_id)
        if not self.service:
            raise ValueError(f"LLM Service '{llm_service_id}' not found in kernel.")
        self._kernel.add_plugin(self._builder_plugin, "BeliefBuilder")

    def validate_argument(self, argument, context: Optional[Dict[str, Any]] = None):
        raise NotImplementedError

    def validate_formula(self, formula: str, context: Optional[Dict[str, Any]] = None):
        raise NotImplementedError
        
    async def is_consistent(self, belief_set):
        if not belief_set.java_object:
            return False, "No Java object in belief set."
        return self.tweety_bridge.check_consistency(belief_set.java_object)

    async def execute_query(self, belief_set, query):
        if not belief_set.java_object:
            return None, "No Java object in belief set."
        return self.tweety_bridge._fol_handler.fol_query(belief_set.java_object, query)