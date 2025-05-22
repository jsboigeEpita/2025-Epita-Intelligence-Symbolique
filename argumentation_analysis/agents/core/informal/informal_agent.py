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

# Log de chargement
logging.getLogger(__name__).debug("Module agents.core.informal.informal_agent chargé.")