import os
import shutil
import sys
from pprint import pprint

# Ajout du chemin racine au sys.path pour résoudre les imports
# Cela suppose que le script est exécuté depuis la racine du projet,
# ou que la structure est gérée par un point d'entrée qui le fait.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from argumentation_analysis.plugin_framework.core.plugin_loader import PluginLoader
from argumentation_analysis.plugin_framework.core.services.orchestration_service import OrchestrationService
from argumentation_analysis.plugin_framework.benchmarking.benchmark_service import BenchmarkService


def main():
    """
    Point d'entrée pour l'exécution du framework de benchmarking.
    """
    print("--- Initialisation du Framework de Benchmarking ---")

    # 1. Initialiser le PluginLoader et charger les plugins
    # Le chemin pointe vers le répertoire standard des plugins.
    plugins_path = os.path.join(
        os.path.dirname(__file__), "core", "plugins", "standard"
    )

    # Pour ce test, nous créons un plugin factice "hello_world"
    # car il n'existe pas encore dans la structure.
    # Ceci est une mesure temporaire pour la validation.
    hello_world_plugin_path = os.path.join(plugins_path, "hello_world")
    os.makedirs(hello_world_plugin_path, exist_ok=True)
    with open(os.path.join(hello_world_plugin_path, "__init__.py"), "w") as f:
        f.write("""
from argumentation_analysis.plugin_framework.core.plugins.interfaces import BasePlugin

class HelloWorldPlugin(BasePlugin):
    def greet(self, name: str) -> dict:
        return {"greeting": f"Hello, {name}!"}
""")

    plugin_loader = PluginLoader(plugin_paths=[plugins_path])
    plugin_registry = plugin_loader.discover()

    if not plugin_registry:
        print(
            "Erreur: Aucun plugin n'a été chargé. Vérifiez le chemin et la structure des plugins.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Plugins chargés : {list(plugin_registry.keys())}")

    # 2. Initialiser l'OrchestrationService avec le registre de plugins
    orchestration_service = OrchestrationService(plugin_registry=plugin_registry)

    # 3. Initialiser le BenchmarkService
    benchmark_service = BenchmarkService(orchestration_service=orchestration_service)

    # 4. Définir et exécuter une suite de tests
    plugin_to_test = "HelloWorldPlugin"
    capability_to_test = "greet"

    if plugin_to_test not in plugin_registry:
        print(
            f"Erreur: Le plugin de test '{plugin_to_test}' n'est pas dans le registre.",
            file=sys.stderr,
        )
        sys.exit(1)

    test_queries = [
        {"name": "Alice"},
        {"name": "Bob"},
        {"name": "Charlie"},
        {"name": "Développeur"},
        {},  # Test avec une entrée potentiellement invalide
    ]

    print(
        f"\nLancement de la suite de tests pour : {plugin_to_test}.{capability_to_test}"
    )

    # 5. Appel au service de benchmark
    suite_result = benchmark_service.run_suite(
        plugin_name=plugin_to_test,
        capability_name=capability_to_test,
        requests=test_queries,
    )

    # 6. Affichage des résultats
    print("\n--- Rapport de Benchmark ---")
    print(f"  Plugin: {suite_result.plugin_name}")
    print(f"  Capacité: {suite_result.capability_name}")
    print("-" * 30)
    print("  Résumé:")
    print(f"    Exécutions totales: {suite_result.total_runs}")
    print(f"    - Réussies: {suite_result.successful_runs}")
    print(f"    - Échouées: {suite_result.failed_runs}")
    print(f"    Durée totale: {suite_result.total_duration_ms:.2f} ms")
    print("\n  Statistiques (sur exécutions réussies):")
    print(f"    Durée moyenne: {suite_result.average_duration_ms:.2f} ms")
    print(f"    Durée min: {suite_result.min_duration_ms:.2f} ms")
    print(f"    Durée max: {suite_result.max_duration_ms:.2f} ms")

    print("\n  Détails des exécutions:")
    # Utilisation de model_dump() de Pydantic pour une sérialisation propre
    pprint([result.model_dump() for result in suite_result.results])

    # Nettoyage du plugin factice
    os.remove(os.path.join(hello_world_plugin_path, "__init__.py"))
    shutil.rmtree(hello_world_plugin_path)


if __name__ == "__main__":
    main()
