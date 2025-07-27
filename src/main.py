import sys
import os

# Ajoute la racine du projet au Python Path pour permettre les imports absolus
# C'est une approche plus robuste pour les scripts exécutables.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.plugin_loader import PluginLoader
from src.core.orchestration_service import OrchestrationService
from src.core.contracts import OrchestrationRequest

def run_integration_test():
    """
    Exécute un test d'intégration de bout en bout du système.
    """
    print("--- DÉBUT DU TEST D'INTÉGRATION ---", flush=True)

    # 1. Initialiser le chargeur de plugins
    # Le répertoire 'plugins' est relatif à la racine du projet
    plugin_directories = [os.path.join(project_root, "plugins")]
    loader = PluginLoader(plugin_dirs=plugin_directories)

    # 2. Découvrir et charger les plugins
    loader.discover_plugins()
    loader.load_plugins()

    # Vérification que le plugin est bien chargé
    if "hello_world" not in loader.plugins:
        print("ERREUR FATALE: Le plugin 'hello_world' n'a pas pu être chargé.", flush=True)
        print("Vérifiez les logs de 'discover_plugins' et 'load_plugins' ci-dessus.", flush=True)
        return

    # 3. Initialiser le service d'orchestration
    orchestration_service = OrchestrationService(plugin_loader=loader)

    # 4. Créer et exécuter une requête de test
    test_request = OrchestrationRequest(
        plugin_name="hello_world",
        inputs={"name": "World"}
    )

    print("\n--- Exécution de la requête de test ---", flush=True)
    response = orchestration_service.execute_request(test_request)

    # 5. Afficher le résultat
    print("\n--- Résultat de la requête ---", flush=True)
    if response:
        print(f"ID Requête: {response.request_id}", flush=True)
        print(f"Statut: {response.status}", flush=True)
        if response.status == "SUCCESS":
            print(f"Sorties: {response.outputs}", flush=True)
        else:
            print(f"Erreur: {response.error_message}", flush=True)
    else:
        print("Aucune réponse reçue du service.", flush=True)

    print("\n--- FIN DU TEST D'INTÉGRATION ---", flush=True)

if __name__ == "__main__":
    run_integration_test()