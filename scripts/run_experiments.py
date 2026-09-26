"""Lance la validation EPITA pour chaque couple (agent, taxonomie) et rapporte
le score de chacun dans un tableau Markdown.

La chaîne : ce script lance
``examples/03_demos_overflow/validation/validation_complete_epita.py`` à travers
``project_core.core_from_scripts.environment_manager run``, puis lit la ligne
``SCORE FINAL`` de sa sortie. Chaque exécution écrit ses traces, une par
scénario, dans ``logs/experiment_traces/agent-<agent>_taxonomy-<taxonomie>/``.

Sans option, la démo appelle le modèle configuré (``OPENAI_CHAT_MODEL_ID``),
une fois par couple. ``--integration-test`` fait tourner la chaîne sur le LLM
simulé, sans crédit : la démo force alors l'agent ``explore_only``, le tableau
ne compare donc rien, il montre seulement que la chaîne tourne de bout en bout.

Lancement depuis la racine du dépôt, dans l'environnement conda du projet :
``python scripts/run_experiments.py [--integration-test]``.
"""

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

from project_core.utils.shell import run_sync, ShellCommandError

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_SCRIPT = (
    REPO_ROOT
    / "examples"
    / "03_demos_overflow"
    / "validation"
    / "validation_complete_epita.py"
)
TAXONOMY_DIR = REPO_ROOT / "argumentation_analysis" / "data"
TRACE_ROOT = REPO_ROOT / "logs" / "experiment_traces"
LOG_FILE = REPO_ROOT / "logs" / "experiments.log"

AGENTS = ["simple", "workflow_only", "explore_only", "full"]
TAXONOMIES = ["taxonomy_small.csv", "taxonomy_medium.csv", "taxonomy_full.csv"]

# La ligne que la démo imprime en fin d'exécution (``final_score_line``).
SCORE_PATTERN = re.compile(r"SCORE FINAL:.*?\((\d+\.\d+)%\)")


def taxonomy_name(taxonomy_file: str) -> str:
    return taxonomy_file.replace(".csv", "").replace("taxonomy_", "")


def build_validation_command(
    agent: str, taxonomy_file: str, trace_dir: Path, integration_test: bool = False
) -> List[str]:
    """La commande d'une expérience : la démo, lancée par l'environment manager."""
    inner_command = [
        sys.executable,
        str(VALIDATION_SCRIPT),
        "--agent-type",
        agent,
        "--taxonomy",
        str(TAXONOMY_DIR / taxonomy_file),
        "--verbose",
        "--trace-dir",
        str(trace_dir),
    ]
    if integration_test:
        inner_command.append("--integration-test")
    return [
        sys.executable,
        "-m",
        "project_core.core_from_scripts.environment_manager",
        "run",
        *inner_command,
    ]


def extract_score(output: str) -> Optional[float]:
    """Le pourcentage de la ligne ``SCORE FINAL``, ou ``None`` sans score noté."""
    match = SCORE_PATTERN.search(output or "")
    return float(match.group(1)) if match else None


def run_experiments(integration_test: bool = False) -> Dict[str, Dict[str, str]]:
    """
    Lance une série d'expériences en variant les agents et les taxonomies,
    capture les scores de précision et génère un rapport Markdown.
    """
    if not VALIDATION_SCRIPT.exists():
        raise FileNotFoundError(
            f"Script de validation introuvable : {VALIDATION_SCRIPT}"
        )

    results: Dict[str, Dict[str, str]] = {agent: {} for agent in AGENTS}
    print("Début des expériences...")

    for agent in AGENTS:
        for taxonomy_file in TAXONOMIES:
            name = taxonomy_name(taxonomy_file)
            trace_dir = TRACE_ROOT / f"agent-{agent}_taxonomy-{name}"

            logging.info(f"Exécution : Agent='{agent}', Taxonomie='{name}'...")
            logging.info(f"Traces : {trace_dir}")

            command = build_validation_command(
                agent, taxonomy_file, trace_dir, integration_test
            )
            try:
                # La démo sort en erreur dès qu'un scénario échoue : le code de
                # sortie ne dit pas si un score a été produit, la sortie le dit.
                result = run_sync(command, cwd=REPO_ROOT, check_errors=False)
            except ShellCommandError as e:
                logging.error(f"  -> Échec du lancement pour {agent}/{name} : {e}")
                logging.error(e.stderr)
                results[agent][name] = "Erreur"
                continue

            logging.info(f"--- STDOUT de {agent}/{name} ---")
            logging.info(result.stdout)
            logging.info("--- Fin STDOUT ---")

            score = extract_score(result.stdout)
            if score is not None:
                results[agent][name] = f"{score:.2f}%"
                logging.info(f"  -> Score trouvé : {score:.2f}%")
            elif result.returncode != 0:
                logging.error(
                    f"  -> Aucun score, code de sortie {result.returncode} "
                    f"pour {agent}/{name}"
                )
                logging.error(result.stderr)
                results[agent][name] = "Erreur"
            else:
                results[agent][name] = "N/A"
                logging.warning("  -> Score non trouvé dans la sortie.")

    logging.info("\nExpériences terminées.\n")
    generate_markdown_report(results, TAXONOMIES)
    return results


def generate_markdown_report(results, taxonomies):
    """
    Génère et affiche un tableau Markdown à partir des résultats des expériences.
    """
    header = (
        "| Agent          | "
        + " | ".join([taxonomy_name(t).capitalize() for t in taxonomies])
        + " |"
    )
    separator = (
        "|----------------|-"
        + "-|-".join(["-" * len(taxonomy_name(t)) for t in taxonomies])
        + "-|"
    )

    logging.info("Tableau des résultats :")
    logging.info(header)
    logging.info(separator)

    for agent, scores in results.items():
        row = f"| {agent:<14} |"
        for taxonomy_file in taxonomies:
            name = taxonomy_name(taxonomy_file)
            score = scores.get(name, "N/A")
            row += f" {score:<{len(name)}} |"
        logging.info(row)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--integration-test",
        action="store_true",
        help="LLM simulé, sans crédit (la démo force l'agent explore_only).",
    )
    args = parser.parse_args(argv)

    # Configuration du logging au lancement, pas à l'import (#2346).
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    run_experiments(integration_test=args.integration_test)


if __name__ == "__main__":
    main()
