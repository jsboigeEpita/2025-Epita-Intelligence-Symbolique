# argumentation_analysis/agents/core/logic/logic_factory.py
"""
Factory pour créer les agents logiques appropriés.
"""

import logging
from typing import Dict, Optional, Any, Type

from semantic_kernel import Kernel

from .abstract_logic_agent import AbstractLogicAgent
from .propositional_logic_agent import PropositionalLogicAgent
from .first_order_logic_agent import FirstOrderLogicAgent
from .modal_logic_agent import ModalLogicAgent

# Configuration du logger
logger = logging.getLogger("Orchestration.LogicAgentFactory")

class LogicAgentFactory:
    """
    Factory pour créer les agents logiques appropriés.
    
    Cette classe permet de créer des instances d'agents logiques
    en fonction du type de logique spécifié.
    """
    
    # Mapping des types de logique vers les classes d'agents
    _agent_classes: Dict[str, Type[AbstractLogicAgent]] = {
        "propositional": PropositionalLogicAgent,
        "first_order": FirstOrderLogicAgent,
        "modal": ModalLogicAgent
    }
    
    @classmethod
    def create_agent(cls, logic_type: str, kernel: Kernel, llm_service=None) -> Optional[AbstractLogicAgent]:
        """
        Crée un agent logique du type spécifié.
        
        Args:
            logic_type: Le type de logique ("propositional", "first_order", "modal")
            kernel: Le kernel Semantic Kernel à utiliser
            llm_service: Le service LLM à utiliser (optionnel)
            
        Returns:
            Une instance de l'agent logique approprié, ou None si le type n'est pas supporté
        """
        logger.info(f"Création d'un agent logique de type '{logic_type}'")
        
        # Normaliser le type de logique
        logic_type = logic_type.lower().strip()
        
        # Vérifier si le type de logique est supporté
        if logic_type not in cls._agent_classes:
            logger.error(f"Type de logique non supporté: {logic_type}")
            logger.info(f"Types supportés: {', '.join(cls._agent_classes.keys())}")
            return None
        
        try:
            # Créer l'instance de l'agent
            agent_class = cls._agent_classes[logic_type]
            agent = agent_class(kernel)
            
            # Configurer le kernel de l'agent si un service LLM est fourni
            if llm_service:
                agent.setup_kernel(llm_service)
            
            logger.info(f"Agent logique de type '{logic_type}' créé avec succès")
            return agent
        
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'agent logique de type '{logic_type}': {str(e)}", exc_info=True)
            return None
    
    @classmethod
    def register_agent_class(cls, logic_type: str, agent_class: Type[AbstractLogicAgent]) -> None:
        """
        Enregistre une nouvelle classe d'agent pour un type de logique.
        
        Cette méthode permet d'étendre la factory avec de nouveaux types de logique.
        
        Args:
            logic_type: Le type de logique
            agent_class: La classe d'agent à associer à ce type
        """
        logger.info(f"Enregistrement de la classe d'agent '{agent_class.__name__}' pour le type de logique '{logic_type}'")
        cls._agent_classes[logic_type.lower().strip()] = agent_class
    
    @classmethod
    def get_supported_logic_types(cls) -> list:
        """
        Retourne la liste des types de logique supportés.
        
        Returns:
            Une liste des types de logique supportés
        """
        return list(cls._agent_classes.keys())