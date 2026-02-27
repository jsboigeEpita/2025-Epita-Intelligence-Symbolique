"""
Registre unifie de capabilities pour l'architecture Lego.

Ce module fournit un registre central permettant d'enregistrer et de decouvrir
des agents, plugins et services par leurs capabilities. Il unifie les mecanismes
existants (OperationalAgentRegistry, AgentFactory) en un seul point d'entree
pour la composition dynamique de workflows agentiques.

Usage:
    registry = CapabilityRegistry()
    registry.register_agent("informal_fallacy", InformalFallacyAgent,
        capabilities=["fallacy_detection", "taxonomy_display"],
        requires=["llm_service"])
    agents = registry.find_agents_for_capability("fallacy_detection")
"""

import logging
from typing import (
    Dict,
    List,
    Any,
    Optional,
    Type,
    Set,
    Callable,
    Union,
)
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("CapabilityRegistry")


class ComponentType(Enum):
    """Type de composant enregistre dans le registre."""

    AGENT = "agent"
    PLUGIN = "plugin"
    SERVICE = "service"


@dataclass
class ComponentRegistration:
    """Enregistrement d'un composant dans le registre."""

    name: str
    component_type: ComponentType
    component_class: Optional[Type] = None
    factory: Optional[Callable] = None
    capabilities: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def provides(self) -> List[str]:
        """Alias pour capabilities (compatibilite LegoPlugin)."""
        return self.capabilities


@dataclass
class SlotDeclaration:
    """Declaration d'un slot de capability non-implemente."""

    name: str
    requires: List[str] = field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class CapabilityRegistry:
    """
    Registre unifie de capabilities pour l'architecture Lego.

    Permet d'enregistrer des agents, plugins et services avec leurs capabilities,
    puis de les decouvrir dynamiquement par capability requise.
    """

    def __init__(self):
        self._registrations: Dict[str, ComponentRegistration] = {}
        self._capability_index: Dict[str, Set[str]] = (
            {}
        )  # capability -> set of component names
        self._slots: Dict[str, SlotDeclaration] = {}
        self._service_discovery: Optional["ServiceDiscovery"] = None
        logger.info("CapabilityRegistry initialized")

    # --- Registration API ---

    def register(
        self,
        name: str,
        component_type: ComponentType,
        component_class: Optional[Type] = None,
        factory: Optional[Callable] = None,
        capabilities: Optional[List[str]] = None,
        requires: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ComponentRegistration":
        """
        Enregistre un composant dans le registre.

        Args:
            name: Nom unique du composant
            component_type: Type (AGENT, PLUGIN, SERVICE)
            component_class: Classe du composant (optionnel si factory fournie)
            factory: Fonction factory pour creer le composant
            capabilities: Liste des capabilities fournies
            requires: Liste des dependances requises
            parameters: Parametres configurables
            metadata: Metadonnees additionnelles

        Returns:
            L'enregistrement cree

        Raises:
            ValueError: Si le nom est deja enregistre
        """
        if name in self._registrations:
            raise ValueError(
                f"Component '{name}' is already registered. "
                f"Use update() to modify or unregister() first."
            )

        registration = ComponentRegistration(
            name=name,
            component_type=component_type,
            component_class=component_class,
            factory=factory,
            capabilities=capabilities or [],
            requires=requires or [],
            parameters=parameters or {},
            metadata=metadata or {},
        )

        self._registrations[name] = registration

        # Index capabilities for fast lookup
        for cap in registration.capabilities:
            if cap not in self._capability_index:
                self._capability_index[cap] = set()
            self._capability_index[cap].add(name)

        # Remove from slots if this fills a declared slot
        for cap in registration.capabilities:
            if cap in self._slots:
                logger.info(f"Slot '{cap}' filled by component '{name}'")
                del self._slots[cap]

        logger.info(
            f"Registered {component_type.value} '{name}' "
            f"with capabilities: {registration.capabilities}"
        )
        return registration

    def register_agent(
        self,
        name: str,
        agent_class: Type,
        capabilities: Optional[List[str]] = None,
        requires: Optional[List[str]] = None,
        **kwargs,
    ) -> "ComponentRegistration":
        """Shorthand for registering an agent."""
        return self.register(
            name=name,
            component_type=ComponentType.AGENT,
            component_class=agent_class,
            capabilities=capabilities,
            requires=requires,
            **kwargs,
        )

    def register_plugin(
        self,
        name: str,
        plugin_class: Type,
        capabilities: Optional[List[str]] = None,
        requires: Optional[List[str]] = None,
        **kwargs,
    ) -> "ComponentRegistration":
        """Shorthand for registering a plugin."""
        return self.register(
            name=name,
            component_type=ComponentType.PLUGIN,
            component_class=plugin_class,
            capabilities=capabilities,
            requires=requires,
            **kwargs,
        )

    def register_service(
        self,
        name: str,
        service_class: Optional[Type] = None,
        factory: Optional[Callable] = None,
        capabilities: Optional[List[str]] = None,
        requires: Optional[List[str]] = None,
        **kwargs,
    ) -> "ComponentRegistration":
        """Shorthand for registering a service."""
        return self.register(
            name=name,
            component_type=ComponentType.SERVICE,
            component_class=service_class,
            factory=factory,
            capabilities=capabilities,
            requires=requires,
            **kwargs,
        )

    def unregister(self, name: str) -> bool:
        """
        Remove a component from the registry.

        Returns:
            True if removed, False if not found.
        """
        if name not in self._registrations:
            return False

        registration = self._registrations[name]

        # Remove from capability index
        for cap in registration.capabilities:
            if cap in self._capability_index:
                self._capability_index[cap].discard(name)
                if not self._capability_index[cap]:
                    del self._capability_index[cap]

        del self._registrations[name]
        logger.info(f"Unregistered component '{name}'")
        return True

    # --- Slot API (for declaring unfilled capabilities) ---

    def declare_slot(
        self,
        name: str,
        requires: Optional[List[str]] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SlotDeclaration:
        """
        Declare a capability slot that is not yet filled by any component.

        Slots represent extension points — capabilities that the system
        knows about but has no implementation for yet.
        """
        if name in self._capability_index:
            logger.info(
                f"Slot '{name}' already has implementations, skipping declaration"
            )
            return SlotDeclaration(name=name)

        slot = SlotDeclaration(
            name=name,
            requires=requires or [],
            description=description,
            metadata=metadata or {},
        )
        self._slots[name] = slot
        logger.debug(f"Declared slot '{name}'")
        return slot

    # --- Discovery API ---

    def find_agents_for_capability(
        self, capability: str
    ) -> List[ComponentRegistration]:
        """Find all agents that provide a given capability."""
        return self._find_by_capability(capability, ComponentType.AGENT)

    def find_plugins_for_capability(
        self, capability: str
    ) -> List[ComponentRegistration]:
        """Find all plugins that provide a given capability."""
        return self._find_by_capability(capability, ComponentType.PLUGIN)

    def find_services_for_capability(
        self, capability: str
    ) -> List[ComponentRegistration]:
        """Find all services that provide a given capability."""
        return self._find_by_capability(capability, ComponentType.SERVICE)

    def find_for_capability(self, capability: str) -> List[ComponentRegistration]:
        """Find all components (any type) that provide a given capability."""
        component_names = self._capability_index.get(capability, set())
        return [self._registrations[n] for n in component_names]

    def _find_by_capability(
        self, capability: str, component_type: ComponentType
    ) -> List[ComponentRegistration]:
        """Internal: find components of a specific type for a capability."""
        component_names = self._capability_index.get(capability, set())
        return [
            self._registrations[n]
            for n in component_names
            if self._registrations[n].component_type == component_type
        ]

    def get_registration(self, name: str) -> Optional[ComponentRegistration]:
        """Get a specific registration by name."""
        return self._registrations.get(name)

    def get_all_capabilities(self) -> Dict[str, List[str]]:
        """
        Get a map of all capabilities and their providers.

        Returns:
            Dict mapping capability name to list of component names.
        """
        return {cap: sorted(names) for cap, names in self._capability_index.items()}

    def get_all_slots(self) -> Dict[str, SlotDeclaration]:
        """Get all unfilled capability slots."""
        return dict(self._slots)

    def get_all_registrations(
        self, component_type: Optional[ComponentType] = None
    ) -> List[ComponentRegistration]:
        """
        Get all registrations, optionally filtered by type.

        Args:
            component_type: If provided, filter by this type.

        Returns:
            List of matching registrations.
        """
        if component_type is None:
            return list(self._registrations.values())
        return [
            r
            for r in self._registrations.values()
            if r.component_type == component_type
        ]

    # --- Dependency checking ---

    def check_requirements(self, name: str) -> Dict[str, bool]:
        """
        Check if a component's requirements are satisfiable.

        Returns:
            Dict mapping requirement name to whether it's available.
        """
        registration = self._registrations.get(name)
        if not registration:
            return {}

        result = {}
        for req in registration.requires:
            # Check if any component provides this capability
            available = (
                req in self._capability_index and len(self._capability_index[req]) > 0
            )
            # Also check service discovery
            if not available and self._service_discovery:
                available = self._service_discovery.has_provider(req)
            result[req] = available
        return result

    def can_satisfy(self, name: str) -> bool:
        """Check if all requirements of a component are satisfiable."""
        requirements = self.check_requirements(name)
        return all(requirements.values()) if requirements else True

    # --- Service Discovery integration ---

    def set_service_discovery(self, service_discovery: "ServiceDiscovery") -> None:
        """Attach a ServiceDiscovery instance to the registry."""
        self._service_discovery = service_discovery

    def get_service_discovery(self) -> Optional["ServiceDiscovery"]:
        """Get the attached ServiceDiscovery instance."""
        return self._service_discovery

    # --- Introspection ---

    def summary(self) -> Dict[str, Any]:
        """
        Get a summary of the registry state.

        Returns:
            Dict with counts of agents, plugins, services, capabilities, slots.
        """
        agents = [
            r
            for r in self._registrations.values()
            if r.component_type == ComponentType.AGENT
        ]
        plugins = [
            r
            for r in self._registrations.values()
            if r.component_type == ComponentType.PLUGIN
        ]
        services = [
            r
            for r in self._registrations.values()
            if r.component_type == ComponentType.SERVICE
        ]
        return {
            "agents": len(agents),
            "plugins": len(plugins),
            "services": len(services),
            "capabilities": len(self._capability_index),
            "slots_unfilled": len(self._slots),
            "total_registrations": len(self._registrations),
        }

    def __repr__(self) -> str:
        s = self.summary()
        return (
            f"CapabilityRegistry("
            f"{s['agents']} agents, "
            f"{s['plugins']} plugins, "
            f"{s['services']} services, "
            f"{s['capabilities']} capabilities, "
            f"{s['slots_unfilled']} unfilled slots)"
        )


class ServiceDiscovery:
    """
    Registre de services disponibles (LLM, solvers, embeddings, STT, etc.).

    Les services sont des dependances d'infrastructure que les agents/plugins
    peuvent requerir. ServiceDiscovery les rend interrogeables a runtime.
    """

    @dataclass
    class ProviderRegistration:
        """Enregistrement d'un fournisseur de service."""

        name: str
        provider_type: str  # "llm", "embedding", "stt", "solver", ...
        endpoint: Optional[str] = None
        api_key: Optional[str] = None
        models: List[str] = field(default_factory=list)
        capabilities: List[str] = field(default_factory=list)
        metadata: Dict[str, Any] = field(default_factory=dict)
        priority: int = 0  # Higher = preferred

    def __init__(self):
        self._providers: Dict[str, "ServiceDiscovery.ProviderRegistration"] = {}
        self._type_index: Dict[str, Set[str]] = {}  # type -> set of provider names
        logger.info("ServiceDiscovery initialized")

    def register_provider(
        self,
        name: str,
        provider_type: str,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        models: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ServiceDiscovery.ProviderRegistration":
        """Register a service provider."""
        registration = self.ProviderRegistration(
            name=name,
            provider_type=provider_type,
            endpoint=endpoint,
            api_key=api_key,
            models=models or [],
            capabilities=capabilities or [],
            metadata=metadata or {},
            priority=priority,
        )
        self._providers[name] = registration

        if provider_type not in self._type_index:
            self._type_index[provider_type] = set()
        self._type_index[provider_type].add(name)

        logger.info(
            f"Registered {provider_type} provider '{name}' "
            f"(endpoint: {endpoint}, priority: {priority})"
        )
        return registration

    def register_llm_provider(
        self,
        name: str,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        models: Optional[List[str]] = None,
        priority: int = 0,
        **kwargs,
    ) -> "ServiceDiscovery.ProviderRegistration":
        """Register an LLM provider."""
        return self.register_provider(
            name=name,
            provider_type="llm",
            endpoint=endpoint,
            api_key=api_key,
            models=models,
            capabilities=["chat_completion"],
            priority=priority,
            **kwargs,
        )

    def register_embedding_provider(
        self,
        name: str,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        priority: int = 0,
        **kwargs,
    ) -> "ServiceDiscovery.ProviderRegistration":
        """Register an embedding provider."""
        return self.register_provider(
            name=name,
            provider_type="embedding",
            endpoint=endpoint,
            models=[model] if model else [],
            capabilities=["embedding"],
            priority=priority,
            metadata={"dimensions": dimensions, **(kwargs.get("metadata", {}))},
            **{k: v for k, v in kwargs.items() if k != "metadata"},
        )

    def register_stt_provider(
        self,
        name: str,
        endpoint: Optional[str] = None,
        priority: int = 0,
        **kwargs,
    ) -> "ServiceDiscovery.ProviderRegistration":
        """Register a speech-to-text provider."""
        return self.register_provider(
            name=name,
            provider_type="stt",
            endpoint=endpoint,
            capabilities=["speech_to_text"],
            priority=priority,
            **kwargs,
        )

    def get_provider(
        self, name: str
    ) -> Optional["ServiceDiscovery.ProviderRegistration"]:
        """Get a specific provider by name."""
        return self._providers.get(name)

    def get_providers_by_type(
        self, provider_type: str
    ) -> List["ServiceDiscovery.ProviderRegistration"]:
        """Get all providers of a given type, sorted by priority (highest first)."""
        names = self._type_index.get(provider_type, set())
        providers = [self._providers[n] for n in names]
        return sorted(providers, key=lambda p: p.priority, reverse=True)

    def get_best_provider(
        self, provider_type: str
    ) -> Optional["ServiceDiscovery.ProviderRegistration"]:
        """Get the highest-priority provider of a given type."""
        providers = self.get_providers_by_type(provider_type)
        return providers[0] if providers else None

    def has_provider(self, provider_type: str) -> bool:
        """Check if at least one provider exists for a type."""
        return bool(self._type_index.get(provider_type))

    def get_all_provider_types(self) -> List[str]:
        """Get list of all registered provider types."""
        return sorted(self._type_index.keys())

    def summary(self) -> Dict[str, int]:
        """Get count of providers by type."""
        return {ptype: len(names) for ptype, names in self._type_index.items()}

    def __repr__(self) -> str:
        s = self.summary()
        parts = [f"{count} {ptype}" for ptype, count in s.items()]
        return f"ServiceDiscovery({', '.join(parts) or 'empty'})"
