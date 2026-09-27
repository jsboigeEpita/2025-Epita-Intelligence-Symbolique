# -*- coding: utf-8 -*-
"""Fixtures shared by the orchestration tests."""

import pytest

# #2711 A2: the service manager asks the route resolver whether an LLM route
# exists (``resolve_chat_endpoint``), and the resolver reads the environment.
# A test's seat is therefore the environment, not ``settings.openai``.
_ROUTE_VARS = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "LLM_EXPECTED_ROUTE",
)


@pytest.fixture
def llm_route_seat(monkeypatch):
    """Return ``seat(openai_key=None, openrouter_key=None)``.

    Clears every route variable, then sets the keys given. An OpenRouter key
    also sets ``OPENROUTER_BASE_URL``, since the resolver's toggle needs both.
    """

    def seat(openai_key=None, openrouter_key=None):
        for var in _ROUTE_VARS:
            monkeypatch.delenv(var, raising=False)
        if openai_key:
            monkeypatch.setenv("OPENAI_API_KEY", openai_key)
        if openrouter_key:
            monkeypatch.setenv("OPENROUTER_API_KEY", openrouter_key)
            monkeypatch.setenv(
                "OPENROUTER_BASE_URL", "https://openrouter.example.test/api/v1"
            )

    return seat
