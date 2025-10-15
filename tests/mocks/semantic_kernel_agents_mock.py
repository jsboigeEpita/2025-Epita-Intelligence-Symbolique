"""
Mock pour semantic_kernel.agents
"""


class MockChatCompletionAgent:
    def __init__(self, *args, **kwargs):
        self.service_id = kwargs.get("service_id", "mock_service")
        self.kernel = kwargs.get("kernel", None)
        self.name = kwargs.get("name", "mock_agent")

    async def invoke(self, *args, **kwargs):
        return "Mock response from ChatCompletionAgent"


class MockAgent:
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get("name", "mock_agent")

    async def invoke(self, *args, **kwargs):
        return "Mock response from Agent"


# Simulation du module agents
agents = type(
    "agents", (), {"ChatCompletionAgent": MockChatCompletionAgent, "Agent": MockAgent}
)()
