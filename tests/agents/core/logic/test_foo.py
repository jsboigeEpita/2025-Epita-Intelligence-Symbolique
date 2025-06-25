# -*- coding: utf-8 -*-
import pytest
from semantic_kernel import Kernel
from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

@pytest.mark.asyncio
async def test_agent_initialization(jvm_session):
    """Tests that the agent initializes correctly with authentic components."""
    # 1. Setup authentic components
    kernel = Kernel()
    tweety_bridge = TweetyBridge()

    # Ensure TweetyBridge is ready
    assert tweety_bridge.is_jvm_ready()

    # 2. Instantiate the agent
    agent = FirstOrderLogicAgent(kernel, tweety_bridge=tweety_bridge, service_id="test_service")

    # 3. Assertions
    assert agent._kernel is kernel
    assert agent.tweety_bridge is tweety_bridge
    assert agent.logic_type == "FOL"