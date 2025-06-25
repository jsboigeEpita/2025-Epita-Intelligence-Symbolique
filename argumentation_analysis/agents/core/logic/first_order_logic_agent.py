# argumentation_analysis/agents/core/logic/first_order_logic_agent.py
"""
Définit l'agent spécialisé dans le raisonnement en logique du premier ordre (FOL),
en s'appuyant sur une architecture de tool-calling robuste et éprouvée.
"""

import logging
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple

import jpype
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from semantic_kernel.connectors.ai.open_ai import OpenAIPromptExecutionSettings
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.prompt_template.prompt_template_config import PromptTemplateConfig
from semantic_kernel.prompt_template.kernel_prompt_template import KernelPromptTemplate
from pydantic import Field
import unidecode

from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent
from .belief_set import FirstOrderBeliefSet
from .tweety_bridge import TweetyBridge

logger = logging.getLogger(__name__)


# ==============================================================================
# PROMPT SYSTÈME (VERSION FINALE VALIDÉE)
# ------------------------------------------------------------------------------
# Ce prompt est la version la plus performante identifiée lors de l'analyse
# des snapshots (inspiré de conv3_snapshot7).
# ==============================================================================
SYSTEM_PROMPT_FOL = """Vous êtes un assistant expert en logique. Votre objectif est de traduire un texte en langage naturel vers une représentation en logique du premier ordre (FOL) en utilisant les outils à votre disposition.

**Votre processus de pensée doit être le suivant :**

**PHASE 1 : Déclaration des Entités (SIGNATURE)**
1.  **Identifier les Concepts :** Lisez le texte pour trouver les catégories (sorts), les objets spécifiques (constantes), et les relations/propriétés (prédicats).
2.  **Construire la Signature :** Utilisez les outils `add_sort`, `add_constant`, et `add_predicate` pour déclarer **TOUS** les éléments nécessaires. Vous **DEVEZ** déclarer un sort, une constante ou un prédicat avant de l'utiliser dans une formule.

**PHASE 2 : Formalisation des Affirmations (FORMULES)**
3.  **Traduire chaque phrase :** Une fois la signature complète, utilisez l'outil `add_formula` pour traduire chaque phrase ou idée en une formule logique valide.

**Règles de syntaxe pour les formules :**
*   **QUANTIFICATEURS UNIVERSELS (`forall`) :** La syntaxe est `forall(X, implies(antecedent, consequent))`.
    *   **Exemple :** "Tous les hommes sont mortels" se traduit par `add_formula("forall(X, implies(Man(X), Mortal(X)))")`. Le prédicat du sort (`Man(X)`) doit être l'antécédent de l'implication.
*   **QUANTIFICATEURS EXISTENTIELS (`exists`) :** La syntaxe est `exists(X, antecedent)`.
    *   **Exemple :** "Il existe un oiseau qui ne vole pas" se traduit par`add_formula("exists(X, and(Bird(X), not(Flies(X))))")`.

**Exemple complet :**
Texte : "Socrate est un homme. Tous les hommes sont mortels."
Appels attendus:
1. `add_sort(sort_name="philosopher")`
2. `add_constant(constant_name="socrates", sort_name="philosopher")`
3. `add_predicate(predicate_name="man", argument_sorts=["philosopher"])`
4. `add_predicate(predicate_name="mortal", argument_sorts=["philosopher"])`
5. `add_formula(formula="man(socrates)")`
6. `add_formula(formula="forall(X, implies(man(X), mortal(X)))")`

Respectez scrupuleusement cet ordre et cette syntaxe. Assurez-vous que tous les identifiants sont en minuscules et sans caractères spéciaux.
"""

# ==============================================================================
# PLUGIN POUR LA CONSTRUCTION DE LA BASE DE CONNAISSANCES
# ==============================================================================
class BeliefSetBuilderPlugin:
    """
    Plugin sémantique fournissant des outils pour construire une base de
    connaissances FOL de manière incrémentale via des appels de LLM.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        """Réinitialise l'état interne du constructeur."""
        self._sorts: Dict[str, List[str]] = {}
        self._predicates: Dict[str, List[str]] = {}
        self._formulas: List[str] = []
        logger.debug("BeliefSetBuilderPlugin a été réinitialisé.")

    def _normalize(self, name: str) -> str:
        """Normalise un identifiant pour la compatibilité avec Tweety."""
        name = unidecode.unidecode(name).lower()
        # Remplace les caractères non alphanumériques par des underscores
        # et s'assure que le nom ne commence pas par un chiffre.
        name = name.replace("-", "_").replace(" ", "_")
        return f"_{name}" if name and name[0].isdigit() else name

    @kernel_function(description="Déclare un nouveau sort (catégorie) et optionnellement les constantes qui lui appartiennent.", name="add_sort")
    def add_sort(self, sort_name: str, constants: Optional[List[str]] = None) -> str:
        norm_sort = self._normalize(sort_name)
        if norm_sort not in self._sorts:
            self._sorts[norm_sort] = []
        if constants:
            for const in constants:
                norm_const = self._normalize(const)
                if norm_const not in self._sorts[norm_sort]:
                    self._sorts[norm_sort].append(norm_const)
        return f"Sort '{norm_sort}' ajouté/mis à jour avec les constantes {self._sorts[norm_sort]}."

    @kernel_function(description="Assigne une constante (objet spécifique) à un sort existant.", name="add_constant")
    def add_constant(self, constant_name: str, sort_name: str) -> str:
        norm_const = self._normalize(constant_name)
        norm_sort = self._normalize(sort_name)
        if norm_sort not in self._sorts:
            return f"Erreur : Le sort '{norm_sort}' n'existe pas. Veuillez d'abord l'ajouter avec add_sort."
        if norm_const not in self._sorts[norm_sort]:
            self._sorts[norm_sort].append(norm_const)
        return f"Constante '{norm_const}' ajoutée au sort '{norm_sort}'."

    @kernel_function(description="Déclare un nouveau prédicat (relation) et les sorts de ses arguments.", name="add_predicate")
    def add_predicate(self, predicate_name: str, argument_sorts: List[str]) -> str:
        norm_pred = self._normalize(predicate_name)
        norm_args = [self._normalize(s) for s in argument_sorts]
        self._predicates[norm_pred] = norm_args
        return f"Prédicat '{norm_pred}' déclaré avec les arguments de sorts {norm_args}."

    @kernel_function(description="Ajoute une formule logique (fait ou règle) à la base de connaissances.", name="add_formula")
    def add_formula(self, formula: str) -> str:
        self._formulas.append(formula)
        return f"Formule '{formula}' ajoutée."

    def build_fologic_string(self) -> str:
        """
        Construit une chaîne de caractères au format .fologic.
        Hypothèse actuelle (v9): Déclaration des prédicats par arité,
        ex: `predicate(nom, arite).`
        """
        lines = []

        # 1. Déclaration des sorts (syntaxe confirmée)
        for sort, constants in self._sorts.items():
            if constants:
                const_str = ', '.join(constants)
                lines.append(f"{sort} = {{{const_str}}}.")

        # 2. Déclaration des prédicats par leur nom et arité.
        # C'est une nouvelle hypothèse pour résoudre les erreurs de parsing.
        # La syntaxe des arguments de sorts (ex: `man(philosopher)`) n'est
        # peut-être pas dans la déclaration, mais seulement vérifiée lors
        # de l'utilisation dans les formules.
        for pred, args in self._predicates.items():
            arity = len(args)
            lines.append(f"predicate({pred}, {arity}).")

        # 3. Déclaration des formules
        lines.extend(f"{f}." for f in self._formulas)

        # Joindre avec des sauts de ligne simples pour un parsing plus sûr.
        return "\n".join(lines)


# ==============================================================================
# AGENT DE LOGIQUE DU PREMIER ORDRE
# ==============================================================================
class FirstOrderLogicAgent(BaseLogicAgent):
    """
    Agent spécialiste de l'analyse en logique du premier ordre (FOL)
    utilisant une architecture à base d'appels d'outils.
    """
    MAX_TOOL_ITERATIONS = 15

    service: Optional[ChatCompletionClientBase] = Field(default=None, exclude=True)

    def __init__(self, kernel: Kernel, agent_name: str = "FirstOrderLogicAgent", service_id: Optional[str] = None):
        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            logic_type_name="FOL",
            system_prompt=SYSTEM_PROMPT_FOL
        )
        self._llm_service_id = service_id
        if kernel and service_id:
            try:
                self.service = kernel.get_service(service_id, type=ChatCompletionClientBase)
            except Exception as e:
                logger.warning(f"Impossible de récupérer le service '{service_id}': {e}")
        
        self._tweety_bridge = TweetyBridge()
        self._builder_plugin = BeliefSetBuilderPlugin()
        kernel.add_plugin(self._builder_plugin, plugin_name="BeliefBuilder")
        
        logger.info(f"Agent {self.name} initialisé avec le plugin 'BeliefBuilder'.")
    
    async def setup_agent_components(self):
        """Assure que le pont JVM est prêt."""
        logger.info(f"Vérification de l'état du pont JVM pour {self.name}...")
        # La fixture jvm_session a déjà démarré la JVM. On vérifie juste que le bridge est ok.
        if not self._tweety_bridge.is_jvm_ready():
            raise RuntimeError("Le pont Tweety signale que la JVM n'est pas prête, même après l'appel de la fixture.")
        logger.info("Pont JVM prêt.")

    async def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[FirstOrderBeliefSet], str]:
        """
        Convertit un texte en langage naturel en un ensemble de croyances FOL
        en orchestrant une conversation avec le LLM via des appels d'outils.
        """
        logger.info(f"Début de la conversion FOL pour le texte : '{text[:80]}...'")
        self._builder_plugin.reset()

        chat = ChatHistory(system_message=self.system_prompt)
        chat.add_user_message(text)

        settings = OpenAIPromptExecutionSettings(
            service_id=self._llm_service_id,
            function_choice_behavior=FunctionChoiceBehavior.Auto(filters={
                "included_plugins": ["BeliefBuilder"]
            }),
        )

        try:
            for i in range(self.MAX_TOOL_ITERATIONS):
                logger.debug(f"Itération {i+1}/{self.MAX_TOOL_ITERATIONS} de l'appel d'outil.")
                
                response = (await self.service.get_chat_message_contents(chat, settings, kernel=self._kernel))[0]
                chat.add_message(response)
                
                tool_calls = [item for item in response.items if isinstance(item, FunctionCallContent)]

                if not tool_calls:
                    logger.info("Aucun autre appel d'outil demandé par le LLM. Fin de la conversion.")
                    break
                
                for tool_call in tool_calls:
                    logger.info(f"Invocation de l'outil : {tool_call.plugin_name}.{tool_call.function_name}({tool_call.arguments})")
                    result = await self._kernel.invoke(
                        plugin_name=tool_call.plugin_name,
                        function_name=tool_call.function_name,
                        **json.loads(tool_call.arguments)
                    )
                    chat.add_tool_message(str(result.value), tool_call_id=tool_call.id)

            else:
                logger.warning("Nombre maximal d'itérations d'outils atteint. Forçage de la fin.")

            # Construit la chaîne finale à partir de l'état du plugin
            fologic_string = self._builder_plugin.build_fologic_string()
            if not fologic_string.strip():
                return None, "L'analyse LLM n'a produit aucune structure logique."

            logger.info("--- SYNTAXE .FOLOGIC GÉNÉRÉE ---")
            logger.info(fologic_string)
            logger.info("---------------------------------")
            
            # Utilise Tweety pour valider et créer l'objet BeliefSet
            belief_set_obj = self._tweety_bridge.create_belief_set_from_string(fologic_string)
            
            final_belief_set = FirstOrderBeliefSet(content=fologic_string, java_object=belief_set_obj)

            return final_belief_set, "Conversion réussie."

        except jpype.JException as j_exc:
            error_message = f"Erreur Java (Tweety): {j_exc.getMessage()}"
            failed_content = self._builder_plugin.build_fologic_string()
            logger.error(f"{error_message}\nContenu ayant échoué:\n{failed_content}", exc_info=True)
            return None, f"Tweety ParserException: {error_message}"
        except Exception as e:
            logger.error(f"Une erreur inattendue est survenue durant la conversion: {e}", exc_info=True)
            return None, f"Échec inattendu. Erreur: {e}"

    async def execute_query(self, belief_set: FirstOrderBeliefSet, query: str) -> Tuple[Optional[bool], str]:
        logger.info(f"Exécution de la requête: '{query}'")
        try:
            # L'objet Java est déjà dans le BeliefSet, pas besoin de le recréer
            if not belief_set.java_object:
                return None, "L'objet Java BeliefSet n'est pas disponible."
            
            entails = self._tweety_bridge.query(belief_set.java_object, query)
            result_str = "ENTAILED" if entails else "NOT_ENTAILED"
            return entails, result_str
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête '{query}': {e}"
            logger.error(error_msg, exc_info=True)
            return None, f"QUERY_ERROR: {e}"

    async def is_consistent(self, belief_set: FirstOrderBeliefSet) -> Tuple[bool, str]:
        logger.info("Vérification de la consistance de l'ensemble de croyances.")
        try:
            if not belief_set.java_object:
                return False, "L'objet Java BeliefSet n'est pas disponible."
            
            is_consistent, details = self._tweety_bridge.check_consistency(belief_set.java_object)
            return is_consistent, details
        except Exception as e:
            error_msg = f"Erreur lors de la vérification de la consistance: {e}"
            logger.error(error_msg, exc_info=True)
            return False, f"CONSISTENCY_ERROR: {e}"

    # ==============================================================================
    # MÉTHODES ABSTRAITES HÉRITÉES (Implémentations minimales pour la compatibilité)
    # ------------------------------------------------------------------------------
    # L'architecture tool-based de cet agent rend plusieurs méthodes héritées
    # non directement applicables. Des implémentations minimales sont fournies
    # pour satisfaire le contrat de la classe de base abstraite.
    # ==============================================================================

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Retourne les capacités spécifiques de cet agent."""
        return {
            "description": "Agent spécialisé dans la conversion de texte en logique du premier ordre (FOL) via des appels d'outils orchestrés par un LLM.",
            "logic_type": "FOL",
            "supported_operations": ["text_to_belief_set", "is_consistent", "execute_query"],
            "tool_plugin": "BeliefBuilderPlugin"
        }

    async def generate_queries(self, text: str, belief_set, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Non applicable pour cet agent, qui ne génère pas de requêtes proactivement."""
        logger.warning(f"La méthode 'generate_queries' n'est pas implémentée pour {self.name}.")
        return []

    async def interpret_results(self, text: str, belief_set, queries: List[str], results: List[Tuple[Optional[bool], str]], context: Optional[Dict[str, Any]] = None) -> str:
        """Non applicable pour cet agent, qui retourne des résultats bruts."""
        logger.warning(f"La méthode 'interpret_results' n'est pas implémentée pour {self.name}.")
        return "L'interprétation des résultats n'est pas supportée."
        
    def validate_formula(self, formula: str) -> bool:
        """Valide une formule en utilisant le pont Tweety."""
        logger.debug(f"Validation de la formule : '{formula}'")
        return self._tweety_bridge.validate_formula(formula)

    async def validate_argument(self, premises: List[str], conclusion: str, **kwargs) -> bool:
        """Non applicable pour cet agent."""
        logger.warning(f"La méthode 'validate_argument' n'est pas implémentée pour {self.name}.")
        return False

    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]):
        """Recrée un BeliefSet à partir de son contenu textuel."""
        content = belief_set_data.get("content")
        if not content:
            raise ValueError("Les données du BeliefSet ne contiennent pas de 'content'.")
        
        java_obj = self._tweety_bridge.create_belief_set_from_string(content)
        return FirstOrderBeliefSet(content=content, java_object=java_obj)

    async def get_response(self, chat_history: ChatHistory, **kwargs) -> Any:
        logger.warning(f"La méthode 'get_response' n'est pas l'interaction standard pour {self.name}.")
        yield []

    async def invoke_single(self, chat_history: ChatHistory, **kwargs) -> ChatMessageContent:
        last_user_message = next((m.content for m in reversed(chat_history) if m.role == "user"), None)
        if not last_user_message or not isinstance(last_user_message, str):
            return ChatMessageContent(role="assistant", content=json.dumps({"error": "Veuillez fournir une instruction en texte."}))
        
        belief_set, status = await self.text_to_belief_set(last_user_message)
        response_content = belief_set.to_dict() if belief_set else {"error": status}
        return ChatMessageContent(role="assistant", content=json.dumps(response_content, indent=2), name=self.name)