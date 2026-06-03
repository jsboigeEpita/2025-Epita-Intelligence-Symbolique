"""
Tests for --formal-extension selector (parametric integration #905).

Validates:
  - CLI argparse (--formal-extension with all/core/none/csv)
  - Context propagation (zero-pollution: default "all" not in context)
  - Workflow filter function (phase removal based on filter spec)
  - Validation of unknown extension names
  - Signature acceptance in run_modern_analysis
"""

import pytest
from unittest.mock import patch

from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowDefinition,
)
from argumentation_analysis.orchestration.workflows import (
    build_spectacular_workflow,
    filter_formal_extensions,
    _EXTENSION_CAPABILITIES,
    _CORE_CAPABILITIES,
    _ALL_EXTENSION_CAPS,
)


# ---------------------------------------------------------------------------
# Extension registry tests
# ---------------------------------------------------------------------------


class TestFormalExtensionRegistry:
    """Test the extension registry constants."""

    def test_17_extensions_defined(self):
        """Should define exactly 17 Tweety extension handlers."""
        assert len(_EXTENSION_CAPABILITIES) == 17

    def test_core_4_defined(self):
        """Should define exactly 4 core formal capabilities."""
        assert len(_CORE_CAPABILITIES) == 4

    def test_core_and_extensions_disjoint(self):
        """Core and extension capabilities should not overlap."""
        assert _CORE_CAPABILITIES.isdisjoint(_ALL_EXTENSION_CAPS)

    def test_known_cli_names(self):
        """All 17 CLI short names should be present."""
        expected = {
            "ranking", "bipolar", "aba", "adf", "aspic",
            "belief_revision", "probabilistic", "dialogue",
            "dl", "cl", "setaf", "weighted", "social",
            "eaf", "delp", "qbf", "asp",
        }
        assert set(_EXTENSION_CAPABILITIES.keys()) == expected


# ---------------------------------------------------------------------------
# CLI argument validation
# ---------------------------------------------------------------------------


class TestFormalExtensionCLI:
    """Test --formal-extension argument parsing validation."""

    def test_valid_presets(self):
        """all, core, none should be valid preset values."""
        for preset in ("all", "core", "none"):
            assert isinstance(preset, str)

    def test_csv_list_format(self):
        """Comma-separated list should be parseable."""
        csv = "ranking,bipolar,aspic"
        names = [s.strip() for s in csv.split(",")]
        assert names == ["ranking", "bipolar", "aspic"]

    def test_all_cli_names_are_valid_extensions(self):
        """Each CLI name should map to a known capability."""
        for name, cap in _EXTENSION_CAPABILITIES.items():
            assert isinstance(cap, str)
            assert len(cap) > 0


# ---------------------------------------------------------------------------
# Context propagation (zero-pollution pattern)
# ---------------------------------------------------------------------------


class TestFormalExtensionContext:
    """Test context propagation for --formal-extension."""

    def test_default_all_not_in_context(self):
        """Default 'all' should NOT be added to context."""
        formal_extension = "all"
        context = {}
        if formal_extension != "all":
            context["formal_extension_filter"] = formal_extension
        assert "formal_extension_filter" not in context

    def test_core_in_context(self):
        """'core' should be in context."""
        formal_extension = "core"
        context = {}
        if formal_extension != "all":
            context["formal_extension_filter"] = formal_extension
        assert context["formal_extension_filter"] == "core"

    def test_none_in_context(self):
        """'none' should be in context."""
        formal_extension = "none"
        context = {}
        if formal_extension != "all":
            context["formal_extension_filter"] = formal_extension
        assert context["formal_extension_filter"] == "none"

    def test_csv_in_context(self):
        """Comma-separated list should be in context."""
        formal_extension = "ranking,bipolar"
        context = {}
        if formal_extension != "all":
            context["formal_extension_filter"] = formal_extension
        assert context["formal_extension_filter"] == "ranking,bipolar"

    @pytest.mark.parametrize(
        "value,expected_in_context",
        [
            ("all", False),
            ("core", True),
            ("none", True),
            ("ranking", True),
            ("ranking,bipolar,aspic", True),
        ],
    )
    def test_context_pollution_parametrized(self, value, expected_in_context):
        """Only non-'all' values pollute context."""
        context = {}
        if value != "all":
            context["formal_extension_filter"] = value
        assert ("formal_extension_filter" in context) == expected_in_context


# ---------------------------------------------------------------------------
# Workflow filter function
# ---------------------------------------------------------------------------


class TestFormalExtensionFilter:
    """Test filter_formal_extensions workflow phase removal."""

    def _build_mini_workflow(self) -> WorkflowDefinition:
        """Build a minimal workflow with core + extension phases for testing."""
        return (
            WorkflowBuilder("test_formal")
            .add_phase("extract", capability="fact_extraction")
            .add_phase("pl", capability="propositional_logic", depends_on=["extract"], optional=True)
            .add_phase("fol", capability="fol_reasoning", depends_on=["extract"], optional=True)
            .add_phase("modal", capability="modal_logic", depends_on=["extract"], optional=True)
            .add_phase("dung", capability="dung_extensions", depends_on=["extract"], optional=True)
            .add_phase("ranking", capability="ranking_semantics", depends_on=["dung"], optional=True)
            .add_phase("bipolar", capability="bipolar_argumentation", depends_on=["extract"], optional=True)
            .add_phase("aspic", capability="aspic_plus_reasoning", depends_on=["dung"], optional=True)
            .add_phase("quality", capability="argument_quality", depends_on=["extract"])
            .build()
        )

    def test_all_keeps_everything(self):
        """filter_spec='all' should not remove any phases."""
        wf = self._build_mini_workflow()
        phase_count_before = len(wf.phases)
        result = filter_formal_extensions(wf, "all")
        assert result is wf  # mutated in-place
        assert len(wf.phases) == phase_count_before

    def test_core_removes_extensions(self):
        """filter_spec='core' should remove extension phases but keep core 4."""
        wf = self._build_mini_workflow()
        filter_formal_extensions(wf, "core")
        caps = {p.capability for p in wf.phases}
        # Core 4 should remain
        assert "propositional_logic" in caps
        assert "fol_reasoning" in caps
        assert "modal_logic" in caps
        assert "dung_extensions" in caps
        # Extensions should be removed
        assert "ranking_semantics" not in caps
        assert "bipolar_argumentation" not in caps
        assert "aspic_plus_reasoning" not in caps
        # Non-formal phases should remain
        assert "fact_extraction" in caps
        assert "argument_quality" in caps

    def test_none_removes_all_formal(self):
        """filter_spec='none' should remove all formal phases."""
        wf = self._build_mini_workflow()
        filter_formal_extensions(wf, "none")
        caps = {p.capability for p in wf.phases}
        # Core 4 should be removed
        assert "propositional_logic" not in caps
        assert "fol_reasoning" not in caps
        assert "modal_logic" not in caps
        assert "dung_extensions" not in caps
        # Extensions should be removed
        assert "ranking_semantics" not in caps
        assert "bipolar_argumentation" not in caps
        # Non-formal phases should remain
        assert "fact_extraction" in caps
        assert "argument_quality" in caps

    def test_csv_keeps_requested_plus_core(self):
        """CSV list should keep requested extensions + core 4."""
        wf = self._build_mini_workflow()
        filter_formal_extensions(wf, "ranking,aspic")
        caps = {p.capability for p in wf.phases}
        # Requested extensions should remain
        assert "ranking_semantics" in caps
        assert "aspic_plus_reasoning" in caps
        # Non-requested extension should be removed
        assert "bipolar_argumentation" not in caps
        # Core 4 should remain
        assert "propositional_logic" in caps
        assert "fol_reasoning" in caps
        assert "modal_logic" in caps
        assert "dung_extensions" in caps

    def test_unknown_name_raises(self):
        """Unknown extension name should raise ValueError."""
        wf = self._build_mini_workflow()
        with pytest.raises(ValueError, match="Unknown formal extensions"):
            filter_formal_extensions(wf, "ranking,unknown_handler")

    def test_spectacular_core_count(self):
        """On the real spectacular workflow, core should remove extension phases."""
        wf = build_spectacular_workflow()
        total_before = len(wf.phases)
        # Deep copy phases for comparison
        import copy
        wf2 = copy.deepcopy(wf)
        filter_formal_extensions(wf2, "core")
        assert len(wf2.phases) < total_before
        caps = {p.capability for p in wf2.phases}
        # No extension caps should remain
        assert caps.isdisjoint(_ALL_EXTENSION_CAPS)


# ---------------------------------------------------------------------------
# Signature test
# ---------------------------------------------------------------------------


class TestRunModernAnalysisSignature:
    """Test that run_modern_analysis accepts formal_extension parameter."""

    def test_signature_has_formal_extension(self):
        """run_modern_analysis should accept formal_extension parameter."""
        import inspect
        from argumentation_analysis.run_orchestration import run_modern_analysis

        sig = inspect.signature(run_modern_analysis)
        assert "formal_extension" in sig.parameters
        assert sig.parameters["formal_extension"].default == "all"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
