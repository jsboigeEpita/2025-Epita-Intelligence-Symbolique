# -*- coding: utf-8 -*-
"""
Mécanisme de découverte et de chargement dynamique des personnalités d'agents.
"""

import importlib
import inspect
import os
import json
from pathlib import Path
from typing import Dict, List, Type

from src.agents.interfaces import IAgentPersonality


class AgentLoader:
    """
    Charge et gère les personnalités des agents.

    Cette classe scanne un répertoire à la recherche de personnalités d'agents,
    qui sont définies par un `config.json`, un `system.md` et une classe
    héritant de `IAgentPersonality`.
    """

    def __init__(self, personalities_path: str):
        """
        Initialise le chargeur d'agents.

        Args:
            personalities_path (str): Chemin vers le répertoire des personnalités.
        """
        self.personalities_path = Path(personalities_path)
        self.loaded_personalities: Dict[str, Type[IAgentPersonality]] = {}

    def discover_and_load(self) -> None:
        """
        Découvre, charge et valide les personnalités d'agents.
        """
        if not self.personalities_path.is_dir():
            print(f"Error: Personalities path {self.personalities_path} is not a valid directory.")
            return

        for root, _, files in os.walk(self.personalities_path):
            if "config.json" in files and "system.md" in files:
                module_path_found = False
                for filename in files:
                    if filename.endswith(".py") and not filename.startswith("__"):
                        module_path_found = True
                        module_path = Path(root) / filename
                        relative_path = module_path.relative_to(Path.cwd())
                        module_name = str(relative_path.with_suffix('')).replace(os.sep, '.')
                        
                        try:
                            module = importlib.import_module(module_name)
                            for _, obj in inspect.getmembers(module, inspect.isclass):
                                if (
                                    issubclass(obj, IAgentPersonality)
                                    and obj is not IAgentPersonality
                                    and obj not in self.loaded_personalities.values()
                                ):
                                    # Valider la présence de tous les fichiers requis
                                    config_path = Path(root) / "config.json"
                                    prompt_path = Path(root) / "system.md"
                                    
                                    if config_path.exists() and prompt_path.exists():
                                        
                                        # Instancier pour charger la config et le prompt
                                        instance = obj()
                                        
                                        with open(config_path, 'r', encoding='utf-8') as f:
                                            config_data = json.load(f)
                                        instance.load_configuration(config_data)

                                        # Le prompt est souvent géré au moment de l'exécution
                                        # mais on valide sa présence.
                                        
                                        self.loaded_personalities[instance.name] = obj
                                        print(f"Discovered and loaded agent personality: {instance.name}")

                        except (ImportError, AttributeError, NotImplementedError, TypeError) as e:
                            print(f"Could not load agent from {module_name}: {e}")
                
                if not module_path_found:
                    print(f"Warning: Found config and system prompt in {root}, but no Python module for personality.")


    def get_personality(self, name: str) -> Type[IAgentPersonality] | None:
        """
        Récupère une classe de personnalité par son nom.
        """
        return self.loaded_personalities.get(name)

    def get_all_personalities(self) -> List[Type[IAgentPersonality]]:
        """
        Retourne toutes les classes de personnalités chargées.
        """
        return list(self.loaded_personalities.values())
