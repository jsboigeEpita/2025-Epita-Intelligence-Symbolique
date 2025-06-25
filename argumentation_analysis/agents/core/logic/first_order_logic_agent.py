# argumentation_analysis/agents/core/logic/first_order_logic_agent.py
import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple, NamedTuple

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
        # Simple normalization for the sake of reconstruction
        return name.lower().replace(" ", "_")

    @kernel_function(description="Declare a new sort.", name="add_sort")
    def add_sort(self, sort_name: str):
        norm_sort = self._normalize(sort_name)
        if norm_sort not in self._sorts:
            self._sorts[norm_sort] = []
        return f"Sort '{norm_sort}' added."

    @kernel_function(description="Add a constant to a sort.", name="add_constant_to_sort")
    def add_constant_to_sort(self, constant_name: str, sort_name: str):
        norm_const = self._normalize(constant_name)
        norm_sort = self._normalize(sort_name)
        if norm_sort not in self._sorts:
            self.add_sort(norm_sort)
        if norm_const not in self._sorts[norm_sort]:
            self._sorts[norm_sort].append(norm_const)
        return f"Constant '{norm_const}' added to sort '{norm_sort}'."

    @kernel_function(description="Define a predicate schema.", name="add_predicate_schema")
    def add_predicate_schema(self, predicate_name: str, argument_sorts: List[str]):
        norm_pred = self._normalize(predicate_name)
        norm_args = [self._normalize(s) for s in argument_sorts]
        self._predicates[norm_pred] = norm_args
        return f"Predicate schema '{norm_pred}' declared."

    @kernel_function(description="Add an atomic fact.", name="add_atomic_fact")
    def add_atomic_fact(self, fact_predicate_name: str, fact_arguments: List[str]):
        p_name = self._normalize(fact_predicate_name)
        arg_list = [self._normalize(arg) for arg in fact_arguments]
        self._atomic_facts.append(AtomicFact(p_name, arg_list))
        return "Atomic fact added."

    @kernel_function(description="Add a universal implication.", name="add_universal_implication")
    def add_universal_implication(self, impl_antecedent_predicate: str, impl_consequent_predicate: str, impl_sort_of_variable: str):
        self._universal_implications.append(UniversalImplication(
            self._normalize(impl_antecedent_predicate),
            self._normalize(impl_consequent_predicate),
            self._normalize(impl_sort_of_variable)
        ))
        return "Universal implication added."
        
    def _build_fologic_string(self) -> Optional[str]:
        if not any([self._sorts, self._predicates, self._atomic_facts, self._universal_implications]):
            return None

        lines = []
        # Sorts and constants
        for sort_name, constants in self._sorts.items():
            if constants:
                constant_str = ", ".join(constants)
                lines.append(f"{sort_name} = {{{constant_str}}}")
        if self._sorts:
            lines.append("")

        # Predicates
        if self._predicates:
            for pred_name, arg_sorts in self._predicates.items():
                arg_str = ", ".join(arg_sorts)
                lines.append(f"type({pred_name}({arg_str}))")
            lines.append("")

        # Formulas
        for fact in self._atomic_facts:
            args_str = ", ".join(fact.arguments)
            lines.append(f"{fact.predicate_name}({args_str}).")
        
        for impl in self._universal_implications:
            var_name = impl.sort_of_variable[0].upper()
            lines.append(f"forall {var_name}: ({impl.sort_of_variable}) (!{impl.antecedent_predicate}({var_name}) || {impl.consequent_predicate}({var_name}))")

        return "\\n".join(lines)

    def build_tweety_belief_set(self, tweety_bridge: "TweetyBridge") -> Optional[Any]:
        fologic_string = self._build_fologic_string()
        if not fologic_string:
            return None
        logger.info(f"Generated .fologic string:\\n{fologic_string}")
        try:
            belief_set_obj = tweety_bridge.create_belief_set_from_string(fologic_string)
            if belief_set_obj is None:
                logger.error("Tweety parser returned None.")
                return None
            return belief_set_obj
        except Exception as e:
            logger.error(f"Error parsing .fologic string: {e}", exc_info=True)
            raise

class FirstOrderLogicAgent(BaseLogicAgent):
    def __init__(self, kernel: Kernel, tweety_bridge: "TweetyBridge", service_id: str):
        super().__init__(kernel, "FirstOrderLogicAgent", "FOL", "SYSTEM PROMPT")
        self.tweety_bridge = tweety_bridge
        self._builder_plugin = BeliefSetBuilderPlugin()
        self.service = kernel.get_service(service_id)
        self._llm_service_id = service_id
        if self.service:
            self._kernel.add_plugin(self._builder_plugin, "BeliefBuilder")
        
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
                return None, "Failed to build belief set."

            belief_set_content = java_belief_set.toString()
            from .belief_set import FirstOrderBeliefSet
            return FirstOrderBeliefSet(content=belief_set_content, java_object=java_belief_set), "Success"

        except Exception as e:
            logger.error(f"Error in text_to_belief_set: {e}", exc_info=True)
            raise e

    def _create_belief_set_from_data(self, data, context: Optional[Dict[str, Any]] = None):
        raise NotImplementedError

    def generate_queries(self, belief_set, num_queries: int = 3):
        raise NotImplementedError

    def get_agent_capabilities(self):
        raise NotImplementedError

    def get_response(self, query, context):
        raise NotImplementedError

    def interpret_results(self, results, context: Optional[Dict[str, Any]] = None):
        raise NotImplementedError

    def invoke_single(self, argument, context):
        raise NotImplementedError

    def setup_agent_components(self):
        raise NotImplementedError

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