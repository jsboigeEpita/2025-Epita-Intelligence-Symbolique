from abc import ABC


class BasePlugin(ABC):
    """
    Classe de base abstraite et marqueur pour tous les plugins.

    Un plugin est une classe qui hérite de BasePlugin. Le PluginLoader
    découvre et instancie automatiquement ces classes. Les capacités d'un
    plugin sont simplement ses méthodes publiques.
    """

    pass
