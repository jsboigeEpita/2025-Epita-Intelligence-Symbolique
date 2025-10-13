from typing import Dict, Any

# On suppose que le CWD est la racine du projet pour cet import relatif
from src.core.plugin_loader import BasePlugin
from src.core.contracts import PluginManifest

class HelloWorldPlugin(BasePlugin):
    """
    Implémentation du plugin 'Hello World'.
    """
    def __init__(self, manifest: PluginManifest):
        super().__init__(manifest)

    def execute(self, capability_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exécute la capacité 'greet'.
        """
        if capability_name == "greet":
            name = inputs.get("name")
            if not name:
                raise ValueError("L'input 'name' est requis pour la capacité 'greet'.")
            
            message = f"Hello, {name}!"
            return {"message": message}
        else:
            raise NotImplementedError(f"La capacité '{capability_name}' n'est pas supportée par ce plugin.")