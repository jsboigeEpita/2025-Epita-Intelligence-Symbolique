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
from typing import Dict, List, Optional, Any, Tuple, AsyncGenerator, NamedTuple
from abc import abstractmethod
import os

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.contents.chat_history import ChatHistory
# Imports are updated based on recent semantic-kernel changes
from semantic_kernel.agents.chat_completion.chat_completion_agent import FunctionChoiceBehavior
# The decorator has been moved to the top-level package for easier access.
from semantic_kernel.functions import kernel_function
from pydantic import Field, field_validator
 
from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent
from .belief_set import BeliefSet, FirstOrderBeliefSet
from .tweety_bridge import TweetyBridge

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
    def __init__(self):
        self.reset()

    def reset(self):
        """Réinitialise l'état interne du constructeur."""
        self._sorts: Dict[str, List[str]] = {}  # {sort_name: [const1, const2]}
        self._predicates: Dict[str, List[str]] = {}  # {pred_name: [sort1, sort2]}
        self._atomic_facts: List[AtomicFact] = []
        self._universal_implications: List[UniversalImplication] = []
        self._existential_conjunctions: List[ExistentialConjunction] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'état du builder en un dictionnaire sérialisable."""
        return {
            "_sorts": self._sorts,
            "_predicates": self._predicates,
            "_atomic_facts": [fact._asdict() for fact in self._atomic_facts],
            "_universal_implications": [impl._asdict() for impl in self._universal_implications],
            "_existential_conjunctions": [conj._asdict() for conj in self._existential_conjunctions],
        }

    def _normalize(self, name: str) -> str:
        """Normalise un identifiant pour être compatible avec Tweety."""
        import unidecode
        # Conserve la casse originale pour les prédicats, mais normalise les caractères
        name = unidecode.unidecode(name)
        # Remplace les espaces/caractères non alphanumériques par _ sauf pour les prédicats
        if name and not name[0].isupper():
             name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        return name

    @kernel_function(
        description="Déclare un nouveau sort (un type de catégorie, comme 'personne' ou 'ville').",
        name="add_sort",
    )
    def add_sort(self, sort_name: str):
        """Ajoute un sort à la base de connaissances."""
        norm_sort = self._normalize(sort_name)
        if norm_sort not in self._sorts:
            self._sorts[norm_sort] = []
        return f"Sort '{norm_sort}' ajouté."
    
    @kernel_function(
        description="Ajoute une constante (un objet spécifique, comme 'socrate') à un sort déclaré.",
        name="add_constant_to_sort",
    )
    def add_constant_to_sort(self, constant_name: str, sort_name: str):
        """Ajoute une constante à un sort."""
        norm_const = self._normalize(constant_name)
        norm_sort = self._normalize(sort_name)
        if norm_sort not in self._sorts:
            self.add_sort(norm_sort) # Tolérance : on crée le sort s'il manque
        if norm_const not in self._sorts[norm_sort]:
            self._sorts[norm_sort].append(norm_const)
        return f"Constante '{norm_const}' ajoutée au sort '{norm_sort}'."

    @kernel_function(
        description="Définit la 'signature' d'une relation ou propriété.",
        name="add_predicate_schema",
    )
    def add_predicate_schema(self, predicate_name: str, argument_sorts: List[str]):
        """Ajoute une déclaration de type de prédicat."""
        norm_pred = self._normalize(predicate_name)
        norm_args = []
        for s in argument_sorts:
            norm_s = self._normalize(s)
            if norm_s not in self._sorts:
                self.add_sort(norm_s) # Tolérance : on crée le sort s'il manque
            norm_args.append(norm_s)
        
        self._predicates[norm_pred] = norm_args
        return f"Schéma du prédicat '{norm_pred}' déclaré avec les arguments {norm_args}."

    @kernel_function(
        description="Ajoute un fait simple et atomique (ex: 'Socrate est un homme').",
        name="add_atomic_fact",
    )
    def add_atomic_fact(self, predicate_name: str, arguments: List[str]):
        """Stocke un fait atomique."""
        norm_pred = self._normalize(predicate_name)
        norm_args = [self._normalize(arg) for arg in arguments]
        self._atomic_facts.append(AtomicFact(predicate_name=norm_pred, arguments=norm_args))
        return f"Fait atomique '{norm_pred}({', '.join(norm_args)})' ajoute."

    @kernel_function(
        description="Ajoute une règle universelle (ex: 'Tous les hommes sont mortels').",
        name="add_universal_implication",
    )
    def add_universal_implication(self, antecedent_predicate: str, consequent_predicate: str, sort_of_variable: str):
        """Stocke une implication universelle."""
        norm_antecedent = self._normalize(antecedent_predicate)
        norm_consequent = self._normalize(consequent_predicate)
        norm_sort = self._normalize(sort_of_variable)

        # Tolérance : si un prédicat n'a pas été déclaré, on le fait implicitement
        # en supposant qu'il s'agit d'un prédicat unaire portant sur le sort de la variable.
        if norm_antecedent not in self._predicates:
            self.add_predicate_schema(norm_antecedent, [norm_sort])
        if norm_consequent not in self._predicates:
            self.add_predicate_schema(norm_consequent, [norm_sort])
            
        self._universal_implications.append(UniversalImplication(
            antecedent_predicate=norm_antecedent,
            consequent_predicate=norm_consequent,
            sort_of_variable=norm_sort
        ))
        return f"Implication universelle 'forall X: {norm_antecedent}(X) => {norm_consequent}(X)' ajoutée pour le sort '{norm_sort}'."

    @kernel_function(
        description="Ajoute une affirmation d'existence (ex: 'Certains penseurs sont des écrivains').",
        name="add_existential_conjunction",
    )
    def add_existential_conjunction(self, predicate1: str, predicate2: str, sort_of_variable: str):
        """Stocke une conjonction existentielle."""
        norm_pred1 = self._normalize(predicate1)
        norm_pred2 = self._normalize(predicate2)
        norm_sort = self._normalize(sort_of_variable)
        self._existential_conjunctions.append(ExistentialConjunction(
            predicate1=norm_pred1,
            predicate2=norm_pred2,
            sort_of_variable=norm_sort
        ))
        return f"Conjonction existentielle 'exists X: {norm_pred1}(X) && {norm_pred2}(X)' ajoutée pour le sort '{norm_sort}'."


    def build_fologic_string(self) -> str:
        """
        Construit la chaîne .fologic finale de manière ordonnée et robuste pour garantir
        la compatibilité avec le parseur Tweety.
        """
        declarations = []
        formulas = []

        # Étape 1: Déclarations des sorts et constantes
        # ===============================================
        # D'après l'analyse du parseur Java de Tweety, la déclaration `sorts = ...` est invalide.
        # La syntaxe correcte est de déclarer chaque sort sur sa propre ligne,
        # au format `sortname = {const1, const2}`.
        if self._sorts:
            all_sort_names = sorted(list(self._sorts.keys())) # Tri pour la déterminisme
            for sort_name in all_sort_names:
                constants = sorted(self._sorts[sort_name]) # Tri pour la déterminisme
                constant_str = ', '.join(constants)
                # La BNF est `sort = {const1, ...}`. Pour un sort vide, cela devient `sort = {}`.
                # Le parseur Java a un bug avec cette syntaxe, mais c'est la forme
                # que nous devons viser pour être sémantiquement corrects.
                declarations.append(f"{sort_name} = {{{constant_str}}}")

        # Étape 2: Inférence de prédicats manquants (stabilisation)
        # =========================================================
        # Parcourir toutes les formules pour s'assurer que chaque prédicat utilisé
        # est bien dans self._predicates avant de générer les 'type(...)'.

        for fact in self._atomic_facts:
            if fact.predicate_name not in self._predicates:
                arg_sorts = []
                for arg in fact.arguments:
                    found_sort = 'thing' # Fallback
                    for sort, constants in self._sorts.items():
                        if arg in constants:
                            found_sort = sort
                            break
                    arg_sorts.append(found_sort)
                self._predicates[fact.predicate_name] = arg_sorts

        for impl in self._universal_implications:
            if impl.antecedent_predicate not in self._predicates:
                self._predicates[impl.antecedent_predicate] = [impl.sort_of_variable]
            if impl.consequent_predicate not in self._predicates:
                self._predicates[impl.consequent_predicate] = [impl.sort_of_variable]
        
        for conj in self._existential_conjunctions:
            if conj.predicate1 not in self._predicates:
                self._predicates[conj.predicate1] = [conj.sort_of_variable]
            if conj.predicate2 not in self._predicates:
                self._predicates[conj.predicate2] = [conj.sort_of_variable]

        # Étape 3: Déclarations de tous les types de prédicats
        # ====================================================
        if self._predicates:
            sorted_preds = sorted(self._predicates.keys()) # Tri
            for pred_name in sorted_preds:
                args = self._predicates[pred_name]
                declarations.append(f"type({pred_name}({', '.join(args)}))")

        # Étape 4: Génération des formules
        # ================================
        
        # Faits atomiques
        for fact in self._atomic_facts:
            formulas.append(f"{fact.predicate_name}({', '.join(fact.arguments)})")

        # Implications universelles
        for impl in self._universal_implications:
            var_name = impl.sort_of_variable[0].upper()
            formulas.append(f"forall {var_name}:{impl.sort_of_variable} ({impl.antecedent_predicate}({var_name}) => {impl.consequent_predicate}({var_name}))")

        # Conjonctions existentielles
        for conj in self._existential_conjunctions:
            var_name = conj.sort_of_variable[0].upper()
            formulas.append(f"exists {var_name}:{conj.sort_of_variable} ({conj.predicate1}({var_name}) && {conj.predicate2}({var_name}))")

        # Assemblage final
        # On s'assure de ne pas avoir de ligne vide entre les sections si l'une d'elles est vide.
        final_lines = []
        if declarations:
            final_lines.extend(declarations)
        if formulas:
            final_lines.extend(formulas)
            
        return "\n".join(final_lines)


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
        self._use_serialization = True  # La sérialisation est maintenant la stratégie par défaut et obligatoire
        if kernel and service_id:
            try:
                self.service = kernel.get_service(service_id, type=ChatCompletionClientBase)
            except Exception as e:
                self.logger.warning(f"Could not retrieve service '{service_id}': {e}")
        
        self._tweety_bridge = tweety_bridge
        # Le plugin qui contient nos outils. Il sera instancié ici.
        self._builder_plugin = BeliefSetBuilderPlugin()
        self.logger.info(f"Agent {self.name} initialisé. Stratégie: Appel d'Outils (Sérialisation JIT activée par défaut).")

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

        if not self.tweety_bridge.is_jvm_ready():
            self.logger.error("Tentative de setup FOL Kernel alors que la JVM n'est PAS démarrée.")
            # Levee d'une exception pour interrompre le test
            raise RuntimeError("TweetyBridge not initialized, JVM not ready.")

        default_settings = self._kernel.get_prompt_execution_settings_from_service_id(llm_service_id)
        
        # Ajout du plugin de construction comme une collection d'outils
        self._kernel.add_plugin(self._builder_plugin, plugin_name="BeliefBuilder")
        
        # Ajout des autres fonctions sémantiques nécessaires (celles-ci peuvent rester basées sur des prompts)
        prompts = {
            "GenerateFOLQueries": PROMPT_GEN_FOL_QUERIES,
            "InterpretFOLResult": PROMPT_INTERPRET_FOL
        }
        for name, prompt in prompts.items():
            self._kernel.add_function(
                prompt=prompt,
                plugin_name=self.name,
                function_name=name,
                prompt_execution_settings=default_settings
            )
        self.logger.info(f"Plugin 'BeliefBuilder' et fonctions sémantiques pour {self.name} ajoutés au kernel.")
            
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
        
        # Paramètres d'exécution pour forcer l'appel d'outils
        # Conformément à la documentation de semantic-kernel v1+, nous devons obtenir
        # la classe des settings directement depuis le service pour garantir le bon type,
        # puis configurer le comportement de choix de fonction.
        settings_class = self.service.get_prompt_execution_settings_class()
        execution_settings = settings_class(service_id=self._llm_service_id)
        execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

        try:
            # La liaison des outils se fait maintenant implicitement en passant l'objet `kernel`
            # à la méthode ci-dessous. Aucune manipulation manuelle des `tools` n'est requise.
            result = await self.service.get_chat_message_content(
                chat,
                settings=execution_settings,
                kernel=self._kernel
            )

            self.logger.info("Le LLM a terminé d'appeler les outils.")
            
            # --- DEBUG: Inspecter les données collectées par le plugin ---
            self.logger.critical(f"DONNÉES DU PLUGIN POUR LE HANDLER: {self._builder_plugin.__dict__}")
            # --- FIN DEBUG ---

            self.logger.info("Construction de la chaîne .fologic à partir des données du plugin.")
            belief_set_content_str = self._builder_plugin.build_fologic_string()
            self.logger.debug(f"Chaîne .fologic construite:\n{belief_set_content_str}")

            if not belief_set_content_str.strip():
                self.logger.warning("Le builder a produit une chaîne .fologic vide.")
                return None, "Le LLM n'a extrait aucune structure logique du texte."

            # La stratégie est maintenant 100% basée sur la sérialisation de la chaîne .fologic.
            final_belief_set = FirstOrderBeliefSet(content=belief_set_content_str, java_object=None)

            # Valider immédiatement la syntaxe pour un feedback rapide.
            java_obj = await self._recreate_java_belief_set(final_belief_set)
            if java_obj is None:
                return None, "La chaîne .fologic générée est syntaxiquement invalide."

            self.logger.info("Conversion via la stratégie d'appel d'outils réussie.")
            return final_belief_set, "Conversion réussie."

        except Exception as e:
            self.logger.error(f"Exception interceptée dans `text_to_belief_set`. Re-levée pour un débogage complet.", exc_info=True)
            raise e

    # Les fonctions _extract_fologic_block et _sanitize_fologic_string ne sont plus nécessaires
    # car la génération de la chaîne est maintenant déterministe et contrôlée en interne.
    
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
            result = await self._kernel.functions[self.name]["GenerateFOLQueries"].invoke(self._kernel, **args)
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
        Recrée l'objet Java à la volée si nécessaire (mode sérialisation).
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
            
            result = await self._kernel.functions[self.name]["InterpretFOLResult"].invoke(
                self._kernel,
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
        Recreates the Java object on-the-fly if needed (serialization mode).
        """
        self.logger.info(f"Vérification de la consistance pour {self.name}")
        
        java_belief_set = await self._recreate_java_belief_set(belief_set)
        if not java_belief_set:
            return False, "Impossible de recréer ou de trouver l'objet belief set Java pour la vérification de consistance."
            
        try:
            return self.tweety_bridge._fol_handler.fol_check_consistency(java_belief_set)
        except Exception as e:
            self.logger.error(f"Erreur inattendue durant la vérification de consistance: {e}", exc_info=True)
            return False, str(e)

    async def _recreate_java_belief_set(self, belief_set: FirstOrderBeliefSet) -> Optional[Any]:
        """
        Garantit qu'un objet Java BeliefSet est disponible.
        En mode sérialisation, il le recrée à partir du contenu stocké (syntaxe native).
        Sinon, il retourne celui qui est déjà stocké.
        """
        if belief_set.java_object:
            self.logger.debug("Utilisation de l'objet Java BeliefSet préexistant.")
            return belief_set.java_object
            
        if not belief_set.content or not belief_set.content.strip():
            self.logger.warning("Reconstruction JIT ignorée: pas de contenu pour recréer l'objet BeliefSet.")
            # Il est valide d'avoir un belief set vide. Ce n'est pas une erreur.
            # On peut créer un BeliefSet vide pour la validation de formules sans contexte.
            try:
                return self.tweety_bridge.create_empty_belief_set()
            except Exception as e:
                self.logger.error(f"Impossible de créer même un BeliefSet vide: {e}", exc_info=True)
                return None

        self.logger.info("Reconstruction JIT de l'objet BeliefSet Java à partir de la syntaxe native...")
        try:
            java_object = self.tweety_bridge.create_belief_set_from_string(belief_set.content)
            
            if not java_object:
                 raise RuntimeError("La création du BeliefSet à partir de la chaîne a retourné None, ce qui ne devrait pas arriver.")

            self.logger.info("Reconstruction JIT à partir de la syntaxe native réussie.")
            return java_object
            
        except (RuntimeError, jpype.JException, ValueError) as e:
            self.logger.error(f"Échec de la reconstruction JIT du BeliefSet: {e}", exc_info=True)
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
            # La réparation de la conclusion est désactivée car elle dépendait de l'ancienne logique JSON
            # et de _normalize_logical_structure.
            # Une nouvelle logique de réparation serait nécessaire pour la syntaxe native.
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