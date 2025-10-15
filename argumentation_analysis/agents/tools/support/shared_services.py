import logging
from typing import Callable, Any


def get_configured_logger(name: str) -> logging.Logger:
    """Retourne un logger configuré de manière centralisée."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger(name)


class ServiceRegistry:
    _services = {}

    @classmethod
    def get(cls, service_class: Any) -> Any:
        """Récupère ou crée une instance unique d'un service."""
        if service_class not in cls._services:
            cls._services[service_class] = service_class()
        return cls._services[service_class]


class ConfigManager:
    _configs = {}

    @classmethod
    def load_config(
        cls,
        config_name: str,
        loader_func: Callable[[], Any],
        force_reload: bool = False,
    ) -> Any:
        """Charge une configuration si elle n'est pas déjà en cache."""
        if config_name not in cls._configs or force_reload:
            cls._configs[config_name] = loader_func()
        return cls._configs[config_name]
