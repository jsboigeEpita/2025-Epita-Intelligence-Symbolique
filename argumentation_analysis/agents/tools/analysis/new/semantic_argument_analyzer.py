import asyncio
import json
import semantic_kernel as sk
from openai import AsyncOpenAI
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.functions import KernelArguments
from argumentation_analysis.core.models.toulmin_model import ToulminAnalysisResult
from argumentation_analysis.plugins.toulmin_plugin import ToulminPlugin


class SemanticArgumentAnalyzer:
    def __init__(
        self,
        api_base_url="http://localhost:8000/v1",
        model_name="Qwen3-1.7B-Toulmin-Analyzer",
    ):
        self.kernel = sk.Kernel()

        # Correction: Instancier un client AsyncOpenAI pour configurer l'URL de base
        client = AsyncOpenAI(base_url=api_base_url, api_key="EMPTY")

        # Migration API Semantic Kernel: add_chat_service -> add_service
        service = OpenAIChatCompletion(ai_model_id=model_name, async_client=client)
        self.kernel.add_service(service)
        self.kernel.add_plugin(ToulminPlugin(), plugin_name="Toulmin")

        self.prompt_function = self.kernel.add_function(
            function_name="toulmin_analysis",
            plugin_name="ToulminOrchestrator",
            prompt="Analyse le texte suivant et utilise l'outil 'Toulmin.analyze_argument' pour extraire les composants.\nTexte : {{$input}}",
        )

    async def run(self, argument_text: str) -> ToulminAnalysisResult:
        result = await self.kernel.invoke(
            self.prompt_function,
            arguments=KernelArguments(input=argument_text),
        )

        # Based on the v3 plan, the native plugin returns a JSON string.
        # The analyzer is responsible for parsing it into the Pydantic model.
        result_str = str(result)
        if isinstance(result_str, str):
            try:
                analysis_dict = json.loads(result_str)
                return ToulminAnalysisResult(**analysis_dict)
            except json.JSONDecodeError:
                # Handle cases where the result is not a valid JSON string
                # This could be an error message or unexpected output from the LLM
                raise ValueError(f"Failed to decode JSON from LLM result: {result_str}")

        # If the result is already a dict or a Pydantic model (if SK handles it magically)
        if isinstance(result_str, dict):
            return ToulminAnalysisResult(**result_str)
        if isinstance(result_str, ToulminAnalysisResult):
            return result_str

        raise TypeError(f"Unexpected result type from kernel: {type(result_str)}")
