import subprocess
import os
import sys
import json
import base64
import tempfile
from pathlib import Path

# Ensure the project root is in the Python path to allow for absolute-like imports
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

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

# --- Demo from command line argument ---
print("=" * 80)
print("STARTING RHETORICAL ANALYSIS DEMONSTRATIONS")
print("=" * 80)

for demo in sample_texts:
    print(f"\n\n--- {demo['title']} ---\n")
    print(f"Analyzing text: \"{demo['text']}\"\n")

    input_temp_path = None
    output_temp_path = None
    try:
        # Create temporary files for both input text and JSON output
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', suffix='.txt') as input_fp:
            input_fp.write(demo['text'])
            input_temp_path = Path(input_fp.name)

        with tempfile.NamedTemporaryFile(mode='r', delete=False, encoding='utf-8', suffix='.json') as output_fp:
            output_temp_path = Path(output_fp.name)

        analysis_input_file = input_temp_path.as_posix()
        analysis_output_file = output_temp_path.as_posix()

        # Construct the command to use --file for input and --output-file for JSON result
        script_path = ".\\activate_project_env.ps1"
        python_command = f'python argumentation_analysis/run_analysis.py --file "{analysis_input_file}" --output-file "{analysis_output_file}"'
        full_ps_command = f"& '{script_path}' -CommandToRun '{python_command}'"

        encoded_command = base64.b64encode(full_ps_command.encode('utf-16-le')).decode('ascii')
        command = [
            "powershell", "-ExecutionPolicy", "Bypass",
            "-EncodedCommand", encoded_command
        ]

        # Execute the command, capturing stderr for logging/debugging
        result = subprocess.run(command, check=True, text=True, capture_output=True, encoding='utf-8')
        
        print("--- ANALYSIS RESULT ---")
        
        # Read the JSON result from the temporary output file
        json_output_str = output_temp_path.read_text(encoding='utf-8')

        try:
            # Check if the output string is not empty before trying to load it
            if json_output_str:
                analysis_data = json.loads(json_output_str)
                print(json.dumps(analysis_data, indent=2, ensure_ascii=False))
            else:
                print("Analysis script returned an empty output file.")
                print("--- RAW STDERR ---")
                print(result.stderr)

        except json.JSONDecodeError:
            print("Could not decode JSON from the analysis script's output file:")
            print("--- RAW FILE CONTENT ---")
            print(json_output_str)
            print("--- RAW STDERR ---")
            print(result.stderr)

        print(f"\n--- {demo['title']} COMPLETED ---")

    except subprocess.CalledProcessError as e:
        print(f"\n--- ERROR during {demo['title']} ---", file=sys.stderr)
        print("Stderr:", e.stderr, file=sys.stderr)
    except FileNotFoundError:
        print("\n--- ERROR: 'python' or 'powershell' command not found. Make sure they are in your PATH.", file=sys.stderr)
        break
    finally:
        # Ensure temporary files are cleaned up
        if input_temp_path and input_temp_path.exists():
            os.remove(input_temp_path)
        if output_temp_path and output_temp_path.exists():
            os.remove(output_temp_path)


# --- Demo from file ---
demo_file_path = "argumentation_analysis/demos/rhetorical_analysis/sample_epita_discourse.txt"
demo_file_content = """
Le projet EPITA Intelligence Symbolique 2025 est un défi majeur.
Certains disent qu'il est trop ambitieux et voué à l'échec car aucun projet étudiant n'a jamais atteint ce niveau d'intégration.
Cependant, cet argument ignore les compétences uniques de notre équipe et les avancées technologiques récentes.
Nous devons nous concentrer sur une livraison incrémentale et prouver que la réussite est possible.
"""

print(f"\n\n--- Demonstration 4: Analysis from File ---\n")
output_temp_path_demo4 = None
try:
    # Write the content to the demo file
    with open(demo_file_path, "w", encoding="utf-8") as f:
        f.write(demo_file_content)
    print(f"Created demo file: {demo_file_path}")

    # Create a temporary file for the JSON output
    with tempfile.NamedTemporaryFile(mode='r', delete=False, encoding='utf-8', suffix='.json') as output_fp:
        output_temp_path_demo4 = Path(output_fp.name)

    print(f"Analyzing text from file...\n")
    
    analysis_output_file = output_temp_path_demo4.as_posix()

    # Construct the command to use --file for input and --output-file for JSON result
    script_path = ".\\activate_project_env.ps1"
    python_command = f'python argumentation_analysis/run_analysis.py --file "{demo_file_path}" --output-file "{analysis_output_file}"'
    full_ps_command = f"& '{script_path}' -CommandToRun '{python_command}'"

    encoded_command = base64.b64encode(full_ps_command.encode('utf-16-le')).decode('ascii')

    command = [
        "powershell", "-ExecutionPolicy", "Bypass",
        "-EncodedCommand", encoded_command
    ]
    result = subprocess.run(command, check=True, text=True, capture_output=True, encoding='utf-8')
    
    print("--- ANALYSIS RESULT ---")
    
    # Read the JSON result from the temporary output file
    json_output_str = output_temp_path_demo4.read_text(encoding='utf-8')
    try:
        if json_output_str:
            analysis_data = json.loads(json_output_str)
            print(json.dumps(analysis_data, indent=2, ensure_ascii=False))
        else:
            print("Analysis script returned an empty output file for Demonstration 4.")
            print("--- RAW STDERR ---")
            print(result.stderr)
    except json.JSONDecodeError:
        print("Could not decode JSON from the analysis script's output file:")
        print("--- RAW FILE CONTENT ---")
        print(json_output_str)
        print("--- RAW STDERR ---")
        print(result.stderr)

    print(f"\n--- Demonstration 4 COMPLETED ---")

except Exception as e:
    print(f"\n--- ERROR during Demonstration 4 ---", file=sys.stderr)
    print(e, file=sys.stderr)
finally:
    # Ensure temporary file is cleaned up
    if output_temp_path_demo4 and output_temp_path_demo4.exists():
        os.remove(output_temp_path_demo4)


print("\n\n" + "=" * 80)
print("ALL DEMONSTRATIONS COMPLETED")
print("=" * 80)