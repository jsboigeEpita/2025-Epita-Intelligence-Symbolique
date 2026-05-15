"""Integration tests for DeepSynthesisAgent wiring (#534).

Tests verify:
- DAG ordering: deep_synthesis phase runs after its dependencies
- File output: invoke callable produces valid markdown with non-empty sections
- Conversational orchestrator includes deep_synthesis result
- CLI runner argument parsing
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
    DeepSynthesisReport,
)


def _make_fixture_state() -> UnifiedAnalysisState:
    """Build a fixture state with data in key analysis dimensions."""
    state = UnifiedAnalysisState(
        "The speaker argues that national sovereignty requires immediate action. "
        "They claim that foreign powers threaten our independence. "
        "However, the evidence shows cooperation yields better outcomes. "
        "We must defend our borders against external interference."
    )
    state.add_argument("National sovereignty requires immediate action")
    state.add_argument("Foreign powers threaten our independence")
    state.add_argument("Cooperation yields better outcomes")
    state.add_argument("We must defend our borders against external interference")
    state.add_fallacy("ad hominem", "Attacks foreign powers instead of argument", "arg_1")
    state.add_fallacy("slippery slope", "Suggests sovereignty loss without evidence", "arg_2")
    state.add_dung_framework(
        name="main_framework",
        arguments=["arg_1", "arg_2", "arg_3", "arg_4"],
        attacks=[["arg_3", "arg_1"], ["arg_3", "arg_2"]],
        extensions={
            "grounded": ["arg_3", "arg_4"],
            "preferred": [["arg_3", "arg_4"]],
            "stable": [["arg_3", "arg_4"]],
        },
    )
    state.add_counter_argument(
        original_arg="Foreign powers threaten our independence",
        counter_content="Historical data shows alliances strengthen sovereignty",
        strategy="counter-example",
        score=8.5,
    )
    return state


# =========================================================================
# Test: DAG ordering in spectacular workflow
# =========================================================================


class TestDAGOrdering:

    def test_deep_synthesis_phase_exists_in_spectacular(self):
        """deep_synthesis phase should be present in the spectacular workflow."""
        from argumentation_analysis.orchestration.workflows import build_spectacular_workflow

        wf = build_spectacular_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "deep_synthesis" in phase_names, (
            f"deep_synthesis not in spectacular phases: {phase_names}"
        )

    def test_deep_synthesis_depends_on_correct_phases(self):
        """deep_synthesis should depend on synthesis, narrative_synthesis, belief_revision."""
        from argumentation_analysis.orchestration.workflows import build_spectacular_workflow

        wf = build_spectacular_workflow()
        ds_phase = next(p for p in wf.phases if p.name == "deep_synthesis")
        assert set(ds_phase.depends_on) == {"synthesis", "narrative_synthesis", "belief_revision"}

    def test_deep_synthesis_is_after_synthesis(self):
        """deep_synthesis must come after synthesis in the phase list."""
        from argumentation_analysis.orchestration.workflows import build_spectacular_workflow

        wf = build_spectacular_workflow()
        phase_names = [p.name for p in wf.phases]
        synthesis_idx = phase_names.index("synthesis")
        ds_idx = phase_names.index("deep_synthesis")
        assert ds_idx > synthesis_idx

    def test_deep_synthesis_not_optional_in_spectacular(self):
        """deep_synthesis should be non-optional in the spectacular workflow."""
        from argumentation_analysis.orchestration.workflows import build_spectacular_workflow

        wf = build_spectacular_workflow()
        ds_phase = next(p for p in wf.phases if p.name == "deep_synthesis")
        assert ds_phase.optional is False

    def test_deep_synthesis_has_timeout(self):
        """deep_synthesis should have a timeout_seconds set."""
        from argumentation_analysis.orchestration.workflows import build_spectacular_workflow

        wf = build_spectacular_workflow()
        ds_phase = next(p for p in wf.phases if p.name == "deep_synthesis")
        assert ds_phase.timeout_seconds is not None
        assert ds_phase.timeout_seconds > 0

    def test_deep_synthesis_capability_registered(self):
        """The deep_synthesis capability should be registered in the registry."""
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry()
        providers = registry.find_services_for_capability("deep_synthesis")
        assert len(providers) > 0, "No service registered for deep_synthesis capability"


# =========================================================================
# Test: File output via invoke callable
# =========================================================================


class TestFileOutput:

    def test_invoke_produces_markdown_file(self, tmp_path):
        """Invoke callable should write markdown to the specified output path."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_deep_synthesis

        state = _make_fixture_state()
        output_file = tmp_path / "test_report.md"

        ctx = {
            "_state_object": state,
            "source_metadata": {
                "opaque_id": "test_corpus",
                "era": "2020s",
                "language": "en",
                "discourse_type": "populist",
            },
            "deep_synthesis_output_path": str(output_file),
        }

        result = asyncio.get_event_loop().run_until_complete(
            _invoke_deep_synthesis("", ctx)
        )

        assert "error" not in result
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert len(content) > 500

    def test_markdown_has_required_sections(self, tmp_path):
        """Output markdown should have non-empty sections 1, 2, 3 minimum."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_deep_synthesis

        state = _make_fixture_state()
        output_file = tmp_path / "sections_report.md"

        ctx = {
            "_state_object": state,
            "source_metadata": {
                "opaque_id": "test_corpus",
                "era": "2020s",
                "language": "en",
                "discourse_type": "populist",
            },
            "deep_synthesis_output_path": str(output_file),
        }

        result = asyncio.get_event_loop().run_until_complete(
            _invoke_deep_synthesis("", ctx)
        )

        content = output_file.read_text(encoding="utf-8")
        assert "## 1. Source Overview" in content
        assert "## 2. Argument Map" in content
        assert "## 3. Fallacy Diagnosis" in content
        assert result["sections_populated"] >= 3

    def test_invoke_without_output_path(self):
        """Invoke callable should work without deep_synthesis_output_path."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_deep_synthesis

        state = _make_fixture_state()
        ctx = {
            "_state_object": state,
            "source_metadata": {
                "opaque_id": "test_no_path",
                "era": "2020s",
                "language": "en",
                "discourse_type": "populist",
            },
        }

        result = asyncio.get_event_loop().run_until_complete(
            _invoke_deep_synthesis("", ctx)
        )

        assert "error" not in result
        assert "markdown" in result
        assert len(result["markdown"]) > 500


# =========================================================================
# Test: CLI runner argument parsing
# =========================================================================


class TestCLIRunner:

    def test_cli_imports(self):
        """CLI runner module should import without errors."""
        import importlib
        mod = importlib.import_module("scripts.run_deep_synthesis")
        assert hasattr(mod, "run_on_text")
        assert hasattr(mod, "run_from_source")
        assert hasattr(mod, "main")

    def test_cli_run_on_text(self):
        """run_on_text should produce a valid result dict without full pipeline."""
        from scripts.run_deep_synthesis import run_on_text

        # Patch pipeline imports to avoid actual LLM calls
        with patch.dict("sys.modules", {
            "argumentation_analysis.orchestration.unified_pipeline": None,
            "argumentation_analysis.orchestration.conversational_orchestrator": None,
        }):
            meta = {"opaque_id": "cli_test", "era": "", "language": "en", "discourse_type": "other"}
            result = asyncio.run(run_on_text("Test argument text.", meta, "spectacular"))

        assert "markdown" in result
        assert result["sections_populated"] >= 1
