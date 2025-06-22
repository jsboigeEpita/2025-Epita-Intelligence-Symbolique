# argumentation_analysis/agents/core/logic/propositional_logic_agent.py
# Refreshing file for git tracking
"""
Définit l'agent spécialisé dans le raisonnement en logique propositionnelle (PL).

Ce module fournit la classe `PropositionalLogicAgent`, une implémentation concrète
de `BaseLogicAgent`. Son rôle est d'orchestrer le traitement de texte en langage
naturel pour le convertir en un format logique, exécuter des raisonnements et
interpréter les résultats.

L'agent s'appuie sur deux piliers :
1.  **Semantic Kernel** : Pour les tâches basées sur les LLMs, comme la traduction
    de texte en formules PL et l'interprétation des résultats. Les prompts
    dédiés à ces tâches sont définis directement dans ce module.
2.  **TweetyBridge** : Pour l'interaction avec le solveur logique sous-jacent,
    notamment pour valider la syntaxe des formules et vérifier l'inférence.
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple, AsyncGenerator

from semantic_kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.contents.chat_history import ChatHistory
from pydantic import Field

from ..abc.agent_bases import BaseLogicAgent
from .belief_set import BeliefSet, PropositionalBeliefSet
from .tweety_bridge import TweetyBridge

# Configuration du logger
logger = logging.getLogger(__name__)

# --- Prompts pour la Logique Propositionnelle (PL) ---

SYSTEM_PROMPT_PL = """Vous êtes un agent spécialisé dans l'analyse et le raisonnement en logique propositionnelle (PL).
Vous utilisez la syntaxe de TweetyProject pour représenter les formules PL.
Vos tâches principales incluent la traduction de texte en formules PL, la génération de requêtes PL pertinentes,
l'exécution de ces requêtes sur un ensemble de croyances PL, et l'interprétation des résultats obtenus.
"""

PROMPT_TEXT_TO_PL_DEFS = """
Vous êtes un expert en logique propositionnelle (PL). Votre tâche est d'identifier les propositions atomiques (faits de base) dans un texte donné.

**Format de Sortie (JSON Strict):**
Votre sortie DOIT être un objet JSON unique contenant une seule clé : `propositions`.
La valeur de `propositions` doit être une liste de chaînes de caractères, où chaque chaîne est une proposition atomique.
Les noms des propositions doivent être concis, en minuscules et en `snake_case` (ex: "is_mortal", "is_man").

**Exemple:**
Texte: "Socrate est un homme. Si un être est un homme, alors il est mortel."

**Sortie JSON attendue:**
```json
{
  "propositions": [
    "socrates_is_a_man",
    "socrates_is_mortal"
  ]
}
```

Analysez le texte suivant et extrayez uniquement les `propositions`.

{{$input}}
"""

PROMPT_TEXT_TO_PL_FORMULAS = """
Vous êtes un expert en logique propositionnelle (PL). Votre tâche est de traduire un texte en formules logiques, en utilisant un ensemble prédéfini de propositions atomiques.

**Contexte Fourni:**
1.  **Texte Original**: Le texte à traduire.
2.  **Propositions Autorisées**: Une liste JSON des propositions atomiques que vous DEVEZ utiliser.

**Votre Tâche:**
Générez un objet JSON contenant UNIQUEMENT la clé `formulas`.

**Règles Strictes:**
*   **Utilisation Exclusive**: N'utilisez QUE les `propositions` fournies. N'en inventez pas de nouvelles.
*   **Connecteurs**: Utilisez `!`, `&&`, `||`, `=>`, `<=>`.
*   **Format**: Les formules sont une liste de chaînes de caractères. N'ajoutez PAS de point-virgule à la fin.

**Exemple:**
Texte Original: "Socrate est un homme. Si un être est un homme, alors il est mortel."
Propositions Autorisées:
```json
{
  "propositions": [
    "socrates_is_a_man",
    "socrates_is_mortal"
  ]
}
```

**Sortie JSON attendue:**
```json
{
  "formulas": [
    "socrates_is_a_man",
    "socrates_is_a_man => socrates_is_mortal"
  ]
}
```

Maintenant, traduisez le texte suivant en utilisant les propositions fournies.

**Texte Original:**
{{$input}}

**Propositions Autorisées:**
{{$definitions}}
"""

PROMPT_GEN_PL_QUERIES_IDEAS = """
Vous êtes un expert en logique propositionnelle. Votre tâche est de générer des "idées" de requêtes pertinentes pour interroger un ensemble de croyances (belief set) donné.

**Contexte Fourni:**
1.  **Texte Original**: Le texte qui motive l'analyse.
2.  **Ensemble de Croyances (Knowledge Base)**: Une liste de propositions atomiques valides.

**Votre Tâche:**
Générez un objet JSON contenant UNIQUEMENT la clé `query_ideas`.
La valeur de `query_ideas` doit être une liste de chaînes de caractères, où chaque chaîne est une proposition que vous jugez pertinent de vérifier.

**Règles Strictes:**
*   **Utilisation Exclusive**: N'utilisez QUE les propositions qui existent dans l'ensemble de croyances fourni. N'en inventez pas.
*   **Pertinence**: Les idées de requêtes doivent être pertinentes par rapport au texte original et chercher à vérifier des conclusions ou des faits intéressants.
*   **Format de Sortie**: Votre sortie DOIT être un objet JSON valide, sans aucun texte ou explication supplémentaire.

**Exemple:**
Texte Original: "Socrate est un homme. Si un être est un homme, alors il est mortel."
Ensemble de Croyances:
```json
{
  "propositions": [
    "socrates_is_a_man",
    "socrates_is_mortal"
  ],
  "formulas": [
    "socrates_is_a_man",
    "socrates_is_a_man => socrates_is_mortal"
  ]
}
```

**Sortie JSON attendue:**
```json
{
  "query_ideas": [
    "socrates_is_mortal",
    "socrates_is_a_man"
  ]
}
```

Maintenant, analysez le contexte suivant et générez les idées de requêtes.

**Texte Original:**
{{$input}}

**Ensemble de Croyances:**
{{$belief_set}}
"""

PROMPT_INTERPRET_PL = """
Vous êtes un expert en logique propositionnelle. Votre tâche est d'interpréter les résultats de requêtes et d'expliquer leur signification dans le contexte du texte source.

Voici le texte source:
{{$input}}

Voici l'ensemble de croyances en logique propositionnelle:
{{$belief_set}}

Voici les requêtes qui ont été exécutées:
{{$queries}}

Voici les résultats de ces requêtes:
{{$tweety_result}}

Interprétez ces résultats et expliquez leur signification. Pour chaque requête:
1. Expliquez ce que la requête cherchait à vérifier.
2. Indiquez si la requête a été prouvée (True) ou non (False).
3. Expliquez ce que cela signifie dans le contexte du texte source.

Fournissez ensuite une conclusion générale. Votre réponse doit être claire et accessible.
"""


class PropositionalLogicAgent(BaseLogicAgent):
    """
    Agent spécialiste de l'analyse en logique propositionnelle (PL).

    Cet agent transforme un texte en un `PropositionalBeliefSet` (ensemble de
    croyances) formalisé en PL. Il orchestre l'utilisation de fonctions sémantiques
    (via LLM) pour l'extraction de propositions et de formules, et s'appuie sur
    `TweetyBridge` pour valider la syntaxe et exécuter des requêtes logiques.

    Le workflow typique de l'agent est le suivant :
    1.  `text_to_belief_set` : Convertit un texte en langage naturel en un
        `PropositionalBeliefSet` structuré et validé.
    2.  `generate_queries` : Propose une liste de requêtes pertinentes à partir
        du `BeliefSet` et du contexte textuel initial.
    3.  `execute_query` : Exécute une requête logique sur le `BeliefSet` en utilisant
        le moteur logique de TweetyProject.
    4.  `interpret_results` : Fait appel au LLM pour traduire les résultats logiques
        bruts en une explication compréhensible en langage naturel.

    Attributes:
        service (Optional[ChatCompletionClientBase]): Le client de complétion de chat
            fourni par le Kernel. Inutilisé directement, les appels passent par le Kernel.
        settings (Optional[Any]): Les paramètres d'exécution pour les fonctions
            sémantiques, récupérés depuis le Kernel.
        _tweety_bridge (TweetyBridge): Instance privée du pont vers la bibliothèque
            logique Java TweetyProject.
    """
    service: Optional[ChatCompletionClientBase] = Field(default=None, exclude=True)
    settings: Optional[Any] = Field(default=None, exclude=True)

    def __init__(self, kernel: Kernel, agent_name: str = "PropositionalLogicAgent", system_prompt: Optional[str] = None, service_id: Optional[str] = None):
        """
        Initialise l'agent de logique propositionnelle.

        Args:
            kernel (Kernel): L'instance du kernel Semantic Kernel.
            agent_name (str, optional): Nom de l'agent.
            system_prompt (Optional[str], optional): Prompt système à utiliser.
                Si `None`, `SYSTEM_PROMPT_PL` est utilisé.
            service_id (Optional[str], optional): ID du service LLM à utiliser
                pour les fonctions sémantiques.
        """
        actual_system_prompt = system_prompt or SYSTEM_PROMPT_PL
        super().__init__(kernel, agent_name=agent_name, logic_type_name="PL", system_prompt=actual_system_prompt)
        self._llm_service_id = service_id
        self._tweety_bridge = TweetyBridge()
        self.logger.info(f"TweetyBridge initialisé pour {self.name}. JVM prête: {self._tweety_bridge.is_jvm_ready()}")
        if not self._tweety_bridge.is_jvm_ready():
            self.logger.error("La JVM n'est pas prête. Les fonctionnalités logiques sont compromises.")

    def get_agent_capabilities(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "logic_type": self.logic_type,
            "description": "Agent capable d'analyser du texte en utilisant la logique propositionnelle (PL).",
            "methods": {
                "text_to_belief_set": "Convertit un texte en un ensemble de croyances PL.",
                "generate_queries": "Génère des requêtes PL pertinentes à partir d'un texte et d'un ensemble de croyances.",
                "execute_query": "Exécute une requête PL sur un ensemble de croyances.",
                "interpret_results": "Interprète les résultats d'une ou plusieurs requêtes PL.",
                "validate_formula": "Valide la syntaxe d'une formule PL."
            }
        }

    def setup_agent_components(self, llm_service_id: str) -> None:
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants sémantiques pour {self.name}...")

        if not self._tweety_bridge.is_jvm_ready():
            self.logger.error(f"La JVM pour TweetyBridge de {self.name} n'est pas prête.")
            return

        prompt_execution_settings = None
        if self._llm_service_id:
            try:
                prompt_execution_settings = self._kernel.get_prompt_execution_settings_from_service_id(self._llm_service_id)
                self.logger.debug(f"Settings LLM récupérés pour {self.name}.")
            except Exception as e:
                self.logger.warning(f"Impossible de récupérer les settings LLM pour {self.name}: {e}")

        semantic_functions = [
            ("TextToPLDefs", PROMPT_TEXT_TO_PL_DEFS, "Extrait les propositions atomiques d'un texte."),
            ("TextToPLFormulas", PROMPT_TEXT_TO_PL_FORMULAS, "Génère les formules PL à partir d'un texte et de propositions."),
            ("GeneratePLQueryIdeas", PROMPT_GEN_PL_QUERIES_IDEAS, "Génère des idées de requêtes PL au format JSON."),
            ("InterpretPLResults", PROMPT_INTERPRET_PL, "Interprète les résultats de requêtes PL.")
        ]

        for func_name, prompt, description in semantic_functions:
            try:
                self._kernel.add_function(
                    prompt=prompt,
                    plugin_name=self.name,
                    function_name=func_name,
                    description=description,
                    prompt_execution_settings=prompt_execution_settings
                )
                self.logger.info(f"Fonction sémantique {self.name}.{func_name} ajoutée.")
            except Exception as e:
                self.logger.error(f"Erreur lors de l'ajout de la fonction sémantique {self.name}.{func_name}: {e}", exc_info=True)
        
        self.logger.info(f"Composants pour {self.name} configurés.")
    
    def _extract_json_block(self, text: str) -> str:
        """Extrait le premier bloc JSON valide de la réponse du LLM."""
        match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            return match.group(1)
        
        start_index = text.find('{')
        end_index = text.rfind('}')
        if start_index != -1 and end_index != -1 and end_index > start_index:
            return text[start_index:end_index + 1]
        
        self.logger.warning("Impossible d'isoler un bloc JSON. Tentative de parsing de la chaîne complète.")
        return text

    def _filter_formulas(self, formulas: List[str], declared_propositions: set) -> List[str]:
        """Filtre les formules pour ne garder que celles qui utilisent des propositions déclarées."""
        valid_formulas = []
        # Regex pour extraire les identifiants qui ressemblent à des propositions
        proposition_pattern = re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b')
        
        for formula in formulas:
            # Extrait tous les identifiants potentiels de la formule
            used_propositions = set(proposition_pattern.findall(formula))
            
            # Vérifie si tous les identifiants utilisés sont dans l'ensemble des propositions déclarées
            if used_propositions.issubset(declared_propositions):
                valid_formulas.append(formula)
            else:
                unknown_props = used_propositions - declared_propositions
                self.logger.warning(
                    f"Formule rejetée: '{formula}'. "
                    f"Contient des propositions non déclarées: {unknown_props}"
                )
        self.logger.info(f"{len(valid_formulas)}/{len(formulas)} formules conservées après filtrage.")
        return valid_formulas

    async def _invoke_llm_for_json(self, kernel: Kernel, plugin_name: str, function_name: str, arguments: Dict[str, Any],
                                 expected_keys: List[str], log_tag: str, max_retries: int) -> Tuple[Optional[Dict[str, Any]], str]:
        """Méthode helper pour invoquer une fonction sémantique et parser une réponse JSON."""
        for attempt in range(max_retries):
            self.logger.debug(f"[{log_tag}] Tentative {attempt + 1}/{max_retries} pour {plugin_name}.{function_name}...")
            try:
                result = await kernel.invoke(
                    plugin_name=plugin_name,
                    function_name=function_name,
                    arguments=KernelArguments(**arguments)
                )
                response_text = str(result)
                json_block = self._extract_json_block(response_text)
                data = json.loads(json_block)

                if all(key in data for key in expected_keys):
                    self.logger.info(f"[{log_tag}] Succès de l'invocation et du parsing JSON.")
                    return data, ""
                else:
                    error_msg = f"Les clés attendues {expected_keys} ne sont pas dans la réponse: {list(data.keys())}"
                    self.logger.warning(f"[{log_tag}] {error_msg}")

            except json.JSONDecodeError as e:
                error_msg = f"Erreur de décodage JSON: {e}. Réponse: {response_text}"
                self.logger.error(f"[{log_tag}] {error_msg}")
            except Exception as e:
                error_msg = f"Erreur inattendue lors de l'invocation LLM: {e}"
                self.logger.error(f"[{log_tag}] {error_msg}", exc_info=True)
        
        final_error = f"[{log_tag}] Échec de l'obtention d'une réponse JSON valide après {max_retries} tentatives."
        self.logger.error(final_error)
        return None, final_error

    async def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[BeliefSet], str]:
        """
        Convertit un texte brut en un `PropositionalBeliefSet` structuré et validé.

        Ce processus complexe s'appuie sur le LLM et `TweetyBridge` :
        1.  **Génération des Propositions** : Le LLM identifie et extrait les
            propositions atomiques candidates à partir du texte.
        2.  **Génération des Formules** : Le LLM traduit le texte en formules
            logiques en se basant sur les propositions précédemment identifiées.
        3.  **Filtrage Rigoureux** : Les formules qui utiliseraient des propositions
            non déclarées à l'étape 1 sont systématiquement rejetées pour garantir
            la cohérence.
        4.  **Validation Syntaxique** : L'ensemble de croyances final est soumis à
            `TweetyBridge` pour une validation syntaxique complète.

        Args:
            text (str): Le texte en langage naturel à convertir.
            context (Optional[Dict[str, Any]]): Contexte additionnel (non utilisé
                actuellement).

        Returns:
            Tuple[Optional[BeliefSet], str]: Un tuple contenant le `BeliefSet` créé
            (ou `None` en cas d'échec) et un message de statut détaillé.
        """
        self.logger.info(f"Début de la conversion de texte en BeliefSet PL pour '{text[:100]}...'")
        max_retries = 3

        # Étape 1: Génération des Propositions
        defs_json, error_msg = await self._invoke_llm_for_json(
            self._kernel, self.name, "TextToPLDefs", {"input": text},
            ["propositions"], "prop-gen", max_retries
        )
        if not defs_json: return None, error_msg

        # Étape 2: Génération des Formules
        formulas_json, error_msg = await self._invoke_llm_for_json(
            self._kernel, self.name, "TextToPLFormulas",
            {"input": text, "definitions": json.dumps(defs_json, indent=2)},
            ["formulas"], "formula-gen", max_retries
        )
        if not formulas_json: return None, error_msg

        # Étape 3: Filtrage et Validation
        declared_propositions = set(defs_json.get("propositions", []))
        all_formulas = formulas_json.get("formulas", [])
        valid_formulas = self._filter_formulas(all_formulas, declared_propositions)
        if not valid_formulas:
            return None, "Aucune formule valide n'a pu être générée ou conservée après filtrage."

        belief_set_content = "\n".join(valid_formulas)
        is_valid, validation_msg = self._tweety_bridge.validate_belief_set(belief_set_content)
        if not is_valid:
            self.logger.error(f"Ensemble de croyances final invalide: {validation_msg}\nContenu:\n{belief_set_content}")
            return None, f"Ensemble de croyances invalide: {validation_msg}"

        belief_set = PropositionalBeliefSet(belief_set_content, propositions=list(declared_propositions))
        self.logger.info("Conversion et validation du BeliefSet réussies.")
        return belief_set, "Conversion réussie."

    async def generate_queries(self, text: str, belief_set: BeliefSet, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Génère une liste de requêtes PL pertinentes pour un `BeliefSet` donné.

        Cette méthode utilise le LLM pour suggérer des "idées" de requêtes basées
        sur le texte original et l'ensemble de croyances. Elle filtre ensuite ces
        suggestions pour ne conserver que celles qui sont syntaxiquement valides
        et qui correspondent à des propositions déclarées dans le `BeliefSet`.

        Args:
            text (str): Le texte original, utilisé pour fournir un contexte au LLM.
            belief_set (BeliefSet): L'ensemble de croyances sur lequel les
                requêtes seront basées.
            context (Optional[Dict[str, Any]]): Contexte additionnel (non utilisé).

        Returns:
            List[str]: Une liste de requêtes PL (chaînes de caractères) validées et
            prêtes à être exécutées par `execute_query`. Retourne une liste vide
            en cas d'échec ou si aucune idée pertinente n'est trouvée.
        """
        self.logger.info(f"Génération de requêtes PL via le modèle de requête pour '{text[:100]}...'")
        
        if not isinstance(belief_set, PropositionalBeliefSet) or not belief_set.propositions:
            self.logger.error("Le BeliefSet n'est pas du bon type ou ne contient pas de propositions déclarées.")
            return []

        try:
            # Le "belief_set" pour le prompt contient les propositions et les formules
            belief_set_for_prompt = json.dumps({
                "propositions": belief_set.propositions,
                "formulas": belief_set.content.splitlines()
            }, indent=2)

            arguments = KernelArguments(input=text, belief_set=belief_set_for_prompt)
            result = await self._kernel.invoke(
                plugin_name=self.name,
                function_name="GeneratePLQueryIdeas",
                arguments=arguments
            )
            
            response_text = str(result)
            json_block = self._extract_json_block(response_text)
            query_ideas_data = json.loads(json_block)
            query_ideas = query_ideas_data.get("query_ideas", [])

            if not query_ideas:
                self.logger.warning("Le LLM n'a généré aucune idée de requête.")
                return []

            self.logger.info(f"{len(query_ideas)} idées de requêtes reçues du LLM.")
            self.logger.debug(f"Idées de requêtes brutes: {query_ideas}")

            valid_queries = []
            declared_propositions = set(belief_set.propositions)
            for idea in query_ideas:
                if not isinstance(idea, str):
                    self.logger.warning(f"Idée de requête rejetée: n'est pas une chaîne de caractères -> {idea}")
                    continue
                
                # Validation: l'idée est-elle une proposition déclarée ?
                if idea in declared_propositions:
                    # En PL, la requête est juste la proposition elle-même.
                    # On valide sa syntaxe pour être sûr.
                    if self.validate_formula(idea):
                        self.logger.info(f"Idée validée et requête assemblée: {idea}")
                        valid_queries.append(idea)
                    else:
                        self.logger.warning(f"Idée rejetée: La requête assemblée '{idea}' a échoué la validation syntaxique.")
                else:
                    self.logger.warning(f"Idée de requête rejetée: Proposition inconnue '{idea}'.")

            self.logger.info(f"Génération terminée. {len(valid_queries)}/{len(query_ideas)} requêtes valides assemblées.")
            return valid_queries

        except json.JSONDecodeError as e:
            self.logger.error(f"Erreur de décodage JSON lors de la génération des requêtes: {e}\nRéponse du LLM: {response_text}")
            return []
        except Exception as e:
            self.logger.error(f"Erreur inattendue lors de la génération des requêtes: {e}", exc_info=True)
            return []
    
    def execute_query(self, belief_set: BeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une seule requête PL sur un `BeliefSet` via `TweetyBridge`.

        Cette méthode valide d'abord la syntaxe de la requête avant de la soumettre
        au moteur logique de Tweety.

        Args:
            belief_set (BeliefSet): L'ensemble de croyances sur lequel la requête
                doit être exécutée.
            query (str): La formule PL à vérifier (par exemple, "socrates_is_mortal").

        Returns:
            Tuple[Optional[bool], str]: Un tuple contenant :
            - Le résultat booléen (`True` si la requête est prouvée, `False` sinon,
              `None` en cas d'erreur).
            - Le message de sortie brut de Tweety, utile pour le débogage.
        """
        self.logger.info(f"Exécution de la requête PL: '{query}'...")
        
        try:
            bs_str = belief_set.content
            
            is_valid, validation_message = self._tweety_bridge.validate_formula(formula_string=query)
            if not is_valid:
                msg = f"Requête invalide: {query}. Raison: {validation_message}"
                self.logger.error(msg)
                return None, f"FUNC_ERROR: {msg}"

            is_entailed, raw_output_str = self._tweety_bridge.execute_pl_query(
                belief_set_content=bs_str,
                query_string=query
            )

            if "FUNC_ERROR:" in raw_output_str:
                self.logger.error(f"Erreur de TweetyBridge pour la requête '{query}': {raw_output_str}")
                return None, raw_output_str
            
            self.logger.info(f"Résultat de l'exécution pour '{query}': {is_entailed}, Output brut: '{raw_output_str}'")
            return is_entailed, raw_output_str
        
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête PL '{query}': {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return None, f"FUNC_ERROR: {error_msg}"

    async def interpret_results(self, text: str, belief_set: BeliefSet,
                                 queries: List[str], results: List[Tuple[Optional[bool], str]],
                                 context: Optional[Dict[str, Any]] = None) -> str:
        """
        Traduit les résultats bruts d'une ou plusieurs requêtes en une explication en langage naturel.

        Utilise un prompt sémantique pour fournir au LLM le contexte complet
        (texte original, ensemble de croyances, requêtes, résultats bruts) afin qu'il
        génère une explication cohérente.

        Args:
            text (str): Le texte original.
            belief_set (BeliefSet): L'ensemble de croyances utilisé.
            queries (List[str]): La liste des requêtes qui ont été exécutées.
            results (List[Tuple[Optional[bool], str]]): La liste des résultats correspondants.
            context (Optional[Dict[str, Any]]): Contexte additionnel (non utilisé).

        Returns:
            str: L'explication générée par le LLM.
        """
        self.logger.info("Interprétation des résultats des requêtes PL...")
        
        try:
            queries_str = "\n".join(queries)
            results_messages_str = "\n".join([f"Query: {q} -> Result: {r[0]} ({r[1]})" for q, r in zip(queries, results)])

            arguments = KernelArguments(
                input=text,
                belief_set=belief_set.content,
                queries=queries_str,
                tweety_result=results_messages_str
            )
            
            result = await self._kernel.invoke(
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
        self.logger.debug(f"Validation de la formule PL: '{formula}'")
        try:
            is_valid, message = self._tweety_bridge.validate_formula(formula_string=formula)
            if not is_valid:
                self.logger.warning(f"Formule PL invalide: '{formula}'. Message: {message}")
            return is_valid
        except Exception as e:
            self.logger.error(f"Erreur lors de la validation de la formule PL '{formula}': {e}", exc_info=True)
            return False

    def is_consistent(self, belief_set: BeliefSet) -> tuple[bool, str]:
        self.logger.debug("Vérification de la cohérence de l'ensemble de croyances PL.")
        try:
            belief_set_content = belief_set.content
            # Correction: Appeler pl_check_consistency sur le _pl_handler du bridge.
            is_valid = self._tweety_bridge._pl_handler.pl_check_consistency(belief_set_content)
            
            if is_valid:
                details = "Belief set is consistent."
                self.logger.info(details)
            else:
                details = "Belief set is inconsistent."
                self.logger.warning(details)
            
            return is_valid, details
        except Exception as e:
            error_msg = f"Erreur inattendue lors de la vérification de la cohérence: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    async def _create_belief_set_from_data(self, data: str, context: Optional[Dict[str, Any]] = None) -> Optional[BeliefSet]:
        """
        Implémentation de la méthode abstraite pour créer un BeliefSet
        à partir de données textuelles brutes.
        """
        self.logger.debug(f"_create_belief_set_from_data appelé pour {self.name}.")
        belief_set, _ = await self.text_to_belief_set(text=data, context=context)
        return belief_set

    async def get_response(self, kernel: "Kernel", arguments: Optional["KernelArguments"] = None) -> list[ChatMessageContent]:
        """Délègue l'invocation à la méthode invoke_single."""
        self.logger.debug(f"get_response appelé, délégation à invoke_single pour {self.name}.")
        return await self.invoke_single(kernel, arguments)

    async def invoke_single(self, kernel: "Kernel", arguments: Optional["KernelArguments"] = None) -> list[ChatMessageContent]:
        """
        Gère l'invocation de l'agent en analysant la dernière instruction du chat
        et en appelant la méthode interne appropriée.
        """
        self.logger.info(f"Invocation de {self.name} avec les arguments fournis.")
        history = arguments.get("chat_history") if arguments else None
        if not history or len(history) == 0:
            error_msg = "L'historique du chat est vide, impossible de continuer."
            self.logger.error(error_msg)
            return [ChatMessageContent(role="assistant", content=f'{{"error": "{error_msg}"}}', name=self.name)]

        last_user_message = history[-1].content
        self.logger.debug(f"Analyse de la dernière instruction: {last_user_message[:200]}...")

        # Analyser la tâche demandée (simplifié)
        if "belief set" in last_user_message.lower():
            task = "text_to_belief_set"
            self.logger.info("Tâche détectée: text_to_belief_set")
            source_text = history[0].content if len(history) > 1 else ""
            belief_set, message = await self.text_to_belief_set(source_text)
            if belief_set:
                response_content = json.dumps(belief_set.to_dict(), indent=2)
            else:
                response_content = f'{{"error": "Échec de la création du belief set", "details": "{message}"}}'
        
        elif "generate queries" in last_user_message.lower():
            task = "generate_queries"
            self.logger.info("Tâche détectée: generate_queries")
            source_text = history[0].content
            belief_set, _ = await self.text_to_belief_set(source_text)
            if belief_set:
                queries = await self.generate_queries(source_text, belief_set)
                response_content = json.dumps({"generated_queries": queries})
            else:
                response_content = f'{{"error": "Impossible de générer les requêtes car le belief set n_a pas pu être créé."}}'
        
        elif "traduire le texte" in last_user_message.lower():
            task = "text_to_belief_set"
            self.logger.info("Tâche détectée: text_to_belief_set (via 'traduire le texte')")
            source_text = history[0].content if len(history) > 1 else ""
            belief_set, message = await self.text_to_belief_set(source_text)
            if belief_set:
                response_content = json.dumps(belief_set.to_dict(), indent=2)
            else:
                response_content = f'{{"error": "Échec de la création du belief set", "details": "{message}"}}'

        elif "exécuter des requêtes" in last_user_message.lower():
            task = "execute_query"
            self.logger.info("Tâche détectée: execute_query (via 'exécuter des requêtes')")
            source_text = history[0].content if len(history) > 1 else ""
            belief_set, message = await self.text_to_belief_set(source_text)
            if belief_set:
                is_consistent, details = self.is_consistent(belief_set)
                response_content = json.dumps({
                    "task": "check_consistency",
                    "is_consistent": is_consistent,
                    "details": details
                }, indent=2)
            else:
                response_content = f'{{"error": "Impossible d\'exécuter la requête car le belief set n\'a pas pu être créé.", "details": "{message}"}}'

        else:
            self.logger.warning(f"Aucune tâche spécifique reconnue dans la dernière instruction pour {self.name}.")
            response_content = f'{{"error": "Tâche non reconnue pour {self.name}", "instruction": "{last_user_message}"}}'
            task = "unknown"

        self.logger.info(f"Tâche '{task}' terminée. Préparation de la réponse.")
        
        response_message = ChatMessageContent(
            role="assistant",
            content=response_content,
            name=self.name,
            metadata={'task_name': task}
        )
        return [response_message]
def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> "BeliefSet":
    """
    Crée une instance de `BeliefSet` à partir d'un dictionnaire de données.
    """
    # Pour PropositionalLogicAgent, le 'content' est une chaîne, et 'propositions' est une liste
    return PropositionalBeliefSet(
        content=belief_set_data.get("content", ""),
        propositions=belief_set_data.get("propositions", [])
    )

async def validate_argument(self, premises: List[str], conclusion: str) -> bool:
        """
        Valide un argument structuré (prémisses, conclusion) en utilisant la logique propositionnelle.
        """
        self.logger.info("Validation d'un argument en logique propositionnelle...")
        
        # 1. Combiner prémisses et conclusion en un seul texte pour l'extraction de propositions
        full_text = " ".join(premises) + " " + conclusion
        
        # 2. Extraire les propositions atomiques de l'ensemble du texte
        defs_json, error_msg = await self._invoke_llm_for_json(
            self._kernel, self.name, "TextToPLDefs", {"input": full_text},
            ["propositions"], "arg-val-prop-gen", 3
        )
        if not defs_json:
            self.logger.error(f"Impossible d'extraire les propositions pour l'argument: {error_msg}")
            return False
            
        declared_propositions = set(defs_json.get("propositions", []))
        
        # 3. Traduire les prémisses en un ensemble de croyances
        premises_text = " ".join(premises)
        formulas_json, error_msg = await self._invoke_llm_for_json(
            self._kernel, self.name, "TextToPLFormulas",
            {"input": premises_text, "definitions": json.dumps(defs_json, indent=2)},
            ["formulas"], "arg-val-premise-gen", 3
        )
        if not formulas_json:
            self.logger.error(f"Impossible de traduire les prémisses en formules: {error_msg}")
            return False

        premise_formulas = self._filter_formulas(formulas_json.get("formulas", []), declared_propositions)
        belief_set_content = "\n".join(premise_formulas)
        belief_set = PropositionalBeliefSet(belief_set_content, propositions=list(declared_propositions))

        # 4. Traduire la conclusion en une formule logique (la requête)
        conclusion_formulas_json, error_msg = await self._invoke_llm_for_json(
            self._kernel, self.name, "TextToPLFormulas",
            {"input": conclusion, "definitions": json.dumps(defs_json, indent=2)},
            ["formulas"], "arg-val-conclusion-gen", 3
        )
        if not conclusion_formulas_json or not conclusion_formulas_json.get("formulas"):
            self.logger.error(f"Impossible de traduire la conclusion en formule: {error_msg}")
            return False

        # Assurez-vous qu'on a au moins une formule pour la conclusion
        conclusion_formulas = self._filter_formulas(conclusion_formulas_json.get("formulas", []), declared_propositions)
        if not conclusion_formulas:
            self.logger.error("La traduction de la conclusion n'a produit aucune formule valide.")
            return False
        
        # Concaténer toutes les formules de conclusion avec '&&'
        # Cela rend la requête plus robuste si le LLM décompose la conclusion.
        query_formula = " && ".join(f"({f})" for f in conclusion_formulas)

        # 5. Exécuter la requête
        is_entailed, _ = self.execute_query(belief_set, query_formula)

        return is_entailed is True