#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Définit l'agent d'analyse informelle pour l'identification des sophismes.

Ce module fournit `InformalAnalysisAgent`, un agent spécialisé dans l'analyse
informelle d'arguments. Il combine des capacités sémantiques (via LLM) et
natives pour détecter, justifier et catégoriser les sophismes dans un texte.

Fonctionnalités principales :
- Identification d'arguments.
- Détection de sophismes avec score de confiance.
- Justification de l'attribution des sophismes.
- Navigation et interrogation d'une taxonomie de sophismes via un plugin natif.
"""

import warnings
import logging
import json
import re
from typing import Dict, List, Any, Optional
from pydantic import Field, PrivateAttr
import semantic_kernel as sk
from semantic_kernel.functions import KernelArguments
from semantic_kernel.contents.chat_message_content import ChatMessageContent

# Import de la classe de base
from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent

# Import des définitions et des prompts
from .informal_definitions import InformalAnalysisPlugin, INFORMAL_AGENT_INSTRUCTIONS
from .prompts import prompt_identify_args_v8, prompt_analyze_fallacies_v1, prompt_justify_fallacy_attribution_v1
from .taxonomy_sophism_detector import TaxonomySophismDetector, get_global_detector
from argumentation_analysis.config.settings import AppSettings

from argumentation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel

# Configuration du logging
# logging.basicConfig( # Commenté car BaseAgent gère son propre logger
#     level=logging.INFO,
#     format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
#     datefmt='%H:%M:%S'
# )

class InformalAnalysisAgent(BaseAgent):
    """
    Agent spécialiste de la détection de sophismes et de l'analyse informelle.

    Cet agent orchestre des fonctions sémantiques et natives pour analyser un
    texte. Il peut identifier des arguments, détecter des sophismes potentiels,
    justifier ses conclusions et classer les sophismes selon une taxonomie.

    L'interaction avec la taxonomie (par exemple, pour explorer la hiérarchie
    des sophismes) est gérée par un plugin natif (`InformalAnalysisPlugin`).

    Attributes:
        config (Dict[str, Any]): Configuration pour l'analyse (profondeur, seuils).
        _taxonomy_file_path (Optional[str]): Chemin vers le fichier JSON de la
            taxonomie, utilisé par le plugin natif.
    """
    config: Dict[str, Any] = {
        "analysis_depth": "standard",
        "confidence_threshold": 0.5,
        "max_fallacies": 5,
        "include_context": False
    }
    logger: Optional[logging.Logger] = Field(default_factory=lambda: logging.getLogger(__name__))
    _taxonomy_file_path: Optional[str] = PrivateAttr(default=None)

    def __init__(
        self,
        kernel: sk.Kernel,
        agent_name: str = "InformalAnalysisAgent",
        taxonomy_file_path: Optional[str] = None,
        instructions: str = INFORMAL_AGENT_INSTRUCTIONS,
    ):
        """
        Initialise l'agent d'analyse informelle.

        Args:
            kernel (sk.Kernel): L'instance du kernel Semantic Kernel.
            agent_name (str, optional): Le nom de l'agent.
            taxonomy_file_path (Optional[str], optional): Chemin vers le fichier
                JSON de la taxonomie pour le plugin natif.
        """
        super().__init__(kernel=kernel, agent_name=agent_name, system_prompt=instructions)
        self._kernel = kernel
        self._instructions = instructions
        self._taxonomy_file_path = taxonomy_file_path
        logging.getLogger(__name__).info(f"Agent {agent_name} initialisé avec la taxonomie: {self._taxonomy_file_path}.")

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Retourne les capacités spécifiques de l'agent d'analyse informelle.

        Returns:
            Dict[str, Any]: Un dictionnaire décrivant les méthodes principales.
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
        Configure les composants de l'agent dans le kernel.

        Cette méthode enregistre à la fois le plugin natif (`InformalAnalysisPlugin`)
        pour la gestion de la taxonomie et les fonctions sémantiques (prompts)
        pour l'analyse de texte.

        Args:
            llm_service_id (str): L'ID du service LLM à utiliser pour les
                fonctions sémantiques.
        """
        # super().setup_agent_components(llm_service_id) # Appel supprimé car la méthode n'existe pas dans BaseAgent
        self.logger.info(f"Configuration des composants pour {self.name} avec le service LLM: {llm_service_id}...")

        # Récupérer le service LLM à partir du noyau principal de l'agent
        llm_service = self.kernel.get_service(llm_service_id)
        if not llm_service:
            raise ValueError(f"Service LLM avec ID '{llm_service_id}' non trouvé dans le kernel.")

        # Appeler la fonction setup_informal_kernel pour enregistrer TOUS les composants
        # (plugin natif ET fonctions sémantiques) dans le noyau de l'agent.
        setup_informal_kernel(
            kernel=self.kernel,
            llm_service=llm_service,
            taxonomy_file_path=self._taxonomy_file_path
        )

        self.logger.info(f"Composants de {self.name} configurés avec succès via setup_informal_kernel.")

    def _extract_json_from_llm_output(self, raw_str: str) -> str:
        """
        Extrait une chaîne JSON d'une sortie de LLM qui peut contenir des
        délimiteurs de bloc de code (comme ```json ... ```).
        """
        match = re.search(r'```\s*json\s*(.*?)\s*```', raw_str, re.DOTALL)
        if match:
            return match.group(1).strip()
        else:
            return raw_str.strip()

    async def analyze_fallacies(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyse un texte pour détecter les sophismes en utilisant une fonction sémantique.

        Cette méthode invoque la fonction `semantic_AnalyzeFallacies` via le kernel.
        Elle prend la sortie brute du LLM, en extrait le bloc de code JSON,
        le parse, puis filtre les résultats en fonction du seuil de confiance
        et du nombre maximum de sophismes définis dans la configuration de l'agent.

        Args:
            text (str): Le texte brut à analyser pour les sophismes.

        Returns:
            List[Dict[str, Any]]: Une liste de dictionnaires, chaque dictionnaire
            représentant un sophisme détecté. En cas d'erreur de parsing ou d'appel LLM,
            la liste contient un seul dictionnaire avec une clé "error".
        """
        self.logger.info(f"Analyse sémantique des sophismes pour un texte de {len(text)} caractères...")
        try:
            arguments = KernelArguments(input=text)
            result = await self.kernel.invoke(
                plugin_name="InformalAnalyzer",
                function_name="semantic_AnalyzeFallacies",
                arguments=KernelArguments(text_to_analyze=text)
            )
            
            # Le traitement du résultat dépendra du format de sortie du prompt.
            raw_result = str(result)
            cleaned_json_str = self._extract_json_from_llm_output(raw_result)

            try:
                parsed_result = json.loads(cleaned_json_str)
                
                # Gérer le cas où le LLM retourne un objet {"sophismes": [...]}
                if isinstance(parsed_result, dict) and "sophismes" in parsed_result:
                    parsed_fallacies = parsed_result["sophismes"]
                elif isinstance(parsed_result, list):
                    parsed_fallacies = parsed_result
                else:
                    self.logger.warning(f"Résultat de semantic_AnalyzeFallacies n'est ni une liste, ni un objet avec la clé 'sophismes': {raw_result}")
                    return [{"error": "Format de résultat inattendu", "details": raw_result}]

                # Appliquer le filtrage - ne filtrer que si le champ confidence existe
                confidence_threshold = self.config.get("confidence_threshold", 0.5)
                filtered_fallacies = []
                for f in parsed_fallacies:
                    if isinstance(f, dict):
                        # Si pas de champ confidence, considérer comme valide (confiance par défaut = 1.0)
                        confidence = f.get("confidence", 1.0)
                        if confidence >= confidence_threshold:
                            filtered_fallacies.append(f)
                
                max_fallacies = self.config.get("max_fallacies", 5)
                if len(filtered_fallacies) > max_fallacies:
                    filtered_fallacies = sorted(filtered_fallacies, key=lambda f: f.get("confidence", 0), reverse=True)[:max_fallacies]
                
                self.logger.info(f"{len(filtered_fallacies)} sophismes (sémantiques) détectés et filtrés.")
                return filtered_fallacies
            except json.JSONDecodeError:
                self.logger.warning(f"Impossible de parser le résultat JSON de semantic_AnalyzeFallacies: {cleaned_json_str}")
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

    async def identify_arguments(self, text: str) -> Optional[List[str]]:
        """
        Identifie les arguments principaux dans un texte via une fonction sémantique.

        Args:
            text (str): Le texte à analyser.

        Returns:
            Optional[List[str]]: Une liste des arguments identifiés. Retourne `None`
            si une exception se produit pendant l'invocation du kernel. Retourne une
            liste vide si aucun argument n'est trouvé.
        """
        self.logger.info(f"Identification sémantique des arguments pour un texte de {len(text)} caractères...")
        try:
            arguments = KernelArguments(input=text)
            result = await self.kernel.invoke(
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
            return None

    async def analyze_argument(self, argument: str) -> Dict[str, Any]:
        """
        Effectue une analyse complète d'un argument unique en se concentrant sur les sophismes.

        Args:
            argument (str): L'argument à analyser.

        Returns:
            Dict[str, Any]: Un dictionnaire contenant l'argument original et les
            résultats de l'analyse des sophismes.
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
        Explore la hiérarchie des sophismes à partir d'un nœud donné via le plugin natif.

        Cette méthode invoque la fonction native (non-sémantique) du plugin
        `InformalAnalyzer` pour naviguer dans la taxonomie des sophismes.

        Args:
            current_pk (int): La clé primaire du nœud à partir duquel commencer l'exploration.
            max_children (int): Le nombre maximum d'enfants à retourner.

        Returns:
            Dict[str, Any]: Une représentation de la sous-hiérarchie, ou un dictionnaire
            d'erreur si le nœud n'est pas trouvé ou si une autre erreur se produit.
        """
        self.logger.info(f"Exploration de la hiérarchie des sophismes (natif) depuis PK {current_pk}...")
        try:
            arguments = KernelArguments(current_pk_str=str(current_pk), max_children=max_children)
            result = await self.kernel.invoke(
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
            result = await self.kernel.invoke(
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
        Orchestre une analyse complète d'un texte pour identifier et catégoriser les sophismes.

        Ce workflow combine plusieurs capacités de l'agent :
        1.  Appelle `analyze_fallacies` pour détecter les sophismes.
        2.  Appelle `categorize_fallacies` pour classer les sophismes trouvés.
        3.  Compile les résultats dans un rapport structuré.

        Args:
            text (str): Le texte à analyser.
            context (Optional[str]): Un contexte optionnel pour l'analyse (non utilisé actuellement).

        Returns:
            Dict[str, Any]: Un rapport d'analyse complet contenant les sophismes,
            leurs catégories, et d'autres métadonnées.
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
            if semantic_args is not None:
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

    async def get_response(self, messages: list[ChatMessageContent]) -> list[ChatMessageContent]:
        """(Compatibility) Gets a response from the agent."""
        warnings.warn(
            "The 'get_response' method is deprecated and will be removed in a future version. "
            "Please use 'invoke' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return await self.invoke(messages)

    async def invoke_single(self, messages: list[ChatMessageContent]) -> list[ChatMessageContent]:
        """
        Invokes the agent to analyze the last message for fallacies.
        """
        if not messages:
            return [ChatMessageContent(role="assistant", content="No messages to analyze.")]

        last_message = messages[-1].content
        
        # Call the core analysis method
        analysis_result = await self.analyze_text(text=str(last_message))
        
        # Format the response
        response_content = json.dumps(analysis_result, indent=2)
        
        return [ChatMessageContent(role="assistant", content=response_content, name=self.name)]

    async def invoke_stream(self, messages: list[ChatMessageContent]):
        # Implémentation de base pour le streaming.
        # Elle peut envelopper la réponse non-streamée dans un stream.
        final_result = await self.invoke(messages)
        
        async def stream_generator():
            yield final_result

        return stream_generator()
