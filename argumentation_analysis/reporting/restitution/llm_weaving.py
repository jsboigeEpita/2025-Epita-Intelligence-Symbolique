"""The one LLM call of the three restitution acts (#2345).

Actes I, II and III each conducted their narrative through the same six lines:
``try: raw = await llm_callable(prompt)``, ``except``: log a warning and return
``""``. Three copies, one defect: the exception lived only in the log, so the
caller, seeing an empty string, recorded *« le LLM n'a rien produit »* — a cause
it had not observed. A model that answered nothing and a call that raised
(timeout, refused key, transport error) reached the reader as the same motif.

``weave`` keeps the fail-loud contract (#1108: empty narrative, no template
fallback) and returns *why* the narrative is empty, so each act records the
cause in its ``degraded`` map — the state, not the log. Only the exception's
type name enters the motif: its message can quote the prompt or a credential,
so it stays in the log.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

# An async LLM callable: prompt in, completion text out (FB-29/38 injectable).
LlmCallable = Callable[[str], Awaitable[str]]

# Motif of the path where the call returned but carried no text.
MUTE_FAILURE = "le LLM n'a rien produit"


@dataclass(frozen=True)
class WeaveOutcome:
    """A woven narrative, or the observed reason there is none.

    ``failure`` is empty exactly when ``narrative`` is not.
    """

    narrative: str
    failure: str = ""


async def weave(prompt: str, llm_callable: LlmCallable, act_label: str) -> WeaveOutcome:
    """Conduct one act's narrative via the LLM (fail-loud, #1108)."""
    try:
        raw = await llm_callable(prompt)
    except Exception as exc:  # noqa: BLE001 — surface, don't fabricate
        logger.warning("%s LLM weaving failed (fail-loud): %s", act_label, exc)
        return WeaveOutcome("", f"l'appel au LLM a échoué ({type(exc).__name__})")
    narrative = str(raw).strip() if raw else ""
    if not narrative:
        return WeaveOutcome("", MUTE_FAILURE)
    return WeaveOutcome(narrative)
