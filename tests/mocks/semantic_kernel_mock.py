"""Mock complet pour semantic_kernel"""


class MockSemanticKernel:
    def __init__(self):
        self.functions = {}
        self.plugins = {}

    def add_function(self, function_name=None, plugin_name=None, **kwargs):
        """Mock pour add_function"""
        if function_name:
            self.functions[function_name] = kwargs
        return self

    def add_plugin(self, plugin, plugin_name=None):
        """Mock pour add_plugin"""
        if plugin_name:
            self.plugins[plugin_name] = plugin
        return self

    def invoke(self, function_name, **kwargs):
        """Mock pour invoke"""
        return MockKernelResult(f"Mock result for {function_name}")


class MockKernelResult:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class MockChatCompletionService:
    def __init__(self, **kwargs):
        pass


class MockOpenAIChatCompletion:
    def __init__(self, **kwargs):
        pass


# Mock pour les contenus
class MockChatMessageContent:
    def __init__(self, role=None, content=None, **kwargs):
        self.role = role
        self.content = content
        self.items = []


class MockTextContent:
    def __init__(self, text=""):
        self.text = text


class MockChatHistory:
    def __init__(self):
        self.messages = []

    def add_message(self, message):
        self.messages.append(message)

    def add_user_message(self, content):
        self.messages.append(MockChatMessageContent(role="user", content=content))

    def add_assistant_message(self, content):
        self.messages.append(MockChatMessageContent(role="assistant", content=content))


# Mock pour les fonctions
class MockKernelFunction:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "mock_function")
        self.description = kwargs.get("description", "Mock function")


def kernel_function(**kwargs):
    """Décorateur mock pour kernel_function"""

    def decorator(func):
        return MockKernelFunction(name=func.__name__, **kwargs)

    return decorator


# Modules et classes disponibles
Kernel = MockSemanticKernel
ChatCompletionService = MockChatCompletionService
OpenAIChatCompletion = MockOpenAIChatCompletion
ChatMessageContent = MockChatMessageContent
TextContent = MockTextContent
ChatHistory = MockChatHistory
KernelFunction = MockKernelFunction


# Sous-modules
class contents:
    ChatMessageContent = MockChatMessageContent
    TextContent = MockTextContent
    ChatHistory = MockChatHistory


class functions:
    kernel_function = kernel_function
    KernelFunction = MockKernelFunction


class connectors:
    class ai:
        class open_ai:
            OpenAIChatCompletion = MockOpenAIChatCompletion


# Export des modules
import sys

current_module = sys.modules[__name__]
current_module.contents = contents
current_module.functions = functions
current_module.connectors = connectors
