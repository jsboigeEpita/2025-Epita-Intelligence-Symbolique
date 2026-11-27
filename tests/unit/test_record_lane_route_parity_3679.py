"""The cassette recorder and the replayer hash one route (#3679, asks 2 and 5).

The model id is part of every raw cache key, and the named Anthropic route is
chosen by two environment variables. So the record step of
``record-llm-cassettes.yml`` and the replay job of ``requires_api_band.yml``
must resolve to the same route, or every cassette recorded by the first
misses in the second. This reads both environments from the two workflow
files — never from a copy of them — and checks what each side resolves, what
it hashes, and that one call recorded under the first replays under the
second.

Key material is not part of a key: the recorder holds the secret and the
replayer a dummy, and each side keeps its own value here.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict

import pytest
import yaml

from argumentation_analysis.core.endpoint_compat import (
    classify_json_provider,
    json_response_format,
    sampling_kwargs,
)
from argumentation_analysis.core.llm_service import (
    create_llm_service,
    resolve_chat_endpoint,
)
from argumentation_analysis.services.llm_cache import (
    LLMCacheMiss,
    cached_raw_chat_completion,
    compute_cache_key,
    compute_raw_cache_key,
    reset_raw_cache,
)
from semantic_kernel.connectors.ai.open_ai import OpenAIPromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

ROOT = Path(__file__).resolve().parents[2]
RECORD_YML = ROOT / ".github" / "workflows" / "record-llm-cassettes.yml"
BAND_YML = ROOT / ".github" / "workflows" / "requires_api_band.yml"

PYTEST_CALL = "--no-capture-output pytest "

# Every variable the two route resolvers read to choose a route and a model id.
ROUTE_VARIABLES = (
    "ANTHROPIC_CHAT_MODEL_ID",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "OPENROUTER_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_CHAT_MODEL_ID",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_CHAT_MODEL_ID",
)
# Variables that change what a call asks for — hence its key — without
# choosing a route. A knob set on one side only would separate the two keys.
KNOB_VARIABLES = (
    "LLM_REASONING_EFFORT",
    "LLM_ANTHROPIC_THINKING",
    "LLM_ENABLE_THINKING",
    "LLM_DETERMINISTIC_MODE",
    "LLM_TEMPERATURE",
    "LLM_SEED",
    "LLM_FORCE_SAMPLING_PARAMS",
)
# The opt-in declared-route guard (#2322). Neither job declares a route; the
# seat running this file might.
GUARD_VARIABLES = ("LLM_EXPECTED_ROUTE",)
# The two secrets of the record lane. Each is a real key there (a reference
# to the repository secret) and a dummy on the replay side.
KEY_VARIABLES = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")

MESSAGES = [{"role": "user", "content": "one request"}]
SECRET_REFERENCE = re.compile(r"^\$\{\{\s*secrets\.[A-Z0-9_]+\s*\}\}$")


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _env_of(node: dict) -> Dict[str, str]:
    return {name: str(value) for name, value in (node.get("env") or {}).items()}


def _record_env() -> Dict[str, str]:
    """Env of the record step: the one job, the step with ``id: record``."""
    steps = _load(RECORD_YML)["jobs"]["record"]["steps"]
    (step,) = [step for step in steps if step.get("id") == "record"]
    return _env_of(step)


def _live_env() -> Dict[str, str]:
    return _env_of(_load(BAND_YML)["jobs"]["requires-api"])


def _replay_env() -> Dict[str, str]:
    """Env of the replay band's pytest step: the job's, completed by the step's."""
    job = _load(BAND_YML)["jobs"]["replay-band"]
    (step,) = [step for step in job["steps"] if PYTEST_CALL in step.get("run", "")]
    return {**_env_of(job), **_env_of(step)}


def _apply(monkeypatch, env: Dict[str, str]) -> None:
    """Make the process see ``env`` for every route and knob variable.

    Everything else the seat holds is removed first: an ambient key must
    never stand in for the value under test.
    """
    for name in ROUTE_VARIABLES + KNOB_VARIABLES + GUARD_VARIABLES + ("OPENAI_ORG_ID",):
        monkeypatch.delenv(name, raising=False)
    for name in ROUTE_VARIABLES + KNOB_VARIABLES:
        if name in env:
            # A reference to a repository secret becomes a placeholder of the
            # same role; a literal (the replayer's dummy) stays as written.
            monkeypatch.setenv(name, SECRET_REFERENCE.sub("not-a-key", env[name]))


def _sides():
    return (("record", _record_env()), ("replay", _replay_env()))


# --- What the two files say -------------------------------------------------


def test_the_record_step_selects_the_named_route_of_the_live_band():
    record, live = _record_env(), _live_env()
    assert record.get("ANTHROPIC_CHAT_MODEL_ID") == live.get("ANTHROPIC_CHAT_MODEL_ID")
    assert record.get("ANTHROPIC_CHAT_MODEL_ID", "").startswith("claude-")
    assert record.get("LLM_CACHE_MODE") == "record"


def test_the_replay_job_selects_that_route_with_nothing_real_to_call():
    record, replay = _record_env(), _replay_env()
    assert replay.get("ANTHROPIC_CHAT_MODEL_ID") == record.get(
        "ANTHROPIC_CHAT_MODEL_ID"
    )
    assert replay.get("LLM_CACHE_MODE") == "replay"


@pytest.mark.parametrize("name", KEY_VARIABLES)
def test_the_recorder_holds_a_secret_reference(name):
    value = _record_env().get(name, "")
    assert SECRET_REFERENCE.match(value), f"record step: {name}={value!r}"


@pytest.mark.parametrize("name", KEY_VARIABLES)
def test_the_replayer_holds_a_dummy_written_in_the_file(name):
    value = _replay_env().get(name, "")
    assert value.strip(), f"replay job: {name} is absent or empty"
    assert "${{" not in value, f"replay job: {name}={value!r} is a secret reference"


@pytest.mark.parametrize(
    "name",
    tuple(v for v in ROUTE_VARIABLES if v not in KEY_VARIABLES)
    + KNOB_VARIABLES
    + GUARD_VARIABLES,
)
def test_no_other_route_or_knob_variable_is_set_on_one_side_only(name):
    record, replay = _record_env(), _replay_env()
    assert record.get(name) == replay.get(
        name
    ), f"{name}: record={record.get(name)!r} replay={replay.get(name)!r}"


# --- What the two environments resolve and hash -----------------------------


def test_the_resolver_returns_one_route_under_both_environments(monkeypatch):
    resolved = {}
    for side, env in _sides():
        _apply(monkeypatch, env)
        _key, base_url, model_id = resolve_chat_endpoint()
        resolved[side] = (base_url, model_id)
    assert resolved["record"] == resolved["replay"]
    assert resolved["record"][1] == _record_env()["ANTHROPIC_CHAT_MODEL_ID"]


def test_the_named_route_decides_the_model_id_not_the_openai_one(monkeypatch):
    """Neither job sets ``OPENAI_CHAT_MODEL_ID``; on the named route it is inert."""
    model_id = _replay_env()["ANTHROPIC_CHAT_MODEL_ID"]
    for extra in ({}, {"OPENAI_CHAT_MODEL_ID": "another-model"}):
        _apply(monkeypatch, {**_replay_env(), **extra})
        assert resolve_chat_endpoint()[2] == model_id


def _wire_decisions(monkeypatch, env: Dict[str, str]):
    """What the wire-compat table (#3096) decides under ``env``.

    ``response_format`` and ``temperature`` are in the raw key, and the table
    is read from the base URL of the route.
    """
    _apply(monkeypatch, env)
    base_url = resolve_chat_endpoint()[1]
    return (
        classify_json_provider(base_url),
        json_response_format(base_url, "s", {"type": "object"}),
        json_response_format(base_url),
        sampling_kwargs(base_url, {"temperature": 0.3, "seed": 42}),
    )


def test_the_wire_decisions_are_the_same_on_both_sides(monkeypatch):
    decisions = {side: _wire_decisions(monkeypatch, env) for side, env in _sides()}
    assert decisions["record"] == decisions["replay"]


def test_the_wire_decisions_follow_the_route_the_control(monkeypatch):
    """Why the test above is a witness: another route reads another row."""
    both = _wire_decisions(monkeypatch, _replay_env())
    other = _wire_decisions(monkeypatch, {name: "dummy" for name in KEY_VARIABLES})
    assert other != both


def _service_model_id(monkeypatch, env: Dict[str, str]) -> str:
    _apply(monkeypatch, env)
    service = create_llm_service(force_authentic=True)
    # In record and replay mode the factory returns the cache wrapper.
    inner = getattr(service, "_inner", service)
    return inner.ai_model_id


def test_the_kernel_path_service_carries_the_same_model_id_under_both_environments(
    monkeypatch,
):
    model_id = _record_env()["ANTHROPIC_CHAT_MODEL_ID"]
    for _side, env in _sides():
        assert _service_model_id(monkeypatch, env) == model_id


def test_one_call_hashes_the_same_under_both_environments(monkeypatch):
    raw_keys, kernel_keys = {}, {}
    for side, env in _sides():
        _apply(monkeypatch, env)
        model_id = resolve_chat_endpoint()[2]
        raw_keys[side] = compute_raw_cache_key(
            model=model_id, messages=MESSAGES, max_completion_tokens=1024
        )
        history = ChatHistory()
        history.add_message(ChatMessageContent(role="user", content="one request"))
        kernel_keys[side] = compute_cache_key(
            history,
            OpenAIPromptExecutionSettings(
                ai_model_id=_service_model_id(monkeypatch, env)
            ),
        )
    assert raw_keys["record"] == raw_keys["replay"]
    assert kernel_keys["record"] == kernel_keys["replay"]


# --- One call, recorded on one side, replayed on the other ------------------


class _FakeClient:
    """Stand-in for an OpenAI client. Counts chat.completions.create calls."""

    def __init__(self, content: str):
        from openai.types.chat import ChatCompletion, ChatCompletionMessage
        from openai.types.chat.chat_completion import Choice

        self._content = content
        self.calls = 0

        async def _create(**kwargs):
            self.calls += 1
            return ChatCompletion(
                id="chatcmpl-x",
                object="chat.completion",
                created=1700000000,
                model=kwargs.get("model", "m"),
                choices=[
                    Choice(
                        index=0,
                        message=ChatCompletionMessage(
                            role="assistant", content=self._content
                        ),
                        finish_reason="stop",
                    )
                ],
            )

        self.chat = type("C", (), {})()
        self.chat.completions = type("P", (), {})()
        self.chat.completions.create = _create


@pytest.fixture
def isolated_raw_cache(tmp_path: Path, monkeypatch):
    """One cache directory per test, and no open handle left behind."""
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path))
    reset_raw_cache()
    yield tmp_path
    reset_raw_cache()


async def test_a_call_recorded_under_the_record_environment_replays_under_the_replay_one(
    monkeypatch, isolated_raw_cache
):
    with monkeypatch.context() as record_side:
        record_env = _record_env()
        _apply(record_side, record_env)
        record_side.setenv("LLM_CACHE_MODE", record_env["LLM_CACHE_MODE"])
        reset_raw_cache()
        recorder = _FakeClient("recorded")
        await cached_raw_chat_completion(
            recorder,
            model=resolve_chat_endpoint()[2],
            messages=MESSAGES,
            max_completion_tokens=1024,
        )
        assert recorder.calls == 1

    with monkeypatch.context() as replay_side:
        replay_env = _replay_env()
        _apply(replay_side, replay_env)
        replay_side.setenv("LLM_CACHE_MODE", replay_env["LLM_CACHE_MODE"])
        reset_raw_cache()
        try:
            replayer = _FakeClient("live")
            # The replayer reads the model id from its own environment.
            served = await cached_raw_chat_completion(
                replayer,
                model=resolve_chat_endpoint()[2],
                messages=MESSAGES,
                max_completion_tokens=1024,
            )
            assert served.choices[0].message.content == "recorded"
            assert replayer.calls == 0  # served by the cassette, never by a call
        finally:
            reset_raw_cache()


async def test_the_same_call_under_another_route_misses_the_control(
    monkeypatch, isolated_raw_cache
):
    """Why the parity above matters: the model id is in the key.

    Same request, replayed under the route without the named model id — the
    shape the two jobs had before #3679 — and there is no cassette for it.
    """
    with monkeypatch.context() as record_side:
        record_env = _record_env()
        _apply(record_side, record_env)
        record_side.setenv("LLM_CACHE_MODE", record_env["LLM_CACHE_MODE"])
        reset_raw_cache()
        await cached_raw_chat_completion(
            _FakeClient("recorded"),
            model=resolve_chat_endpoint()[2],
            messages=MESSAGES,
            max_completion_tokens=1024,
        )

    with monkeypatch.context() as replay_side:
        _apply(replay_side, {name: "dummy" for name in KEY_VARIABLES})
        replay_side.setenv("LLM_CACHE_MODE", "replay")
        reset_raw_cache()
        try:
            assert (
                resolve_chat_endpoint()[2] != _record_env()["ANTHROPIC_CHAT_MODEL_ID"]
            )
            with pytest.raises(LLMCacheMiss, match="Raw cache miss in replay mode"):
                await cached_raw_chat_completion(
                    _FakeClient("live"),
                    model=resolve_chat_endpoint()[2],
                    messages=MESSAGES,
                    max_completion_tokens=1024,
                )
        finally:
            reset_raw_cache()
