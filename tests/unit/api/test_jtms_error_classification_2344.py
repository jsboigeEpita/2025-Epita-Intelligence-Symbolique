# -*- coding: utf-8 -*-
"""#2344 family (c) — jtms_endpoints: a server defect is not a client error.

Every handler of the module used to map ANY exception to HTTP 400 (the
client's fault): the ``NotImplementedError`` of the graphml export path,
an internal ``AttributeError``, a broken plugin — all surfaced as if the
caller had sent a bad request. Provenance rules (#1019): the service marks
client input — the requested entity or format does not exist — with the
named ``JTMSClientInputError`` (a ``ValueError`` subclass), which stays 400;
anything else, including ``ValueError``-shaped server defects (a ``KeyError``
on the handler's own dict read, a ``ValidationError``, a
``JSONDecodeError``), is a server defect and must surface as 500. The hourly
expired-session cleanup loop swallowed each failure in
``except Exception: pass`` — a permanently broken cleanup was invisible;
its failures are now named in a warning, and the loop survives them.
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from argumentation_analysis.api import jtms_endpoints
from argumentation_analysis.api.jtms_endpoints import jtms_router
from argumentation_analysis.services.jtms_service import JTMSService
from argumentation_analysis.services.jtms_session_manager import JTMSSessionManager


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(jtms_router, prefix="/api/v1")
    return application


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _restore_module_globals():
    """The lazy DI getters REASSIGN the module globals mid-request, so a test
    that patches one global can leave an orphan in another (e.g. a session
    manager built on a broken service). Snapshot and restore all three."""
    saved = (
        jtms_endpoints._jtms_service,
        jtms_endpoints._session_manager,
        jtms_endpoints._sk_plugin,
    )
    yield
    (
        jtms_endpoints._jtms_service,
        jtms_endpoints._session_manager,
        jtms_endpoints._sk_plugin,
    ) = saved


def _real_service_with_instance():
    """A REAL service holding a REAL instance — no mock on the export path."""
    service = JTMSService()
    instance_id = asyncio.run(service.create_jtms_instance("session_2344"))
    return service, instance_id


class TestServerDefectsAreInternalErrors:
    """Provenance: anything but a client-input error is a 500 (#2344)."""

    def test_notimplemented_export_path_is_500(self, client):
        """The real service raises NotImplementedError for graphml export —
        a missing server feature is not the caller's fault."""
        service, instance_id = _real_service_with_instance()
        with patch.object(jtms_endpoints, "_jtms_service", service):
            response = client.post(
                "/api/v1/jtms/export",
                json={"instance_id": instance_id, "format": "graphml"},
            )
        assert (
            response.status_code == 500
        ), "NotImplementedError is a server defect and must not surface as 400"
        assert response.json()["detail"]["error_type"] == "NotImplementedError"

    def test_internal_bug_is_500(self, client):
        """An AttributeError inside the handler chain is a server defect."""
        broken = MagicMock()
        broken.create_belief = AsyncMock(side_effect=AttributeError("server bug"))
        with patch.object(jtms_endpoints, "_jtms_service", broken):
            response = client.post(
                "/api/v1/jtms/beliefs",
                json={
                    "belief_name": "b",
                    "session_id": "s",
                    "instance_id": "i",
                    "agent_id": "a",
                },
            )
        assert (
            response.status_code == 500
        ), "an internal AttributeError must not surface as a client error"
        assert response.json()["detail"]["error_type"] == "AttributeError"

    def test_sk_endpoint_server_defect_is_500(self, client):
        """The /sk/* convenience endpoints share the same provenance rule."""
        broken_plugin = MagicMock()
        broken_plugin.create_belief = AsyncMock(side_effect=TypeError("boom"))
        with patch.object(jtms_endpoints, "_sk_plugin", broken_plugin):
            response = client.post(
                "/api/v1/jtms/sk/create_belief",
                params={"belief_name": "b"},
            )
        assert (
            response.status_code == 500
        ), "a TypeError in the SK plugin is a server defect, not a 400"
        assert response.json()["detail"]["error_type"] == "TypeError"

    def test_handler_dict_read_is_500(self, client):
        """Review round 2 probe: the service returning a dict WITHOUT the
        handler's expected key is a server contract defect — the KeyError
        raised by result["name"] is not the caller's fault."""
        broken = MagicMock()
        broken.create_belief = AsyncMock(return_value={})
        with patch.object(jtms_endpoints, "_jtms_service", broken):
            response = client.post(
                "/api/v1/jtms/beliefs",
                json={
                    "belief_name": "b",
                    "session_id": "s",
                    "instance_id": "i",
                    "agent_id": "a",
                },
            )
        assert (
            response.status_code == 500
        ), "a KeyError on the handler's own dict read is a server defect, not a 400"
        assert response.json()["detail"]["error_type"] == "KeyError"

    def test_handler_response_construction_is_500(self, client):
        """Review round 2 probe: the service returning well-named but wrongly
        typed fields breaks the handler's pydantic construction — a
        ValidationError (a ValueError subclass) is a server defect here."""
        broken = MagicMock()
        broken.create_belief = AsyncMock(
            return_value={
                "name": "b",
                "valid": "not-a-bool",
                "non_monotonic": "not-a-bool",
                "justifications_count": "not-an-int",
                "implications_count": "not-an-int",
            }
        )
        with patch.object(jtms_endpoints, "_jtms_service", broken):
            response = client.post(
                "/api/v1/jtms/beliefs",
                json={
                    "belief_name": "b",
                    "session_id": "s",
                    "instance_id": "i",
                    "agent_id": "a",
                },
            )
        assert (
            response.status_code == 500
        ), "a pydantic ValidationError on the response body is a server defect, not a 400"
        assert response.json()["detail"]["error_type"] == "ValidationError"

    def test_sk_non_json_result_is_500(self, client):
        """Review round 2 probe: a plugin returning a non-JSON string breaks
        the handler's json.loads — a JSONDecodeError (a ValueError subclass)
        is a server defect, not a 400."""
        broken_plugin = MagicMock()
        broken_plugin.create_belief = AsyncMock(return_value="not json at all")
        with patch.object(jtms_endpoints, "_sk_plugin", broken_plugin):
            response = client.post(
                "/api/v1/jtms/sk/create_belief",
                params={"belief_name": "b"},
            )
        assert (
            response.status_code == 500
        ), "a JSONDecodeError on the plugin result is a server defect, not a 400"
        assert response.json()["detail"]["error_type"] == "JSONDecodeError"


class TestClientInputStays400:
    """Anti-pendulum: the legitimate 400s keep their meaning."""

    def test_unknown_session_is_still_400(self, client):
        """A unknown session id is client input — the named type stays 400."""
        service = JTMSService()
        manager = JTMSSessionManager(service)
        with patch.object(jtms_endpoints, "_jtms_service", service), patch.object(
            jtms_endpoints, "_session_manager", manager
        ):
            response = client.post(
                "/api/v1/jtms/beliefs",
                json={
                    "belief_name": "b",
                    "session_id": "does_not_exist",
                    "agent_id": "a",
                },
            )
        assert (
            response.status_code == 400
        ), "an unknown session is a client-input error and must stay 400"
        assert (
            response.json()["detail"]["error_type"] == "JTMSClientInputError"
        ), "the service marks client input with the named type (a ValueError subclass)"


class TestCleanupNamesItsFailures:
    """The hourly cleanup loop no longer swallows failures in silence."""

    def test_cleanup_failure_is_logged_and_loop_survives(self, caplog):
        manager = MagicMock()
        manager.cleanup_expired_sessions = AsyncMock(
            side_effect=RuntimeError("db gone")
        )
        with caplog.at_level(
            logging.WARNING, logger="argumentation_analysis.api.jtms_endpoints"
        ):
            with patch(
                "argumentation_analysis.api.jtms_endpoints.asyncio.sleep",
                new=AsyncMock(side_effect=[None, asyncio.CancelledError()]),
            ):
                with pytest.raises(asyncio.CancelledError):
                    asyncio.run(jtms_endpoints._expired_session_cleanup_loop(manager))
        warnings = [
            r
            for r in caplog.records
            if r.levelno == logging.WARNING and "db gone" in r.getMessage()
        ]
        assert (
            warnings
        ), "a failing cleanup tick must be named in a warning, not passed silently"
        assert manager.cleanup_expired_sessions.await_count >= 1
