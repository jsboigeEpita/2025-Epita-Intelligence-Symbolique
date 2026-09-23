"""Cut the LLM route for one test (#2444).

A test whose verdict does not read a model output must not reach a model. The
unit gate used to enforce that by patching one SDK class per test
(``openai.AsyncOpenAI``). That reopened the leak each time a new kind of client
appeared: #2331 added a sync ``openai.OpenAI`` client to the quality phase, and
four gate tests went back to the network (16 billed requests per CI run).

This helper cuts the route itself instead. Every raw-SDK caller resolves its
endpoint through ``core.llm_service.resolve_chat_endpoint`` (#2352), and that
resolver reads the environment on each call. Without a key it returns
``api_key == ""``, which every caller reads as "no LLM": the async client is
not built, the sync agentic client is not built, and each phase takes its named
degraded path. The test should then assert that path, for example
``agentic_wiring["mode"] == "degraded_no_route"`` on the quality phase.

The cut lasts for the test only (``monkeypatch``). It is checked on the spot: if
the resolver still finds a key, a variable was added to it that this list does
not name, and the helper raises instead of letting the test leak.
"""

from typing import Tuple

# The variables ``resolve_chat_endpoint`` takes a key from: the OpenRouter pair
# first, then the OpenAI key.
LLM_ROUTE_VARS: Tuple[str, ...] = (
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "OPENAI_API_KEY",
)


def cut_llm_route(monkeypatch) -> None:
    """Remove the LLM route variables for this test and check the cut holds."""
    for name in LLM_ROUTE_VARS:
        monkeypatch.delenv(name, raising=False)

    from argumentation_analysis.core.llm_service import resolve_chat_endpoint

    api_key, base_url, _model = resolve_chat_endpoint()
    if api_key:
        raise AssertionError(
            f"cut_llm_route: resolve_chat_endpoint still returns a key for "
            f"{base_url} after removing {LLM_ROUTE_VARS}. It reads a variable "
            "this helper does not name."
        )
