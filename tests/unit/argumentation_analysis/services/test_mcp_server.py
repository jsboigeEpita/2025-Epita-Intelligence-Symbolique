"""
Unit tests for argumentation_analysis/services/mcp_server/main.py
and related modules (session_manager, tools/_serialization, tools/*).

Targets: raise coverage from ~38% to 60%+.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch, PropertyMock

import pytest

# ---------------------------------------------------------------------------
# 1. safe_serialize tests
# ---------------------------------------------------------------------------


class TestSafeSerialize:
    """Tests for _serialization.safe_serialize."""

    def _get_safe_serialize(self):
        from argumentation_analysis.services.mcp_server.tools._serialization import (
            safe_serialize,
        )

        return safe_serialize

    def test_none(self):
        ss = self._get_safe_serialize()
        assert ss(None) is None

    def test_primitives(self):
        ss = self._get_safe_serialize()
        assert ss("hello") == "hello"
        assert ss(42) == 42
        assert ss(3.14) == 3.14
        assert ss(True) is True

    def test_dict(self):
        ss = self._get_safe_serialize()
        result = ss({"a": 1, "b": "two"})
        assert result == {"a": 1, "b": "two"}

    def test_nested_dict(self):
        ss = self._get_safe_serialize()
        result = ss({"outer": {"inner": [1, 2, 3]}})
        assert result == {"outer": {"inner": [1, 2, 3]}}

    def test_dict_with_non_string_keys(self):
        ss = self._get_safe_serialize()
        result = ss({1: "one", 2: "two"})
        assert result == {"1": "one", "2": "two"}

    def test_list(self):
        ss = self._get_safe_serialize()
        assert ss([1, "a", None]) == [1, "a", None]

    def test_tuple(self):
        ss = self._get_safe_serialize()
        assert ss((1, 2, 3)) == [1, 2, 3]

    def test_set(self):
        ss = self._get_safe_serialize()
        result = ss({3, 1, 2})
        assert result == [1, 2, 3]

    def test_enum(self):
        ss = self._get_safe_serialize()

        class Color(Enum):
            RED = "red"
            GREEN = "green"

        assert ss(Color.RED) == "red"

    def test_dataclass(self):
        ss = self._get_safe_serialize()

        @dataclass
        class Point:
            x: int
            y: int

        result = ss(Point(x=10, y=20))
        assert result == {"x": 10, "y": 20}

    def test_nested_dataclass(self):
        ss = self._get_safe_serialize()

        @dataclass
        class Inner:
            val: str

        @dataclass
        class Outer:
            child: Inner
            items: list

        result = ss(Outer(child=Inner(val="hi"), items=[1, 2]))
        assert result == {"child": {"val": "hi"}, "items": [1, 2]}

    def test_unknown_type_to_str(self):
        ss = self._get_safe_serialize()

        class Custom:
            def __str__(self):
                return "custom_obj"

        assert ss(Custom()) == "custom_obj"

    def test_complex_nested(self):
        ss = self._get_safe_serialize()

        class Status(Enum):
            ACTIVE = "active"

        result = ss({"status": Status.ACTIVE, "tags": {"a", "b"}, "data": (1, 2)})
        assert result["status"] == "active"
        assert result["tags"] == ["a", "b"]
        assert result["data"] == [1, 2]


# ---------------------------------------------------------------------------
# 2. SessionManager tests
# ---------------------------------------------------------------------------


class TestSessionManager:
    """Tests for session_manager.SessionManager."""

    def _make_manager(self, **kwargs):
        from argumentation_analysis.services.mcp_server.session_manager import (
            SessionManager,
        )

        return SessionManager(**kwargs)

    def test_create_session_returns_state(self):
        sm = self._make_manager()
        session = sm.create_session("some text", workflow_name="light")
        assert session.text == "some text"
        assert session.workflow_name == "light"
        assert session.session_id is not None
        assert session.conversation_history == []

    def test_create_session_with_config(self):
        sm = self._make_manager()
        cfg = {"max_rounds": 5, "threshold": 0.9}
        session = sm.create_session("txt", config=cfg)
        assert session.config == cfg

    def test_get_session_found(self):
        sm = self._make_manager()
        s = sm.create_session("hello")
        retrieved = sm.get_session(s.session_id)
        assert retrieved is not None
        assert retrieved.session_id == s.session_id

    def test_get_session_not_found(self):
        sm = self._make_manager()
        assert sm.get_session("nonexistent") is None

    def test_get_session_expired(self):
        sm = self._make_manager(ttl_seconds=1)
        s = sm.create_session("hello")
        # Force expiry by manipulating last_accessed
        s.last_accessed = time.time() - 10
        result = sm.get_session(s.session_id)
        assert result is None

    def test_update_session_appends_history(self):
        sm = self._make_manager()
        s = sm.create_session("text")
        result = sm.update_session(s.session_id, {"round": 1, "status": "ok"})
        assert result is True
        assert len(s.conversation_history) == 1
        assert s.conversation_history[0]["round"] == 1

    def test_update_session_nonexistent(self):
        sm = self._make_manager()
        assert sm.update_session("bad_id", {}) is False

    def test_delete_session(self):
        sm = self._make_manager()
        s = sm.create_session("text")
        assert sm.delete_session(s.session_id) is True
        assert sm.get_session(s.session_id) is None

    def test_delete_session_nonexistent(self):
        sm = self._make_manager()
        assert sm.delete_session("no_such") is False

    def test_list_sessions(self):
        sm = self._make_manager()
        sm.create_session("a")
        sm.create_session("b", workflow_name="full")
        result = sm.list_sessions()
        assert len(result) == 2
        workflows = {s["workflow"] for s in result}
        assert "standard" in workflows
        assert "full" in workflows

    def test_list_sessions_filters_expired(self):
        sm = self._make_manager(ttl_seconds=1)
        s1 = sm.create_session("a")
        s2 = sm.create_session("b")
        # Expire s1
        s1.last_accessed = time.time() - 10
        result = sm.list_sessions()
        assert len(result) == 1
        assert result[0]["session_id"] == s2.session_id

    def test_max_sessions_evicts_oldest(self):
        sm = self._make_manager(max_sessions=2)
        s1 = sm.create_session("first")
        s2 = sm.create_session("second")
        # Make s1 the oldest
        s1.last_accessed = time.time() - 100
        s2.last_accessed = time.time() - 50
        s3 = sm.create_session("third")
        # s1 should be evicted
        assert sm.get_session(s1.session_id) is None
        assert sm.get_session(s2.session_id) is not None
        assert sm.get_session(s3.session_id) is not None

    def test_cleanup_expired_removes_old(self):
        sm = self._make_manager(ttl_seconds=1)
        s = sm.create_session("old")
        s.last_accessed = time.time() - 10
        sm._cleanup_expired()
        assert len(sm._sessions) == 0

    def test_session_state_defaults(self):
        from argumentation_analysis.services.mcp_server.session_manager import (
            SessionState,
        )

        ss = SessionState(
            session_id="test",
            created_at=1.0,
            last_accessed=1.0,
            text="hello",
        )
        assert ss.workflow_name == "standard"
        assert ss.conversation_history == []
        assert ss.state is None
        assert ss.config == {}
        assert ss.metadata == {}


# ---------------------------------------------------------------------------
# 3. AppServices tests
# ---------------------------------------------------------------------------


class TestAppServices:
    """Tests for main.AppServices.

    #1864 : les cinq doubles de classes sont autospec'és. Avant, un Mock nu
    acceptait n'importe quel constructeur et répondait à n'importe quelle
    méthode — la suite restait verte au-dessus d'un conteneur inconstructible
    (TypeError : llm_service) et d'un dict de santé appelant is_healthy() sur
    un service qui ne l'exposait pas. Le spec fait rougir les deux.
    """

    @patch(
        "argumentation_analysis.services.mcp_server.main.FrameworkService",
        autospec=True,
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.FallacyService", autospec=True
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.ValidationService",
        autospec=True,
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.AnalysisService", autospec=True
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.LogicService", autospec=True
    )
    def test_init_creates_services(
        self, mock_logic, mock_analysis, mock_validation, mock_fallacy, mock_framework
    ):
        from argumentation_analysis.services.mcp_server.main import AppServices

        app = AppServices()
        mock_logic.assert_called_once()
        mock_analysis.assert_called_once()
        mock_validation.assert_called_once_with(mock_logic.return_value)
        mock_fallacy.assert_called_once()
        mock_framework.assert_called_once()
        # Né-rouge #1864 : sur l'arbre d'avant, ce même AppServices() levait
        # "TypeError: LogicService.__init__() missing 1 required positional
        # argument: 'llm_service'" — c'est le spec qui l'a rendu visible.
        for mock_cls in (mock_logic, mock_analysis):
            assert "llm_service" in mock_cls.call_args.kwargs

    @patch(
        "argumentation_analysis.services.mcp_server.main.FrameworkService",
        autospec=True,
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.FallacyService", autospec=True
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.ValidationService",
        autospec=True,
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.AnalysisService", autospec=True
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.LogicService", autospec=True
    )
    @patch("argumentation_analysis.services.mcp_server.main.create_llm_service")
    def test_init_wires_llm_services(
        self,
        mock_llm_factory,
        mock_logic,
        mock_analysis,
        mock_validation,
        mock_fallacy,
        mock_framework,
    ):
        """Contrôle dédié du câblage : un service LLM par consommateur, en
        miroir du conteneur de l'API Web (l'app Flask archivée)."""
        from argumentation_analysis.services.mcp_server.main import AppServices

        logic_llm, analysis_llm = object(), object()
        mock_llm_factory.side_effect = [logic_llm, analysis_llm]

        AppServices()

        assert [c.kwargs["service_id"] for c in mock_llm_factory.call_args_list] == [
            "logic_service",
            "analysis_service",
        ]
        assert mock_logic.call_args.kwargs["llm_service"] is logic_llm
        assert mock_analysis.call_args.kwargs["llm_service"] is analysis_llm
        assert mock_validation.call_args.args == (mock_logic.return_value,)

    @patch(
        "argumentation_analysis.services.mcp_server.main.FrameworkService",
        autospec=True,
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.FallacyService", autospec=True
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.ValidationService",
        autospec=True,
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.AnalysisService", autospec=True
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.LogicService", autospec=True
    )
    @patch("argumentation_analysis.services.mcp_server.main.jpype")
    def test_is_healthy_jvm_running(
        self,
        mock_jpype,
        mock_logic,
        mock_analysis,
        mock_validation,
        mock_fallacy,
        mock_framework,
    ):
        mock_jpype.isJVMStarted.return_value = True
        for m in [
            mock_logic,
            mock_analysis,
            mock_validation,
            mock_fallacy,
            mock_framework,
        ]:
            # Le contrat réel des services frères est un bool (#1864) — pas
            # le dict {"status": "ok"} que l'ancien Mock nu fabriquait.
            m.return_value.is_healthy.return_value = True

        from argumentation_analysis.services.mcp_server.main import AppServices

        app = AppServices()
        health = app.is_healthy()
        assert health["jvm"]["running"] is True
        assert health["jvm"]["status"] == "OK"
        # Né-rouge #1864 (2e couche) : sur l'arbre d'avant, l'accès à
        # mock_framework.return_value.is_healthy levait AttributeError —
        # la vraie classe ne l'exposait pas ; le double la fabriquait.
        assert health["framework"] is True
        assert health["logic"] is True

    @patch(
        "argumentation_analysis.services.mcp_server.main.FrameworkService",
        autospec=True,
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.FallacyService", autospec=True
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.ValidationService",
        autospec=True,
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.AnalysisService", autospec=True
    )
    @patch(
        "argumentation_analysis.services.mcp_server.main.LogicService", autospec=True
    )
    @patch("argumentation_analysis.services.mcp_server.main.jpype")
    def test_is_healthy_jvm_not_running(
        self,
        mock_jpype,
        mock_logic,
        mock_analysis,
        mock_validation,
        mock_fallacy,
        mock_framework,
    ):
        mock_jpype.isJVMStarted.return_value = False
        for m in [
            mock_logic,
            mock_analysis,
            mock_validation,
            mock_fallacy,
            mock_framework,
        ]:
            m.return_value.is_healthy.return_value = False

        from argumentation_analysis.services.mcp_server.main import AppServices

        app = AppServices()
        health = app.is_healthy()
        assert health["jvm"]["running"] is False
        assert health["jvm"]["status"] == "Not Running"
        assert health["framework"] is False


# ---------------------------------------------------------------------------
# 4. MCPService tests — tool methods
# ---------------------------------------------------------------------------


def _make_mcp_service():
    """Create an MCPService with all heavy dependencies mocked."""
    with patch(
        "argumentation_analysis.services.mcp_server.main.MCPServer"
    ) as mock_fmcp, patch(
        "argumentation_analysis.services.mcp_server.main.initialize_project_environment"
    ), patch(
        "argumentation_analysis.services.mcp_server.main.AppServices"
    ) as mock_app, patch(
        "argumentation_analysis.services.mcp_server.main.jpype"
    ) as mock_jpype, patch.dict(
        "sys.modules",
        {
            "argumentation_analysis.services.mcp_server.tools.workflow_tools": MagicMock(),
            "argumentation_analysis.services.mcp_server.tools.conversation_tools": MagicMock(),
            "argumentation_analysis.services.mcp_server.tools.capability_tools": MagicMock(),
            "argumentation_analysis.services.mcp_server.tools.specialized_tools": MagicMock(),
        },
    ):
        mock_fmcp.return_value = MagicMock()
        mock_jpype.isJVMStarted.return_value = True
        mock_app.return_value = MagicMock()
        from argumentation_analysis.services.mcp_server.main import MCPService

        svc = MCPService("test_mcp")
    return svc


class TestMCPServiceInit:
    """Tests for MCPService initialization."""

    def test_init_sets_attributes(self):
        svc = _make_mcp_service()
        assert svc._initialized is True
        assert svc.services is not None

    def test_init_failure_raises_runtime_error(self):
        with patch(
            "argumentation_analysis.services.mcp_server.main.MCPServer"
        ) as mock_fmcp, patch(
            "argumentation_analysis.services.mcp_server.main.initialize_project_environment",
            side_effect=Exception("init failed"),
        ):
            mock_fmcp.return_value = MagicMock()
            from argumentation_analysis.services.mcp_server.main import MCPService

            with pytest.raises(RuntimeError, match="init failed"):
                MCPService("failing_mcp")

    def test_v2_tools_failure_is_silent(self):
        """V2 tool registration failure should not crash init."""
        with patch(
            "argumentation_analysis.services.mcp_server.main.MCPServer"
        ) as mock_fmcp, patch(
            "argumentation_analysis.services.mcp_server.main.initialize_project_environment"
        ), patch(
            "argumentation_analysis.services.mcp_server.main.AppServices"
        ), patch(
            "argumentation_analysis.services.mcp_server.main.jpype"
        ):
            mock_fmcp.return_value = MagicMock()
            # Make v2 imports fail
            import builtins

            original_import = builtins.__import__

            def failing_import(name, *args, **kwargs):
                if (
                    "workflow_tools" in name
                    or "conversation_tools" in name
                    or "capability_tools" in name
                    or "specialized_tools" in name
                ):
                    raise ImportError("no v2")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=failing_import):
                from argumentation_analysis.services.mcp_server.main import MCPService

                svc = MCPService("test_no_v2")
                # Should not raise
                assert svc._initialized is True


class TestMCPServiceHealthCheck:
    """Tests for MCPService.health_check."""

    async def test_health_check_healthy(self):
        svc = _make_mcp_service()
        svc.services.is_healthy.return_value = {"all": "ok"}
        with patch(
            "argumentation_analysis.services.mcp_server.main.jpype"
        ) as mock_jpype:
            mock_jpype.isJVMStarted.return_value = True
            result = await svc.health_check()
        assert result["status"] == "healthy"
        assert "services" in result

    async def test_health_check_unhealthy(self):
        svc = _make_mcp_service()
        svc.services.is_healthy.return_value = {"all": "ok"}
        with patch(
            "argumentation_analysis.services.mcp_server.main.jpype"
        ) as mock_jpype:
            mock_jpype.isJVMStarted.return_value = False
            result = await svc.health_check()
        assert result["status"] == "unhealthy"

    async def test_health_check_error(self):
        svc = _make_mcp_service()
        svc.services.is_healthy.side_effect = Exception("boom")
        with patch(
            "argumentation_analysis.services.mcp_server.main.jpype"
        ) as mock_jpype:
            mock_jpype.isJVMStarted.return_value = True
            result = await svc.health_check()
        assert result["status"] == "error"
        assert "boom" in result["message"]


class TestMCPServiceAnalyzeText:
    """Tests for MCPService.analyze_text."""

    async def test_analyze_text_success(self):
        svc = _make_mcp_service()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"analysis": "done"}
        svc.services.analysis_service.analyze_text = AsyncMock(return_value=mock_result)
        result = await svc.analyze_text("Some argument text")
        assert result == {"analysis": "done"}

    async def test_analyze_text_validation_error(self):
        svc = _make_mcp_service()
        from pydantic import ValidationError

        # Trigger validation error via invalid severity_threshold
        # We mock the AnalysisRequest to raise
        with patch(
            "argumentation_analysis.services.mcp_server.main.AnalysisRequest",
            side_effect=ValidationError.from_exception_data(
                title="AnalysisRequest",
                line_errors=[
                    {
                        "type": "string_type",
                        "loc": ("text",),
                        "msg": "bad",
                        "input": None,
                        "ctx": {},
                    }
                ],
            ),
        ):
            result = await svc.analyze_text("test")
        assert result["status_code"] == 400

    async def test_analyze_text_runtime_error(self):
        svc = _make_mcp_service()
        svc.services.analysis_service.analyze_text = AsyncMock(
            side_effect=RuntimeError("service down")
        )
        result = await svc.analyze_text("test")
        assert result["status_code"] == 500
        assert "service down" in result["message"]


class TestMCPServiceValidateArgument:
    """Tests for MCPService.validate_argument."""

    async def test_validate_argument_success(self):
        svc = _make_mcp_service()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"valid": True}
        svc.services.validation_service.validate_argument = AsyncMock(
            return_value=mock_result
        )
        result = await svc.validate_argument(
            premises=["All A are B", "X is A"],
            conclusion="X is B",
        )
        assert result == {"valid": True}

    async def test_validate_argument_error(self):
        svc = _make_mcp_service()
        svc.services.validation_service.validate_argument = AsyncMock(
            side_effect=Exception("fail")
        )
        result = await svc.validate_argument(["p1"], "c1")
        assert result["status_code"] == 500


class TestMCPServiceDetectFallacies:
    """Tests for MCPService.detect_fallacies."""

    async def test_detect_fallacies_success(self):
        svc = _make_mcp_service()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"fallacies": []}
        svc.services.fallacy_service.detect_fallacies = AsyncMock(
            return_value=mock_result
        )
        result = await svc.detect_fallacies("some text")
        assert result == {"fallacies": []}

    async def test_detect_fallacies_error(self):
        svc = _make_mcp_service()
        svc.services.fallacy_service.detect_fallacies = AsyncMock(
            side_effect=Exception("detection failed")
        )
        result = await svc.detect_fallacies("text")
        assert result["status_code"] == 500


class TestMCPServiceBuildFramework:
    """Tests for MCPService.build_framework.

    #1864 : repointés sur la surface réelle — analyze_dung_framework(ids,
    paires), synchrone, dict brut. L'ancien double fabriquait
    build_framework(FrameworkRequest), la méthode fantôme.
    """

    def _spec_services(self, svc):
        from argumentation_analysis.services.web_api.services.framework_service import (
            FrameworkService,
        )

        # Spec sur le double qui décide : une instance spec'ée de la vraie
        # classe refuse build_framework (méthode fantôme) et expose
        # analyze_dung_framework — un Mock nu fabriquait les deux.
        framework = create_autospec(FrameworkService, instance=True)
        svc.services.framework_service = framework
        return framework

    async def test_build_framework_success(self):
        svc = _make_mcp_service()
        framework = self._spec_services(svc)
        framework.analyze_dung_framework.return_value = {"extensions": [["a1"]]}
        args = [
            {"id": "a1", "content": "arg1", "attacks": ["a2"], "supports": []},
            {"id": "a2", "content": "arg2"},
        ]
        result = await svc.build_framework(args)
        assert result == {"extensions": [["a1"]]}
        framework.analyze_dung_framework.assert_called_once_with(
            ["a1", "a2"], [["a1", "a2"]]
        )

    async def test_build_framework_error(self):
        svc = _make_mcp_service()
        framework = self._spec_services(svc)
        framework.analyze_dung_framework.side_effect = Exception("fw fail")
        result = await svc.build_framework([{"id": "a1", "content": "x"}])
        assert result["status_code"] == 500

    async def test_build_framework_rejects_too_many_arguments(self):
        svc = _make_mcp_service()
        framework = self._spec_services(svc)
        args = [{"id": f"a{i}", "content": "c"} for i in range(3)]
        result = await svc.build_framework(args, max_arguments=2)
        assert result["status_code"] == 400
        framework.analyze_dung_framework.assert_not_called()


class TestFrameworkServiceAnalyzeDung:
    """#1864 : couverture minimale de FrameworkService.analyze_dung_framework —
    la seule surface vivante du service, jusque-là sans aucun test (le serveur
    MCP qui la consomme ne pouvait même pas se construire). JVM-free : le pont
    est doublé dans l'espace de nom du module, aucune JVM n'est démarrée.
    """

    def _make_service(self, bridge):
        from argumentation_analysis.services.web_api.services import framework_service

        with patch.object(framework_service, "TweetyBridge") as mock_bridge_cls:
            mock_bridge_cls.get_instance.return_value = bridge
            return framework_service.FrameworkService()

    def _make_degraded_service(self):
        from argumentation_analysis.services.web_api.services import framework_service

        with patch.object(framework_service, "TweetyBridge") as mock_bridge_cls:
            mock_bridge_cls.get_instance.side_effect = RuntimeError("no jvm")
            return framework_service.FrameworkService()

    def test_forwards_to_af_handler(self):
        bridge = MagicMock()
        expected = {"status": "preferred", "extensions": [["a1"]]}
        bridge.af_handler.analyze_dung_framework.return_value = expected

        svc = self._make_service(bridge)
        result = svc.analyze_dung_framework(["a1", "a2"], [["a1", "a2"]])

        assert result is expected
        bridge.af_handler.analyze_dung_framework.assert_called_once_with(
            arguments=["a1", "a2"], attacks=[["a1", "a2"]], semantics="preferred"
        )

    def test_bridge_construction_failed_returns_error_payload(self):
        svc = self._make_degraded_service()
        result = svc.analyze_dung_framework(["a1"], [])
        assert result["status_code"] == 500
        assert "TweetyBridge" in result["error"]

    def test_handler_failure_returns_error_payload(self):
        bridge = MagicMock()
        bridge.af_handler.analyze_dung_framework.side_effect = RuntimeError("jvm down")

        svc = self._make_service(bridge)
        result = svc.analyze_dung_framework(["a1"], [])
        assert result["status_code"] == 500

    def test_is_healthy_reflects_bridge_state(self):
        assert self._make_service(MagicMock()).is_healthy() is True
        assert self._make_degraded_service().is_healthy() is False


class TestMCPServiceLogicGraph:
    """Tests for MCPService.logic_graph."""

    async def test_logic_graph_success(self):
        svc = _make_mcp_service()
        result = await svc.logic_graph("Some logical text")
        assert "graph" in result
        assert "svg" in result["graph"]

    async def test_logic_graph_empty_text(self):
        svc = _make_mcp_service()
        result = await svc.logic_graph("")
        assert result["status_code"] == 400
        assert "vide" in result["error"].lower() or "vide" in result["message"].lower()

    async def test_logic_graph_whitespace_only(self):
        svc = _make_mcp_service()
        result = await svc.logic_graph("   ")
        assert result["status_code"] == 400


class TestMCPServiceLogicTools:
    """Tests for logic-related MCP tools."""

    async def test_create_belief_set_success(self):
        svc = _make_mcp_service()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"belief_set_id": "bs1"}
        svc.services.logic_service.create_belief_set = AsyncMock(
            return_value=mock_result
        )
        result = await svc.create_belief_set("p => q", "propositional")
        assert result == {"belief_set_id": "bs1"}

    async def test_create_belief_set_error(self):
        svc = _make_mcp_service()
        svc.services.logic_service.create_belief_set = AsyncMock(
            side_effect=Exception("fail")
        )
        result = await svc.create_belief_set("text", "propositional")
        assert result["status_code"] == 500

    async def test_execute_logic_query_success(self):
        svc = _make_mcp_service()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"answer": True}
        svc.services.logic_service.execute_query = AsyncMock(return_value=mock_result)
        result = await svc.execute_logic_query("bs1", "p", "propositional")
        assert result == {"answer": True}

    async def test_execute_logic_query_error(self):
        svc = _make_mcp_service()
        svc.services.logic_service.execute_query = AsyncMock(
            side_effect=Exception("query fail")
        )
        result = await svc.execute_logic_query("bs1", "p", "propositional")
        assert result["status_code"] == 500

    async def test_generate_logic_queries_success(self):
        svc = _make_mcp_service()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"queries": ["q1"]}
        svc.services.logic_service.generate_queries = AsyncMock(
            return_value=mock_result
        )
        result = await svc.generate_logic_queries("bs1", "text", "first_order")
        assert result == {"queries": ["q1"]}

    async def test_generate_logic_queries_error(self):
        svc = _make_mcp_service()
        svc.services.logic_service.generate_queries = AsyncMock(
            side_effect=Exception("gen fail")
        )
        result = await svc.generate_logic_queries("bs1", "text", "modal")
        assert result["status_code"] == 500


class TestMCPServiceListTools:
    """Tests for MCPService.list_available_tools."""

    async def test_list_tools_returns_all(self):
        svc = _make_mcp_service()
        result = await svc.list_available_tools()
        assert result["version"] == "2.0.0"
        assert result["total_tools"] == 23
        assert "health_check" in result["tools"]
        assert "run_workflow" in result["tools"]
        assert "evaluate_quality" in result["tools"]


class TestMCPServiceRegistryAndSession:
    """Tests for _ensure_registry and _get_session_manager."""

    def test_ensure_registry_lazy_init(self):
        svc = _make_mcp_service()
        svc._registry = None
        mock_registry = MagicMock()
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.setup_registry",
            return_value=mock_registry,
        ):
            result = svc._ensure_registry()
        assert result is mock_registry
        assert svc._registry is mock_registry

    def test_ensure_registry_cached(self):
        svc = _make_mcp_service()
        sentinel = object()
        svc._registry = sentinel
        result = svc._ensure_registry()
        assert result is sentinel

    def test_get_session_manager_lazy_init(self):
        svc = _make_mcp_service()
        svc._session_manager = None
        with patch(
            "argumentation_analysis.services.mcp_server.session_manager.SessionManager"
        ) as mock_sm_cls:
            mock_sm_cls.return_value = MagicMock()
            result = svc._get_session_manager()
        assert result is not None
        assert svc._session_manager is not None

    def test_get_session_manager_cached(self):
        svc = _make_mcp_service()
        sentinel = object()
        svc._session_manager = sentinel
        result = svc._get_session_manager()
        assert result is sentinel


class TestMCPServiceRun:
    """Tests for MCPService.run."""

    def test_run_delegates_to_mcp(self):
        svc = _make_mcp_service()
        svc.run("stdio")
        # mcp 2.x (#1559): host/port now flow through run() (moved out of the
        # ctor). stdio ignores them server-side, but the delegation contract
        # forwards them regardless of transport.
        svc.mcp.run.assert_called_once_with(
            transport="stdio", host="0.0.0.0", port=8000
        )


# ---------------------------------------------------------------------------
# 5. Tool registration module tests (workflow, capability, specialized, conversation)
# ---------------------------------------------------------------------------


class TestWorkflowToolsRegistration:
    """Tests for workflow_tools.register_workflow_tools."""

    def test_registers_three_tools(self):
        from argumentation_analysis.services.mcp_server.tools.workflow_tools import (
            register_workflow_tools,
        )

        mock_mcp = MagicMock()
        mock_mcp.tool.return_value = lambda fn: fn
        register_workflow_tools(mock_mcp, MagicMock())
        assert mock_mcp.tool.call_count == 3


class TestCapabilityToolsRegistration:
    """Tests for capability_tools.register_capability_tools."""

    def test_registers_three_tools(self):
        from argumentation_analysis.services.mcp_server.tools.capability_tools import (
            register_capability_tools,
        )

        mock_mcp = MagicMock()
        mock_mcp.tool.return_value = lambda fn: fn
        register_capability_tools(mock_mcp, MagicMock())
        assert mock_mcp.tool.call_count == 3


class TestSpecializedToolsRegistration:
    """Tests for specialized_tools.register_specialized_tools."""

    def test_registers_four_tools(self):
        from argumentation_analysis.services.mcp_server.tools.specialized_tools import (
            register_specialized_tools,
        )

        mock_mcp = MagicMock()
        mock_mcp.tool.return_value = lambda fn: fn
        register_specialized_tools(mock_mcp, MagicMock())
        assert mock_mcp.tool.call_count == 4


class TestConversationToolsRegistration:
    """Tests for conversation_tools.register_conversation_tools."""

    def test_registers_three_tools(self):
        from argumentation_analysis.services.mcp_server.tools.conversation_tools import (
            register_conversation_tools,
        )

        mock_mcp = MagicMock()
        mock_mcp.tool.return_value = lambda fn: fn
        register_conversation_tools(mock_mcp, MagicMock(), MagicMock())
        assert mock_mcp.tool.call_count == 3
