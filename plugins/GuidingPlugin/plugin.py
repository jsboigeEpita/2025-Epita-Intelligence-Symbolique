import json
from core.plugins.interfaces import BasePlugin, IWorkflowPlugin
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function


class GuidingPlugin(BasePlugin):
    """
    A plugin to guide the analysis by identifying relevant categories of fallacies.
    """

    def __init__(self, kernel: Kernel):
        self.kernel = kernel
        # In a real implementation, the prompt would be loaded from a file
        # and registered as a semantic function.
        self.guiding_prompt = """
Based on the following text, identify the most relevant general fallacy categories to investigate.
The available categories are: Fallacies of Relevance, Fallacies of Ambiguity, Fallacies of Presumption.
Return your answer as a JSON object with a single key "relevant_categories" containing a list of strings.

Example:
Text: "The senator's argument about the economy is weak because he is a known philanderer."
Response:
{
    "relevant_categories": ["Fallacies of Relevance"]
}

Text: {{$input}}
Response:
"""
        self.guiding_function = self.kernel.add_function(
            function_name="suggest_categories_semantic",
            plugin_name="GuidingPlugin",
            prompt=self.guiding_prompt,
        )

    @kernel_function(
        name="suggest_categories",
        description="Suggests relevant fallacy categories to focus on.",
    )
    async def suggest_categories(self, text: str) -> str:
        """
        Suggests relevant fallacy categories based on the input text.
        """
        response = await self.kernel.invoke(self.guiding_function, input=text)
        return str(response)
