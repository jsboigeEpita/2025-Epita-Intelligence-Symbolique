"""
Module définissant le registre des agents opérationnels.

Ce module fournit une classe pour gérer les agents opérationnels disponibles
et sélectionner l'agent approprié pour une tâche donnée.
"""

import logging
from typing import Dict, List, Any, Optional, Type, Union
import asyncio
import semantic_kernel as sk # Ajout de l'import

from argumentation_analysis.core.bootstrap import ProjectContext # Ajout de l'import
from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import OperationalAgent
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter import InformalAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.pl_agent_adapter import PLAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.rhetorical_tools_adapter import RhetoricalToolsAdapter


class OperationalAgentRegistry:
    """
    Registre des agents opérationnels.
    
    Cette classe gère les agents opérationnels disponibles et permet
    de sélectionner l'agent approprié pour une tâche donnée.
    """
    
    def __init__(self,
                 operational_state: Optional[OperationalState] = None,
                 kernel: Optional[sk.Kernel] = None,
                 llm_service_id: Optional[str] = None,
                 project_context: Optional[ProjectContext] = None):
        """
        Initialise un nouveau registre d'agents opérationnels.
        
        Args:
            operational_state: État opérationnel à utiliser. Si None, un nouvel état est créé.
            kernel: Le kernel Semantic Kernel à utiliser pour initialiser les agents.
            llm_service_id: L'ID du service LLM à utiliser.
            project_context: Le contexte global du projet.
        """
        self.operational_state = operational_state if operational_state else OperationalState()
        self.kernel = kernel
        self.llm_service_id = llm_service_id
        self.project_context = project_context
        self.agents: Dict[str, OperationalAgent] = {}
        self.agent_classes: Dict[str, Type[OperationalAgent]] = {
            "extract": ExtractAgentAdapter,
            "informal": InformalAgentAdapter,
            "pl": PLAgentAdapter,
            "rhetorical": RhetoricalToolsAdapter
        }
        self.logger = logging.getLogger("OperationalAgentRegistry")

        if not self.kernel or not self.llm_service_id:
            self.logger.warning("Kernel ou llm_service_id non fournis à OperationalAgentRegistry. L'initialisation des agents échouera.")
        if not self.project_context:
            self.logger.warning("ProjectContext non fourni à OperationalAgentRegistry. L'initialisation des agents risque d'échouer.")
    
    async def get_agent(self, agent_type: str) -> Optional[OperationalAgent]:
        """
        Récupère un agent opérationnel par son type.
        
        Args:
            agent_type: Type de l'agent à récupérer
            
        Returns:
            L'agent opérationnel ou None si le type n'existe pas
        """
        # Vérifier si l'agent existe déjà dans le registre
        if agent_type in self.agents:
            return self.agents[agent_type]
        
        # Vérifier si le type d'agent est connu
        if agent_type not in self.agent_classes:
            self.logger.error(f"Type d'agent inconnu: {agent_type}")
            return None
        
        # Créer une nouvelle instance de l'agent
        try:
            agent_class = self.agent_classes[agent_type]
            agent = agent_class(
                name=f"{agent_type.capitalize()}Agent",
                operational_state=self.operational_state,
                project_context=self.project_context
            )
            
            # Initialiser l'agent avec kernel et llm_service_id
            if not self.kernel or not self.llm_service_id or not self.project_context:
                self.logger.error(f"Kernel, llm_service_id ou project_context manquant pour initialiser l'agent {agent_type}")
                return None
            
            success = await agent.initialize(self.kernel, self.llm_service_id, self.project_context)
            if not success:
                self.logger.error(f"Échec de l'initialisation de l'agent {agent_type}")
                return None
            
            # Ajouter l'agent au registre
            self.agents[agent_type] = agent
            self.logger.info(f"Agent {agent_type} créé et initialisé avec succès")
            
            return agent
        except Exception as e:
            self.logger.error(f"Erreur lors de la création de l'agent {agent_type}: {e}")
            return None
    
    def get_agent_types(self) -> List[str]:
        """
        Récupère la liste des types d'agents disponibles.
        
        Returns:
            Liste des types d'agents disponibles
        """
        return list(self.agent_classes.keys())
    
    async def select_agent_for_task(self, task: Dict[str, Any]) -> Optional[OperationalAgent]:
        """
        Sélectionne l'agent approprié pour une tâche donnée.
        
        Args:
            task: La tâche à traiter
            
        Returns:
            L'agent opérationnel approprié ou None si aucun agent ne peut traiter la tâche
        """
        # Extraire les capacités requises
        required_capabilities = task.get("required_capabilities", [])
        
        if not required_capabilities:
            self.logger.warning("Aucune capacité requise spécifiée dans la tâche")
            return None
        
        # Initialiser tous les agents
        for agent_type in self.agent_classes.keys():
            await self.get_agent(agent_type)
        
        # Évaluer chaque agent pour la tâche
        best_agent = None
        best_score = 0
        
        for agent in self.agents.values():
            # Vérifier si l'agent peut traiter la tâche
            if not agent.can_process_task(task):
                continue
            
            # Calculer un score pour l'agent
            agent_capabilities = agent.get_capabilities()
            score = sum(1 for cap in required_capabilities if cap in agent_capabilities)
            
            # Mettre à jour le meilleur agent si nécessaire
            if score > best_score:
                best_agent = agent
                best_score = score
        
        if best_agent:
            self.logger.info(f"Agent sélectionné pour la tâche: {best_agent.name}")
        else:
            self.logger.warning("Aucun agent approprié trouvé pour la tâche")
        
        return best_agent
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une tâche en sélectionnant l'agent approprié.
        
        Args:
            task: La tâche à traiter
            
        Returns:
            Le résultat du traitement de la tâche
        """
        # Sélectionner l'agent approprié
        agent = await self.select_agent_for_task(task)
        
        if not agent:
            return {
                "id": f"result-{task.get('id')}",
                "task_id": task.get("id"),
                "tactical_task_id": task.get("tactical_task_id"),
                "status": "failed",
                "outputs": {},
                "metrics": {},
                "issues": [{
                    "type": "agent_selection_error",
                    "description": "Aucun agent approprié trouvé pour la tâche",
                    "severity": "high"
                }]
            }
        
        # Traiter la tâche avec l'agent sélectionné
        return await agent.process_task(task)
    
    def register_agent_class(self, agent_type: str, agent_class: Type[OperationalAgent]) -> bool:
        """
        Enregistre une nouvelle classe d'agent.
        
        Args:
            agent_type: Type de l'agent
            agent_class: Classe de l'agent
            
        Returns:
            True si l'enregistrement a réussi, False sinon
        """
        if agent_type in self.agent_classes:
            self.logger.warning(f"Type d'agent déjà enregistré: {agent_type}")
            return False
        
        self.agent_classes[agent_type] = agent_class
        self.logger.info(f"Classe d'agent enregistrée: {agent_type}")
        return True
    
    def unregister_agent_class(self, agent_type: str) -> bool:
        """
        Désenregistre une classe d'agent.
        
        Args:
            agent_type: Type de l'agent
            
        Returns:
            True si le désenregistrement a réussi, False sinon
        """
        if agent_type not in self.agent_classes:
            self.logger.warning(f"Type d'agent non enregistré: {agent_type}")
            return False
        
        # Supprimer l'agent du registre s'il existe
        if agent_type in self.agents:
            del self.agents[agent_type]
        
        # Supprimer la classe d'agent
        del self.agent_classes[agent_type]
        self.logger.info(f"Classe d'agent désenregistrée: {agent_type}")
        return True