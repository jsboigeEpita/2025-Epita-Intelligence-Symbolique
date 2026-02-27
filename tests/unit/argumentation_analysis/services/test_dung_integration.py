"""
Tests for abs_arg_dung integration (proper package imports, no sys.path hacks).

Tests validate:
- abs_arg_dung is importable as a proper Python package
- No sys.path manipulation in api/ and jtms_service files
- CapabilityRegistry registration for all Phase 1 components
"""

import pathlib

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[4]


class TestDungPackageImport:
    """Test that abs_arg_dung is importable as a proper package."""

    def test_import_package(self):
        """abs_arg_dung imports without errors."""
        import abs_arg_dung

        assert abs_arg_dung is not None

    def test_package_has_init(self):
        """abs_arg_dung has __init__.py (is a proper package)."""
        init_file = PROJECT_ROOT / "abs_arg_dung" / "__init__.py"
        assert init_file.exists(), "abs_arg_dung/__init__.py is missing"


class TestNoSysPathHacks:
    """Verify that sys.path hacks have been removed from key files."""

    def test_no_sys_path_in_api_main(self):
        """api/main.py does not contain sys.path manipulation."""
        source = (PROJECT_ROOT / "api" / "main.py").read_text(encoding="utf-8")
        assert (
            "sys.path" not in source
        ), "api/main.py still contains sys.path manipulation"

    def test_no_sys_path_in_api_services(self):
        """api/services.py does not contain sys.path manipulation."""
        source = (PROJECT_ROOT / "api" / "services.py").read_text(encoding="utf-8")
        assert (
            "sys.path" not in source
        ), "api/services.py still contains sys.path manipulation"

    def test_no_sys_path_in_jtms_service(self):
        """jtms_service.py does not contain sys.path manipulation."""
        svc_path = (
            PROJECT_ROOT / "argumentation_analysis" / "services" / "jtms_service.py"
        )
        source = svc_path.read_text(encoding="utf-8")
        assert (
            "sys.path" not in source
        ), "jtms_service.py still contains sys.path manipulation"

    def test_api_services_imports_from_abs_arg_dung(self):
        """api/services.py imports from abs_arg_dung package (not relative)."""
        source = (PROJECT_ROOT / "api" / "services.py").read_text(encoding="utf-8")
        assert "from abs_arg_dung" in source or "import abs_arg_dung" in source

    def test_jtms_service_imports_from_package(self):
        """jtms_service.py imports from argumentation_analysis.services.jtms."""
        svc_path = (
            PROJECT_ROOT / "argumentation_analysis" / "services" / "jtms_service.py"
        )
        source = svc_path.read_text(encoding="utf-8")
        assert "from argumentation_analysis.services.jtms" in source


class TestPhase1Registration:
    """Test CapabilityRegistry integration for all Phase 1 components."""

    def test_register_jtms(self):
        """JTMS service registers in CapabilityRegistry."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.services.jtms import JTMS

        registry = CapabilityRegistry()
        registry.register_service(
            "jtms",
            JTMS,
            capabilities=["belief_maintenance", "non_monotonic_reasoning"],
        )
        services = registry.find_services_for_capability("belief_maintenance")
        assert len(services) == 1
        assert services[0].name == "jtms"

    def test_register_quality_evaluator(self):
        """Quality evaluator registers in CapabilityRegistry."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.agents.core.quality import (
            ArgumentQualityEvaluator,
        )

        registry = CapabilityRegistry()
        registry.register_agent(
            "quality_evaluator",
            ArgumentQualityEvaluator,
            capabilities=["argument_quality", "virtue_scoring"],
        )
        agents = registry.find_agents_for_capability("argument_quality")
        assert len(agents) == 1
        assert agents[0].name == "quality_evaluator"

    def test_register_local_llm(self):
        """LocalLLMService registers in CapabilityRegistry."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.services.local_llm_service import LocalLLMService

        registry = CapabilityRegistry()
        registry.register_service(
            "local_llm",
            LocalLLMService,
            capabilities=["chat_completion"],
        )
        services = registry.find_services_for_capability("chat_completion")
        assert len(services) == 1
        assert services[0].name == "local_llm"

    def test_register_dung_framework(self):
        """Dung framework class registers in CapabilityRegistry."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )

        # Use a placeholder class since root api.services can't be imported
        # from this test path (shadows argumentation_analysis.api)
        class DungAnalysisServiceStub:
            """Stub representing DungAnalysisService for registration test."""

            pass

        registry = CapabilityRegistry()
        registry.register_service(
            "dung_framework",
            DungAnalysisServiceStub,
            capabilities=["dung_semantics", "abstract_argumentation"],
        )
        services = registry.find_services_for_capability("dung_semantics")
        assert len(services) == 1
        assert services[0].name == "dung_framework"

    def test_register_all_phase1_no_conflict(self):
        """All Phase 1 components register together without conflict."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.services.jtms import JTMS
        from argumentation_analysis.agents.core.quality import (
            ArgumentQualityEvaluator,
        )
        from argumentation_analysis.services.local_llm_service import LocalLLMService

        class DungAnalysisServiceStub:
            pass

        registry = CapabilityRegistry()

        registry.register_service(
            "jtms",
            JTMS,
            capabilities=["belief_maintenance", "non_monotonic_reasoning"],
        )
        registry.register_agent(
            "quality_evaluator",
            ArgumentQualityEvaluator,
            capabilities=["argument_quality", "virtue_scoring"],
        )
        registry.register_service(
            "local_llm",
            LocalLLMService,
            capabilities=["chat_completion"],
        )
        registry.register_service(
            "dung_framework",
            DungAnalysisServiceStub,
            capabilities=["dung_semantics", "abstract_argumentation"],
        )

        # All capabilities present
        all_caps = registry.get_all_capabilities()
        expected = {
            "belief_maintenance",
            "non_monotonic_reasoning",
            "argument_quality",
            "virtue_scoring",
            "chat_completion",
            "dung_semantics",
            "abstract_argumentation",
        }
        assert expected.issubset(set(all_caps.keys()))

        # Each component findable by its correct type
        assert len(registry.find_services_for_capability("belief_maintenance")) == 1
        assert len(registry.find_agents_for_capability("argument_quality")) == 1
        assert len(registry.find_services_for_capability("chat_completion")) == 1
        assert len(registry.find_services_for_capability("dung_semantics")) == 1
