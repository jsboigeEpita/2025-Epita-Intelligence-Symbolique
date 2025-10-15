"""
Service d'Orchestration Central

Ce service est la pierre angulaire de l'architecture "Guichet de Service".
Il est responsable de :
- Centraliser les points d'entrée pour les opérations d'analyse.
- Gérer le cycle de vie et l'accès aux plugins.
- Orchestrer les workflows complexes en invoquant les plugins adéquats.

Ce service est implémenté en tant que Singleton pour garantir une instance unique
à travers toute l'application, en cohérence avec le ServiceRegistry.
"""

import threading
from typing import Dict, Optional, List


# Pour l'instant, nous définissons une classe de base pour les plugins.
# Cela sera probablement remplacé par une interface plus formelle.
class BasePlugin:
    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def dependencies(self) -> List[str]:
        """Retourne la liste des noms des plugins requis."""
        return []

    def execute(self, **kwargs) -> dict:
        """Exécute la logique du plugin."""
        raise NotImplementedError


class PluginDependencyError(Exception):
    """Exception levée lorsque les dépendances d'un plugin ne sont pas satisfaites."""

    pass


class OrchestrationService:
    """
    Le Guichet de Service Unique pour orchestrer les capacités d'analyse.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.initialized = True
            self._plugins: Dict[str, BasePlugin] = {}
            # Dans le futur, nous utiliserons le ServiceRegistry pour obtenir
            # des services comme le PluginLoader.
            # from argumentation_analysis.agents.tools.support.shared_services import ServiceRegistry
            # self.service_registry = ServiceRegistry.get_instance()

    @classmethod
    def get_instance(cls):
        """
        Méthode de classe pour accéder à l'instance unique du Singleton.
        """
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = cls()
        return cls._instance

    def register_plugin(self, plugin: BasePlugin):
        """
        Enregistre une instance de plugin dans le service.

        Args:
            plugin: L'instance du plugin à enregistrer.

        Raises:
            ValueError: Si le plugin est invalide, sans nom, ou si un plugin
                avec le même nom est déjà enregistré.
            TypeError: Si l'objet fourni n'est pas une instance de BasePlugin.
        """
        if not isinstance(plugin, BasePlugin):
            raise TypeError("Le plugin doit être une instance de BasePlugin.")

        try:
            if not plugin.name:
                raise ValueError("Plugin invalide ou sans nom.")
        except AttributeError:
            # Ce cas est un peu redondant avec le isinstance, mais conservé pour la robustesse.
            raise ValueError("Plugin invalide ou sans nom.")

        if plugin.name in self._plugins:
            raise ValueError(
                f"A plugin with the name '{plugin.name}' is already registered."
            )
        self._plugins[plugin.name] = plugin

    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """
        Récupère un plugin enregistré par son nom.

        Args:
            plugin_name: Le nom du plugin à récupérer.

        Returns:
            L'instance du plugin si elle est trouvée, sinon None.
        """
        if not isinstance(plugin_name, str):
            raise TypeError("Le nom du plugin doit être une chaîne de caractères.")
        return self._plugins.get(plugin_name)

    def _resolve_dependencies(self, plugin: BasePlugin) -> List[BasePlugin]:
        """
        Résout et récupère les instances des plugins dépendants.

        Args:
            plugin: Le plugin pour lequel résoudre les dépendances.

        Returns:
            Une liste des instances de plugins dépendants.

        Raises:
            PluginDependencyError: Si une dépendance n'est pas trouvée.
        """
        resolved_dependencies = []
        for dep_name in plugin.dependencies:
            dependency_plugin = self.get_plugin(dep_name)
            if not dependency_plugin:
                raise PluginDependencyError(
                    f"Dépendance non satisfaite : le plugin '{dep_name}' "
                    f"requis par '{plugin.name}' est introuvable."
                )
            resolved_dependencies.append(dependency_plugin)
        return resolved_dependencies

    def execute_plugin(self, plugin_name: str, **kwargs) -> dict:
        """
        Exécute un plugin et ses dépendances.

        Args:
            plugin_name: Le nom du plugin à exécuter.
            **kwargs: Arguments à passer à la méthode execute du plugin.

        Returns:
            Le résultat de l'exécution du plugin.

        Raises:
            ValueError: Si le plugin demandé n'est pas trouvé.
            PluginDependencyError: Si une dépendance n'est pas satisfaite.
        """
        if not isinstance(plugin_name, str):
            raise TypeError("Le nom du plugin doit être une chaîne de caractères.")

        plugin = self.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"Plugin '{plugin_name}' non trouvé.")

        resolved_dependencies = self._resolve_dependencies(plugin)

        # Injecte les dépendances dans les arguments d'exécution
        kwargs["dependencies"] = resolved_dependencies

        return plugin.execute(**kwargs)
