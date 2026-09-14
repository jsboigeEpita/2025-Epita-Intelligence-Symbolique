"""
Comprehensive unit tests for the argumentation_analysis/plugin_framework/ module.

Tests cover:
- core/contracts.py — Pydantic models (OrchestrationRequest, OrchestrationResponse,
  Capability, PluginManifest, BenchmarkResult, BenchmarkSuiteResult)
- core/plugins/interfaces.py — BasePlugin ABC
- retrait #2099 — the three consumer-less discovery mechanisms are withdrawn
  (core/plugin_loader.py, core/plugins/plugin_loader.py, agents/agent_loader.py);
  the real plugins join the system by direct import (guard below)
- core/services/orchestration_service.py — OrchestrationService routing
- core/decorators.py — track_tokens decorator
- benchmarking/benchmark_service.py — BenchmarkService suite runner
"""

import importlib
import json
import os
import time
from abc import ABC
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from pydantic import ValidationError

from argumentation_analysis.plugin_framework.core.contracts import (
    BenchmarkResult,
    BenchmarkSuiteResult,
    Capability,
    OrchestrationRequest,
    OrchestrationResponse,
    PluginManifest,
)
from argumentation_analysis.plugin_framework.core.plugins.interfaces import BasePlugin
from argumentation_analysis.plugin_framework.core.services.orchestration_service import (
    OrchestrationService,
)
from argumentation_analysis.plugin_framework.benchmarking.benchmark_service import (
    BenchmarkService,
)

# ============================================================================
# contracts.py — OrchestrationRequest
# ============================================================================


class TestOrchestrationRequest:
    """Tests for OrchestrationRequest Pydantic model."""

    def test_valid_direct_plugin_call(self):
        req = OrchestrationRequest(
            mode="direct_plugin_call",
            target="plugin.function",
        )
        assert req.mode == "direct_plugin_call"
        assert req.target == "plugin.function"
        assert req.payload == {}
        assert req.session_id is None

    def test_withdrawn_workflow_execution_mode_rejected(self):
        """#2102 §5 : le mode fantôme 'workflow_execution' (déclaré, jamais
        implémenté) est retiré du contrat — sa construction est rejetée,
        plus acceptée-puis-erreur au guichet."""
        with pytest.raises(ValidationError):
            OrchestrationRequest(mode="workflow_execution", target="my_workflow")

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValidationError):
            OrchestrationRequest(mode="invalid_mode", target="x")

    def test_missing_mode_rejected(self):
        with pytest.raises(ValidationError):
            OrchestrationRequest(target="x")

    def test_missing_target_rejected(self):
        with pytest.raises(ValidationError):
            OrchestrationRequest(mode="direct_plugin_call")

    def test_payload_default_factory(self):
        """Each instance gets its own default dict (no shared mutable default)."""
        req1 = OrchestrationRequest(mode="direct_plugin_call", target="a")
        req2 = OrchestrationRequest(mode="direct_plugin_call", target="b")
        req1.payload["x"] = 1
        assert "x" not in req2.payload

    def test_model_dump(self):
        req = OrchestrationRequest(
            mode="direct_plugin_call",
            target="p.f",
            payload={"a": 1},
            session_id="s1",
        )
        d = req.model_dump()
        assert d == {
            "mode": "direct_plugin_call",
            "target": "p.f",
            "payload": {"a": 1},
            "session_id": "s1",
        }

    def test_model_dump_excludes_none_when_asked(self):
        req = OrchestrationRequest(mode="direct_plugin_call", target="t")
        d = req.model_dump(exclude_none=True)
        assert "session_id" not in d


# ============================================================================
# contracts.py — OrchestrationResponse
# ============================================================================


class TestOrchestrationResponse:
    """Tests for OrchestrationResponse Pydantic model."""

    def test_success_response(self):
        resp = OrchestrationResponse(status="success", result={"output": "data"})
        assert resp.status == "success"
        assert resp.result == {"output": "data"}
        assert resp.error_message is None

    def test_error_response(self):
        resp = OrchestrationResponse(
            status="error", error_message="Something went wrong"
        )
        assert resp.status == "error"
        assert resp.result is None
        assert resp.error_message == "Something went wrong"

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            OrchestrationResponse(status="pending")

    def test_missing_status_rejected(self):
        with pytest.raises(ValidationError):
            OrchestrationResponse()

    def test_defaults_are_none(self):
        resp = OrchestrationResponse(status="success")
        assert resp.result is None
        assert resp.error_message is None

    def test_model_dump_success(self):
        resp = OrchestrationResponse(status="success", result={"k": "v"})
        d = resp.model_dump()
        assert d["status"] == "success"
        assert d["result"] == {"k": "v"}


# ============================================================================
# contracts.py — Capability
# ============================================================================


class TestCapability:
    """Tests for Capability Pydantic model with alias handling."""

    def test_valid_creation_with_aliases(self):
        """Capability uses alias='input' and alias='output' for construction."""
        cap = Capability(
            name="analyze",
            description="Analyze text",
            input={"type": "string"},
            output={"type": "object"},
        )
        assert cap.name == "analyze"
        assert cap.description == "Analyze text"
        assert cap.input_schema == {"type": "string"}
        assert cap.output_schema == {"type": "object"}

    def test_field_names_require_alias(self):
        """Capability fields use alias='input'/'output', so field names alone
        are rejected — aliases are mandatory for construction."""
        with pytest.raises(ValidationError):
            Capability(
                name="analyze",
                description="Analyze text",
                input_schema={"type": "string"},
                output_schema={"type": "object"},
            )

    def test_missing_name_rejected(self):
        with pytest.raises(ValidationError):
            Capability(
                description="d",
                input={"type": "string"},
                output={"type": "object"},
            )

    def test_missing_description_rejected(self):
        with pytest.raises(ValidationError):
            Capability(
                name="n",
                input={"type": "string"},
                output={"type": "object"},
            )

    def test_missing_input_schema_rejected(self):
        with pytest.raises(ValidationError):
            Capability(
                name="n",
                description="d",
                output={"type": "object"},
            )

    def test_missing_output_schema_rejected(self):
        with pytest.raises(ValidationError):
            Capability(
                name="n",
                description="d",
                input={"type": "string"},
            )

    def test_model_dump_by_alias(self):
        cap = Capability(
            name="x",
            description="y",
            input={"a": 1},
            output={"b": 2},
        )
        d = cap.model_dump(by_alias=True)
        assert "input" in d
        assert "output" in d
        assert d["input"] == {"a": 1}
        assert d["output"] == {"b": 2}

    def test_model_dump_by_field_name(self):
        cap = Capability(
            name="x",
            description="y",
            input={"a": 1},
            output={"b": 2},
        )
        d = cap.model_dump()
        assert "input_schema" in d
        assert "output_schema" in d


# ============================================================================
# contracts.py — PluginManifest
# ============================================================================


class TestPluginManifest:
    """Tests for PluginManifest Pydantic model."""

    def _make_capability(self, name="cap1"):
        return Capability(
            name=name,
            description="desc",
            input={"type": "string"},
            output={"type": "string"},
        )

    def test_valid_standard_manifest(self):
        m = PluginManifest(
            manifest_version="1.0",
            plugin_name="my_plugin",
            plugin_type="STANDARD",
            version="0.1.0",
            description="A plugin",
            entrypoint="my_plugin.main.MyPlugin",
            capabilities=[self._make_capability()],
        )
        assert m.plugin_type == "STANDARD"
        assert m.dependencies == []
        assert len(m.capabilities) == 1

    def test_valid_workflow_manifest(self):
        m = PluginManifest(
            manifest_version="1.0",
            plugin_name="wf",
            plugin_type="WORKFLOW",
            version="1.0.0",
            description="Workflow",
            entrypoint="wf.main.WF",
            dependencies=["dep1", "dep2"],
            capabilities=[self._make_capability("a"), self._make_capability("b")],
        )
        assert m.plugin_type == "WORKFLOW"
        assert m.dependencies == ["dep1", "dep2"]
        assert len(m.capabilities) == 2

    def test_invalid_plugin_type_rejected(self):
        with pytest.raises(ValidationError):
            PluginManifest(
                manifest_version="1.0",
                plugin_name="p",
                plugin_type="UNKNOWN",
                version="0.1.0",
                description="d",
                entrypoint="e",
                capabilities=[self._make_capability()],
            )

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            PluginManifest(plugin_name="p")


# ============================================================================
# contracts.py — BenchmarkResult
# ============================================================================


class TestBenchmarkResult:
    """Tests for BenchmarkResult Pydantic model."""

    def test_success_result(self):
        r = BenchmarkResult(
            request_id="run-1",
            is_success=True,
            duration_ms=42.5,
            output={"answer": "yes"},
        )
        assert r.is_success is True
        assert r.duration_ms == 42.5
        assert r.error is None
        assert r.custom_metrics == {}

    def test_failure_result(self):
        r = BenchmarkResult(
            request_id="run-2",
            is_success=False,
            duration_ms=10.0,
            error="timeout",
        )
        assert r.is_success is False
        assert r.error == "timeout"
        assert r.output is None

    def test_custom_metrics_default(self):
        r = BenchmarkResult(request_id="r", is_success=True, duration_ms=1.0)
        assert r.custom_metrics == {}


# ============================================================================
# contracts.py — BenchmarkSuiteResult
# ============================================================================


class TestBenchmarkSuiteResult:
    """Tests for BenchmarkSuiteResult Pydantic model."""

    def test_valid_suite_result(self):
        sr = BenchmarkSuiteResult(
            plugin_name="p",
            capability_name="c",
            total_runs=3,
            successful_runs=2,
            failed_runs=1,
            total_duration_ms=100.0,
            average_duration_ms=40.0,
            min_duration_ms=30.0,
            max_duration_ms=50.0,
            results=[
                BenchmarkResult(request_id="r1", is_success=True, duration_ms=30.0),
                BenchmarkResult(request_id="r2", is_success=True, duration_ms=50.0),
                BenchmarkResult(
                    request_id="r3", is_success=False, duration_ms=20.0, error="e"
                ),
            ],
        )
        assert sr.total_runs == 3
        assert sr.successful_runs == 2
        assert sr.failed_runs == 1
        assert sr.aggregated_custom_metrics == {}


# ============================================================================
# plugins/interfaces.py — BasePlugin ABC
# ============================================================================


class TestBasePlugin:
    """Tests for the BasePlugin abstract base class."""

    def test_cannot_instantiate_directly(self):
        """BasePlugin is abstract, but since it has no abstract methods,
        it actually CAN be instantiated. The ABC marker is just a convention."""
        # BasePlugin has `pass` body and no @abstractmethod, so it IS instantiable.
        # This test documents the actual behavior.
        instance = BasePlugin()
        assert isinstance(instance, ABC)

    def test_subclass_is_instance(self):
        class MyPlugin(BasePlugin):
            def do_stuff(self):
                return "done"

        p = MyPlugin()
        assert isinstance(p, BasePlugin)
        assert p.do_stuff() == "done"

    def test_subclass_detected_by_issubclass(self):
        class AnotherPlugin(BasePlugin):
            pass

        assert issubclass(AnotherPlugin, BasePlugin)
        assert AnotherPlugin is not BasePlugin


# ============================================================================
# retrait #2099 — discovery mechanisms without a consumer
# ============================================================================


class TestDiscoveryMechanismsWithdrawn:
    """#2099 : les trois mécanismes de découverte sont retirés, pas réparés.

    Mesuré sur `4c733b93` (base de ce retrait) : aucun des trois modules
    n'avait d'appelant de production — le loader #1 (`core/plugin_loader.py`)
    n'était appelé que par `main.py` et `run_benchmark.py`, deux fossiles du
    même paquet ; le loader #2 (`core/plugins/plugin_loader.py`) et
    `AgentLoader` (`agents/agent_loader.py`) n'étaient appelés que par les
    tests. Les plugins réels rejoignent le système par import direct — garde
    positive dans la classe suivante.
    """

    WITHDRAWN_MODULES = (
        "argumentation_analysis.plugin_framework.core.plugin_loader",
        "argumentation_analysis.plugin_framework.core.plugins.plugin_loader",
        "argumentation_analysis.plugin_framework.agents.agent_loader",
    )

    @pytest.mark.parametrize("module_name", WITHDRAWN_MODULES)
    def test_withdrawn_module_no_longer_imports(self, module_name):
        with pytest.raises(ImportError):
            importlib.import_module(module_name)


class TestRealPluginsByDirectImport:
    """Le chemin vivant survit au retrait : import direct, contrat canonique.

    Né-rouge exécuté avant le fix (#2099 constat 5) :
    `issubclass(TaxonomyExplorerPlugin, BasePlugin)` rendait False — le plugin
    portait une classe `BasePlugin` locale factice. Il importe désormais le
    contrat canonique `core/plugins/interfaces.py`, comme son frère
    `external_verification`.
    """

    def test_taxonomy_explorer_honours_the_canonical_contract(self):
        from argumentation_analysis.plugin_framework.core.plugins.standard.taxonomy_explorer.plugin import (
            TaxonomyExplorerPlugin,
        )

        assert issubclass(TaxonomyExplorerPlugin, BasePlugin)

    async def test_real_plugin_instantiates_and_executes_a_capability(self):
        from argumentation_analysis.plugin_framework.core.plugins.standard.taxonomy_explorer.plugin import (
            TaxonomyExplorerPlugin,
        )

        plugin = TaxonomyExplorerPlugin()
        families = await plugin.list_families()

        assert len(families) > 0
        assert all({"family_id", "name_fr"} <= set(f) for f in families)


# ============================================================================
# orchestration_service.py — OrchestrationService
# ============================================================================


class TestOrchestrationService:
    """Tests for OrchestrationService routing and execution."""

    def _make_service(self, **plugins):
        return OrchestrationService(plugin_registry=plugins)

    def test_direct_plugin_call_success(self):
        plugin = MagicMock()
        plugin.greet.return_value = {"message": "hello"}
        svc = self._make_service(my_plugin=plugin)

        req = OrchestrationRequest(
            mode="direct_plugin_call",
            target="my_plugin.greet",
            payload={"name": "world"},
        )
        resp = svc.handle_request(req)

        assert resp.status == "success"
        assert resp.result == {"message": "hello"}
        plugin.greet.assert_called_once_with(name="world")

    def test_direct_plugin_call_empty_payload(self):
        plugin = MagicMock()
        plugin.do_thing.return_value = {"ok": True}
        svc = self._make_service(p=plugin)

        req = OrchestrationRequest(mode="direct_plugin_call", target="p.do_thing")
        resp = svc.handle_request(req)

        assert resp.status == "success"
        plugin.do_thing.assert_called_once_with()

    def test_missing_plugin_error(self):
        svc = self._make_service()
        req = OrchestrationRequest(mode="direct_plugin_call", target="nonexistent.func")
        resp = svc.handle_request(req)

        assert resp.status == "error"
        assert "non trouv" in resp.error_message

    def test_missing_function_error(self):
        plugin = MagicMock(spec=[])  # Empty spec -> no attributes
        svc = self._make_service(p=plugin)

        req = OrchestrationRequest(mode="direct_plugin_call", target="p.missing_func")
        resp = svc.handle_request(req)

        assert resp.status == "error"
        assert "missing_func" in resp.error_message

    def test_target_without_dot_separator_error(self):
        svc = self._make_service()
        req = OrchestrationRequest(mode="direct_plugin_call", target="no_dot_here")
        resp = svc.handle_request(req)

        assert resp.status == "error"
        # ValueError from split() with not enough values

    def test_target_with_multiple_dots_error(self):
        svc = self._make_service()
        req = OrchestrationRequest(mode="direct_plugin_call", target="a.b.c")
        resp = svc.handle_request(req)

        assert resp.status == "error"
        # ValueError from too many values to unpack

    def test_plugin_function_raises_exception(self):
        plugin = MagicMock()
        plugin.crash.side_effect = RuntimeError("boom")
        svc = self._make_service(my=plugin)

        req = OrchestrationRequest(mode="direct_plugin_call", target="my.crash")
        resp = svc.handle_request(req)

        assert resp.status == "error"
        assert "boom" in resp.error_message

    def test_plugin_function_receives_kwargs(self):
        """Payload is unpacked as keyword arguments."""
        plugin = MagicMock()
        plugin.compute.return_value = {"sum": 3}
        svc = self._make_service(math=plugin)

        req = OrchestrationRequest(
            mode="direct_plugin_call",
            target="math.compute",
            payload={"a": 1, "b": 2},
        )
        svc.handle_request(req)
        plugin.compute.assert_called_once_with(a=1, b=2)

    def test_response_is_orchestration_response_type(self):
        plugin = MagicMock()
        plugin.f.return_value = {}
        svc = self._make_service(p=plugin)
        req = OrchestrationRequest(mode="direct_plugin_call", target="p.f")
        resp = svc.handle_request(req)
        assert isinstance(resp, OrchestrationResponse)


# ============================================================================
# decorators.py — track_tokens
# ============================================================================


class TestTrackTokensDecorator:
    """Tests for the track_tokens decorator."""

    def _make_benchmark_service(self):
        """Create a minimal BenchmarkService mock that records metrics."""
        svc = MagicMock(spec=BenchmarkService)
        svc.recorded = {}

        def record_metric(metric_type, value):
            svc.recorded[metric_type] = value

        svc.record_metric = record_metric
        return svc

    def test_basic_string_input_output(self):
        try:
            import tiktoken
        except ImportError:
            pytest.skip("tiktoken not installed")

        from argumentation_analysis.plugin_framework.core.decorators import track_tokens

        bench_svc = self._make_benchmark_service()

        @track_tokens(bench_svc)
        def echo(text):
            return text

        result = echo("hello world")
        assert result == "hello world"
        assert "input_tokens" in bench_svc.recorded
        assert "output_tokens" in bench_svc.recorded
        assert bench_svc.recorded["input_tokens"] > 0
        assert bench_svc.recorded["output_tokens"] > 0

    def test_dict_input(self):
        try:
            import tiktoken
        except ImportError:
            pytest.skip("tiktoken not installed")

        from argumentation_analysis.plugin_framework.core.decorators import track_tokens

        bench_svc = self._make_benchmark_service()

        @track_tokens(bench_svc)
        def process(data):
            return {"result": "ok"}

        result = process({"key": "some text value"})
        assert result == {"result": "ok"}
        assert bench_svc.recorded["input_tokens"] > 0

    def test_kwargs_string_counted(self):
        try:
            import tiktoken
        except ImportError:
            pytest.skip("tiktoken not installed")

        from argumentation_analysis.plugin_framework.core.decorators import track_tokens

        bench_svc = self._make_benchmark_service()

        @track_tokens(bench_svc)
        def greet(name="default"):
            return "hi"

        greet(name="Alice")
        assert bench_svc.recorded["input_tokens"] > 0

    def test_non_string_args_zero_tokens(self):
        try:
            import tiktoken
        except ImportError:
            pytest.skip("tiktoken not installed")

        from argumentation_analysis.plugin_framework.core.decorators import track_tokens

        bench_svc = self._make_benchmark_service()

        @track_tokens(bench_svc)
        def add(a, b):
            return a + b

        result = add(1, 2)
        assert result == 3
        assert bench_svc.recorded["input_tokens"] == 0

    def test_dict_output_tokens(self):
        try:
            import tiktoken
        except ImportError:
            pytest.skip("tiktoken not installed")

        from argumentation_analysis.plugin_framework.core.decorators import track_tokens

        bench_svc = self._make_benchmark_service()

        @track_tokens(bench_svc)
        def generate():
            return {"text": "generated output text"}

        generate()
        assert bench_svc.recorded["output_tokens"] > 0

    def test_none_output_zero_tokens(self):
        try:
            import tiktoken
        except ImportError:
            pytest.skip("tiktoken not installed")

        from argumentation_analysis.plugin_framework.core.decorators import track_tokens

        bench_svc = self._make_benchmark_service()

        @track_tokens(bench_svc)
        def noop():
            return None

        noop()
        assert bench_svc.recorded["output_tokens"] == 0

    def test_preserves_function_name(self):
        try:
            import tiktoken
        except ImportError:
            pytest.skip("tiktoken not installed")

        from argumentation_analysis.plugin_framework.core.decorators import track_tokens

        bench_svc = self._make_benchmark_service()

        @track_tokens(bench_svc)
        def my_function():
            return "x"

        assert my_function.__name__ == "my_function"


# ============================================================================
# benchmark_service.py — BenchmarkService
# ============================================================================


class TestBenchmarkService:
    """Tests for BenchmarkService.run_suite() and record_metric()."""

    def _make_orchestration_service(self):
        return MagicMock(spec=OrchestrationService)

    def test_record_metric_stores_values(self):
        orch = self._make_orchestration_service()
        bench = BenchmarkService(orch)
        bench.record_metric("latency", 10)
        bench.record_metric("latency", 20)
        assert bench.custom_metrics["latency"] == [10, 20]

    def test_record_metric_multiple_types(self):
        orch = self._make_orchestration_service()
        bench = BenchmarkService(orch)
        bench.record_metric("tokens", 5)
        bench.record_metric("cost", 0.01)
        assert "tokens" in bench.custom_metrics
        assert "cost" in bench.custom_metrics

    def test_clear_metrics(self):
        orch = self._make_orchestration_service()
        bench = BenchmarkService(orch)
        bench.record_metric("x", 1)
        bench._clear_metrics()
        assert bench.custom_metrics == {}

    def test_run_suite_all_success(self):
        orch = self._make_orchestration_service()
        orch.handle_request.return_value = OrchestrationResponse(
            status="success", result={"val": 42}
        )
        bench = BenchmarkService(orch)

        result = bench.run_suite(
            "myplugin",
            "analyze",
            [
                {"text": "hello"},
                {"text": "world"},
            ],
        )

        assert isinstance(result, BenchmarkSuiteResult)
        assert result.plugin_name == "myplugin"
        assert result.capability_name == "analyze"
        assert result.total_runs == 2
        assert result.successful_runs == 2
        assert result.failed_runs == 0
        assert result.average_duration_ms > 0
        assert result.min_duration_ms > 0
        assert result.max_duration_ms >= result.min_duration_ms
        assert len(result.results) == 2

    def test_run_suite_all_failures(self):
        orch = self._make_orchestration_service()
        orch.handle_request.return_value = OrchestrationResponse(
            status="error", error_message="broken"
        )
        bench = BenchmarkService(orch)

        result = bench.run_suite("p", "c", [{"x": 1}])

        assert result.total_runs == 1
        assert result.successful_runs == 0
        assert result.failed_runs == 1
        assert result.average_duration_ms == 0
        assert result.min_duration_ms == 0
        assert result.max_duration_ms == 0

    def test_run_suite_mixed_results(self):
        orch = self._make_orchestration_service()
        responses = [
            OrchestrationResponse(status="success", result={"ok": True}),
            OrchestrationResponse(status="error", error_message="fail"),
            OrchestrationResponse(status="success", result={"ok": True}),
        ]
        orch.handle_request.side_effect = responses
        bench = BenchmarkService(orch)

        result = bench.run_suite("p", "c", [{"a": 1}, {"a": 2}, {"a": 3}])

        assert result.total_runs == 3
        assert result.successful_runs == 2
        assert result.failed_runs == 1

    def test_run_suite_empty_requests(self):
        orch = self._make_orchestration_service()
        bench = BenchmarkService(orch)

        result = bench.run_suite("p", "c", [])

        assert result.total_runs == 0
        assert result.successful_runs == 0
        assert result.failed_runs == 0
        assert result.average_duration_ms == 0
        assert len(result.results) == 0

    def test_run_suite_clears_metrics_before_run(self):
        orch = self._make_orchestration_service()
        orch.handle_request.return_value = OrchestrationResponse(
            status="success", result={}
        )
        bench = BenchmarkService(orch)
        bench.record_metric("stale", 999)

        bench.run_suite("p", "c", [{"x": 1}])

        # Stale metric should not appear in results since _clear_metrics is called
        # The custom_metrics dict itself is cleared
        # But the result's custom_metrics comes from what was recorded DURING the run
        assert all(
            "stale" not in r.custom_metrics
            for r in bench.run_suite("p", "c", [{"x": 1}]).results
        )

    def test_run_suite_request_ids_sequential(self):
        orch = self._make_orchestration_service()
        orch.handle_request.return_value = OrchestrationResponse(
            status="success", result={}
        )
        bench = BenchmarkService(orch)

        result = bench.run_suite("p", "c", [{"a": 1}, {"a": 2}, {"a": 3}])

        assert result.results[0].request_id == "benchmark-run-1"
        assert result.results[1].request_id == "benchmark-run-2"
        assert result.results[2].request_id == "benchmark-run-3"

    def test_run_suite_total_duration(self):
        orch = self._make_orchestration_service()
        orch.handle_request.return_value = OrchestrationResponse(
            status="success", result={}
        )
        bench = BenchmarkService(orch)

        result = bench.run_suite("p", "c", [{"a": 1}, {"a": 2}])

        # Total duration should be sum of all individual durations
        expected_total = sum(r.duration_ms for r in result.results)
        assert abs(result.total_duration_ms - expected_total) < 0.01

    def test_run_suite_constructs_correct_target(self):
        orch = self._make_orchestration_service()
        orch.handle_request.return_value = OrchestrationResponse(
            status="success", result={}
        )
        bench = BenchmarkService(orch)

        bench.run_suite("my_plugin", "my_cap", [{"x": 1}])

        call_args = orch.handle_request.call_args[0][0]
        assert isinstance(call_args, OrchestrationRequest)
        assert call_args.target == "my_plugin.my_cap"
        assert call_args.mode == "direct_plugin_call"

    def test_run_suite_aggregates_numeric_metrics(self):
        """Custom numeric metrics are summed in aggregation."""
        orch = self._make_orchestration_service()
        orch.handle_request.return_value = OrchestrationResponse(
            status="success", result={}
        )
        bench = BenchmarkService(orch)

        # Simulate metric recording during each handle_request call
        call_count = [0]
        original_handle = orch.handle_request

        def handle_with_metrics(req):
            call_count[0] += 1
            bench.record_metric("tokens", call_count[0] * 10)
            return OrchestrationResponse(status="success", result={})

        orch.handle_request.side_effect = handle_with_metrics

        result = bench.run_suite("p", "c", [{"a": 1}, {"a": 2}])

        # tokens: [10, 20] -> sum = 30
        assert result.aggregated_custom_metrics.get("tokens") == 30

    def test_run_suite_metric_attaches_to_its_own_run_not_by_index(self):
        """#2102 §4 : identité explicite métrique↔exécution.

        Né-rouge exécuté avant le fix : le run 1 enregistrait DEUX valeurs et
        le run 2 aucune — la deuxième valeur glissait dans le run 2
        (association par index). Désormais, une valeur enregistrée pendant un
        run appartient à ce run (liste si plusieurs), et un run muet n'emprunte
        jamais la valeur d'un autre.
        """
        orch = self._make_orchestration_service()
        calls = [0]

        def handle_with_metrics(req):
            calls[0] += 1
            if calls[0] == 1:
                bench.record_metric("tokens", 100)
                bench.record_metric("tokens", 200)
            # run 2 : aucune métrique enregistrée
            return OrchestrationResponse(status="success", result={})

        orch.handle_request.side_effect = handle_with_metrics
        bench = BenchmarkService(orch)

        result = bench.run_suite("p", "c", [{"a": 1}, {"a": 2}])

        assert result.results[0].custom_metrics["tokens"] == [100, 200]
        assert "tokens" not in result.results[1].custom_metrics

    def test_recorded_metric_outside_any_run_never_attaches(self):
        """#2102 §4 : une métrique enregistrée hors de tout run reste tamponnée
        dans custom_metrics et n'est attachée à AUCUN run de la suite suivante
        (elle est effacée au départ du run_suite)."""
        orch = self._make_orchestration_service()

        def handle(req):
            return OrchestrationResponse(status="success", result={})

        orch.handle_request.side_effect = handle
        bench = BenchmarkService(orch)
        bench.record_metric("orphan", 7)

        result = bench.run_suite("p", "c", [{"a": 1}])

        assert all("orphan" not in r.custom_metrics for r in result.results)
        assert "orphan" not in result.aggregated_custom_metrics
