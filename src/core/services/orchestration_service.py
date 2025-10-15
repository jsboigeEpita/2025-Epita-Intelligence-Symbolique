from typing import Dict, Any
from src.core.contracts import OrchestrationRequest, OrchestrationResponse


class OrchestrationService:
    """
    Guichet de Service Unique. Centralise les requêtes et les dirige
    vers les plugins ou workflows appropriés.
    """

    def __init__(self, plugin_registry: Dict[str, Any]):
        """
        Initialise le service avec un registre de plugins.

        Args:
            plugin_registry: Un dictionnaire mappant les noms de plugins
                             à leurs instances.
        """
        self.plugin_registry = plugin_registry

    def handle_request(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """
        Traite une requête d'orchestration et la route en fonction de son mode.
        """
        # Dans cette itération, nous ne gérons que le mode 'direct_plugin_call'
        # comme requis pour le benchmark.
        if request.mode == "direct_plugin_call":
            return self._handle_direct_plugin_call(request)
        else:
            return OrchestrationResponse(
                status="error",
                error_message=f"Le mode d'orchestration '{request.mode}' n'est pas supporté.",
            )

    def _handle_direct_plugin_call(
        self, request: OrchestrationRequest
    ) -> OrchestrationResponse:
        """
        Gère l'appel direct à une capacité d'un plugin standard.
        """
        try:
            plugin_name, function_name = request.target.split(".")

            if plugin_name not in self.plugin_registry:
                raise ValueError(f"Plugin '{plugin_name}' non trouvé dans le registre.")

            plugin_instance = self.plugin_registry[plugin_name]

            if not hasattr(plugin_instance, function_name):
                raise ValueError(
                    f"La capacité '{function_name}' n'a pas été trouvée dans le plugin '{plugin_name}'."
                )

            function_to_call = getattr(plugin_instance, function_name)

            # Invocation de la fonction avec le payload
            result = function_to_call(**request.payload)

            return OrchestrationResponse(status="success", result=result)

        except Exception as e:
            return OrchestrationResponse(status="error", error_message=str(e))
