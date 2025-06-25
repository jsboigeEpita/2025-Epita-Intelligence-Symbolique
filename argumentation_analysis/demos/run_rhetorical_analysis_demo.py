import os
import sys
import json
import asyncio
import argparse
import logging
from pathlib import Path

# Ensure the project root is in the Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from argumentation_analysis.pipelines.analysis_pipeline import run_text_analysis_pipeline
from argumentation_analysis.core.utils.logging_utils import setup_logging

# Define a list of sample texts for the default demonstration mode
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
    },
    {
        "title": "Demonstration 4: Analysis from File",
        "file_path": "argumentation_analysis/demos/sample_epita_discourse.txt"
    }
]

async def run_and_log_analysis(title, text=None, file_path=None, output_path=None, log_level="INFO"):
    """Runs a single analysis, logs the process, and handles output."""
    logger = logging.getLogger("RhetoricalAnalysisDemo")
    logger.info(f"--- Starting: {title} ---")

    input_desc = f"text: \"{text[:50]}...\"" if text else f"file: '{file_path}'"
    logger.info(f"Analyzing {input_desc}")

    try:
        analysis_results = await run_text_analysis_pipeline(
            input_text_content=text,
            input_file_path=file_path,
            log_level=log_level
        )

        logger.info("--- ANALYSIS RESULT ---")
        if analysis_results:
            output_json_str = json.dumps(analysis_results, indent=2, ensure_ascii=False)
            if output_path:
                try:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(output_json_str, encoding='utf-8')
                    logger.info(f"Analysis results saved to: {output_path}")
                except Exception as write_error:
                    logger.error(f"Failed to write to output file {output_path}: {write_error}")
                    print(output_json_str) # Fallback to stdout
            else:
                print(output_json_str)
        else:
            logger.warning("Analysis returned None or empty result.")

        logger.info(f"--- Completed: {title} ---")

    except Exception as e:
        logger.error(f"--- ERROR during {title} ---", exc_info=True)

async def main():
    """Main function to parse arguments and run rhetorical analysis."""
    parser = argparse.ArgumentParser(description="Canonical entry point for Rhetorical Analysis.")
    
    text_source = parser.add_mutually_exclusive_group()
    text_source.add_argument("--file", "-f", type=str, help="Path to a text file to analyze.")
    text_source.add_argument("--text", "-t", type=str, help="Text to analyze directly from the command line.")
    
    parser.add_argument("--output-file", "-o", type=str, help="Path to save the output JSON report.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable detailed DEBUG logging.")
    
    args = parser.parse_args()
    
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level_str=log_level)
    logger = logging.getLogger("RhetoricalAnalysisDemo")

    output_file_path = Path(args.output_file) if args.output_file else None

    # If no arguments are provided, run the default demonstrations
    if not (args.file or args.text):
        logger.info("No input specified. Running default demonstrations.")
        print("=" * 80)
        print("STARTING RHETORICAL ANALYSIS DEMONSTRATIONS")
        print("=" * 80)
        for i, demo in enumerate(sample_texts):
            demo_output_path = None
            if output_file_path:
                 # Create a unique output file for each demo run
                demo_output_path = output_file_path.with_name(f"{output_file_path.stem}_demo_{i+1}{output_file_path.suffix}")
            
            file_path = demo.get('file_path')
            if file_path and not os.path.exists(file_path):
                 logger.warning(f"Skipping demo '{demo['title']}' - File not found: {file_path}")
                 continue

            await run_and_log_analysis(
                title=demo['title'], 
                text=demo.get('text'), 
                file_path=file_path,
                output_path=demo_output_path,
                log_level=log_level
            )
        print("\\n" + "=" * 80)
        print("ALL DEMONSTRATIONS COMPLETED")
        print("=" * 80)
    else:
        # Run with specified command-line arguments
        title = "Command-Line Analysis"
        await run_and_log_analysis(
            title=title,
            text=args.text,
            file_path=args.file,
            output_path=output_file_path,
            log_level=log_level
        )

if __name__ == "__main__":
    asyncio.run(main())