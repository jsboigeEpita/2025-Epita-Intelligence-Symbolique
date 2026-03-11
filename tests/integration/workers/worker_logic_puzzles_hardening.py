# -*- coding: utf-8 -*-
# tests/integration/workers/worker_logic_puzzles_hardening.py
"""
Worker pour l'exécution des tests de puzzles logiques dans un environnement JVM isolé.
"""

import sys
import json
import asyncio
from pathlib import Path

# Assurer que le répertoire racine du projet est dans le sys.path
# pour que les imports de modules fonctionnent correctement.
# Ce chemin est relatif à l'emplacement de ce script.
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from argumentation_analysis.config.settings import AppSettings
from argumentation_analysis.kernel.kernel_builder import KernelBuilder
from argumentation_analysis.orchestration.orchestrator import Orchestrator


def main(scenario_path_str: str):
    """
    Fonction principale du worker. Charge un scénario, exécute l'analyse
    et vérifie que le résultat est conforme aux attentes.
    """
    scenario_path = Path(scenario_path_str)
    if not scenario_path.exists():
        print(
            f"Erreur: Le fichier de scénario '{scenario_path_str}' n'existe pas.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Worker: Exécution du scénario de durcissement: {scenario_path.name}")

    with open(scenario_path, "r", encoding="utf-8") as f:
        scenario_data = json.load(f)

    facts = scenario_data.get("facts")
    expected_outcome = scenario_data.get("expected_outcome")

    if not facts or not expected_outcome:
        print(
            "Erreur: Le fichier de scénario doit contenir 'facts' et 'expected_outcome'.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Worker: Faits chargés: {len(facts)}")
    print(f"Worker: Résultat attendu: {expected_outcome}")

    # Initialisation de l'environnement
    settings = AppSettings()
    kernel = KernelBuilder.create_kernel(settings)
    llm_service_id = settings.service_manager.default_llm_service_id
    orchestrator = Orchestrator(kernel, llm_service_id)
    input_text = ". ".join(facts)

    try:
        # Exécution de l'analyse
        result = asyncio.run(orchestrator.run_analysis_async(input_text))
        print(f"Worker: Analyse terminée. Résultat obtenu: {result}")

        # Validation
        # C'est ici que l'assertion principale du test a lieu.
        # En cas d'échec, pytest (qui exécute ce script) le capturera.
        assert (
            expected_outcome in result
        ), f"Le résultat attendu '{expected_outcome}' n'a pas été trouvé dans le résultat réel '{result}'"
        print(f"Worker: Validation réussie pour {scenario_path.name}!")

    except Exception as e:
        print(
            f"Worker: Une erreur est survenue pendant l'analyse du scénario {scenario_path.name}: {e}",
            file=sys.stderr,
        )
        # Sortir avec un code d'erreur pour que le processus parent sache que le test a échoué.
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python worker_logic_puzzles_hardening.py <path_to_scenario.json>",
            file=sys.stderr,
        )
        sys.exit(1)

    scenario_file_path = sys.argv[1]
    main(scenario_file_path)
