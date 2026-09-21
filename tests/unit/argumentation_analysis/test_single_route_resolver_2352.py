"""#2352 — ONE LLM route resolver in production; the copies CALL it.

The audit measured six resolvers for one route, four diverging. The repair is
**delegation**, not a shared helper pasted into five files: every migrated site
calls :func:`resolve_chat_endpoint` and nothing else re-implements the
OpenRouter toggle.

Two divergence classes, both measured on the seat ``.env.example`` prescribes
(only ``OPENAI_CHAT_MODEL_ID`` is set, so ``OPENROUTER_CHAT_MODEL_ID`` is
absent — the normal case for that seat, and the case where the copies broke):

- **A — missing jump**: the two mirrors read ``OPENROUTER_CHAT_MODEL_ID`` and
  fell to a hardcoded literal instead of ``OPENAI_CHAT_MODEL_ID``, so they never
  saw the prescribed seat's model and never applied the #1930 obsolescence
  table (measured: ``gpt-5-mini`` where the canonical resolver renders
  ``gpt-5.6-luna``);
- **B — provider-prefixed literal**: three sites defaulted to
  ``openai/gpt-5.6-luna``, a string no resolver returns — divergent in *every*
  configuration where ``OPENROUTER_CHAT_MODEL_ID`` is absent, obsolescence or
  not.

These tests import **no post-repair symbol at module level**, so the né-rouge
on pre-repair main is a *model value* failure, never an ``ImportError``. They
own every route env var, so no inherited ``.env`` can make a case pass by
accident. The last test measures the file text rather than the call graph: the
delegation tests pin today's wiring, the structural one keeps the next copy
from being born.
"""

import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

from argumentation_analysis.core.llm_service import (
    resolve_active_model_id,
    resolve_chat_endpoint,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

# Every knob a route resolver could consult. Each test owns all of them, so an
# inherited .env value cannot decide an outcome.
_ROUTE_VARS = (
    "OPENROUTER_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_CHAT_MODEL_ID",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_CHAT_MODEL_ID",
)

# The files that used to re-derive the toggle. `core/llm_service.py` is absent
# on purpose: it is where the route environment is allowed to be read.
_NON_CANONICAL_FILES = (
    "argumentation_analysis/orchestration/invoke_callables.py",
    "argumentation_analysis/plugins/coordinated_logic_plugin.py",
    "argumentation_analysis/services/nl_to_logic.py",
    "argumentation_analysis/services/ai_shield/layers/llm_validator.py",
)

_ROUTE_ENV_READ = re.compile(
    r"""environ(?:\.get\(\s*|\[\s*)["']"""
    r"""(OPENROUTER_[A-Z_]*|OPENAI_CHAT_MODEL_ID|OPENAI_BASE_URL|OPENAI_API_KEY)["']"""
)


def _seat_without_openrouter_model(monkeypatch: pytest.MonkeyPatch, model: str) -> None:
    """The seat ``.env.example`` prescribes: the OpenRouter pair, no model id.

    ``OPENROUTER_CHAT_MODEL_ID`` absent is what makes the canonical resolver
    jump to ``OPENAI_CHAT_MODEL_ID`` — the jump the two mirrors did not have.
    """
    for var in _ROUTE_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-synthetic-not-a-real-key")
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", model)


async def _nl_to_logic_model(monkeypatch: pytest.MonkeyPatch) -> str:
    """The model id ``nl_to_logic`` actually sends.

    Recorded on the client that site builds: the stub appends the request kwargs
    and then fails, so the retry loop ends without reaching Tweety validation.
    Nothing leaves the machine — ``openai.AsyncOpenAI`` is replaced.
    """
    from argumentation_analysis.services.nl_to_logic import NLToLogicTranslator

    sent: List[Dict[str, Any]] = []

    class _Completions:
        async def create(self, **kwargs: Any) -> Any:
            sent.append(kwargs)
            raise RuntimeError("recording stub — no API call is made")

    class _Chat:
        def __init__(self) -> None:
            self.completions = _Completions()

    class _Client:
        def __init__(self, **_kwargs: Any) -> None:
            self.chat = _Chat()

    monkeypatch.setattr("openai.AsyncOpenAI", _Client)
    translator = NLToLogicTranslator(max_retries=1)
    await translator._translate_with_llm("Un argument quelconque.", "propositional")

    assert sent, "nl_to_logic never built a chat completion — nothing to measure"
    return sent[0]["model"]


async def _all_site_models(monkeypatch: pytest.MonkeyPatch) -> Dict[str, str]:
    """The model id each migrated site would send/name, keyed by site."""
    from argumentation_analysis.orchestration.invoke_callables import _resolve_llm_route
    from argumentation_analysis.plugins.coordinated_logic_plugin import (
        _get_openai_client,
    )
    from argumentation_analysis.services.ai_shield.layers.llm_validator import (
        LLMValidatorLayer,
    )

    return {
        "core.resolve_active_model_id": resolve_active_model_id(),
        "invoke_callables._resolve_llm_route": _resolve_llm_route()[2],
        "coordinated_logic_plugin._get_openai_client": _get_openai_client()[1],
        "nl_to_logic._translate_with_llm": await _nl_to_logic_model(monkeypatch),
        "llm_validator.LLMValidatorLayer": LLMValidatorLayer()._model,
    }


async def test_measured_seat_agrees_with_the_canonical_resolver(monkeypatch):
    """THE measured divergence, on the seat the repo prescribes.

    Pre-repair this reddens on **model values**: ``gpt-5-mini`` from the two
    mirrors (class A — no #1930 substitution) and ``openai/gpt-5.6-luna`` from
    the three literals (class B) — never on an ImportError.
    """
    _seat_without_openrouter_model(monkeypatch, model="gpt-5-mini")  # retired (#1930)
    canonical = resolve_chat_endpoint()[2]
    assert canonical == "gpt-5.6-luna", "the canonical resolver must substitute it"

    models = await _all_site_models(monkeypatch)

    divergent = {site: model for site, model in models.items() if model != canonical}
    assert (
        not divergent
    ), f"sites diverging from the canonical model {canonical!r}: {divergent}"


async def test_no_site_names_a_provider_prefixed_literal(monkeypatch):
    """Class B isolated: same seat, a NON-retired ``OPENAI_CHAT_MODEL_ID``.

    The two mirrors agreed pre-repair in this configuration (the model is not
    obsolete, so the missing substitution was invisible) — which is exactly why
    the three ``openai/gpt-5.6-luna`` literals need their own case: they diverge
    by *prefix* whenever ``OPENROUTER_CHAT_MODEL_ID`` is absent.
    """
    _seat_without_openrouter_model(monkeypatch, model="gpt-5.6-luna")

    models = await _all_site_models(monkeypatch)

    assert set(models.values()) == {"gpt-5.6-luna"}, models


async def test_declared_openrouter_model_control_agreed_before_and_after(monkeypatch):
    """Non-vacuity control: this case passed on pre-repair main too.

    With ``OPENROUTER_CHAT_MODEL_ID`` set, all five sites already agreed — so a
    green suite here cannot be read as "the repair fixed what was never broken".
    It pairs with the measured-seat test to show the divergence was
    configuration-dependent, not universal.
    """
    for var in _ROUTE_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-synthetic-not-a-real-key")
    monkeypatch.setenv("OPENROUTER_CHAT_MODEL_ID", "gpt-5.6-luna")
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "gpt-4o")  # never consulted

    models = await _all_site_models(monkeypatch)

    assert set(models.values()) == {"gpt-5.6-luna"}, models


async def test_every_site_calls_the_canonical_resolver(monkeypatch):
    """Delegation, not coincidence: make the canonical resolver return a
    sentinel and check each site follows it.

    A copy that re-derived the toggle from the environment cannot see the
    sentinel, whatever the environment says — so this reddens on any re-inlined
    resolver. On pre-repair main it fails because the delegates do not exist
    (``AttributeError`` on the patch), which is the point: the delegation is
    what is being asserted.
    """
    import argumentation_analysis.core.llm_service as llm_service
    import argumentation_analysis.orchestration.invoke_callables as invoke_callables
    import argumentation_analysis.plugins.coordinated_logic_plugin as coordinated
    import argumentation_analysis.services.ai_shield.layers.llm_validator as validator
    import argumentation_analysis.services.nl_to_logic as nl_to_logic

    sentinel = (
        "sk-sentinel-not-a-real-key",
        "https://sentinel.invalid/v1",
        "sentinel-model",
    )

    def _sentinel_resolver(*_args: Any, **_kwargs: Any):
        return sentinel

    for module in (llm_service, invoke_callables, coordinated, nl_to_logic, validator):
        monkeypatch.setattr(module, "resolve_chat_endpoint", _sentinel_resolver)

    from argumentation_analysis.orchestration.invoke_callables import _resolve_llm_route
    from argumentation_analysis.plugins.coordinated_logic_plugin import (
        _get_openai_client,
    )
    from argumentation_analysis.services.ai_shield.layers.llm_validator import (
        LLMValidatorLayer,
    )

    assert resolve_active_model_id() == "sentinel-model"
    assert _resolve_llm_route() == (
        "sk-sentinel-not-a-real-key",
        "https://sentinel.invalid/v1",
        "sentinel-model",
        "openai",  # classify_route of a non-OpenRouter endpoint
    )
    assert _get_openai_client()[1] == "sentinel-model"
    assert await _nl_to_logic_model(monkeypatch) == "sentinel-model"

    layer = LLMValidatorLayer()
    assert layer._model == "sentinel-model"
    assert layer._base_url == "https://sentinel.invalid/v1"


@pytest.mark.parametrize("relpath", _NON_CANONICAL_FILES)
def test_no_non_canonical_file_reads_the_route_environment(relpath: str) -> None:
    """Structural guard: among the migrated files, the route environment is
    read in ``core/llm_service.py`` and nowhere else.

    The delegation test pins today's call graph; this one pins the file text, so
    a future copy that "just needs the key here" reddens at review time instead
    of at the next silent divergence.
    """
    source = (REPO_ROOT / relpath).read_text(encoding="utf-8")

    found = sorted(set(_ROUTE_ENV_READ.findall(source)))

    assert not found, (
        f"{relpath} reads the route environment ({found}) — it must call "
        "resolve_chat_endpoint instead of re-deriving the toggle (#2352)."
    )
