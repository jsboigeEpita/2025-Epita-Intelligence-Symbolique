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
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

# An async LLM callable: prompt in, completion text out (FB-29/38 injectable).
LlmCallable = Callable[[str], Awaitable[str]]

# Motif of the path where the call returned but carried no text.
MUTE_FAILURE = "le LLM n'a rien produit"

# The degraded-map CODE an act files its cut under (#3658 item 46a). The guard
# reads the CODE, never the prose: ``restitution_acts_degraded`` is a closed
# code vocabulary at the producer (#3249), and a rule keyed on wording would
# drift with it. Exported so the producer and the reader cannot disagree.
CUT_CODE_SUFFIX = "_cut_length"


def cut_code(capability: str) -> str:
    """The key an act's cut takes in its degraded map, from the act's own key."""
    return f"{capability}{CUT_CODE_SUFFIX}"


@dataclass(frozen=True)
class WeaveOutcome:
    """A woven narrative, or the observed reason there is none.

    ``failure`` is empty exactly when ``narrative`` is not.

    ``cut`` (#3658 item 46a) is the reason a length-stopped call gives, and is
    empty when the call did not stop on ``finish_reason=length``. It is set in
    BOTH cut shapes: the cap spent before any text (then ``failure`` carries the
    same reason, and nothing is read as « rien produit ») and the cap spent
    mid-text (the kept prose is truncated, and the act must be recorded as cut
    rather than graded as a whole arm).
    """

    narrative: str
    failure: str = ""
    cut: str = ""


def cut_reason(cap: Optional[int] = None, kept_nothing: bool = False) -> str:
    """The reason a length-stopped act records (#3658 item 46a).

    The item-41 wording for the first reading, applied to the acts: the signal
    is the call's OWN finish reason, never an inference from a token count, and
    the cap the call spent is named so a reader can tell an 8 192 stop from a
    larger one without re-deriving it (#3658 item 36d).

    ``kept_nothing`` (#3658 item 41c) is the other measured outcome: the cap was
    spent before the act's first word — the likely shape on a route whose
    reasoning tokens are billed but not returned — so the wording must not
    claim prose that survived.
    """
    cap_text = f" (plafond {cap})" if cap else ""
    if kept_nothing:
        return (
            f"l'appel de l'acte s'est arrêté sur finish_reason=length{cap_text} : "
            "le plafond a été épuisé avant le premier mot de l'acte — rien "
            "n'a été produit, ce n'est pas une réponse vide du modèle"
        )
    return (
        f"l'appel de l'acte s'est arrêté sur finish_reason=length{cap_text} : "
        "l'acte a été coupé au milieu du texte — le début écrit avant la "
        "coupe est conservé, la suite n'a jamais été produite"
    )


def _finish_reason_of(llm_callable: LlmCallable) -> Optional[str]:
    """The call's own finish reason, when the callable exposes one.

    Same seam as the first reading's (#3658 item 36d): the production callable
    records the envelope's ``finish_reason`` on itself, and a plain callable (a
    test double) exposes ``last_finish_reason``. A string-valued enum is
    unwrapped so ``"length"`` is read either way; anything else is ``None``,
    which says nothing about the call — never a guess.
    """
    reason = getattr(llm_callable, "last_finish_reason", None)
    if reason is None:
        return None
    value = getattr(reason, "value", reason)
    return str(value) if value is not None else None


async def weave(prompt: str, llm_callable: LlmCallable, act_label: str) -> WeaveOutcome:
    """Conduct one act's narrative via the LLM (fail-loud, #1108)."""
    try:
        raw = await llm_callable(prompt)
    except Exception as exc:  # noqa: BLE001 — surface, don't fabricate
        logger.warning("%s LLM weaving failed (fail-loud): %s", act_label, exc)
        return WeaveOutcome("", f"l'appel au LLM a échoué ({type(exc).__name__})")
    narrative = str(raw).strip() if raw else ""
    cut = (
        cut_reason(
            cap=getattr(llm_callable, "last_max_tokens", None),
            kept_nothing=not narrative,
        )
        if _finish_reason_of(llm_callable) == "length"
        else ""
    )
    if not narrative:
        # #3658 item 46a — a cut call says so. « le LLM n'a rien produit »
        # described an observation the code had not made: on the measured
        # route the cap is spent on reasoning before the first word, so the
        # empty act is the ceiling's doing, not the model's silence.
        return WeaveOutcome("", cut or MUTE_FAILURE, cut)
    return WeaveOutcome(narrative, cut=cut)
