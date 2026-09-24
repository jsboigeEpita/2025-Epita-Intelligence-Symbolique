import logging
from typing import Callable, Any


def get_configured_logger(name: str) -> logging.Logger:
    """Retourne le logger ``name``, sans toucher au logger racine.

    Il appelait ``logging.basicConfig`` : construire un analyseur (l'API web
    et la fabrique d'agents le font) configurait le logger racine du processus
    à la place de son point d'entrée (#2346).
    """
    return logging.getLogger(name)


class ServiceRegistry:
    """Une instance par classe de service, pour tout le processus."""

    _services = {}

    @classmethod
    def get(cls, service_class: Any) -> Any:
        """Récupère ou crée une instance unique d'un service."""
        if service_class not in cls._services:
            cls._services[service_class] = service_class()
        return cls._services[service_class]

    @classmethod
    def reset(cls) -> None:
        """Oublie toutes les instances (les tests l'appellent après chaque cas)."""
        cls._services.clear()


class ConfigManager:
    """Une configuration chargée par nom, pour tout le processus."""

    _configs = {}

    @classmethod
    def load_config(
        cls,
        config_name: str,
        loader_func: Callable[[], Any],
        force_reload: bool = False,
    ) -> Any:
        """Charge une configuration si elle n'est pas déjà en cache.

        Un chargeur qui rend ``None`` n'a rien chargé : ce résultat n'est pas
        gardé, et l'appel suivant réessaie. Gardé, un échec au premier appel
        (taxonomie absente un instant) restait l'état du processus jusqu'à son
        redémarrage (#2346).
        """
        if config_name in cls._configs and not force_reload:
            return cls._configs[config_name]
        config = loader_func()
        if config is None:
            cls._configs.pop(config_name, None)
        else:
            cls._configs[config_name] = config
        return config

    @classmethod
    def reset(cls) -> None:
        """Oublie toutes les configurations (les tests l'appellent après chaque cas)."""
        cls._configs.clear()
