import pytest
from config.unified_config import UnifiedConfig
from argumentation_analysis.scripts.test_performance_extraits import StateManagerMock
from argumentation_analysis.agents.core.informal.informal_definitions import (
    setup_informal_kernel,
)


@pytest.fixture(scope="module")
def kernel():
    """
    Provides a real, configured Semantic Kernel instance for performance tests.
    This fixture now also loads the InformalAnalyzer plugin.
    """
    try:
        config = UnifiedConfig(mock_level="none", use_authentic_llm=True)
        sk_kernel = config.get_kernel_with_gpt4o_mini()

        # The gpt4o_mini service is the default, so we can get it like this.
        llm_service = sk_kernel.get_service()

        # Setup the informal kernel with the required plugins
        setup_informal_kernel(sk_kernel, llm_service)

        return sk_kernel
    except Exception as e:
        pytest.fail(f"Failed to initialize the authentic Semantic Kernel: {e}")


@pytest.fixture
def state_manager():
    """
    Provides a mock StateManager for isolated testing.
    """
    return StateManagerMock()
