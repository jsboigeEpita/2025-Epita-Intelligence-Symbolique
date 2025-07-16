import asyncio
import json
import semantic_kernel as sk
from semantic_kernel.functions.kernel_arguments import KernelArguments

class ParallelWorkflowManager:
    """
    Orchestrates the parallel exploration of a text for different fallacy categories.
    """
    def __init__(self, kernel: sk.Kernel, plugins_directory: str):
        """
        Initializes the workflow manager and loads the required plugins.

        :param kernel: An instance of the semantic-kernel.
        :param plugins_directory: The path to the directory containing the plugins.
        """
        self.kernel = kernel
        
        # Load the semantic functions from the kernel using the new method
        exploration_plugin = self.kernel.add_plugin(parent_directory=plugins_directory, plugin_name="ExplorationPlugin")
        synthesis_plugin = self.kernel.add_plugin(parent_directory=plugins_directory, plugin_name="SynthesisPlugin")

        self.exploration_func = exploration_plugin["Explore"]
        self.synthesis_func = synthesis_plugin["Synthesize"]

    async def _run_single_exploration(self, text: str, taxonomy_path: str, taxonomy_definition: str) -> dict:
        """
        Asynchronously runs a single exploration path using the ExplorationPlugin.
        """
        print(f"Starting exploration for: {taxonomy_path}")
        
        arguments = KernelArguments(
            input=text,
            taxonomy_path=taxonomy_path,
            taxonomy_definition=taxonomy_definition
        )
        
        result = await self.kernel.invoke(self.exploration_func, arguments)
        
        try:
            # The plugin is expected to return a valid JSON object string
            analysis_result = json.loads(str(result))
        except json.JSONDecodeError:
            print(f"Error decoding JSON from exploration result for {taxonomy_path}: {result}")
            analysis_result = {}

        print(f"Finished exploration for: {taxonomy_path}")
        return analysis_result

    async def execute_parallel_workflow(self, text: str, taxonomy_branches: dict) -> dict:
        """
        Executes the full parallel workflow.
        It runs multiple explorations concurrently and then synthesizes the results.
        """
        # Create a list of coroutines for each exploration task
        exploration_tasks = [
            self._run_single_exploration(text, path, definition) 
            for path, definition in taxonomy_branches.items()
        ]
        
        # Run all exploration tasks concurrently
        aggregated_results = await asyncio.gather(*exploration_tasks)
        
        # Filter out empty results before synthesis
        valid_results = [r for r in aggregated_results if r]
        
        if not valid_results:
            return {"summary": "No fallacies found after exploration.", "findings": []}

        print("All explorations completed. Synthesizing results...")
        
        # Prepare arguments for the synthesis plugin
        synthesis_args = KernelArguments(
            input_findings=json.dumps(valid_results)
        )

        # Invoke the synthesis plugin
        synthesis_result_str = await self.kernel.invoke(self.synthesis_func, synthesis_args)
        
        synthesis_str = str(synthesis_result_str)
        # Clean the string if it's wrapped in a markdown code block
        if synthesis_str.startswith("```json"):
            synthesis_str = synthesis_str[7:]
        if synthesis_str.endswith("```"):
            synthesis_str = synthesis_str[:-3]
        
        try:
            final_result = json.loads(synthesis_str)
        except json.JSONDecodeError:
            print(f"Error decoding JSON from synthesis result: {synthesis_result_str}")
            final_result = {"summary": "Failed to synthesize results.", "findings": valid_results}
            
        return final_result