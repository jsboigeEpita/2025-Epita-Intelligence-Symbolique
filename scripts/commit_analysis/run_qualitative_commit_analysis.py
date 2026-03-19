import os
import sys
import collections
import semantic_kernel as sk
import logging
import argparse


# Add project root to PYTHONPATH to resolve module imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from semantic_kernel.functions import KernelArguments
from datetime import datetime
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    OpenAIPromptExecutionSettings,
)
from dotenv import load_dotenv
from tqdm import tqdm
import asyncio
import json
import time
import re
from plugins.NativeGitAudit.analyzer import NativeGitAudit
from project_core.llm.models.commit_analysis import CommitAnalysis

# --- Utility Functions ---

def setup_logging():
    """Sets up a centralized logger."""
    log_dir = os.path.join(project_root, "_temp", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "qualitative_commit_analysis.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.info("Logging configured.")

def extract_json_from_markdown(raw_output):
    """Extracts a JSON object from a markdown code block."""
    match = re.search(r"```json\s*(\{.*?\})\s*```", raw_output, re.DOTALL)
    if match:
        return match.group(1)
    # Fallback for raw JSON
    try:
        json.loads(raw_output)
        return raw_output
    except json.JSONDecodeError:
        logging.error(f"Failed to extract JSON. Raw output was: {raw_output}")
        return None

def get_sort_key(filename):
    """
    Returns a sortable key from a commit filename.
    Handles both Unix timestamps and YYYY-MM-DD-HH-MM-SS formats.
    """
    try:
        # Try to parse as a Unix timestamp (integer part before '_')
        return int(filename.split('_')[0])
    except ValueError:
        try:
            # If it fails, try to parse as a detailed datetime format
            # Example: '2025-04-28-17-48-30-010e1f2...json' -> '2025-04-28-17-48-30'
            date_str = '-'.join(filename.split('-')[:6])
            dt_object = datetime.strptime(date_str, '%Y-%m-%d-%H-%M-%S')
            # Return a timestamp for consistent sorting
            return int(dt_object.timestamp())
        except (ValueError, IndexError):
            # If all else fails, treat it as a very old file to sort it last
            return 0

async def process_commit_file(kernel, prompt, args, filename, semaphore):
    """
    Traite un seul fichier de commit de manière asynchrone.
    
    Args:
        kernel: Instance du Semantic Kernel
        prompt: Template de prompt pour l'analyse
        args: Arguments de ligne de commande
        filename: Nom du fichier de commit à traiter
        semaphore: asyncio.Semaphore pour contrôler la concurrence
    
    Returns:
        tuple: (filename, success: bool, duration: float)
    """
    async with semaphore:
        commit_start_time = time.monotonic()
        logging.info(f"Processing file: {filename}")
        try:
            filepath = os.path.join(args.commits_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                commit_data = json.load(f)

            # Skip already processed files unless overwrite is requested
            analysis = commit_data.get("qualitative_analysis")
            if analysis and analysis.get("detailed_summary") and not args.overwrite:
                logging.info(f"[{filename}] Valid analysis already exists. Skipping.")
                commit_duration = time.monotonic() - commit_start_time
                return (filename, True, commit_duration)

            if not commit_data.get("files_changed"):
                logging.warning(f"[{filename}] No files_changed found. Skipping.")
                commit_duration = time.monotonic() - commit_start_time
                return (filename, True, commit_duration)

            aggregated_analysis = {
                "detailed_summary": "",
                "technical_debt_signals": [],
                "quality_leaps": []
            }

            files_to_process = commit_data["files_changed"]
            total_llm_time = 0
            for file_change in tqdm(files_to_process, desc=f"Analyzing files in {filename}", leave=False):
                if isinstance(file_change, str):
                    logging.warning(f"[{filename}] file_change is a string, not a dict. Skipping file: {file_change}")
                    continue
                
                file_path = file_change.get("filename")
                if not file_path:
                    logging.warning(f"[{filename}] No file_path found in a file_change entry. Skipping.")
                    continue
                diff_content = file_change.get("diff")

                if not diff_content:
                    logging.warning(f"[{filename}/{file_path}] No diff content. Skipping file.")
                    continue

                execution_settings = OpenAIPromptExecutionSettings(
                    service_id="default",
                    response_format={"type": "json_object"},
                )

                try:
                    logging.info(f"[{filename}/{file_path}] Invoking LLM for file...")
                    llm_start_time = time.monotonic()
                    result = await kernel.invoke_prompt(
                        prompt,
                        arguments=KernelArguments(input=diff_content),
                        settings=execution_settings
                    )
                    llm_duration = time.monotonic() - llm_start_time
                    total_llm_time += llm_duration
                    
                    raw_output = str(result)
                    json_str = extract_json_from_markdown(raw_output)

                    if not json_str:
                        raise ValueError("Could not extract JSON from LLM output.")

                    file_analysis = CommitAnalysis.model_validate_json(json_str)

                    # Aggregate results
                    aggregated_analysis["detailed_summary"] += f"--- Analysis for {file_path} ---\n{file_analysis.detailed_summary}\n\n"
                    aggregated_analysis["technical_debt_signals"].extend(file_analysis.technical_debt_signals)
                    aggregated_analysis["quality_leaps"].extend(file_analysis.quality_leaps)

                except Exception as e:
                    logging.error(f"[{filename}/{file_path}] Failed to analyze file: {e}")
                    continue
            
            logging.info(f"[{filename}] Total LLM analysis time: {total_llm_time:.2f} seconds.")
            
            if aggregated_analysis["detailed_summary"]:
                commit_data["qualitative_analysis"] = aggregated_analysis
                commit_data.pop("llm_summary", None)
                commit_data.pop("llm_summary_is_detailed", None)

                if args.prune_diffs:
                    logging.info(f"[{filename}] Pruning diff content as requested.")
                    for file_change in commit_data.get("files_changed", []):
                        if isinstance(file_change, dict):
                            file_change.pop("diff", None)
                
                output_file_path = os.path.join(args.commits_dir, filename)
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    json.dump(commit_data, f, indent=4)
                
                logging.info(f"Successfully enriched and saved analysis for {filename}")
            else:
                logging.warning(f"[{filename}] No analysis was generated (likely no diffs). Skipping file save.")
            
            commit_duration = time.monotonic() - commit_start_time
            logging.info(f"[{filename}] Total processing time: {commit_duration:.2f} seconds.")
            return (filename, True, commit_duration)

        except (FileNotFoundError, json.JSONDecodeError) as e:
            commit_duration = time.monotonic() - commit_start_time
            logging.error(f"[{filename}] File error: {e}")
            return (filename, False, commit_duration)
        except Exception as e:
            commit_duration = time.monotonic() - commit_start_time
            logging.error(f"[{filename}] Unexpected error: {e}")
            return (filename, False, commit_duration)


async def main():
    """
    Orchestrates the qualitative analysis of Git commits using Semantic Kernel.
    """
    # Initialize Semantic Kernel
    setup_logging()
    
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Run qualitative analysis on git commits.")
    parser.add_argument("--commits-dir", type=str, default=os.path.join(project_root, "docs", "commits_audit"), help="Directory containing commit JSON files.")
    parser.add_argument("--max-commits", type=int, default=100, help="Maximum number of commits to process.")
    parser.add_argument("--specific-filename", type=str, default=None, help="Specify a single filename to process.")
    parser.add_argument("--overwrite", action='store_true', help="Overwrite existing analysis.")
    parser.add_argument("--prune-diffs", action='store_true', help="Remove diff content from JSON after successful analysis.")
    parser.add_argument(
        "--num-workers",
        type=int,
        default=5,
        help="Number of parallel workers for commit analysis (default: 5, max recommended: 15)"
    )
    args = parser.parse_args()

    # Validation de la plage de workers
    if args.num_workers < 1:
        logging.error("num-workers must be at least 1")
        sys.exit(1)
    elif args.num_workers > 15:
        logging.warning(f"num-workers set to {args.num_workers}, but maximum recommended is 15")

    # --- Kernel Initialization ---
    kernel = sk.Kernel()
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    model_id = os.environ.get("OPENAI_CHAT_MODEL_ID")

    if not all([api_key, model_id]):
        logging.error("Missing required environment variables: OPENAI_API_KEY, OPENAI_CHAT_MODEL_ID")
        return

    try:
        service = OpenAIChatCompletion(service_id="default", ai_model_id=model_id, api_key=api_key)
        kernel.add_service(service)
    except Exception as e:
        logging.error(f"Failed to initialize Semantic Kernel service: {e}")
        return

    prompt = """
Analyze the following git diff and provide a qualitative analysis in JSON format.
The JSON object must conform to the following Pydantic model:

class CommitAnalysis(BaseModel):
    detailed_summary: str = Field(description="A detailed, factual summary of the commit's purpose and changes.")
    technical_debt_signals: List[str] = Field(description="A list of observations indicating potential new or increased technical debt.")
    quality_leaps: List[str] = Field(description="A list of observations indicating significant quality improvements.")

Git Diff:
{{$input}}

JSON Output:
"""
    # --- File Processing ---
    try:
        if args.specific_filename:
            commit_files = [args.specific_filename]
            logging.info(f"Processing specific file: {args.specific_filename}")
        else:
            commit_files = [f for f in os.listdir(args.commits_dir) if f.endswith('.json')]
            commit_files.sort(key=get_sort_key)
            logging.info(f"Found {len(commit_files)} commit files in {args.commits_dir}.")
    except (FileNotFoundError, IndexError) as e:
        logging.error(f"Error accessing or parsing commit files in {args.commits_dir}: {e}")
        return
        
    # --- Configuration de la parallélisation ---
    semaphore = asyncio.Semaphore(args.num_workers)
    
    # --- Traitement parallèle des fichiers ---
    tasks = []
    for filename in commit_files[:args.max_commits]:
        task = asyncio.create_task(
            process_commit_file(kernel, prompt, args, filename, semaphore)
        )
        tasks.append(task)
    
    # Exécution parallèle avec suivi de progression
    results = []
    total_start_time = time.monotonic()
    with tqdm(total=len(tasks), desc="Analyzing Commits") as pbar:
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            pbar.update(1)
            if result:
                logging.info(f"Completed: {result[0]} ({'Success' if result[1] else 'Failed'})")
    
    # --- Rapport final ---
    total_duration = time.monotonic() - total_start_time
    successful = sum(1 for r in results if r and r[1])
    total_time_from_results = sum(r[2] for r in results if r)
    logging.info(f"Parallel processing completed: {successful}/{len(results)} files successful")
    logging.info(f"Total script duration: {total_duration:.2f} seconds")
    logging.info(f"Sum of individual processing times: {total_time_from_results:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())