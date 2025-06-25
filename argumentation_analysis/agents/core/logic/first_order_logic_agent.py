# FORCE_RELOAD
# argumentation_analysis/agents/core/logic/first_order_logic_agent.py
"""
Définit l'agent spécialisé dans le raisonnement en logique du premier ordre (FOL).
"""

import logging
import re
import json
import jpype
import asyncio
from typing import Dict, List, Optional, Any, Tuple, AsyncGenerator

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from pydantic import Field

from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent
from .belief_set import BeliefSet, FirstOrderBeliefSet
from .tweety_bridge import TweetyBridge

logger = logging.getLogger(__name__)

# ==============================================================================
# STRATÉGIE D'ARCHITECTURE (BASÉE SUR LES OUTILS SIMPLIFIÉS)
# ------------------------------------------------------------------------------
# L'approche consiste à utiliser un plugin avec des outils pour que le LLM
# construise la base de connaissances.
# Cette version restaure une approche qui a montré des résultats partiels :
# un prompt système très directif et un ensemble d'outils simples.
# ==============================================================================

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
        self._sorts: Dict[str, List[str]] = {}
        self._predicates: Dict[str, List[str]] = {}
        self._formulas: List[str] = []

    def _normalize(self, name: str) -> str:
        """Normalise un identifiant pour être compatible avec Tweety."""
        import unidecode
        name = unidecode.unidecode(name)
        # Conserver la capitalisation pour les noms propres (qui commencent par une majuscule)
        if name and not name[0].isupper():
            name = name.lower()
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        return name

    @kernel_function(
        description="Déclare un nouveau sort (une catégorie comme 'personne' ou 'chose').",
        name="add_sort",
    )
    def add_sort(self, sort_name: str, constants: Optional[List[str]] = None):
        norm_sort = self._normalize(sort_name)
        if norm_sort not in self._sorts:
            self._sorts[norm_sort] = []
        if constants:
            for const in constants:
                norm_const = self._normalize(const)
                if norm_const not in self._sorts[norm_sort]:
                    self._sorts[norm_sort].append(norm_const)
        return f"Sort '{norm_sort}' ajouté/mis à jour."

    @kernel_function(
        description="Assigne un objet spécifique (constante) à un sort.",
        name="add_constant",
    )
    def add_constant(self, constant_name: str, sort_name: str):
        norm_const = self._normalize(constant_name)
        norm_sort = self._normalize(sort_name)
        if norm_sort not in self._sorts:
            self._sorts[norm_sort] = []
        if norm_const not in self._sorts[norm_sort]:
            self._sorts[norm_sort].append(norm_const)
        return f"Constante '{norm_const}' ajoutée au sort '{norm_sort}'."

    @kernel_function(
        description="Déclare un prédicat (relation) et les sorts de ses arguments.",
        name="add_predicate",
    )
    def add_predicate(self, predicate_name: str, argument_sorts: List[str]):
        norm_pred = self._normalize(predicate_name)
        norm_args = [self._normalize(s) for s in argument_sorts]
        self._predicates[norm_pred] = norm_args
        return f"Prédicat '{norm_pred}' déclaré."

    @kernel_function(
        description="Ajoute une formule logique (un fait ou une règle) à la base de connaissance.",
        name="add_formula",
    )
    def add_formula(self, formula: str):
        self._formulas.append(formula)
        return f"Formule '{formula}' ajoutée."

    def build_fologic_string(self) -> str:
        """Construit la chaîne .fologic finale à partir de l'état accumulé."""
        lines = []
        for sort, constants in self._sorts.items():
            if constants:
                lines.append(f"sort({sort}, {{{', '.join(constants)}}})")
            else:
                lines.append(f"sort({sort})")

        for pred, args in self._predicates.items():
            lines.append(f"predicate({pred}({', '.join(args)}))")
            
        lines.extend(f"formula({f})" for f in self._formulas)
        
        return "\n".join(lines)

# Le prompt système qui a donné les meilleurs résultats partiels
SYSTEM_PROMPT_FOL = """Vous êtes un assistant expert en logique. Votre objectif est de traduire un texte en langage naturel vers une représentation en logique du premier ordre (FOL) en utilisant les outils à votre disposition.
**Votre processus de pensée doit être le suivant :**

**PHASE 1 : Déclaration des Entités**
1.  **Identifier les Concepts Clés :** Lisez le texte pour trouver les catégories (sorts), les objets spécifiques (constantes), et les relations/propriétés (prédicats).
2.  **Construire la Base de Connaissances :** Utilisez les outils `add_sort`, `add_constant`, et `add_predicate` pour déclarer **TOUS** les éléments nécessaires. Vous **DEVEZ** déclarer un sort ou une constante avant de pouvoir l'utiliser dans un prédicat ou une formule.

**PHASE 2 : Formalisation des Affirmations**
3.  **Traduire chaque phrase :** Utilisez l'outil `add_formula` pour traduire chaque phrase ou idée en une formule logique valide.

**Instructions cruciales pour les formules :**
*   **QUANTIFICATEURS UNIVERSELS (`forall`) :**
    *   La syntaxe **CORRECTE** est `forall(X, implies(antecedent, consequent))`.
    *   **Exemple :** "Tous les hommes sont mortels" se traduit par `add_formula("forall(X, implies(Man(X), Mortal(X)))")`. Vous devez utiliser le prédicat du sort (ex: `Man(X)`) comme antécédent de l'implication.
*   **PRÉDICATS MULTI-ARGUMENTS :** Assurez-vous que le nombre de variables correspond à la déclaration du prédicat.

**Exemple complet :**
Texte : "Socrate est un homme. Tous les hommes sont mortels."
Appels attendus:
1. `add_sort(sort_name="Philosopher")`
2. `add_constant(constant_name="Socrates", sort_name="Philosopher")`
3. `add_predicate(predicate_name="Man", argument_sorts=["Philosopher"])`
4. `add_predicate(predicate_name="Mortal", argument_sorts=["Philosopher"])`
5. `add_formula(formula="Man(Socrates)")`
6. `add_formula(formula="forall(X, implies(Man(X), Mortal(X)))")`

Respectez scrupuleusement cet ordre et cette syntaxe.
"""

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
**Contexte :**
*   **Texte :** {{$input}}
*   **Belief Set (signature et formules existantes) :** {{$belief_set}}
Génère le JSON contenant les requêtes.
"""

PROMPT_INTERPRET_FOL = """Expert FOL : Interprétez les résultats de requêtes FOL en langage accessible.
**Contexte :**
*   **Texte original :** {{$input}}
*   **Ensemble de croyances (Belief Set) :** {{$belief_set}}
*   **Requêtes exécutées :** {{$queries}}
*   **Résultats bruts de Tweety :** {{$tweety_result}}
**Votre Tâche :**
Pour chaque requête, fournissez une interprétation claire.
"""

class FirstOrderLogicAgent(BaseLogicAgent):
    """
    Agent spécialiste de l'analyse en logique du premier ordre (FOL).
    """
    service: Optional[ChatCompletionClientBase] = Field(default=None, exclude=True)

    def __init__(self, kernel: Kernel, agent_name: str = "FirstOrderLogicAgent", service_id: Optional[str] = None, use_serialization: bool = True):
        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            logic_type_name="FOL",
            system_prompt=SYSTEM_PROMPT_FOL
        )
        self._llm_service_id = service_id
        self._use_serialization = use_serialization
        if kernel and service_id:
            try:
                self.service = kernel.get_service(service_id, type=ChatCompletionClientBase)
            except Exception as e:
                self.logger.warning(f"Could not retrieve service '{service_id}': {e}")
        
        self._tweety_bridge = None
        self._builder_plugin = BeliefSetBuilderPlugin()
        self.logger.info(f"Agent {self.name} initialisé.")

    def get_agent_capabilities(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "logic_type": self.logic_type,
            "description": "Agent capable d'analyser du texte en utilisant la logique du premier ordre (FOL).",
            "methods": {
                "text_to_belief_set": "Convertit un texte en un ensemble de croyances FOL.",
                "generate_queries": "Génère des requêtes FOL pertinentes.",
                "execute_query": "Exécute une requête FOL sur un ensemble de croyances.",
            }
        }

    async def setup_agent_components(self, llm_service_id: str) -> None:
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants pour {self.name}...")
        self._tweety_bridge = TweetyBridge()
        if hasattr(self._tweety_bridge, 'wait_for_jvm') and asyncio.iscoroutinefunction(self._tweety_bridge.wait_for_jvm):
            await self._tweety_bridge.wait_for_jvm()
        if not self.tweety_bridge.is_jvm_ready():
            raise RuntimeError("TweetyBridge not initialized, JVM not ready.")

        self._kernel.add_plugin(self._builder_plugin, plugin_name="BeliefBuilder")
        
        prompts = {
            "GenerateFOLQueries": PROMPT_GEN_FOL_QUERIES,
            "InterpretFOLResult": PROMPT_INTERPRET_FOL
        }
        default_settings = self._kernel.get_prompt_execution_settings_from_service_id(llm_service_id)
        for name, prompt in prompts.items():
            self._kernel.add_function(
                prompt=prompt,
                plugin_name=self.name,
                function_name=name,
                prompt_execution_settings=default_settings
            )
        self.logger.info(f"Plugin 'BeliefBuilder' et fonctions sémantiques pour {self.name} ajoutés au kernel.")

    async def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[FirstOrderBeliefSet], str]:
        self.logger.info(f"Début de la conversion de texte vers FOL pour {self.name}...")
        self._builder_plugin.reset()

        chat = ChatHistory(system_message=SYSTEM_PROMPT_FOL)
        chat.add_user_message(text)
        
        execution_settings = self._kernel.get_prompt_execution_settings_from_service_id(self._llm_service_id)
        execution_settings.tool_choice = "auto"
        
        try:
            # Invocation du kernel avec le chat, qui va utiliser les outils du BeliefBuilderPlugin
            result = await self._kernel.invoke(
                prompt=text,
                chat_history=chat,
                settings=execution_settings
            )
            
            # Gérer les appels de fonction retournés
            function_calls = [item for item in result.items if isinstance(item, FunctionCallContent)]
            
            if not function_calls:
                self.logger.warning("Le LLM n'a retourné aucun appel de fonction. Tentative de traitement du contenu texte.")
                # Fallback si aucun appel d'outil n'est fait
                content_str = str(result)
                if not content_str:
                    return None, "L'analyse n'a produit aucune structure logique."

            # Le kernel devrait avoir déjà appelé les fonctions du plugin et mis à jour son état interne.
            # Nous pouvons maintenant construire la chaîne de syntaxe.
            
            tweety_syntax_str = self._builder_plugin.build_fologic_string()
            
            if not tweety_syntax_str.strip():
                return None, "L'analyse n'a produit aucune structure logique."

            self.logger.critical(f"--- SYNTAXE .FOLOGIC GÉNÉRÉE ---\n{tweety_syntax_str}\n---------------------------------")
            
            belief_set_obj = self.tweety_bridge.create_belief_set_from_string(tweety_syntax_str)
            
            if self._use_serialization:
                final_belief_set = FirstOrderBeliefSet(content=tweety_syntax_str, java_object=None)
            else:
                final_belief_set = FirstOrderBeliefSet(content=tweety_syntax_str, java_object=belief_set_obj)

            self.logger.info("Conversion via la stratégie d'appel d'outils réussie.")
            return final_belief_set, "Conversion réussie."

        except jpype.JException as j_exc:
            error_message = str(j_exc)
            self.logger.error(f"Erreur Java (Tweety) durant la conversion : {error_message}", exc_info=True)
            # Ajout du contenu qui a causé l'erreur pour le débogage
            failed_content = self._builder_plugin.build_fologic_string()
            self.logger.error(f"Contenu ayant échoué:\n{failed_content}")
            return None, f"Tweety ParserException: {error_message}"
        except Exception as e:
            last_error = str(e)
            self.logger.error(f"Une erreur est survenue durant le processus : {last_error}", exc_info=True)
            return None, f"Échec final. Erreur: {last_error}"

    def _extract_json_block(self, text: str) -> str:
        match = re.search(r"```(json)?\s*(.*?)\s*```", text, re.DOTALL)
        return match.group(2).strip() if match else text

    async def generate_queries(self, text: str, belief_set: FirstOrderBeliefSet, **kwargs) -> List[str]:
        self.logger.info(f"Génération de requêtes FOL pour {self.name}...")
        try:
            if not belief_set or not belief_set.content:
                return []
            args = {"input": text, "belief_set": belief_set.content}
            result = await self._kernel.functions[self.name]["GenerateFOLQueries"].invoke(self._kernel, **args)
            queries = json.loads(self._extract_json_block(str(result))).get("queries", [])
            
            valid_queries = [q for q in queries if await self.validate_formula(q, belief_set)]
            return valid_queries
        except Exception as e:
            self.logger.error(f"Erreur durant la génération de requêtes: {e}", exc_info=True)
            return []

    async def execute_query(self, belief_set: FirstOrderBeliefSet, query: str) -> Tuple[Optional[bool], str]:
        self.logger.info(f"Exécution de la requête: {query} pour l'agent {self.name}")
        java_belief_set = await self._recreate_java_belief_set(belief_set)
        if not java_belief_set:
            return None, "Impossible de recréer l'objet belief set Java."
        try:
            entails = self.tweety_bridge.query(java_belief_set, query)
            result_str = "ACCEPTED" if entails else "REJECTED"
            return entails, result_str
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête: {e}"
            self.logger.error(error_msg, exc_info=True)
            return None, f"FUNC_ERROR: {error_msg}"

    async def interpret_results(self, text: str, belief_set: BeliefSet, queries: List[str], results: List[Tuple[Optional[bool], str]], context: Optional[Dict[str, Any]] = None) -> str:
        self.logger.info(f"Interprétation des résultats pour l'agent {self.name}...")
        # ... implémentation ...
        return "Interprétation non implémentée dans cette version."

    async def validate_formula(self, formula: str, belief_set: Optional[FirstOrderBeliefSet] = None) -> bool:
        self.logger.debug(f"Validation de la formule FOL: {formula}")
        # ... implémentation ...
        return self.tweety_bridge.validate_formula(formula, belief_set)

    async def is_consistent(self, belief_set: FirstOrderBeliefSet) -> Tuple[bool, str]:
        self.logger.info(f"Vérification de la consistance pour {self.name}")
        java_belief_set = await self._recreate_java_belief_set(belief_set)
        if not java_belief_set:
            return False, "Impossible de recréer l'objet belief set Java."
        return self.tweety_bridge.check_consistency(java_belief_set)

    async def _recreate_java_belief_set(self, belief_set: FirstOrderBeliefSet) -> Optional[Any]:
        if belief_set.java_object and not self._use_serialization:
            return belief_set.java_object
        if not belief_set.content:
            return None
        self.logger.info("Reconstruction JIT de l'objet BeliefSet Java...")
        try:
            return self.tweety_bridge.create_belief_set_from_string(belief_set.content)
        except Exception as e:
            self.logger.error(f"Échec de la reconstruction JIT du BeliefSet: {e}", exc_info=True)
            return None

    # Méthodes génériques de l'agent
    async def get_response(self, chat_history: ChatHistory, **kwargs) -> AsyncGenerator[List[ChatMessageContent], None]:
        logger.warning(f"La méthode 'get_response' n'est pas l'interaction standard pour {self.name}.")
        yield []
    
    async def invoke_single(self, chat_history: ChatHistory, **kwargs) -> ChatMessageContent:
        last_user_message = next((m.content for m in reversed(chat_history) if m.role == "user"), None)
        if not last_user_message or not isinstance(last_user_message, str):
            return ChatMessageContent(role="assistant", content="Veuillez fournir une instruction en texte.")
        
        belief_set, status = await self.text_to_belief_set(last_user_message)
        response_content = belief_set.to_dict() if belief_set else {"error": status}
        return ChatMessageContent(role="assistant", content=json.dumps(response_content), name=self.name)