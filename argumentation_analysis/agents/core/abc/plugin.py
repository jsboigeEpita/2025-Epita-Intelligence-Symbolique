from abc import ABC, abstractmethod


class BasePlugin(ABC):
    """Abstract base class for all plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the plugin."""
        raise NotImplementedError()

    @abstractmethod
    def execute(self, **kwargs) -> dict:
        """The main execution method of the plugin."""
        raise NotImplementedError()
