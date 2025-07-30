import pytest
from src.agents.agent_loader import AgentLoader

def test_agent_loader_can_be_imported():
    """
    Tests that the AgentLoader class can be imported successfully.
    """
    assert AgentLoader is not None