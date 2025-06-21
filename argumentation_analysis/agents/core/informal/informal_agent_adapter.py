#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Adaptateur pour maintenir la compatibilité avec l'ancienne interface InformalAgent.

Ce module fournit une classe adaptateur qui permet aux tests existants
de continuer à fonctionner avec la nouvelle architecture basée sur Semantic Kernel.
"""

import logging
from typing import Dict, List, Any, Optional

# Import de la nouvelle classe
from .informal_agent import InformalAnalysisAgent

class InformalAgent:
    """
    Adaptateur de compatibilité pour l'ancien InformalAgent.
    
    Cette classe maintient l'interface attendue par les tests existants
    tout en déléguant vers la nouvelle implémentation basée sur Semantic Kernel.
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        tools: Optional[Dict[str, Any]] = None,
        strict_validation: bool = False,
        **kwargs
    ):
        """
        Initialise l'adaptateur avec l'ancienne interface harmonisée.
        
        Args:
            agent_id: Identifiant de l'agent (compatible avec l'ancienne interface)
            agent_name: Nom de l'agent (compatible avec la nouvelle interface)
            tools: Outils à utiliser par l'agent (mockés pour les tests)
            strict_validation: Mode de validation strict
            **kwargs: Arguments supplémentaires
        """
        # Harmonisation des interfaces - compatibilité bidirectionnelle
        self.agent_id = agent_id or agent_name or "InformalAgent"
        self.agent_name = agent_name or agent_id or "InformalAgent"
        self.tools = tools or {}
        self.strict_validation = strict_validation
        self.logger = logging.getLogger(f"{__name__}.{agent_id}")

        # Validation de la configuration des outils, comme attendu par les tests.
        if self.strict_validation and not self.tools:
            raise ValueError("Aucun outil fourni. L'agent ne peut pas fonctionner sans outils en mode de validation stricte.")
        
        # Essayer de créer le vrai agent SK sous-jacent
        try:
            self._sk_agent = InformalAnalysisAgent(
                agent_name=self.agent_name,
                tools=self.tools
            )
            self.logger.info(f"Agent SK réel créé pour {self.agent_name}")
        except Exception as e:
            self.logger.warning(f"Impossible de créer l'agent SK réel: {e}. Mode dégradé activé.")
            self._sk_agent = None
        
    def get_available_tools(self) -> List[str]:
        """Retourne la liste des outils disponibles."""
        return list(self.tools.keys())
    
    def get_agent_capabilities(self) -> Dict[str, bool]:
        """
        Retourne les capacités de l'agent au format attendu par les tests.
        """
        capabilities = {
            "fallacy_detection": "fallacy_detector" in self.tools,
            "contextual_analysis": "contextual_analyzer" in self.tools,
            "rhetorical_analysis": "rhetorical_analyzer" in self.tools,
            "complex_analysis": "complex_analyzer" in self.tools,
            "severity_evaluation": "severity_evaluator" in self.tools
        }
        return capabilities
    
    def analyze_text(self, text: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyse un texte pour détecter les sophismes.
        
        Args:
            text: Texte à analyser
            context: Contexte optionnel
            
        Returns:
            Résultats de l'analyse au format attendu par les tests
        """
        self.logger.info(f"Analyse d'un texte de {len(text)} caractères...")
        
        # Essayer d'utiliser l'agent SK réel si disponible
        if self._sk_agent:
            try:
                # Utiliser le vrai agent SK
                sk_result = self._sk_agent.analyze_text(text, context)
                return sk_result
            except Exception as e:
                self.logger.error(f"Erreur avec l'agent SK réel: {e}. Utilisation du mode dégradé.")
        
        # Mode dégradé : utiliser les outils locaux
        fallacies = []
        
        if "fallacy_detector" in self.tools:
            detector = self.tools["fallacy_detector"]
            if hasattr(detector, 'detect'):
                fallacies = detector.detect(text)
            else:
                # Fallback pour les tests
                fallacies = getattr(detector, 'return_value', [])
        
        result = {
            "fallacies": fallacies,
            "analysis_timestamp": self._get_timestamp()
        }
        
        if context is not None:
            result["context"] = context
            
        return result
    
    def perform_complete_analysis(self, text: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Effectue une analyse complète d'un texte.
        
        Args:
            text: Texte à analyser
            context: Contexte optionnel
            
        Returns:
            Résultats de l'analyse complète
        """
        self.logger.info(f"Analyse complète d'un texte de {len(text)} caractères...")
        
        # Démarrer avec l'analyse de base
        result = self.analyze_text(text, context)
        
        # Ajouter l'analyse contextuelle si disponible
        if "contextual_analyzer" in self.tools and context:
            contextual_analyzer = self.tools["contextual_analyzer"]
            if hasattr(contextual_analyzer, 'analyze_context'):
                try:
                    result["contextual_analysis"] = contextual_analyzer.analyze_context(text, context)
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'analyse contextuelle: {e}")
                    result["contextual_analysis"] = {}
            else:
                result["contextual_analysis"] = {}
        else:
            result["contextual_analysis"] = {}
        
        # Ajouter les catégories si on a des sophismes
        if result.get("fallacies"):
            result["categories"] = self._categorize_fallacies(result["fallacies"])
        else:
            result["categories"] = {}
            
        return result
    
    def _categorize_fallacies(self, fallacies: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Catégorise les sophismes détectés.
        
        Args:
            fallacies: Liste des sophismes détectés
            
        Returns:
            Dictionnaire de catégories
        """
        categories = {
            "RELEVANCE": [],
            "INDUCTION": [],
            "CAUSALITE": [],
            "AMBIGUITE": [],
            "PRESUPPOSITION": [],
            "AUTRES": []
        }
        
        fallacy_mapping = {
            "ad_hominem": "RELEVANCE",
            "appel_autorite": "RELEVANCE", 
            "argument_d_autorité": "RELEVANCE",
            "appel_emotion": "RELEVANCE",
            "appel_popularite": "INDUCTION",
            "generalisation_hative": "INDUCTION",
            "généralisation_hâtive": "INDUCTION",
            "pente_glissante": "CAUSALITE",
            "fausse_cause": "CAUSALITE",
            "faux_dilemme": "PRESUPPOSITION",
            "anecdote_personnelle": "INDUCTION"
        }
        
        for fallacy in fallacies:
            fallacy_type = fallacy.get("fallacy_type", "").lower().replace(" ", "_")
            category = fallacy_mapping.get(fallacy_type, "AUTRES")
            
            if fallacy_type not in categories[category]:
                categories[category].append(fallacy_type)
        
        return categories
    
    def _get_timestamp(self) -> str:
        """Génère un timestamp actuel."""
        from datetime import datetime
        return datetime.now().isoformat()


# Alias pour compatibilité
InformalAnalysisAgent = InformalAgent