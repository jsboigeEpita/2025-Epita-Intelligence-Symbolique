import json
from src.core.plugins.interfaces import BasePlugin
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function
from semantic_kernel.functions.kernel_arguments import KernelArguments


class ExplorationPlugin(BasePlugin):
    """
    A plugin to explore a specific fallacy category in a given text.
    """

    PROMPT = """
You are a specialized fallacy detector. Your task is to analyze a given text and determine if it contains fallacies from a specific category.

You will be provided with:
1. The user's text to analyze.
2. The name of the fallacy category to focus on (`taxonomy_path`).
3. The definition of that fallacy category (`taxonomy_definition`).

Analyze the text *only* for fallacies belonging to the "{{$taxonomy_path}}" category.

If you find one or more fallacies:
- Return a JSON object containing the `name` of the specific fallacy, its `definition`, your `confidence` (0.0 to 1.0), the `evidence` (the exact quote from the text), and your `explanation`.

If you find no fallacies from this category, return an empty JSON object: {}.

---
Taxonomy Path: {{$taxonomy_path}}
Definition: {{$taxonomy_definition}}
---
Text to Analyze:
{{$text}}
---

Your response MUST be a single, valid JSON object.
"""

    def __init__(self, kernel: Kernel):
        self.kernel = kernel
        self.exploration_function = self.kernel.add_function(
            function_name="explore_fallacy_semantic",
            plugin_name="ExplorationPlugin",
            prompt=self.PROMPT,
        )

    @kernel_function(
        name="explore_fallacy", description="Analyzes a text for a specific fallacy."
    )
    async def explore_fallacy(
        self, text: str, taxonomy_path: str, taxonomy_definition: str
    ) -> str:
        """
        Analyzes a text for a specific fallacy based on its taxonomy.
        """
        arguments = KernelArguments(
            text=text,
            taxonomy_path=taxonomy_path,
            taxonomy_definition=taxonomy_definition,
        )
        response = await self.kernel.invoke(self.exploration_function, arguments)

        # Ensure the response is a clean JSON string
        response_str = str(response).strip()
        if response_str.startswith("```json"):
            response_str = response_str[7:]
        if response_str.endswith("```"):
            response_str = response_str[:-3]

        return response_str
