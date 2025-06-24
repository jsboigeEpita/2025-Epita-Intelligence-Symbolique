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
from abc import abstractmethod

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.contents.chat_history import ChatHistory
from pydantic import Field
 
from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent
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

PROMPT_TEXT_TO_UNIFIED_FOL = """Expert en Logique du Premier Ordre (FOL), votre tâche est d'analyser un texte et de le convertir en une structure logique complète, incluant définitions et formules, dans un format JSON strict.

**Instructions Fondamentales :**

1.  **Analyse Complète :** Vous devez extraire les `sorts`, `constants`, `predicates` ET les `formulas` logiques qui traduisent les affirmations du texte.

2.  **Nomenclature :**
    *   `sorts`, `constants` : `snake_case` minuscule, singulier (ex: `etudiant`, `livre`).
    *   `predicates` : `PascalCase` (ex: `EstMortel`, `InfluenceCulture`).
    *   Ne jamais utiliser de pluriel pour les noms de prédicats.

3.  **Sorts vs. Prédicats :**
    *   Un `sort` est une catégorie (`homme`).
    *   Un `prédicat` est une propriété (`EstMortel`) ou une relation (`Aime`).
    *   Ne créez pas un `sort` pour une simple propriété.

4.  **Génération de Formules (RÈGLES IMPÉRATIVES) :**
    *   **RÈGLE D'OR - COHÉRENCE DES TYPES :** C'est la règle la plus importante. Le `sort` d'une variable ou d'une constante utilisée comme argument dans une formule DOIT correspondre EXACTEMENT au `sort` défini pour ce prédicat. Toute incohérence rend la sortie invalide.
        *   **Exemple de VIOLATION DE TYPE :**
            *   Définition: `{"name": "Mange", "args": ["animal", "nourriture"]}`
            *   Formule INCORRECTE: `forall X:chat (exists Y:plante (Mange(X, Y)))`
            *   **Analyse de l'erreur :** La formule est invalide car le prédicat `Mange` attend un `animal` et une `nourriture`, mais reçoit un `chat` et une `plante`. Même si conceptuellement un chat est un animal, vous devez utiliser les types exacts de la définition pour la validité logique.
    *   **Utilisation des définitions :** Utilisez **UNIQUEMENT** les `sorts`, `constants` et `predicates` que vous avez définis dans ce même JSON.
    *   **Syntaxe de quantification :** `forall X:sort (...)` ou `exists Y:sort (...)`.
    *   **ERREUR À ÉVITER (Sorts vs Constantes) :** N'utilisez **JAMAIS** un nom de `sort` (ex: `culture`) comme argument direct d'un prédicat.
        *   **Contexte :** `influence(ecrivain, culture)` est un prédicat et `culture` est un `sort`.
        *   **INCORRECT :** `influence(auteur_constant, culture)` <-- `culture` est un type, pas un individu.
        *   **CORRECT :** `exists X:culture (influence(auteur_constant, X))` <-- On quantifie sur une variable de type `culture`.

5.  **Format de sortie (JSON Strict IMPÉRATIF) :**
    ```json
    {
      "sorts": ["<type_1>", ...],
      "constants": {"<const_1>": "<type_1>", ...},
      "predicates": [{"name": "NomPredicat", "args": ["<type_1>", ...]}, ...],
      "formulas": ["<formule_1>", "<formule_2>", ...]
    }
    ```

**Exemple Complet :**

*   **Texte :** "Socrate est un homme. Tous les hommes sont mortels."
*   **JSON Attendu :**
    ```json
    {
      "sorts": ["homme"],
      "constants": {"socrate": "homme"},
      "predicates": [{"name": "EstMortel", "args": ["homme"]}],
      "formulas": [
        "EstMortel(socrate)",
        "forall X:homme (EstMortel(X))"
      ]
    }
    ```

**Votre Tâche :**

Texte à analyser : {{$input}}

Produisez le JSON final complet.
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
                self.logger.warning(f"Could not retrieve service '{service_id}': {e}")
        
        self._tweety_bridge = None
        self.logger.info(f"Agent {self.name} initialisé avec le type de logique {self.logic_type}.")

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

    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Configure les composants de l'agent, notamment le pont logique et les fonctions sémantiques.
        """
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants pour {self.name}...")
        self._tweety_bridge = TweetyBridge()

        if not self.tweety_bridge.is_jvm_ready():
            self.logger.error("Tentative de setup FOL Kernel alors que la JVM n'est PAS démarrée.")
            return

        default_settings = self._kernel.get_prompt_execution_settings_from_service_id(llm_service_id)
        
        # Ajout de la fonction unifiée pour la conversion texte -> FOL
        self._kernel.add_function(
            prompt=PROMPT_TEXT_TO_UNIFIED_FOL,
            plugin_name=self.name,
            function_name="TextToFOL",
            description="Convertit un texte en définitions et formules FOL en une seule étape.",
            prompt_execution_settings=default_settings
        )
        
        # Ajout des autres fonctions sémantiques nécessaires
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
        self.logger.info(f"Fonctions sémantiques pour {self.name} ajoutées au kernel.")
            
    def _normalize_identifier(self, text: str) -> str:
        """Normalise un identifiant en snake_case sans accents."""
        import unidecode
        text = unidecode.unidecode(text)
        text = re.sub(r'\s+', '_', text)
        text = re.sub(r'[^a-zA-Z0-9_]', '', text)
        return text.lower()

    async def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[BeliefSet], str]:
        """
        Convertit un texte en `FirstOrderBeliefSet` en utilisant un seul prompt unifié.
        """
        self.logger.info(f"Début de la conversion texte vers FOL pour {self.name}...")
        try:
            # Étape 1 : Appel unique au LLM pour tout générer
            self.logger.info("Étape 1: Génération de la structure logique complète...")
            unified_result = await self._kernel.plugins[self.name]["TextToFOL"].invoke(self._kernel, input=text)
            raw_unified_json = json.loads(self._extract_json_block(str(unified_result)))
            self.logger.debug(f"Structure brute reçue du LLM: {json.dumps(raw_unified_json, indent=2)}")

            # Étape 2 : Normalisation et inférence de la hiérarchie des sorts
            self.logger.info("Étape 2: Normalisation de la structure et inférence de la hiérarchie...")
            normalized_structure = self._normalize_logical_structure(raw_unified_json)
            self.logger.debug(f"Structure logique normalisée: {json.dumps(normalized_structure, indent=2)}")
            
            if not any(normalized_structure.get(k) for k in ["sorts", "constants", "predicates"]):
                return None, "Aucune structure logique (sorts, constantes, prédicats) n'a pu être extraite."


            # Étape 3 : Création de la signature Tweety
            self.logger.info("Étape 3: Création de l'objet signature Tweety...")
            signature_obj = self.tweety_bridge._fol_handler.create_programmatic_fol_signature(normalized_structure)
            if not signature_obj:
                return None, "Échec de la création d'un objet signature Tweety valide."

            # Étape 4 : Validation des formules
            self.logger.info("Étape 4: Validation des formules générées...")
            valid_formulas = []
            for formula_str in normalized_structure.get("formulas", []):
                cleaned_formula_str = re.sub(r'/\*.*?\*/', '', formula_str).strip()
                is_valid, msg = self.tweety_bridge._fol_handler.validate_formula_with_signature(signature_obj, cleaned_formula_str)
                if is_valid:
                    valid_formulas.append(cleaned_formula_str)
                    self.logger.info(f"Formule acceptée: '{cleaned_formula_str}'")
                else:
                    self.logger.warning(f"Formule rejetée: '{formula_str}'. Raison: {msg}")
            
            if not valid_formulas and normalized_structure.get("formulas"):
                 return None, "Toutes les formules générées étaient invalides selon la signature."

            # Étape 5 : Création du BeliefSet final
            self.logger.info("Étape 5: Création de l'ensemble de croyances final...")
            belief_set_obj = self.tweety_bridge._fol_handler.create_belief_set_from_formulas(signature_obj, valid_formulas)
            
            final_kb_json = {**normalized_structure, "formulas": valid_formulas}
            final_belief_set = FirstOrderBeliefSet(content=json.dumps(final_kb_json, indent=2), java_object=belief_set_obj)
            
            is_consistent, _ = self.is_consistent(final_belief_set)
            if not is_consistent:
                self.logger.warning("La base de connaissances finale est incohérente.")

            return final_belief_set, "Conversion unifiée réussie."

        except Exception as e:
            error_msg = f"Échec lors de la création de l'ensemble de croyances : {e}"
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

    def _normalize_logical_structure(self, structure_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalise les identifiants, infère la hiérarchie des sorts, et nettoie la structure logique.
        """
        import unidecode
        identifier_map = {}

        # 1. Normaliser sorts, constantes, prédicats et créer une map d'identifiants
        original_sorts = structure_json.get("sorts", [])
        normalized_sorts = sorted([self._normalize_identifier(s) for s in original_sorts])
        for orig, norm in zip(original_sorts, normalized_sorts):
             identifier_map[orig] = norm

        original_constants = structure_json.get("constants", {})
        normalized_constants = {}
        for const, sort in original_constants.items():
            norm_const = self._normalize_identifier(const)
            norm_sort = identifier_map.get(sort, self._normalize_identifier(sort))
            normalized_constants[norm_const] = norm_sort
            identifier_map[const] = norm_const

        original_predicates = structure_json.get("predicates", [])
        normalized_predicates = []
        # Map pour accès rapide : nom_pred_normalisé -> [sort_arg_1, sort_arg_2, ...]
        pred_sig_map = {}
        for pred in original_predicates:
            pred_name = pred.get("name", "")
            norm_pred_name = unidecode.unidecode(pred_name)
            norm_args = [identifier_map.get(arg, self._normalize_identifier(arg)) for arg in pred.get("args", [])]
            normalized_predicates.append({"name": norm_pred_name, "args": norm_args})
            pred_sig_map[norm_pred_name] = norm_args
            identifier_map[pred_name] = norm_pred_name

        # 2. Normaliser les formules en substituant les identifiants
        original_formulas = structure_json.get("formulas", [])
        formulas_with_normalized_ids = []
        sorted_identifiers = sorted(identifier_map.keys(), key=len, reverse=True)
        for formula in original_formulas:
            norm_formula = formula
            for orig_id in sorted_identifiers:
                norm_id = identifier_map[orig_id]
                norm_formula = re.sub(r'\b' + re.escape(orig_id) + r'\b', norm_id, norm_formula, flags=re.UNICODE)
            formulas_with_normalized_ids.append(norm_formula)
        
        # 3. Inférence de la hiérarchie des sorts à partir des incohérences de type
        sort_hierarchy = {}
        # Regex pour trouver les variables quantifiées et leur sort, e.g., "forall X:philosophe"
        quantified_vars_re = re.compile(r'(?:forall|exists)\s+([A-Z][a-zA-Z0-9]*):([a-z_]+)')
        # Regex pour trouver les appels de prédicats, e.g., "EstMortel(X)" ou "Amis(X, Y)"
        predicate_calls_re = re.compile(r'([A-Z][a-zA-Z0-9_]*)\(([^)]+)\)')

        for formula in formulas_with_normalized_ids:
            # Créer une map locale variable -> sort pour cette formule
            var_sort_map = {m.group(1): m.group(2) for m in quantified_vars_re.finditer(formula)}
            
            for call in predicate_calls_re.finditer(formula):
                pred_name = call.group(1)
                args = [arg.strip() for arg in call.group(2).split(',')]
                
                if pred_name not in pred_sig_map:
                    continue # Prédicat non défini, sera attrapé par la validation Tweety

                expected_sorts = pred_sig_map[pred_name]
                if len(args) != len(expected_sorts):
                    continue # Arity mismatch, sera aussi attrapé plus tard

                for i, arg_name in enumerate(args):
                    actual_sort = None
                    if arg_name in var_sort_map:
                        actual_sort = var_sort_map[arg_name]
                    elif arg_name in normalized_constants:
                        actual_sort = normalized_constants[arg_name]

                    expected_sort = expected_sorts[i]
                    
                    if actual_sort and actual_sort != expected_sort:
                        self.logger.info(f"Inférence de hiérarchie: '{actual_sort}' est un sous-sort de '{expected_sort}' "
                                         f"d'après l'usage dans {pred_name}(...{arg_name}...).")
                        sort_hierarchy[actual_sort] = expected_sort

        return {
            "sorts": normalized_sorts,
            "constants": normalized_constants,
            "predicates": normalized_predicates,
            "formulas": formulas_with_normalized_ids,
            "sort_hierarchy": sort_hierarchy # Nouvelle information cruciale
        }
        
    async def generate_queries(self, text: str, belief_set: FirstOrderBeliefSet, **kwargs) -> List[str]:
        """
        Génère une liste de requêtes FOL pertinentes en utilisant le LLM.
        """
        self.logger.info(f"Génération de requêtes FOL pour {self.name}...")
        try:
            if not belief_set or not belief_set.content:
                return []
                
            args = {"input": text, "belief_set": belief_set.content}
            result = await self._kernel.plugins[self.name]["GenerateFOLQueries"].invoke(self._kernel, **args)
            queries = json.loads(self._extract_json_block(str(result))).get("queries", [])
            self.logger.info(f"{len(queries)} requêtes potentielles reçues du LLM.")
            
            # Valider chaque requête générée
            valid_queries = []
            for q_str in queries:
                if self.validate_formula(q_str, belief_set):
                    valid_queries.append(q_str)
                    self.logger.info(f"Requête validée: {q_str}")
                else:
                    self.logger.warning(f"Requête invalide rejetée: {q_str}")
            return valid_queries
        except Exception as e:
            self.logger.error(f"Erreur durant la génération de requêtes: {e}", exc_info=True)
            return []

    def execute_query(self, belief_set: FirstOrderBeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête FOL sur un `FirstOrderBeliefSet` donné.
        """
        self.logger.info(f"Exécution de la requête: {query} pour l'agent {self.name}")
        if not belief_set.java_belief_set:
            return None, "Objet Java 'belief set' non trouvé."
        try:
            entails = self.tweety_bridge._fol_handler.fol_query(belief_set.java_belief_set, query)
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
            
            result = await self._kernel.plugins[self.name]["InterpretFOLResult"].invoke(
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

    def validate_formula(self, formula: str, belief_set: Optional[FirstOrderBeliefSet] = None) -> bool:
        """
        Validates the syntax of a FOL formula, optionally against a belief set's signature.
        """
        self.logger.debug(f"Validation de la formule FOL: {formula}")
        if belief_set and belief_set.java_belief_set:
            signature = belief_set.java_belief_set.getSignature()
            is_valid, _ = self.tweety_bridge._fol_handler.validate_formula_with_signature(signature, formula)
        else: # Fallback to context-less validation if no belief set provided
            is_valid, _ = self.tweety_bridge.validate_fol_formula(formula)
        return is_valid

    def is_consistent(self, belief_set: FirstOrderBeliefSet) -> Tuple[bool, str]:
        """Checks if a FOL belief set is consistent using its Java object."""
        self.logger.info(f"Vérification de la consistance pour {self.name}")
        if not belief_set.java_belief_set:
            return False, "Objet Java BeliefSet non créé."
        try:
            return self.tweety_bridge._fol_handler.fol_check_consistency(belief_set.java_belief_set)
        except Exception as e:
            self.logger.error(f"Erreur inattendue durant la vérification de consistance: {e}", exc_info=True)
            return False, str(e)

    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> BeliefSet:
        """Recreates a BeliefSet object from a dictionary."""
        content = belief_set_data.get("content", "")
        # This is a simplified recreation; the Java object is lost on serialization.
        return FirstOrderBeliefSet(content)

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

        if not self.validate_formula(conclusion, belief_set):
            self.logger.warning(f"La conclusion '{conclusion}' a une syntaxe invalide ou n'est pas alignée avec la signature du belief set.")
            
            #Tentative de réparation de la conclusion
            self.logger.info("Tentative de réparation de la conclusion en utilisant la normalisation...")
            
            # Crée une structure ad-hoc pour la normalisation
            temp_structure = json.loads(belief_set.content)
            temp_structure["formulas"] = [conclusion]
            
            repaired_structure = self._normalize_logical_structure(temp_structure)
            repaired_conclusion = repaired_structure["formulas"][0]
            self.logger.info(f"Conclusion réparée (tentative) : {repaired_conclusion}")

            if not self.validate_formula(repaired_conclusion, belief_set):
                 self.logger.error("La conclusion réparée est toujours invalide.")
                 return False
            conclusion = repaired_conclusion

        entails, query_status = self.execute_query(belief_set, conclusion)

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