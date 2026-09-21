"""#2322 (route-assertable tranche) — the declared canonical route is
ASSERTED at resolution time, never silently divergent.

The measured failure mode: a lane carrying only ``OPENAI_API_KEY`` resolves
to api.openai.com; with a reasoning model, every function-tools call 400s
(``reasoning_effort``) — forty scattered failures instead of one named
error. ``LLM_EXPECTED_ROUTE`` is the opt-in declaration: when a run declares
its canonical route, ``resolve_chat_endpoint`` (and every site funnelling
through ``_log_resolved_llm_config``) must refuse a divergent resolution by
RAISING ``LLMRouteDivergenceError`` naming both sides. The guard never
reroutes — fix the environment or the declaration.

Born-red: on pre-guard main, the divergent test fails because no such error
exists / nothing raises — the silent pass IS the defect. The error class is
imported INSIDE the born-red test (per the new-symbol né-rouge convention)
so the file's other tests stay meaningful on main.
"""

import pytest

from argumentation_analysis.core.llm_service import (
    _log_resolved_llm_config,
    resolve_chat_endpoint,
)

_ROUTE_VARS = (
    "OPENROUTER_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_CHAT_MODEL_ID",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_CHAT_MODEL_ID",
    "LLM_EXPECTED_ROUTE",
)


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _ROUTE_VARS:
        monkeypatch.delenv(var, raising=False)


def test_divergent_route_raises_named_error(monkeypatch):
    """THE guard — declared openrouter, environment resolves openai ⇒ the
    exact #2322 divergence raises with both routes named."""
    from argumentation_analysis.core.llm_service import (  # local: né-rouge
        LLMRouteDivergenceError,
    )

    _clean_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    monkeypatch.setenv("LLM_EXPECTED_ROUTE", "openrouter")

    with pytest.raises(LLMRouteDivergenceError) as excinfo:
        resolve_chat_endpoint()
    msg = str(excinfo.value)
    assert "declared=openrouter" in msg and "resolved=openai" in msg
    assert "api.openai.com" in msg  # the endpoint the lane actually hit


def test_matching_route_passes(monkeypatch):
    """Declared route matches the pinned environment ⇒ resolution proceeds."""
    _clean_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    monkeypatch.setenv("OPENROUTER_CHAT_MODEL_ID", "gpt-5.6-luna")
    monkeypatch.setenv("LLM_EXPECTED_ROUTE", "openrouter:gpt-5.6-luna")

    api_key, base_url, model_id = resolve_chat_endpoint()

    assert api_key == "sk-or-x"
    assert "openrouter" in base_url
    assert model_id == "gpt-5.6-luna"


def test_undeclared_is_a_noop(monkeypatch):
    """No declaration ⇒ behavior unchanged (local runs on any route)."""
    _clean_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")

    api_key, base_url, _model = resolve_chat_endpoint()  # must not raise

    assert api_key == "sk-x"
    assert "api.openai.com" in base_url


def test_empty_declaration_warns_not_raises(monkeypatch):
    """Empty string ≠ absent (#2281): WARNING, no assertion."""
    _clean_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    monkeypatch.setenv("LLM_EXPECTED_ROUTE", "")

    resolve_chat_endpoint()  # must not raise


def test_model_mismatch_raises(monkeypatch):
    """Provider matches but the declared model does not ⇒ named divergence."""
    from argumentation_analysis.core.llm_service import LLMRouteDivergenceError

    _clean_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    monkeypatch.setenv("OPENROUTER_CHAT_MODEL_ID", "gpt-5.6-luna")
    monkeypatch.setenv("LLM_EXPECTED_ROUTE", "openrouter:gpt-5-mini")

    with pytest.raises(LLMRouteDivergenceError) as excinfo:
        resolve_chat_endpoint()
    assert "model declared=gpt-5-mini" in str(excinfo.value)
    assert "resolved=gpt-5.6-luna" in str(excinfo.value)


def test_log_funnel_asserts(monkeypatch):
    """The funnel every resolution site shares carries the guard — a direct
    call with a divergent environment raises (covers create_llm_service's
    site without going through its pytest mock gate)."""
    from argumentation_analysis.core.llm_service import LLMRouteDivergenceError

    _clean_env(monkeypatch)
    monkeypatch.setenv("LLM_EXPECTED_ROUTE", "openrouter")

    with pytest.raises(LLMRouteDivergenceError):
        _log_resolved_llm_config(
            "sk-x", "https://api.openai.com/v1", "gpt-5.6-luna", "OPENAI_API_KEY"
        )
