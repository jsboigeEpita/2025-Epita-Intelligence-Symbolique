import abc
import json
from enum import Enum
import semantic_kernel as sk
import os
from argumentation_analysis.orchestration.workflow import ParallelWorkflowManager
from argumentation_analysis.utils.taxonomy_loader import TaxonomyLoader

class FallacyAgentBase(abc.ABC):
    """Abstract base class for fallacy detection agents."""

    def __init__(self, kernel: sk.Kernel):
        """Initializes the agent with a semantic kernel instance."""
        self._kernel = kernel

    @abc.abstractmethod
    async def analyze_text(self, text: str) -> dict:
        """
        Analyzes a given text for fallacies.

        :param text: The text to analyze.
        :return: A dictionary containing the analysis results.
        """
        pass

class MethodicalAuditorAgent(FallacyAgentBase):
    """
    Agent that performs a two-step analysis.
    1. A guiding plugin suggests relevant fallacy categories.
    2. A parallel exploration runs only on the suggested categories.
    This aims for a balance of speed and accuracy.
    """
    def __init__(self, kernel: sk.Kernel):
        super().__init__(kernel)
        script_dir = os.path.dirname(__file__)
        self.plugins_directory = os.path.join(script_dir, "..", "plugins")
        self.taxonomy_directory = os.path.join(script_dir, "..", "taxonomy", "fallacies")

        # Load the guiding function
        kernel.add_plugin(parent_directory=self.plugins_directory, plugin_name="GuidingPlugin")
        self.guiding_func = kernel.plugins["GuidingPlugin"]["GuidingPlugin"]
        
        # Initialize the workflow manager
        self.manager = ParallelWorkflowManager(kernel, self.plugins_directory)

    async def analyze_text(self, text: str) -> dict:
        """
        Orchestrates the guided analysis workflow.
        """
        print("--- Running Methodical Auditor Agent ---")
        
        # 1. Run the guiding plugin to find relevant categories
        print("Step 1: Identifying relevant fallacy categories...")
        guiding_result = await self.kernel.invoke(self.guiding_func, input=text)
        
        try:
            relevant_categories_data = json.loads(str(guiding_result))
            relevant_categories = relevant_categories_data.get("relevant_categories", [])
        except (json.JSONDecodeError, AttributeError):
            relevant_categories = []

        if not relevant_categories:
            print("No relevant categories suggested. Aborting focused exploration.")
            return {"summary": "Analysis aborted: No relevant fallacy categories were identified by the guiding model.", "findings": []}

        print(f"Guiding plugin suggested: {relevant_categories}")

        # 2. Filter taxonomy branches based on the suggested categories
        print("Step 2: Filtering taxonomy for focused exploration...")
        loader = TaxonomyLoader()
        all_branches = loader.load_taxonomy()
        
        # The category is the first part of the path, e.g., "Fallacies of Relevance/Ad Hominem.txt"
        # We need to normalize the path format for reliable matching.
        targeted_branches = {
            path: definition for path, definition in all_branches.items()
            if os.path.normpath(path).split(os.sep)[0] in relevant_categories
        }

        if not targeted_branches:
            print("No matching taxonomy branches found for the suggested categories.")
            return {"summary": "Analysis complete: The categories suggested by the guiding model did not match any available taxonomies.", "findings": []}

        print(f"Executing workflow on {len(targeted_branches)} targeted branches.")

        # 3. Execute the workflow on the filtered set of branches
        analysis_result = await self.manager.execute_parallel_workflow(text, targeted_branches)
        
        return analysis_result

class ParallelExplorerAgent(FallacyAgentBase):
    """
    Agent that explores all taxonomy branches in parallel.
    Uses the ParallelWorkflowManager for a comprehensive but potentially less focused analysis.
    """
    def __init__(self, kernel: sk.Kernel):
        super().__init__(kernel)
        # Determine paths relative to this file's location
        script_dir = os.path.dirname(__file__)
        self.plugins_directory = os.path.join(script_dir, "..", "plugins")
        self.taxonomy_directory = os.path.join(script_dir, "..", "taxonomy", "fallacies")
        
        # Initialize the workflow manager
        self.manager = ParallelWorkflowManager(kernel, self.plugins_directory)

    async def analyze_text(self, text: str) -> dict:
        """
        Loads all taxonomy branches and executes the parallel workflow.
        """
        print("--- Running Parallel Explorer Agent ---")
        loader = TaxonomyLoader()
        taxonomy_branches = loader.load_taxonomy()
        
        print(f"Loaded {len(taxonomy_branches)} branches for parallel exploration.")
        
        # For cost and performance management during testing, let's cap the exploration
        # to a subset of branches. We will use all of them in the final integration tests.
        # selected_branches = dict(list(taxonomy_branches.items())[:10])
        # print(f"Executing workflow on {len(selected_branches)} selected branches.")

        analysis_result = await self.manager.execute_parallel_workflow(text, taxonomy_branches)
        
        return analysis_result

class ResearchAssistantAgent(FallacyAgentBase):
    """
    Placeholder for a future agent that will use a planner
    for interactive, step-by-step analysis.
    This agent is not yet implemented.
    """
    def __init__(self, kernel: sk.Kernel):
        super().__init__(kernel)
        print("--- Research Assistant Agent Initialized (Placeholder) ---")

    async def analyze_text(self, text: str) -> dict:
        """
        Returns a message indicating that the agent is not implemented.
        """
        print("--- Running Research Assistant Agent (Placeholder) ---")
        return {
            "summary": "This agent is a placeholder and is not yet implemented.",
            "findings": [
                {
                    "fallacy_name": "Not Implemented",
                    "explanation": "The ResearchAssistantAgent is designed for a future interactive, planner-based analysis workflow. This feature is currently under development.",
                    "is_fallacious": "N/A"
                }
            ]
        }
