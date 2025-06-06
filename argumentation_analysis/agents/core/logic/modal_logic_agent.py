# argumentation_analysis/agents/core/logic/modal_logic_agent.py
"""
Agent spécialisé pour la logique modale (Modal Logic).

Ce module définit `ModalLogicAgent`, une classe qui hérite de
`BaseLogicAgent` et implémente les fonctionnalités spécifiques pour interagir
avec la logique modale. Il utilise `TweetyBridge` pour la communication
avec TweetyProject et s'appuie sur des prompts sémantiques définis dans ce
module pour la conversion texte-vers-Modal, la génération de requêtes et
l'interprétation des résultats.
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
from .belief_set import BeliefSet, ModalBeliefSet
from .tweety_bridge import TweetyBridge

# Configuration du logger
logger = logging.getLogger(__name__)

# Prompt Système pour l'agent Modal Logic
SYSTEM_PROMPT_MODAL = """Vous êtes un agent spécialisé dans l'analyse et le raisonnement en logique modale (Modal Logic).
Vous utilisez la syntaxe de TweetyProject pour représenter les formules modales.
Vos tâches principales incluent la traduction de texte en formules modales, la génération de requêtes modales pertinentes,
l'exécution de ces requêtes sur un ensemble de croyances modales, et l'interprétation des résultats obtenus.

Les opérateurs modaux que vous utilisez sont :
- [] (nécessité) : "il est nécessaire que"
- <> (possibilité) : "il est possible que"
"""

# Prompts pour la logique modale
PROMPT_TEXT_TO_MODAL_BELIEF_SET = """
Vous êtes un expert en logique modale. Votre tâche est de convertir un texte en langage naturel en un ensemble de croyances modales.

**Format de Sortie (JSON Strict):**
Votre sortie DOIT être un objet JSON unique contenant deux clés : `propositions` et `modal_formulas`.

1. **`propositions`**: Une liste des propositions de base extraites du texte. Les propositions doivent être en minuscules et en `snake_case` (ex: ["il_pleut", "jean_travaille"]).

2. **`modal_formulas`**: Une liste de formules modales utilisant les opérateurs `[]` (nécessité) et `<>` (possibilité). Utilisez les propositions définies précédemment.

**Opérateurs modaux:**
- `[]p` signifie "il est nécessaire que p"
- `<>p` signifie "il est possible que p"
- Vous pouvez utiliser les connecteurs logiques: `!`, `&&`, `||`, `=>`, `<=>`

**Exemple:**
Texte: "Il pleut nécessairement. Il est possible que Jean travaille. S'il pleut, alors il est nécessaire que les routes soient mouillées."

**Sortie JSON attendue:**
```json
{
  "propositions": ["il_pleut", "jean_travaille", "routes_mouillees"],
  "modal_formulas": [
    "[]il_pleut",
    "<>jean_travaille",
    "il_pleut => []routes_mouillees"
  ]
}
```

**Règles importantes:**
- N'utilisez QUE les propositions que vous avez déclarées dans la liste `propositions`
- Les formules modales doivent être syntaxiquement correctes
- Gardez les noms de propositions courts et descriptifs

Analysez le texte suivant et générez l'ensemble de croyances modal:

{{$input}}
"""

PROMPT_GEN_MODAL_QUERIES_IDEAS = """
Vous êtes un expert en logique modale. Votre tâche est de générer des "idées" de requêtes pertinentes pour interroger un ensemble de croyances modales.

**Contexte Fourni:**
1. **Texte Original**: Le texte qui motive l'analyse.
2. **Ensemble de Croyances Modales**: Une description structurée de la logique extraite du texte, contenant les `propositions` et les `modal_formulas`.

**Votre Tâche:**
Générez un objet JSON contenant UNIQUEMENT la clé `query_ideas`.
La valeur de `query_ideas` doit être une liste d'objets JSON, où chaque objet représente une idée de requête et contient une clé :
1. `formula`: Une formule modale à tester (ex: "[]il_pleut", "<>jean_travaille").

**Règles Strictes:**
- **Utilisation Exclusive**: N'utilisez QUE les `propositions` qui existent dans l'ensemble de croyances fourni. N'en inventez pas.
- **Pertinence**: Les idées de requêtes doivent être pertinentes par rapport au texte original et chercher à vérifier des conclusions modales intéressantes.
- **Opérateurs modaux**: Utilisez `[]` pour la nécessité et `<>` pour la possibilité.
- **Format de Sortie**: Votre sortie DOIT être un objet JSON valide, sans aucun texte ou explication supplémentaire.

**Exemple:**
Texte Original: "Il pleut nécessairement. Il est possible que Jean travaille."
Ensemble de Croyances:
```json
{
  "propositions": ["il_pleut", "jean_travaille"],
  "modal_formulas": [
    "[]il_pleut",
    "<>jean_travaille"
  ]
}
```

**Sortie JSON attendue:**
```json
{
  "query_ideas": [
    {
      "formula": "[]il_pleut"
    },
    {
      "formula": "<>jean_travaille"
    },
    {
      "formula": "![]!jean_travaille"
    }
  ]
}
```

Maintenant, analysez le contexte suivant et générez les idées de requêtes.

**Texte Original:**
{{$input}}

**Ensemble de Croyances:**
{{$belief_set}}
"""

PROMPT_INTERPRET_MODAL = """
Vous êtes un expert en logique modale. Votre tâche est d'interpréter les résultats de requêtes en logique modale et d'expliquer leur signification dans le contexte du texte source.

Voici le texte source:
{{$input}}

Voici l'ensemble de croyances en logique modale:
{{$belief_set}}

Voici les requêtes qui ont été exécutées:
{{$queries}}

Voici les résultats de ces requêtes:
{{$tweety_result}}

Interprétez ces résultats et expliquez leur signification dans le contexte du texte source. Pour chaque requête:
1. Expliquez ce que la requête cherchait à vérifier (en termes de nécessité ou possibilité)
2. Indiquez si la requête a été acceptée (ACCEPTED) ou rejetée (REJECTED)
3. Expliquez ce que cela signifie dans le contexte du texte source
4. Si pertinent, mentionnez les implications modales de ce résultat

**Rappel des opérateurs modaux:**
- `[]p` signifie "il est nécessaire que p"
- `<>p` signifie "il est possible que p"

Fournissez ensuite une conclusion générale sur ce que ces résultats nous apprennent sur les modalités présentes dans le texte source.

Votre réponse doit être claire, précise et accessible à quelqu'un qui n'est pas expert en logique modale.
"""

class ModalLogicAgent(BaseLogicAgent): 
    """
    Agent spécialisé pour la logique modale (Modal Logic).

    Cet agent étend `BaseLogicAgent` pour fournir des capacités de traitement
    spécifiques à la logique modale. Il intègre des fonctions sémantiques
    pour traduire le langage naturel en ensembles de croyances modales, générer des
    requêtes modales pertinentes, exécuter ces requêtes via `TweetyBridge`, et
    interpréter les résultats en langage naturel.

    Attributes:
        _tweety_bridge (TweetyBridge): Instance de `TweetyBridge` configurée pour la logique modale.
    """
    
    # Attributs requis par Pydantic V2 pour la nouvelle classe de base Agent
    service: Optional[ChatCompletionClientBase] = Field(default=None, exclude=True)
    settings: Optional[Any] = Field(default=None, exclude=True)

    def __init__(self, kernel: Kernel, agent_name: str = "ModalLogicAgent", service_id: Optional[str] = None):
        """
        Initialise une instance de `ModalLogicAgent`.

        :param kernel: Le kernel Semantic Kernel à utiliser pour les fonctions sémantiques.
        :param agent_name: Le nom de l'agent (par défaut "ModalLogicAgent").
        :param service_id: L'ID du service LLM à utiliser.
        """
        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            logic_type_name="Modal",
            system_prompt=SYSTEM_PROMPT_MODAL
        )
        self._llm_service_id = service_id

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Retourne un dictionnaire décrivant les capacités spécifiques de cet agent Modal.

        :return: Un dictionnaire détaillant le nom, le type de logique, la description
                 et les méthodes de l'agent.
        :rtype: Dict[str, Any]
        """
        return {
            "name": self.name,
            "logic_type": self.logic_type,
            "description": "Agent capable d'analyser du texte en utilisant la logique modale. "
                           "Peut convertir du texte en un ensemble de croyances modales, générer des requêtes modales, "
                           "exécuter ces requêtes, et interpréter les résultats.",
            "methods": {
                "text_to_belief_set": "Convertit un texte en un ensemble de croyances modales.",
                "generate_queries": "Génère des requêtes modales pertinentes à partir d'un texte et d'un ensemble de croyances.",
                "execute_query": "Exécute une requête modale sur un ensemble de croyances.",
                "interpret_results": "Interprète les résultats d'une ou plusieurs requêtes modales.",
                "validate_formula": "Valide la syntaxe d'une formule modale."
            }
        }

    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Configure les composants spécifiques de l'agent de logique modale.

        Initialise `TweetyBridge` pour la logique modale et enregistre les fonctions
        sémantiques nécessaires (TextToModalBeliefSet, GenerateModalQueries,
        InterpretModalResults) dans le kernel Semantic Kernel.

        :param llm_service_id: L'ID du service LLM à utiliser pour les fonctions sémantiques.
        :type llm_service_id: str
        """
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants pour {self.name}...")

        self._tweety_bridge = TweetyBridge()

        if not self.tweety_bridge.is_jvm_ready():
            self.logger.error("Tentative de setup Modal Kernel alors que la JVM n'est PAS démarrée.")
            return
        
        default_settings = None
        if self._llm_service_id: 
            try:
                default_settings = self.sk_kernel.get_prompt_execution_settings_from_service_id(
                    self._llm_service_id
                )
                self.logger.debug(f"Settings LLM récupérés pour {self.name}.")
            except Exception as e:
                self.logger.warning(f"Impossible de récupérer settings LLM pour {self.name}: {e}")

        semantic_functions = [
            ("TextToModalBeliefSet", PROMPT_TEXT_TO_MODAL_BELIEF_SET,
             "Convertit le texte en ensemble de croyances modales."),
            ("GenerateModalQueryIdeas", PROMPT_GEN_MODAL_QUERIES_IDEAS,
             "Génère des idées de requêtes modales au format JSON."),
            ("InterpretModalResult", PROMPT_INTERPRET_MODAL,
             "Interprète résultat requête modale Tweety formaté.")
        ]

        for func_name, prompt, description in semantic_functions:
            try:
                if not prompt or not isinstance(prompt, str):
                    self.logger.error(f"ERREUR: Prompt invalide pour {self.name}.{func_name}")
                    continue
                
                self.logger.info(f"Ajout fonction {self.name}.{func_name} avec prompt de {len(prompt)} caractères")
                self.sk_kernel.add_function(
                    prompt=prompt,
                    plugin_name=self.name, 
                    function_name=func_name,
                    description=description,
                    prompt_execution_settings=default_settings
                )
                self.logger.debug(f"Fonction sémantique {self.name}.{func_name} ajoutée/mise à jour.")
                
                if self.name in self.sk_kernel.plugins and func_name in self.sk_kernel.plugins[self.name]:
                    self.logger.info(f"(OK) Fonction {self.name}.{func_name} correctement enregistrée.")
                else:
                    self.logger.error(f"(CRITICAL ERROR) Fonction {self.name}.{func_name} non trouvée après ajout!")
            except ValueError as ve:
                self.logger.warning(f"Problème ajout/MàJ {self.name}.{func_name}: {ve}")
            except Exception as e:
                self.logger.error(f"Exception inattendue lors de l'ajout de {self.name}.{func_name}: {e}", exc_info=True)
        
        self.logger.info(f"Composants de {self.name} configurés.")

    def _construct_modal_kb_from_json(self, kb_json: Dict[str, Any]) -> str:
        """
        Construit une base de connaissances modale textuelle à partir d'un JSON structuré,
        en respectant la syntaxe de TweetyProject pour la logique modale.
        """
        kb_parts = []

        # 1. Déclaration des propositions
        propositions = kb_json.get("propositions", [])
        if propositions:
            # En logique modale, les propositions peuvent être déclarées comme des variables propositionnelles
            prop_declarations = [f"prop({prop})" for prop in propositions]
            kb_parts.extend(prop_declarations)

        # 2. Formules modales
        modal_formulas = kb_json.get("modal_formulas", [])
        if modal_formulas:
            # Assurer que les formules sont bien séparées des déclarations
            if kb_parts:
                kb_parts.append("")
            kb_parts.extend(modal_formulas)

        return "\n".join(kb_parts)

    def _validate_modal_kb_json(self, kb_json: Dict[str, Any]) -> Tuple[bool, str]:
        """Valide la cohérence interne du JSON généré par le LLM pour la logique modale."""
        if not all(k in kb_json for k in ["propositions", "modal_formulas"]):
            return False, "Le JSON doit contenir les clés 'propositions' et 'modal_formulas'."

        declared_propositions = set(kb_json.get("propositions", []))
        
        # Vérifier que toutes les propositions utilisées dans les formules sont déclarées
        for formula in kb_json.get("modal_formulas", []):
            # Extraire les propositions utilisées (identifiants en minuscules)
            used_props = set(re.findall(r'\b[a-z_][a-z0-9_]*\b', formula))
            undeclared_props = used_props - declared_propositions
            if undeclared_props:
                return False, f"Propositions non déclarées utilisées dans '{formula}': {undeclared_props}"

        return True, "Validation du JSON modale réussie."

    def _extract_json_block(self, text: str) -> str:
        """Extrait le premier bloc JSON valide de la réponse du LLM."""
        start_index = text.find('{')
        end_index = text.rfind('}')
        if start_index != -1 and end_index != -1 and end_index > start_index:
            return text[start_index:end_index + 1]
        self.logger.warning("Impossible d'isoler un bloc JSON. Tentative de parsing de la chaîne complète.")
        return text

    async def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[BeliefSet], str]:
        """
        Convertit un texte en langage naturel en un ensemble de croyances modales.
        
        :param text: Le texte en langage naturel à convertir.
        :param context: Un dictionnaire optionnel de contexte (non utilisé actuellement).
        :return: Un tuple contenant l'objet `ModalBeliefSet` si la conversion réussit, 
                 et un message de statut.
        """
        self.logger.info(f"Conversion de texte en ensemble de croyances modales pour {self.name}...")
        
        max_retries = 3
        last_error = ""
        
        for attempt in range(max_retries):
            self.logger.info(f"Tentative de conversion {attempt + 1}/{max_retries}...")
            
            try:
                # Appel de la fonction sémantique pour générer l'ensemble de croyances modales
                result = await self.sk_kernel.plugins[self.name]["TextToModalBeliefSet"].invoke(
                    self.sk_kernel, input=text
                )
                
                # Extraire et parser le JSON
                json_str = self._extract_json_block(str(result))
                kb_json = json.loads(json_str)
                
                # Valider la cohérence du JSON
                is_valid, validation_msg = self._validate_modal_kb_json(kb_json)
                if not is_valid:
                    raise ValueError(f"JSON invalide: {validation_msg}")
                
                # Construire la base de connaissances modale
                belief_set_content = self._construct_modal_kb_from_json(kb_json)
                
                if not belief_set_content:
                    raise ValueError("La conversion a produit une base de connaissances vide.")

                # Valider avec Tweety (si le modal_handler supporte la validation)
                try:
                    # Note: adapter selon les méthodes disponibles dans modal_handler
                    is_valid, validation_msg = self.tweety_bridge.validate_modal_belief_set(belief_set_content)
                    if not is_valid:
                        raise ValueError(f"Ensemble de croyances invalide selon Tweety: {validation_msg}")
                except AttributeError:
                    # Si la méthode n'existe pas encore, on log un warning et on continue
                    self.logger.warning("Méthode validate_modal_belief_set non disponible, validation Tweety ignorée.")

                belief_set_obj = ModalBeliefSet(belief_set_content)
                self.logger.info("Conversion et validation réussies.")
                return belief_set_obj, "Conversion réussie"

            except (json.JSONDecodeError, ValueError, jpype.JException) as e:
                last_error = f"Erreur de conversion/validation: {e}"
                self.logger.warning(f"{last_error} à la tentative {attempt + 1}")
                
                if attempt == max_retries - 1:
                    break
                    
            except Exception as e:
                error_msg = f"Erreur inattendue lors de la conversion: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                return None, error_msg

        self.logger.error(f"Échec de la conversion après {max_retries} tentatives. Dernière erreur: {last_error}")
        return None, f"Échec de la conversion après {max_retries} tentatives. Dernière erreur: {last_error}"

    def _parse_modal_belief_set_content(self, belief_set_content: str) -> Dict[str, Any]:
        """
        Analyse le contenu textuel d'un belief set modal pour en extraire les propositions.
        """
        knowledge_base = {
            "propositions": set(),
            "modal_formulas": []
        }

        lines = belief_set_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Extraire les déclarations de propositions (format: prop(nom_prop))
            prop_match = re.match(r'prop\(([^)]+)\)', line)
            if prop_match:
                knowledge_base["propositions"].add(prop_match.group(1))
            else:
                # Traiter comme une formule modale
                if line and not line.startswith('prop('):
                    knowledge_base["modal_formulas"].append(line)
                    # Extraire les propositions utilisées dans la formule
                    used_props = re.findall(r'\b[a-z_][a-z0-9_]*\b', line)
                    knowledge_base["propositions"].update(used_props)

        return knowledge_base

    async def generate_queries(self, text: str, belief_set: BeliefSet, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Génère des requêtes modales valides en utilisant une approche de "Modèle de Requête".
        
        :param text: Le texte source.
        :param belief_set: L'ensemble de croyances modales associé.
        :param context: Contexte additionnel optionnel.
        :return: Une liste de requêtes modales valides.
        """
        self.logger.info(f"Génération de requêtes modales via le modèle de requête pour {self.name}...")
        response_text = ""
        
        try:
            # Étape 1: Extraire les informations de la base de connaissances
            kb_details = self._parse_modal_belief_set_content(belief_set.content)
            self.logger.debug(f"Détails de la KB extraits: {kb_details}")

            # Étape 2: Générer les idées de requêtes avec le LLM
            args = {
                "input": text,
                "belief_set": belief_set.content
            }
            
            result = await self.sk_kernel.plugins[self.name]["GenerateModalQueryIdeas"].invoke(
                self.sk_kernel, **args
            )
            response_text = str(result)
            
            # Extraire le bloc JSON de la réponse
            json_block = self._extract_json_block(response_text)
            if not json_block:
                self.logger.error("Aucun bloc JSON trouvé dans la réponse du LLM pour les idées de requêtes.")
                return []
                
            query_ideas_data = json.loads(json_block)
            query_ideas = query_ideas_data.get("query_ideas", [])

            if not query_ideas:
                self.logger.warning("Le LLM n'a généré aucune idée de requête.")
                return []

            self.logger.info(f"{len(query_ideas)} idées de requêtes reçues du LLM.")
            self.logger.debug(f"Idées de requêtes brutes reçues: {json.dumps(query_ideas, indent=2)}")

            # Étape 3: Assemblage et validation des requêtes
            valid_queries = []
            for idea in query_ideas:
                formula = idea.get("formula")

                # Validation 1: La formule est-elle une chaîne de caractères ?
                if not isinstance(formula, str):
                    self.logger.info(f"Idée de requête rejetée: 'formula' invalide (pas une chaîne) -> {formula}")
                    continue

                # Validation 2: Toutes les propositions utilisées existent-elles dans la KB ?
                used_props = set(re.findall(r'\b[a-z_][a-z0-9_]*\b', formula))
                invalid_props = used_props - kb_details["propositions"]
                if invalid_props:
                    self.logger.info(f"Idée de requête rejetée pour '{formula}': Propositions inconnues: {invalid_props}")
                    continue
                
                # Validation contextuelle avec Tweety (si disponible)
                try:
                    validation_result = self.tweety_bridge.validate_modal_query_with_context(belief_set.content, formula)
                    is_valid, validation_msg = validation_result if isinstance(validation_result, tuple) else (validation_result, "")
                    if is_valid:
                        self.logger.info(f"Idée validée et requête assemblée: {formula}")
                        valid_queries.append(formula)
                    else:
                        self.logger.info(f"Idée rejetée: La requête '{formula}' a échoué la validation de Tweety: {validation_msg}")
                except AttributeError:
                    # Si la méthode n'existe pas encore, on accepte la requête après validation basique
                    self.logger.warning("Méthode validate_modal_query_with_context non disponible, validation basique utilisée.")
                    valid_queries.append(formula)

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
        Exécute une requête logique modale sur un ensemble de croyances donné.

        :param belief_set: L'ensemble de croyances modales sur lequel exécuter la requête.
        :param query: La requête modale à exécuter.
        :return: Un tuple contenant le résultat booléen de la requête et la chaîne de résultat brute.
        """
        self.logger.info(f"Exécution de la requête modale: {query} pour l'agent {self.name}")
        
        try:
            bs_str = belief_set.content
            
            # Utiliser le modal_handler via TweetyBridge
            result_str = self.tweety_bridge.execute_modal_query(
                belief_set_content=bs_str,
                query_string=query
            )
            
            if result_str is None or "ERROR" in result_str.upper(): 
                self.logger.error(f"Erreur lors de l'exécution de la requête: {result_str}")
                return None, result_str if result_str else "Erreur inconnue de TweetyBridge"
            
            if "ACCEPTED" in result_str: 
                return True, result_str
            elif "REJECTED" in result_str:
                return False, result_str
            else:
                self.logger.warning(f"Résultat de requête inattendu: {result_str}")
                return None, result_str
        
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return None, f"FUNC_ERROR: {error_msg}" 

    async def interpret_results(self, text: str, belief_set: BeliefSet,
                         queries: List[str], results: List[Tuple[Optional[bool], str]],
                         context: Optional[Dict[str, Any]] = None) -> str:
        """
        Interprète les résultats d'une série de requêtes modales en langage naturel.

        :param text: Le texte original en langage naturel.
        :param belief_set: L'ensemble de croyances modales utilisé.
        :param queries: La liste des requêtes modales qui ont été exécutées.
        :param results: La liste des résultats correspondant à chaque requête.
        :param context: Un dictionnaire optionnel de contexte.
        :return: Une chaîne de caractères contenant l'interprétation en langage naturel.
        """
        self.logger.info(f"Interprétation des résultats pour l'agent {self.name}...")
        
        try:
            queries_str = "\n".join(queries)
            results_text_list = [res_tuple[1] if res_tuple else "Error: No result" for res_tuple in results]
            results_str = "\n".join(results_text_list)
            
            result = await self.sk_kernel.plugins[self.name]["InterpretModalResult"].invoke(
                self.sk_kernel,
                input=text,
                belief_set=belief_set.content,
                queries=queries_str,
                tweety_result=results_str
            )
            
            interpretation = str(result)
            self.logger.info("Interprétation terminée")
            return interpretation
        
        except Exception as e:
            error_msg = f"Erreur lors de l'interprétation des résultats: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return f"Erreur d'interprétation: {error_msg}"

    def validate_formula(self, formula: str) -> bool:
        """
        Valide la syntaxe d'une formule de logique modale.

        :param formula: La formule modale à valider.
        :return: `True` si la formule est syntaxiquement valide, `False` sinon.
        """
        self.logger.debug(f"Validation de la formule modale: {formula}")
        try:
            is_valid, message = self.tweety_bridge.validate_modal_formula(formula)
            if not is_valid:
                self.logger.warning(f"Formule modale invalide: {formula}. Message: {message}")
            return is_valid
        except AttributeError:
            # Si la méthode n'existe pas encore dans le bridge, on fait une validation basique
            self.logger.warning("Méthode validate_modal_formula non disponible, validation basique utilisée.")
            # Validation basique: vérifier que la formule contient des caractères valides
            return bool(re.match(r'^[a-zA-Z0-9_\[\]<>()!&|=><=\s]+$', formula))

    def is_consistent(self, belief_set: BeliefSet) -> Tuple[bool, str]:
        """
        Vérifie si un ensemble de croyances modales est cohérent.

        :param belief_set: L'ensemble de croyances à vérifier.
        :return: Un tuple (bool, str) indiquant la cohérence et un message.
        """
        self.logger.info(f"Vérification de la cohérence pour l'agent {self.name}")
        try:
            is_consistent, message = self.tweety_bridge.is_modal_kb_consistent(belief_set.content)
            if not is_consistent:
                self.logger.warning(f"Ensemble de croyances modales jugé incohérent par Tweety: {message}")
            return is_consistent, message
        except AttributeError:
            # Si la méthode n'existe pas encore, on retourne une réponse par défaut
            self.logger.warning("Méthode is_modal_kb_consistent non disponible, cohérence supposée vraie.")
            return True, "Vérification de cohérence non implémentée pour la logique modale"
        except Exception as e:
            error_msg = f"Erreur inattendue lors de la vérification de la cohérence modale: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> BeliefSet:
        """
        Crée un objet `ModalBeliefSet` à partir d'un dictionnaire de données.

        :param belief_set_data: Un dictionnaire contenant au moins la clé "content".
        :return: Une instance de `ModalBeliefSet`.
        """
        content = belief_set_data.get("content", "")
        return ModalBeliefSet(content)

    async def get_response(
        self,
        chat_history: ChatHistory,
        settings: Optional[Any] = None,
    ) -> AsyncGenerator[list[ChatMessageContent], None]:
        """
        Méthode abstraite de `Agent` pour obtenir une réponse.
        Non implémentée car cet agent utilise des méthodes spécifiques.
        """
        logger.warning("La méthode 'get_response' n'est pas implémentée pour ModalLogicAgent et ne devrait pas être appelée directement.")
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
        logger.warning("La méthode 'invoke' n'est pas implémentée pour ModalLogicAgent et ne devrait pas être appelée directement.")
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
        logger.warning("La méthode 'invoke_stream' n'est pas implémentée pour ModalLogicAgent et ne devrait pas être appelée directement.")
        yield []
        return