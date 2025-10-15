import json
from core.plugins.interfaces import BasePlugin
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function
from semantic_kernel.functions.kernel_arguments import KernelArguments


class SynthesisPlugin(BasePlugin):
    """
    A plugin to synthesize findings from multiple explorations into a single report.
    """

    PROMPT = """
You are an expert in logical argumentation. You will receive a series of analysis findings from different exploration paths. Each finding is a JSON object detailing a potential fallacy.

Your task is to synthesize these independent findings into a single, coherent summary.

Do not simply list the findings. Your goal is to:
1.  Identify the most likely and relevant fallacies from the combined input.
2.  Group similar or overlapping findings.
3.  Provide a high-level summary of the overall argumentative structure.
4.  Return the result as a single JSON object. This object must contain a "summary" key, and a "fallacies" key, which is a list of objects. Each fallacy object in the list must include "name", "definition", "confidence", "explanation", and an "evidence" field containing the relevant quote from the text.

Input findings will be provided as a JSON string in the `input_findings` variable.

Analysis Findings:
{{$input_findings}}

Produce a single, valid JSON object as your output.
"""

    def __init__(self, kernel: Kernel):
        self.kernel = kernel
        self.synthesis_function = self.kernel.add_function(
            function_name="synthesize_findings_semantic",
            plugin_name="SynthesisPlugin",
            prompt=self.PROMPT,
        )

    @kernel_function(
        name="synthesize_findings",
        description="Synthesizes a list of JSON findings into a final report.",
    )
    async def synthesize_findings(self, findings: str) -> str:
        """
        Synthesizes a list of JSON findings.
        """
        arguments = KernelArguments(input_findings=findings)
        response = await self.kernel.invoke(self.synthesis_function, arguments)

        response_str = str(response).strip()
        if response_str.startswith("```json"):
            response_str = response_str[7:]
        if response_str.endswith("```"):
            response_str = response_str[:-3]

        return response_str
