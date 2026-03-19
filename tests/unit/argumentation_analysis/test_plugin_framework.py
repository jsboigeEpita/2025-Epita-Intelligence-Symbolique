"""
Comprehensive unit tests for the argumentation_analysis/plugin_framework/ module.

Tests cover:
- core/contracts.py — Pydantic models (OrchestrationRequest, OrchestrationResponse,
  Capability, PluginManifest, BenchmarkResult, BenchmarkSuiteResult)
- core/plugins/interfaces.py — BasePlugin ABC
- core/plugin_loader.py — PluginLoader discovery
- core/services/orchestration_service.py — OrchestrationService routing
- core/decorators.py — track_tokens decorator
- benchmarking/benchmark_service.py — BenchmarkService suite runner
- agents/agent_loader.py — AgentLoader discovery and loading
"""

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
from argumentation_analysis.plugin_framework.core.plugin_loader import PluginLoader
from argumentation_analysis.plugin_framework.core.services.orchestration_service import (
    OrchestrationService,
)
from argumentation_analysis.plugin_framework.benchmarking.benchmark_service import (
    BenchmarkService,
)
from argumentation_analysis.plugin_framework.agents.agent_loader import AgentLoader

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

    def test_valid_workflow_execution(self):
        req = OrchestrationRequest(
            mode="workflow_execution",
            target="my_workflow",
            payload={"key": "value"},
            session_id="sess-123",
        )
        assert req.mode == "workflow_execution"
        assert req.payload == {"key": "value"}
        assert req.session_id == "sess-123"

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
# plugin_loader.py — PluginLoader
# ============================================================================


class TestPluginLoader:
    """Tests for PluginLoader.discover()."""

    def test_nonexistent_path_skipped(self, tmp_path):
        loader = PluginLoader([str(tmp_path / "nonexistent")])
        result = loader.discover()
        assert result == {}

    def test_empty_directory(self, tmp_path):
        loader = PluginLoader([str(tmp_path)])
        result = loader.discover()
        assert result == {}

    def test_file_in_directory_ignored(self, tmp_path):
        """Only subdirectories are scanned, not files."""
        (tmp_path / "somefile.py").write_text("x = 1")
        loader = PluginLoader([str(tmp_path)])
        result = loader.discover()
        assert result == {}

    def test_import_error_handled_gracefully(self, tmp_path):
        """Subdirectory exists but import fails -> no crash, empty registry."""
        subdir = tmp_path / "myplugin"
        subdir.mkdir()
        loader = PluginLoader([str(tmp_path)])
        # The import will fail because module src.core.plugins.standard.myplugin doesn't exist
        result = loader.discover()
        assert result == {}

    def test_discover_valid_plugin_via_mock(self, tmp_path):
        """Mock importlib.import_module to return a module with a BasePlugin subclass."""
        subdir = tmp_path / "test_plugin"
        subdir.mkdir()

        class FakePlugin(BasePlugin):
            pass

        # Set __module__ to match what PluginLoader expects
        FakePlugin.__module__ = "src.core.plugins.standard.test_plugin"

        fake_module = MagicMock()
        fake_module.__name__ = "src.core.plugins.standard.test_plugin"
        # Make inspect.getmembers find our class
        fake_module.FakePlugin = FakePlugin

        with patch(
            "argumentation_analysis.plugin_framework.core.plugin_loader.importlib.import_module"
        ) as mock_import:
            mock_import.return_value = fake_module

            # We need inspect.getmembers to work on our mock module
            with patch(
                "argumentation_analysis.plugin_framework.core.plugin_loader.inspect.getmembers"
            ) as mock_members:
                mock_members.return_value = [("FakePlugin", FakePlugin)]

                loader = PluginLoader([str(tmp_path)])
                result = loader.discover()

        assert "FakePlugin" in result
        assert isinstance(result["FakePlugin"], FakePlugin)

    def test_base_plugin_itself_not_registered(self, tmp_path):
        """BasePlugin class itself should not be registered even if found."""
        subdir = tmp_path / "base_mod"
        subdir.mkdir()

        fake_module = MagicMock()

        with patch(
            "argumentation_analysis.plugin_framework.core.plugin_loader.importlib.import_module"
        ) as mock_import:
            mock_import.return_value = fake_module
            with patch(
                "argumentation_analysis.plugin_framework.core.plugin_loader.inspect.getmembers"
            ) as mock_members:
                # Return BasePlugin itself — should be filtered out
                bp = BasePlugin
                bp.__module__ = "src.core.plugins.standard.base_mod"
                mock_members.return_value = [("BasePlugin", bp)]

                loader = PluginLoader([str(tmp_path)])
                result = loader.discover()

        assert "BasePlugin" not in result

    def test_multiple_paths(self, tmp_path):
        """Loader handles multiple plugin paths."""
        path1 = tmp_path / "dir1"
        path2 = tmp_path / "dir2"
        path1.mkdir()
        path2.mkdir()
        loader = PluginLoader([str(path1), str(path2)])
        result = loader.discover()
        assert result == {}

    def test_duplicate_plugin_not_overwritten(self, tmp_path):
        """First discovered plugin with a given name wins."""
        subdir1 = tmp_path / "plug1"
        subdir1.mkdir()
        subdir2 = tmp_path / "plug2"
        subdir2.mkdir()

        class FakePlugin(BasePlugin):
            pass

        FakePlugin.__module__ = "src.core.plugins.standard.plug1"

        class FakePlugin2(BasePlugin):
            pass

        # Same class name but different module
        FakePlugin2.__name__ = "FakePlugin"
        FakePlugin2.__module__ = "src.core.plugins.standard.plug2"

        with patch(
            "argumentation_analysis.plugin_framework.core.plugin_loader.importlib.import_module"
        ) as mock_import:
            with patch(
                "argumentation_analysis.plugin_framework.core.plugin_loader.inspect.getmembers"
            ) as mock_members:
                call_count = [0]

                def side_effect_import(name):
                    m = MagicMock()
                    return m

                def side_effect_members(module, predicate=None):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        return [("FakePlugin", FakePlugin)]
                    return [("FakePlugin", FakePlugin2)]

                mock_import.side_effect = side_effect_import
                mock_members.side_effect = side_effect_members

                loader = PluginLoader([str(tmp_path)])
                result = loader.discover()

        assert "FakePlugin" in result
        # Should be first instance (FakePlugin, not FakePlugin2)
        assert type(result["FakePlugin"]) is FakePlugin


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

    def test_workflow_execution_not_supported(self):
        svc = self._make_service()
        req = OrchestrationRequest(mode="workflow_execution", target="wf1")
        resp = svc.handle_request(req)

        assert resp.status == "error"
        assert "n'est pas support" in resp.error_message

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


# ============================================================================
# agents/agent_loader.py — AgentLoader
# ============================================================================


class TestAgentLoader:
    """Tests for AgentLoader.discover_agents() and load_agent()."""

    def test_discover_nonexistent_path(self, tmp_path):
        loader = AgentLoader()
        result = loader.discover_agents(str(tmp_path / "nonexistent"))
        assert result == []

    def test_discover_empty_directory(self, tmp_path):
        loader = AgentLoader()
        result = loader.discover_agents(str(tmp_path))
        assert result == []

    def test_discover_single_manifest(self, tmp_path):
        agent_dir = tmp_path / "my_agent"
        agent_dir.mkdir()
        manifest_file = agent_dir / "agent_manifest.json"
        manifest_file.write_text("{}")

        loader = AgentLoader()
        result = loader.discover_agents(str(tmp_path))
        assert len(result) == 1
        assert str(manifest_file) == result[0]

    def test_discover_nested_manifests(self, tmp_path):
        """os.walk finds manifests in nested subdirectories."""
        d1 = tmp_path / "a" / "b"
        d1.mkdir(parents=True)
        (d1 / "agent_manifest.json").write_text("{}")

        d2 = tmp_path / "c"
        d2.mkdir()
        (d2 / "agent_manifest.json").write_text("{}")

        loader = AgentLoader()
        result = loader.discover_agents(str(tmp_path))
        assert len(result) == 2

    def test_discover_ignores_non_manifest_files(self, tmp_path):
        (tmp_path / "other.json").write_text("{}")
        (tmp_path / "manifest.json").write_text("{}")  # Wrong name

        loader = AgentLoader()
        result = loader.discover_agents(str(tmp_path))
        assert result == []

    def test_load_agent_valid_manifest(self, tmp_path):
        manifest_data = {
            "manifest_version": "1.0",
            "agent_name": "test_agent",
            "version": "0.1.0",
            "entry_point": "test_agent.main.TestAgent",
        }
        path = tmp_path / "agent_manifest.json"
        path.write_text(json.dumps(manifest_data))

        loader = AgentLoader()
        result = loader.load_agent(str(path))
        assert result is not None
        assert result["agent_name"] == "test_agent"
        assert result["manifest_version"] == "1.0"

    def test_load_agent_missing_file(self, tmp_path):
        loader = AgentLoader()
        result = loader.load_agent(str(tmp_path / "nonexistent.json"))
        assert result is None

    def test_load_agent_invalid_json(self, tmp_path):
        path = tmp_path / "agent_manifest.json"
        path.write_text("not valid json {{{")

        loader = AgentLoader()
        result = loader.load_agent(str(path))
        assert result is None

    def test_load_agent_missing_required_keys(self, tmp_path):
        """Manifest with missing required keys returns None."""
        manifest_data = {
            "manifest_version": "1.0",
            "agent_name": "incomplete",
            # Missing 'version' and 'entry_point'
        }
        path = tmp_path / "agent_manifest.json"
        path.write_text(json.dumps(manifest_data))

        loader = AgentLoader()
        result = loader.load_agent(str(path))
        assert result is None

    def test_load_agent_extra_keys_accepted(self, tmp_path):
        """Manifest with extra keys is still valid."""
        manifest_data = {
            "manifest_version": "1.0",
            "agent_name": "agent",
            "version": "1.0.0",
            "entry_point": "agent.main.Agent",
            "extra_field": "bonus",
        }
        path = tmp_path / "agent_manifest.json"
        path.write_text(json.dumps(manifest_data))

        loader = AgentLoader()
        result = loader.load_agent(str(path))
        assert result is not None
        assert result["extra_field"] == "bonus"

    def test_load_agent_empty_json_object(self, tmp_path):
        """Empty JSON object has no required keys -> returns None."""
        path = tmp_path / "agent_manifest.json"
        path.write_text("{}")

        loader = AgentLoader()
        result = loader.load_agent(str(path))
        assert result is None

    def test_discover_and_load_integration(self, tmp_path):
        """End-to-end: discover then load."""
        agent_dir = tmp_path / "my_agent"
        agent_dir.mkdir()
        manifest_data = {
            "manifest_version": "1.0",
            "agent_name": "my_agent",
            "version": "2.0.0",
            "entry_point": "my_agent.main.MyAgent",
        }
        manifest_path = agent_dir / "agent_manifest.json"
        manifest_path.write_text(json.dumps(manifest_data))

        loader = AgentLoader()
        discovered = loader.discover_agents(str(tmp_path))
        assert len(discovered) == 1

        loaded = loader.load_agent(discovered[0])
        assert loaded is not None
        assert loaded["agent_name"] == "my_agent"
