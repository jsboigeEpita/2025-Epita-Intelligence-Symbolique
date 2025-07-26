import os
import sys

# List of files identified with syntax errors, likely due to BOM
FILES_TO_FIX = [
    "argumentation_analysis/agents/core/logic/fol_logic_agent.py",
    "argumentation_analysis/agents/core/pm/pm_agent.py",
    "argumentation_analysis/core/llm_service.py",
    "argumentation_analysis/core/strategies.py",
    "argumentation_analysis/orchestration/cluedo_extended_orchestrator.py",
    "argumentation_analysis/orchestration/conversation_orchestrator.py",
    "argumentation_analysis/orchestration/hierarchical/operational/adapters/informal_agent_adapter.py",
    "argumentation_analysis/orchestration/hierarchical/operational/adapters/pl_agent_adapter.py",
    "argumentation_analysis/orchestration/real_llm_orchestrator.py",
    "argumentation_analysis/pipelines/unified_text_analysis.py",
    "argumentation_analysis/scripts/simulate_balanced_participation.py",
    "argumentation_analysis/utils/dev_tools/repair_utils.py",
    "argumentation_analysis/utils/extract_repair/verify_extracts_with_llm.py",
    "argumentation_analysis/utils/tweety_error_analyzer.py",
    "examples/scripts_demonstration/demonstration_epita.py",
    "examples/scripts_demonstration/modules/demo_cas_usage.py",
    "examples/scripts_demonstration/modules/demo_integrations.py",
    "examples/scripts_demonstration/modules/demo_outils_utils.py",
    "examples/scripts_demonstration/modules/demo_services_core.py",
    "examples/scripts_demonstration/modules/demo_tests_validation.py",
    "examples/scripts_demonstration/modules/demo_utils.py",
    # Note: documentation_system/interactive_guide.py has a different error (f-string)
    # and will be handled separately if needed.
    # tests/unit/agents/test_fol_agent_sort_repair.py was not found.
]

UTF8_BOM = b'\xef\xbb\xbf'

def fix_bom_in_file(file_path):
    """
    Checks for and removes the UTF-8 BOM from a file.
    Returns True if the file was fixed, False otherwise.
    """
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}", file=sys.stderr)
        return False

    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        if content.startswith(UTF8_BOM):
            print(f"Fixing BOM in: {file_path}")
            content = content[len(UTF8_BOM):]
            with open(file_path, 'wb') as f:
                f.write(content)
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error processing file {file_path}: {e}", file=sys.stderr)
        return False

def main():
    """
    Main function to iterate through files and fix BOM issues.
    """
    fixed_count = 0
    not_bom_count = 0
    
    print("--- Starting BOM Fixer ---")
    for file_path in FILES_TO_FIX:
        if fix_bom_in_file(file_path):
            fixed_count += 1
        else:
            not_bom_count += 1
    
    print("\n--- BOM Fixer Complete ---")
    print(f"Successfully fixed {fixed_count} files.")
    print(f"{not_bom_count} files did not have a BOM.")

if __name__ == "__main__":
    main()