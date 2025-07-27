import uuid
from typing import Dict, Any

from .contracts import OrchestrationRequest, OrchestrationResponse
from .plugin_loader import PluginLoader

class OrchestrationService:
    """
    Point d'entrée principal pour l'exécution des requêtes.
    Ce service utilise le PluginLoader pour exécuter des capacités de plugin spécifiques.
    """
    def __init__(self, plugin_loader: PluginLoader):
        """
        Initialise le service avec une instance de PluginLoader.
        """
        if not isinstance(plugin_loader, PluginLoader):
            raise TypeError("plugin_loader doit être une instance de PluginLoader.")
        self.plugin_loader = plugin_loader
        print("OrchestrationService initialisé.")

    def execute_request(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """
        Traite une OrchestrationRequest et retourne une OrchestrationResponse.
        """
        request_id = str(uuid.uuid4())
        print(f"[{request_id}] Traitement de la requête pour le plugin '{request.plugin_name}'...")

        try:
            # 1. Récupérer le plugin
            plugin = self.plugin_loader.get_plugin(request.plugin_name)

            # 2. Extraire la première capacité (logique simplifiée pour l'instant)
            # NOTE: Une future version devrait permettre de spécifier la capacité dans la requête.
            if not plugin.manifest.capabilities:
                raise RuntimeError(f"Le plugin '{request.plugin_name}' n'a aucune capacité définie.")
            
            capability_name = plugin.manifest.capabilities[0].name
            print(f"[{request_id}] Exécution de la capacité '{capability_name}'...")

            # 3. Exécuter la capacité du plugin
            outputs = plugin.execute(
                capability_name=capability_name,
                inputs=request.inputs
            )

            # 4. Construire la réponse de succès
            response = OrchestrationResponse(
                request_id=request_id,
                status="SUCCESS",
                outputs=outputs
            )
            print(f"[{request_id}] Exécution terminée avec succès.")

        except (ValueError, RuntimeError, TypeError) as e:
            # Erreurs attendues (plugin non trouvé, pas de capacité, etc.)
            error_message = f"Erreur lors du traitement de la requête : {e}"
            print(f"[{request_id}] {error_message}")
            response = OrchestrationResponse(
                request_id=request_id,
                status="ERROR",
                error_message=error_message
            )
        except Exception as e:
            # Erreurs inattendues
            error_message = f"Une erreur inattendue est survenue : {e}"
            print(f"[{request_id}] {error_message}")
            response = OrchestrationResponse(
                request_id=request_id,
                status="ERROR",
                error_message=error_message
            )

        return response