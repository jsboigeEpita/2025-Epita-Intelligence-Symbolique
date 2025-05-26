#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Agent Informel pour l'analyse des sophismes dans les arguments.

Cet agent utilise différents outils pour analyser les sophismes dans les arguments:
1. Un détecteur de sophismes (obligatoire)
2. Un analyseur rhétorique (optionnel)
3. Un analyseur contextuel (optionnel)

Il peut également utiliser un kernel sémantique pour des analyses plus avancées.
"""

import logging
import json
from typing import Dict, List, Any, Optional
import semantic_kernel as sk

# Import des définitions et des prompts
from .informal_definitions import InformalAnalysisPlugin, setup_informal_kernel

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)

class InformalAgent:
    """
    Agent pour l'analyse informelle des arguments et des sophismes.
    
    Cet agent utilise différents outils pour analyser les sophismes dans les arguments.
    Il peut également utiliser un kernel sémantique pour des analyses plus avancées.
    """
    
    def __init__(
        self,
        agent_id: str,
        tools: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
        semantic_kernel: Optional[sk.Kernel] = None,
        informal_plugin: Optional[InformalAnalysisPlugin] = None
    ):
        """
        Initialise l'agent informel.
        
        Args:
            agent_id: Identifiant unique de l'agent
            tools: Dictionnaire des outils disponibles pour l'agent
            config: Configuration optionnelle de l'agent
            semantic_kernel: Kernel sémantique optionnel pour les analyses avancées
            informal_plugin: Plugin d'analyse informelle optionnel
        
        Raises:
            ValueError: Si aucun outil n'est fourni ou si le détecteur de sophismes est manquant
            TypeError: Si un outil fourni n'est pas valide
        """
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"InformalAgent:{agent_id}")
        self.logger.info(f"Initialisation de l'agent informel {agent_id}...")
        
        # Vérifier que les outils sont valides
        if not tools:
            raise ValueError("Aucun outil fourni pour l'agent informel")
        
        # Vérifier que le détecteur de sophismes est présent
        if "fallacy_detector" not in tools:
            raise ValueError("Le détecteur de sophismes est requis pour l'agent informel")
        
        # Vérifier que tous les outils sont valides
        for tool_name, tool in tools.items():
            if not callable(tool) and not isinstance(tool, object) or isinstance(tool, (int, float, str, bool)):
                raise TypeError(f"L'outil {tool_name} n'est pas valide")
        
        self.tools = tools
        self.config = config or {
            "analysis_depth": "standard",
            "confidence_threshold": 0.5,
            "max_fallacies": 5,
            "include_context": False
        }
        
        # Kernel sémantique et plugin informel
        self.semantic_kernel = semantic_kernel
        self.informal_plugin = informal_plugin
        
        # Si un kernel sémantique est fourni, configurer le plugin informel
        if self.semantic_kernel:
            setup_informal_kernel(self.semantic_kernel, None)
        
        self.logger.info(f"Agent informel {agent_id} initialisé avec {len(tools)} outils")
    
    def get_available_tools(self) -> List[str]:
        """
        Retourne la liste des outils disponibles pour l'agent.
        
        Returns:
            Liste des noms des outils disponibles
        """
        return list(self.tools.keys())
    
    def get_agent_capabilities(self) -> Dict[str, bool]:
        """
        Retourne les capacités de l'agent en fonction des outils disponibles.
        
        Returns:
            Dictionnaire des capacités de l'agent
        """
        capabilities = {
            "fallacy_detection": "fallacy_detector" in self.tools,
            "rhetorical_analysis": "rhetorical_analyzer" in self.tools,
            "contextual_analysis": "contextual_analyzer" in self.tools
        }
        return capabilities
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Retourne les informations sur l'agent.
        
        Returns:
            Dictionnaire des informations sur l'agent
        """
        return {
            "agent_id": self.agent_id,
            "agent_type": "informal",
            "capabilities": self.get_agent_capabilities(),
            "tools": self.get_available_tools()
        }
    
    def analyze_fallacies(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyse les sophismes dans un texte.
        
        Args:
            text: Texte à analyser
        
        Returns:
            Liste des sophismes détectés
        """
        self.logger.info(f"Analyse des sophismes dans un texte de {len(text)} caractères...")
        
        # Utiliser le détecteur de sophismes
        fallacies = self.tools["fallacy_detector"].detect(text)
        
        # Filtrer les sophismes selon le seuil de confiance
        confidence_threshold = self.config.get("confidence_threshold", 0.5)
        fallacies = [f for f in fallacies if f.get("confidence", 0) >= confidence_threshold]
        
        # Limiter le nombre de sophismes
        max_fallacies = self.config.get("max_fallacies", 5)
        if len(fallacies) > max_fallacies:
            fallacies = sorted(fallacies, key=lambda f: f.get("confidence", 0), reverse=True)[:max_fallacies]
        
        self.logger.info(f"{len(fallacies)} sophismes détectés")
        return fallacies
    
    def analyze_rhetoric(self, text: str) -> Dict[str, Any]:
        """
        Analyse la rhétorique d'un texte.
        
        Args:
            text: Texte à analyser
        
        Returns:
            Résultats de l'analyse rhétorique
        
        Raises:
            ValueError: Si l'analyseur rhétorique n'est pas disponible
        """
        if "rhetorical_analyzer" not in self.tools:
            raise ValueError("L'analyseur rhétorique n'est pas disponible")
        
        self.logger.info(f"Analyse rhétorique d'un texte de {len(text)} caractères...")
        return self.tools["rhetorical_analyzer"].analyze(text)
    
    def analyze_context(self, text: str) -> Dict[str, Any]:
        """
        Analyse le contexte d'un texte.
        
        Args:
            text: Texte à analyser
        
        Returns:
            Résultats de l'analyse contextuelle
        
        Raises:
            ValueError: Si l'analyseur contextuel n'est pas disponible
        """
        if "contextual_analyzer" not in self.tools:
            raise ValueError("L'analyseur contextuel n'est pas disponible")
        
        self.logger.info(f"Analyse contextuelle d'un texte de {len(text)} caractères...")
        return self.tools["contextual_analyzer"].analyze_context(text)
    
    def identify_arguments(self, text: str) -> List[str]:
        """
        Identifie les arguments dans un texte en utilisant le kernel sémantique.
        
        Args:
            text: Texte à analyser
        
        Returns:
            Liste des arguments identifiés
        
        Raises:
            ValueError: Si le kernel sémantique n'est pas disponible
        """
        if not self.semantic_kernel:
            raise ValueError("Le kernel sémantique n'est pas disponible")
        
        self.logger.info(f"Identification des arguments dans un texte de {len(text)} caractères...")
        
        try:
            # Utiliser la fonction sémantique pour identifier les arguments
            result = self.semantic_kernel.invoke("InformalAnalyzer", "semantic_IdentifyArguments", input=text)
            
            # Traiter le résultat
            arguments = str(result).strip().split("\n")
            arguments = [arg.strip() for arg in arguments if arg.strip()]
            
            self.logger.info(f"{len(arguments)} arguments identifiés")
            return arguments
        except Exception as e:
            self.logger.error(f"Erreur lors de l'identification des arguments: {e}")
            return []
    
    def analyze_argument(self, argument: str) -> Dict[str, Any]:
        """
        Analyse complète d'un argument (sophismes, rhétorique, contexte).
        
        Args:
            argument: Argument à analyser
        
        Returns:
            Résultats de l'analyse
        """
        self.logger.info(f"Analyse complète d'un argument de {len(argument)} caractères...")
        
        results = {
            "argument": argument,
            "fallacies": self.analyze_fallacies(argument)
        }
        
        # Ajouter l'analyse rhétorique si disponible
        if "rhetorical_analyzer" in self.tools:
            try:
                results["rhetoric"] = self.analyze_rhetoric(argument)
            except Exception as e:
                self.logger.error(f"Erreur lors de l'analyse rhétorique: {e}")
        
        # Ajouter l'analyse contextuelle si disponible et demandée
        if "contextual_analyzer" in self.tools and self.config.get("include_context", False):
            try:
                results["context"] = self.analyze_context(argument)
            except Exception as e:
                self.logger.error(f"Erreur lors de l'analyse contextuelle: {e}")
        
        return results
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyse complète d'un texte (identification des arguments et analyse de chaque argument).
        
        Args:
            text: Texte à analyser
        
        Returns:
            Résultats de l'analyse
        """
        self.logger.info(f"Analyse complète d'un texte de {len(text)} caractères...")
        
        # Identifier les arguments
        arguments = self.identify_arguments(text) if self.semantic_kernel else [text]
        
        # Analyser chaque argument
        results = {
            "text": text,
            "arguments": []
        }
        
        for i, arg in enumerate(arguments):
            self.logger.info(f"Analyse de l'argument {i+1}/{len(arguments)}...")
            arg_analysis = self.analyze_argument(arg)
            results["arguments"].append(arg_analysis)
        
        return results
    
    def explore_fallacy_hierarchy(self, current_pk: int = 0) -> Dict[str, Any]:
        """
        Explore la hiérarchie des sophismes à partir d'un nœud donné.
        
        Args:
            current_pk: PK du nœud à explorer
        
        Returns:
            Résultats de l'exploration
        
        Raises:
            ValueError: Si le plugin informel n'est pas disponible
        """
        if not self.informal_plugin:
            raise ValueError("Le plugin informel n'est pas disponible")
        
        self.logger.info(f"Exploration de la hiérarchie des sophismes depuis PK {current_pk}...")
        
        try:
            result_json = self.informal_plugin.explore_fallacy_hierarchy(str(current_pk))
            return json.loads(result_json)
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exploration de la hiérarchie: {e}")
            return {"error": str(e)}
    
    def get_fallacy_details(self, fallacy_pk: int) -> Dict[str, Any]:
        """
        Obtient les détails d'un sophisme spécifique.
        
        Args:
            fallacy_pk: PK du sophisme
        
        Returns:
            Détails du sophisme
        
        Raises:
            ValueError: Si le plugin informel n'est pas disponible
        """
        if not self.informal_plugin:
            raise ValueError("Le plugin informel n'est pas disponible")
        
        self.logger.info(f"Récupération des détails du sophisme PK {fallacy_pk}...")
        
        try:
            result_json = self.informal_plugin.get_fallacy_details(str(fallacy_pk))
            return json.loads(result_json)
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des détails du sophisme: {e}")
            return {"error": str(e)}
    def categorize_fallacies(self, fallacies: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Catégorise les sophismes détectés selon leur type.
        
        Args:
            fallacies: Liste des sophismes à catégoriser
        
        Returns:
            Dictionnaire des catégories avec les types de sophismes
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
    
    def perform_complete_analysis(self, text: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Effectue une analyse complète d'un texte (sophismes, rhétorique, contexte).
        
        Args:
            text: Texte à analyser
            context: Contexte optionnel pour l'analyse
        
        Returns:
            Résultats de l'analyse complète
        """
        self.logger.info(f"Analyse complète d'un texte de {len(text)} caractères...")
        
        results = {
            "text": text,
            "context": context,
            "fallacies": [],
            "rhetorical_analysis": {},
            "contextual_analysis": {},
            "categories": {}
        }
        
        try:
            # Analyse des sophismes
            fallacies = self.analyze_fallacies(text)
            results["fallacies"] = fallacies
            
            # Catégorisation des sophismes
            if fallacies:
                results["categories"] = self.categorize_fallacies(fallacies)
            
            # Analyse rhétorique si disponible
            if "rhetorical_analyzer" in self.tools:
                try:
                    results["rhetorical_analysis"] = self.analyze_rhetoric(text)
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'analyse rhétorique: {e}")
                    results["rhetorical_analysis"] = {"error": str(e)}
            
            # Analyse contextuelle si disponible et contexte fourni
            if "contextual_analyzer" in self.tools and (context or self.config.get("include_context", False)):
                try:
                    results["contextual_analysis"] = self.analyze_context(text)
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'analyse contextuelle: {e}")
                    results["contextual_analysis"] = {"error": str(e)}
            
            self.logger.info("Analyse complète terminée avec succès")
            return results
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse complète: {e}")
            results["error"] = str(e)
            return results
    
    def _extract_arguments(self, text: str) -> List[Dict[str, Any]]:
        """
        Extrait les arguments d'un texte de manière structurée.
        
        Args:
            text: Texte à analyser
        
        Returns:
            Liste des arguments extraits avec leurs composants
        """
        self.logger.info(f"Extraction des arguments d'un texte de {len(text)} caractères...")
        
        arguments = []
        
        try:
            # Utiliser le kernel sémantique si disponible
            if self.semantic_kernel:
                semantic_args = self.identify_arguments(text)
                for i, arg_text in enumerate(semantic_args):
                    arguments.append({
                        "id": f"arg-{i+1}",
                        "text": arg_text,
                        "type": "semantic",
                        "confidence": 0.8
                    })
            else:
                # Méthode de base : diviser par paragraphes ou phrases
                paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                
                if not paragraphs:
                    # Diviser par phrases si pas de paragraphes
                    import re
                    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
                    
                    # Regrouper les phrases en arguments
                    for i in range(0, len(sentences), 2):
                        arg_text = '. '.join(sentences[i:i+2])
                        if arg_text:
                            arguments.append({
                                "id": f"arg-{len(arguments)+1}",
                                "text": arg_text + '.',
                                "type": "sentence_group",
                                "confidence": 0.6
                            })
                else:
                    # Utiliser les paragraphes comme arguments
                    for i, paragraph in enumerate(paragraphs):
                        arguments.append({
                            "id": f"arg-{i+1}",
                            "text": paragraph,
                            "type": "paragraph",
                            "confidence": 0.7
                        })
            
            self.logger.info(f"{len(arguments)} arguments extraits")
            return arguments
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction des arguments: {e}")
            return []
    
    def _process_text(self, text: str) -> Dict[str, Any]:
        """
        Traite et analyse les propriétés de base d'un texte.
        
        Args:
            text: Texte à traiter
        
        Returns:
            Dictionnaire avec les propriétés du texte
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
    
    def analyze_and_categorize(self, text: str) -> Dict[str, Any]:
        """
        Analyse un texte et catégorise les sophismes trouvés.
        
        Args:
            text: Texte à analyser
        
        Returns:
            Résultats de l'analyse avec catégorisation
        """
        self.logger.info(f"Analyse et catégorisation d'un texte de {len(text)} caractères...")
        
        try:
            # Analyser les sophismes
            fallacies = self.analyze_fallacies(text)
            
            # Catégoriser les sophismes
            categories = self.categorize_fallacies(fallacies) if fallacies else {}
            
            result = {
                "text": text,
                "fallacies": fallacies,
                "categories": categories,
                "summary": {
                    "total_fallacies": len(fallacies),
                    "categories_count": len([cat for cat, items in categories.items() if items])
                }
            }
            
            self.logger.info(f"Analyse terminée: {len(fallacies)} sophismes trouvés")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse et catégorisation: {e}")
            return {
                "text": text,
                "fallacies": [],
                "categories": {},
                "error": str(e)
            }

# Log de chargement
logging.getLogger(__name__).debug("Module agents.core.informal.informal_agent chargé.")