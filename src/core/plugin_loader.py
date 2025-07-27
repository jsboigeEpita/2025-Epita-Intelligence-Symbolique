import os
import importlib
import inspect
from typing import Dict, List, Any
from src.core.plugins.interfaces import BasePlugin

class PluginLoader:
    """
    Découvre, charge et instancie les plugins à partir de répertoires spécifiés.
    """

    def __init__(self, plugin_paths: List[str]):
        """
        Initialise le chargeur avec une liste de chemins vers les plugins.
        """
        self.plugin_paths = plugin_paths

    def discover(self) -> Dict[str, BasePlugin]:
        """
        Scanne les chemins, charge dynamiquement les modules de plugins,
        et retourne un registre des instances de plugins valides.
        """
        plugin_registry: Dict[str, BasePlugin] = {}
        
        for path in self.plugin_paths:
            if not os.path.isdir(path):
                continue

            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    module_name = f"src.core.plugins.standard.{item}"
                    try:
                        module = importlib.import_module(module_name)
                        for _, class_member in inspect.getmembers(module, inspect.isclass):
                            # Vérifie si la classe est bien définie dans ce module,
                            # hérite de BasePlugin, et n'est pas BasePlugin elle-même.
                            if class_member.__module__ == module_name and \
                               issubclass(class_member, BasePlugin) and \
                               class_member is not BasePlugin:
                                
                                # Le nom du plugin est le nom de la classe.
                                plugin_name = class_member.__name__
                                if plugin_name not in plugin_registry:
                                    plugin_registry[plugin_name] = class_member()
                                    
                    except ImportError as e:
                        print(f"Avertissement : Impossible d'importer le module {module_name}. Erreur: {e}")

        return plugin_registry