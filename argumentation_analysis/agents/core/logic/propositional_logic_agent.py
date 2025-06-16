# argumentation_analysis/agents/core/logic/propositional_logic_agent.py
"""
Agent spécialisé pour la logique propositionnelle (PL).

Ce module définit `PropositionalLogicAgent`, une classe qui hérite de
`BaseLogicAgent` et implémente les fonctionnalités spécifiques pour interagir
avec la logique propositionnelle. Il utilise `TweetyBridge` pour la communication
avec TweetyProject et s'appuie sur des prompts sémantiques définis dans
`argumentation_analysis.agents.core.pl.prompts` pour la conversion
texte-vers-PL, la génération de requêtes et l'interprétation des résultats.
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
    Agent spécialisé pour la logique propositionnelle (PL).
    Refactorisé pour une robustesse et une transparence accrues, inspiré par FirstOrderLogicAgent.
    """
    service: Optional[ChatCompletionClientBase] = Field(default=None, exclude=True)
    settings: Optional[Any] = Field(default=None, exclude=True)

    def __init__(self, kernel: Kernel, agent_name: str = "PropositionalLogicAgent", system_prompt: Optional[str] = None, service_id: Optional[str] = None):
        actual_system_prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT_PL
        super().__init__(kernel,
                         agent_name=agent_name,
                         logic_type_name="PL",
                         system_prompt=actual_system_prompt)
        self._llm_service_id = service_id
        self._tweety_bridge = TweetyBridge()
        self.logger.info(f"TweetyBridge initialisé pour {self.name}. JVM prête: {self._tweety_bridge.is_jvm_ready()}")
        if not self._tweety_bridge.is_jvm_ready():
            self.logger.error("La JVM n'est pas prête. Les fonctionnalités de TweetyBridge pourraient ne pas fonctionner.")

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
                prompt_execution_settings = self.sk_kernel.get_prompt_execution_settings_from_service_id(self._llm_service_id)
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
                self.sk_kernel.add_function(
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

    async def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[BeliefSet], str]:
        self.logger.info(f"Conversion de texte en ensemble de croyances PL pour '{text[:100]}...'")
        max_retries = 3
        
        # --- Étape 1: Génération des Propositions ---
        self.logger.info("Étape 1: Génération des propositions atomiques...")
        defs_json = None
        for attempt in range(max_retries):
            try:
                defs_result = await self.sk_kernel.plugins[self.name]["TextToPLDefs"].invoke(self.sk_kernel, input=text)
                defs_json_str = self._extract_json_block(str(defs_result))
                defs_json = json.loads(defs_json_str)
                if "propositions" in defs_json and isinstance(defs_json["propositions"], list):
                    self.logger.info(f"Propositions générées avec succès à la tentative {attempt + 1}.")
                    break
                else:
                    raise ValueError("Le JSON ne contient pas la clé 'propositions' ou ce n'est pas une liste.")
            except (json.JSONDecodeError, ValueError, Exception) as e:
                self.logger.warning(f"Tentative {attempt + 1}/{max_retries} échouée pour générer les propositions: {e}")
                if attempt + 1 == max_retries:
                    error_msg = f"Échec final de la génération des propositions: {e}"
                    self.logger.error(error_msg)
                    return None, error_msg
        
        if defs_json is None:
            return None, "Impossible de générer les propositions après plusieurs tentatives."

        # --- Étape 2: Génération des Formules ---
        self.logger.info("Étape 2: Génération des formules...")
        formulas_json = None
        for attempt in range(max_retries):
            try:
                definitions_for_prompt = json.dumps(defs_json, indent=2)
                formulas_result = await self.sk_kernel.plugins[self.name]["TextToPLFormulas"].invoke(
                    self.sk_kernel, input=text, definitions=definitions_for_prompt
                )
                formulas_json_str = self._extract_json_block(str(formulas_result))
                formulas_json = json.loads(formulas_json_str)
                if "formulas" in formulas_json and isinstance(formulas_json["formulas"], list):
                    self.logger.info(f"Formules générées avec succès à la tentative {attempt + 1}.")
                    break
                else:
                    raise ValueError("Le JSON ne contient pas la clé 'formulas' ou ce n'est pas une liste.")
            except (json.JSONDecodeError, ValueError, Exception) as e:
                self.logger.warning(f"Tentative {attempt + 1}/{max_retries} échouée pour générer les formules: {e}")
                if attempt + 1 == max_retries:
                    error_msg = f"Échec final de la génération des formules: {e}"
                    self.logger.error(error_msg)
                    return None, error_msg

        if formulas_json is None:
            return None, "Impossible de générer les formules après plusieurs tentatives."

        # --- Étape 3: Filtrage programmatique des formules ---
        self.logger.info("Étape 3: Filtrage des formules...")
        declared_propositions = set(defs_json.get("propositions", []))
        valid_formulas = []
        all_formulas = formulas_json.get("formulas", [])
        
        for formula in all_formulas:
            # Extraire tous les identifiants (propositions atomiques) de la formule
            used_propositions = set(re.findall(r'\b[a-z_][a-z0-9_]*\b', formula))
            
            # Vérifier si toutes les propositions utilisées ont été déclarées
            if used_propositions.issubset(declared_propositions):
                valid_formulas.append(formula)
            else:
                invalid_props = used_propositions - declared_propositions
                self.logger.warning(f"Formule rejetée: '{formula}'. Contient des propositions non déclarées: {invalid_props}")

        self.logger.info(f"Filtrage terminé. {len(valid_formulas)}/{len(all_formulas)} formules conservées.")
        
        # --- Étape 4: Assemblage et Validation Finale ---
        self.logger.info("Étape 4: Assemblage et validation finale...")
        belief_set_content = "\n".join(valid_formulas)
        
        if not belief_set_content.strip():
            self.logger.error("La conversion a produit un ensemble de croyances vide après filtrage.")
            return None, "Ensemble de croyances vide après filtrage."
            
        is_valid, validation_msg = self._tweety_bridge.validate_belief_set(belief_set_string=belief_set_content)
        if not is_valid:
            self.logger.error(f"Ensemble de croyances final invalide: {validation_msg}\nContenu:\n{belief_set_content}")
            return None, f"Ensemble de croyances invalide: {validation_msg}"
        
        belief_set = PropositionalBeliefSet(belief_set_content, propositions=list(declared_propositions))
        self.logger.info("Conversion et validation réussies.")
        return belief_set, "Conversion réussie."

    async def generate_queries(self, text: str, belief_set: BeliefSet, context: Optional[Dict[str, Any]] = None) -> List[str]:
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
            result = await self.sk_kernel.invoke(
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
            
            result = await self.sk_kernel.invoke(
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
            is_valid, message = self._tweety_bridge.is_pl_kb_consistent(belief_set_content)
            if not is_valid:
                self.logger.warning(f"Ensemble de croyances PL incohérent: {message}")
            return is_valid, message
        except Exception as e:
            error_msg = f"Erreur inattendue lors de la vérification de la cohérence: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    async def get_response(
        self,
        chat_history: ChatHistory,
        settings: Optional[Any] = None,
    ) -> AsyncGenerator[list[ChatMessageContent], None]:
        """
        Méthode abstraite de `Agent` pour obtenir une réponse.
        Non implémentée car cet agent utilise des méthodes spécifiques.
        """
        logger.warning("La méthode 'get_response' n'est pas implémentée pour PropositionalLogicAgent et ne devrait pas être appelée directement.")
        yield []
        return

    async def invoke(
        self,
        chat_history: ChatHistory,
        settings: Optional[Any] = None,
    ) -> list[ChatMessageContent]:
        """
        Méthode abstraite de `Agent` pour invoquer l'agent.
        Non implémentée car cet agent utilise des méthodes spécifiques.
        """
        logger.warning("La méthode 'invoke' n'est pas implémentée pour PropositionalLogicAgent et ne devrait pas être appelée directement.")
        return []

    async def invoke_stream(
        self,
        chat_history: ChatHistory,
        settings: Optional[Any] = None,
    ) -> AsyncGenerator[list[ChatMessageContent], None]:
        """
        Méthode abstraite de `Agent` pour invoquer l'agent en streaming.
        Non implémentée car cet agent utilise des méthodes spécifiques.
        """
        logger.warning("La méthode 'invoke_stream' n'est pas implémentée pour PropositionalLogicAgent et ne devrait pas être appelée directement.")
        yield []
        return