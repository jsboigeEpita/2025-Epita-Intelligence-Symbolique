import asyncio
import os
import sys
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.open_ai.settings.open_ai_settings import (
    OpenAISettings,
)

# Add project root to path for reliable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from argumentation_analysis.orchestration.workflow import ParallelWorkflowManager
from argumentation_analysis.reporting.reporting import render_markdown_report


async def main():
    """
    Main execution function to run the parallel workflow integration test.
    """
    # --- Kernel Configuration ---
    kernel = sk.Kernel()
    try:
        openai_settings = OpenAISettings.create()
        kernel.add_service(
            OpenAIChatCompletion(
                ai_model_id=openai_settings.chat_model_id,
                api_key=openai_settings.api_key.get_secret_value()
                if openai_settings.api_key
                else None,
                org_id=openai_settings.org_id,
            ),
        )
    except Exception as e:
        print(f"Error configuring OpenAI service: {e}")
        print(
            "Please ensure your .env file is correctly set up with OPENAI_API_KEY and OPENAI_CHAT_MODEL_ID."
        )
        return

    # --- Directory and Path Configuration ---
    script_dir = os.path.dirname(__file__)
    # Correct the path to be relative to the project root, not the demos folder
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    plugins_directory = os.path.join(project_root, "argumentation_analysis", "plugins")
    template_path = os.path.join(
        project_root, "templates", "synthesis_report.md.template"
    )

    # --- Create Mock Taxonomy Data for Validation ---
    print("Creating mock taxonomy branches for validation...")
    selected_branches = {
        "ad_hominem": "Attaquer la personne plutôt que l'argument. Par exemple, 'Ne l'écoutez pas, c'est un idiot.'",
        "straw_man": "Dénaturer l'argument de l'adversaire pour le rendre plus facile à attaquer. Par exemple, 'Vous voulez interdire les voitures, vous détestez la liberté.'",
        "false_dichotomy": "Présenter deux options comme les seules possibles, alors qu'il en existe d'autres. Par exemple, 'Soit vous êtes avec nous, soit vous êtes contre nous.'",
        "appeal_to_authority": "Faire appel à une autorité non pertinente ou biaisée. Par exemple, 'Un célèbre acteur a dit que ce produit est le meilleur.'",
    }
    print(
        f"Selected {len(selected_branches)} branches for validation: {list(selected_branches.keys())}"
    )

    # The text to be analyzed
    text_to_analyze = """
    Le projet de loi sur la sécurité est essentiel. Les opposants prétendent qu'il menace nos libertés, 
    mais nous ne pouvons pas écouter des gens qui sont clairement antipatriotiques. 
    Soit vous soutenez cette loi pour protéger notre pays, soit vous êtes du côté des criminels. 
    De plus, un expert respecté en sécurité a confirmé que c'était la seule solution viable.
    """
    print("\n--- Text to Analyze ---")
    print(text_to_analyze)

    # --- Workflow Execution ---
    print("\nInitializing Parallel Workflow Manager...")
    try:
        manager = ParallelWorkflowManager(kernel, plugins_directory)
    except Exception as e:
        print(f"Error initializing ParallelWorkflowManager: {e}")
        print("Please check your plugin structure and folder paths.")
        return

    print("Executing parallel workflow...")
    analysis_result = await manager.execute_parallel_workflow(
        text_to_analyze, selected_branches
    )

    # --- Report Generation ---
    print("\n--- Analysis Complete. Generating Report ---")
    try:
        final_report = render_markdown_report(template_path, analysis_result)
        print("\n--- Final Markdown Report ---")
        print(final_report)
    except Exception as e:
        print(f"Error rendering report: {e}")
        print("\n--- Raw Analysis Result ---")
        import json

        print(json.dumps(analysis_result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
