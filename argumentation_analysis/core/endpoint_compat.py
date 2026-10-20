"""#3096 — ONE wire-compat decision per provider, read by every JSON-mode site.

Measured on the Anthropic OpenAI-compatible endpoint (probes 20/10, on
``claude-haiku-5-5`` through ``https://api.anthropic.com/v1/``):

* ``response_format {"type": "json_object"}`` → **400** ("Input should be
  'json_schema'");
* ``{"type": "json_schema", ...}`` is accepted **only with ``strict: true``**;
* ``temperature`` → **400** ("`temperature` is deprecated for this model") —
  the stakes extractor's hardcoded 0.3 died there, silently (its broad
  ``except`` returned an empty result the phase reported as ``completed``);
* ``seed`` → accepted (200).

Before this module, each call site spelled its own ``response_format`` (four
literal copies of ``{"type": "json_object"}``), so an endpoint that rejects
one parameter was discovered per site, by failure. The decision now lives
here, declared once per provider:

* a **schema-bearing** call sends ``json_schema`` with ``strict: true`` on
  providers that reject ``json_object`` — the schema is the same contract the
  prompt already states in prose;
* a call without a schema on such a provider sends NO ``response_format``
  (prompt-only JSON — the instruction stays in the prompt);
* every other provider keeps ``json_object`` (the measured-working mode the
  existing cassettes were recorded with — cache keys unchanged on those
  routes).

Sampling parameters follow the same table: a provider that rejects a
parameter never receives it (``sampling_kwargs`` strips it), mirroring
``is_reasoning_model`` suppression in ``llm_service`` — but WITHOUT touching
that module (the route naming is #3095/#3096 item 6, another lane's file).

This module deliberately does not build clients or resolve routes: it reads
the ``base_url`` the caller already resolved (or resolves it once itself via
``resolve_chat_endpoint``, a pure env read — never a network call).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("UnifiedPipeline")

# The decision table. A provider enters this table ONLY on a measured
# rejection (STOP&REPAIR: no speculative entries). "anthropic" = Anthropic's
# OpenAI-compatible endpoint; everything else keeps the OpenAI-compatible
# defaults the fleet's cassettes were recorded under.
_REJECTS_JSON_OBJECT: Tuple[str, ...] = ("anthropic",)
_REJECTS_TEMPERATURE: Tuple[str, ...] = ("anthropic",)

_ANTHROPIC_MARKER = "api.anthropic.com"


def classify_json_provider(base_url: str) -> str:
    """Classify an endpoint for JSON-mode purposes (NOT a route rename).

    Distinct vocabulary from ``llm_service.classify_route`` on purpose: that
    vocabulary names the route for the run log (#3095/#3096 item 6 own it);
    this one answers a different question — "which wire-compat table row
    applies" — and stays inside this module.
    """
    return "anthropic" if _ANTHROPIC_MARKER in (base_url or "") else "openai-compatible"


def json_response_format(
    base_url: str,
    schema_name: Optional[str] = None,
    schema: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """The ONE ``response_format`` decision for a JSON-expecting call.

    Returns the kwargs value to put under ``response_format`` — or ``None``
    for prompt-only JSON (the caller must then NOT set the key: sending
    ``response_format=None`` is not the same request).

    * openai-compatible (default): ``{"type": "json_object"}`` — the mode
      every existing cassette was recorded with.
    * anthropic + schema: ``json_schema`` with ``strict: true`` (the only
      accepted form, measured).
    * anthropic without schema: ``None`` — prompt-only JSON.
    """
    provider = classify_json_provider(base_url)
    if provider in _REJECTS_JSON_OBJECT:
        if schema is None or schema_name is None:
            return None
        return {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "schema": schema,
                "strict": True,
            },
        }
    return {"type": "json_object"}


def sampling_kwargs(base_url: str, requested: Dict[str, Any]) -> Dict[str, Any]:
    """Filter sampling parameters the endpoint rejects (declared table).

    ``temperature`` on the anthropic endpoint is a measured 400 — the caller's
    determinism params are stripped of anything the provider's row rejects,
    exactly like ``is_reasoning_model`` suppression, but provider-keyed. An
    empty ``requested`` returns empty (no invention of parameters).
    """
    provider = classify_json_provider(base_url)
    if provider in _REJECTS_TEMPERATURE and "temperature" in requested:
        dropped = requested["temperature"]
        filtered = {k: v for k, v in requested.items() if k != "temperature"}
        logger.info(
            "#3096: dropping temperature=%s — %s endpoint rejects it "
            "(measured 400, 'temperature is deprecated for this model')",
            dropped,
            provider,
        )
        return filtered
    return dict(requested)


def resolved_json_response_format(
    schema_name: Optional[str] = None,
    schema: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Decision helper for sites that do not carry the base_url themselves.

    Resolves the endpoint once from the environment (pure env read via
    ``llm_service.resolve_chat_endpoint`` — same resolver every client is
    built from, so the decision matches the client the caller holds) and
    returns ``(response_format_or_None, base_url)``.
    """
    from argumentation_analysis.core.llm_service import resolve_chat_endpoint

    _api_key, base_url, _model_id = resolve_chat_endpoint()
    return json_response_format(base_url, schema_name, schema), base_url
