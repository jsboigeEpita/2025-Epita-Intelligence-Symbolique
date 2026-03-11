"""
Tests for the CapabilityRegistry and ServiceDiscovery.

These tests validate the Lego architecture foundation:
- Component registration (agents, plugins, services)
- Capability-based discovery
- Slot declarations for unfilled capabilities
- ServiceDiscovery for LLM/embedding/STT providers
- Dependency checking
"""

import pytest
from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentType,
    ComponentRegistration,
    ServiceDiscovery,
)


class TestCapabilityRegistry:
    """Tests for the CapabilityRegistry."""

    def setup_method(self):
        self.registry = CapabilityRegistry()

    def test_register_agent(self):
        """Test basic agent registration."""
        reg = self.registry.register_agent(
            name="informal_fallacy",
            agent_class=type("FakeAgent", (), {}),
            capabilities=["fallacy_detection", "taxonomy_display"],
            requires=["llm_service"],
        )
        assert reg.name == "informal_fallacy"
        assert reg.component_type == ComponentType.AGENT
        assert "fallacy_detection" in reg.capabilities
        assert "llm_service" in reg.requires

    def test_register_plugin(self):
        """Test basic plugin registration."""
        reg = self.registry.register_plugin(
            name="quality_plugin",
            plugin_class=type("FakePlugin", (), {}),
            capabilities=["argument_quality"],
        )
        assert reg.component_type == ComponentType.PLUGIN

    def test_register_service(self):
        """Test basic service registration."""
        reg = self.registry.register_service(
            name="jtms_service",
            service_class=type("FakeService", (), {}),
            capabilities=["belief_maintenance"],
        )
        assert reg.component_type == ComponentType.SERVICE

    def test_duplicate_registration_raises(self):
        """Test that duplicate registration raises ValueError."""
        self.registry.register_agent(
            name="test_agent",
            agent_class=type("A", (), {}),
            capabilities=["cap_a"],
        )
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register_agent(
                name="test_agent",
                agent_class=type("B", (), {}),
                capabilities=["cap_b"],
            )

    def test_find_agents_for_capability(self):
        """Test finding agents by capability."""
        self.registry.register_agent(
            "agent_a", type("A", (), {}), capabilities=["cap_x", "cap_y"]
        )
        self.registry.register_agent(
            "agent_b", type("B", (), {}), capabilities=["cap_x"]
        )
        self.registry.register_agent(
            "agent_c", type("C", (), {}), capabilities=["cap_z"]
        )

        results = self.registry.find_agents_for_capability("cap_x")
        assert len(results) == 2
        names = {r.name for r in results}
        assert names == {"agent_a", "agent_b"}

    def test_find_for_capability_mixed_types(self):
        """Test finding across different component types."""
        self.registry.register_agent(
            "agent_a", type("A", (), {}), capabilities=["fallacy_detection"]
        )
        self.registry.register_plugin(
            "plugin_b", type("B", (), {}), capabilities=["fallacy_detection"]
        )

        all_results = self.registry.find_for_capability("fallacy_detection")
        assert len(all_results) == 2

        agent_results = self.registry.find_agents_for_capability("fallacy_detection")
        assert len(agent_results) == 1

        plugin_results = self.registry.find_plugins_for_capability("fallacy_detection")
        assert len(plugin_results) == 1

    def test_unregister(self):
        """Test component unregistration."""
        self.registry.register_agent(
            "to_remove", type("X", (), {}), capabilities=["cap_a"]
        )
        assert self.registry.get_registration("to_remove") is not None

        result = self.registry.unregister("to_remove")
        assert result is True
        assert self.registry.get_registration("to_remove") is None
        assert len(self.registry.find_for_capability("cap_a")) == 0

    def test_unregister_nonexistent(self):
        """Test unregistering a non-existent component."""
        assert self.registry.unregister("ghost") is False

    def test_get_all_capabilities(self):
        """Test getting all capabilities map."""
        self.registry.register_agent(
            "a1", type("A", (), {}), capabilities=["cap_x", "cap_y"]
        )
        self.registry.register_agent("a2", type("B", (), {}), capabilities=["cap_x"])

        caps = self.registry.get_all_capabilities()
        assert "cap_x" in caps
        assert len(caps["cap_x"]) == 2
        assert "cap_y" in caps
        assert len(caps["cap_y"]) == 1

    def test_declare_slot(self):
        """Test slot declaration for unfilled capabilities."""
        slot = self.registry.declare_slot(
            "aspic_plus_reasoning",
            requires=["jvm"],
            description="ASPIC+ argumentation framework",
        )
        assert slot.name == "aspic_plus_reasoning"
        assert "jvm" in slot.requires

        slots = self.registry.get_all_slots()
        assert "aspic_plus_reasoning" in slots

    def test_slot_filled_by_registration(self):
        """Test that registering a component fills the corresponding slot."""
        self.registry.declare_slot("formal_reasoning")
        assert "formal_reasoning" in self.registry.get_all_slots()

        self.registry.register_agent(
            "fol_agent", type("FOL", (), {}), capabilities=["formal_reasoning"]
        )
        # Slot should be removed
        assert "formal_reasoning" not in self.registry.get_all_slots()

    def test_check_requirements_satisfied(self):
        """Test requirement checking when all requirements are met."""
        self.registry.register_service(
            "llm", type("LLM", (), {}), capabilities=["llm_service"]
        )
        self.registry.register_agent(
            "agent_a",
            type("A", (), {}),
            capabilities=["fallacy_detection"],
            requires=["llm_service"],
        )

        reqs = self.registry.check_requirements("agent_a")
        assert reqs == {"llm_service": True}
        assert self.registry.can_satisfy("agent_a") is True

    def test_check_requirements_unsatisfied(self):
        """Test requirement checking when requirements are missing."""
        self.registry.register_agent(
            "agent_a",
            type("A", (), {}),
            capabilities=["dung_semantics"],
            requires=["jvm"],
        )

        reqs = self.registry.check_requirements("agent_a")
        assert reqs == {"jvm": False}
        assert self.registry.can_satisfy("agent_a") is False

    def test_summary(self):
        """Test registry summary."""
        self.registry.register_agent("a1", type("A", (), {}), capabilities=["cap_a"])
        self.registry.register_plugin("p1", type("P", (), {}), capabilities=["cap_b"])
        self.registry.register_service("s1", type("S", (), {}), capabilities=["cap_c"])
        self.registry.declare_slot("unfilled_cap")

        summary = self.registry.summary()
        assert summary["agents"] == 1
        assert summary["plugins"] == 1
        assert summary["services"] == 1
        assert summary["capabilities"] == 3
        assert summary["slots_unfilled"] == 1

    def test_repr(self):
        """Test string representation."""
        self.registry.register_agent("a1", type("A", (), {}), capabilities=["cap_a"])
        repr_str = repr(self.registry)
        assert "CapabilityRegistry" in repr_str
        assert "1 agents" in repr_str

    def test_provides_alias(self):
        """Test that ComponentRegistration.provides is an alias for capabilities."""
        reg = self.registry.register_agent(
            "a1", type("A", (), {}), capabilities=["cap_a", "cap_b"]
        )
        assert reg.provides == reg.capabilities


class TestServiceDiscovery:
    """Tests for the ServiceDiscovery."""

    def setup_method(self):
        self.sd = ServiceDiscovery()

    def test_register_llm_provider(self):
        """Test LLM provider registration."""
        reg = self.sd.register_llm_provider(
            name="local_qwen",
            endpoint="http://localhost:5003",
            models=["qwen-3.5-35b"],
            priority=10,
        )
        assert reg.name == "local_qwen"
        assert reg.provider_type == "llm"
        assert "qwen-3.5-35b" in reg.models
        assert reg.priority == 10

    def test_register_embedding_provider(self):
        """Test embedding provider registration."""
        reg = self.sd.register_embedding_provider(
            name="local_embed",
            endpoint="https://embeddings.myia.io",
            model="qwen3-4b-awq",
            dimensions=1536,
        )
        assert reg.provider_type == "embedding"
        assert reg.metadata["dimensions"] == 1536

    def test_register_stt_provider(self):
        """Test STT provider registration."""
        reg = self.sd.register_stt_provider(
            name="whisper",
            endpoint="https://whisper-webui.myia.io",
        )
        assert reg.provider_type == "stt"

    def test_get_best_provider(self):
        """Test getting the highest-priority provider."""
        self.sd.register_llm_provider("openai", priority=5)
        self.sd.register_llm_provider("local_qwen", priority=10)
        self.sd.register_llm_provider("openrouter", priority=7)

        best = self.sd.get_best_provider("llm")
        assert best is not None
        assert best.name == "local_qwen"

    def test_get_providers_by_type(self):
        """Test getting providers sorted by priority."""
        self.sd.register_llm_provider("low", priority=1)
        self.sd.register_llm_provider("high", priority=10)
        self.sd.register_llm_provider("mid", priority=5)

        providers = self.sd.get_providers_by_type("llm")
        assert len(providers) == 3
        assert providers[0].name == "high"
        assert providers[1].name == "mid"
        assert providers[2].name == "low"

    def test_has_provider(self):
        """Test checking provider existence."""
        assert self.sd.has_provider("llm") is False
        self.sd.register_llm_provider("test")
        assert self.sd.has_provider("llm") is True

    def test_summary(self):
        """Test discovery summary."""
        self.sd.register_llm_provider("llm1")
        self.sd.register_llm_provider("llm2")
        self.sd.register_embedding_provider("emb1")

        summary = self.sd.summary()
        assert summary["llm"] == 2
        assert summary["embedding"] == 1

    def test_repr(self):
        """Test string representation."""
        self.sd.register_llm_provider("test")
        repr_str = repr(self.sd)
        assert "ServiceDiscovery" in repr_str
        assert "1 llm" in repr_str


class TestRegistryServiceDiscoveryIntegration:
    """Tests for CapabilityRegistry + ServiceDiscovery integration."""

    def test_attach_service_discovery(self):
        """Test attaching ServiceDiscovery to the registry."""
        registry = CapabilityRegistry()
        sd = ServiceDiscovery()
        sd.register_llm_provider("test_llm")

        registry.set_service_discovery(sd)
        assert registry.get_service_discovery() is sd

    def test_requirements_check_with_service_discovery(self):
        """Test that requirement checking considers ServiceDiscovery."""
        registry = CapabilityRegistry()
        sd = ServiceDiscovery()
        sd.register_llm_provider("test_llm")
        registry.set_service_discovery(sd)

        registry.register_agent(
            "agent_a",
            type("A", (), {}),
            capabilities=["fallacy_detection"],
            requires=["llm"],
        )

        reqs = registry.check_requirements("agent_a")
        assert reqs["llm"] is True
