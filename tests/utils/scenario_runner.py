import asyncio
import json
import sys
from pathlib import Path


from argumentation_analysis.config.settings import AppSettings
from argumentation_analysis.kernel.kernel_builder import KernelBuilder
from argumentation_analysis.orchestration.orchestrator import Orchestrator


def run_scenario_from_file(scenario_path: str):
    """
    Exécute un scénario de test de durcissement à partir d'un fichier JSON.

    Ce runner charge un scénario avec des faits et un résultat attendu,
    puis valide le comportement de l'agent logique.

    Args:
        scenario_path: Le chemin vers le fichier de scénario JSON.
    """
    print(f"Running hardening scenario: {scenario_path}")

    # 1. Charger le scénario
    with open(scenario_path, "r", encoding="utf-8") as f:
        scenario_data = json.load(f)

    facts = scenario_data.get("facts")
    if not facts:
        raise ValueError(
            "Le fichier de scénario de durcissement doit contenir une clé 'facts'."
        )

    expected_outcome = scenario_data.get("expected_outcome")
    if not expected_outcome:
        raise ValueError(
            "Le fichier de scénario de durcissement doit contenir une clé 'expected_outcome'."
        )

    # 2. Configuration et initialisation de l'application
    settings = AppSettings()
    kernel = KernelBuilder.create_kernel(settings)
    llm_service_id = settings.service_manager.default_llm_service_id

    # 3. Initialiser l'Orchestrateur
    orchestrator = Orchestrator(kernel, llm_service_id)

    # 4. Exécuter l'analyse
    try:
        # L'orchestrateur exécute une méthode asynchrone
        # Note: nous passons les faits comme une seule chaîne de caractères concaténée pour l'instant.
        # Une amélioration future pourrait être de gérer une liste de faits directement.
        input_text = ". ".join(facts)
        result = asyncio.run(orchestrator.run_analysis_async(input_text))

        # Pour les tests de durcissement, nous vérifions si le résultat contient le résultat attendu
        # (par exemple, "contradiction").
        # C'est une simplification ; une assertion plus robuste serait nécessaire dans un vrai test.
        print(f"Analysis Result: {result}")
        print(f"Expected Outcome: {expected_outcome}")

        # La logique de validation réelle se trouvera dans le corps du test qui appelle ce runner.
        # Ce runner se contente d'exécuter et de retourner le résultat.
        return result, expected_outcome

    except Exception as e:
        print(f"Une erreur est survenue pendant l'exécution du scénario: {e}")
        raise
