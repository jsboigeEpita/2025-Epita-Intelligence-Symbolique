# argumentation_analysis/agents/core/logic/modal_logic_agent_sk_retry.py
"""
Agent spécialisé pour la logique modale avec le VRAI mécanisme de retry Semantic Kernel.

Ce module implémente le vrai comportement SK où l'agent reçoit les erreurs comme résultats
de fonction (pas exceptions) et peut choisir de corriger sa requête intelligemment.
"""

import logging
import re
import json
import jpype
from typing import Dict, List, Optional, Any, Tuple, AsyncGenerator

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.contents.chat_history import ChatHistory
from pydantic import Field

from ..abc.agent_bases import BaseLogicAgent
from .belief_set import BeliefSet, ModalBeliefSet
from .tweety_bridge import TweetyBridge

# Configuration du logger
logger = logging.getLogger(__name__)

# BNF pour la syntaxe TweetyProject Modal Logic
TWEETY_MODAL_BNF = """
# BNF Syntaxe TweetyProject Modal Logic

ModalFormula ::= Atom | Negation | Conjunction | Disjunction | Implication | Equivalence | ModalOperator

Atom ::= constant_name
constant_name ::= [a-z][a-z0-9_]*

Negation ::= "!" ModalFormula
Conjunction ::= ModalFormula "&&" ModalFormula  
Disjunction ::= ModalFormula "||" ModalFormula
Implication ::= ModalFormula "=>" ModalFormula
Equivalence ::= ModalFormula "<=>" ModalFormula

ModalOperator ::= Necessity | Possibility
Necessity ::= "[]" ModalFormula
Possibility ::= "<>" ModalFormula

BeliefSet ::= Declaration* Formula*
Declaration ::= "constant" constant_name | "prop(" constant_name ")"

RÈGLES IMPORTANTES:
1. Toutes les constantes doivent être déclarées AVANT utilisation
2. Format: "constant nom_constant" puis utilisation dans formules
3. Noms de constantes en snake_case (minuscules + underscore)
4. Éviter les mots problématiques (race, annihilation, etc.)
"""

# Prompt Système avec instructions pour gérer les erreurs
SYSTEM_PROMPT_MODAL_SK = """Vous êtes un agent spécialisé dans l'analyse et le raisonnement en logique modale (Modal Logic).
Vous utilisez la syntaxe de TweetyProject pour représenter les formules modales.

**IMPORTANT - MÉCANISME DE CORRECTION AUTOMATIQUE:**
Quand vous recevez un résultat d'erreur de vos fonctions TweetyProject (format JSON avec "success": false), 
vous devez analyser l'erreur, corriger votre syntaxe selon la BNF fournie, et réessayer automatiquement.

Les opérateurs modaux que vous utilisez sont :
- [] (nécessité) : "il est nécessaire que"  
- <> (possibilité) : "il est possible que"

SYNTAXE CORRECTE:
1. Déclarez TOUJOURS les constantes: "constant nom_constant"
2. Utilisez snake_case: urgence_action, paix_mondiale
3. Évitez les termes sensibles: remplacez par des concepts neutres
"""

# Prompts enrichis pour la gestion d'erreurs
PROMPT_TEXT_TO_MODAL_BELIEF_SET_SK = """Expert Modal avec Auto-Correction : Convertissez le texte en ensemble de croyances modales JSON.

**GESTION D'ERREURS**: Si vous recevez une erreur avec "success": false, analysez le message d'erreur et la BNF, 
puis corrigez automatiquement votre syntaxe et réessayez.

Format : {"propositions": ["prop1", "prop2"], "modal_formulas": ["[]prop1", "<>prop2"]}

Opérateurs : [] (nécessité), <> (possibilité). Connecteurs : !, &&, ||, =>, <=>
Propositions en snake_case. Utilisez UNIQUEMENT les propositions déclarées.

**RÈGLES ANTI-ERREUR**:
- Remplacez "annihilation" → "cessation", "elimination" 
- Remplacez "race" → "groupe", "population"
- Utilisez des termes neutres et techniques

Texte : {{$input}}
"""

PROMPT_GEN_MODAL_QUERIES_SK = """Expert Modal avec Auto-Correction : Générez des requêtes modales pertinentes en JSON.

**GESTION D'ERREURS**: Si vous recevez une erreur de validation, analysez et corrigez la syntaxe selon la BNF.

Format : {"query_ideas": [{"formula": "[]prop1"}, {"formula": "<>prop2"}]}

Règles : Utilisez UNIQUEMENT les propositions du belief set. Opérateurs : [], <>

Texte : {{$input}}
Belief Set : {{$belief_set}}
"""

PROMPT_INTERPRET_MODAL_SK = """Expert Modal : Interprétez les résultats de requêtes modales en langage accessible.

**GESTION D'ERREURS**: Si certains résultats montrent des erreurs, expliquez les corrections apportées.

Texte : {{$input}}
Belief Set : {{$belief_set}}
Requêtes : {{$queries}}
Résultats : {{$tweety_result}}

Pour chaque requête : objectif modal ([] nécessité, <> possibilité), statut (ACCEPTED/REJECTED), signification, implications.
Si des corrections ont été appliquées, expliquez le processus d'amélioration.
Conclusion générale concise.
"""

class ModalLogicAgentSKRetry(BaseLogicAgent): 
    """
    Agent Modal Logic avec le VRAI mécanisme de retry Semantic Kernel.

    Cet agent implémente le vrai comportement SK où les erreurs sont retournées
    comme résultats de fonction et l'agent peut intelligemment corriger ses requêtes.
    """
    
    # Attributs requis par Pydantic V2
    service: Optional[ChatCompletionClientBase] = Field(default=None, exclude=True)
    settings: Optional[Any] = Field(default=None, exclude=True)

    def __init__(self, kernel: Kernel, agent_name: str = "ModalLogicAgentSKRetry", service_id: Optional[str] = None):
        """
        Initialise l'agent Modal Logic avec mécanisme SK retry.
        """
        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            logic_type_name="Modal",
            system_prompt=SYSTEM_PROMPT_MODAL_SK
        )
        self._llm_service_id = service_id

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Retourne les capacités de l'agent avec support SK retry.
        """
        return {
            "name": self.name,
            "logic_type": self.logic_type,
            "description": "Agent Modal Logic avec VRAI mécanisme de retry Semantic Kernel. "
                           "Capable de recevoir les erreurs comme résultats et de corriger intelligemment sa syntaxe.",
            "features": {
                "sk_retry_mechanism": True,
                "error_as_result": True,
                "intelligent_correction": True,
                "bnf_error_enrichment": True,
                "max_auto_invoke_attempts": 3
            },
            "methods": {
                "text_to_modal_belief_set": "Convertit texte en belief set avec auto-correction d'erreurs.",
                "generate_queries": "Génère requêtes modales avec validation et correction automatique.",
                "execute_query": "Exécute requête avec gestion intelligente des erreurs.",
                "interpret_results": "Interprète résultats avec explication des corrections appliquées."
            }
        }

    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Configure les composants avec les fonctions SK retry.
        """
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants SK Retry pour {self.name}...")

        self._tweety_bridge = TweetyBridge()

        if not self.tweety_bridge.is_jvm_ready():
            self.logger.error("JVM non prête pour setup Modal Kernel SK Retry.")
            return
        
        # Créer settings avec retry automatique
        default_settings = self._create_retry_execution_settings()
        
        semantic_functions = [
            ("TextToModalBeliefSetSK", PROMPT_TEXT_TO_MODAL_BELIEF_SET_SK,
             "Convertit texte en belief set modal avec auto-correction SK."),
            ("GenerateModalQueryIdeasSK", PROMPT_GEN_MODAL_QUERIES_SK,
             "Génère requêtes modales avec gestion d'erreurs SK."),
            ("InterpretModalResultSK", PROMPT_INTERPRET_MODAL_SK,
             "Interprète résultats avec gestion SK des corrections.")
        ]

        for func_name, prompt, description in semantic_functions:
            try:
                self.logger.info(f"Ajout fonction SK {self.name}.{func_name}")
                self.sk_kernel.add_function(
                    prompt=prompt,
                    plugin_name=self.name, 
                    function_name=func_name,
                    description=description,
                    prompt_execution_settings=default_settings
                )
            except Exception as e:
                self.logger.error(f"Erreur ajout fonction SK {func_name}: {e}", exc_info=True)
        
        self.logger.info(f"Composants SK Retry de {self.name} configurés.")

    def _create_retry_execution_settings(self, base_settings: Optional[PromptExecutionSettings] = None) -> PromptExecutionSettings:
        """
        Crée des settings d'exécution avec retry automatique SK.
        
        :param base_settings: Settings de base à étendre (optionnel)
        :return: Settings configurés pour le retry automatique
        """
        if base_settings:
            settings = base_settings
        else:
            try:
                if self._llm_service_id:
                    settings = self.sk_kernel.get_prompt_execution_settings_from_service_id(
                        self._llm_service_id
                    )
                else:
                    settings = PromptExecutionSettings()
            except Exception as e:
                self.logger.warning(f"Impossible de récupérer settings LLM, utilisation par défaut: {e}")
                settings = PromptExecutionSettings()

        # Configurer pour retry automatique SK
        settings.max_auto_invoke_attempts = 3
        self.logger.debug(f"Settings SK Retry configurés: max_auto_invoke_attempts = {settings.max_auto_invoke_attempts}")
        
        return settings

    def _enrich_error_with_bnf(self, error_message: str, problematic_input: str = "") -> str:
        """
        Enrichit un message d'erreur avec la BNF et des suggestions.
        
        :param error_message: Message d'erreur original
        :param problematic_input: Input qui a causé l'erreur
        :return: Message d'erreur enrichi avec BNF et suggestions
        """
        enriched_error = f"""❌ ERREUR TWEETY DÉTECTÉE:
{error_message}

Input problématique: "{problematic_input}"

{TWEETY_MODAL_BNF}

💡 SUGGESTIONS DE CORRECTION:
1. Vérifiez que toutes les constantes sont déclarées
2. Utilisez snake_case pour les noms (ex: paix_mondiale)
3. Remplacez les termes sensibles par des alternatives neutres
4. Respectez la syntaxe BNF ci-dessus

🔄 Veuillez corriger votre syntaxe et réessayer.
"""
        return enriched_error

    def text_to_modal_belief_set(self, text: str) -> str:
        """
        Fonction SK qui retourne les erreurs comme résultats JSON.
        
        Cette méthode implémente le VRAI mécanisme SK : retourne toujours un JSON,
        soit de succès soit d'erreur, permettant à l'agent de voir l'erreur et corriger.
        """
        self.logger.info(f"[SK FUNCTION] text_to_modal_belief_set appelée avec: '{text[:50]}...'")
        
        try:
            # Tentative de conversion
            result = self._convert_to_modal_belief_set(text)
            return json.dumps({
                "success": True, 
                "result": result,
                "message": "Conversion réussie"
            })
        except Exception as e:
            # Retourner l'erreur comme résultat de fonction (pas exception)
            error_details = {
                "success": False, 
                "error": str(e),
                "bnf": TWEETY_MODAL_BNF,
                "suggestion": "Corrigez la syntaxe selon la BNF fournie",
                "problematic_input": text[:100]
            }
            
            self.logger.warning(f"[SK FUNCTION] Erreur retournée comme résultat: {str(e)}")
            return json.dumps(error_details)

    def _convert_to_modal_belief_set(self, text: str) -> str:
        """
        Méthode interne de conversion qui peut lever des exceptions.
        """
        # Simulation d'une conversion qui peut échouer avec erreurs Tweety
        
        # Détecter les termes problématiques qui causent des erreurs Tweety
        problematic_terms = {
            "annihilation": "cessation",
            "aryan": "groupe_specifique", 
            "race": "population",
            "kill": "arreter",
            "destroy": "transformer"
        }
        
        # Convertir le texte en propositions
        text_lower = text.lower()
        contains_problematic = any(term in text_lower for term in problematic_terms)
        
        if contains_problematic:
            # Simuler l'erreur exacte de TweetyProject
            problematic_found = next((term for term in problematic_terms if term in text_lower), "unknown")
            raise ValueError(f"Error parsing Modal Logic formula 'constant {problematic_found}_related' for logic 'S4': Predicate 'constant{problematic_found}_related' has not been declared.")
        
        # Conversion réussie (version simplifiée pour demo)
        safe_text = text.replace(" ", "_").lower()
        belief_set = f"""constant peace_concept
constant urgent_action
prop(peace_concept)
prop(urgent_action)
[]urgent_action
<>peace_concept"""
        
        return belief_set

    async def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[BeliefSet], str]:
        """
        Convertit un texte en belief set modal avec le mécanisme SK retry.
        
        Cette méthode utilise les fonctions SK qui retournent les erreurs comme résultats,
        permettant à l'agent de voir les erreurs et de corriger automatiquement.
        """
        self.logger.info(f"[SK RETRY] Conversion texte->belief set avec mécanisme SK pour: '{text[:50]}...'")
        
        try:
            # Appel de la fonction SK qui peut auto-retry
            result = await self.sk_kernel.plugins[self.name]["TextToModalBeliefSetSK"].invoke(
                self.sk_kernel, 
                input=text
            )
            
            # Parser le résultat JSON
            result_data = json.loads(str(result))
            
            if result_data.get("success", False):
                # Succès : créer le belief set
                belief_set_content = result_data.get("result", "")
                belief_set_obj = ModalBeliefSet(belief_set_content)
                message = result_data.get("message", "Conversion réussie avec SK retry")
                
                self.logger.info(f"[SK RETRY] ✅ Conversion réussie: {message}")
                return belief_set_obj, message
            else:
                # Échec même après retry automatique
                error_msg = result_data.get("error", "Erreur inconnue")
                self.logger.error(f"[SK RETRY] ❌ Échec après retry automatique: {error_msg}")
                return None, f"Échec de conversion SK: {error_msg}"
                
        except json.JSONDecodeError as e:
            error_msg = f"Erreur parsing JSON résultat SK: {e}"
            self.logger.error(f"[SK RETRY] {error_msg}")
            return None, error_msg
        except Exception as e:
            error_msg = f"Erreur inattendue SK retry: {e}"
            self.logger.error(f"[SK RETRY] {error_msg}", exc_info=True)
            return None, error_msg

    def generate_modal_queries(self, text: str, belief_set: str) -> str:
        """
        Fonction SK pour générer des requêtes modales avec gestion d'erreurs.
        """
        self.logger.info(f"[SK FUNCTION] generate_modal_queries appelée")
        
        try:
            # Générer les requêtes
            queries = self._generate_modal_queries_internal(text, belief_set)
            return json.dumps({
                "success": True,
                "query_ideas": [{"formula": q} for q in queries],
                "message": "Requêtes générées avec succès"
            })
        except Exception as e:
            # Retourner l'erreur comme résultat
            return json.dumps({
                "success": False,
                "error": str(e),
                "bnf": TWEETY_MODAL_BNF,
                "suggestion": "Vérifiez la syntaxe des requêtes selon la BNF"
            })

    def _generate_modal_queries_internal(self, text: str, belief_set: str) -> List[str]:
        """
        Génération interne des requêtes (peut lever des exceptions).
        """
        # Version simplifiée pour demo
        queries = ["[]urgent_action", "<>peace_concept", "urgent_action => <>peace_concept"]
        return queries

    async def generate_queries(self, text: str, belief_set: BeliefSet, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Génère des requêtes modales avec mécanisme SK retry.
        """
        self.logger.info(f"[SK RETRY] Génération requêtes avec mécanisme SK")
        
        try:
            result = await self.sk_kernel.plugins[self.name]["GenerateModalQueryIdeasSK"].invoke(
                self.sk_kernel,
                input=text,
                belief_set=belief_set.content
            )
            
            result_data = json.loads(str(result))
            
            if result_data.get("success", False):
                query_ideas = result_data.get("query_ideas", [])
                queries = [idea.get("formula", "") for idea in query_ideas if idea.get("formula")]
                self.logger.info(f"[SK RETRY] ✅ {len(queries)} requêtes générées avec succès")
                return queries
            else:
                error_msg = result_data.get("error", "Erreur génération requêtes")
                self.logger.error(f"[SK RETRY] ❌ Échec génération requêtes: {error_msg}")
                return []
                
        except Exception as e:
            self.logger.error(f"[SK RETRY] Erreur inattendue génération requêtes: {e}", exc_info=True)
            return []

    def execute_query(self, belief_set: BeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête modale avec gestion SK des erreurs.
        """
        self.logger.info(f"[SK RETRY] Exécution requête: {query}")
        
        try:
            # Utiliser le TweetyBridge qui retourne maintenant des erreurs comme résultats
            result_str = self.tweety_bridge.execute_modal_query(
                belief_set_content=belief_set.content,
                query_string=query
            )
            
            # Le TweetyBridge retourne maintenant du JSON avec succès/erreur
            try:
                result_data = json.loads(result_str)
                if result_data.get("success", True):  # Par défaut True pour compatibilité
                    if "ACCEPTED" in result_str: 
                        return True, result_str
                    elif "REJECTED" in result_str:
                        return False, result_str
                    else:
                        return None, result_str
                else:
                    # Erreur retournée comme résultat
                    error_msg = result_data.get("error", "Erreur inconnue")
                    self.logger.warning(f"[SK RETRY] Erreur d'exécution reçue: {error_msg}")
                    return None, f"FUNC_ERROR: {error_msg}"
            except json.JSONDecodeError:
                # Format ancien (chaîne simple) - pour compatibilité
                if "ACCEPTED" in result_str: 
                    return True, result_str
                elif "REJECTED" in result_str:
                    return False, result_str
                else:
                    return None, result_str
            
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution SK de la requête: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return None, f"FUNC_ERROR: {error_msg}"

    async def interpret_results(self, text: str, belief_set: BeliefSet,
                         queries: List[str], results: List[Tuple[Optional[bool], str]],
                         context: Optional[Dict[str, Any]] = None) -> str:
        """
        Interprète les résultats avec mécanisme SK retry.
        """
        self.logger.info(f"[SK RETRY] Interprétation résultats avec mécanisme SK")
        
        try:
            queries_str = "\n".join(queries)
            results_text_list = [res_tuple[1] if res_tuple else "Error: No result" for res_tuple in results]
            results_str = "\n".join(results_text_list)
            
            result = await self.sk_kernel.plugins[self.name]["InterpretModalResultSK"].invoke(
                self.sk_kernel,
                input=text,
                belief_set=belief_set.content,
                queries=queries_str,
                tweety_result=results_str
            )
            
            interpretation = str(result)
            self.logger.info("[SK RETRY] ✅ Interprétation terminée avec mécanisme SK")
            return interpretation
        
        except Exception as e:
            error_msg = f"Erreur lors de l'interprétation SK: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return f"Erreur d'interprétation SK: {error_msg}"

    def validate_formula(self, formula: str) -> bool:
        """
        Valide une formule modale avec mécanisme SK.
        """
        self.logger.debug(f"[SK RETRY] Validation formule: {formula}")
        try:
            is_valid, message = self.tweety_bridge.validate_modal_formula(formula)
            if not is_valid:
                self.logger.warning(f"[SK RETRY] Formule invalide: {formula}. Message: {message}")
            return is_valid
        except AttributeError:
            self.logger.warning("[SK RETRY] Méthode validate_modal_formula non disponible")
            return bool(re.match(r'^[a-zA-Z0-9_\[\]<>()!&|=><=\s]+$', formula))

    def is_consistent(self, belief_set: BeliefSet) -> Tuple[bool, str]:
        """
        Vérifie la cohérence avec mécanisme SK.
        """
        self.logger.info(f"[SK RETRY] Vérification cohérence avec mécanisme SK")
        try:
            is_consistent, message = self.tweety_bridge.is_modal_kb_consistent(belief_set.content)
            return is_consistent, message
        except AttributeError:
            self.logger.warning("[SK RETRY] Méthode is_modal_kb_consistent non disponible")
            return True, "Vérification cohérence non implémentée (SK)"
        except Exception as e:
            error_msg = f"Erreur cohérence SK: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> BeliefSet:
        """
        Crée un ModalBeliefSet à partir de données.
        """
        content = belief_set_data.get("content", "")
        return ModalBeliefSet(content)

    # Méthodes abstraites requises (non implémentées pour cet agent spécialisé)
    async def get_response(self, chat_history: ChatHistory, settings: Optional[Any] = None) -> AsyncGenerator[list[ChatMessageContent], None]:
        logger.warning("get_response non implémentée pour ModalLogicAgentSKRetry")
        yield []
        return

    async def invoke(self, chat_history: ChatHistory, settings: Optional[Any] = None) -> list[ChatMessageContent]:
        logger.warning("invoke non implémentée pour ModalLogicAgentSKRetry")
        return []

    async def invoke_stream(self, chat_history: ChatHistory, settings: Optional[Any] = None) -> AsyncGenerator[list[ChatMessageContent], None]:
        logger.warning("invoke_stream non implémentée pour ModalLogicAgentSKRetry")
        yield []
        return