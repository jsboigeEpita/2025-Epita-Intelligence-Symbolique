# argumentation_analysis/core/llm_errors.py
"""Tell a provider failure apart from an unusable model output (#2832).

The logic agents degrade on any exception: ``text_to_belief_set`` returns
``(None, message)``, ``generate_queries`` returns ``[]``. That is the right
shape for a model whose *output* cannot be used — unparsable JSON, a formula the
parser rejects. The caller keeps running with a traced degradation, which is
#1019's doctrine: an input from calling code fails loud, a model output degrades.

It is the wrong shape for a *provider* failure. A rejected key, a rate limit, a
timeout or a 5xx is raised by the SDK, never produced by the model; collapsing it
into "the model said nothing" makes a dead or misconfigured provider look like an
ordinary empty result. Five authentic tests read exactly that (one passed on
``[]``, four skipped on ``None``) — measured on ai-01 with a dummy key, #2832.

The seat decides the shape of the exception, so the test is the FAMILY and never
a status code. Measured on po-2023 through the fleet gateway, a dummy key raises::

    semantic_kernel.exceptions.KernelInvokeException
      └─ __cause__: FunctionExecutionException
           └─ __cause__: openai.APIConnectionError('Connection error.')

while a direct api.openai.com route raises ``openai.AuthenticationError`` (401).
Both — plus rate limits, timeouts and 5xx — are ``openai.APIError`` descendants,
so walking the cause chain finds them wherever Semantic Kernel put them.
"""

from __future__ import annotations

from typing import Iterator, Optional

try:
    # Pinned in environment.yml (pip: openai==3.3.0). Imported defensively so a
    # path that loads ``argumentation_analysis.core`` without the SDK installed
    # still works — there simply are no provider errors to find in that case.
    from openai import APIError as _ProviderAPIError
except Exception:  # pragma: no cover - openai is a pinned dependency
    _ProviderAPIError = None  # type: ignore[assignment]

__all__ = ["provider_failure"]


def _cause_chain(exc: BaseException) -> Iterator[BaseException]:
    """Yield ``exc`` then its causes, guarding against cycles."""
    seen: set[int] = set()
    node: Optional[BaseException] = exc
    while node is not None and id(node) not in seen:
        seen.add(id(node))
        yield node
        node = node.__cause__ or node.__context__


def provider_failure(exc: BaseException) -> Optional[BaseException]:
    """Return the provider/transport failure in ``exc``'s cause chain, or None.

    ``None`` means the exception was not raised by the LLM provider — the
    caller may keep degrading it. A returned exception means the provider
    itself failed and the caller must let it out (a bare ``raise`` inside its
    ``except`` block preserves the chain and the original traceback).
    """
    if _ProviderAPIError is None:
        return None
    for node in _cause_chain(exc):
        if isinstance(node, _ProviderAPIError):
            return node
    return None
