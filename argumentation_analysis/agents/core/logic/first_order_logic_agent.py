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
from typing import Dict, List, Optional, Any, Tuple, AsyncGenerator

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.contents.chat_history import ChatHistory
from pydantic import Field

from ..abc.agent_bases import BaseLogicAgent
from .belief_set import BeliefSet, FirstOrderBeliefSet
from .tweety_bridge import TweetyBridge

# Configuration du logger
logger = logging.getLogger(__name__) # Utilisation de __name__ pour une meilleure pratique

# Prompt Système pour l'agent FOL
SYSTEM_PROMPT_FOL = """Vous êtes un agent spécialisé dans l'analyse et le raisonnement en logique du premier ordre (FOL).
Vous utilisez la syntaxe de TweetyProject pour représenter les formules FOL.
Vos tâches principales incluent la traduction de texte en formules FOL, la génération de requêtes FOL pertinentes,
l'exécution de ces requêtes sur un ensemble de croyances FOL, et l'interprétation des résultats obtenus.
"""

# Prompts pour la logique du premier ordre (optimisés)
PROMPT_TEXT_TO_FOL_DEFS = """Expert FOL : Extrayez sorts et prédicats du texte en format JSON strict.

Format : {"sorts": {"type": ["const1", "const2"]}, "predicates": [{"name": "PredName", "args": ["type1"]}]}

Règles : sorts/constantes en snake_case, prédicats commencent par majuscule.

Exemple : "Jean aime Paris" → {"sorts": {"person": ["jean"], "place": ["paris"]}, "predicates": [{"name": "Loves", "args": ["person", "place"]}]}

Texte : {{$input}}
"""

PROMPT_TEXT_TO_FOL_FORMULAS = """Expert FOL : Traduisez le texte en formules FOL en JSON strict.

Format : {"formulas": ["Pred(const)", "forall X: (Pred1(X) => Pred2(X))"]}

Règles : Utilisez UNIQUEMENT les sorts/prédicats fournis. Variables majuscules (X,Y). Connecteurs : !, &&, ||, =>, <=>

Texte : {{$input}}
Définitions : {{$definitions}}
"""

PROMPT_GEN_FOL_QUERIES_IDEAS = """Expert FOL : Générez des requêtes pertinentes en JSON strict.

Format : {"query_ideas": [{"predicate_name": "PredName", "constants": ["const1"]}]}

Règles : Utilisez UNIQUEMENT les prédicats/constantes du belief set. Priorité aux requêtes vérifiables.

Texte : {{$input}}
Belief Set : {{$belief_set}}
"""

PROMPT_INTERPRET_FOL = """Expert FOL : Interprétez les résultats de requêtes FOL en langage accessible.

Texte : {{$input}}
Belief Set : {{$belief_set}}
Requêtes : {{$queries}}
Résultats : {{$tweety_result}}

Pour chaque requête : objectif, statut (ACCEPTED/REJECTED), signification, implications.
Conclusion générale concise.
"""

from ..abc.agent_bases import BaseLogicAgent

class FirstOrderLogicAgent(BaseLogicAgent):
    """
    Agent spécialiste de l'analyse en logique du premier ordre (FOL).

    Cet agent étend `BaseLogicAgent` pour le traitement spécifique à la FOL.
    Il combine des fonctions sémantiques (via LLM) pour l'interprétation du
    langage naturel et `TweetyBridge` pour la rigueur logique.

    Le workflow principal est similaire à celui des autres agents logiques :
    1.  `text_to_belief_set` : Convertit le texte en `FirstOrderBeliefSet`.
    2.  `generate_queries` : Suggère des requêtes FOL pertinentes.
    3.  `execute_query` : Exécute une requête sur le `FirstOrderBeliefSet`.
    4.  `interpret_results` : Traduit le résultat logique en explication naturelle.

    La complexité de la FOL impose une gestion plus fine de la signature (sorts,
    constantes, prédicats), qui est gérée en interne par cet agent.

    Attributes:
        _tweety_bridge (TweetyBridge): Pont vers la bibliothèque logique Java Tweety.
            Cette instance est créée dynamiquement lors du `setup_agent_components`.
    """
    
    # Attributs requis par Pydantic V2 pour la nouvelle classe de base Agent
    # Ces attributs ne sont pas utilisés activement par cette classe, mais doivent être déclarés.
    # Ils sont normalement gérés par la classe de base `Agent` mais Pydantic exige leur présence.
    # Utilisation de `Field(default=..., exclude=True)` pour éviter qu'ils soient inclus
    # dans la sérialisation ou la validation standard du modèle.
    service: Optional[ChatCompletionClientBase] = Field(default=None, exclude=True)
    settings: Optional[Any] = Field(default=None, exclude=True) # Remplace PromptExecutionSettings

    def __init__(self, kernel: Kernel, agent_name: str = "FirstOrderLogicAgent", service_id: Optional[str] = None):
        """
        Initialise l'agent de logique du premier ordre.

        Args:
            kernel (Kernel): L'instance du kernel Semantic Kernel.
            agent_name (str, optional): Nom de l'agent.
            service_id (Optional[str], optional): ID du service LLM à utiliser
                pour les fonctions sémantiques.
        """
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
                self.logger.warning(f"Could not retrieve service '{service_id}': {e}")

        self.logger.info(f"Agent {self.name} initialisé avec le type de logique {self.logic_type}.")

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Retourne un dictionnaire décrivant les capacités de l'agent.

        Returns:
            Dict[str, Any]: Un dictionnaire détaillant le nom, le type de logique,
            la description et les méthodes principales de l'agent.
        """
        return {
            "name": self.name,
            "logic_type": self.logic_type,
            "description": "Agent capable d'analyser du texte en utilisant la logique du premier ordre (FOL). "
                           "Peut convertir du texte en un ensemble de croyances FOL, générer des requêtes FOL, "
                           "exécuter ces requêtes, et interpréter les résultats.",
            "methods": {
                "text_to_belief_set": "Convertit un texte en un ensemble de croyances FOL.",
                "generate_queries": "Génère des requêtes FOL pertinentes à partir d'un texte et d'un ensemble de croyances.",
                "execute_query": "Exécute une requête FOL sur un ensemble de croyances.",
                "interpret_results": "Interprète les résultats d'une ou plusieurs requêtes FOL.",
                "validate_formula": "Valide la syntaxe d'une formule FOL."
            }
        }

    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Configure les composants de l'agent, notamment le pont logique et les fonctions sémantiques.

        Cette méthode initialise `TweetyBridge` et enregistre tous les prompts
        spécifiques à la FOL en tant que fonctions dans le kernel.

        Args:
            llm_service_id (str): L'ID du service LLM à utiliser pour les
                fonctions sémantiques enregistrées.
        """
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants pour {self.name}...")

        self._tweety_bridge = TweetyBridge()

        if not self.tweety_bridge.is_jvm_ready():
            self.logger.error("Tentative de setup FOL Kernel alors que la JVM n'est PAS démarrée.")
            return
        
        default_settings = None
        if self._llm_service_id: 
            try:
                default_settings = self._kernel.get_prompt_execution_settings_from_service_id(
                    self._llm_service_id
                )
                self.logger.debug(f"Settings LLM récupérés pour {self.name}.")
            except Exception as e:
                self.logger.warning(f"Impossible de récupérer settings LLM pour {self.name}: {e}")

        semantic_functions = [
            ("TextToFOLDefs", PROMPT_TEXT_TO_FOL_DEFS,
             "Extrait les sorts et prédicats FOL d'un texte."),
            ("TextToFOLFormulas", PROMPT_TEXT_TO_FOL_FORMULAS,
             "Génère les formules FOL à partir d'un texte et de définitions."),
            ("GenerateFOLQueryIdeas", PROMPT_GEN_FOL_QUERIES_IDEAS,
             "Génère des idées de requêtes FOL au format JSON."),
            ("InterpretFOLResult", PROMPT_INTERPRET_FOL,
             "Interprète résultat requête FOL Tweety formaté.")
        ]

        for func_name, prompt, description in semantic_functions:
            try:
                if not prompt or not isinstance(prompt, str):
                    self.logger.error(f"ERREUR: Prompt invalide pour {self.name}.{func_name}")
                    continue
                
                self.logger.info(f"Ajout fonction {self.name}.{func_name} avec prompt de {len(prompt)} caractères")
                self._kernel.add_function(
                    prompt=prompt,
                    plugin_name=self.name,
                    function_name=func_name,
                    description=description,
                    prompt_execution_settings=default_settings
                )
                self.logger.debug(f"Fonction sémantique {self.name}.{func_name} ajoutée/mise à jour.")
                
                if self.name in self._kernel.plugins and func_name in self._kernel.plugins[self.name]:
                    self.logger.info(f"(OK) Fonction {self.name}.{func_name} correctement enregistrée.")
                else:
                    self.logger.error(f"(CRITICAL ERROR) Fonction {self.name}.{func_name} non trouvée après ajout!")
            except ValueError as ve:
                self.logger.warning(f"Problème ajout/MàJ {self.name}.{func_name}: {ve}")
            except Exception as e:
                self.logger.error(f"Exception inattendue lors de l'ajout de {self.name}.{func_name}: {e}", exc_info=True)
        
        self.logger.info(f"Composants de {self.name} configurés.")

    def _normalize_identifier(self, text: str) -> str:
        """Normalise un identifiant en snake_case sans accents."""
        import unidecode
        text = unidecode.unidecode(text)
        text = re.sub(r'\s+', '_', text)
        text = re.sub(r'[^a-zA-Z0-9_]', '', text)
        return text.lower()

    async def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[BeliefSet], str]:
        """
        Convertit un texte en langage naturel en un `FirstOrderBeliefSet` validé.

        Ce processus multi-étapes utilise le LLM pour la génération de la signature
        (sorts, prédicats) et des formules, puis s'appuie sur `TweetyBridge` pour
        la validation rigoureuse de chaque formule par rapport à la signature.

        Args:
            text (str): Le texte en langage naturel à convertir.
            context (Optional[Dict[str, Any]]): Contexte additionnel (non utilisé).

        Returns:
            Tuple[Optional[BeliefSet], str]: Un tuple contenant le `FirstOrderBeliefSet`
            créé (qui inclut l'objet Java pour les opérations futures) ou `None`
            en cas d'échec, et un message de statut.
        """
        self.logger.info(f"Converting text to FOL belief set for {self.name} (programmatic approach)...")
        
        try:
            self.logger.info("Step 1: Generating definitions (sorts, predicates)...")
            defs_result = await self._kernel.plugins[self.name]["TextToFOLDefs"].invoke(self._kernel, input=text)
            defs_json = json.loads(self._extract_json_block(str(defs_result)))

            self.logger.info("Step 1.5: Programmatically correcting predicate arguments...")
            sorts_map = {c: s_name for s_name, consts in defs_json.get("sorts", {}).items() for c in consts}
            defs_json["predicates"] = [
                {"name": p["name"], "args": [sorts_map.get(arg, arg) for arg in p.get("args", [])]}
                for p in defs_json.get("predicates", [])
            ]

            self.logger.info("Step 2: Generating formulas...")
            definitions_for_prompt = json.dumps(defs_json, indent=2)
            formulas_result = await self._kernel.plugins[self.name]["TextToFOLFormulas"].invoke(
                self._kernel, input=text, definitions=definitions_for_prompt
            )
            formulas_json = json.loads(self._extract_json_block(str(formulas_result)))

            self.logger.info("Step 3: Normalizing and assembling...")
            kb_json = self._normalize_and_validate_json({
                "sorts": defs_json.get("sorts", {}),
                "predicates": defs_json.get("predicates", []),
                "formulas": formulas_json.get("formulas", [])
            })

            self.logger.info("Step 4: Programmatic construction and validation...")
            signature_obj = self.tweety_bridge._fol_handler.create_programmatic_fol_signature(kb_json)
            
            valid_formulas = []
            for formula_str in kb_json.get("formulas", []):
                is_valid, msg = self.tweety_bridge._fol_handler.validate_formula_with_signature(signature_obj, formula_str)
                if is_valid:
                    valid_formulas.append(formula_str)
                else:
                    self.logger.warning(f"Formula rejected by Tweety: '{formula_str}'. Reason: {msg}")

            if not valid_formulas and kb_json.get("formulas"):
                return None, "All generated formulas were invalid."

            belief_set_obj = self.tweety_bridge._fol_handler.create_belief_set_from_formulas(signature_obj, valid_formulas)
            
            kb_json["formulas"] = valid_formulas
            final_belief_set = FirstOrderBeliefSet(content=json.dumps(kb_json), java_object=belief_set_obj)

            is_consistent, _ = self.is_consistent(final_belief_set)
            if not is_consistent:
                self.logger.warning("The final knowledge base is inconsistent.")

            return final_belief_set, "Conversion successful."

        except (ValueError, jpype.JException, json.JSONDecodeError) as e:
            error_msg = f"Failed during belief set creation: {e}"
            self.logger.error(error_msg, exc_info=True)
            return None, error_msg

    def _extract_json_block(self, text: str) -> str:
        """Extracts the first valid JSON block from the LLM's response."""
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            return match.group(1)
        
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return text[start:end+1]
        
        self.logger.warning("No JSON block found in the response.")
        return "{}"

    def _normalize_and_validate_json(self, kb_json: Dict[str, Any]) -> Dict[str, Any]:
        """Normalises identifiers in the JSON knowledge base."""
        normalized_kb = {"predicates": kb_json.get("predicates", [])}
        constant_map = {}
        normalized_sorts = {}
        for sort_name, constants in kb_json.get("sorts", {}).items():
            norm_sort_name = self._normalize_identifier(sort_name)
            norm_constants = [self._normalize_identifier(c) for c in constants]
            constant_map.update({c: nc for c, nc in zip(constants, norm_constants)})
            normalized_sorts[norm_sort_name] = norm_constants
        normalized_kb["sorts"] = normalized_sorts
        
        normalized_formulas = []
        for formula in kb_json.get("formulas", []):
            norm_formula = formula
            for orig, norm in constant_map.items():
                norm_formula = re.sub(r'\b' + re.escape(orig) + r'\b', norm, norm_formula)
            normalized_formulas.append(norm_formula)
        normalized_kb["formulas"] = normalized_formulas

        self.logger.info("JSON normalization complete.")
        return normalized_kb

    def _parse_belief_set_content(self, belief_set: FirstOrderBeliefSet) -> Dict[str, Any]:
        """Extracts sorts, constants, and predicates from the source JSON of a belief set."""
        if not belief_set or not belief_set.content:
            return {"sorts": {}, "constants": set(), "predicates": {}}
        try:
            kb_json = json.loads(belief_set.content)
            all_constants = {c for consts in kb_json.get("sorts", {}).values() for c in consts}
            predicates_map = {p["name"]: len(p.get("args", [])) for p in kb_json.get("predicates", [])}
            return {
                "constants": all_constants,
                "predicates": predicates_map,
                "signature_obj": belief_set.java_belief_set.getSignature() if belief_set.java_belief_set else None,
            }
        except (json.JSONDecodeError, AttributeError) as e:
            self.logger.error(f"Could not parse belief set content for query generation: {e}")
            return {"constants": set(), "predicates": {}}

    async def generate_queries(self, text: str, belief_set: FirstOrderBeliefSet, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Génère une liste de requêtes FOL pertinentes et valides pour un `BeliefSet` donné.

        Le processus :
        1. Utilise le LLM pour suggérer des "idées" de requêtes.
        2. Valide que chaque idée est conforme à la signature du `BeliefSet` (prédicats, constantes, arité).
        3. Assemble les idées valides en chaînes de requêtes FOL.
        4. Valide la syntaxe finale de chaque requête assemblée avec `TweetyBridge`.

        Args:
            text (str): Le texte original pour le contexte.
            belief_set (FirstOrderBeliefSet): Le `BeliefSet` à interroger.
            context (Optional[Dict[str, Any]]): Contexte additionnel (non utilisé).

        Returns:
            List[str]: Une liste de chaînes de requêtes FOL prêtes à être exécutées.
        """
        self.logger.info(f"Generating FOL queries for {self.name}...")
        try:
            kb_details = self._parse_belief_set_content(belief_set)
            if not kb_details["predicates"]:
                 return []
            
            args = {"input": text, "belief_set": belief_set.content}
            result = await self._kernel.plugins[self.name]["GenerateFOLQueryIdeas"].invoke(self._kernel, **args)
            query_ideas = json.loads(self._extract_json_block(str(result))).get("query_ideas", [])
            self.logger.info(f"{len(query_ideas)} query ideas received from LLM.")

            valid_queries = []
            signature_obj = kb_details.get("signature_obj")
            if not signature_obj:
                return []

            for idea in query_ideas:
                p_name, constants = idea.get("predicate_name"), idea.get("constants", [])
                if not (p_name in kb_details["predicates"] and
                        all(c in kb_details["constants"] for c in constants) and
                        kb_details["predicates"][p_name] == len(constants)):
                    continue
                
                query_str = f"{p_name}({', '.join(constants)})"
                is_valid, _ = self.tweety_bridge._fol_handler.validate_formula_with_signature(signature_obj, query_str)
                if is_valid:
                    self.logger.info(f"Assembled and validated query: {query_str}")
                    valid_queries.append(query_str)
            return valid_queries
        except Exception as e:
            self.logger.error(f"Error during query generation: {e}", exc_info=True)
            return []

    def execute_query(self, belief_set: FirstOrderBeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête FOL sur un `FirstOrderBeliefSet` donné.

        Cette méthode s'appuie sur l'objet Java `BeliefSet` stocké dans l'instance
        `FirstOrderBeliefSet` pour effectuer l'interrogation via `TweetyBridge`.

        Args:
            belief_set (FirstOrderBeliefSet): L'ensemble de croyances contenant l'objet Java.
            query (str): La requête FOL à exécuter.

        Returns:
            Tuple[Optional[bool], str]: Un tuple contenant le résultat (`True` si
            prouvé, `False` sinon, `None` en cas d'erreur) et un statut textuel
            ("ACCEPTED", "REJECTED", ou message d'erreur).
        """
        self.logger.info(f"Executing query: {query} for agent {self.name}")
        if not belief_set.java_belief_set:
            return None, "Java belief set object not found."
        try:
            entails = self.tweety_bridge._fol_handler.fol_query(belief_set.java_belief_set, query)
            result_str = "ACCEPTED" if entails else "REJECTED"
            return entails, result_str
        except Exception as e:
            error_msg = f"Error executing query: {e}"
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
        self.logger.info(f"Interpreting results for agent {self.name}...")
        try:
            queries_str = "\n".join(queries)
            results_text_list = [res[1] if res else "Error: No result" for res in results]
            results_str = "\n".join(results_text_list)
            
            result = await self._kernel.plugins[self.name]["InterpretFOLResult"].invoke(
                self._kernel,
                input=text,
                belief_set=belief_set.content,
                queries=queries_str,
                tweety_result=results_str
            )
            return str(result)
        except Exception as e:
            error_msg = f"Error during result interpretation: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"Interpretation Error: {error_msg}"

    def validate_formula(self, formula: str, belief_set: Optional[FirstOrderBeliefSet] = None) -> bool:
        """
        Validates the syntax of a FOL formula, optionally against a belief set's signature.
        """
        self.logger.debug(f"Validating FOL formula: {formula}")
        if belief_set and belief_set.java_belief_set:
            signature = belief_set.java_belief_set.getSignature()
            is_valid, _ = self.tweety_bridge._fol_handler.validate_formula_with_signature(signature, formula)
        else: # Fallback to context-less validation if no belief set provided
            is_valid, _ = self.tweety_bridge.validate_fol_formula(formula)
        return is_valid

    def is_consistent(self, belief_set: FirstOrderBeliefSet) -> Tuple[bool, str]:
        """Checks if a FOL belief set is consistent using its Java object."""
        self.logger.info(f"Checking consistency for {self.name}")
        if not belief_set.java_belief_set:
            return False, "Java BeliefSet object not created."
        try:
            return self.tweety_bridge._fol_handler.fol_check_consistency(belief_set.java_belief_set)
        except Exception as e:
            self.logger.error(f"Unexpected error during consistency check: {e}", exc_info=True)
            return False, str(e)

    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> BeliefSet:
        """Recreates a BeliefSet object from a dictionary."""
        content = belief_set_data.get("content", "")
        # This is a simplified recreation; the Java object is lost on serialization.
        # A more robust implementation would re-parse the content JSON here.
        return FirstOrderBeliefSet(content)

    async def get_response(
        self,
        chat_history: ChatHistory,
        settings: Optional[Any] = None,
    ) -> AsyncGenerator[list[ChatMessageContent], None]:
        logger.warning(f"Method 'get_response' is not implemented for {self.name}.")
        yield []
        return

    async def invoke(
        self,
        chat_history: ChatHistory,
        settings: Optional[Any] = None,
    ) -> list[ChatMessageContent]:
        logger.warning(f"Method 'invoke' is not implemented for {self.name}.")
        return []

    async def invoke_stream(
        self,
        chat_history: ChatHistory,
        settings: Optional[Any] = None,
    ) -> AsyncGenerator[list[ChatMessageContent], None]:
        logger.warning(f"Method 'invoke_stream' is not implemented for {self.name}.")
        yield []
        return
        
    async def invoke_single(self, *args, **kwargs) -> list[ChatMessageContent]:
        """Generic entry point. Not the primary way to use this agent."""
        self.logger.info(f"Generic invocation of {self.name}. Analyzing arguments...")
        if "text_to_belief_set_input" in kwargs:
            text = kwargs["text_to_belief_set_input"]
            belief_set_obj, message = await self.text_to_belief_set(text)
            response_content = belief_set_obj.to_dict() if belief_set_obj else {"error": message}
        elif "generate_queries_input" in kwargs and "belief_set" in kwargs:
             text, belief_set = kwargs["generate_queries_input"], kwargs["belief_set"]
             queries = await self.generate_queries(text, belief_set)
             response_content = {"generated_queries": queries}
        else:
            response_content = {"error": "Unrecognized task."}
        return [ChatMessageContent(role="assistant", content=json.dumps(response_content), name=self.name)]