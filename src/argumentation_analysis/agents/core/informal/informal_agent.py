#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Agent d'analyse informelle pour l'identification et l'analyse des sophismes.

Ce module implémente `InformalAnalysisAgent`, un agent spécialisé dans
l'analyse informelle des arguments, en particulier la détection et la
catégorisation des sophismes (fallacies). Il s'appuie sur Semantic Kernel
pour interagir avec des modèles de langage via des prompts spécifiques
et peut intégrer un plugin natif (`InformalAnalysisPlugin`) pour des
opérations liées à la taxonomie des sophismes.

L'agent est conçu pour :
- Identifier les arguments dans un texte.
- Analyser un texte ou un argument spécifique pour y détecter des sophismes.
- Justifier l'attribution de ces sophismes.
- Explorer une hiérarchie de taxonomie des sophismes.
- Catégoriser les sophismes détectés.
- Effectuer une analyse complète combinant ces étapes.
"""

import logging
import json
from typing import Dict, List, Any, Optional
import semantic_kernel as sk
from semantic_kernel.functions.kernel_arguments import KernelArguments

# Import de la classe de base
from ..abc.agent_bases import BaseAgent

# Import des définitions et des prompts
from .informal_definitions import InformalAnalysisPlugin, INFORMAL_AGENT_INSTRUCTIONS
from .prompts import prompt_identify_args_v8, prompt_analyze_fallacies_v1, prompt_justify_fallacy_attribution_v1


# Configuration du logging
# logging.basicConfig( # Commenté car BaseAgent gère son propre logger
#     level=logging.INFO,
#     format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
#     datefmt='%H:%M:%S'
# )

class InformalAnalysisAgent(BaseAgent):
    """
    Agent spécialisé dans l'analyse informelle des arguments et la détection de sophismes.

    Hérite de `BaseAgent` et utilise des fonctions sémantiques ainsi qu'un plugin
    natif (`InformalAnalysisPlugin`) pour interagir avec une taxonomie de sophismes
    et analyser des textes.

    Attributes:
        config (Dict[str, Any]): Configuration spécifique à l'agent, comme
                                 les seuils de confiance pour la détection.
                                 (Note: la gestion de la configuration pourrait être améliorée).
    """
    
    def __init__(
        self,
        kernel: sk.Kernel,
        agent_name: str = "InformalAnalysisAgent",
        # Les anciens paramètres tools, config, semantic_kernel, informal_plugin, strict_validation
        # ne sont plus nécessaires ici car gérés par BaseAgent et setup_agent_components.
    ):
        """
        Initialise l'agent d'analyse informelle.

        :param kernel: Le kernel Semantic Kernel à utiliser par l'agent.
        :type kernel: sk.Kernel
        :param agent_name: Le nom de cet agent. Par défaut "InformalAnalysisAgent".
        :type agent_name: str
        """
        super().__init__(kernel, agent_name, system_prompt=INFORMAL_AGENT_INSTRUCTIONS)
        self.logger.info(f"Initialisation de l'agent informel {self.name}...")
        # self.config est conservé pour l'instant pour la compatibilité de certaines méthodes
        # mais devrait idéalement être géré au niveau du plugin ou via des arguments de fonction.
        self.config = { # Valeurs par défaut, peuvent être surchargées si nécessaire
            "analysis_depth": "standard",
            "confidence_threshold": 0.5,
            "max_fallacies": 5,
            "include_context": False
        }
        self.logger.info(f"Agent informel {self.name} initialisé.")

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Retourne les capacités de l'agent d'analyse informelle.

        :return: Un dictionnaire mappant les noms des capacités à leurs descriptions.
        :rtype: Dict[str, Any]
        """
        return {
            "identify_arguments": "Identifies main arguments in a text using semantic functions.",
            "analyze_fallacies": "Analyzes text for fallacies using semantic functions and a taxonomy.",
            "explore_fallacy_hierarchy": "Navigates the fallacy taxonomy using a native plugin.",
            "get_fallacy_details": "Gets details for a specific fallacy using a native plugin.",
            "categorize_fallacies": "Categorizes identified fallacies based on their type.",
            "perform_complete_analysis": "Performs a comprehensive analysis of a text for arguments and fallacies."
        }

    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Configure les composants spécifiques de l'agent d'analyse informelle dans le kernel SK.

        Enregistre le plugin natif `InformalAnalysisPlugin` et les fonctions sémantiques
        pour l'identification d'arguments, l'analyse de sophismes et la justification
        d'attribution de sophismes.

        :param llm_service_id: L'ID du service LLM à utiliser pour les fonctions sémantiques.
        :type llm_service_id: str
        :return: None
        :rtype: None
        :raises Exception: Si une erreur survient lors de l'enregistrement des fonctions sémantiques.
        """
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants pour {self.name} avec le service LLM: {llm_service_id}...")

        # 1. Initialisation et Enregistrement du Plugin Natif
        informal_plugin_instance = InformalAnalysisPlugin()
        # Utiliser self.name comme nom de plugin pour la cohérence, ou un nom spécifique comme "InformalAnalyzer"
        # Si le system_prompt fait référence à "InformalAnalyzer", il faut utiliser ce nom.
        # D'après INFORMAL_AGENT_INSTRUCTIONS, le plugin est appelé "InformalAnalyzer"
        native_plugin_name = "InformalAnalyzer"
        self.sk_kernel.add_plugin(informal_plugin_instance, plugin_name=native_plugin_name)
        self.logger.info(f"Plugin natif '{native_plugin_name}' enregistré dans le kernel.")

        # 2. Enregistrement des Fonctions Sémantiques
        # Le plugin_name pour les fonctions sémantiques est souvent le nom de l'agent ou un domaine.
        # Ici, nous utilisons aussi native_plugin_name pour que les appels soient cohérents
        # si le prompt système s'attend à `InformalAnalyzer.semantic_IdentifyArguments`.
        
        # Récupérer les settings d'exécution par défaut pour le service LLM spécifié
        try:
            execution_settings = self.sk_kernel.get_prompt_execution_settings_from_service_id(llm_service_id)
        except Exception as e:
            self.logger.warning(f"Impossible de récupérer les settings LLM pour {llm_service_id}: {e}. Utilisation des settings par défaut.")
            execution_settings = None

        try:
            self.sk_kernel.add_function(
                prompt=prompt_identify_args_v8,
                plugin_name=native_plugin_name, # Cohérent avec les appels attendus
                function_name="semantic_IdentifyArguments",
                description="Identifie les arguments clés dans un texte.",
                prompt_execution_settings=execution_settings
            )
            self.logger.info(f"Fonction sémantique '{native_plugin_name}.semantic_IdentifyArguments' enregistrée.")

            self.sk_kernel.add_function(
                prompt=prompt_analyze_fallacies_v1,
                plugin_name=native_plugin_name,
                function_name="semantic_AnalyzeFallacies",
                description="Analyse les sophismes dans un argument.",
                prompt_execution_settings=execution_settings
            )
            self.logger.info(f"Fonction sémantique '{native_plugin_name}.semantic_AnalyzeFallacies' enregistrée.")

            self.sk_kernel.add_function(
                prompt=prompt_justify_fallacy_attribution_v1,
                plugin_name=native_plugin_name,
                function_name="semantic_JustifyFallacyAttribution",
                description="Justifie l'attribution d'un sophisme à un argument.",
                prompt_execution_settings=execution_settings
            )
            self.logger.info(f"Fonction sémantique '{native_plugin_name}.semantic_JustifyFallacyAttribution' enregistrée.")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'enregistrement des fonctions sémantiques: {e}", exc_info=True)
            raise  # Propage l'erreur pour indiquer un échec de configuration

        self.logger.info(f"Composants de {self.name} configurés avec succès.")

    async def analyze_fallacies(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyse les sophismes dans un texte en utilisant la fonction sémantique `semantic_AnalyzeFallacies`.

        Le résultat brut du LLM est parsé (en supposant un format JSON) et filtré
        selon les seuils de confiance et le nombre maximum de sophismes configurés.

        :param text: Le texte à analyser pour les sophismes.
        :type text: str
        :return: Une liste de dictionnaires, chaque dictionnaire représentant un sophisme détecté.
                 Retourne une liste avec une entrée d'erreur en cas d'échec du parsing ou de l'appel LLM.
        :rtype: List[Dict[str, Any]]
        """
        self.logger.info(f"Analyse sémantique des sophismes pour un texte de {len(text)} caractères...")
        try:
            arguments = KernelArguments(input=text)
            result = await self.sk_kernel.invoke(
                plugin_name="InformalAnalyzer", # Doit correspondre au nom utilisé dans setup_agent_components
                function_name="semantic_AnalyzeFallacies",
                arguments=arguments
            )
            
            # Le traitement du résultat dépendra du format de sortie du prompt.
            # Pour l'instant, on suppose qu'il retourne une chaîne JSON ou un format parsable.
            # Exemple basique:
            raw_result = str(result)
            # Ici, il faudrait parser raw_result pour le transformer en List[Dict[str, Any]]
            # Pour l'instant, on retourne une structure basique.
            # Une implémentation réelle nécessiterait un parsing robuste.
            # Exemple: si le prompt retourne un JSON de liste de sophismes:
            try:
                parsed_fallacies = json.loads(raw_result)
                if isinstance(parsed_fallacies, list):
                    # Appliquer le filtrage de l'ancienne méthode si pertinent
                    confidence_threshold = self.config.get("confidence_threshold", 0.5)
                    filtered_fallacies = [f for f in parsed_fallacies if isinstance(f, dict) and f.get("confidence", 0) >= confidence_threshold]
                    
                    max_fallacies = self.config.get("max_fallacies", 5)
                    if len(filtered_fallacies) > max_fallacies:
                        filtered_fallacies = sorted(filtered_fallacies, key=lambda f: f.get("confidence", 0), reverse=True)[:max_fallacies]
                    
                    self.logger.info(f"{len(filtered_fallacies)} sophismes (sémantiques) détectés et filtrés.")
                    return filtered_fallacies
                else:
                    self.logger.warning(f"Résultat de semantic_AnalyzeFallacies n'est pas une liste JSON: {raw_result}")
                    return [{"error": "Format de résultat inattendu", "details": raw_result}]
            except json.JSONDecodeError:
                self.logger.warning(f"Impossible de parser le résultat JSON de semantic_AnalyzeFallacies: {raw_result}")
                return [{"error": "Résultat non JSON", "details": raw_result}]

        except Exception as e:
            self.logger.error(f"Erreur lors de l'appel à semantic_AnalyzeFallacies: {e}", exc_info=True)
            return [{"error": str(e)}]

    # Les méthodes analyze_rhetoric et analyze_context dépendaient d'outils externes
    # qui ne sont pas gérés par cette refonte initiale. Elles sont commentées.
    # async def analyze_rhetoric(self, text: str) -> Dict[str, Any]:
        """
        Analyse la rhétorique d'un texte.
        
        Args:
            text: Texte à analyser
        
        Returns:
            Résultats de l'analyse rhétorique
        
        Raises:
            ValueError: Si l'analyseur rhétorique n'est pas disponible
        """
    #     """
    #     Analyse la rhétorique d'un texte.
    #     """
    #     # if "rhetorical_analyzer" not in self.tools: # self.tools n'existe plus
    #     #     raise ValueError("L'analyseur rhétorique n'est pas disponible")
    #     self.logger.warning("analyze_rhetoric n'est pas implémenté dans la version BaseAgent.")
    #     return {"error": "Non implémenté"}
        # self.logger.info(f"Analyse rhétorique d'un texte de {len(text)} caractères...")
        # return self.tools["rhetorical_analyzer"].analyze(text)

    # async def analyze_context(self, text: str) -> Dict[str, Any]:
    #     """
    #     Analyse le contexte d'un texte.
    #     """
    #     # if "contextual_analyzer" not in self.tools: # self.tools n'existe plus
    #     #     raise ValueError("L'analyseur contextuel n'est pas disponible")
    #     self.logger.warning("analyze_context n'est pas implémenté dans la version BaseAgent.")
    #     return {"error": "Non implémenté"}
        # self.logger.info(f"Analyse contextuelle d'un texte de {len(text)} caractères...")
        # return self.tools["contextual_analyzer"].analyze_context(text)

    async def identify_arguments(self, text: str) -> List[str]:
        """
        Identifie les arguments principaux dans un texte en utilisant la fonction
        sémantique `semantic_IdentifyArguments`.

        :param text: Le texte à analyser.
        :type text: str
        :return: Une liste de chaînes de caractères, chaque chaîne représentant un argument identifié.
                 Retourne une liste vide en cas d'erreur ou si aucun argument n'est identifié.
        :rtype: List[str]
        """
        self.logger.info(f"Identification sémantique des arguments pour un texte de {len(text)} caractères...")
        try:
            arguments = KernelArguments(input=text)
            result = await self.sk_kernel.invoke(
                plugin_name="InformalAnalyzer", # Doit correspondre au nom utilisé dans setup_agent_components
                function_name="semantic_IdentifyArguments",
                arguments=arguments
            )
            
            # Traiter le résultat
            raw_arguments = str(result).strip()
            if not raw_arguments: # Gérer le cas où le LLM ne retourne rien ou que des espaces
                self.logger.info("Aucun argument identifié par la fonction sémantique (résultat vide).")
                return []

            identified_args = raw_arguments.split("\n")
            identified_args = [arg.strip() for arg in identified_args if arg.strip()]
            
            self.logger.info(f"{len(identified_args)} arguments (sémantiques) identifiés.")
            return identified_args
        except Exception as e:
            self.logger.error(f"Erreur lors de l'appel à semantic_IdentifyArguments: {e}", exc_info=True)
            return []

    async def analyze_argument(self, argument: str) -> Dict[str, Any]:
        """
        Effectue une analyse complète d'un argument unique.

        Actuellement, cela se limite à l'analyse des sophismes pour l'argument donné.
        Les analyses rhétorique et contextuelle sont commentées car elles dépendaient
        d'outils externes non gérés dans cette version.

        :param argument: La chaîne de caractères de l'argument à analyser.
        :type argument: str
        :return: Un dictionnaire contenant l'argument original et une liste des sophismes détectés.
        :rtype: Dict[str, Any]
        """
        self.logger.info(f"Analyse complète d'un argument de {len(argument)} caractères...")
        
        results = {
            "argument": argument,
            "fallacies": await self.analyze_fallacies(argument) # Appel asynchrone
        }
        
        # L'analyse rhétorique et contextuelle sont commentées car elles dépendaient d'outils externes
        # if "rhetorical_analyzer" in self.tools: # self.tools n'existe plus
        #     try:
        #         # results["rhetoric"] = await self.analyze_rhetoric(argument) # Devrait être async
        #         pass
        #     except Exception as e:
        #         self.logger.error(f"Erreur lors de l'analyse rhétorique: {e}")
        
        # if "contextual_analyzer" in self.tools and self.config.get("include_context", False): # self.tools n'existe plus
        #     try:
        #         # results["context"] = await self.analyze_context(argument) # Devrait être async
        #         pass
        #     except Exception as e:
        #         self.logger.error(f"Erreur lors de l'analyse contextuelle: {e}")
        
        return results

    async def analyze_text(self, text: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Effectue une analyse complète d'un texte.

        Cette méthode se concentre actuellement sur l'analyse des sophismes dans le texte fourni.
        Elle ne procède pas à une identification et une analyse individuelle des arguments
        comme le faisait `perform_complete_analysis`.

        :param text: Le texte à analyser.
        :type text: str
        :param context: Contexte optionnel pour l'analyse (non utilisé actuellement dans cette méthode).
        :type context: Optional[str]
        :return: Un dictionnaire contenant la liste des sophismes détectés, le contexte (si fourni),
                 un timestamp, et potentiellement un message d'erreur.
        :rtype: Dict[str, Any]
        """
        # Validation du texte d'entrée
        if text is None or text == "":
            self.logger.warning("Texte vide fourni pour l'analyse")
            return {
                "fallacies": [],
                "context": context,
                "analysis_timestamp": self._get_timestamp(),
                "error": "Le texte est vide"
            }
        
        self.logger.info(f"Analyse complète d'un texte de {len(text)} caractères...")
        
        try:
            # Analyser les sophismes directement
            fallacies = await self.analyze_fallacies(text) # Appel asynchrone
            
            # Construire le résultat dans le format attendu par les tests
            results = {
                "fallacies": fallacies,
                "analysis_timestamp": self._get_timestamp()
            }
            
            # Ajouter le contexte si fourni
            if context is not None:
                results["context"] = context
            
            self.logger.info(f"Analyse terminée: {len(fallacies)} sophismes détectés (via analyze_text).")
            return results
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse: {e}")
            return {
                "fallacies": [],
                "context": context,
                "analysis_timestamp": self._get_timestamp(),
                "error": f"Erreur lors de l'analyse: {str(e)}"
            }
    
    async def explore_fallacy_hierarchy(self, current_pk: int = 0, max_children: int = 15) -> Dict[str, Any]:
        """
        Explore la hiérarchie des sophismes à partir d'un nœud donné, en utilisant
        la fonction native `explore_fallacy_hierarchy` du plugin `InformalAnalyzer`.

        :param current_pk: La clé primaire (PK) du nœud de la hiérarchie à partir duquel explorer.
                           Par défaut 0 (racine).
        :type current_pk: int
        :param max_children: Le nombre maximum d'enfants directs à retourner pour chaque nœud.
        :type max_children: int
        :return: Un dictionnaire représentant la sous-hiérarchie explorée (format JSON parsé),
                 ou un dictionnaire d'erreur en cas d'échec.
        :rtype: Dict[str, Any]
        """
        self.logger.info(f"Exploration de la hiérarchie des sophismes (natif) depuis PK {current_pk}...")
        try:
            arguments = KernelArguments(current_pk_str=str(current_pk), max_children=max_children)
            result = await self.sk_kernel.invoke(
                plugin_name="InformalAnalyzer", # Doit correspondre au nom utilisé dans setup_agent_components
                function_name="explore_fallacy_hierarchy", # Nom de la fonction native dans InformalAnalysisPlugin
                arguments=arguments
            )
            # La fonction native retourne déjà un JSON string, qui est parsé par invoke (?) ou doit l'être.
            # Si invoke retourne un FunctionResult, il faut prendre sa valeur.
            # Si la fonction native retourne un dict, c'est encore mieux.
            # D'après la définition du plugin, elle retourne un str JSON.
            result_str = str(result)
            return json.loads(result_str)
        except Exception as e:
            self.logger.error(f"Erreur lors de l'appel à explore_fallacy_hierarchy (natif): {e}", exc_info=True)
            return {"error": str(e)}

    async def get_fallacy_details(self, fallacy_pk: int) -> Dict[str, Any]:
        """
        Obtient les détails d'un sophisme spécifique par sa clé primaire (PK),
        en utilisant la fonction native `get_fallacy_details` du plugin `InformalAnalyzer`.

        :param fallacy_pk: La clé primaire du sophisme.
        :type fallacy_pk: int
        :return: Un dictionnaire contenant les détails du sophisme (format JSON parsé),
                 ou un dictionnaire d'erreur en cas d'échec.
        :rtype: Dict[str, Any]
        """
        self.logger.info(f"Récupération des détails du sophisme (natif) PK {fallacy_pk}...")
        try:
            arguments = KernelArguments(fallacy_pk_str=str(fallacy_pk))
            result = await self.sk_kernel.invoke(
                plugin_name="InformalAnalyzer", # Doit correspondre au nom utilisé dans setup_agent_components
                function_name="get_fallacy_details", # Nom de la fonction native dans InformalAnalysisPlugin
                arguments=arguments
            )
            result_str = str(result)
            return json.loads(result_str)
        except Exception as e:
            self.logger.error(f"Erreur lors de l'appel à get_fallacy_details (natif): {e}", exc_info=True)
            return {"error": str(e)}

    def categorize_fallacies(self, fallacies: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Catégorise une liste de sophismes détectés en fonction de types prédéfinis.

        Utilise un mapping interne pour assigner chaque type de sophisme à une catégorie
        plus large (RELEVANCE, INDUCTION, CAUSALITE, AMBIGUITE, PRESUPPOSITION, AUTRES).

        :param fallacies: Une liste de dictionnaires, chaque dictionnaire représentant
                          un sophisme détecté et devant contenir une clé "fallacy_type".
        :type fallacies: List[Dict[str, Any]]
        :return: Un dictionnaire où les clés sont les noms des catégories et les valeurs
                 sont des listes des types de sophismes appartenant à cette catégorie.
        :rtype: Dict[str, List[str]]
        """
        self.logger.info(f"Catégorisation de {len(fallacies)} sophismes...")
        
        categories = {
            "RELEVANCE": [],
            "INDUCTION": [],
            "CAUSALITE": [],
            "AMBIGUITE": [],
            "PRESUPPOSITION": [],
            "AUTRES": []
        }
        
        # Mapping des types de sophismes vers les catégories
        fallacy_mapping = {
            "ad_hominem": "RELEVANCE",
            "appel_autorite": "RELEVANCE",
            "appel_emotion": "RELEVANCE",
            "appel_popularite": "INDUCTION",
            "generalisation_hative": "INDUCTION",
            "pente_glissante": "CAUSALITE",
            "fausse_cause": "CAUSALITE",
            "equivoque": "AMBIGUITE",
            "amphibologie": "AMBIGUITE",
            "petitio_principii": "PRESUPPOSITION",
            "fausse_dichotomie": "PRESUPPOSITION"
        }
        
        for fallacy in fallacies:
            fallacy_type = fallacy.get("fallacy_type", "").lower().replace(" ", "_")
            category = fallacy_mapping.get(fallacy_type, "AUTRES")
            
            if fallacy_type not in categories[category]:
                categories[category].append(fallacy_type)
        
        self.logger.info(f"Sophismes catégorisés: {sum(len(v) for v in categories.values())} types")
        return categories
    
    async def perform_complete_analysis(self, text: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Effectue une analyse complète d'un texte, incluant la détection et la catégorisation des sophismes.

        Les analyses rhétorique et contextuelle sont actuellement commentées.

        :param text: Le texte à analyser.
        :type text: str
        :param context: Contexte optionnel pour l'analyse (non utilisé actuellement).
        :type context: Optional[str]
        :return: Un dictionnaire contenant le texte original, la liste des sophismes détectés,
                 les catégories de ces sophismes, un timestamp, un résumé, et potentiellement
                 un message d'erreur.
        :rtype: Dict[str, Any]
        """
        self.logger.info(f"Analyse complète (refactorée) d'un texte de {len(text)} caractères...")
        
        results = {
            "text": text,
            "context": context,
            "fallacies": [],
            # "rhetorical_analysis": {}, # Commenté
            # "contextual_analysis": {}, # Commenté
            "categories": {},
            "analysis_timestamp": self._get_timestamp() # Peut rester synchrone
        }
        
        try:
            # Analyse des sophismes
            fallacies = await self.analyze_fallacies(text) # Appel asynchrone
            results["fallacies"] = fallacies
            
            # Catégorisation des sophismes
            if fallacies:
                # categorize_fallacies est synchrone, pas besoin de await
                results["categories"] = self.categorize_fallacies(fallacies)
            
            # Les analyses rhétorique et contextuelle sont commentées
            # if "rhetorical_analyzer" in self.tools: # self.tools n'existe plus
            #     try:
            #         # results["rhetorical_analysis"] = await self.analyze_rhetoric(text)
            #         pass
            #     except Exception as e:
            #         self.logger.error(f"Erreur lors de l'analyse rhétorique: {e}")
            #         # results["rhetorical_analysis"] = {"error": str(e)}
            
            # if "contextual_analyzer" in self.tools and (context or self.config.get("include_context", False)): # self.tools n'existe plus
            #     try:
            #         # if context:
            #         #     results["contextual_analysis"] = await self.tools["contextual_analyzer"].analyze_context(text, context)
            #         # else:
            #         #     results["contextual_analysis"] = await self.analyze_context(text)
            #         pass
            #     except Exception as e:
            #         self.logger.error(f"Erreur lors de l'analyse contextuelle: {e}")
            #         # results["contextual_analysis"] = {"error": str(e)}
            
            self.logger.info("Analyse complète (refactorée) terminée avec succès.")
            return results
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse complète (refactorée): {e}", exc_info=True)
            results["error"] = str(e)
            return results

    async def _extract_arguments(self, text: str) -> List[Dict[str, Any]]:
        """
        Extrait les arguments d'un texte en utilisant la méthode sémantique `identify_arguments`.

        :param text: Le texte à partir duquel extraire les arguments.
        :type text: str
        :return: Une liste de dictionnaires, chaque dictionnaire représentant un argument
                 extrait avec un ID, le texte, le type ("semantic"), et une confiance par défaut.
                 Retourne une liste vide en cas d'erreur ou si aucun argument n'est extrait.
        :rtype: List[Dict[str, Any]]
        """
        self.logger.info(f"Extraction des arguments d'un texte de {len(text)} caractères...")
        
        arguments = []
        
        try:
            # Utiliser la méthode identify_arguments refactorée (qui utilise le kernel)
            # Plus besoin de vérifier self.semantic_kernel ici, car BaseAgent le gère.
            semantic_args = await self.identify_arguments(text) # Appel asynchrone
            for i, arg_text in enumerate(semantic_args):
                arguments.append({
                    "id": f"arg-{i+1}",
                    "text": arg_text,
                    "type": "semantic", # Indique que cela vient de l'analyse sémantique
                    "confidence": 0.8 # Exemple de confiance, pourrait être ajusté
                })
            
            # La logique de fallback (paragraphes/phrases) peut être conservée si identify_arguments retourne une liste vide
            # ou si une stratégie hybride est souhaitée. Pour l'instant, on se fie à l'appel sémantique.
            if not arguments:
                 self.logger.info("Aucun argument extrait par la méthode sémantique, _extract_arguments retourne une liste vide.")
            else:
                self.logger.info(f"{len(arguments)} arguments extraits via _extract_arguments (utilisant identify_arguments).")
            return arguments
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction des arguments: {e}")
            return []
    
    def _process_text(self, text: str) -> Dict[str, Any]:
        """
        Analyse les propriétés de base d'un texte, telles que le nombre de mots,
        de phrases, de paragraphes, la langue détectée (heuristique simple),
        et une estimation de la complexité.

        :param text: Le texte à traiter.
        :type text: str
        :return: Un dictionnaire contenant les propriétés analysées du texte,
                 ou un dictionnaire d'erreur si le traitement échoue.
        :rtype: Dict[str, Any]
        """
        self.logger.info(f"Traitement d'un texte de {len(text)} caractères...")
        
        try:
            import re
            
            # Compter les mots
            words = re.findall(r'\b\w+\b', text.lower())
            word_count = len(words)
            
            # Compter les phrases
            sentences = re.split(r'[.!?]+', text)
            sentence_count = len([s for s in sentences if s.strip()])
            
            # Compter les paragraphes
            paragraphs = text.split('\n\n')
            paragraph_count = len([p for p in paragraphs if p.strip()])
            
            # Détecter la langue (simple heuristique)
            french_words = ['le', 'la', 'les', 'de', 'du', 'des', 'et', 'ou', 'est', 'sont', 'dans', 'pour', 'avec', 'sur']
            english_words = ['the', 'and', 'or', 'is', 'are', 'in', 'for', 'with', 'on', 'at', 'to', 'of']
            
            french_count = sum(1 for word in words if word in french_words)
            english_count = sum(1 for word in words if word in english_words)
            
            language = "fr" if french_count > english_count else "en" if english_count > 0 else "unknown"
            
            # Calculer la complexité (mots par phrase)
            avg_words_per_sentence = word_count / sentence_count if sentence_count > 0 else 0
            
            result = {
                "processed_text": text,
                "word_count": word_count,
                "sentence_count": sentence_count,
                "paragraph_count": paragraph_count,
                "language": language,
                "avg_words_per_sentence": round(avg_words_per_sentence, 2),
                "complexity": "high" if avg_words_per_sentence > 20 else "medium" if avg_words_per_sentence > 10 else "low"
            }
            
            self.logger.info(f"Texte traité: {word_count} mots, {sentence_count} phrases, langue: {language}")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement du texte: {e}")
            return {
                "processed_text": text,
                "word_count": 0,
                "sentence_count": 0,
                "paragraph_count": 0,
                "language": "unknown",
                "error": str(e)
            }
    
    def _get_timestamp(self) -> str:
        """
        Génère un timestamp actuel au format ISO.

        :return: Une chaîne de caractères représentant le timestamp au format ISO.
        :rtype: str
        """
        from datetime import datetime # Importation locale pour éviter une dépendance globale
        return datetime.now().isoformat()
    
    async def analyze_and_categorize(self, text: str) -> Dict[str, Any]:
        """
        Analyse un texte pour détecter les sophismes et les catégorise ensuite.

        :param text: Le texte à analyser.
        :type text: str
        :return: Un dictionnaire contenant le texte original, la liste des sophismes détectés,
                 leurs catégories, un timestamp, un résumé, et potentiellement un message d'erreur.
        :rtype: Dict[str, Any]
        """
        self.logger.info(f"Analyse et catégorisation (refactorée) d'un texte de {len(text)} caractères...")
        
        try:
            # Analyser les sophismes
            fallacies = await self.analyze_fallacies(text) # Appel asynchrone
            
            # Catégoriser les sophismes (méthode synchrone)
            categories = self.categorize_fallacies(fallacies) if fallacies else {}
            
            result = {
                "text": text,
                "fallacies": fallacies,
                "categories": categories,
                "analysis_timestamp": self._get_timestamp(), # Méthode synchrone
                "summary": {
                    "total_fallacies": len(fallacies),
                    "categories_count": len([cat for cat, items in categories.items() if items])
                }
            }
            
            self.logger.info(f"Analyse et catégorisation (refactorée) terminée: {len(fallacies)} sophismes trouvés.")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse et catégorisation (refactorée): {e}", exc_info=True)
            return {
                "text": text,
                "fallacies": [],
                "categories": {},
                "error": str(e),
                "analysis_timestamp": self._get_timestamp()
            }

# Log de chargement
# logging.getLogger(__name__).debug("Module agents.core.informal.informal_agent chargé.") # Géré par BaseAgent