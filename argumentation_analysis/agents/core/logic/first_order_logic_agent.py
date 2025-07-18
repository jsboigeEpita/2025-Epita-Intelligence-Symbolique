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
# The decorator has been moved to the top-level package for easier access.
from semantic_kernel.functions import kernel_function, KernelFunctionFromPrompt, KernelPlugin, KernelArguments
from semantic_kernel.prompt_template.prompt_template_config import PromptTemplateConfig
from semantic_kernel.connectors.ai.open_ai import OpenAIPromptExecutionSettings
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
        
        # Correction spécifique pour le cas multilingue
        if predicate_name.lower() in ['mortale', 'mortales']:
            norm_pred = 'mortel'
        else:
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
        """Ajoute une constante à un sort. Si la constante a déjà une sorte de base,
        interprète cette nouvelle assignation comme un fait atomique."""
        logger.info(f"AUDIT - [BeliefSetBuilderPlugin({id(self)})] Appel de add_constant_to_sort avec: '{constant_name}', '{sort_name}'")
        norm_const = self._normalize(constant_name)
        norm_sort = self._normalize(sort_name)

        # 1. S'assurer que la sorte de destination existe.
        if norm_sort not in self._sorts:
            self.add_sort(norm_sort)

        # 2. Vérifier si la constante a déjà une sorte de base.
        existing_sort = self._find_sort_of_constant(norm_const)
        
        if not existing_sort:
            # Cas simple : la constante est nouvelle. On l'assigne à sa sorte de base.
            self._sorts[norm_sort].append(norm_const)
            return f"Constant '{norm_const}' assigned to base sort '{norm_sort}'."
        
        # Cas où la constante a déjà une sorte
        if existing_sort == norm_sort:
            return f"Constant '{norm_const}' is already in sort '{norm_sort}'. No action needed."

        # --- LOGIQUE CLÉ ---
        # Cas complexe : La constante a déjà une sorte de base différente.
        # Interpréter cela comme l'intention de déclarer un fait : `nouvelle_sorte(constante)`.
        self.logger.info(f"La constante '{norm_const}' a déjà une sorte de base ('{existing_sort}'). "
                         f"L'assignation à '{norm_sort}' est interprétée comme un fait atomique.")
        
        # Le nom du prédicat est dérivé de la nouvelle sorte.
        predicate_name_candidate = norm_sort
        
        # S'assurer que le prédicat correspondant existe.
        # Sa sorte d'argument doit être elle-même.
        self._ensure_predicate_exists(predicate_name_candidate, arity=1)
        
        # Ajouter le fait atomique. La validation dans `add_atomic_fact` va maintenant
        # utiliser la hiérarchie de sortes pour vérifier la compatibilité.
        try:
            self.add_atomic_fact(fact_predicate_name=predicate_name_candidate, fact_arguments=[norm_const])
            return f"Fact '{predicate_name_candidate}({norm_const})' added instead of changing sort."
        except ValueError as e:
            # Si `add_atomic_fact` lève une erreur, c'est une vraie incohérence.
            self.logger.error(f"Failed to create implicit atomic fact for '{norm_const}': {e}")
            return f"Error: Could not assert fact '{predicate_name_candidate}({norm_const})' due to validation error: {e}"

    @kernel_function(
        description="Adds a simple positive statement (atomic fact), like 'Socrates is a philosopher'. Use `predicate_name` for the property (e.g., 'Philosopher') and `arguments` for the individual(s) (e.g., ['socrate']).",
        name="add_atomic_fact"
    )
    def add_atomic_fact(self, fact_predicate_name: str, fact_arguments: List[str]):
        """Ajoute un fait atomique après une validation stricte."""
        logger.info(f"AUDIT - [BeliefSetBuilderPlugin({id(self)})] Appel de add_atomic_fact avec: '{fact_predicate_name}', {fact_arguments}")
        norm_pred_name = self._normalize(fact_predicate_name)
        norm_args = [self._normalize(arg) for arg in fact_arguments]

        # Assure que le prédicat existe pour éviter les KeyErrors.
        self._ensure_predicate_exists(norm_pred_name, arity=len(norm_args))

        # Validation de l'arité
        expected_arity = len(self._predicates[norm_pred_name])
        actual_arity = len(norm_args)
        if actual_arity != expected_arity:
            raise ValueError(f"Erreur d'arité pour '{norm_pred_name}'. Attendu: {expected_arity}, Reçu: {actual_arity}.")

        # Validation des sortes
        expected_sorts = self._predicates[norm_pred_name]
        
        if len(norm_args) != len(expected_sorts):
            logger.error(f"Arity mismatch for '{norm_pred_name}'. Expected {len(expected_sorts)}, got {len(norm_args)}.")
            return f"Error: Arity mismatch for predicate '{norm_pred_name}'."

        # The new combined logic
        for i, arg_name in enumerate(norm_args):
            expected_sort = self._normalize(expected_sorts[i])
            actual_sort = self._find_sort_of_constant(arg_name)

            if not actual_sort:
                # La constante n'a pas de sorte. On l'assigne à la sorte attendue.
                logger.info(f"Réparation : La constante '{arg_name}' était non déclarée. Assignation à la sorte attendue '{expected_sort}'.")
                self.add_constant_to_sort(arg_name, expected_sort)
                actual_sort = expected_sort # Mettre à jour pour la suite

            # Utiliser la hiérarchie pour la validation, avec auto-correction
            if not self._is_compatible(actual_sort, expected_sort):
                logger.warning(
                    f"Incompatibilité de sorte détectée pour '{arg_name}' dans '{norm_pred_name}'. "
                    f"Attendu '{expected_sort}', trouvé '{actual_sort}'. "
                    f"Inférence d'une nouvelle règle de hiérarchie : '{actual_sort}' est une sous-sorte de '{expected_sort}'."
                )
                # On force la compatibilité en ajoutant une règle hiérarchique
                self._sort_hierarchy.setdefault(actual_sort, set()).add(expected_sort)

        # Si toutes les validations passent, ajouter le fait.
        new_fact = AtomicFact(norm_pred_name, norm_args)
        if new_fact not in self._atomic_facts:
            self._atomic_facts.append(new_fact)
        return f"Fait atomique '{norm_pred_name}({', '.join(norm_args)})' ajouté avec succès après validation et inférence de hiérarchie."

    @kernel_function(
        description="Adds a negative statement (negated atomic fact), like 'Socrates is NOT a god'. Use `predicate_name` for the property and `arguments` for the individual.",
        name="add_negated_atomic_fact"
    )
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

    @kernel_function(
        description="Adds a universal rule (implication), like 'All A are B'. Use `antecedent_predicate` for A, `consequent_predicate` for B, and `sort_of_variable` for the category they belong to.",
        name="add_universal_implication"
    )
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
        This method is now a placeholder. The sort unification logic has been moved
        directly into `add_universal_implication` to build the hierarchy incrementally.
        """
        logger.debug("Call to _infer_sort_hierarchy() noted. Unification is now incremental.")
        pass

    def _find_sort_of_constant(self, constant_name: str) -> Optional[str]:
        """Finds the most specific sort a constant belongs to."""
        for sort, constants in self._sorts.items():
            if constant_name in constants:
                return sort
        return None

    def _is_compatible(self, sub_sort_candidate: str, super_sort_target: str) -> bool:
        """
        Checks if sub_sort_candidate is a sub-sort of super_sort_target,
        using the explicitly inferred sort hierarchy. This performs a traversal
        of the sort graph.
        """
        norm_sub = self._normalize(sub_sort_candidate)
        norm_super = self._normalize(super_sort_target)

        if norm_sub == norm_super:
            return True

        # Parcours en profondeur (DFS) pour trouver un chemin dans la hiérarchie.
        # `visited` prévient les cycles infinis dans le graphe des sortes.
        visited = set()
        # `stack` contient les sortes à explorer. On commence avec la sous-sorte candidate.
        stack = [norm_sub]

        while stack:
            current_sort = stack.pop()
            if current_sort in visited:
                continue
            visited.add(current_sort)

            # Vérifier si la sorte courante a des super-sortes directes.
            if current_sort in self._sort_hierarchy:
                direct_super_sorts = self._sort_hierarchy[current_sort]
                # Si la cible est une super-sorte directe, c'est compatible.
                if norm_super in direct_super_sorts:
                    return True
                # Sinon, ajouter les super-sortes à la pile pour les explorer plus tard.
                stack.extend(list(direct_super_sorts))
        
        # Si après avoir parcouru tout le graphe accessible depuis norm_sub,
        # on n'a pas trouvé norm_super, alors ce n'est pas compatible.
        return False

        
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
                if not j_arg_sorts.isEmpty():
                    jpred = Predicate(pred_name, j_arg_sorts)
                    signature.add(jpred)
                    java_predicates[pred_name] = jpred
                else:
                    logger.warning(f"Predicate '{pred_name}' could not be created due to missing argument sorts.")

            belief_set = FolBeliefSet()
            belief_set.setSignature(signature) # CRITICAL FIX: Attach the signature to the belief set

            # 3. Add formulas

            # 3a. Update signature with inferred sort hierarchy (Pass 1)
            self.logger.debug(f"Mise à jour de la signature avec la hiérarchie de sortes inférée : {self._sort_hierarchy}")
            for sub_sort_str, super_sorts in self._sort_hierarchy.items():
                sub_sort_java = java_sorts.get(sub_sort_str)
                if not sub_sort_java:
                    continue
                for super_sort_str in super_sorts:
                    super_sort_java = java_sorts.get(super_sort_str)
                    if super_sort_java:
                        self.logger.info(f"Déclaration de la hiérarchie à la signature Tweety : '{sub_sort_str}' < '{super_sort_str}'")
                        signature.add(sub_sort_java, super_sort_java)
                    else:
                        logger.warning(f"Impossible de déclarer la hiérarchie car la super-sorte '{super_sort_str}' n'a pas été trouvée.")

            # 3b. Add atomic facts with pre-creation validation
            for fact in self._atomic_facts:
                if fact.predicate_name in java_predicates:
                    j_pred = java_predicates[fact.predicate_name]
                    
                    # --- Python-side validation before Java call ---
                    expected_sorts_java = j_pred.getArgumentTypes()
                    is_compatible_fact = True
                    
                    j_args_list = []
                    for i, arg_name in enumerate(fact.arguments):
                        if arg_name not in java_constants:
                            logger.warning(f"Constant '{arg_name}' not found for fact '{fact.predicate_name}'. Skipping fact.")
                            is_compatible_fact = False
                            break
                        
                        j_const = java_constants[arg_name]
                        j_args_list.append(j_const)
                        
                        actual_sort_name = str(j_const.getSort().getName())
                        expected_sort_name = str(expected_sorts_java.get(i).getName())
                        
                        if not self._is_compatible(actual_sort_name, expected_sort_name):
                            logger.warning(f"Pré-validation échouée pour le fait '{fact.predicate_name}({arg_name})'. "
                                         f"Sorte actuelle '{actual_sort_name}' n'est pas compatible avec la sorte attendue '{expected_sort_name}'. "
                                         "Ce fait ne sera pas ajouté, car il devrait être inférable par la hiérarchie.")
                            is_compatible_fact = False
                            break
                    
                    if not is_compatible_fact:
                        continue # Skip this fact
                    
                    # Convert list to ArrayList for Java
                    j_args = ArrayList()
                    for j_arg in j_args_list:
                        j_args.add(j_arg)

                    try:
                        atom = FolAtom(j_pred, j_args)
                        belief_set.add(atom)
                    except Exception as e:
                        logger.warning(f"La création de FolAtom a échoué pour le prédicat '{fact.predicate_name}' même après la pré-validation : {e}", exc_info=True)

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
                    
                    try:
                        atom = FolAtom(j_pred, j_args)
                        negated_formula = Negation(atom)
                        belief_set.add(negated_formula)
                    except Exception as e:
                        logger.warning(f"Could not create negated FolAtom for predicate '{fact.predicate_name}': {e}", exc_info=True)

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
                antecedent = FolAtom(ante_pred, ante_args)
                
                cons_pred = java_predicates.get(impl.consequent_predicate)
                cons_args = ArrayList()
                cons_args.add(j_var)
                consequent = FolAtom(cons_pred, cons_args)

                if antecedent and consequent:
                    implication = Implication(antecedent, consequent)
                    quantified_formula = ForallQuantifiedFormula(implication, j_var)
                    belief_set.add(quantified_formula)
                else:
                    logger.warning(f"Skipping universal implication due to atom creation failure: forall {var_name}:{impl.sort_of_variable}.({impl.antecedent_predicate}({var_name}) => {impl.consequent_predicate}({var_name}))")

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
                atom1 = FolAtom(p1, p1_args)
                
                p2 = java_predicates.get(ex.predicate2)
                p2_args = ArrayList()
                p2_args.add(j_var)
                atom2 = FolAtom(p2, p2_args)

                if atom1 and atom2:
                    conjunction = Conjunction(atom1, atom2)
                    quantified_formula = ExistsQuantifiedFormula(conjunction, j_var)
                    belief_set.add(quantified_formula)
                else:
                    logger.warning(f"Skipping existential conjunction due to atom creation failure: exists {var_name}:{ex.sort_of_variable}.({ex.predicate1}({var_name}) and {ex.predicate2}({var_name}))")

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
            logger.warning(f"Failed to build Tweety belief set due to an exception: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.warning(f"An unexpected error occurred during belief set construction: {e}", exc_info=True)
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
        # Forcer l'initialisation du FOL handler pour éviter les NoneType errors
        if self._tweety_bridge.initializer.is_jvm_ready():
            _ = self._tweety_bridge.fol_handler
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

    def _parse_and_invoke_tool_calls(self, llm_response: str):
        """
        Parses the LLM's text response to find and execute tool calls.
        This manual parsing is more robust for older SK versions.
        """
        import ast
        
        # Split response into individual lines, as LLM should provide one call per line
        for line in llm_response.strip().split('\n'):
            line = line.strip()
            if not line.startswith("BeliefBuilder."):
                continue

            # Regex to find `BeliefBuilder.method_name(arguments)`
            match = re.match(r"BeliefBuilder\.([a-zA-Z_]\w*)\((.*)\)", line)
            if not match:
                self.logger.warning(f"Could not parse tool call: {line}")
                continue

            method_name = match.group(1)
            args_str = match.group(2).strip()

            try:
                method_to_call = getattr(self._builder_plugin, method_name, None)
                if not method_to_call:
                    self.logger.warning(f"LLM tried to call non-existent method: {method_name}")
                    continue

                # Argument parsing using a more robust regex and ast.literal_eval
                kwargs = {}
                # This regex captures key-value pairs, handling strings and lists
                arg_pattern = re.compile(r"(\w+)\s*=\s*((?:'.*?'|\".*?\"|\[.*?\]))")
                
                for arg_match in arg_pattern.finditer(args_str):
                    key = arg_match.group(1)
                    value_str = arg_match.group(2)
                    
                    try:
                        # Use literal_eval on the value part only
                        value = ast.literal_eval(value_str)
                        kwargs[key] = value
                    except (ValueError, SyntaxError) as e:
                        self.logger.error(f"Could not parse argument value '{value_str}' for key '{key}' in tool call '{line}'. Error: {e}")
                        # Skip this argument
                        continue
                
                if not kwargs:
                    # Handle calls with no arguments if necessary
                    if args_str:
                       self.logger.warning(f"Could not parse any arguments from '{args_str}' for method '{method_name}'.")

                # --- Map LLM-generated argument names to actual Python function parameter names ---
                arg_mapping = {
                    "add_atomic_fact": {
                        "predicate_name": "fact_predicate_name",
                        "arguments": "fact_arguments",
                    },
                    "add_negated_atomic_fact": {
                        "predicate_name": "fact_predicate_name",
                        "arguments": "fact_arguments",
                    },
                    "add_universal_implication": {
                        "antecedent_predicate": "impl_antecedent_predicate",
                        "consequent_predicate": "impl_consequent_predicate",
                        "sort_of_variable": "impl_sort_of_variable",
                    },
                }

                mapped_kwargs = {}
                # Use the mapping if the method requires it
                if method_name in arg_mapping:
                    current_map = arg_mapping[method_name]
                    for key, value in kwargs.items():
                        # Map the key from the LLM response to the actual function parameter name
                        mapped_key = current_map.get(key, key)
                        mapped_kwargs[mapped_key] = value
                else:
                    # If no mapping is needed, use the arguments as they are
                    mapped_kwargs = kwargs
                
                self.logger.info(f"Manually invoking tool: {method_name} with mapped args: {mapped_kwargs}")
                method_to_call(**mapped_kwargs)

            except Exception as e:
                self.logger.error(f"Failed to invoke tool call: {line}. Error: {e}", exc_info=True)

    async def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[FirstOrderBeliefSet], str]:
        """
        Converts text to a FirstOrderBeliefSet by manually parsing LLM tool call suggestions.
        """
        self.logger.info(f"Début de la conversion de texte vers FOL (stratégie de parsing manuel) pour {self.name}...")
        self._builder_plugin.reset()

        try:
            # Simple invocation to get tool suggestions as text
            chat_history = ChatHistory(system_message=self.system_prompt)
            chat_history.add_user_message(text)

            arguments = KernelArguments()

            # Manually create a KernelFunctionFromPrompt, following this agent's specific pattern
            prompt_function = KernelFunctionFromPrompt(
                function_name="get_tool_calls_from_text",
                plugin_name="Instructions",
                prompt=self.system_prompt,
            )
    
            # Now invoke the function
            result = await self._kernel.invoke(
                function=prompt_function,
                arguments=KernelArguments(input=text)  # Pass the main text as 'input'
            )
            llm_response_text = str(result)
            
            # Manually parse and execute the tool calls from the response
            self._parse_and_invoke_tool_calls(llm_response_text)
            
            # --- PROCESS THE RESULTS ---
            self.logger.info("Le parsing et l'invocation manuelle des outils sont terminés.")
            self._builder_plugin._infer_sort_hierarchy()
            
            self.logger.info("Construction de l'ensemble de croyances Tweety...")
            java_belief_set = self._builder_plugin.build_tweety_belief_set(self._tweety_bridge)
            
            if java_belief_set is None:
                return FirstOrderBeliefSet(content="", java_object=None), "La construction programmatique du belief set a échoué. Le résultat est None."

            final_belief_set = FirstOrderBeliefSet(content=str(java_belief_set.toString()), java_object=java_belief_set)

            if final_belief_set.is_empty():
                 return final_belief_set, "Aucune structure logique pertinente n'a été trouvée."

            return final_belief_set, "Conversion réussie."

        except (KernelException, Exception) as e:
            self.logger.error(f"Exception interceptée dans `text_to_belief_set` ({type(e).__name__}). Re-levée pour un débogage complet.", exc_info=True)
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
            # La méthode fol_query attend la requête sous forme de chaîne de caractères.
            entails = self._tweety_bridge.fol_query(java_belief_set, query)
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
            is_cons, _ = await self._tweety_bridge.fol_check_consistency(java_belief_set)
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