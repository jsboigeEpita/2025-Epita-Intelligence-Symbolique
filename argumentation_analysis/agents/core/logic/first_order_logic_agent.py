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
from typing import Dict, List, Optional, Any, Tuple, AsyncGenerator
from abc import abstractmethod

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents import ChatMessageContent, AuthorRole
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
        self._formulas: List[str] = []

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
        name="add_constant",
    )
    def add_constant(self, constant_name: str, sort_name: str):
        """Ajoute une constante à un sort."""
        norm_const = self._normalize(constant_name)
        norm_sort = self._normalize(sort_name)
        if norm_sort not in self._sorts:
            self.add_sort(norm_sort) # Tolérance : on crée le sort s'il manque
        if norm_const not in self._sorts[norm_sort]:
            self._sorts[norm_sort].append(norm_const)
        return f"Constante '{norm_const}' ajoutée au sort '{norm_sort}'."

    @kernel_function(
        description="Déclare un nouveau prédicat (une propriété ou une relation, comme 'EstMortel').",
        name="add_predicate",
    )
    def add_predicate(self, predicate_name: str, argument_sorts: List[str]):
        """Ajoute une déclaration de type de prédicat."""
        norm_pred = self._normalize(predicate_name)
        norm_args = [self._normalize(s) for s in argument_sorts]
        self._predicates[norm_pred] = norm_args
        return f"Prédicat '{norm_pred}' déclaré avec les arguments {norm_args}."

    @kernel_function(
        description="Ajoute une formule logique (un fait ou une règle) à la base de connaissances.",
        name="add_formula",
    )
    def add_formula(self, formula: str):
        """Ajoute une formule, en normalisant la syntaxe des quantificateurs."""
        
        # Normalisation des symboles de quantificateurs
        normalized_formula = formula.replace("∀", "forall ").replace("∃", "exists ")
        # Remplacement des opérateurs logiques communs par la syntaxe attendue par Tweety
        normalized_formula = normalized_formula.replace("→", "=>").replace("∧", "&&").replace("∨", "||").replace("¬", "!").replace("↔", "<=>")

        # Normalisation de la syntaxe du quantificateur (ex: "forall x(...)" -> "forall X:(...)")
        # Cette regex recherche "forall" ou "exists", suivi d'un espace, d'un nom de variable,
        # d'un espace optionnel, et d'une parenthèse ouvrante.
        # Elle remplace cela par "forall/exists", la variable en MAJUSCULE, deux-points, et la parenthèse.
        def replacer(match):
            keyword = match.group(1)
            variable_lower = match.group(2)
            variable_upper = variable_lower.upper()
            inner_formula = match.group(3)
            
            # Remplace toutes les occurrences de la variable (insensible à la casse) par sa version majuscule
            # à l'intérieur de l'expression. \b est une ancre de mot pour éviter de remplacer
            # des parties de noms plus longs.
            inner_formula_replaced = re.sub(r'\b' + re.escape(variable_lower) + r'\b', variable_upper, inner_formula, flags=re.IGNORECASE)

            # Nouvelle stratégie : les variables sont toujours quantifiées sur un sort générique "thing".
            # La propriété (ex: "être un homme") est gérée par un prédicat unaire (homme(X)).
            # Le prompt système guide maintenant le LLM vers cette approche.
            sort_name = "thing"

            # La syntaxe est `forall X:thing ( inner_formula )`
            return f"{keyword} {variable_upper}:{sort_name} ({inner_formula_replaced})"

        # La regex capture maintenant le contenu entre les parenthèses pour le traitement
        # Exemple: forall x (P(x) -> Q(x))
        # group(1): forall
        # group(2): x
        # group(3): P(x) -> Q(x)
        # Note: on enlève la parenthèse fermante de la capture globale
        normalized_formula = re.sub(r'(forall|exists)\s+([a-zA-Z][a-zA-Z0-9]*)\s*\((.*)\)', replacer, normalized_formula, flags=re.DOTALL)

        self._formulas.append(normalized_formula)
        # self.logger.debug(f"Formule ajoutée après normalisation: '{normalized_formula}' (Original: '{formula}')")
        return f"Formule '{normalized_formula}' ajoutée."

    def build_fologic_string(self) -> str:
        """Construit la chaîne .fologic finale à partir de l'état accumulé."""
        lines = []
        # 1. Déclarer TOUS les sorts, qu'ils aient des constantes ou non.
        # La syntaxe pour un sort sans constante est 'sort_name = {}'.
        for sort, constants in self._sorts.items():
            lines.append(f"{sort} = {{{', '.join(constants)}}}")

        # 2. Construire les déclarations de types de prédicats
        for pred, args in self._predicates.items():
            lines.append(f"type({pred}({', '.join(args)}))")
            
        # 3. Ajouter les formules
        lines.extend(self._formulas)
        return "\n".join(lines)


# Prompt Système pour l'agent FOL
SYSTEM_PROMPT_FOL = """Vous êtes un assistant d'analyse logique. Votre tâche est de décomposer un texte en ses composants logiques fondamentaux en utilisant les outils fournis.

**Philosophie Clé : Prédicats Unaires au lieu de Sorts Complexes**
Pour représenter une propriété (comme "être un homme"), utilisez un PRÉDICAT UNAIRE (ex: `homme(X)`), pas un sort. N'utilisez les sorts que pour les catégories fondamentales et distinctes (ex: `personne`, `objet`, `lieu`). Par défaut, un sort universel `thing` existe.

**Exemple d'Analyse Correcte pour "Tous les hommes sont mortels. Socrate est un homme."**
1.  `add_sort("thing")` (ou un autre sort de base comme "personne")
2.  `add_constant("Socrate", "thing")`
3.  `add_predicate("homme", ["thing"])` <-- 'homme' est un prédicat
4.  `add_predicate("EstMortel", ["thing"])`
5.  `add_formula("forall X (homme(X) => EstMortel(X))")`
6.  `add_formula("homme(Socrate)")`

**Règles d'Appel des Outils :**
1.  **Déclarez les sorts fondamentaux** (comme `thing`) s'ils ne sont pas implicites.
2.  **Déclarez les constantes** en les associant à un sort.
3.  **Déclarez TOUS les prédicats** avant de les utiliser, y compris ceux utilisés pour les propriétés comme `homme`.
4.  **Ajoutez les formules** en dernier. Assurez-vous que chaque prédicat est déclaré.
5.  **Soyez exhaustif.**
6.  **Ne répondez rien d'autre.** Votre seule sortie doit être les appels aux outils.
"""

# Anciens prompts conservés pour les autres fonctions de l'agent

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

    def __init__(self, kernel: Kernel, tweety_bridge: "TweetyBridge", agent_name: str = "FirstOrderLogicAgent", service_id: Optional[str] = None, use_serialization: bool = True):
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
        
        self._tweety_bridge = tweety_bridge
        # Le plugin qui contient nos outils. Il sera instancié ici.
        self._builder_plugin = BeliefSetBuilderPlugin()
        self.logger.info(f"Agent {self.name} initialisé. Stratégie: Appel d'Outils. Sérialisation: {self._use_serialization}")

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
        chat = ChatHistory(system_message=SYSTEM_PROMPT_FOL)
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
            
            # NOUVELLE STRATÉGIE : Construction programmatique de l'objet BeliefSet
            # On contourne complètement le parsing de la chaîne .fologic
            self.logger.info("Construction programmatique du BeliefSet à partir des données du plugin...")
            belief_set_obj = self.tweety_bridge.create_belief_set_programmatically(self._builder_plugin.__dict__)

            if not belief_set_obj:
                return None, "La création programmatique du BeliefSet a échoué."

            # Pour la sérialisation et le logging, nous avons toujours besoin d'une représentation textuelle.
            # On utilise la méthode toString() de l'objet Java, qui est fiable.
            belief_set_content_str = str(belief_set_obj.toString())
            self.logger.debug(f"Représentation textuelle du BeliefSet construit:\n{belief_set_content_str}")

            # Créer l'objet BeliefSet final
            if self._use_serialization:
                # On stocke la représentation textuelle fiable pour la recréation JIT.
                final_belief_set = FirstOrderBeliefSet(content=belief_set_content_str, java_object=None)
            else:
                # On stocke à la fois la représentation textuelle et l'objet Java.
                final_belief_set = FirstOrderBeliefSet(content=belief_set_content_str, java_object=belief_set_obj)

            self.logger.info("Conversion via la stratégie d'appel d'outils réussie.")
            return final_belief_set, "Conversion réussie."

        except Exception as e:
            last_error = str(e)
            self.logger.error(f"Une erreur est survenue durant le processus de conversion par outils: {last_error}", exc_info=True)
            return None, f"Échec final. Erreur: {last_error}"

    # Les fonctions _extract_fologic_block et _sanitize_fologic_string ne sont plus nécessaires
    # car la génération de la chaîne est maintenant déterministe et contrôlée en interne.
    
    def _extract_json_block(self, text: str) -> str:
        """Extracts a JSON block from a markdown-formatted string."""
        match = re.search(r"```(json)?\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(2).strip()
        return text # Assume it's raw JSON if no block is found
        
        
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
            
        if not belief_set.content:
            self.logger.error("Reconstruction JIT impossible: pas de contenu pour recréer l'objet BeliefSet.")
            return None

        self.logger.info("Reconstruction JIT de l'objet BeliefSet Java à partir de la syntaxe native...")
        try:
            # Le contenu est maintenant la chaîne de syntaxe native
            java_object = self.tweety_bridge.create_belief_set_from_string(belief_set.content)
            
            if not java_object:
                 raise RuntimeError("La création du BeliefSet à partir de la chaîne a retourné None.")

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