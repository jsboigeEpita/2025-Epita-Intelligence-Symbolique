import re
import os
import sys
import shlex

import logging

from project_core.utils.shell import run_sync, ShellCommandError

# Configuration du logging
log_file_path = 'logs/experiments.log'
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
def run_experiments():
    """
    Lance une série d'expériences en variant les agents et les taxonomies,
    capture les scores de précision et génère un rapport Markdown.
    """
    agents = ["simple", "workflow_only", "explore_only", "full"]
    taxonomies = ["taxonomy_small.csv", "taxonomy_medium.csv", "taxonomy_full.csv"]
    taxonomy_base_path = "argumentation_analysis/data/"
    validation_script_path = "demos/validation_complete_epita.py"

    results = {agent: {} for agent in agents}

    print("Début des expériences...")

    # Créer le répertoire pour les traces d'expérimentation
    trace_log_dir = "logs/experiment_traces"
    os.makedirs(trace_log_dir, exist_ok=True)


    for agent in agents:
        for taxonomy_file in taxonomies:
            taxonomy_path = os.path.join(taxonomy_base_path, taxonomy_file)
            taxonomy_name = taxonomy_file.replace('.csv', '').replace('taxonomy_', '')

            # Définir un nom de fichier de log unique pour la trace
            trace_log_filename = f"agent-{agent}_taxonomy-{taxonomy_name}.log"
            trace_log_path = os.path.join(trace_log_dir, trace_log_filename)

            logging.info(f"Exécution : Agent='{agent}', Taxonomie='{taxonomy_name}'...")
            logging.info(f"Fichier de trace : {trace_log_path}")

            # Construction de la commande à exécuter à l'intérieur de l'environnement géré
            inner_command_parts = [
                sys.executable,
                validation_script_path,
                "--agent-type", agent,
                "--taxonomy", taxonomy_path,
                "--verbose",
                "--trace-log-path", trace_log_path
            ]
            
            # La commande est directement passée comme une liste d'arguments
            # au script environment_manager, qui attend maintenant une liste.
            command = [
                sys.executable,
                "-m", "project_core.core_from_scripts.environment_manager",
                "run",
                *inner_command_parts
            ]
            
            try:
                # Utilisation du nouveau service unifié
                result = run_sync(command, check_errors=True)
                
                output = result.stdout
                
                logging.info(f"--- STDOUT de {agent}/{taxonomy_name} ---")
                logging.info(output)
                logging.info(f"--- Fin STDOUT ---")

                # La gestion d'erreur est maintenant centralisée, on capture ShellCommandError
                # L'ancien 'if process.returncode != 0:' est géré par check_errors=True

                # Expression régulière pour trouver le score de précision final
                match = re.search(r"SCORE FINAL:.*?\((\d+\.\d+)%\)", output)
                
                if match:
                    score = float(match.group(1))
                    results[agent][taxonomy_name] = f"{score:.2f}%"
                    logging.info(f"  -> Score trouvé : {score:.2f}%")
                else:
                    results[agent][taxonomy_name] = "N/A"
                    logging.warning("  -> Score non trouvé dans la sortie.")

            except ShellCommandError as e:
                logging.error(f"  -> Erreur lors de l'exécution pour Agent='{agent}', Taxonomie='{taxonomy_name}':")
                logging.error(f"--- STDERR de {agent}/{taxonomy_name} ---")
                logging.error(e.stderr)
                logging.error(f"--- Fin STDERR ---")
                results[agent][taxonomy_name] = "Erreur"
            except FileNotFoundError:
                logging.error(f"Erreur: Le script '{validation_script_path}' est introuvable.")
                return

    logging.info("\nExpériences terminées.\n")
    generate_markdown_report(results, taxonomies)

def generate_markdown_report(results, taxonomies):
    """
    Génère et affiche un tableau Markdown à partir des résultats des expériences.
    """
    header = "| Agent          | " + " | ".join([t.replace('.csv', '').replace('taxonomy_', '').capitalize() for t in taxonomies]) + " |"
    separator = "|----------------|-" + "-|-".join(["-" * len(t.replace('.csv', '').replace('taxonomy_', '')) for t in taxonomies]) + "-|"
    
    logging.info("Tableau des résultats :")
    logging.info(header)
    logging.info(separator)

    for agent, scores in results.items():
        row = f"| {agent:<14} |"
        for taxonomy_file in taxonomies:
            taxonomy_name = taxonomy_file.replace('.csv', '').replace('taxonomy_', '')
            score = scores.get(taxonomy_name, "N/A")
            row += f" {score:<{len(taxonomy_name)}} |"
        logging.info(row)

if __name__ == "__main__":
    run_experiments()