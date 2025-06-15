import subprocess
import os
import sys
import json

# Ensure the script is run from the root of the argumentation_analysis directory
# This helps locate run_analysis.py correctly.
# A more robust solution might involve setting Python paths, but for a demo, this is sufficient.
if not os.path.exists('run_analysis.py'):
    print("Error: This script must be run from the 'argumentation_analysis' directory.", file=sys.stderr)
    sys.exit(1)

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

    # Construct the command to run the analysis
    command = [
        "python",
        "run_analysis.py",
        "--text",
        demo["text"]
    ]

    # Execute the command
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True, encoding='utf-8')
        print("--- ANALYSIS RESULT ---")
        
        # Le stdout peut contenir des logs avant le JSON. Trouver le début du JSON.
        json_output_str = result.stdout
        json_start_index = json_output_str.find('{')
        if json_start_index != -1:
            json_output_str = json_output_str[json_start_index:]
            try:
                analysis_data = json.loads(json_output_str)
                print(json.dumps(analysis_data, indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                print("Could not decode JSON from analysis script output:")
                print(result.stdout)
        else:
            print("No JSON object found in the output.")
            print("--- RAW STDOUT ---")
            print(result.stdout)
            print("--- RAW STDERR ---")
            print(result.stderr)

        print(f"\n--- {demo['title']} COMPLETED ---")
    except subprocess.CalledProcessError as e:
        print(f"\n--- ERROR during {demo['title']} ---", file=sys.stderr)
        print("Stderr:", e.stderr, file=sys.stderr)
    except FileNotFoundError:
        print("\n--- ERROR: 'python' command not found. Make sure Python is in your PATH.", file=sys.stderr)
        break


# --- Demo from file ---
demo_file_path = "demos/sample_epita_discourse.txt"
demo_file_content = """
Le projet EPITA Intelligence Symbolique 2025 est un défi majeur.
Certains disent qu'il est trop ambitieux et voué à l'échec car aucun projet étudiant n'a jamais atteint ce niveau d'intégration.
Cependant, cet argument ignore les compétences uniques de notre équipe et les avancées technologiques récentes.
Nous devons nous concentrer sur une livraison incrémentale et prouver que la réussite est possible.
"""

print(f"\n\n--- Demonstration 4: Analysis from File ---\n")
try:
    with open(demo_file_path, "w", encoding="utf-8") as f:
        f.write(demo_file_content)
    print(f"Created demo file: {demo_file_path}")

    print(f"Analyzing text from file...\n")
    command = [
        "python",
        "run_analysis.py",
        "--file",
        demo_file_path
    ]
    result = subprocess.run(command, check=True, text=True, capture_output=True, encoding='utf-8')
    print("--- ANALYSIS RESULT ---")
    try:
        analysis_data = json.loads(result.stdout)
        print(json.dumps(analysis_data, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print("Could not decode JSON from analysis script output:")
        print(result.stdout)
    print(f"\n--- Demonstration 4 COMPLETED ---")

except Exception as e:
    print(f"\n--- ERROR during Demonstration 4 ---", file=sys.stderr)
    print(e, file=sys.stderr)


print("\n\n" + "=" * 80)
print("ALL DEMONSTRATIONS COMPLETED")
print("=" * 80)