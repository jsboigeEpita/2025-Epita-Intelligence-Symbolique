from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


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


@dataclass
class ParameterSpec:
    """Specification for a plugin parameter."""

    name: str
    type: str = "string"  # string, int, float, bool, list, dict
    required: bool = False
    default: Any = None
    description: str = ""


class LegoPlugin(BasePlugin):
    """
    Extended plugin interface for the Lego architecture.

    LegoPlugin adds capability declarations (provides/requires) and
    typed parameters to the base plugin interface. This allows the
    CapabilityRegistry to discover and compose plugins dynamically.

    Subclasses should override the class-level `provides`, `requires`,
    and `parameters` attributes, plus implement `name` and `execute`.

    Example:
        class MyFallacyPlugin(LegoPlugin):
            provides = ["fallacy_detection", "taxonomy_display"]
            requires = ["llm_service"]
            parameters = [
                ParameterSpec("language", type="string", default="fr"),
                ParameterSpec("threshold", type="float", default=0.5),
            ]

            @property
            def name(self) -> str:
                return "my_fallacy_plugin"

            def execute(self, **kwargs) -> dict:
                ...
    """

    provides: List[str] = []
    requires: List[str] = []
    parameters: List[ParameterSpec] = []

    def get_capabilities(self) -> Dict[str, Any]:
        """Return a structured description of this plugin's capabilities."""
        return {
            "name": self.name,
            "provides": list(self.provides),
            "requires": list(self.requires),
            "parameters": {
                p.name: {
                    "type": p.type,
                    "required": p.required,
                    "default": p.default,
                    "description": p.description,
                }
                for p in self.parameters
            },
        }

    def check_requirements(self, available_services: List[str]) -> List[str]:
        """
        Check which requirements are not met.

        Args:
            available_services: List of available service/capability names.

        Returns:
            List of missing requirements (empty if all met).
        """
        return [r for r in self.requires if r not in available_services]

    def is_available(self, available_services: Optional[List[str]] = None) -> bool:
        """
        Check if this plugin can run given available services.

        Args:
            available_services: List of available services. If None,
                assumes all requirements are met.

        Returns:
            True if all requirements are satisfied.
        """
        if available_services is None:
            return True
        return len(self.check_requirements(available_services)) == 0
