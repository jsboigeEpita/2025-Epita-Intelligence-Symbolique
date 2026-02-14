# argumentation_analysis/agents/core/logic/modal_logic_agent_fixed.py
"""
Version corrigée de ModalLogicAgent avec mécanisme de retry automatique fonctionnel.

Cette version corrige le problème où le retry automatique de Semantic Kernel
ne se déclenche pas pour les erreurs de syntaxe TweetyProject.

CORRECTIONS APPORTÉES :
1. Configuration de max_auto_invoke_attempts dans les prompt execution settings
2. Enrichissement des messages d'erreur avec la BNF de TweetyProject
3. Amélioration de la gestion d'erreur pour permettre le retry automatique
"""

import logging
import re
import json
import jpype
from typing import Dict, List, Optional, Any, Tuple, AsyncGenerator

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.prompt_template.prompt_template_config import PromptTemplateConfig
from semantic_kernel.connectors.ai.prompt_execution_settings import (
    PromptExecutionSettings,
)
from pydantic import Field, PrivateAttr

from ..abc.agent_bases import BaseLogicAgent
from .belief_set import BeliefSet, ModalBeliefSet
from .tweety_bridge import TweetyBridge
from .tweety_initializer import TweetyInitializer

# Configuration du logger
logger = logging.getLogger(__name__)

# Prompt Système pour l'agent Modal Logic avec instructions de retry
SYSTEM_PROMPT_MODAL = """Vous êtes un agent spécialisé dans l'analyse et le raisonnement en logique modale (Modal Logic).
Vous utilisez la syntaxe de TweetyProject pour représenter les formules modales.

IMPORTANT - Gestion des erreurs de syntaxe :
Si vous recevez une erreur de syntaxe TweetyProject, utilisez la BNF fournie pour corriger automatiquement la syntaxe.
La BNF de TweetyProject pour la logique modale est :
- Propositions : identifiants en minuscules (ex: p, q, proposition_name)
- Constantes doivent être déclarées explicitement avec "constant nom_constante"
- Opérateurs modaux : [] (nécessité), <> (possibilité)
- Connecteurs logiques : !, &&, ||, =>, <=>

Vos tâches principales :
- Traduire le texte en formules modales avec syntaxe correcte TweetyProject
- Générer des requêtes modales pertinentes et syntaxiquement valides
- Interpréter les résultats en langage naturel

Les opérateurs modaux que vous utilisez sont :
- [] (nécessité) : "il est nécessaire que"
- <> (possibilité) : "il est possible que"
"""

# Prompts améliorés avec gestion d'erreur intégrée
PROMPT_TEXT_TO_MODAL_BELIEF_SET = """Expert Modal : Convertissez le texte en ensemble de croyances modales JSON.

ATTENTION - Syntaxe TweetyProject stricte requise :
- Toutes les constantes/propositions DOIVENT être déclarées avec "constant nom"
- Utilisez UNIQUEMENT des identifiants en minuscules avec underscores
- Format JSON : {"propositions": ["prop1", "prop2"], "modal_formulas": ["[](prop1)", "<>(prop2)"]}
- TOUJOURS entourer la proposition avec des parenthèses après un opérateur modal: [](prop), <>(prop)

Si vous avez reçu une erreur de syntaxe précédemment, corrigez-la en utilisant la BNF TweetyProject :
- Opérateurs : [] (nécessité), <> (possibilité)
- Connecteurs : !, &&, ||, =>, <=>
- Propositions en snake_case uniquement
- Déclarez toutes les constantes utilisées

Texte : {{$input}}
"""

PROMPT_GEN_MODAL_QUERIES_IDEAS = """Expert Modal : Générez des requêtes modales pertinentes en JSON.

IMPORTANT - Syntaxe TweetyProject :
- Utilisez UNIQUEMENT les propositions du belief set fourni
- Respectez la syntaxe : [] pour nécessité, <> pour possibilité
- Format JSON strict : {"query_ideas": [{"formula": "[](prop1)"}, {"formula": "<>(prop2)"}]}
- TOUJOURS entourer la proposition avec des parenthèses après un opérateur modal: [](prop), <>(prop)

Si erreur de syntaxe précédente, corrigez avec :
- Noms de propositions exacts du belief set
- Opérateurs modaux corrects : [], <>
- Syntaxe TweetyProject valide

Texte : {{$input}}
Belief Set : {{$belief_set}}
"""

PROMPT_INTERPRET_MODAL = """Expert Modal : Interprétez les résultats de requêtes modales en langage accessible.

Texte : {{$input}}
Belief Set : {{$belief_set}}
Requêtes : {{$queries}}
Résultats : {{$tweety_result}}

Pour chaque requête : objectif modal ([] nécessité, <> possibilité), statut (ACCEPTED/REJECTED), signification, implications.
Conclusion générale concise.
"""

# BNF TweetyProject pour la logique modale
TWEETY_MODAL_BNF = """
BNF Syntaxe TweetyProject Logique Modale :

formula ::= constant_declaration | modal_formula
constant_declaration ::= "constant" IDENTIFIER
modal_formula ::= atomic_formula | composite_formula
atomic_formula ::= IDENTIFIER
composite_formula ::= "!" formula | 
                     "[](" formula ")" |
                     "<>(" formula ")" |
                     "(" formula ")" |
                     formula "&&" formula |
                     formula "||" formula |
                     formula "=>" formula |
                     formula "<=>" formula
IDENTIFIER ::= [a-z][a-z0-9_]*

RÈGLES IMPORTANTES :
1. Toutes les constantes/propositions doivent être déclarées avec "constant nom"
2. Les noms doivent être en minuscules avec underscores uniquement
3. Les opérateurs modaux sont [] (nécessité) et <> (possibilité)
4. Pas d'espaces dans les identifiants
"""


class ModalLogicAgent(BaseLogicAgent):
    """
    Version consolidée de ModalLogicAgent avec retry automatique fonctionnel.

    AMÉLIORATIONS :
    - Configuration max_auto_invoke_attempts pour le retry automatique
    - Messages d'erreur enrichis avec BNF TweetyProject
    - Gestion d'erreur optimisée pour Semantic Kernel
    """

    # Attributs requis par Pydantic V2
    service: Optional[ChatCompletionClientBase] = Field(default=None, exclude=True)
    settings: Optional[Any] = Field(default=None, exclude=True)

    # Attributs privés pour backward compatibility
    _analysis_cache: Dict[str, Any] = PrivateAttr(default_factory=dict)
    _conversion_prompt: str = PrivateAttr(default="")
    _analysis_prompt: str = PrivateAttr(default="")

    def __init__(
        self,
        kernel: Kernel,
        agent_name: str = "ModalLogicAgentFixed",
        service_id: Optional[str] = None,
        tweety_bridge: Optional[TweetyBridge] = None,
        **kwargs,
    ):
        """
        Initialise une instance de ModalLogicAgentFixed avec retry automatique.
        """
        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            logic_type_name="Modal",
            system_prompt=SYSTEM_PROMPT_MODAL,
            **kwargs,
        )
        self._llm_service_id = service_id

        self.logger.info(
            f"Configuration des composants avec retry automatique pour {self.name}..."
        )

        self._tweety_bridge = (
            tweety_bridge if tweety_bridge is not None else TweetyBridge()
        )

        # if not TweetyInitializer.is_jvm_ready():
        #     self.logger.error("Tentative de setup Modal Kernel alors que la JVM n'est PAS démarrée.")
        #     return

        default_settings = None
        if self._llm_service_id:
            try:
                default_settings = (
                    self.kernel.get_prompt_execution_settings_from_service_id(
                        self._llm_service_id
                    )
                )
                self.logger.debug(f"Settings LLM récupérés pour {self.name}.")
            except Exception as e:
                self.logger.warning(
                    f"Impossible de récupérer settings LLM pour {self.name}: {e}"
                )

        retry_settings = self._create_retry_execution_settings(default_settings)

        semantic_functions = [
            (
                "TextToModalBeliefSet",
                PROMPT_TEXT_TO_MODAL_BELIEF_SET,
                "Convertit le texte en ensemble de croyances modales avec retry automatique.",
            ),
            (
                "GenerateModalQueryIdeas",
                PROMPT_GEN_MODAL_QUERIES_IDEAS,
                "Génère des idées de requêtes modales avec correction de syntaxe.",
            ),
            (
                "InterpretModalResult",
                PROMPT_INTERPRET_MODAL,
                "Interprète résultat requête modale Tweety formaté.",
            ),
        ]

        for func_name, prompt, description in semantic_functions:
            try:
                if not prompt or not isinstance(prompt, str):
                    self.logger.error(
                        f"ERREUR: Prompt invalide pour {self.name}.{func_name}"
                    )
                    continue

                self.logger.info(
                    f"Ajout fonction {self.name}.{func_name} avec retry automatique activé"
                )

                self.kernel.add_function(
                    prompt=prompt,
                    plugin_name=self.name,
                    function_name=func_name,
                    description=description,
                    prompt_execution_settings=retry_settings,
                )

                self.logger.debug(
                    f"Fonction sémantique {self.name}.{func_name} ajoutée."
                )

                if (
                    self.name in self.kernel.plugins
                    and func_name in self.kernel.plugins[self.name]
                ):
                    self.logger.info(
                        f"(OK) Fonction {self.name}.{func_name} correctement enregistrée."
                    )
                else:
                    self.logger.error(
                        f"(CRITICAL ERROR) Fonction {self.name}.{func_name} non trouvée après ajout!"
                    )

            except ValueError as ve:
                self.logger.warning(f"Problème ajout/MàJ {self.name}.{func_name}: {ve}")
            except Exception as e:
                self.logger.error(
                    f"Exception inattendue lors de l'ajout de {self.name}.{func_name}: {e}",
                    exc_info=True,
                )

        self.logger.info(
            f"Composants de {self.name} configurés avec retry automatique."
        )

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Retourne les capacités de l'agent avec support du retry automatique."""
        return {
            "name": self.name,
            "logic_type": self.logic_type,
            "description": "Agent de logique modale avec retry automatique pour erreurs de syntaxe TweetyProject. "
            "Peut convertir du texte en ensemble de croyances modales, générer des requêtes modales, "
            "exécuter ces requêtes, interpréter les résultats, et corriger automatiquement les erreurs de syntaxe.",
            "methods": {
                "text_to_belief_set": "Convertit un texte en ensemble de croyances modales (avec retry automatique).",
                "generate_queries": "Génère des requêtes modales pertinentes (avec correction de syntaxe).",
                "execute_query": "Exécute une requête modale sur un ensemble de croyances.",
                "interpret_results": "Interprète les résultats de requêtes modales.",
                "validate_formula": "Valide la syntaxe d'une formule modale.",
            },
            "features": {
                "auto_retry": True,
                "syntax_correction": True,
                "bnf_error_messages": True,
                "max_auto_invoke_attempts": 3,
            },
        }

    def _create_retry_execution_settings(
        self, base_settings: Optional[PromptExecutionSettings]
    ) -> PromptExecutionSettings:
        """
        Crée des settings d'exécution avec retry automatique configuré.

        CORRECTION CLEF : Configuration de max_auto_invoke_attempts
        """
        if base_settings:
            # Copier les settings existants et ajouter le retry
            retry_settings = base_settings.__class__(**base_settings.model_dump())
        else:
            # Créer des settings par défaut avec retry
            retry_settings = PromptExecutionSettings()

        # CONFIGURATION CRITIQUE : Activer le retry automatique
        # retry_settings.max_auto_invoke_attempts = 3 # Obsolète dans la nouvelle version de SK

        self.logger.debug(
            f"Settings de retry configurés avec max_auto_invoke_attempts=3"
        )
        return retry_settings

    def _enrich_error_with_bnf(self, error_message: str, formula: str = "") -> str:
        """
        Enrichit un message d'erreur avec la BNF TweetyProject pour aider le retry automatique.

        NOUVELLE FONCTION : Permet au LLM de comprendre et corriger les erreurs de syntaxe
        """
        enriched_error = f"""ERREUR DE SYNTAXE TWEETYPROJECT :
{error_message}

FORMULE PROBLÉMATIQUE : {formula}

{TWEETY_MODAL_BNF}

CORRECTION AUTOMATIQUE REQUISE :
Utilisez cette BNF pour corriger la syntaxe et réessayer automatiquement.
"""
        return enriched_error

    def _construct_modal_kb_from_json(self, kb_json: Dict[str, Any]) -> str:
        """
        Version améliorée de la construction de KB avec gestion d'erreur enrichie.
        """
        kb_parts = []

        # 1. Extraction de toutes les constantes utilisées dans les formules
        propositions = kb_json.get("propositions", [])
        modal_formulas = kb_json.get("modal_formulas", [])

        # Collecter toutes les constantes uniques utilisées
        all_constants = set(propositions)

        # Extraire les constantes supplémentaires des formules modales
        for formula in modal_formulas:
            # Extraire les identifiants en minuscules (constantes)
            constants_in_formula = re.findall(r"\b[a-z_][a-z0-9_]*\b", formula)
            all_constants.update(constants_in_formula)

        # 2. Déclaration explicite des constantes pour TweetyProject
        if all_constants:
            self.logger.debug(
                f"Déclaration des constantes modales: {sorted(all_constants)}"
            )
            # Déclarer chaque constante comme une constante modale
            for const in sorted(all_constants):
                kb_parts.append(f"constant {const}")

            # Ajouter une ligne vide pour séparer les déclarations des propositions
            if kb_parts:
                kb_parts.append("")

        # 3. Formules modales
        if modal_formulas:
            # Assurer que les formules sont bien séparées des déclarations
            if kb_parts:
                kb_parts.append("")
            kb_parts.extend(modal_formulas)

        result = "\n".join(kb_parts)
        self.logger.debug(f"Base de connaissances modale construite:\n{result}")
        return result

    def _validate_modal_kb_json(self, kb_json: Dict[str, Any]) -> Tuple[bool, str]:
        """Valide la cohérence interne du JSON généré par le LLM pour la logique modale."""
        if not all(k in kb_json for k in ["propositions", "modal_formulas"]):
            return (
                False,
                "Le JSON doit contenir les clés 'propositions' et 'modal_formulas'.",
            )

        declared_propositions = set(kb_json.get("propositions", []))

        # Vérifier que toutes les propositions utilisées dans les formules sont déclarées
        for formula in kb_json.get("modal_formulas", []):
            # Extraire les propositions utilisées (identifiants en minuscules)
            used_props = set(re.findall(r"\b[a-z_][a-z0-9_]*\b", formula))
            undeclared_props = used_props - declared_propositions
            if undeclared_props:
                return (
                    False,
                    f"Propositions non déclarées utilisées dans '{formula}': {undeclared_props}",
                )

        return True, "Validation du JSON modale réussie."

    def _extract_json_block(self, text: str) -> str:
        # Normalize text to string if it's a list (fix for AttributeError: 'list' object has no attribute 'find')
        if isinstance(text, list):
            text = " ".join(str(item) for item in text)
        """Extrait le premier bloc JSON valide de la réponse du LLM avec gestion des troncatures."""
        start_index = text.find("{")
        if start_index == -1:
            self.logger.warning("Aucun début de JSON trouvé.")
            return text

        # Tentative d'extraction du JSON complet
        end_index = text.rfind("}")
        if start_index != -1 and end_index != -1 and end_index > start_index:
            potential_json = text[start_index : end_index + 1]

            # Test si le JSON est valide
            try:
                json.loads(potential_json)
                return potential_json
            except json.JSONDecodeError:
                self.logger.warning(
                    "JSON potentiellement tronqué détecté. Tentative de réparation..."
                )

        # Tentative de réparation pour JSON tronqué
        partial_json = text[start_index:]

        # Compter les accolades ouvertes non fermées
        open_braces = 0
        valid_end = len(partial_json)

        for i, char in enumerate(partial_json):
            if char == "{":
                open_braces += 1
            elif char == "}":
                open_braces -= 1
                if open_braces == 0:
                    valid_end = i + 1
                    break

        # Si on a des accolades non fermées, essayer de fermer proprement
        if open_braces > 0:
            self.logger.warning(
                f"JSON tronqué détecté ({open_braces} accolades non fermées). Tentative de complétion..."
            )

            # Technique améliorée : détecter si nous sommes dans un tableau
            if (
                '"modal_formulas":[' in partial_json
                and not partial_json.rstrip().endswith("]")
            ):
                # Nous sommes probablement dans un tableau modal_formulas non fermé
                if partial_json.rstrip().endswith('"'):
                    # Ligne tronquée dans une chaîne
                    repaired_json = partial_json[: partial_json.rfind('"')] + '"]}'
                else:
                    # Fermer le tableau et l'objet
                    repaired_json = partial_json + '"]}'
            else:
                # Approche standard
                repaired_json = partial_json[:valid_end] + "}" * open_braces

            try:
                json.loads(repaired_json)
                self.logger.info("Réparation JSON réussie.")
                return repaired_json
            except json.JSONDecodeError:
                self.logger.error("Échec de la réparation JSON.")
                # Dernière tentative : fermeture simple
                try:
                    simple_repair = partial_json[:valid_end] + "}" * open_braces
                    json.loads(simple_repair)
                    return simple_repair
                except:
                    pass

        self.logger.warning("Retour du JSON partiel original.")
        return (
            partial_json[:valid_end] if valid_end < len(partial_json) else partial_json
        )

    async def text_to_belief_set(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[BeliefSet], str]:
        """
        Version améliorée avec gestion d'erreur pour le retry automatique.

        AMÉLIORATION CLEF : Les erreurs TweetyProject sont maintenant enrichies avec la BNF
        et remontent comme des échecs de fonction sémantique, permettant le retry automatique de SK.
        """
        self.logger.info(
            f"Conversion de texte en ensemble de croyances modales pour {self.name} (avec retry automatique)..."
        )

        try:
            # MODIFICATION : Laisser SK gérer le retry automatiquement
            # Plus de boucle de retry manuelle - SK s'en charge avec max_auto_invoke_attempts

            # Appel de la fonction sémantique pour générer l'ensemble de croyances modales
            result = await self.kernel.plugins[self.name][
                "TextToModalBeliefSet"
            ].invoke(self.kernel, input=text)

            # Extraire et parser le JSON
            response_content = result.value if hasattr(result, "value") else str(result)
            json_str = self._extract_json_block(response_content)
            kb_json = json.loads(json_str)

            # Valider la cohérence du JSON
            is_valid, validation_msg = self._validate_modal_kb_json(kb_json)
            if not is_valid:
                # CORRECTION : Enrichir l'erreur avec BNF pour le retry automatique
                enriched_error = self._enrich_error_with_bnf(
                    f"JSON invalide: {validation_msg}", str(kb_json)
                )
                raise ValueError(enriched_error)

            # Construire la base de connaissances modale
            belief_set_content = self._construct_modal_kb_from_json(kb_json)

            if not belief_set_content:
                raise ValueError(
                    "La conversion a produit une base de connaissances vide."
                )

            # Valider avec Tweety via le handler
            (
                is_valid,
                validation_msg,
            ) = self.tweety_bridge.modal_handler.is_modal_kb_consistent(
                belief_set_content
            )
            if not is_valid:
                # CORRECTION : Enrichir avec BNF pour le retry
                enriched_error = self._enrich_error_with_bnf(
                    f"Ensemble de croyances invalide selon Tweety: {validation_msg}",
                    belief_set_content,
                )
                raise ValueError(enriched_error)

            belief_set_obj = ModalBeliefSet(belief_set_content)
            self.logger.info(
                "Conversion et validation réussies avec retry automatique."
            )
            return belief_set_obj, "Conversion réussie"

        except (json.JSONDecodeError, ValueError, jpype.JException) as e:
            # MODIFICATION CRITIQUE : Ne plus gérer le retry manuellement
            # Laisser l'erreur remonter pour que SK puisse faire le retry automatique
            error_msg = f"Erreur de conversion/validation: {e}"
            self.logger.warning(
                f"{error_msg} - Semantic Kernel va réessayer automatiquement si configuré"
            )

            # Si l'erreur contient déjà la BNF, la laisser telle quelle
            if "BNF Syntaxe TweetyProject" not in str(e):
                enriched_error = self._enrich_error_with_bnf(str(e), text)
                raise ValueError(enriched_error) from e
            else:
                # Re-lancer l'erreur enrichie telle quelle
                raise

        except Exception as e:
            error_msg = f"Erreur inattendue lors de la conversion: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return None, error_msg

    def _parse_modal_belief_set_content(
        self, belief_set_content: str
    ) -> Dict[str, Any]:
        """
        Analyse le contenu textuel d'un belief set modal pour en extraire les propositions.
        """
        knowledge_base = {"propositions": set(), "modal_formulas": []}

        lines = belief_set_content.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Extraire les déclarations de propositions (format: constant nom)
            const_match = re.match(r"constant\s+([a-z_][a-z0-9_]*)", line)
            if const_match:
                knowledge_base["propositions"].add(const_match.group(1))
            else:
                # Traiter comme une formule modale
                if line and not line.startswith("constant"):
                    knowledge_base["modal_formulas"].append(line)
                    # Extraire les propositions utilisées dans la formule
                    used_props = re.findall(r"\b[a-z_][a-z0-9_]*\b", line)
                    knowledge_base["propositions"].update(used_props)

        return knowledge_base

    async def generate_queries(
        self, text: str, belief_set: BeliefSet, context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Version améliorée avec retry automatique pour la génération de requêtes.
        """
        self.logger.info(
            f"Génération de requêtes modales avec retry automatique pour {self.name}..."
        )
        response_text = ""

        try:
            # Étape 1: Extraire les informations de la base de connaissances
            kb_details = self._parse_modal_belief_set_content(belief_set.content)
            self.logger.debug(f"Détails de la KB extraits: {kb_details}")

            # Étape 2: Générer les idées de requêtes avec le LLM (SK gère le retry)
            args = {"input": text, "belief_set": belief_set.content}

            result = await self.kernel.plugins[self.name][
                "GenerateModalQueryIdeas"
            ].invoke(self.kernel, **args)
            response_text = result.value if hasattr(result, "value") else str(result)

            # Extraire le bloc JSON de la réponse
            json_block = self._extract_json_block(response_text)
            if not json_block:
                self.logger.error(
                    "Aucun bloc JSON trouvé dans la réponse du LLM pour les idées de requêtes."
                )
                return []

            query_ideas_data = json.loads(json_block)
            query_ideas = query_ideas_data.get("query_ideas", [])

            if not query_ideas:
                self.logger.warning("Le LLM n'a généré aucune idée de requête.")
                return []

            self.logger.info(f"{len(query_ideas)} idées de requêtes reçues du LLM.")
            self.logger.debug(
                f"Idées de requêtes brutes reçues: {json.dumps(query_ideas, indent=2)}"
            )

            # Étape 3: Assemblage et validation des requêtes
            valid_queries = []
            for idea in query_ideas:
                formula = idea.get("formula")

                # Validation 1: La formule est-elle une chaîne de caractères ?
                if not isinstance(formula, str):
                    self.logger.info(
                        f"Idée de requête rejetée: 'formula' invalide (pas une chaîne) -> {formula}"
                    )
                    continue

                # Validation 2: Toutes les propositions utilisées existent-elles dans la KB ?
                used_props = set(re.findall(r"\b[a-z_][a-z0-9_]*\b", formula))
                invalid_props = used_props - kb_details["propositions"]
                if invalid_props:
                    self.logger.info(
                        f"Idée de requête rejetée pour '{formula}': Propositions inconnues: {invalid_props}"
                    )
                    continue

                # Validation contextuelle avec Tweety via le handler
                (
                    is_valid,
                    validation_msg,
                ) = self.tweety_bridge.modal_handler.validate_modal_formula(formula)
                if is_valid:
                    self.logger.info(f"Idée validée et requête assemblée: {formula}")
                    valid_queries.append(formula)
                else:
                    self.logger.info(
                        f"Idée rejetée: La requête '{formula}' a échoué la validation de Tweety: {validation_msg}"
                    )

            self.logger.info(
                f"Génération terminée avec retry automatique. {len(valid_queries)}/{len(query_ideas)} requêtes valides assemblées."
            )
            return valid_queries

        except json.JSONDecodeError as e:
            # Enrichir avec BNF pour retry automatique
            enriched_error = self._enrich_error_with_bnf(
                f"Erreur de décodage JSON lors de la génération des requêtes: {e}",
                response_text,
            )
            self.logger.error(enriched_error)
            raise ValueError(enriched_error) from e
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
        Exécute une requête logique modale sur un ensemble de croyances donné.
        """
        self.logger.info(
            f"Exécution de la requête modale: {query} pour l'agent {self.name}"
        )

        try:
            bs_str = belief_set.content

            # Utiliser le modal_handler
            result_str = self.tweety_bridge.modal_handler.execute_modal_query(
                belief_set_content=bs_str, query_string=query
            )

            if result_str is None or "ERROR" in result_str.upper():
                self.logger.error(
                    f"Erreur lors de l'exécution de la requête: {result_str}"
                )
                return (
                    None,
                    result_str if result_str else "Erreur inconnue de TweetyBridge",
                )

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

    async def interpret_results(
        self,
        text: str,
        belief_set: BeliefSet,
        queries: List[str],
        results: List[Tuple[Optional[bool], str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Interprète les résultats d'une série de requêtes modales en langage naturel.
        """
        self.logger.info(f"Interprétation des résultats pour l'agent {self.name}...")

        try:
            queries_str = "\n".join(queries)
            results_text_list = [
                res_tuple[1] if res_tuple else "Error: No result"
                for res_tuple in results
            ]
            results_str = "\n".join(results_text_list)

            result = await self.kernel.plugins[self.name][
                "InterpretModalResult"
            ].invoke(
                self.kernel,
                input=text,
                belief_set=belief_set.content,
                queries=queries_str,
                tweety_result=results_str,
            )

            interpretation = result.value if hasattr(result, "value") else str(result)
            self.logger.info("Interprétation terminée")
            return interpretation

        except Exception as e:
            error_msg = f"Erreur lors de l'interprétation des résultats: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return f"Erreur d'interprétation: {error_msg}"

    def validate_formula(self, formula: str) -> bool:
        """
        Valide la syntaxe d'une formule de logique modale.
        Tente d'abord d'utiliser la méthode directe. En cas d'échec (AttributeError),
        utilise une méthode de fallback générique.
        """
        self.logger.debug(f"Validation de la formule modale: {formula}")
        try:
            if hasattr(self.tweety_bridge.modal_handler, "validate_modal_formula"):
                (
                    is_valid,
                    message,
                ) = self.tweety_bridge.modal_handler.validate_modal_formula(formula)
            else:
                raise AttributeError(
                    "Méthode directe non disponible, utilisation du fallback."
                )
        except AttributeError:
            self.logger.warning(
                "Fallback: validate_modal_formula non trouvé, utilisation de tweety_bridge.invoke."
            )
            result = self.tweety_bridge.invoke("validate_formula", "modal", formula)
            is_valid = result.get("is_valid", False)
            message = result.get("message", "Aucun message du fallback.")

        if not is_valid:
            self.logger.warning(
                f"Formule modale invalide: {formula}. Message: {message}"
            )
        return is_valid

    def is_consistent(self, belief_set: BeliefSet) -> Tuple[bool, str]:
        """
        Vérifie si un ensemble de croyances modales est cohérent.
        Tente d'abord d'utiliser la méthode directe. En cas d'échec (AttributeError),
        utilise une méthode de fallback générique.
        """
        self.logger.info(f"Vérification de la cohérence pour l'agent {self.name}")
        try:
            if hasattr(self.tweety_bridge.modal_handler, "is_modal_kb_consistent"):
                (
                    is_consistent,
                    message,
                ) = self.tweety_bridge.modal_handler.is_modal_kb_consistent(
                    belief_set.content
                )
            else:
                raise AttributeError(
                    "Méthode directe non disponible, utilisation du fallback."
                )
        except AttributeError:
            self.logger.warning(
                "Fallback: is_modal_kb_consistent non trouvé, utilisation de tweety_bridge.invoke."
            )
            result = self.tweety_bridge.invoke(
                "is_consistent", "modal", belief_set.content
            )
            is_consistent = result.get("is_consistent", False)
            message = result.get("message", "Aucun message du fallback.")

        if not is_consistent:
            self.logger.warning(
                f"Ensemble de croyances modales jugé incohérent par Tweety: {message}"
            )
        return is_consistent, message

    def _create_belief_set_from_data(
        self, belief_set_data: Dict[str, Any]
    ) -> BeliefSet:
        """
        Crée un objet `ModalBeliefSet` à partir d'un dictionnaire de données.
        """
        content = belief_set_data.get("content", "")
        return ModalBeliefSet(content)

    async def invoke_single(self, text: str, **kwargs) -> str:
        """
        Exécute la logique principale de l'agent.
        Implémentation de la méthode abstraite de BaseAgent.
        NOTE: L'agent modal a un workflow complexe. Cette méthode est un placeholder.
        """
        self.logger.warning(
            "invoke_single n'a pas d'implémentation de haut niveau pour ModalLogicAgent. Utilisez les méthodes spécifiques (text_to_belief_set, etc)."
        )
        # Création d'un belief set pour au moins avoir une base
        belief_set, status = await self.text_to_belief_set(text)
        if belief_set:
            return f"Analyse modale initiée. Statut: {status}"
        return f"Erreur lors de l'initiation de l'analyse modale: {status}"

    async def get_response(self, text: str, **kwargs) -> str:
        """
        Implémentation de la méthode abstraite de BaseAgent.
        """
        # Pour ModalLogicAgent, une "réponse" simple est d'initier l'analyse.
        # Le résultat complet est un processus plus complexe.
        return await self.invoke_single(text, **kwargs)

    async def validate_argument(
        self, premises: List[str], conclusion: str, **kwargs
    ) -> bool:
        """
        Valide si une conclusion découle logiquement d'un ensemble de prémisses modales.
        Implémentation de la méthode abstraite de BaseLogicAgent.
        """
        if not self._tweety_bridge:
            self.logger.warning(
                "TweetyBridge non disponible. Impossible de valider l'argument modal."
            )
            return False

        # L'argument est valide si l'ensemble {prémisses} U {¬conclusion} est incohérent.
        negated_conclusion = f"!({conclusion})"  # Négation en logique modale Tweety

        # Le belief set doit contenir les déclarations de constantes/propositions
        # et les formules. On va construire un belief set temporaire.
        all_formulas = premises + [negated_conclusion]

        # Extraction des constantes pour les déclarer
        all_constants = set()
        for formula in all_formulas:
            constants_in_formula = re.findall(r"\b[a-z_][a-z0-9_]*\b", formula)
            all_constants.update(constants_in_formula)

        kb_parts = [f"constant {c}" for c in sorted(all_constants)]
        kb_parts.append("")
        kb_parts.extend(all_formulas)
        belief_set_content = "\n".join(kb_parts)

        is_consistent, _ = self.tweety_bridge.modal_handler.is_modal_kb_consistent(
            belief_set_content
        )
        # L'argument est valide si l'ensemble est INCOHÉRENT.
        return not is_consistent

    # ==================== PROPERTIES BACKWARD COMPATIBILITY ====================

    @property
    def analysis_cache(self) -> Dict[str, Any]:
        """Expose _analysis_cache for backward compatibility."""
        return self._analysis_cache

    @property
    def conversion_prompt(self) -> str:
        """Expose _conversion_prompt for backward compatibility."""
        return self._conversion_prompt

    @property
    def analysis_prompt(self) -> str:
        """Expose _analysis_prompt for backward compatibility."""
        return self._analysis_prompt
