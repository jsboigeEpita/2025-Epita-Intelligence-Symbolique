"""
Agent Factory Module

Provides factory methods for creating different types of agents
with proper dependency injection and configuration.
"""

from typing import Dict, Type, Any, Optional
import logging
from .core.abc.agent_bases import BaseAgent
from .plugins.project_management_plugin import ProjectManagementPlugin
from semantic_kernel import Kernel


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
        """
        if agent_type == "informal":
            return self._create_informal_fallacy_agent(**kwargs)
        elif agent_type == "project_manager":
            return self._create_project_manager_agent(**kwargs)
        else:
            self.logger.error(f"Unknown agent type: {agent_type}")
            raise ValueError(f"Unknown agent type: {agent_type}")

    def _create_informal_fallacy_agent(self, **kwargs) -> InformalFallacyAgent:
        """Create an informal fallacy analysis agent."""
        from .concrete_agents.informal_fallacy_agent import InformalFallacyAgent
        return InformalFallacyAgent(self.config, **kwargs)

    def _create_project_manager_agent(self, **kwargs) -> ProjectManagerAgent:
        """Create a project management agent."""
        from .concrete_agents.project_manager_agent import ProjectManagerAgent
        return ProjectManagerAgent(self.config, **kwargs)
