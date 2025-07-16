from enum import Enum
import semantic_kernel as sk
from .agents import FallacyAgentBase, MethodicalAuditorAgent, ParallelExplorerAgent, ResearchAssistantAgent

class AgentType(Enum):
    """Enumeration of available agent archetypes."""
    METHODICAL_AUDITOR = "MethodicalAuditor"
    PARALLEL_EXPLORER = "ParallelExplorer"
    RESEARCH_ASSISTANT = "ResearchAssistant"

class AgentFactory:
    """Factory class for creating fallacy detection agents."""

    _agent_map = {
        AgentType.METHODICAL_AUDITOR: MethodicalAuditorAgent,
        AgentType.PARALLEL_EXPLORER: ParallelExplorerAgent,
        AgentType.RESEARCH_ASSISTANT: ResearchAssistantAgent,
    }

    def __init__(self, kernel: sk.Kernel, llm_service_id: str):
        """Initializes the factory with a kernel and LLM service ID."""
        self.kernel = kernel
        self.llm_service_id = llm_service_id

    def create_agent(self, agent_type: AgentType, **kwargs) -> FallacyAgentBase:
        """
        Creates an agent instance of the specified type.

        :param agent_type: The type of agent to create.
        :param kwargs: Additional arguments for the agent constructor.
        :return: An instance of a class derived from FallacyAgentBase.
        :raises ValueError: If the agent type is unknown.
        """
        agent_class = self._agent_map.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return agent_class(kernel=self.kernel, **kwargs)