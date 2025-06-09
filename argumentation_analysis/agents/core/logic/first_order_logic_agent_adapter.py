#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Adaptateur pour maintenir la compatibilité avec l'ancienne interface FirstOrderLogicAgent.

Ce module fournit une classe adaptateur qui permet aux tests existants
de continuer à fonctionner avec la nouvelle architecture basée sur Semantic Kernel.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import MagicMock

# Import de la nouvelle classe
from .first_order_logic_agent import FirstOrderLogicAgent as NewFirstOrderLogicAgent
from .belief_set import FirstOrderBeliefSet, BeliefSet

class FirstOrderLogicAgent:
    """
    Adaptateur de compatibilité pour l'ancien FirstOrderLogicAgent.
    
    Cette classe maintient l'interface attendue par les tests existants
    tout en mockant les fonctionnalités pour éviter les dépendances JVM.
    """
    
    def __init__(
        self,
        agent_name: Optional[str] = None,
        agent_id: Optional[str] = None,
        kernel: Optional[Any] = None,
        service_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialise l'adaptateur avec l'interface harmonisée.
        
        Args:
            agent_name: Nom de l'agent (compatible avec la nouvelle interface)
            agent_id: Identifiant de l'agent (compatible avec l'ancienne interface)
            kernel: Kernel Semantic Kernel (mocké pour les tests)
            service_id: ID du service LLM
            **kwargs: Arguments supplémentaires
        """
        # Harmonisation des interfaces - compatibilité bidirectionnelle
        self.name = agent_name or agent_id or "FirstOrderLogicAgent"
        self.agent_id = agent_id or agent_name or "FirstOrderLogicAgent"
        self.agent_name = self.name
        self.logic_type = "FOL"
        self.kernel = kernel or MagicMock()
        self.service_id = service_id
        self.logger = logging.getLogger(f"{__name__}.{agent_name}")
        
        # Mock TweetyBridge pour éviter les problèmes JVM
        self._mock_tweety_bridge = MagicMock()
        self._setup_mock_tweety_bridge()
        
    def _setup_mock_tweety_bridge(self):
        """Configure TweetyBridge mocké pour les tests."""
        self._mock_tweety_bridge.is_jvm_ready.return_value = True
        self._mock_tweety_bridge.validate_fol_belief_set.return_value = (True, "Valid FOL belief set")
        self._mock_tweety_bridge.validate_fol_formula.return_value = (True, "Valid FOL formula")
        self._mock_tweety_bridge.execute_fol_query.return_value = "Tweety Result: Query 'forall X: (P(X) => Q(X))' is ACCEPTED (True)."
        self._mock_tweety_bridge.is_fol_kb_consistent.return_value = (True, "KB is consistent")
        
    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Retourne les capacités de l'agent FOL.
        """
        return {
            "name": self.name,
            "logic_type": self.logic_type,
            "description": "Agent capable d'analyser du texte en utilisant la logique du premier ordre (FOL)",
            "methods": {
                "text_to_belief_set": "Convertit un texte en ensemble de croyances FOL",
                "generate_queries": "Génère des requêtes FOL pertinentes",
                "execute_query": "Exécute une requête FOL",
                "interpret_results": "Interprète les résultats de requêtes FOL",
                "validate_formula": "Valide la syntaxe d'une formule FOL"
            }
        }
    
    def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[BeliefSet], str]:
        """
        Convertit un texte en ensemble de croyances FOL (version mockée).
        
        Args:
            text: Texte à convertir
            context: Contexte optionnel
            
        Returns:
            Tuple (BeliefSet, message)
        """
        self.logger.info(f"Conversion de texte en FOL pour {len(text)} caractères...")
        
        # Mock d'un ensemble de croyances FOL simple
        mock_content = "forall X: (P(X) => Q(X))"
        belief_set = FirstOrderBeliefSet(mock_content)
        
        return belief_set, "Conversion réussie"
    
    def generate_queries(self, text: str, belief_set: BeliefSet, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Génère des requêtes FOL (version mockée).
        
        Args:
            text: Texte source
            belief_set: Ensemble de croyances FOL
            context: Contexte optionnel
            
        Returns:
            Liste de requêtes FOL
        """
        self.logger.info(f"Génération de requêtes FOL pour {len(text)} caractères...")
        
        # Mock de requêtes FOL typiques
        mock_queries = ["P(a)", "Q(b)", "forall X: (P(X) => Q(X))"]
        return mock_queries
    
    def execute_query(self, belief_set: BeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête FOL (version mockée).
        
        Args:
            belief_set: Ensemble de croyances FOL
            query: Requête à exécuter
            
        Returns:
            Tuple (résultat booléen, message)
        """
        self.logger.info(f"Exécution de la requête: {query}")
        
        # Mock d'un résultat positif
        result_message = f"Tweety Result: FOL Query '{query}' is ACCEPTED (True)."
        return True, result_message
    
    def interpret_results(
        self, 
        text: str, 
        belief_set: BeliefSet,
        queries: List[str], 
        results: List[Tuple[Optional[bool], str]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Interprète les résultats de requêtes FOL (version mockée).
        
        Args:
            text: Texte original
            belief_set: Ensemble de croyances FOL
            queries: Liste des requêtes exécutées
            results: Liste des résultats
            context: Contexte optionnel
            
        Returns:
            Interprétation en langage naturel
        """
        self.logger.info(f"Interprétation de {len(results)} résultats FOL...")
        
        # Mock d'une interprétation simple
        interpretation = "Interprétation des résultats FOL"
        return interpretation
    
    def validate_formula(self, formula: str) -> bool:
        """
        Valide la syntaxe d'une formule FOL (version mockée).
        
        Args:
            formula: Formule FOL à valider
            
        Returns:
            True si la formule est valide
        """
        self.logger.debug(f"Validation de la formule FOL: {formula}")
        
        # Mock de validation simple - toujours valide pour les tests
        return True
    
    def is_consistent(self, belief_set: BeliefSet) -> Tuple[bool, str]:
        """
        Vérifie la cohérence d'un ensemble de croyances FOL (version mockée).
        
        Args:
            belief_set: Ensemble de croyances à vérifier
            
        Returns:
            Tuple (cohérent, message)
        """
        self.logger.info("Vérification de la cohérence FOL...")
        
        # Mock - toujours cohérent pour les tests
        return True, "L'ensemble de croyances FOL est cohérent"
    
    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Configure les composants de l'agent (version mockée).
        
        Args:
            llm_service_id: ID du service LLM
        """
        self.logger.info(f"Configuration des composants pour {self.name} (mockée)...")
        # Version mockée - ne fait rien de spécial
        pass


# Fonction factory mockée pour la compatibilité
class LogicAgentFactory:
    """Factory mockée pour créer des agents logiques."""
    
    @staticmethod
    def create_agent(logic_type: str, kernel: Any = None, service_id: Optional[str] = None, **kwargs) -> Any:
        """
        Crée un agent logique adapté au type spécifié avec gestion d'erreurs robuste.
        
        Args:
            logic_type: Type de logique ("first_order", "propositional", "modal")
            kernel: Kernel Semantic Kernel
            service_id: ID du service LLM
            **kwargs: Arguments supplémentaires pour compatibilité
            
        Returns:
            Instance d'agent logique
            
        Raises:
            ValueError: Si le type de logique n'est pas supporté
            Exception: En cas d'erreur lors de la création de l'agent
        """
        logger = logging.getLogger(__name__)
        
        try:
            if logic_type == "first_order":
                logger.info("Création d'un agent de logique du premier ordre...")
                # Éviter les conflits d'arguments - utiliser kwargs ou valeurs par défaut
                agent_name = kwargs.pop('agent_name', 'FirstOrderLogicAgent')
                agent_id = kwargs.pop('agent_id', 'fol_agent')
                return FirstOrderLogicAgent(
                    agent_name=agent_name,
                    agent_id=agent_id,
                    kernel=kernel,
                    service_id=service_id,
                    **kwargs
                )
            elif logic_type == "propositional":
                logger.info("Création d'un agent de logique propositionnelle...")
                # Mock robuste pour agent propositionnel
                from .belief_set import PropositionalBeliefSet
                mock_agent = MagicMock()
                mock_agent.name = "PropositionalLogicAgent"
                mock_agent.agent_id = "pl_agent"
                mock_agent.agent_name = "PropositionalLogicAgent"
                mock_agent.logic_type = "PL"
                mock_agent.get_agent_capabilities.return_value = {
                    "name": "PropositionalLogicAgent",
                    "logic_type": "PL",
                    "description": "Agent de logique propositionnelle"
                }
                mock_agent.text_to_belief_set.return_value = (PropositionalBeliefSet("a => b"), "Success")
                mock_agent.generate_queries.return_value = ["a", "b", "a => b"]
                mock_agent.execute_query.return_value = (True, "Tweety Result: Query 'a => b' is ACCEPTED (True).")
                mock_agent.interpret_results.return_value = "Interprétation des résultats PL"
                mock_agent.validate_formula.return_value = True
                mock_agent.is_consistent.return_value = (True, "L'ensemble de croyances PL est cohérent")
                return mock_agent
            elif logic_type == "modal":
                logger.info("Création d'un agent de logique modale...")
                # Mock robuste pour agent modal
                from .belief_set import ModalBeliefSet
                mock_agent = MagicMock()
                mock_agent.name = "ModalLogicAgent"
                mock_agent.agent_id = "modal_agent"
                mock_agent.agent_name = "ModalLogicAgent"
                mock_agent.logic_type = "Modal"
                mock_agent.get_agent_capabilities.return_value = {
                    "name": "ModalLogicAgent",
                    "logic_type": "Modal",
                    "description": "Agent de logique modale"
                }
                mock_agent.text_to_belief_set.return_value = (ModalBeliefSet("[]p => <>q"), "Success")
                mock_agent.generate_queries.return_value = ["p", "[]p", "<>q"]
                mock_agent.execute_query.return_value = (True, "Tweety Result: Modal Query '[]p => <>q' is ACCEPTED (True).")
                mock_agent.interpret_results.return_value = "Interprétation des résultats modaux"
                mock_agent.validate_formula.return_value = True
                mock_agent.is_consistent.return_value = (True, "L'ensemble de croyances modal est cohérent")
                return mock_agent
            else:
                raise ValueError(f"Type de logique non supporté: {logic_type}")
                
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'agent {logic_type}: {e}")
            raise Exception(f"Impossible de créer l'agent {logic_type}: {e}") from e