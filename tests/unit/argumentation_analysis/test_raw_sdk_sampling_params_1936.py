"""#1936 — raw-SDK callers must consult the central sampling-params policy.

Background: reasoning-model families (gpt-5*, o1*, o3* — including the
production default gpt-5.6-luna) reject temperature/seed and the max_tokens
spelling with a 400 BadRequest. The suppression lived only in
orchestration.invoke_callables._get_determinism_params; raw-SDK callers
outside the orchestrator could not consult it without an adapter→orchestrator
import cycle. The policy now lives in core.llm_service and this file guards
both the call-site behavior and the class-level invariant.
"""

import ast
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[3]
SWEEP_ROOTS = (REPO_ROOT / "argumentation_analysis", REPO_ROOT / "project_core")
SAMPLING_PARAMS = {"temperature", "max_tokens", "seed"}

_DET_ENV_KEYS = (
    "LLM_DETERMINISTIC_MODE",
    "LLM_TEMPERATURE",
    "LLM_SEED",
    "LLM_FORCE_SAMPLING_PARAMS",
    "OPENAI_CHAT_MODEL_ID",
    "OPENROUTER_CHAT_MODEL_ID",
    "OPENROUTER_BASE_URL",
    "OPENROUTER_API_KEY",
)


class _FakeCompletions:
    def __init__(self, captured):
        self._captured = captured

    async def create(self, **kwargs):
        self._captured.update(kwargs)
        content = '{"fallacies": []}'
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


class _FakeChat:
    def __init__(self, captured):
        self.completions = _FakeCompletions(captured)


def _setup_env(monkeypatch, model_id):
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", model_id)
    for key in _DET_ENV_KEYS:
        if key.startswith("LLM_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("LLM_TEMPERATURE", "0.3")


async def _capture_create_kwargs(monkeypatch):
    captured = {}
    # Build a per-call fake class so captures don't leak between tests.
    fake = type(
        "FakeAsyncOpenAI",
        (),
        {"__init__": lambda self, **kw: setattr(self, "chat", _FakeChat(captured))},
    )
    monkeypatch.setattr("openai.AsyncOpenAI", fake)

    from argumentation_analysis.adapters.french_fallacy_adapter import (
        LLMFallacyDetector,
    )

    detector = LLMFallacyDetector(confidence_threshold=0.4)
    await detector.detect_async("Un texte quelconque, sans sophisme.")
    assert not detector.last_degraded, "fake client call must succeed"
    return captured


async def test_detect_async_suppresses_sampling_params_for_reasoning_model(
    monkeypatch,
):
    """luna (reasoning) + LLM_TEMPERATURE asked → temperature/seed suppressed."""
    _setup_env(monkeypatch, "gpt-5.6-luna")
    captured = await _capture_create_kwargs(monkeypatch)

    assert (
        "temperature" not in captured
    ), "reasoning model must not receive temperature (400 risk)"
    assert "seed" not in captured
    assert (
        "max_tokens" not in captured
    ), "reasoning models reject the max_tokens spelling"
    assert captured.get("max_completion_tokens") == 1024
    assert captured["model"] == "gpt-5.6-luna"


async def test_detect_async_keeps_sampling_params_for_non_reasoning_model(
    monkeypatch,
):
    """Negative control: gpt-4o (non-reasoning) + LLM_TEMPERATURE → kept.

    Without this contrast, the suppression test above could not distinguish
    'suppressed by policy' from 'never sends sampling params at all'.
    """
    _setup_env(monkeypatch, "gpt-4o")
    captured = await _capture_create_kwargs(monkeypatch)

    assert captured.get("temperature") == 0.3
    assert "max_tokens" not in captured
    assert captured.get("max_completion_tokens") == 1024


def test_get_determinism_params_model_id_override(monkeypatch):
    """The explicit model_id wins over the env-resolved one, both directions."""
    from argumentation_analysis.core.llm_service import get_determinism_params

    for key in _DET_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")

    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "gpt-4o")
    assert get_determinism_params(model_id="gpt-5.6-luna") == {}

    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "gpt-5.6-luna")
    assert get_determinism_params(model_id="gpt-4o") == {"temperature": 0.2}


def test_invoke_callables_aliases_point_at_central_policy():
    """The orchestration names must be the core policy, not a divergent copy."""
    from argumentation_analysis.core import llm_service
    from argumentation_analysis.orchestration import invoke_callables

    assert (
        invoke_callables._get_determinism_params is llm_service.get_determinism_params
    )
    assert invoke_callables._is_reasoning_model is llm_service.is_reasoning_model
    assert invoke_callables._resolve_model_id is llm_service.resolve_active_model_id


def test_no_literal_sampling_params_on_raw_sdk_create_calls():
    """AST guard: production raw-SDK create() calls must not hardcode sampling
    params — temperature/seed/max_tokens belong to the central policy helper.

    max_completion_tokens is the compliant spelling for token caps and is
    allowed. Non-literal values (config attributes, env-driven dicts) are not
    flagged: this guard targets the regression it can decide statically.
    """
    violations = []
    for root in SWEEP_ROOTS:
        for py in root.rglob("*.py"):
            # utf-8-sig: several production files carry a UTF-8 BOM that
            # plain "utf-8" + ast.parse rejects with a SyntaxError.
            tree = ast.parse(py.read_text(encoding="utf-8-sig"), filename=str(py))
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "create"
                    and isinstance(node.func.value, ast.Attribute)
                    and node.func.value.attr == "completions"
                ):
                    continue
                for kw in node.keywords:
                    if kw.arg in SAMPLING_PARAMS and isinstance(kw.value, ast.Constant):
                        rel = py.relative_to(REPO_ROOT)
                        violations.append(
                            f"{rel}:{node.lineno} {kw.arg}={kw.value.value!r}"
                        )
    assert (
        not violations
    ), "raw-SDK sampling params bypassing the central policy:\n" + "\n".join(violations)
