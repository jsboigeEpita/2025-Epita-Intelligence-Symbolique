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
from semantic_kernel.functions import KernelArguments
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.contents.chat_history import ChatHistory
from pydantic import Field, PrivateAttr
from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent
from .belief_set import BeliefSet, PropositionalBeliefSet
from .tweety_bridge import TweetyBridge
from .tweety_initializer import TweetyInitializer

# Configuration du logger
logger = logging.getLogger(__name__)

# --- Prompts pour la Logique Propositionnelle (PL) ---

SYSTEM_PROMPT_PL = """
Votre Rôle: Spécialiste en logique propositionnelle utilisant Tweety. Vous devez générer et interpréter des formules logiques en respectant **STRICTEMENT** la syntaxe Tweety.

**Syntaxe Tweety PlParser Requise (BNF) :**
```bnf
FORMULASET ::== FORMULA ( "\\n" FORMULA )*
FORMULA ::== PROPOSITION | "(" FORMULA ")" | FORMULA ">>" FORMULA |
             FORMULA "||" FORMULA | FORMULA "=>" FORMULA | FORMULA "<=>" FORMULA |
             FORMULA "^^" FORMULA | "!" FORMULA | "+" | "-"
PROPOSITION is a sequence of characters excluding |,&,!,(),=,<,> and whitespace.
IMPORTANT: N'utilisez PAS l'opérateur >> (cause des erreurs). Utilisez !, ||, =>, <=>, ^^. Formules séparées par \\n dans les Belief Sets. Propositions courtes et sans espaces (ex: renewable_essential).

Fonctions Outils Disponibles:

    StateManager.*: Pour lire/écrire dans l'état (get_current_state_snapshot, add_belief_set, log_query_result, add_answer).
    PLAnalyzer.semantic_TextToPLBeliefSet(input: str): Fonction sémantique pour traduire texte en Belief Set PL.
    PLAnalyzer.semantic_GeneratePLQueries(input: str, belief_set: str): Fonction sémantique pour générer des requêtes PL.
    PLAnalyzer.semantic_InterpretPLResult(input: str, belief_set: str, queries: str, tweety_result: str): Fonction sémantique pour interpréter les résultats.
    PLAnalyzer.execute_pl_query(belief_set_content: str, query_string: str): Fonction native pour exécuter une requête PL via Tweety. Retourne le résultat formaté (ACCEPTED/REJECTED/Unknown/FUNC_ERROR). Nécessite une JVM prête.


Processus OBLIGATOIRE à chaque tour:

    CONSULTER L'ÉTAT: Appelez StateManager.get_current_state_snapshot(summarize=True).
    IDENTIFIER VOTRE TÂCHE: Lisez DERNIER message PM (ID tâche, description). Extrayez task_id.
    EXÉCUTER LA TÂCHE:
        Si Tâche = "Traduire ... en Belief Set PL":
        a.  Récupérer le texte source (arguments/texte brut) depuis l'état ou le message du PM.
        b.  Appelez PLAnalyzer.semantic_TextToPLBeliefSet(input=[Texte source]). Validez mentalement la syntaxe de la sortie (Belief Set string) selon la BNF.
        c.  Si la syntaxe semble OK, appelez StateManager.add_belief_set(logic_type="Propositional", content="[Belief Set string généré]"). Notez bs_id. Si l'appel retourne FUNC_ERROR:, signalez l'erreur.
        d.  Préparez réponse texte indiquant succès et bs_id (ou l'erreur).
        e.  Appelez StateManager.add_answer(task_id="[ID reçu]", author_agent="PropositionalLogicAgent", answer_text="...", source_ids=[bs_id si succès]).
        Si Tâche = "Exécuter ... Requêtes PL" (avec belief_set_id):
        a.  Récupérez le belief_set_content correspondant au belief_set_id depuis l'état (StateManager.get_current_state_snapshot(summarize=False) -> belief_sets). Si impossible (ID non trouvé), signalez erreur via add_answer et stoppez.
        b.  Récupérez le raw_text depuis l'état pour le contexte.
        c.  Appelez PLAnalyzer.semantic_GeneratePLQueries(input=raw_text, belief_set=belief_set_content). Validez mentalement la syntaxe des requêtes générées.
        d.  Initialisez formatted_results_list (pour l'interprétation) et log_ids_list. Pour CHAQUE requête q valide générée:
        i.  Appelez PLAnalyzer.execute_pl_query(belief_set_content=belief_set_content, query_string=q).
        ii. Notez le result_str retourné. Ajoutez-le à formatted_results_list. Si result_str commence par FUNC_ERROR:, loggez l'erreur mais continuez si possible avec les autres requêtes.
        iii.Appelez StateManager.log_query_result(belief_set_id=belief_set_id, query=q, raw_result=result_str). Notez le log_id. Ajoutez log_id à log_ids_list.
        e.  Si AU MOINS UNE requête a été tentée: Concaténez tous les result_str dans aggregated_results_str (séparés par newline \\n). Concaténez les requêtes valides testées dans queries_str.
        f.  Appelez PLAnalyzer.semantic_InterpretPLResult(input=raw_text, belief_set=belief_set_content, queries=queries_str, tweety_result=aggregated_results_str). Notez l'interpretation.
        g.  Préparez réponse texte (l'interpretation). Inclure un avertissement si des erreurs (FUNC_ERROR:) ont été rencontrées pendant l'exécution des requêtes.
        h.  Appelez StateManager.add_answer(task_id="[ID reçu]", author_agent="PropositionalLogicAgent", answer_text=interpretation, source_ids=[belief_set_id] + log_ids_list).
        Si Tâche Inconnue/Erreur Préliminaire: Indiquez-le et appelez StateManager.add_answer(task_id=\\"[ID reçu]\\", ...) avec le message d'erreur.


Important: Utilisez TOUJOURS task_id reçu pour add_answer. La syntaxe Tweety est STRICTE. Gérez les FUNC_ERROR: retournés par les outils. Vérifiez que la JVM est prête avant d'appeler execute_pl_query (normalement géré par le plugin, mais soyez conscient).
**CRUCIAL : Lorsque vous appelez une fonction (outil), vous DEVEZ fournir TOUS ses arguments requis dans le champ `arguments` de l'appel `tool_calls`. Ne faites PAS d'appels avec des arguments vides ou manquants.**
**CRUCIAL : Si vous décidez d'appeler la fonction `StateManager.designate_next_agent`, l'argument `agent_name` DOIT être l'un des noms d'agents valides suivants : "ProjectManagerAgent", "InformalAnalysisAgent", "PropositionalLogicAgent", "ExtractAgent". N'utilisez JAMAIS un nom de plugin ou un nom de fonction sémantique comme nom d'agent.**
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

    _llm_service_id: Optional[str] = PrivateAttr(default=None)
    _tweety_bridge: Optional[TweetyBridge] = PrivateAttr(default=None)

    def __init__(
        self,
        kernel: Kernel,
        agent_name: str = "PropositionalLogicAgent",
        instructions: Optional[str] = None,
        service_id: Optional[str] = None,
        tweety_bridge: Optional[TweetyBridge] = None,
    ):
        """
        Initialise l'agent de logique propositionnelle.

        Args:
            kernel (Kernel): L'instance du kernel Semantic Kernel.
            agent_name (str, optional): Nom de l'agent.
            instructions (Optional[str], optional): Prompt système à utiliser.
                Si `None`, `SYSTEM_PROMPT_PL` est utilisé.
            service_id (Optional[str], optional): ID du service LLM à utiliser
                pour les fonctions sémantiques.
            tweety_bridge (Optional[TweetyBridge], optional): Une instance pré-configurée
                de TweetyBridge. Si None, une nouvelle sera créée.
        """
        actual_instructions = instructions or SYSTEM_PROMPT_PL
        # Appel correct au constructeur de BaseLogicAgent
        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            logic_type_name="PL",
            system_prompt=actual_instructions,
            llm_service_id=service_id,
        )

        self.logger.info(
            f"Configuration des composants sémantiques pour {self.name}..."
        )

        # Utiliser le TweetyBridge injecté ou en créer un nouveau
        if tweety_bridge:
            self._tweety_bridge = tweety_bridge
            self.logger.info(
                f"Utilisation de l'instance TweetyBridge injectée pour {self.name}."
            )
        else:
            self.logger.info(
                f"Aucun TweetyBridge injecté. Création d'une nouvelle instance pour {self.name}."
            )
            self._tweety_bridge = TweetyBridge()

        if not self._tweety_bridge.initializer.is_jvm_ready():
            self.logger.critical(
                f"La JVM pour TweetyBridge de {self.name} n'est pas prête après initialisation. Impossible de continuer."
            )
            raise RuntimeError(
                f"JVM not ready for agent {self.name} after initialization attempt."
            )

        prompt_execution_settings = None
        if self._llm_service_id:
            try:
                prompt_execution_settings = (
                    self._kernel.get_prompt_execution_settings_from_service_id(
                        self._llm_service_id
                    )
                )
                self.logger.debug(f"Settings LLM récupérés pour {self.name}.")
            except Exception as e:
                self.logger.warning(
                    f"Impossible de récupérer les settings LLM pour {self.name}: {e}"
                )

        semantic_functions = [
            (
                "TextToPLDefs",
                PROMPT_TEXT_TO_PL_DEFS,
                "Extrait les propositions atomiques d'un texte.",
            ),
            (
                "TextToPLFormulas",
                PROMPT_TEXT_TO_PL_FORMULAS,
                "Génère les formules PL à partir d'un texte et de propositions.",
            ),
            (
                "GeneratePLQueryIdeas",
                PROMPT_GEN_PL_QUERIES_IDEAS,
                "Génère des idées de requêtes PL au format JSON.",
            ),
            (
                "InterpretPLResults",
                PROMPT_INTERPRET_PL,
                "Interprète les résultats de requêtes PL.",
            ),
        ]

        for func_name, prompt, description in semantic_functions:
            try:
                self._kernel.add_function(
                    prompt=prompt,
                    plugin_name=self.name,
                    function_name=func_name,
                    description=description,
                    prompt_execution_settings=prompt_execution_settings,
                )
                self.logger.info(
                    f"Fonction sémantique {self.name}.{func_name} ajoutée."
                )
            except Exception as e:
                self.logger.error(
                    f"Erreur lors de l'ajout de la fonction sémantique {self.name}.{func_name}: {e}",
                    exc_info=True,
                )

        self.logger.info(f"Composants pour {self.name} configurés.")

    def get_agent_capabilities(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "logic_type": self.logic_type_name,
            "description": "Agent capable d'analyser du texte en utilisant la logique propositionnelle (PL).",
            "methods": {
                "text_to_belief_set": "Convertit un texte en un ensemble de croyances PL.",
                "generate_queries": "Génère des requêtes PL pertinentes à partir d'un texte et d'un ensemble de croyances.",
                "execute_query": "Exécute une requête PL sur un ensemble de croyances.",
                "interpret_results": "Interprète les résultats d'une ou plusieurs requêtes PL.",
                "validate_formula": "Valide la syntaxe d'une formule PL.",
            },
        }

    def _extract_json_block(self, text: str) -> str:
        """Extrait le premier bloc JSON valide de la réponse du LLM."""
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            return match.group(1)

        start_index = text.find("{")
        end_index = text.rfind("}")
        if start_index != -1 and end_index != -1 and end_index > start_index:
            return text[start_index : end_index + 1]

        self.logger.warning(
            "Impossible d'isoler un bloc JSON. Tentative de parsing de la chaîne complète."
        )
        return text

    def _filter_formulas(
        self, formulas: List[str], declared_propositions: set
    ) -> List[str]:
        """Filtre les formules pour ne garder que celles qui utilisent des propositions déclarées."""
        valid_formulas = []
        # Regex pour extraire les identifiants qui ressemblent à des propositions
        proposition_pattern = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b")

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
        self.logger.info(
            f"{len(valid_formulas)}/{len(formulas)} formules conservées après filtrage."
        )
        return valid_formulas

    async def _invoke_llm_for_json(
        self,
        kernel: Kernel,
        plugin_name: str,
        function_name: str,
        arguments: Dict[str, Any],
        expected_keys: List[str],
        log_tag: str,
        max_retries: int,
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """Méthode helper pour invoquer une fonction sémantique et parser une réponse JSON."""
        for attempt in range(max_retries):
            self.logger.debug(
                f"[{log_tag}] Tentative {attempt + 1}/{max_retries} pour {plugin_name}.{function_name}..."
            )
            try:
                result = await kernel.invoke(
                    plugin_name=plugin_name,
                    function_name=function_name,
                    arguments=KernelArguments(**arguments),
                )
                response_text = str(result)
                json_block = self._extract_json_block(response_text)
                data = json.loads(json_block)

                if all(key in data for key in expected_keys):
                    self.logger.info(
                        f"[{log_tag}] Succès de l'invocation et du parsing JSON."
                    )
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

    async def text_to_belief_set(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[BeliefSet], str]:
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
        self.logger.info(
            f"Début de la conversion de texte en BeliefSet PL pour '{text[:100]}...'"
        )
        max_retries = 3

        # Étape 1: Génération des Propositions
        self.logger.debug(
            "[text_to_belief_set] Étape 1: Invocation du LLM pour TextToPLDefs..."
        )
        defs_json, error_msg = await self._invoke_llm_for_json(
            self._kernel,
            self.name,
            "TextToPLDefs",
            {"input": text},
            ["propositions"],
            "prop-gen",
            max_retries,
        )
        if not defs_json:
            return None, error_msg
        self.logger.debug("[text_to_belief_set] Étape 1: Terminé.")

        # Étape 2: Génération des Formules
        self.logger.debug(
            "[text_to_belief_set] Étape 2: Invocation du LLM pour TextToPLFormulas..."
        )
        formulas_json, error_msg = await self._invoke_llm_for_json(
            self._kernel,
            self.name,
            "TextToPLFormulas",
            {"input": text, "definitions": json.dumps(defs_json, indent=2)},
            ["formulas"],
            "formula-gen",
            max_retries,
        )
        if not formulas_json:
            return None, error_msg
        self.logger.debug("[text_to_belief_set] Étape 2: Terminé.")

        # Étape 3: Filtrage et Validation
        self.logger.debug("[text_to_belief_set] Étape 3: Filtrage des formules...")
        declared_propositions = set(defs_json.get("propositions", []))
        all_formulas = formulas_json.get("formulas", [])
        valid_formulas = self._filter_formulas(all_formulas, declared_propositions)
        if not valid_formulas:
            return (
                None,
                "Aucune formule valide n'a pu être générée ou conservée après filtrage.",
            )
        self.logger.debug("[text_to_belief_set] Étape 3: Terminé.")

        belief_set_content = "\n".join(valid_formulas)
        self.logger.debug(f"--- DÉBUT VÉRIFICATION CONSISTANCE ---")
        self.logger.debug(f"Contenu envoyé à Tweety:\n{belief_set_content}")

        is_consistent = False
        try:
            self.logger.debug(
                "Appel à self._tweety_bridge.pl_handler.pl_check_consistency..."
            )
            # Note: L'appel correct se fait via le pl_handler du bridge
            is_consistent = self._tweety_bridge.pl_handler.pl_check_consistency(
                belief_set_content
            )
            self.logger.debug(f"Appel à Tweety réussi. Résultat: {is_consistent}")
        except Exception as e:
            import traceback

            tb_str = "".join(
                traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
            )
            self.logger.error(
                f"############################################################"
            )
            self.logger.error(f"EXCEPTION CATASTROPHIQUE DANS PL_CHECK_CONSISTENCY")
            self.logger.error(f"TYPE: {type(e).__name__}")
            self.logger.error(f"MESSAGE: {e}")
            self.logger.error(f"TRACEBACK:\n{tb_str}")
            self.logger.error(
                f"############################################################"
            )
            # Propage l'erreur pour qu'elle soit visible dans les logs du serveur
            raise

        self.logger.debug(f"--- FIN VÉRIFICATION CONSISTANCE ---")

        if not is_consistent:
            self.logger.error(
                f"Ensemble de croyances final invalide: Incohérent\nContenu:\n{belief_set_content}"
            )
            return None, f"Ensemble de croyances invalide: Incohérent"

        belief_set = PropositionalBeliefSet(
            belief_set_content, propositions=list(declared_propositions)
        )
        self.logger.info("Conversion et validation du BeliefSet réussies.")
        return belief_set, "Conversion réussie."

    async def generate_queries(
        self, text: str, belief_set: BeliefSet, context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
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
        self.logger.info(
            f"Génération de requêtes PL via le modèle de requête pour '{text[:100]}...'"
        )

        if (
            not isinstance(belief_set, PropositionalBeliefSet)
            or not belief_set.propositions
        ):
            self.logger.error(
                "Le BeliefSet n'est pas du bon type ou ne contient pas de propositions déclarées."
            )
            return []

        try:
            # Le "belief_set" pour le prompt contient les propositions et les formules
            belief_set_for_prompt = json.dumps(
                {
                    "propositions": belief_set.propositions,
                    "formulas": belief_set.content.splitlines(),
                },
                indent=2,
            )

            arguments = KernelArguments(input=text, belief_set=belief_set_for_prompt)
            result = await self._kernel.invoke(
                plugin_name=self.name,
                function_name="GeneratePLQueryIdeas",
                arguments=arguments,
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
                    self.logger.warning(
                        f"Idée de requête rejetée: n'est pas une chaîne de caractères -> {idea}"
                    )
                    continue

                # Validation: l'idée est-elle une proposition déclarée ?
                if idea in declared_propositions:
                    # En PL, la requête est juste la proposition elle-même.
                    # On valide sa syntaxe pour être sûr.
                    if self.validate_formula(idea):
                        self.logger.info(f"Idée validée et requête assemblée: {idea}")
                        valid_queries.append(idea)
                    else:
                        self.logger.warning(
                            f"Idée rejetée: La requête assemblée '{idea}' a échoué la validation syntaxique."
                        )
                else:
                    self.logger.warning(
                        f"Idée de requête rejetée: Proposition inconnue '{idea}'."
                    )

            self.logger.info(
                f"Génération terminée. {len(valid_queries)}/{len(query_ideas)} requêtes valides assemblées."
            )
            return valid_queries

        except json.JSONDecodeError as e:
            self.logger.error(
                f"Erreur de décodage JSON lors de la génération des requêtes: {e}\nRéponse du LLM: {response_text}"
            )
            return []
        except Exception as e:
            self.logger.error(
                f"Erreur inattendue lors de la génération des requêtes: {e}",
                exc_info=True,
            )
            return []

    def execute_query(
        self, belief_set: BeliefSet, query: str
    ) -> Tuple[Optional[bool], str]:
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

            is_valid = self._tweety_bridge.validate_pl_formula(formula=query)
            if not is_valid:
                msg = f"Requête invalide: {query}."
                self.logger.error(msg)
                return None, f"FUNC_ERROR: {msg}"

            is_entailed, raw_output_str = self._tweety_bridge.execute_pl_query(
                belief_set_content=bs_str, query_string=query
            )

            if "FUNC_ERROR:" in raw_output_str:
                self.logger.error(
                    f"Erreur de TweetyBridge pour la requête '{query}': {raw_output_str}"
                )
                return None, raw_output_str

            self.logger.info(
                f"Résultat de l'exécution pour '{query}': {is_entailed}, Output brut: '{raw_output_str}'"
            )
            return is_entailed, raw_output_str

        except Exception as e:
            error_msg = (
                f"Erreur lors de l'exécution de la requête PL '{query}': {str(e)}"
            )
            self.logger.error(error_msg, exc_info=True)
            return None, f"FUNC_ERROR: {error_msg}"

    async def interpret_results(
        self,
        text: str,
        belief_set: BeliefSet,
        queries: List[str],
        results: List[Tuple[Optional[bool], str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
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
            results_messages_str = "\n".join(
                [
                    f"Query: {q} -> Result: {r[0]} ({r[1]})"
                    for q, r in zip(queries, results)
                ]
            )

            arguments = KernelArguments(
                input=text,
                belief_set=belief_set.content,
                queries=queries_str,
                tweety_result=results_messages_str,
            )

            result = await self._kernel.invoke(
                plugin_name=self.name,
                function_name="InterpretPLResults",
                arguments=arguments,
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
            is_valid = self._tweety_bridge.validate_pl_formula(formula=formula)
            if not is_valid:
                self.logger.warning(f"Formule PL invalide: '{formula}'.")
            return is_valid
        except Exception as e:
            self.logger.error(
                f"Erreur lors de la validation de la formule PL '{formula}': {e}",
                exc_info=True,
            )
            return False

    def is_consistent(self, belief_set: BeliefSet) -> tuple[bool, str]:
        self.logger.debug("Vérification de la cohérence de l'ensemble de croyances PL.")
        try:
            belief_set_content = belief_set.content
            # Correction: Appeler pl_check_consistency sur le _pl_handler du bridge.
            is_valid = self._tweety_bridge._pl_handler.pl_check_consistency(
                belief_set_content
            )

            if is_valid:
                details = "Belief set is consistent."
                self.logger.info(details)
            else:
                details = "Belief set is inconsistent."
                self.logger.warning(details)

            return is_valid, details
        except Exception as e:
            error_msg = (
                f"Erreur inattendue lors de la vérification de la cohérence: {e}"
            )
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    async def _create_belief_set_from_data(
        self, data: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[BeliefSet]:
        """
        Implémentation de la méthode abstraite pour créer un BeliefSet
        à partir de données textuelles brutes.
        """
        self.logger.debug(f"_create_belief_set_from_data appelé pour {self.name}.")
        belief_set, _ = await self.text_to_belief_set(text=data, context=context)
        return belief_set

    async def get_response(
        self, messages: list[ChatMessageContent]
    ) -> list[ChatMessageContent]:
        """(Compatibility) Gets a response from the agent."""
        import warnings

        warnings.warn(
            "The 'get_response' method is deprecated and will be removed in a future version. "
            "Please use 'invoke' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # La méthode prend maintenant une liste de messages, pas un kernel et des arguments.
        # Nous devons adapter l'appel si la logique interne de invoke() en dépend.
        # Pour l'instant, on délègue directement.
        return await self.invoke(messages)

    async def invoke_single(
        self, messages: list[ChatMessageContent]
    ) -> list[ChatMessageContent]:
        """
        Gère l'invocation de l'agent en analysant la dernière instruction du chat
        et en appelant la méthode interne appropriée.
        """
        self.logger.info(f"Invocation de {self.name} avec les messages fournis.")
        if not messages:
            error_msg = "L'historique du chat est vide, impossible de continuer."
            self.logger.error(error_msg)
            return [
                ChatMessageContent(
                    role="assistant",
                    content=f'{{"error": "{error_msg}"}}',
                    name=self.name,
                )
            ]

        last_user_message = messages[-1].content
        self.logger.debug(
            f"Analyse de la dernière instruction: {last_user_message[:200]}..."
        )

        # Analyser la tâche demandée (simplifié)
        if "belief set" in last_user_message.lower():
            task = "text_to_belief_set"
            self.logger.info("Tâche détectée: text_to_belief_set")
            source_text = messages[0].content if len(messages) > 1 else ""
            belief_set, message = await self.text_to_belief_set(source_text)
            if belief_set:
                response_content = json.dumps(belief_set.to_dict(), indent=2)
            else:
                response_content = f'{{"error": "Échec de la création du belief set", "details": "{message}"}}'

        elif "generate queries" in last_user_message.lower():
            task = "generate_queries"
            self.logger.info("Tâche détectée: generate_queries")
            source_text = messages[0].content
            belief_set, _ = await self.text_to_belief_set(source_text)
            if belief_set:
                queries = await self.generate_queries(source_text, belief_set)
                response_content = json.dumps({"generated_queries": queries})
            else:
                response_content = f'{{"error": "Impossible de générer les requêtes car le belief set n_a pas pu être créé."}}'

        elif "traduire le texte" in last_user_message.lower():
            task = "text_to_belief_set"
            self.logger.info(
                "Tâche détectée: text_to_belief_set (via 'traduire le texte')"
            )
            source_text = messages[0].content if len(messages) > 1 else ""
            belief_set, message = await self.text_to_belief_set(source_text)
            if belief_set:
                response_content = json.dumps(belief_set.to_dict(), indent=2)
            else:
                response_content = f'{{"error": "Échec de la création du belief set", "details": "{message}"}}'

        elif "exécuter des requêtes" in last_user_message.lower():
            task = "execute_query"
            self.logger.info(
                "Tâche détectée: execute_query (via 'exécuter des requêtes')"
            )
            source_text = messages[0].content if len(messages) > 1 else ""
            belief_set, message = await self.text_to_belief_set(source_text)
            if belief_set:
                is_consistent, details = self.is_consistent(belief_set)
                response_content = json.dumps(
                    {
                        "task": "check_consistency",
                        "is_consistent": is_consistent,
                        "details": details,
                    },
                    indent=2,
                )
            else:
                response_content = f'{{"error": "Impossible d\'exécuter la requête car le belief set n\'a pas pu être créé.", "details": "{message}"}}'

        else:
            self.logger.warning(
                f"Aucune tâche spécifique reconnue dans la dernière instruction pour {self.name}."
            )
            response_content = f'{{"error": "Tâche non reconnue pour {self.name}", "instruction": "{last_user_message}"}}'
            task = "unknown"

        self.logger.info(f"Tâche '{task}' terminée. Préparation de la réponse.")

        response_message = ChatMessageContent(
            role="assistant",
            content=response_content,
            name=self.name,
            metadata={"task_name": task},
        )
        return [response_message]

    async def invoke_stream(self, messages: list[ChatMessageContent]):
        final_result = await self.invoke(messages)

        async def stream_generator():
            yield final_result

        return stream_generator()
