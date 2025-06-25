import os
import sys
import json
import asyncio
from pathlib import Path

# Ensure the project root is in the Python path to allow for absolute-like imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from argumentation_analysis.pipelines.analysis_pipeline import run_text_analysis_pipeline
from argumentation_analysis.core.utils.logging_utils import setup_logging

# Define a list of sample texts for demonstration
sample_texts = [
    {
        "title": "Demonstration 1: Simple Fallacy",
        "text": "Everyone is buying this new phone, so it must be the best one on the market. You should buy it too."
    },
    {
        "title": "Demonstration 2: Political Discourse",
        "text": "My opponent's plan for the economy is terrible. He is a known flip-flopper and cannot be trusted with our country's future."
    },
    {
        "title": "Demonstration 3: Complex Argument",
        "text": "While some studies suggest a correlation between ice cream sales and crime rates, it is a fallacy to assume causation. The lurking variable is clearly the weather; hot temperatures lead to both more ice cream consumption and more people being outside, which can lead to more public disturbances."
    }
]

async def _run_single_demo(title, text=None, file_path=None):
    """Helper function to run a single analysis demonstration."""
    print(f"\n\n--- {title} ---\n")
    
    log_level = "INFO"
    input_desc = f"text: \"{text}\"" if text else f"file: '{file_path}'"
    print(f"Analyzing {input_desc}\n")

    try:
        analysis_results = await run_text_analysis_pipeline(
            input_text_content=text,
            input_file_path=file_path,
            log_level=log_level
        )

        print("--- ANALYSIS RESULT ---")
        if analysis_results:
            print(json.dumps(analysis_results, indent=2, ensure_ascii=False))
        else:
            print("Analysis returned None or empty result.")

        print(f"\n--- {title} COMPLETED ---")

    except Exception as e:
        print(f"\n--- ERROR during {title} ---", file=sys.stderr)
        print(f"An exception of type {type(e).__name__} occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

async def main():
    """Main async function to run demonstrations."""
    setup_logging(log_level_str="INFO")
    
    print("=" * 80)
    print("STARTING RHETORICAL ANALYSIS DEMONSTRATIONS")
    print("=" * 80)

    # --- Run demonstrations from predefined texts ---
    for demo in sample_texts:
        await _run_single_demo(demo['title'], text=demo['text'])

    # --- Run demonstration from a file ---
    demo_file_path = "argumentation_analysis/demos/rhetorical_analysis/sample_epita_discourse.txt"
    if os.path.exists(demo_file_path):
        await _run_single_demo("Demonstration 4: Analysis from File", file_path=demo_file_path)
    else:
        print(f"\n--- SKIPPING Demonstration 4: Analysis from File ---", file=sys.stderr)
        print(f"File not found: {demo_file_path}", file=sys.stderr)


    print("\n\n" + "=" * 80)
    print("ALL DEMONSTRATIONS COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())