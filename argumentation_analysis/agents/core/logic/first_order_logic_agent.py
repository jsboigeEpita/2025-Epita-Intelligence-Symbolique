# FORCE_RELOAD
# argumentation_analysis/agents/core/logic/first_order_logic_agent.py
"""
Définit l'agent spécialisé dans le raisonnement en logique du premier ordre (FOL).

Ce module fournit la classe `FirstOrderLogicAgent`, une implémentation pour la FOL,
héritant de `BaseLogicAgent`. Son rôle est d'orchestrer le traitement de texte
en langage naturel pour le convertir en un format logique FOL structuré,
d'exécuter des raisonnements et d'interpréter les résultats.

L'agent utilise une combinaison de prompts sémantiques pour le LLM (définis ici)
et d'appels à `TweetyBridge` pour la validation et l'interrogation de la base de
connaissances.
"""

import logging
import re
import json
import jpype
import asyncio
import unicodedata
from typing import Dict, List, Optional, Any, Tuple, AsyncGenerator, NamedTuple, Set
from abc import abstractmethod
import os

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.contents.chat_history import ChatHistory
# Imports are updated based on recent semantic-kernel changes
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.contents.function_result_content import FunctionResultContent
# The decorator has been moved to the top-level package for easier access.
from semantic_kernel.functions import kernel_function, KernelFunctionFromPrompt, KernelPlugin, KernelArguments
from semantic_kernel.prompt_template.prompt_template_config import PromptTemplateConfig
from semantic_kernel.connectors.ai.open_ai import OpenAIPromptExecutionSettings
from semantic_kernel.connectors.ai.function_calling_utils import kernel_function_metadata_to_function_call_format
from pydantic import Field, field_validator
from semantic_kernel.exceptions.kernel_exceptions import KernelException
 
from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent
from .belief_set import BeliefSet, FirstOrderBeliefSet
from .tweety_bridge import TweetyBridge
from .tweety_initializer import TweetyInitializer

# Configuration du logger
logger = logging.getLogger(__name__)

# ==============================================================================
# STRATÉGIE D'ARCHITECTURE FINALE (BASÉE SUR LES OUTILS)
# ------------------------------------------------------------------------------
# L'approche précédente, consistant à demander au LLM de générer directement la
# syntaxe `.fologic`, s'est avérée peu fiable. Les LLMs ne sont pas doués pour
# respecter des grammaires strictes.
#
# La nouvelle stratégie est beaucoup plus robuste :
# 1. DÉFINIR DES OUTILS : Nous définissons un "Plugin" avec des fonctions claires
#    (`add_sort`, `add_constant`, etc.) qui représentent les opérations de
#    construction d'une base de connaissances.
# 2. RÔLE DU LLM : Le LLM n'écrit plus de code. Son unique rôle est d'analyser
#    le texte et de décider QUELS outils appeler avec QUELS arguments.
# 3. RÔLE DU CODE PYTHON : Le code Python (le plugin) reçoit ces appels,
#    accumule les informations dans une structure de données interne fiable,
#    puis génère la chaîne `.fologic` finale de manière déterministe.
#
# C'est une séparation claire des responsabilités qui tire parti des forces
# de chaque composant.
# ==============================================================================

# Structures de données pour stocker les éléments logiques sémantiquement
class AtomicFact(NamedTuple):
    predicate_name: str
    arguments: List[str]

class NegatedAtomicFact(NamedTuple):
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
    """
    Un plugin sémantique qui fournit des outils pour construire une base de
    connaissances FOL de manière incrémentale. Le LLM appellera ces fonctions
    comme des outils.
    """
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.reset()

    def reset(self):
        """Réinitialise l'état interne du constructeur."""
        # Ne pas réinitialiser le logger
        self._sorts: Dict[str, List[str]] = {}  # {sort_name: [const1, const2]}
        self._predicates: Dict[str, List[str]] = {}  # {pred_name: [sort1, sort2]}
        self._atomic_facts: List[AtomicFact] = []
        self._negated_atomic_facts: List[NegatedAtomicFact] = []
        self._universal_implications: List[UniversalImplication] = []
        self._existential_conjunctions: List[ExistentialConjunction] = []
        # --- Hiérarchie de sortes pour l'inférence ---
        self._sort_hierarchy: Dict[str, Set[str]] = {} # {sous_sorte: {super_sorte_1, ...}}
        # --- Union-Find structure for sort unification ---
        self._sort_parent: Dict[str, str] = {} # Maps a predicate to its representative
        self._predicate_to_sort: Dict[str, str] = {} # Maps a predicate to its final sort name

    def _find_sort_representative(self, predicate_name: str) -> str:
        """Finds the representative for a predicate's sort group (with path compression)."""
        if predicate_name not in self._sort_parent:
            # A predicate MUST be initialized before it can be part of the unification system.
            # This is done in `add_predicate_schema` or implicitly in `add_universal_implication`.
            raise KeyError(f"Predicate '{predicate_name}' is not part of the sort unification system. It must be declared first.")
        
        # Path compression
        if self._sort_parent[predicate_name] == predicate_name:
            return predicate_name
        
        root = self._find_sort_representative(self._sort_parent[predicate_name])
        self._sort_parent[predicate_name] = root
        return root

    def _unify_sorts(self, pred1: str, pred2: str):
        """
        Unifies the sort groups of two predicates and, crucially, updates the schemas
        of all affected predicates to use the new canonical sort.
        """
        try:
            root1 = self._find_sort_representative(pred1)
            root2 = self._find_sort_representative(pred2)

            if root1 == root2:
                return # Already unified

            # The sort of the first predicate's group becomes the canonical one.
            self._sort_parent[root2] = root1
            canonical_root = root1
            absorbed_root = root2
            
            # Get the canonical sort name from the representative predicate.
            canonical_sort_name = self._predicate_to_sort[canonical_root]
            logger.debug(f"Unifying sorts: '{absorbed_root}' -> '{canonical_root}'. New canonical sort: '{canonical_sort_name}'.")

            # --- CRITICAL STEP: Update schemas of all predicates in the absorbed group ---
            # We need to find all predicates that were part of the old group (now absorbed).
            # We can't just iterate `self._sort_parent` as some paths might not be compressed yet.
            # So, we iterate through all known predicates.
            all_known_predicates = list(self._sort_parent.keys())
            for pred_name in all_known_predicates:
                # Find the current representative for each predicate to see if it belongs to the unified group.
                current_root = self._find_sort_representative(pred_name)
                if current_root == canonical_root:
                    # This predicate is now in the unified group. Update its schema.
                    old_schema = self._predicates.get(pred_name)
                    if not old_schema:
                        logger.warning(f"Predicate '{pred_name}' is in the unification tree but has no schema. Skipping update.")
                        continue
                    
                    # Update all its argument sorts to the new canonical sort.
                    old_sorts = self._predicates[pred_name]
                    new_sorts = [canonical_sort_name] * len(old_sorts)
                    self._predicates[pred_name] = new_sorts
                    if old_sorts != new_sorts:
                        logger.debug(f"Updated schema for '{pred_name}': {old_sorts} -> {new_sorts}")

        except KeyError as e:
            logger.error(f"Cannot unify sorts. Predicate not initialized in the unification system. {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'état du builder en un dictionnaire sérialisable."""
        return {
            "_sorts": self._sorts,
            "_predicates": self._predicates,
            "_atomic_facts": [fact._asdict() for fact in self._atomic_facts],
            "_negated_atomic_facts": [fact._asdict() for fact in self._negated_atomic_facts],
            "_universal_implications": [impl._asdict() for impl in self._universal_implications],
            "_existential_conjunctions": [conj._asdict() for conj in self._existential_conjunctions],
        }

    def _normalize(self, name: str) -> str:
        """
        Normalizes a name for a predicate, sort, or constant by making it lowercase,
        removing accents, stripping parenthesized expressions, and replacing spaces/hyphens with underscores.
        e.g., "Un Étudiant-Français(x)" becomes "un_etudiant_francais".
        """
        # Remove any parenthesized expressions like "(x)"
        name = re.sub(r'\(.*\)', '', name).strip()
        
        # Convert to lowercase
        name = name.lower()
        
        # Decompose and remove accents (e.g., 'é' -> 'e')
        normalized_name = unicodedata.normalize('NFD', name)
        name_without_accents = ''.join(c for c in normalized_name if unicodedata.category(c) != 'Mn')
        
        # Replace spaces and hyphens with underscores
        final_name = name_without_accents.replace(" ", "_").replace("-", "_")
        
        return final_name

    def _ensure_predicate_exists(self, predicate_name: str, arity: int = 1):
        """
        Ensures a predicate schema exists. If not, creates a default one.
        This prevents errors when LLMs use predicates before declaring them.
        """
        norm_pred = self._normalize(predicate_name)
        if norm_pred not in self._predicates:
            # Create a default schema with arity 1 and a sort named after the predicate.
            default_sort_name = norm_pred
            logger.debug(f"Predicate '{norm_pred}' not found. Creating default schema with arity {arity} and sort '{default_sort_name}'.")
            
            # The schema will have `arity` arguments, all of the same default sort.
            default_arg_sorts = [default_sort_name] * arity
            self.add_predicate_schema(norm_pred, default_arg_sorts)
        return norm_pred

    @kernel_function(
        description="Déclare un nouveau sort (un type de catégorie, comme 'personne' ou 'ville').",
        name="add_sort",
    )
    def add_sort(self, sort_name: str):
        """Ajoute un sort à la base de connaissances."""
        logger.info(f"AUDIT - [BeliefSetBuilderPlugin({id(self)})] Appel de add_sort avec: '{sort_name}'")
        norm_sort = self._normalize(sort_name)
        if norm_sort not in self._sorts:
            self._sorts[norm_sort] = []
        return f"Sort '{norm_sort}' added."

    @kernel_function(description="Define a predicate schema.", name="add_predicate_schema")
    def add_predicate_schema(self, predicate_name: str, argument_sorts: List[str]):
        logger.info(f"AUDIT - [BeliefSetBuilderPlugin({id(self)})] Appel de add_predicate_schema avec: '{predicate_name}', {argument_sorts}")
        norm_pred = self._normalize(predicate_name)
        norm_args = [self._normalize(s) for s in argument_sorts]
        
        # The first argument's sort is considered the primary sort for this predicate.
        # This is the source of truth for its type.
        new_sort_name = norm_args[0] if norm_args else self._normalize(norm_pred)
        
        # Ensure the sort itself is registered
        if new_sort_name not in self._sorts:
            self.add_sort(new_sort_name)

        # Initialize the predicate in the unification system if it's not there yet.
        if norm_pred not in self._sort_parent:
            self._sort_parent[norm_pred] = norm_pred # It is its own representative initially.
            
        # This explicit declaration sets the cannonsical sort for THIS predicate's group root.
        self._predicate_to_sort[norm_pred] = new_sort_name
        self._predicates[norm_pred] = norm_args
        
        logger.debug(f"Predicate schema '{norm_pred}' registered with explicit sort '{new_sort_name}'.")
        return f"Predicate schema '{norm_pred}' declared with sort '{new_sort_name}'."

    @kernel_function(
        description="Déclare une constante (un individu spécifique, comme 'Socrate') et l'associe à un sort (une catégorie, comme 'homme').",
        name="add_constant_to_sort"
    )
    def add_constant_to_sort(self, constant_name: str, sort_name: str):
        """Ajoute une constante à un sort."""
        logger.info(f"AUDIT - [BeliefSetBuilderPlugin({id(self)})] Appel de add_constant_to_sort avec: '{constant_name}', '{sort_name}'")
        norm_const = self._normalize(constant_name)
        norm_sort = self._normalize(sort_name)
        if norm_sort not in self._sorts:
            self.add_sort(norm_sort)
        if norm_const not in self._sorts[norm_sort]:
            self._sorts[norm_sort].append(norm_const)
        return f"Constant '{norm_const}' added to sort '{norm_sort}'."

    @kernel_function(description="Add an atomic fact, e.g., 'Socrates is a man'.", name="add_atomic_fact")
    def add_atomic_fact(self, fact_predicate_name: str, fact_arguments: List[str]):
        logger.info(f"AUDIT - [BeliefSetBuilderPlugin({id(self)})] Appel de add_atomic_fact avec: '{fact_predicate_name}', {fact_arguments}")
        p_name = self._normalize(fact_predicate_name)
        arg_list = [self._normalize(arg) for arg in fact_arguments]

        if p_name not in self._predicates:
            raise ValueError(f"Validation Error: Attempted to use undeclared predicate '{p_name}'. All predicates must be declared with 'add_predicate_schema' first.")

        expected_arity = len(self._predicates[p_name])
        actual_arity = len(arg_list)
        if actual_arity != expected_arity:
            raise ValueError(f"Validation Error: Arity mismatch for predicate '{p_name}'. Expected {expected_arity} arguments, but received {actual_arity}.")

        expected_sorts = self._predicates[p_name]
        for i, arg_name in enumerate(arg_list):
            expected_sort = self._normalize(expected_sorts[i])
            actual_sort = None
            
            # Trouver la sorte actuelle de la constante
            for s_name, constants in self._sorts.items():
                if arg_name in constants:
                    actual_sort = s_name
                    break

            # Scénario 1: Constante inconnue
            if not actual_sort:
                logger.info(f"Repairing: Constant '{arg_name}' is undeclared. Adding it to expected sort '{expected_sort}'.")
                self.add_constant_to_sort(arg_name, expected_sort)
                continue # Passe à l'argument suivant

            # Scénario 2: Sorte compatible (exacte ou via hiérarchie)
            if self._is_compatible(actual_sort, expected_sort):
                logger.debug(f"Validation OK: Sort '{actual_sort}' for constant '{arg_name}' is compatible with expected sort '{expected_sort}'.")
                continue # Passe à l'argument suivant

            # Scénario 3: Incompatibilité
            raise ValueError(f"Validation Error: Irreparable sort mismatch for argument '{arg_name}' of predicate '{p_name}'. "
                             f"Expected a sort compatible with '{expected_sort}', but found '{actual_sort}'.")

        self._atomic_facts.append(AtomicFact(p_name, arg_list))
        return f"Atomic fact '{p_name}({', '.join(arg_list)})' added after flexible validation."

    @kernel_function(description="Add a negated atomic fact, e.g., 'Socrates is NOT a god'.", name="add_negated_atomic_fact")
    def add_negated_atomic_fact(self, fact_predicate_name: str, fact_arguments: List[str]):
        p_name = self._normalize(fact_predicate_name)
        arg_list = [self._normalize(arg) for arg in fact_arguments]

        if p_name not in self._predicates:
            sort_name_for_predicate = p_name
            self.add_predicate_schema(p_name, [sort_name_for_predicate])

        expected_sorts = self._predicates[p_name]
        for i, arg_name in enumerate(arg_list):
            if i < len(expected_sorts):
                sort_name = expected_sorts[i]
                if sort_name not in self._sorts:
                    self.add_sort(sort_name)
                if arg_name not in self._sorts[sort_name]:
                    self._sorts[sort_name].append(arg_name)

        self._negated_atomic_facts.append(NegatedAtomicFact(p_name, arg_list))
        return f"Negated atomic fact 'not {p_name}({', '.join(arg_list)})' added."

    @kernel_function(description="Add a universal implication.", name="add_universal_implication")
    def add_universal_implication(self, impl_antecedent_predicate: str, impl_consequent_predicate: str, impl_sort_of_variable: str):
        logger.info(f"AUDIT - [BeliefSetBuilderPlugin({id(self)})] Appel de add_universal_implication avec: '{impl_antecedent_predicate}' => '{impl_consequent_predicate}'")
        # Ensure predicates exist with a default arity of 1 before proceeding.
        norm_antecedent = self._ensure_predicate_exists(impl_antecedent_predicate, arity=1)
        norm_consequent = self._ensure_predicate_exists(impl_consequent_predicate, arity=1)

        # Now that they are guaranteed to exist, unify their sorts.
        self._unify_sorts(norm_antecedent, norm_consequent)
        unified_sort = self._predicate_to_sort[self._find_sort_representative(norm_antecedent)]

        self._universal_implications.append(UniversalImplication(
            norm_antecedent,
            norm_consequent,
            unified_sort
        ))
        return "Universal implication added."
        
    @kernel_function(description="Add an existential conjunction, e.g., 'Some A are B'.", name="add_existential_conjunction")
    def add_existential_conjunction(self, predicate1: str, predicate2: str, sort_of_variable: str):
        logger.info(f"AUDIT - [BeliefSetBuilderPlugin({id(self)})] Appel de add_existential_conjunction avec: '{predicate1}' and '{predicate2}'")
        # Ensure predicates exist with a default arity of 1 before proceeding.
        norm_p1 = self._ensure_predicate_exists(predicate1, arity=1)
        norm_p2 = self._ensure_predicate_exists(predicate2, arity=1)

        self._unify_sorts(norm_p1, norm_p2)
        unified_sort = self._predicate_to_sort[self._find_sort_representative(norm_p1)]

        self._existential_conjunctions.append(ExistentialConjunction(norm_p1, norm_p2, unified_sort))
        return "Existential conjunction added."

    def _infer_sort_hierarchy(self):
        """
        Analyse les implications universelles pour inférer une hiérarchie de sortes.
        Par exemple, de `forall X: (homme(X) => mortel(X))`, on déduit que `homme`
        est une sous-sorte de `mortel`.
        """
        self.logger.info("Starting sort hierarchy inference from universal implications...")
        # L'unification via _unify_sorts a déjà aligné les prédicats sur un nom de sorte canonique.
        # Maintenant, nous établissons la relation hiérarchique directionnelle.
        for impl in self._universal_implications:
            try:
                # La sorte de l'antécédent est la sous-sorte.
                # Le nom de la sorte est dérivé du nom du prédicat antécédent.
                sub_sort = self._normalize(self._predicate_to_sort.get(impl.antecedent_predicate, impl.antecedent_predicate))
                
                # Le conséquent définit la super-sorte.
                super_sort = self._normalize(self._predicate_to_sort.get(impl.consequent_predicate, impl.consequent_predicate))

                if sub_sort != super_sort:
                    if sub_sort not in self._sort_hierarchy:
                        self._sort_hierarchy[sub_sort] = set()
                    
                    if super_sort not in self._sort_hierarchy.get(sub_sort, set()):
                        self._sort_hierarchy[sub_sort].add(super_sort)
                        self.logger.debug(f"Inferred hierarchy: '{sub_sort}' is a sub-sort of '{super_sort}'.")

            except Exception as e:
                self.logger.error(f"Error during hierarchy inference for implication {impl}: {e}", exc_info=True)
        self.logger.info(f"Sort hierarchy inference completed. Current hierarchy: {self._sort_hierarchy}")

    def _is_compatible(self, actual_sort: str, expected_sort: str) -> bool:
        """
        Vérifie si la sorte `actual_sort` est compatible avec `expected_sort`,
        c'est-à-dire si elles sont identiques ou si `actual_sort` est une sous-sorte
        directe ou indirecte de `expected_sort`.
        """
        if actual_sort == expected_sort:
            return True

        # Parcours en largeur pour trouver si expected_sort est un ancêtre
        q = [actual_sort]
        visited = {actual_sort}
        
        while q:
            current_sort = q.pop(0)
            
            super_sorts = self._sort_hierarchy.get(current_sort, set())
            for super_sort in super_sorts:
                if super_sort == expected_sort:
                    return True
                if super_sort not in visited:
                    visited.add(super_sort)
                    q.append(super_sort)
        
        return False

    def _create_safe_fol_atom(self, FolAtom, predicate, arguments):
        """
        Safely creates a FolAtom after checking for sort compatibility.
        Returns the atom on success, or None on failure.
        """
        try:
            # Direct check for arity
            if predicate.getArity() != arguments.size():
                logger.error(f"Arity mismatch for predicate '{str(predicate.getName())}'. "
                             f"Expected {predicate.getArity()}, but got {arguments.size()}.")
                return None

            # Check sort compatibility for each argument
            expected_sorts = predicate.getArgumentTypes()
            for i in range(arguments.size()):
                arg = arguments.get(i)
                arg_sort = arg.getSort()
                expected_sort = expected_sorts.get(i)
                if not arg_sort.equals(expected_sort):
                    logger.error(f"Sort mismatch for predicate '{str(predicate.getName())}' at position {i}. "
                                 f"Expected sort '{str(expected_sort.getName())}' but argument '{str(arg.toString())}' has sort '{str(arg_sort.getName())}'.")
                    return None
            
            # If all checks pass, create and return the atom
            return FolAtom(predicate, arguments)

        except Exception as e:
            # Catch potential Java exceptions during creation
            logger.error(f"Failed to create FolAtom for predicate '{str(predicate.getName())}' due to Java exception: {e}", exc_info=True)
            return None
        
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
            initializer = tweety_bridge.initializer
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
            Negation = initializer.Negation
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
                    jconst = Constant(const_name, jsort)
                    signature.add(jconst)
                    java_constants[const_name] = jconst

            # 2. Add predicates to signature
            java_predicates = {}
            for pred_name, arg_sorts in self._predicates.items():
                j_arg_sorts = ArrayList()
                valid_sorts = True
                for s_name in arg_sorts:
                    if s_name in java_sorts:
                        j_arg_sorts.add(java_sorts[s_name])
                    else:
                        logger.warning(f"Sort '{s_name}' for predicate '{pred_name}' not found. Skipping.")
                jpred = Predicate(pred_name, j_arg_sorts)
                signature.add(jpred)
                java_predicates[pred_name] = jpred

            belief_set = FolBeliefSet()
            belief_set.setSignature(signature) # CRITICAL FIX: Attach the signature to the belief set

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
                            logger.warning(f"Constant '{arg_name}' not found for fact '{fact.predicate_name}'. Skipping argument.")
                    
                    atom = self._create_safe_fol_atom(FolAtom, j_pred, j_args)
                    if atom:
                        belief_set.add(atom)

            # Add negated atomic facts
            for fact in self._negated_atomic_facts:
                if fact.predicate_name in java_predicates:
                    j_pred = java_predicates[fact.predicate_name]
                    j_args = ArrayList()
                    for arg_name in fact.arguments:
                        if arg_name in java_constants:
                            j_args.add(java_constants[arg_name])
                        else:
                            logger.warning(f"Constant '{arg_name}' not found for negated fact '{fact.predicate_name}'. Skipping argument.")
                    
                    atom = self._create_safe_fol_atom(FolAtom, j_pred, j_args)
                    if atom:
                        negated_formula = Negation(atom)
                        belief_set.add(negated_formula)

            # Add universal implications
            for impl in self._universal_implications:
                base_char = impl.sort_of_variable[0]
                normalized_char = unicodedata.normalize('NFKD', base_char).encode('ascii', 'ignore').decode('ascii')
                var_name = normalized_char.upper() if normalized_char else 'X'

                j_sort = java_sorts.get(impl.sort_of_variable)
                if not j_sort:
                    logger.error(f"Sort '{impl.sort_of_variable}' not found for universal implication.")
                    continue
                
                j_var = Variable(var_name, j_sort)
                
                ante_pred = java_predicates.get(impl.antecedent_predicate)
                ante_args = ArrayList()
                ante_args.add(j_var)
                antecedent = self._create_safe_fol_atom(FolAtom, ante_pred, ante_args)
                
                cons_pred = java_predicates.get(impl.consequent_predicate)
                cons_args = ArrayList()
                cons_args.add(j_var)
                consequent = self._create_safe_fol_atom(FolAtom, cons_pred, cons_args)

                if antecedent and consequent:
                    implication = Implication(antecedent, consequent)
                    quantified_formula = ForallQuantifiedFormula(implication, j_var)
                    belief_set.add(quantified_formula)
                else:
                    logger.error(f"Skipping universal implication due to atom creation failure: forall {var_name}:{impl.sort_of_variable}.({impl.antecedent_predicate}({var_name}) => {impl.consequent_predicate}({var_name}))")

            # Add existential conjunctions
            for ex in self._existential_conjunctions:
                var_name = ex.sort_of_variable[0].upper()
                j_sort = java_sorts.get(ex.sort_of_variable)
                if not j_sort:
                    logger.error(f"Sort '{ex.sort_of_variable}' not found for existential conjunction.")
                    continue

                j_var = Variable(var_name, j_sort)

                p1 = java_predicates.get(ex.predicate1)
                p1_args = ArrayList()
                p1_args.add(j_var)
                atom1 = self._create_safe_fol_atom(FolAtom, p1, p1_args)
                
                p2 = java_predicates.get(ex.predicate2)
                p2_args = ArrayList()
                p2_args.add(j_var)
                atom2 = self._create_safe_fol_atom(FolAtom, p2, p2_args)

                if atom1 and atom2:
                    conjunction = Conjunction(atom1, atom2)
                    quantified_formula = ExistsQuantifiedFormula(conjunction, j_var)
                    belief_set.add(quantified_formula)
                else:
                    logger.error(f"Skipping existential conjunction due to atom creation failure: exists {var_name}:{ex.sort_of_variable}.({ex.predicate1}({var_name}) and {ex.predicate2}({var_name}))")

            # --- DEBUT DEBUG LOGS ---
            sig_string = f"Signature state:\n"
            # Explicitly cast Java strings to Python strings
            sig_string += f"  Sorts: {[str(s.getName()) for s in signature.getSorts()]}\n"

            const_list = []
            for c in signature.getConstants():
                # Explicitly cast Java strings to Python strings
                const_list.append(f"{str(c.toString())}:{str(c.getSort().getName())}")
            sig_string += f"  Constants: {const_list}\n"

            pred_list = []
            for p in signature.getPredicates():
                # Explicitly cast Java strings to Python strings
                arg_sort_names = [str(s.getName()) for s in p.getArgumentTypes()]
                pred_list.append(f"{str(p.getName())}({', '.join(arg_sort_names)})")
            sig_string += f"  Predicates: {pred_list}\n"

            logger.info(sig_string)
            # Explicitly cast the belief set's string representation
            logger.info(f"Programmatically built belief set: {str(belief_set.toString())}")
            # --- FIN DEBUG LOGS ---
            
            return belief_set

        except (jpype.JException, AttributeError, TypeError) as e:
            logger.error(f"Failed to build Tweety belief set due to an exception: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during belief set construction: {e}", exc_info=True)
            return None


def _load_prompt_from_file(prompt_filename: str) -> str:
    """Charge un prompt depuis un fichier dans le répertoire 'prompts'."""
    script_dir = os.path.dirname(__file__)
    # Remonter de deux niveaux (logic -> core -> agents) pour trouver le répertoire 'prompts'
    agents_dir = os.path.dirname(os.path.dirname(script_dir))
    prompt_path = os.path.join(agents_dir, 'prompts', prompt_filename)
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Fichier de prompt introuvable : {prompt_path}")
        raise

SYSTEM_PROMPT_FOL = _load_prompt_from_file("fol_system.prompt")
PROMPT_GEN_FOL_QUERIES = """Expert FOL : À partir du texte et de l'ensemble de croyances (belief set), générez des requêtes FOL pertinentes et syntaxiquement valides au format JSON.

Règles impératives :
1.  **Format de sortie :** Produire un JSON unique contenant une clé "queries" avec une liste de chaînes de caractères.
    ```json
    {
      "queries": [
        "NomPredicat(constante1)",
        "exists X:sort (AutrePredicat(X))",
        "forall Y:autre_sort (Implique(Y, Z))"
      ]
    }
    ```
2.  **Validation :** Chaque requête DOIT être syntaxiquement correcte et utiliser UNIQUEMENT les sorts, constantes et prédicats définis dans le `belief_set`.
3.  **Pertinence :** Les requêtes doivent être en lien direct avec le texte fourni et chercher à vérifier ou inférer des informations.
4.  **Simplicité :** Préférez des requêtes simples et atomiques (une seule proposition).

**Contexte :**

*   **Texte :** {{$input}}
*   **Belief Set (signature et formules existantes) :** {{$belief_set}}

Générez le JSON contenant les requêtes.
"""


PROMPT_INTERPRET_FOL = """Expert FOL : Interprétez les résultats de requêtes FOL en langage accessible.

**Contexte :**
*   **Texte original :** {{$input}}
*   **Ensemble de croyances (Belief Set) :** {{$belief_set}}
*   **Requêtes exécutées :** {{$queries}}
*   **Résultats bruts de Tweety :** {{$tweety_result}}

**Votre Tâche :**
Pour chaque requête, fournissez :
1.  **L'objectif de la requête :** Que cherchait-on à savoir ? (par exemple, "Vérifier si Socrate est mortel").
2.  **Le résultat :** `ACCEPTED` (prouvé) ou `REJECTED` (non prouvé).
3.  **L'interprétation :** Expliquez ce que le résultat signifie en langage simple, en vous basant sur le contexte.
4.  **Les implications :** Quelles conclusions peut-on tirer de ce résultat ?

Terminez par une **conclusion générale concise** qui résume les apprentissages clés de l'analyse.
"""

class FirstOrderLogicAgent(BaseLogicAgent):
    """
    Agent spécialiste de l'analyse en logique du premier ordre (FOL).
    """
    
    service: Optional[ChatCompletionClientBase] = Field(default=None, exclude=True)
    settings: Optional[Any] = Field(default=None, exclude=True)

    def __init__(self, kernel: Kernel, tweety_bridge: "TweetyBridge", agent_name: str = "FirstOrderLogicAgent", service_id: Optional[str] = None):
        system_prompt = _load_prompt_from_file("fol_system.prompt")
        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            logic_type_name="FOL",
            system_prompt=system_prompt
        )
        self._llm_service_id = service_id
        if kernel and service_id:
            try:
                self.service = kernel.get_service(service_id, type=ChatCompletionClientBase)
            except Exception as e:
                self.logger.warning(f"Could not retrieve service '{service_id}': {e}")
        
        self._tweety_bridge = tweety_bridge
        # Le plugin qui contient nos outils. Il sera instancié ici.
        self._builder_plugin = BeliefSetBuilderPlugin(logger=self.logger)
        self.logger.info(f"AUDIT - Agent {self.name} a initialisé son plugin builder avec l'ID: {id(self._builder_plugin)}")
        self.logger.info(f"Agent {self.name} initialisé. Stratégie: Appel d'Outils (construction programmatique).")

    def get_agent_capabilities(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "logic_type": self.logic_type,
            "description": "Agent capable d'analyser du texte en utilisant la logique du premier ordre (FOL).",
            "methods": {
                "text_to_belief_set": "Convertit un texte en un ensemble de croyances FOL.",
                "generate_queries": "Génère des requêtes FOL pertinentes.",
                "execute_query": "Exécute une requête FOL sur un ensemble de croyances.",
                "interpret_results": "Interprète les résultats de requêtes FOL.",
                "validate_formula": "Valide la syntaxe d'une formule FOL."
            }
        }

    async def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Configure les composants de l'agent, notamment le pont logique et les fonctions sémantiques.
        """
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants pour {self.name}...")

        # Attendre que le pont Tweety soit prêt si l'initialisation est asynchrone
        if hasattr(self._tweety_bridge, 'wait_for_jvm') and asyncio.iscoroutinefunction(self._tweety_bridge.wait_for_jvm):
            await self._tweety_bridge.wait_for_jvm()

        if not TweetyInitializer.is_jvm_ready():
            self.logger.error("Tentative de setup FOL Kernel alors que la JVM n'est PAS démarrée.")
            raise RuntimeError("TweetyBridge not initialized, JVM not ready.")

        # Ajout du plugin de construction comme une collection d'outils
        self._kernel.add_plugin(self._builder_plugin, plugin_name="BeliefBuilder")

        # Manually create KernelFunctions from prompts
        gen_queries_func = KernelFunctionFromPrompt(
            function_name="GenerateFOLQueries",
            plugin_name="fol_reasoning",
            prompt=PROMPT_GEN_FOL_QUERIES
        )
        interpret_func = KernelFunctionFromPrompt(
            function_name="InterpretFOLResult",
            plugin_name="fol_reasoning",
            prompt=PROMPT_INTERPRET_FOL
        )

        # Create a plugin from these functions
        prompt_plugin = KernelPlugin(
            name="fol_reasoning",
            functions=[gen_queries_func, interpret_func]
        )
        
        # Add the plugin to the kernel
        self._kernel.add_plugin(prompt_plugin)

        self.logger.info(f"Plugin 'BeliefBuilder' and prompt-based plugin 'fol_reasoning' added to the kernel.")
            
    def _normalize_identifier(self, text: str) -> str:
        """Normalise un identifiant en snake_case sans accents."""
        import unidecode
        text = unidecode.unidecode(text)
        text = re.sub(r'\s+', '_', text)
        text = re.sub(r'[^a-zA-Z0-9_]', '', text)
        return text.lower()

    async def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[FirstOrderBeliefSet], str]:
        """
        Convertit un texte en `FirstOrderBeliefSet` en utilisant la stratégie d'appel d'outils.
        """
        self.logger.info(f"Début de la conversion de texte vers FOL (stratégie Outils) pour {self.name}...")
        
        # Réinitialiser l'état du plugin builder pour cette nouvelle conversion
        self._builder_plugin.reset()

        # Configurer l'historique de chat pour l'invocation avec outils
        chat = ChatHistory(system_message=self.system_prompt)
        chat.add_user_message(text)
        
        # This is the modern way to handle tool calling.
        # We retrieve the plugin and manually format each function's metadata
        # into the format expected by the OpenAI API.
        builder_plugin = self._kernel.plugins.get("BeliefBuilder")
        if not builder_plugin:
            self.logger.error("Plugin 'BeliefBuilder' could not be found in the kernel.")
            raise ValueError("Plugin 'BeliefBuilder' not found during tool preparation.")

        tools_list = [kernel_function_metadata_to_function_call_format(f.metadata) for f in builder_plugin]

        execution_settings = OpenAIPromptExecutionSettings(
            service_id=self._llm_service_id,
            tool_choice="auto",
            tools=tools_list,
            # Disable auto-invoke to handle the loop manually for stateful plugins
            auto_invoke_kernel_functions=False,
        )

        try:
            successful_tool_calls = 0
            max_loops = 5
            result = None

            for i in range(max_loops):
                self.logger.info(f"Début de la boucle d'appel d'outils, itération {i+1}/{max_loops}")
                
                result = await self.service.get_chat_message_content(
                    chat,
                    settings=execution_settings
                )
                chat.add_message(result)
                
                tool_calls_from_message = [item for item in result.items if isinstance(item, FunctionCallContent)]
                
                if not tool_calls_from_message:
                    self.logger.info("Fin de la boucle: le LLM n'a plus d'appels d'outils à effectuer.")
                    break

                self.logger.info(f"{len(tool_calls_from_message)} appel(s) d'outil(s) reçu(s) du LLM.")

                for tool_call in tool_calls_from_message:
                    self.logger.info(f"Invocation manuelle de l'outil: '{tool_call.function_name}' avec les arguments: {tool_call.arguments}")
                    
                    function_to_call = self._kernel.plugins[tool_call.plugin_name][tool_call.function_name]
                    tool_result = await self._kernel.invoke(
                        function_to_call, **tool_call.to_kernel_arguments()
                    )
                    
                    func_result_content = FunctionResultContent.from_function_call_content_and_result(
                        function_call_content=tool_call,
                        result=tool_result
                    )
                    
                    successful_tool_calls += 1
                    chat.add_message(func_result_content.to_chat_message_content())
            else:
                 self.logger.warning("La boucle d'appel d'outils a atteint le nombre maximum d'itérations.")

            self.logger.info("Le LLM a terminé d'appeler les outils via la boucle manuelle.")

            if result and result.finish_reason == "stop" and successful_tool_calls == 0:
                self.logger.warning(f"LLM stopped with ZERO successful tool calls. Returning an empty BeliefSet.")
                return FirstOrderBeliefSet(content="", java_object=None), "Aucune structure logique pertinente n'a été trouvée."

            # --- NOUVELLE ÉTAPE : INFERENCE DE LA HIERARCHIE ---
            self.logger.info("Le LLM a terminé d'appeler les outils. Inférence de la hiérarchie des sortes...")
            self._builder_plugin._infer_sort_hierarchy()
            # ----------------------------------------------------

            self.logger.info("Construction de l'ensemble de croyances Tweety...")
            java_belief_set = self._builder_plugin.build_tweety_belief_set(self._tweety_bridge)

            if java_belief_set is None:
                return None, "La construction programmatique du belief set a échoué."

            final_belief_set = FirstOrderBeliefSet(content=str(java_belief_set.toString()), java_object=java_belief_set)

            if final_belief_set.is_empty():
                 return final_belief_set, "Aucune structure logique pertinente n'a été trouvée."

            return final_belief_set, "Conversion réussie."

        except KernelException as e:
            # Check if the underlying cause is a validation error from our plugin
            if e.__cause__ and isinstance(e.__cause__, ValueError):
                msg = f"Erreur de validation: {e.__cause__}"
                self.logger.warning(f"Validation error during tool call: '{msg}'. Returning empty belief set.")
                return FirstOrderBeliefSet(content="", java_object=None), msg
            
            # Handle other kernel-related errors if necessary
            self.logger.error(f"Erreur du noyau sémantique inattendue : {e}", exc_info=True)
            raise e
        except Exception as e:
            self.logger.error(f"Exception inattendue dans `text_to_belief_set`: {e}", exc_info=True)
            raise e
    
    def _extract_json_block(self, text: str) -> str:
        """
        Extracts a JSON block from a string, handling both markdown-formatted
        blocks and raw JSON possibly surrounded by other text.
        """
        # Priorité 1: Chercher un bloc ```json ... ```
        match = re.search(r"```(json)?\s*({.*})\s*```", text, re.DOTALL)
        if match:
            return match.group(2).strip()
        
        # Priorité 2: Chercher le JSON entre la première et la dernière accolade
        # ce qui est plus robuste aux textes explicatifs du LLM.
        match = re.search(r"({.*})", text, re.DOTALL)
        if match:
            return match.group(1).strip()
            
        return text # Fallback: retourne le texte original s'il n'y a pas d'accolades.
        
        
    async def generate_queries(self, text: str, belief_set: FirstOrderBeliefSet, **kwargs) -> List[str]:
        """
        Génère une liste de requêtes FOL pertinentes en utilisant le LLM.
        """
        self.logger.info(f"Génération de requêtes FOL pour {self.name}...")
        try:
            if not belief_set or not belief_set.content:
                return []
                
            args = {"input": text, "belief_set": belief_set.content}
            result = await self._kernel.invoke(
                self._kernel.plugins["fol_reasoning"]["GenerateFOLQueries"], **args
            )
            queries = json.loads(self._extract_json_block(str(result))).get("queries", [])
            self.logger.info(f"{len(queries)} requêtes potentielles reçues du LLM.")
            
            # Valider chaque requête générée
            valid_queries = []
            for q_str in queries:
                if await self.validate_formula(q_str, belief_set):
                    valid_queries.append(q_str)
                    self.logger.info(f"Requête validée: {q_str}")
                else:
                    self.logger.warning(f"Requête invalide rejetée: {q_str}")
            return valid_queries
        except Exception as e:
            self.logger.error(f"Erreur durant la génération de requêtes: {e}", exc_info=True)
            return []

    async def execute_query(self, belief_set: FirstOrderBeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête FOL sur un `FirstOrderBeliefSet` donné.
        """
        self.logger.info(f"Exécution de la requête: {query} pour l'agent {self.name}")
        
        java_belief_set = await self._recreate_java_belief_set(belief_set)
        if not java_belief_set:
            return None, "Impossible de recréer ou de trouver l'objet belief set Java."
            
        try:
            entails = self.tweety_bridge._fol_handler.fol_query(java_belief_set, query)
            result_str = "ACCEPTED" if entails else "REJECTED"
            return entails, result_str
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête: {e}"
            self.logger.error(error_msg, exc_info=True)
            return None, f"FUNC_ERROR: {error_msg}"

    async def interpret_results(self, text: str, belief_set: BeliefSet,
                         queries: List[str], results: List[Tuple[Optional[bool], str]],
                         context: Optional[Dict[str, Any]] = None) -> str:
        """
        Traduit les résultats bruts d'une ou plusieurs requêtes en une explication en langage naturel.
        """
        self.logger.info(f"Interprétation des résultats pour l'agent {self.name}...")
        try:
            queries_str = "\n".join(queries)
            results_text_list = [res[1] if res else "Error: No result" for res in results]
            results_str = "\n".join(results_text_list)
            
            result = await self._kernel.invoke(
                self._kernel.plugins["fol_reasoning"]["InterpretFOLResult"],
                input=text,
                belief_set=belief_set.content,
                queries=queries_str,
                tweety_result=results_str
            )
            return str(result)
        except Exception as e:
            error_msg = f"Erreur durant l'interprétation des résultats: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

    async def validate_formula(self, formula: str, belief_set: Optional[FirstOrderBeliefSet] = None) -> bool:
        """
        Validates the syntax of a FOL formula, optionally against a belief set's signature.
        """
        self.logger.debug(f"Validation de la formule FOL: {formula}")
        if belief_set:
            java_belief_set = await self._recreate_java_belief_set(belief_set)
            if java_belief_set:
                signature = java_belief_set.getSignature()
                is_valid, _ = self.tweety_bridge._fol_handler.validate_formula_with_signature(signature, formula)
                return is_valid

        # Fallback to context-less validation
        is_valid, _ = self.tweety_bridge.validate_fol_formula(formula)
        return is_valid

    async def is_consistent(self, belief_set: FirstOrderBeliefSet) -> Tuple[bool, str]:
        """
        Checks if a FOL belief set is consistent.
        """
        self.logger.info(f"Vérification de la consistance pour {self.name}")
        
        java_belief_set = await self._recreate_java_belief_set(belief_set)
        if not java_belief_set:
            return False, "Impossible de recréer ou de trouver l'objet belief set Java pour la vérification de consistance."
            
        try:
            is_cons, _ = await self.tweety_bridge._fol_handler.fol_check_consistency(java_belief_set)
            if not is_cons:
                return False, "Le belief set est incohérent (inconsistent)."
            
            return True, "Le belief set est cohérent (consistent)."
        except Exception as e:
            self.logger.error(f"Erreur inattendue durant la vérification de consistance: {e}", exc_info=True)
            return False, str(e)

    async def _recreate_java_belief_set(self, belief_set: FirstOrderBeliefSet) -> Optional[Any]:
        """
        Ensures a Java BeliefSet object is available. If an object is already present,
        it's returned. Otherwise, this logic should be handled by the method that
        initially creates the belief set, like `text_to_belief_set`.
        """
        if belief_set.java_object:
            self.logger.debug("Utilisation de l'objet Java BeliefSet préexistant.")
            return belief_set.java_object
        
        # Fallback for situations where a belief set might need to be created from string content
        if belief_set.content:
            self.logger.warning("Tentative de reconstruction JIT (Just-In-Time) du BeliefSet à partir du contenu. "
                               "Cette approche est obsolète et peut manquer de fiabilité.")
            try:
                java_object = self.tweety_bridge.create_belief_set_from_string(belief_set.content)
                if java_object:
                    return java_object
            except Exception as e:
                self.logger.error(f"Échec de la reconstruction JIT du BeliefSet: {e}", exc_info=True)
                return None

        self.logger.error("Aucun objet Java BeliefSet disponible et aucune chaîne de contenu valide pour le reconstruire.")
        return None

    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> Optional[FirstOrderBeliefSet]:
        """Recreates a BeliefSet object from a dictionary."""
        content = belief_set_data.get("content", "")
        if not content:
            return None
        
        # This method is synchronous, so we can't call async methods here.
        # It's better to rely on JIT reconstruction.
        return FirstOrderBeliefSet(content=content, java_object=None)

    async def validate_argument(self, premises: List[str], conclusion: str, **kwargs) -> bool:
        """
        Valide un argument structuré (prémisses, conclusion) en FOL.
        """
        self.logger.info(f"Validation de l'argument FOL pour {self.name}...")
        context_text = " ".join(premises)
        belief_set, status = await self.text_to_belief_set(context_text)

        if not belief_set:
            self.logger.error(f"Impossible de créer un belief set à partir des prémisses. Statut: {status}")
            return False

        if not await self.validate_formula(conclusion, belief_set):
            self.logger.warning(f"La conclusion '{conclusion}' a une syntaxe invalide ou n'est pas alignée avec la signature du belief set.")
            return False

        entails, query_status = await self.execute_query(belief_set, conclusion)

        if entails is None:
            self.logger.error(f"Erreur lors de l'exécution de la requête pour la conclusion '{conclusion}': {query_status}")
            return False

        return entails

    # Méthodes génériques de l'agent (interfaces requises)
    async def get_response(self, chat_history: ChatHistory, **kwargs) -> AsyncGenerator[List[ChatMessageContent], None]:
        logger.warning(f"La méthode 'get_response' n'est pas l'interaction standard pour {self.name}.")
        yield []
    
    async def invoke_single(self, chat_history: ChatHistory, **kwargs) -> ChatMessageContent:
        """Point d'entrée principal pour les interactions génériques."""
        last_user_message = next((m.content for m in reversed(chat_history) if m.role == "user"), None)
        if not last_user_message or not isinstance(last_user_message, str):
             return ChatMessageContent(role="assistant", content="Veuillez fournir une instruction en texte.", name=self.name)
        
        # Ce point d'entrée est un passe-plat vers la logique principale
        belief_set, status = await self.text_to_belief_set(last_user_message)
        if not belief_set:
            response_content = {"error": status}
        else:
            response_content = belief_set.to_dict()

        return ChatMessageContent(role="assistant", content=json.dumps(response_content), name=self.name)