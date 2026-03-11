"""
Tests for the WorkflowDSL (declarative workflow composition).

These tests validate:
- WorkflowBuilder fluent API
- Workflow validation (dependencies, duplicates)
- Execution order computation
- WorkflowExecutor with CapabilityRegistry integration
"""

import pytest
from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowDefinition,
    WorkflowExecutor,
    PhaseStatus,
)
from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentType,
)


class TestWorkflowBuilder:
    """Tests for the WorkflowBuilder."""

    def test_build_simple_workflow(self):
        """Test building a simple linear workflow."""
        workflow = (
            WorkflowBuilder("simple")
            .add_phase("extract", capability="fact_extraction")
            .add_phase("fallacy", capability="fallacy_detection")
            .add_phase("synthesis", capability="synthesis")
            .build()
        )

        assert workflow.name == "simple"
        assert len(workflow.phases) == 3
        assert workflow.phases[0].name == "extract"
        assert workflow.phases[0].capability == "fact_extraction"

    def test_build_with_dependencies(self):
        """Test building a workflow with dependencies."""
        workflow = (
            WorkflowBuilder("with_deps")
            .add_phase("extract", capability="fact_extraction")
            .add_phase(
                "counter",
                capability="counter_argument",
                depends_on=["extract"],
            )
            .build()
        )

        phase_counter = workflow.get_phase("counter")
        assert phase_counter is not None
        assert "extract" in phase_counter.depends_on

    def test_build_with_optional_phases(self):
        """Test building a workflow with optional phases."""
        workflow = (
            WorkflowBuilder("optional")
            .add_phase("extract", capability="fact_extraction")
            .add_phase(
                "transcribe",
                capability="speech_transcription",
                optional=True,
            )
            .build()
        )

        phase_transcribe = workflow.get_phase("transcribe")
        assert phase_transcribe is not None
        assert phase_transcribe.optional is True

    def test_build_with_parameters(self):
        """Test building phases with custom parameters."""
        workflow = (
            WorkflowBuilder("params")
            .add_phase(
                "fallacy",
                capability="fallacy_detection",
                parameters={"language": "fr", "threshold": 0.5},
            )
            .build()
        )

        phase = workflow.get_phase("fallacy")
        assert phase.parameters["language"] == "fr"
        assert phase.parameters["threshold"] == 0.5

    def test_build_with_metadata(self):
        """Test setting metadata on the workflow."""
        workflow = (
            WorkflowBuilder("meta")
            .set_metadata("author", "test")
            .set_metadata("version", "1.0")
            .add_phase("extract", capability="fact_extraction")
            .build()
        )

        assert workflow.metadata["author"] == "test"
        assert workflow.metadata["version"] == "1.0"

    def test_validation_bad_dependency(self):
        """Test that referencing non-existent dependency raises ValueError."""
        with pytest.raises(ValueError, match="validation failed"):
            (
                WorkflowBuilder("bad_dep")
                .add_phase("extract", capability="fact_extraction")
                .add_phase(
                    "counter",
                    capability="counter_argument",
                    depends_on=["nonexistent"],
                )
                .build()
            )

    def test_validation_duplicate_names(self):
        """Test that duplicate phase names raise ValueError."""
        with pytest.raises(ValueError, match="Duplicate"):
            (
                WorkflowBuilder("dup")
                .add_phase("extract", capability="fact_extraction")
                .add_phase("extract", capability="another_cap")
                .build()
            )


class TestWorkflowDefinition:
    """Tests for WorkflowDefinition."""

    def test_get_phase(self):
        """Test getting a phase by name."""
        workflow = (
            WorkflowBuilder("test")
            .add_phase("a", capability="cap_a")
            .add_phase("b", capability="cap_b")
            .build()
        )

        assert workflow.get_phase("a") is not None
        assert workflow.get_phase("a").capability == "cap_a"
        assert workflow.get_phase("nonexistent") is None

    def test_execution_order_linear(self):
        """Test execution order for a linear workflow (no dependencies)."""
        workflow = (
            WorkflowBuilder("linear")
            .add_phase("a", capability="cap_a")
            .add_phase("b", capability="cap_b")
            .add_phase("c", capability="cap_c")
            .build()
        )

        order = workflow.get_execution_order()
        # All phases have no deps, so they should all be in level 0
        assert len(order) == 1
        assert set(order[0]) == {"a", "b", "c"}

    def test_execution_order_sequential(self):
        """Test execution order with sequential dependencies."""
        workflow = (
            WorkflowBuilder("seq")
            .add_phase("a", capability="cap_a")
            .add_phase("b", capability="cap_b", depends_on=["a"])
            .add_phase("c", capability="cap_c", depends_on=["b"])
            .build()
        )

        order = workflow.get_execution_order()
        assert len(order) == 3
        assert order[0] == ["a"]
        assert order[1] == ["b"]
        assert order[2] == ["c"]

    def test_execution_order_diamond(self):
        """Test execution order for diamond dependency pattern."""
        workflow = (
            WorkflowBuilder("diamond")
            .add_phase("a", capability="cap_a")
            .add_phase("b", capability="cap_b", depends_on=["a"])
            .add_phase("c", capability="cap_c", depends_on=["a"])
            .add_phase("d", capability="cap_d", depends_on=["b", "c"])
            .build()
        )

        order = workflow.get_execution_order()
        assert len(order) == 3
        assert order[0] == ["a"]
        assert set(order[1]) == {"b", "c"}
        assert order[2] == ["d"]

    def test_required_capabilities(self):
        """Test getting list of required capabilities."""
        workflow = (
            WorkflowBuilder("caps")
            .add_phase("a", capability="cap_x")
            .add_phase("b", capability="cap_y")
            .build()
        )

        caps = workflow.get_required_capabilities()
        assert caps == ["cap_x", "cap_y"]

    def test_wildcard_dependency_valid(self):
        """Test that wildcard dependency pattern is accepted."""
        # "fallacy_*" matches "fallacy_neural" and "fallacy_symbolic"
        workflow = (
            WorkflowBuilder("wildcard")
            .add_phase("fallacy_neural", capability="neural_fallacy")
            .add_phase("fallacy_symbolic", capability="symbolic_fallacy")
            .add_phase(
                "counter",
                capability="counter_argument",
                depends_on=["fallacy_*"],
            )
            .build()
        )
        assert len(workflow.phases) == 3


class TestWorkflowExecutor:
    """Tests for the WorkflowExecutor."""

    def setup_method(self):
        self.registry = CapabilityRegistry()

    @pytest.mark.asyncio
    async def test_execute_simple_workflow(self):
        """Test executing a simple workflow with all capabilities available."""
        self.registry.register_agent(
            "agent_a", type("A", (), {}), capabilities=["cap_a"]
        )
        self.registry.register_agent(
            "agent_b", type("B", (), {}), capabilities=["cap_b"]
        )

        workflow = (
            WorkflowBuilder("test")
            .add_phase("a", capability="cap_a")
            .add_phase("b", capability="cap_b")
            .build()
        )

        executor = WorkflowExecutor(self.registry)
        results = await executor.execute(workflow, "test input")

        assert "a" in results
        assert "b" in results
        assert results["a"].status == PhaseStatus.COMPLETED
        assert results["b"].status == PhaseStatus.COMPLETED
        assert results["a"].component_used == "agent_a"

    @pytest.mark.asyncio
    async def test_execute_optional_missing(self):
        """Test that optional phases are skipped when no provider exists."""
        self.registry.register_agent(
            "agent_a", type("A", (), {}), capabilities=["cap_a"]
        )

        workflow = (
            WorkflowBuilder("test")
            .add_phase("a", capability="cap_a")
            .add_phase("b", capability="cap_missing", optional=True)
            .build()
        )

        executor = WorkflowExecutor(self.registry)
        results = await executor.execute(workflow, "test input")

        assert results["a"].status == PhaseStatus.COMPLETED
        assert results["b"].status == PhaseStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_execute_required_missing(self):
        """Test that required phases fail when no provider exists."""
        workflow = (
            WorkflowBuilder("test").add_phase("a", capability="cap_missing").build()
        )

        executor = WorkflowExecutor(self.registry)
        results = await executor.execute(workflow, "test input")

        assert results["a"].status == PhaseStatus.FAILED
        assert "No provider" in results["a"].error


class TestLegoWorkflowExamples:
    """Tests for the example workflows from the plan."""

    def test_quick_analysis_workflow(self):
        """Test building the quick analysis workflow from the plan."""
        workflow = (
            WorkflowBuilder("quick_analysis")
            .add_phase("extract", capability="fact_extraction")
            .add_phase("fallacy", capability="fallacy_detection")
            .add_phase("synthesis", capability="synthesis")
            .build()
        )
        assert len(workflow.phases) == 3
        assert workflow.get_required_capabilities() == [
            "fact_extraction",
            "fallacy_detection",
            "synthesis",
        ]

    def test_full_analysis_workflow(self):
        """Test building the full analysis workflow from the plan."""
        workflow = (
            WorkflowBuilder("full_analysis")
            .add_phase(
                "transcribe",
                capability="speech_transcription",
                optional=True,
            )
            .add_phase("extract", capability="fact_extraction")
            .add_phase("fallacy_neural", capability="neural_fallacy_detection")
            .add_phase("fallacy_symbolic", capability="symbolic_fallacy_detection")
            .add_phase("quality", capability="argument_quality")
            .add_phase(
                "counter",
                capability="counter_argument",
                depends_on=["fallacy_neural", "fallacy_symbolic"],
            )
            .add_phase("jtms", capability="belief_maintenance")
            .add_phase("dung", capability="dung_semantics")
            .add_phase(
                "governance",
                capability="governance_simulation",
                optional=True,
            )
            .add_phase(
                "debate",
                capability="adversarial_debate",
                optional=True,
            )
            .add_phase("index", capability="semantic_indexing")
            .add_phase("synthesis", capability="synthesis")
            .build()
        )

        assert len(workflow.phases) == 12
        assert workflow.get_phase("transcribe").optional is True
        assert workflow.get_phase("governance").optional is True
        assert "fallacy_neural" in workflow.get_phase("counter").depends_on

    def test_custom_student_workflow(self):
        """Test building a custom student experiment workflow."""
        workflow = (
            WorkflowBuilder("student_experiment")
            .add_phase("quality", capability="argument_quality")
            .add_phase("debate", capability="adversarial_debate")
            .add_phase("governance", capability="governance_simulation")
            .build()
        )

        assert len(workflow.phases) == 3
        # All phases independent — single execution level
        order = workflow.get_execution_order()
        assert len(order) == 1
