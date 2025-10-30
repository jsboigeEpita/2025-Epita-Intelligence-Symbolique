"""
Agent Factory Module

Provides factory methods for creating different types of agents
with proper dependency injection and configuration.
"""

from typing import Dict, Type, Any, Optional
import logging

from .core.abc.agent_bases import BaseAgent
from .plugins.project_management_plugin import ProjectManagementPlugin


class AgentFactory:
    """Factory class for creating agents with proper configuration."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the agent factory.
        
        Args:
            config: Configuration dictionary for agents
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
    def create_agent(self, agent_type: str, **kwargs) -> BaseAgent:
        """
        Create an agent of the specified type.
        
        Args:
            agent_type: Type of agent to create
            **kwargs: Additional arguments for agent creation
            
        Returns:
            Configured agent instance
            
        Raises:
            ValueError: If agent_type is not supported
        """
        if agent_type == "project_management":
            return self._create_project_management_agent(**kwargs)
        else:
            raise ValueError(f"Unsupported agent type: {agent_type}")
    
    def _create_project_management_agent(self, **kwargs) -> BaseAgent:
        """Create a project management agent with plugin support."""
        plugin = ProjectManagementPlugin(self.config.get("project_management", {}))
        # Import here to avoid circular imports
        from .project_management_agent import ProjectManagementAgent
        return ProjectManagementAgent(plugin=plugin, **kwargs)
    
    def get_supported_agent_types(self) -> list[str]:
        """Get list of supported agent types."""
        return ["project_management"]
    
    def register_agent_type(self, agent_type: str, creator_method: str):
        """
        Register a new agent type.
        
        Args:
            agent_type: Type identifier
            creator_method: Method name for creating this agent type
        """
        self.logger.info(f"Registering agent type: {agent_type}")
        # This would be extended in a real implementation


def create_agent_factory(config: Optional[Dict[str, Any]] = None) -> AgentFactory:
    """
    Convenience function to create an agent factory.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured AgentFactory instance
    """
    return AgentFactory(config)