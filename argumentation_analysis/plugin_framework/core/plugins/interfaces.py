from abc import ABC


class BasePlugin(ABC):
    """
    Classe de base abstraite et marqueur pour tous les plugins.

    Un plugin est une classe qui hérite de BasePlugin et qui rejoint le
    système par **import direct** : les mécanismes de découverte, sans
    appelant de production, ont été retirés (#2099) — aucun chargeur ne
    découvre ni n'instancie ces classes automatiquement. Les capacités d'un
    plugin sont simplement ses méthodes publiques.
    """

    pass
