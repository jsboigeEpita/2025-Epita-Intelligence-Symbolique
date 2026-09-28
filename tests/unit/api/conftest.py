"""Keep existing API behavior tests independent of the serving auth policy."""

import pytest


@pytest.fixture(autouse=True)
def allow_anonymous_api_in_existing_behavior_tests(monkeypatch):
    # Security tests explicitly remove this opt-in to exercise the closed default.
    monkeypatch.setenv("SHIELD_ALLOW_ANONYMOUS", "1")
    monkeypatch.delenv("SHIELD_ENDPOINT_TOKEN", raising=False)
