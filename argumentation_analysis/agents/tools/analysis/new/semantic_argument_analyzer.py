import asyncio
import json
import semantic_kernel as sk
from openai import AsyncOpenAI
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
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

        self.kernel.add_chat_service(
            "local_vllm_service",
            OpenAIChatCompletion(ai_model_id=model_name, async_client=client),
        )
        self.kernel.import_skill(ToulminPlugin(), skill_name="Toulmin")

        self.prompt_template = self.kernel.create_semantic_function(
            "Analyse le texte suivant et utilise l'outil 'Toulmin.analyze_argument' pour extraire les composants.\nTexte : {{$input}}",
            function_name="toulmin_analysis",
            skill_name="ToulminOrchestrator",
        )

    async def run(self, argument_text: str) -> ToulminAnalysisResult:
        context = self.kernel.create_new_context()
        context.variables["input"] = argument_text

        result = await self.kernel.run_async(
            self.prompt_template,
            input_context=context,
            auto_invoke_kernel_functions=True,
        )

        # Based on the v3 plan, the native plugin returns a JSON string.
        # The analyzer is responsible for parsing it into the Pydantic model.
        # Note: The plan is slightly ambiguous. One part says the kernel returns the object,
        # another part shows the plugin returning a JSON string. We follow the explicit code.
        result_str = result.result
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
