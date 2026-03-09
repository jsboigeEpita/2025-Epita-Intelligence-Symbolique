"""Tests for WebSocket routes.

Validates:
- WebSocket connection on all 3 channels (analysis, debate, deliberation)
- Ping/pong keepalive
- Clean disconnect handling
"""
import pytest
from starlette.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


class TestWebSocketAnalysis:
    def test_connect_and_ping(self, client):
        with client.websocket_connect("/ws/analysis/test-session") as ws:
            ws.send_text("ping")
            data = ws.receive_json()
            assert data["type"] == "pong"

    def test_disconnect(self, client):
        with client.websocket_connect("/ws/analysis/sess-1") as ws:
            ws.send_text("ping")
            ws.receive_json()
        # No exception means clean disconnect


class TestWebSocketDebate:
    def test_connect_and_ping(self, client):
        with client.websocket_connect("/ws/debate/debate-1") as ws:
            ws.send_text("ping")
            data = ws.receive_json()
            assert data["type"] == "pong"


class TestWebSocketDeliberation:
    def test_connect_and_ping(self, client):
        with client.websocket_connect("/ws/deliberation/delib-1") as ws:
            ws.send_text("ping")
            data = ws.receive_json()
            assert data["type"] == "pong"
