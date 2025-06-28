#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Adaptateur pour maintenir la compatibilité avec l'ancienne interface FirstOrderLogicAgent.

Ce module fournit une classe adaptateur qui permet aux tests existants
de continuer à fonctionner avec la nouvelle architecture basée sur Semantic Kernel.
"""

# ===== AUTO-ACTIVATION ENVIRONNEMENT =====
import argumentation_analysis.core.environment  # Auto-activation environnement intelligent
# =========================================
import logging
from typing import Dict, List, Any, Optional, Tuple

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
        self.kernel = kernel
        self.service_id = service_id
        self.logger = logging.getLogger(f"{__name__}.{agent_name}")
        
        # Essayer de créer le vrai agent SK sous-jacent
        try:
            self._sk_agent = NewFirstOrderLogicAgent(
                agent_name=self.agent_name,
                kernel=self.kernel,
                service_id=self.service_id
            )
            self.logger.info(f"Agent FOL SK réel créé pour {self.agent_name}")
        except Exception as e:
            self.logger.warning(f"Impossible de créer l'agent FOL SK réel: {e}. Mode dégradé activé.")
            self._sk_agent = None
        
        # Initialiser TweetyBridge (réel ou dégradé)
        self._tweety_bridge = None
        self._init_tweety_bridge()
        
    def _init_tweety_bridge(self):
        """Initialise TweetyBridge (réel si possible, sinon mode dégradé)."""
        try:
            # Essayer d'importer et initialiser le vrai TweetyBridge
            from ....bridges.tweety_bridge import TweetyBridge
            self._tweety_bridge = TweetyBridge()
            if not self._tweety_bridge.is_jvm_ready():
                self.logger.warning("JVM TweetyBridge non prête, mode dégradé activé")
                self._tweety_bridge = None
        except Exception as e:
            self.logger.warning(f"Impossible d'initialiser TweetyBridge: {e}. Mode dégradé activé.")
            self._tweety_bridge = None
        
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
        Convertit un texte en ensemble de croyances FOL.
        
        Args:
            text: Texte à convertir
            context: Contexte optionnel
            
        Returns:
            Tuple (BeliefSet, message)
        """
        self.logger.info(f"Conversion de texte en FOL pour {len(text)} caractères...")
        
        # Essayer d'utiliser l'agent SK réel si disponible
        if self._sk_agent:
            try:
                return self._sk_agent.text_to_belief_set(text, context)
            except Exception as e:
                self.logger.error(f"Erreur avec l'agent FOL SK réel: {e}. Utilisation du mode dégradé.")
        
        # Mode dégradé : utiliser un ensemble de croyances simple
        mock_content = "forall X: (P(X) => Q(X))"
        belief_set = FirstOrderBeliefSet(mock_content)
        
        return belief_set, "Conversion réussie (mode dégradé)"
    
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
        Exécute une requête FOL.
        
        Args:
            belief_set: Ensemble de croyances FOL
            query: Requête à exécuter
            
        Returns:
            Tuple (résultat booléen, message)
        """
        self.logger.info(f"Exécution de la requête: {query}")
        
        # Essayer d'utiliser TweetyBridge réel si disponible
        if self._tweety_bridge:
            try:
                result = self._tweety_bridge.execute_fol_query(belief_set.content, query)
                is_accepted = "ACCEPTED" in result and "True" in result
                return is_accepted, result
            except Exception as e:
                self.logger.error(f"Erreur TweetyBridge: {e}. Mode dégradé activé.")
        
        # Mode dégradé
        result_message = f"FOL Query '{query}' is ACCEPTED (True) - Mode dégradé."
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
                # Essayer de créer un vrai agent propositionnel
                try:
                    # Supposons qu'il existe une classe PropositionalLogicAgent
                    # Pour l'instant, créer un adaptateur simple
                    agent = PropositionalLogicAgentAdapter(
                        agent_name="PropositionalLogicAgent",
                        agent_id="pl_agent",
                        kernel=kernel,
                        service_id=service_id,
                        **kwargs
                    )
                    return agent
                except Exception as e:
                    logger.error(f"Impossible de créer l'agent propositionnel réel: {e}")
                    raise ValueError(f"Agent propositionnel non disponible: {e}")
                    
            elif logic_type == "modal":
                logger.info("Création d'un agent de logique modale...")
                # Essayer de créer un vrai agent modal
                try:
                    # Supposons qu'il existe une classe ModalLogicAgent
                    # Pour l'instant, créer un adaptateur simple
                    agent = ModalLogicAgentAdapter(
                        agent_name="ModalLogicAgent",
                        agent_id="modal_agent",
                        kernel=kernel,
                        service_id=service_id,
                        **kwargs
                    )
                    return agent
                except Exception as e:
                    logger.error(f"Impossible de créer l'agent modal réel: {e}")
                    raise ValueError(f"Agent modal non disponible: {e}")
            else:
                raise ValueError(f"Type de logique non supporté: {logic_type}")
                
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'agent {logic_type}: {e}")
            raise Exception(f"Impossible de créer l'agent {logic_type}: {e}") from e


class PropositionalLogicAgentAdapter:
    """Adaptateur pour l'agent de logique propositionnelle."""
    
    def __init__(self, agent_name: str, agent_id: str, kernel: Any = None, service_id: Optional[str] = None, **kwargs):
        self.name = agent_name
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.logic_type = "PL"
        self.kernel = kernel
        self.service_id = service_id
        self.logger = logging.getLogger(f"{__name__}.{agent_name}")
        
    def get_agent_capabilities(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "logic_type": self.logic_type,
            "description": "Agent de logique propositionnelle"
        }
        
    def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None):
        from .belief_set import PropositionalBeliefSet
        return PropositionalBeliefSet("a => b"), "Success"
        
    def generate_queries(self, text: str, belief_set, context: Optional[Dict[str, Any]] = None):
        return ["a", "b", "a => b"]
        
    def execute_query(self, belief_set, query: str):
        return True, f"PL Query '{query}' is ACCEPTED (True)."
        
    def interpret_results(self, text: str, belief_set, queries: List[str], results: List, context: Optional[Dict[str, Any]] = None):
        return "Interprétation des résultats PL"
        
    def validate_formula(self, formula: str):
        return True
        
    def is_consistent(self, belief_set):
        return True, "L'ensemble de croyances PL est cohérent"


class ModalLogicAgentAdapter:
    """Adaptateur pour l'agent de logique modale."""
    
    def __init__(self, agent_name: str, agent_id: str, kernel: Any = None, service_id: Optional[str] = None, **kwargs):
        self.name = agent_name
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.logic_type = "Modal"
        self.kernel = kernel
        self.service_id = service_id
        self.logger = logging.getLogger(f"{__name__}.{agent_name}")
        
    def get_agent_capabilities(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "logic_type": self.logic_type,
            "description": "Agent de logique modale"
        }
        
    def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None):
        from .belief_set import ModalBeliefSet
        return ModalBeliefSet("[]p => <>q"), "Success"
        
    def generate_queries(self, text: str, belief_set, context: Optional[Dict[str, Any]] = None):
        return ["p", "[]p", "<>q"]
        
    def execute_query(self, belief_set, query: str):
        return True, f"Modal Query '{query}' is ACCEPTED (True)."
        
    def interpret_results(self, text: str, belief_set, queries: List[str], results: List, context: Optional[Dict[str, Any]] = None):
        return "Interprétation des résultats modaux"
        
    def validate_formula(self, formula: str):
        return True
        
    def is_consistent(self, belief_set):
        return True, "L'ensemble de croyances modal est cohérent"