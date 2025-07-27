# -*- coding: utf-8 -*-
"""
Mécanisme de découverte et de chargement dynamique des plugins.
"""

import importlib
import inspect
import os
from pathlib import Path
from typing import Dict, List, Type

from src.core.plugins.interfaces import BasePlugin


class PluginLoader:
    """
    Charge et gère les plugins du système.

    Cette classe est responsable de la découverte, du chargement et de 
    l'instanciation des plugins qui respectent l'interface `BasePlugin`.
    Elle scanne un répertoire donné, importe dynamiquement les modules Python
    et identifie les classes de plugins valides.
    """

    def __init__(self, plugins_path: str):
        """
        Initialise le chargeur de plugins.

        Args:
            plugins_path (str): Le chemin vers le répertoire contenant les plugins.
        """
        self.plugins_path = Path(plugins_path)
        self.loaded_plugins: Dict[str, Type[BasePlugin]] = {}

    def discover_and_load(self) -> None:
        """
        Découvre et charge tous les plugins valides depuis le `plugins_path`.

        Parcourt le répertoire, importe les modules, inspecte leur contenu pour trouver
        des classes qui héritent de `BasePlugin`, et les stocke pour une
        utilisation ultérieure.
        """
        if not self.plugins_path.is_dir():
            print(f"Error: Plugin path {self.plugins_path} is not a valid directory.")
            return

        for root, _, files in os.walk(self.plugins_path):
            for filename in files:
                if filename.endswith(".py") and not filename.startswith("__"):
                    module_path = Path(root) / filename
                    # Convert file path to module path (e.g., src/plugins/standard -> src.plugins.standard)
                    relative_path = module_path.relative_to(Path.cwd())
                    module_name = str(relative_path.with_suffix('')).replace(os.sep, '.')
                    
                    try:
                        module = importlib.import_module(module_name)
                        for _, obj in inspect.getmembers(module, inspect.isclass):
                            if (
                                issubclass(obj, BasePlugin)
                                and obj is not BasePlugin
                                and obj not in self.loaded_plugins.values()
                            ):
                                # We store the class, not the instance
                                self.loaded_plugins[obj.name] = obj
                                print(f"Discovered and loaded plugin: {obj.name}")
                    except (ImportError, AttributeError, NotImplementedError) as e:
                        print(f"Could not load plugin from {module_name}: {e}")

    def get_plugin(self, name: str) -> Type[BasePlugin] | None:
        """
        Récupère une classe de plugin chargée par son nom.

        Args:
            name (str): Le nom du plugin à récupérer.

        Returns:
            Type[BasePlugin] | None: La classe du plugin si elle est trouvée, sinon None.
        """
        return self.loaded_plugins.get(name)

    def get_all_plugins(self) -> List[Type[BasePlugin]]:
        """
        Retourne la liste de toutes les classes de plugins chargées.

        Returns:
            List[Type[BasePlugin]]: Une liste des classes de plugins.
        """
        return list(self.loaded_plugins.values())
