import pytest
from unittest.mock import MagicMock
from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent

@pytest.fixture
def mock_kernel():
    """Provides a mocked Semantic Kernel."""
    kernel = MagicMock()
    kernel.plugins = MagicMock()
    # Mock a function within the mocked plugin collection
    mock_plugin = MagicMock()
    mock_function = MagicMock()
    mock_function.invoke.return_value = '{"formulas": ["exists X: (Cat(X))"]}' # Default mock response
    mock_plugin.__getitem__.return_value = mock_function
    kernel.plugins.__getitem__.return_value = mock_plugin
    return kernel

@pytest.fixture
def fol_agent(mock_kernel):
    """Provides an instance of FirstOrderLogicAgent with a mocked kernel."""
    agent = FirstOrderLogicAgent(kernel=mock_kernel, service_id="test_service")
    # Mocking the bridge to avoid real Java calls
    agent._tweety_bridge = MagicMock()
    agent._tweety_bridge.validate_fol_belief_set.return_value = (True, "Valid")
    return agent